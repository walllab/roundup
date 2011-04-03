#!/usr/bin/env python

'''
contain orchestra and roundup specific code.
'''

import os
import shutil
import re

import config
import cachedispatch
import cacheutil
import execute
import format_orthology_cluster_result
import roundup_common
import roundup_db
import roundup_compute
import util


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
    returns: a string containing contents of roundup results file described by params or None if the results do not exist.
    '''
    path = roundup_common.makeRoundupResultsCachePath(*params)
    if roundup_common.isValidRoundupFile(path):
        return open(path).read()        
    else:
        return None


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
                updates.append(dt.strftime('%Y/%m/%d')+ ': Updated existing genome '+format_orthology_cluster_result.roundupGenomeDisplayName(genome)+'\n')
            if msg.find('add_new_genome') != -1:
                genome = reGenome.search(msg).group(1)
                updates.append(dt.strftime('%Y/%m/%d')+ ': Added new genome '+format_orthology_cluster_result.roundupGenomeDisplayName(genome)+'\n')
    return updates


def getGenomeDescriptions(genomes):
    '''
    genomes: a list of genomes currently in roundup.
    returns: a list of genome descriptions for the current genomes in roundup.
    '''
    return [roundup_common.getGenomeDescription(genome) for genome in genomes]


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
    '''
    dispatcher = cachedispatch.Dispatcher(table=config.CACHE_TABLE, create=False, manager=util.ClosingFactoryCM(config.openDbConn))
    dispatcher.dispatch(fullyQualifiedFuncName, keywords, cacheKey, outputPath)


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
