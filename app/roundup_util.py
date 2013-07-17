#!/usr/bin/env python

'''
acts as an interface between web code and other roundup code.
contain orchestra and roundup specific code.
'''

import argparse
import glob
import os

import config
import webconfig
import cacheutil
import filemsg
import cliutil
import lsf
import orthquery
import roundup.dataset
import roundup_common
import roundup_db
import util
import settings # django settings


#################################
# DATASET FILE DOWNLOAD FUNCTIONS

def get_dataset_download_datas(ds):
    '''
    Return a list containing the filename, path and size of the download files
    in dataset ds.

    Example output:

        [{'filename': '0.2_1e-10.orthologs.txt.gz',
        'size': '10.7GB',
        'path': '/groups/cbi/sites/roundup/datasets/4/download/roundup-4-orthologs_0.2_1e-10.txt.gz'},
        ...
        {'filename': 'genomes.tar.gz',
        'size': '2.2GB',
        'path': '/groups/cbi/sites/roundup/datasets/4/download/roundup-4-genomes.tar.gz'},
    '''
    datas = []
    download_dir = roundup.dataset.getDownloadDir(ds)
    paths = glob.glob(os.path.join(download_dir, '*'))
    files = sorted([p for p in paths if os.path.isfile(p)])
    for path in files:
        filename = os.path.basename(path)
        size = os.path.getsize(path)
        datas.append({'size': size, 'filename': filename, 'path': path})

    return datas


def static_download_path(release, filename):
    '''
    A path corresponding to the static url for a dataset download file.
    e.g. /www/roundup.hms.harvard.edu/app/public/static/download/4/roundup-4-genomes.tar.gz
    '''
    return os.path.join(webconfig.STATIC_DIR, 'download', release, filename)


def static_download_url(release, filename):
    '''
    A static url to a dataset download file.
    e.g. /static/download/4/roundup-4-genomes.tar.gz
    '''
    return os.path.join(settings.STATIC_URL, 'download', release, filename)


def link_downloads():
    '''
    Create links (and directories as needed) under the static web dir to the
    download files for various data sets.  This allows dataset files to be
    served statically (e.g. via apache) instead of through django.
    '''
    for ds in webconfig.ARCHIVE_DATASETS:
        release = roundup.dataset.getDatasetId(ds)
        for data in get_dataset_download_datas(ds):
            src = data['path']
            link = static_download_path(release, data['filename'])
            if not os.path.isdir(os.path.dirname(link)):
                os.makedirs(os.path.dirname(link), mode=0775)
            os.symlink(src, link)


##########################
# USED BY ROUNDUP WEB PAGE


