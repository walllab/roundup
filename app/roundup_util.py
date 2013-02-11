#!/usr/bin/env python

'''
acts as an interface between web code and other roundup code.
contain orchestra and roundup specific code.
'''

import argparse

import cacheutil
import cliutil
import config
import lsf
import orthquery
import roundup.dataset
import roundup_common
import roundup_db
import util


##########################
# USED BY ROUNDUP WEB PAGE


def getOrthData(params):
    qdb, sdb, div, evalue = params
    pair = roundup_common.makePair(qdb, sdb)
    # get orthologs from db
    dbOrthologs = roundup_db.getOrthologs(qdb=pair[0], sdb=pair[1], divergence=div, evalue=evalue)
    # get a map to external sequence ids
    sequenceIds = set()
    for ortholog in dbOrthologs:
        sequenceIds.add(ortholog[0])
        sequenceIds.add(ortholog[1])
    sequenceIds = list(sequenceIds)
    sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(sequenceIds)
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
    orthologs = roundup_db.getOrthologs(qdb=pair[0], sdb=pair[1], divergence=div, evalue=evalue)
    # get a map to external sequence ids
    sequenceIds = set()
    for ortholog in orthologs:
        sequenceIds.add(ortholog[0])
        sequenceIds.add(ortholog[1])
    sequenceIds = list(sequenceIds)
    sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(sequenceIds)

    # format orthologs for download by mapping to external sequence ids.
    results = None
    if orthologs:
        results = ''.join(['{}\t{}\t{}\n'.format(sequenceIdToSequenceDataMap[qid][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                                 sequenceIdToSequenceDataMap[sid][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                                 dist) for qid, sid, dist in orthologs])
    return results
        

def getDatasetStats():
    return roundup.dataset.getDatasetStats(config.CURRENT_DATASET)
    

def getSourceUrls(ds=config.CURRENT_DATASET):
    return roundup.dataset.getSourceUrls(ds)


def getRelease(ds=config.CURRENT_DATASET):
    return roundup.dataset.getReleaseName(ds)


def getReleaseDate(ds=config.CURRENT_DATASET):
    return roundup.dataset.getReleaseDate(ds)


def getUniprotRelease(ds=config.CURRENT_DATASET):
    return roundup.dataset.getUniprotRelease(ds)


def getGenomesAndNames():
    '''
    return: list of pairs of genome and name.  used by website for dropdowns.  
    '''
    return roundup_db.getGenomesAndNames()


def getGenomeDescriptions():
    '''
    returns: a list of tuples with data describing each genome in roundup.
    '''
    genomesData = roundup_db.getGenomesData()
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
                           table=config.CACHE_TABLE).has_key(key)


def cacheGet(key, default=None):
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn),
                           table=config.CACHE_TABLE).get(key, default=default)


def cacheSet(key, value):
    '''
    value: serialized in the cache as json, so only strings as dict keys.
    '''
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn),
                           table=config.CACHE_TABLE).set(key, value)


def dropCreateCache():
    '''
    create a clean cache.  used when "refreshing" the roundup mysql database
    '''
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn),
                           table=config.CACHE_TABLE, drop=True, create=True)


def cache(output, key, filename):
    '''
    Save output to filename.  Store filename in a cache (database) under key.
    '''
    util.dumpObject(output, filename)
    cacheSet(key, filename)
    return output


########################
# COMMAND LINE INTERFACE


def cli_orthology_query(args):
    # function args and kws
    fargs, fkws = cliutil.params_from_file(args.params)
    do_orthology_query(*fargs, **fkws)


def bsub_orthology_query(cache_key, cache_file, query_kws, job_name):
    lsf_options = ['-o', '/dev/null', '-N', '-q', 'short', '-W', '2:0',
                  '-J', job_name]
    filename = cliutil.params_to_file(kws={'cache_key': cache_key,
                                   'cache_file': cache_file,
                                   'query_kws': query_kws})
    cmd = cliutil.script_argv(__file__) + ['orthquery', '--params', filename]
    return lsf.bsub(cmd, lsf_options)


def main():
    parser = argparse.ArgumentParser(description='')
    subparsers = parser.add_subparsers(dest='action')

    # do_orthology_query
    subparser = subparsers.add_parser('orthquery')
    subparser.add_argument('--params', required=True, help='A file of '
                           'serialized parameters.')
    subparser.set_defaults(func=cli_orthology_query)

    # parse command line arguments and invoke the appropriate handler.
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()


#################
# DEPRECATED CODE
#################

# last line python emacs semantic cache bug fix
