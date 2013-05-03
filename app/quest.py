

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
import glob
import os
import re
import subprocess
import sys
from pprint import pprint

import fasta
import nested
import orthutil
import roundup.dataset as rd
import dones
import kvstore
import config


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
            msg += ' prefix followed by a uniprot version (e.g. 2011_04).'
            msg = msg.format(self.dsid)
            raise Exception(msg)
        else:
            self.version = m.group('version')

        # Dones
        ns = 'roundup_dataset_{}_dones'.format(self.dsid)
        connect = kvstore.make_closing_connect(config.openDbConn)
        k = kvstore.KStore(connect, ns=ns)
        self.dones = dones.Dones(k)

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


    def compute_jobs(self):
        '''
        A wrapper around roundup.dataset.computeJobs() to make it more
        compatible for use in workflow() by raising an exception when
        the jobs are not all done.
        '''
        all_done = rd.computeJobs(self.ds)
        if not all_done:
            # indicate to workflow that this step is not done yet.
            raise Exception('Jobs are not all done.')


    def format_genomes(self):
        '''
        A wrapper around roundup.dataset.format_genome to only format a 
        genome if it is not done already.
        '''
        for genome in rd.getGenomes(self.ds):
            self.do('format_genome {}'.format(genome),
                    rd.format_genome, self.ds)

    # WORKFLOW

    def do(self, name, func, *args, **kws):
        '''
        Use name to track whether or not func has been run.  If it has,
        skip it.  If it has not, run it with args and kws and mark it done
        if it successfully completes.
        '''
        if not self.dones.done(name):
            print 'Doing', name
            out = func(*args, **kws)
            self.dones.mark(name)
            return out

        print 'Done', name

    def workflow(self):

        self.do('prepare_dataset', rd.prepare_dataset, self.ds)
        self.do('download_reference_proteomes',
                self.download_reference_proteomes)
        self.do('unpack_reference_proteomes',
                self.unpack_reference_proteomes)
        # self.dones.unmark('set_genomes_and_fasta_from_reference_proteomes')
        self.do('set_genomes_and_fasta_from_reference_proteomes',
                self.set_genomes_and_fasta_from_reference_proteomes)
        self.do('format_genomes', self.format_genomes)
        self.do('prepare_jobs', rd.prepareJobs, self.ds)
        self.do('compute_jobs', self.compute_jobs)
        self.do('collate_orthologs', rd.collateOrthologs, self.ds)
        self.do('zip_download_paths', rd.zipDownloadPaths, self.ds)

        return

def do_all():
    pass
    # process proteomes into dataset genomes

    # compute orthologs

    # collate orthologs

    # convert orthologs to orthoxml

    # prepare as a downloadable file.



def convert_fasta(infile, outfile):
    '''
    Convert reference proteome fasta file namelines into a format that rsd can parse.
    Basically it changes the namelines from '>ns:id blah' to '>lcl|id' and
    removes some blank lines from the files.
    '''
    # set filterBlankLines because 
    # /groups/cbi/td23/quest_for_orthologs/v5/2011_04_reference_proteomes/9606_homo_sapiens.fasta
    # starts with a blank line and has a blank line within the file after a single sequence.  Weird.
    outlines = []
    for lines in fasta.readFastaLines(infile, filterBlankLines=True): 
        nameline = lines[0]
        seqlines = lines[1:]
        seqid = nameline.split(':')[1].split()[0]
        # add 'lcl' because ncbi blast expects it in order to parse namelines (like the ones we have)
        # when formating a fasta file, and we format thusly b/c roundup likes to retrieve fasta
        # sequences by id, for which parsing namelines when formatting is required.
        # More on namelines: http://www.ncbi.nlm.nih.gov/books/NBK7183/?rendertype=table&id=ch_demo.T5
        newNameline = '>lcl|' + seqid + '\n'
        outlines.append(newNameline)
        outlines.extend(seqlines)
    with open(outfile, 'w') as fh:
        fh.write(''.join(outlines))

    numIn = fasta.numSeqsInPath(infile)
    numOut = fasta.numSeqsInPath(outfile)
    if numIn != numOut:
        msg = 'Different number of sequences between infile and outfile.'
        msg += ' infile={}, num_in_seqs={}, outfile={}, num_out_seqs={}\n'
        print msg.format(infile, numIn, outfile, numOut)


def convert_fastas(ds, srcdir):
    '''
    Converts all the reference proteomes fasta files to a nameline format rsd likes,
    Also writes those files to the appropriate location in the dataset and
    parses the genomeToTaxon and genomeToName metadata from the srcdir filenames
    and saves that info.
    All fasta files are in srcdir and named <taxonid>_<genomename>.fasta
    '''
    print 'convert_fastas'
    infiles = glob.glob(os.path.join(srcdir, '*_*.fasta'))
    # example filenames: 10090_mus_musculus.fasta, 6239_caenorhabditis_elegans.fasta 
    filenameRE = re.compile('(\d+)_(.+?)\.fasta')
    print 'infiles', infiles
    with nested.NestedTempDir() as tmpDir:
        fasta_file = os.path.join(tmpDir, 'converted.fasta')
        cmd = '../webapp/python ../webapp/roundup/dataset.py add_fasta {ds}'
        cmd += ' {genome} {fasta_file} --name {name} --taxon {taxon}'
        for infile in infiles:
            m = filenameRE.search(os.path.basename(infile))
            taxon, name = m.group(1), m.group(2)
            genome = taxon
            convert_fasta(infile, fasta_file)
            # copy fasta file into dataset.  update name and taxon metadata.
            cmd2 = cmd.format(**locals())
            print 'running:', cmd2
            subprocess.check_call(cmd2, shell=True)


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


    def do_fastas(args):
        return convert_fastas(args.dataset, args.srcdir)

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