def getOrthData(params):
    qdb, sdb, div, evalue = params
    pair = roundup_common.makePair(qdb, sdb)
    # get orthologs from db
    dbOrthologs = roundup_db.getOrthologs(release=webconfig.CURRENT_RELEASE,
                                          qdb=pair[0], sdb=pair[1],
                                          divergence=div, evalue=evalue)
    # get a map to external sequence ids
    sequenceIds = set()
    for ortholog in dbOrthologs:
        sequenceIds.add(ortholog[0])
        sequenceIds.add(ortholog[1])
    sequenceIds = list(sequenceIds)
    sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(
        release=webconfig.CURRENT_RELEASE, sequenceIds=sequenceIds)
    # 
    orthologs = [(sequenceIdToSequenceDataMap[qid][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                  sequenceIdToSequenceDataMap[sid][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                  str(dist)) for qid, sid, dist in dbOrthologs]
    return (params, orthologs)

    
def getRawResults(params):
    '''
    params: a 4-tuple of roundup params like (qdb, sdb, div, evalue).
    returns: a string containing all the orthologs for the params. in the form external query sequence id, external subject sequence id, and distance
      or None if the results do not exist.
    '''
    qdb, sdb, div, evalue = params
    pair = roundup_common.makePair(qdb, sdb)
    # get orthologs from db
    orthologs = roundup_db.getOrthologs(release=webconfig.CURRENT_RELEASE,
                                        qdb=pair[0], sdb=pair[1],
                                        divergence=div, evalue=evalue)
    # get a map to external sequence ids
    sequenceIds = set()
    for ortholog in orthologs:
        sequenceIds.add(ortholog[0])
        sequenceIds.add(ortholog[1])
    sequenceIds = list(sequenceIds)
    sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(
        release=webconfig.CURRENT_RELEASE, sequenceIds=sequenceIds)

    # format orthologs for download by mapping to external sequence ids.
    results = None
    if orthologs:
        results = ''.join(['{}\t{}\t{}\n'.format(sequenceIdToSequenceDataMap[qid][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                                 sequenceIdToSequenceDataMap[sid][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                                 dist) for qid, sid, dist in orthologs])
    return results
        

def getDatasetStats():
    return roundup.dataset.getDatasetStats(webconfig.CURRENT_DATASET)
    

def getSourceUrls(ds=webconfig.CURRENT_DATASET):
    return roundup.dataset.getSourceUrls(ds)


def getRelease(ds=webconfig.CURRENT_DATASET):
    return roundup.dataset.getReleaseName(ds)


def getReleaseDate(ds=webconfig.CURRENT_DATASET):
    return roundup.dataset.getReleaseDate(ds)


def getUniprotRelease(ds=webconfig.CURRENT_DATASET):
    return roundup.dataset.getUniprotRelease(ds)


def getGenomesAndNames():
    '''
    return: list of pairs of genome and name.  used by website for dropdowns.  
    '''
    return roundup_db.getGenomesAndNames(release=webconfig.CURRENT_RELEASE)


def getGenomeDescriptions():
    '''
    returns: a list of tuples with data describing each genome in roundup.
    '''
    genomesData = roundup_db.getGenomesData(release=webconfig.CURRENT_RELEASE)
    return genomesData


def do_orthology_query(cache_key, cache_file, query_kws):

    # run on lsf
    # cache results
    output = orthquery.doOrthologyQuery(**query_kws)
    return cache(output, cache_key, cache_file)


#########
# CACHING
# Used to cache query results.

def cacheHasKey(key):
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn),
                           table=webconfig.CACHE_TABLE).has_key(key)


def cacheGet(key, default=None):
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn),
                           table=webconfig.CACHE_TABLE).get(key, default=default)


def cacheSet(key, value):
    '''
    value: serialized in the cache as json, so only strings as dict keys.
    '''
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn),
                           table=webconfig.CACHE_TABLE).set(key, value)


def dropCreateCache():
    '''
    create a clean cache.  used when "refreshing" the roundup mysql database
    '''
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn),
                           table=webconfig.CACHE_TABLE, drop=True, create=True)


def cache(output, key, filename):
    '''
    Save output to filename.  Store filename in a cache (database) under key.
    '''
    util.dumpObject(output, filename)
    cacheSet(key, filename)
    return output


def bsub_orthology_query(cache_key, cache_file, query_kws, job_name):
    lsf_options = ['-o', '/dev/null', '-N',
                   # '-q', 'short', # short is a big queue but often busy
                   '-q', 'cbi_12h', # cbi_12h has few nodes but is rarely busy
                   '-W', '2:0',
                   '-J', job_name]
    filename = filemsg.dump({'cache_key': cache_key, 'cache_file': cache_file,
                             'query_kws': query_kws})
    cmd = cliutil.args(__file__) + ['orthquery', '--params', filename]
    return lsf.bsub(cmd, lsf_options)


########################
# COMMAND LINE INTERFACE


def cli_orthology_query(params):
    '''
    params: file containing the args and kws params
    '''
    # function args and kws
    kws = filemsg.load(params)
    do_orthology_query(**kws)


def main():
    parser = argparse.ArgumentParser(description='')
    subparsers = parser.add_subparsers()

    # do_orthology_query
    subparser = subparsers.add_parser('orthquery')
    subparser.add_argument('--params', required=True, help='A file of '
                           'serialized parameters.')
    subparser.set_defaults(func=cli_orthology_query)

    # do_orthology_query
    help = ['Make symbolic links from /static/ section of website to',
            'downloads for datasets (and quest for orthologs datasets).']
    subparser = subparsers.add_parser('link_downloads', help=' '.join(help))
    subparser.set_defaults(func=link_downloads)

    # parse command line arguments and run func with the keyword args.
    args = parser.parse_args()
    kws = dict(vars(args))
    del kws['func']
    return args.func(**kws)

if __name__ == '__main__':
    main()


#################
# DEPRECATED CODE
#################

# last line python emacs semantic cache bug fix
