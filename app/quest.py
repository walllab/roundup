

'''
Quest For Orthologs.

This module is responsible for creating a dataset for a release of the Quest
for Orthologs reference proteomes.  http://www.ebi.ac.uk/reference_proteomes/

This involves:

- Creating a dataset in which to work.
- Downloading the reference proteomes and processing them into a format suitable for a roundup dataset computation.
- Computing the orthologs
- Packaging the orthologs as a gzipped OrthoXML file for download on the website.
'''

import argparse
import os
import re
import subprocess
from pprint import pprint

import config # import config to set up DONES_DB_URL and other env vars.
import orthutil
import roundup.dataset as rd
import lsfdo


def makedirs(d, mode=0775):
    '''
    Idempotently make directory d (and any parent directories) if it is missing
    and return d
    '''
    if not os.path.exists(d):
        os.makedirs(d, mode)

    return d


class Quest(object):

    def __init__(self, ds):
        '''
        '''
        self.ds = ds
        self.dsid = rd.getDatasetId(ds) # e.g. 'qfo_2011_04'
        # assert that the dataset used to store a quest for orthologs
        # computation is named like 'qfo_2011_04'.
        m = re.search(r'^qfo_(?P<version>\d{4}_\d{2})$', self.dsid)
        if not m:
            msg = 'Dataset id {} does not match expected pattern of a "qfo_"'
            msg += ' prefix followed by a uniprot version (e.g. qfo_2011_04).'
            msg = msg.format(self.dsid)
            raise Exception(msg)
        else:
            self.version = m.group('version')

    # SOURCES

    def reference_proteomes_url(self):
        url = 'ftp://ftp.ebi.ac.uk/pub/databases/reference_proteomes/'
        url += 'current_release/Reference_Proteomes_{version}.tar.gz'.format(
            version=self.version)
        return url

    def reference_proteomes_dir(self):
        return os.path.join(rd.getSourcesDir(self.ds), 'quest_for_orthologs',
                            'reference_proteomes',)

    def reference_proteomes_unpacked_dir(self):
        return self.reference_proteomes_tarfile().rstrip('.tar.gz')

    def reference_proteomes_tarfile(self):
        return os.path.join(
            self.reference_proteomes_dir(),
            os.path.basename(self.reference_proteomes_url()))

    def download_reference_proteomes(self):
        url = self.reference_proteomes_url()
        dest = self.reference_proteomes_tarfile()
        makedirs(os.path.dirname(dest))
        cmd = 'curl --remote-time --output '+dest+' '+url
        subprocess.check_call(cmd, shell=True)

    def unpack_reference_proteomes(self):
        path = self.reference_proteomes_tarfile()
        
        # since the tarball vomits its contents into the current directory
        # extract it to a specific location.
        subprocess.check_call([
            'tar', '-C', makedirs(self.reference_proteomes_unpacked_dir()),
            '-xzf', path])

    def set_genomes_and_fasta_from_reference_proteomes(self):
        '''
        Move the genome fasta files into the genomes directory and add the
        genomes to the dataset genomes list.
        '''
        d = self.reference_proteomes_unpacked_dir()
        genomes = [] # ncbi taxon ids
        for fn in os.listdir(d):
            m = re.search(r'^(?P<taxon>\d+)\.fasta$', fn)
            if m:
                genome = m.group('taxon')
                fasta_path = os.path.join(d, fn)
                rd.addGenomeFasta(self.ds, genome, fasta_path)
                genomes.append(genome)

        pprint(genomes)
        print 'Number of genomes:', len(genomes)
        rd.setGenomes(self.ds, genomes)
        return genomes


    # WORKFLOW

    def workflow(self):

        ns = 'roundup_dataset_{}_dones'.format(self.dsid)

        # helper functions
        def dofunc(name, func, *args, **kws):
            task = lsfdo.FuncTask(name, func, args, kws)
            lsfdo.do(ns, task)

        def dometh(name, obj, method, *args, **kws):
            task = lsfdo.MethodTask(name, obj, method, args, kws)
            lsfdo.do(ns, task)

        dofunc('prepare_dataset', rd.prepare_dataset, self.ds)
        dometh('download_reference_proteomes', self,
               'download_reference_proteomes')
        dometh('unpack_reference_proteomes', self, 'unpack_reference_proteomes')
        dometh('set_genomes_and_fasta_from_reference_proteomes', self,
               'set_genomes_and_fasta_from_reference_proteomes')
        dofunc('format_genomes', rd.format_genomes, self.ds)
        # format genomes in parallel
        # tasks = [
            # lsfdo.FuncTask('quest_format_genome {}'.format(genome),
                           # rd.format_genome, [self.ds, genome])
            # for genome in rd.getGenomes(self.ds)]
        # opts = [['-q', 'short', '-W', '60'] for task in tasks]
        # lsfdo.bsubmany(ns, tasks, opts, timeout=0)
        dofunc('prepare_jobs', rd.prepare_jobs, self.ds)
        dofunc('compute_jobs', rd.computeJobs, self.ds)
        dofunc('collate_orthologs', rd.collate_orthologs, self.ds)
        dofunc('zip_download_paths', rd.zip_download_paths, self.ds)


def convert_orthologs_for_upload(infile, outfile):
    '''
    The Ortholog Benchmarking website expects orthologs in a file
    where each line has an ortholog, represented as a pair of sequence
    ids separated by a tab.
    http://linneus54.inf.ethz.ch:8080/cgi-bin/gateway.pl
    '''
    with open(outfile, 'w') as fh:
        for params, orthologs in orthutil.orthDatasFromFileGen(infile):
            for qdb, sdb, distance in orthologs:
                fh.write('{qdb}\t{sdb}\n'.format(**locals()))



def main():


    parser = argparse.ArgumentParser(description='')
    subparsers = parser.add_subparsers()

    def add_quest_parser(funcname, help=None):
        '''
        Create a subparser named by funcname and add a dataset argument.
        Also add a function which will take dataset argument, create a Quest
        object, and invoke the method named by funcname on the object,
        passing any other arguments added to the subparser to the function.
        Return the subparser (so more arguments can be added if needed.
        '''
        subparser = subparsers.add_parser(funcname, help=help)
        subparser.add_argument('dataset', help='root directory of the dataset')
        def run_quest_func(dataset, **kws):
            return getattr(Quest(dataset), funcname)(**kws)
        subparser.set_defaults(func=run_quest_func)
        return subparser

    add_quest_parser('workflow')

    args = parser.parse_args()
    kws = dict(vars(args))
    del kws['func']
    return args.func(**kws)



if __name__ == '__main__':
    main()

