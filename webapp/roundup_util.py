#!/usr/bin/env python

'''
contain orchestra and roundup specific code.
'''

import os
import shutil
import re
import logging
import time

import config
import cachedispatch
import lsfdispatch
import cacheutil
import execute
import orthresult
import roundup_common
import roundup_db
import util
import LSF


##########################
# USED BY ROUNDUP WEB PAGE
##########################


def rawResultsExist(params):
    '''
    params: a 4-tuple of roundup params like (qdb, sdb, div, evalue).
    returns: True if the roundup results file exists and is valid.  False otherwise.
    '''
    path = roundup_common.makeRoundupResultsCachePath(*params)
    if roundup_common.isValidRoundupFile(path):
        return True
    else:
        return False
    

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
        

def getRoundupDataStats():
    '''
    used by the website to report the latest size of roundup.
    '''
    return util.loadObject(roundup_common.STATS_PATH)


def getUpdateDescriptions():
    '''
    returns history.txt log as a web-readable list of updates.
    '''
    reGenome = re.compile('genome=([^ ]+)')
    updates = []
    history = roundup_common.getHistory()
    # show the most recent updates first.
    history.sort(reverse=True)
    for dt, msg in history:
        if msg.startswith('compute'):
            if msg.find('replace_existing_genome') != -1:
                genome = reGenome.search(msg).group(1)
                updates.append(dt.strftime('%Y/%m/%d')+ ': Updated existing genome '+orthresult.roundupGenomeDisplayName(genome)+'\n')
            if msg.find('add_new_genome') != -1:
                genome = reGenome.search(msg).group(1)
                updates.append(dt.strftime('%Y/%m/%d')+ ': Added new genome '+orthresult.roundupGenomeDisplayName(genome)+'\n')
    return updates


def getGenomeDescriptions(genomes):
    '''
    genomes: a list of genomes currently in roundup.
    returns: a list of genome descriptions for the current genomes in roundup.
    '''
    descs = []
    for genome in genomes:
        try:
            descs.append(roundup_common.getGenomeDescription(genome))
        except IOError:
            # ignore missing description files to make the webpage more robust.
            logging.error('getGenomeDescriptions(): failing to get description for genome={}'.format(genome))
    return descs



def isEndedJob(jobId):
    '''
    The job is ended if there is not status for it on LSF (i.e. bjobs returns nothing for it)
    or if its status is DONE, EXIT, or ZOMBIE.
    '''
    infos = LSF.getJobInfos([jobId])
    if not infos: # pause to let lsf catch up.
        time.sleep(1);
        infos = LSF.getJobInfos([jobId])
    return bool(not infos or LSF.isEndedStatus(infos[0][LSF.STATUS]))


#########
# CACHING
#########


def dropCreateCache():
    '''
    create a clean cache.  used when "refreshing" the roundup mysql database
    '''
    cache = cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn), table=config.CACHE_TABLE, drop=True, create=True)

    
def cacheDispatch(fullyQualifiedFuncName=None, keywords=None, cacheKey=None, outputPath=None):
    '''
    fullyQualifiedFuncName: required. function name including modules, etc., e.g. 'foo_package.gee_package.bar_module.baz_class.wiz_func'
    keywords: dict of keyword parameters passed to the function.  optional.  defaults to {}
    outputPath: required. function output is serialized and written to this file.
    cacheKey: required. outputPath is added to cache under this key.
    run function, saving its output in the file and caching the filename under the cache key in the roundup cache.
    returns: output of fullyQualifiedFuncName
    '''
    dispatcher = cachedispatch.Dispatcher(table=config.CACHE_TABLE, create=False, manager=util.ClosingFactoryCM(config.openDbConn))
    return dispatcher.dispatch(fullyQualifiedFuncName, keywords, cacheKey, outputPath)


def lsfDispatch(fullyQualifiedFuncName=None, keywords=None):
    '''
    fullyQualifiedFuncName: required. function name including modules, etc., e.g. 'foo_package.gee_package.bar_module.baz_class.wiz_func'
    keywords: dict of keyword parameters passed to the function.  optional.  defaults to {}
    outputPath: required. function output is serialized and written to this file.
    cacheKey: required. outputPath is added to cache under this key.
    returns: jobId of lsf job.
    '''
    lsfOptions = ['-N', '-q shared_2h']
    return lsfdispatch.dispatch(fullyQualifiedFuncName, keywords, lsfOptions)


def lsfAndCacheDispatch(fullyQualifiedFuncName=None, keywords=None, cacheKey=None, outputPath=None):
    '''
    run fullyQualifiedFuncName on lsf and cache its output.
    returns: jobId of lsf job.
    '''
    newFunc = 'roundup_util.cacheDispatch'
    newKw = {'fullyQualifiedFuncName': fullyQualifiedFuncName, 'keywords': keywords, 'cacheKey': cacheKey, 'outputPath': outputPath}
    return lsfDispatch(newFunc, newKw)


def cacheHasKey(key):
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn), table=config.CACHE_TABLE).has_key(key)


def cacheGet(key, default=None):
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn), table=config.CACHE_TABLE).get(key, default=default)


def cacheSet(key, value):
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn), table=config.CACHE_TABLE).set(key, value)



#######################################
# GENOME AND RESULTS DELETION FUNCTIONS
# these function remove results files with this genome, loaded results from the mysql db, the current and any updated genome database
# the objective is to completely remove the db/genome from roundup, leaving no trace.
#######################################

def deleteGenomeById(dbId):
    '''
    dbId: Id of genome to delete, e.g. 'Homo_sapiens.aa'
    removes a genome from roundup as completely as possible.  removes any current and updated versions of the genome.
    removes all results files based on the genome.  removes all results based on the genome from the (mysql) database.
    note: this will not remove a genome that is currently being computed.
    '''
    print 'deleting %s'%dbId
    
    print 'deleting existing results files...'
    allPairs = roundup_common.getPairs(roundup_common.getGenomes())
    for qdb, sdb in allPairs:
        if qdb == dbId or sdb == dbId:
            for div, evalue in roundup_common.genDivEvalueParams():
                print 'cleaning', qdb, sdb, div, evalue
                path = roundup_common.makeRoundupResultsCachePath(qdb, sdb, div, evalue)
                if os.path.isfile(path):
                    os.remove(path)
            
    print 'deleting current database path (fasta, indices, metadata, etc.) if exists...'
    currentDbPath = roundup_common.currentDbPath(dbId)
    if os.path.isdir(currentDbPath):
        print '...deleting %s'%currentDbPath
        shutil.rmtree(currentDbPath)
        
    print 'deleting updated database path (fasta, indices, metadata, etc.) if exists...'
    updatedDbPath = roundup_common.updatedDbPath(dbId)
    if os.path.isdir(updatedDbPath):
        print '...deleting %s'%updatedDbPath
        shutil.rmtree(updatedDbPath)

    print 'deleting results from mysql db...'
    # this is slow b/c of the size of the table and indexing scheme used
    roundup_db.deleteGenomeByName(dbId)





# last line python emacs semantic cache bug fix