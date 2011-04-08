#!/usr/bin/env python

'''
HEY YOU!  RUNNING A COMPUTATION?  THEN READ ALL OF THIS COMMENTARY.  ALL OF IT.  TWICE.  BEFORE DOING ANY COMPUTATION.

What is a computation?  Currently it is a 3 step process: make a computation dir, compute the pairs of genomes, and complete the computation
by loading the orthologs into mysql and copying the files to the current roundup dataset.  Some pairs of genomes take only a few minutes to compute
all blast results and all 12 roundup parameter combinations.  Some pairs, like euykaryotes, can take around a week to compute all that.  A typical computation will have most of its pairs finish very quickly and a few pairs take a long time.  In order to fully utilize the cluster, it is best to run either a large roundup computation, where many updated genomes are computed, or run a smaller computation and when there are free slots on the cluster (i.e. when the computation has no more pairs pending on LSF) run another computation that 'depends' on the first computation.  See below for examples.

As of 2009/04/21, I would define a large computation as > 150 updated genomes and a smaller computation as ~50 updated genomes.

What is a computeDir?  It is a uniquely named directory within /groups/rodeo/compute/roundup/compute.  Updated and current genomes are copied into the computeDir and then every pair of genomes that needs to be computed (based on the updated genomes) has a directory created for it.  Theses pair dirs are nested just like roundup results files are.  Each pair is computed and its results are put in its pair dir.  A history of computation and other metadata is kept in computeDir.  

# How to remove old/unused computation dirs.  Do this occasionally, because computeDirs take up a lot of room.
step 1) go to /groups/rodeo/compute/roundup/compute
step 2) remove any old or unused dirs in there.

'''


import os
import datetime
import shutil
import time
import uuid
import logging

import config
import blast_results_db
import execute
import fasta
import LSF
import nested
import kvstore
import RoundUp
import roundup_common
import util
import roundup_db
import lsfdispatch
import BioUtilities


# NUM_PAIRS_DEFAULT = None # submit all pairs to lsf
NUM_PAIRS_DEFAULT = 20000 # avoid overloading lsf with jobs.


def deleteGenomeFromComputation(computeDir, genome):
    # delete pairs
    pairs = getPairs(computeDir)
    goodPairs = [p for p in pairs if genome not in p]
    badPairs = [p for p in pairs if genome in p]
    setPairs(computeDir, goodPairs)
    # delete genome
    computeDbPath = getComputeGenomePath(computeDir, genome)
    if os.path.exists(computeDbPath):
        roundup_common.removeDbPath(computeDbPath)
    # results, completes, stats, locks.  


######################
# CREATE A COMPUTATION
######################

def makeCurrentPairsComputation(pairs):
    '''
    useful for TESTING purposes.  Makes a small computation consisting of only a few pairs from the current genomes.
    '''
    computeDir = prepareComputeDir()
    genomes = list(set([p[0] for p in pairs] + [p[1] for p in pairs]))
    for genome in genomes:
        sourceDbPath = roundup_common.currentDbPath(genome)
        computeDbPath = getComputeGenomePath(computeDir, genome)
        roundup_common.copyDbPath(sourceDbPath, computeDbPath)
    setPairs(computeDir, pairs)
    return computeDir


def makeNewAndSmallGenomesComputation(numGenomes=None, depends=None):
    '''
    make a computation only with new genomes (not updated current genomes) and select the smallest genomes (by number of sequences) first, up to numGenomes.
    this is like makeUpdatedComputation, but it only does new genomes and it orders the genomes by size before taking the first numGenomes ones.
    '''
    computeDir = prepareComputeDir()
    updatedGenomesAndPaths, dependsGenomesAndPaths, currentGenomesAndPaths = getEachGenomesAndPaths(depends)
    
    newGenomesAndPaths = {}
    for genome, path in updatedGenomesAndPaths.items():
        if genome not in dependsGenomesAndPaths and genome not in currentGenomesAndPaths:
            newGenomesAndPaths[genome] = path
    sortedSizesAndNewGenomes = sorted([(fasta.numSeqsInFastaDb(roundup_common.fastaFileForDbPath(newGenomesAndPaths[g])), g) for g in newGenomesAndPaths])
    for x in sortedSizesAndNewGenomes:
        print x
    someNewGenomesAndPaths = dict((genome, newGenomesAndPaths[genome]) for size, genome in sortedSizesAndNewGenomes[:numGenomes])
    print 'len someNewGenomesAndPaths:', len(someNewGenomesAndPaths)
    pairs = prepareUpdatedComputation(computeDir, someNewGenomesAndPaths, dependsGenomesAndPaths, currentGenomesAndPaths)
    newGenomes = someNewGenomesAndPaths.keys()
    metadata = {'numGenomes': numGenomes, 'newGenomes': newGenomes, 'pairs': pairs, 'depends': depends}
    dumpComputationMetadata(computeDir, metadata)
    util.writeToFile('makeNewAndSmallGenomesComputation: computeDir=%s\nnewGenomes=%s\ndepends=%s\n'%(computeDir, newGenomes, depends),
                     os.path.join(computeDir, makeUniqueDatetimeName(prefix='roundup_compute_history_')))
    return computeDir


def makeUpdatedComputation(numGenomes=None, depends=None):
    '''
    numGenomes: compute against this many updated genomes.  If None, compute all updated genomes.
    construct a new computation directory for at most numGenomes of updated genomes and every current genome.
    depends: a computeDirs that this computation depends upon, or None.  Used to start a computation before the previous computation (the "depends" computation)  has finished.
    if the computation in depends is not complete, it is used as the source for current genomes.
    returns: computeDir of new computation
    '''
    # create directory for this computation, copy genomes there, and calculate what pairs need rounding up.
    computeDir = prepareComputeDir()
    # get genomes and their locations
    updatedGenomesAndPaths, dependsGenomesAndPaths, currentGenomesAndPaths = getEachGenomesAndPaths(depends)
    
    # select at most numGenomes updated genomes that are different from current and depends genomes.
    # a genome in both current and updated SHOULD always be different, so this is just a sanity check.
    # a genome in depends and updated CAN be the same if a depends computation is computing orthologs for the updated genome and has not completed yet.
    filteredUpdatedGenomesAndPaths = {}
    for genome, path in updatedGenomesAndPaths.items():
        if genome in dependsGenomesAndPaths and roundup_common.dbPathsEqual(path, dependsGenomesAndPaths[genome]):
            continue
        elif genome in currentGenomesAndPaths and roundup_common.dbPathsEqual(path, currentGenomesAndPaths[genome]):
            raise Exception('makeUpdatedComputation(): updated genome == current genome!.  genome: %s, updatedPath: %s, currentPath: %s'%(genome, path, currentGenomesAndPaths[genome]))
        else:
            filteredUpdatedGenomesAndPaths[genome] = path
    # limit updatedGenomes to numGenomes
    someUpdatedGenomesAndPaths = dict(filteredUpdatedGenomesAndPaths.items()[:numGenomes])

    # move genomes into compute dir, create pairs directories for the pairs to be computed.
    pairs = prepareUpdatedComputation(computeDir, someUpdatedGenomesAndPaths, dependsGenomesAndPaths, currentGenomesAndPaths)
    # write metadata and history
    updatedGenomes = someUpdatedGenomesAndPaths.keys()
    metadata = {'numGenomes': numGenomes, 'updatedGenomes': updatedGenomes, 'pairs': pairs, 'depends': depends}
    dumpComputationMetadata(computeDir, metadata)
    util.writeToFile('makeUpdatedComputation: computeDir=%s\nupdatedGenomes=%s\ndepends=%s\n'%(computeDir, updatedGenomes, depends),
                     os.path.join(computeDir, makeUniqueDatetimeName(prefix='roundup_compute_history_')))
    return computeDir


################################
# IMPORT OR EXPORT A COMPUTATION
################################

# Importing is a two-step process:
#   Copy all the results from resultsDir to computeDir.  This is parallelized so it does not take days.
#   Mark pairs that have all results completed as complete.

def exportComputationToAmazon(computeDir, exportDir, pairs=None):
    '''
    exports the genomes of the parameter combinations of the pairs that are not complete in a format suitable for AWS roundup pipeline.
    '''
    # put genomes in a genomes directory
    exportGenomesDir = os.path.join(exportDir, 'genomes')
    os.makedirs(exportGenomesDir, 0770)
    for genome in getGenomesFromComputeDir(computeDir):
        computeDbPath = getComputeGenomePath(computeDir, genome)
        exportDbPath = os.path.join(exportGenomesDir, genome)
        # print genome
        roundup_common.copyDbPath(computeDbPath, exportDbPath)

    # create a list of pairs that need computation
    if pairs is None:
        pairs = getPairs(computeDir)
    util.dumpObject(pairs, os.path.join(exportDir, 'pairs.pickle'))


def importResultsToComputation(computeDir, resultsDir):
    '''
    resultsDir: directory containing only roundup results files.
    imports the results files into the right locations in computeDir, marking any pairs complete if they are.
    '''
    paths = [os.path.join(resultsDir, f) for f in os.listdir(resultsDir)] # this could take a while on a dir with millions of files.
    for group in util.groupsOfN(paths, 2000):
        kw = {'computeDir': computeDir, 'paths': group}
        print lsfdispatch.dispatch('roundup_compute.importResultsToComputationSub', keywords=kw, lsfOptions=['-q all_unlimited'])


def importResultsToComputationSub(computeDir, paths):
    for path in paths:
        if not roundup_common.isRoundupFile(path):
            pass
        qdb, sdb, div, evalue = roundup_common.splitRoundupFilename(path)
        if not roundup_common.isSortedPair(qdb, sdb):
            raise Exception('importResultsToComputation(): pair incorrectly sorted. pair=%s %s.  file=%s'%(qdb, sdb, path))
        roundupResultsPath = roundup_common.makeRoundupResultsCachePath(qdb, sdb, div, evalue, dir=computeDir)
        shutil.copy(path, roundupResultsPath)
        markRoundupComplete(computeDir, qdb, sdb, div, evalue)
        

def finishImportResultsToComputation(computeDir):
    pairs = getPairs(computeDir)
    for pair in pairs:
        qdb, sdb = pair
        complete = True
        for div, evalue in roundup_common.genDivEvalueParams():
            if not isRoundupComplete(computeDir, qdb, sdb, div, evalue):
                complete = False
                break
        if complete:
            markPairComplete(computeDir, pair)
            

#####################################
# MOVE COMPUTATION TO ROUNDUP DATASET
#####################################

def completeComputationCopyResults(computeDir, pairs):
    logging.debug('completeComputationCopyResults %s %s'%(computeDir, len(pairs)))
    for qdb, sdb in pairs:
        key = 'complete copy pair %s %s'%(qdb, sdb)
        if getKVCacheValue(computeDir, key):
            continue
        startTime = time.time()
        for div, evalue in roundup_common.genDivEvalueParams():
            computePath = roundup_common.makeRoundupResultsCachePath(qdb, sdb, div, evalue, dir=computeDir)
            currentPath = roundup_common.makeRoundupResultsCachePath(qdb, sdb, div, evalue)
            shutil.copy(computePath, currentPath)
        totalTime = time.time() - startTime
        putKVCacheValue(computeDir, key, totalTime)
    

def completeComputationCopyGenomes(computeDir, genomes):
    logging.debug('completeComputationCopyGenomes %s %s'%(computeDir, len(genomes)))
    for genome in genomes:
        key = 'complete copy genome %s'%genome
        if getKVCacheValue(computeDir, key):
            continue
        startTime = time.time()
        computeDbPath = getComputeGenomePath(computeDir, genome)
        currentDbPath = roundup_common.currentDbPath(genome)
        updatedDbPath = roundup_common.updatedDbPath(genome)
        if not roundup_common.dbPathsEqual(computeDbPath, currentDbPath):
            if os.path.exists(currentDbPath):
                roundup_common.logHistory('compute replace_existing_genome genome=%s computeDir=%s\n'%(genome, computeDir))
                logging.log(roundup_common.ROUNDUP_LOG_LEVEL, 'removing current db %s' % currentDbPath)
                roundup_common.removeDbPath(currentDbPath)

            else:
                roundup_common.logHistory('compute add_new_genome genome=%s computeDir=%s\n'%(genome, computeDir))
            logging.log(roundup_common.ROUNDUP_LOG_LEVEL, 'moving compute/updated db %s to current %s' % (computeDbPath, currentDbPath))
            roundup_common.copyDbPath(computeDbPath, currentDbPath)
        # do not remove updated db if it is newer (=different) from db used to compute results.
        if roundup_common.dbPathsEqual(computeDbPath, updatedDbPath):
            logging.log(roundup_common.ROUNDUP_LOG_LEVEL, 'removing updated db %s which equals compute/updated db %s' % (updatedDbPath, computeDbPath))
            roundup_common.removeDbPath(updatedDbPath)
        totalTime = time.time() - startTime
        putKVCacheValue(computeDir, key, totalTime)


def completeComputationLoadGenomes(computeDir, genomes):
    logging.debug('completeComputationLoadGenomes %s %s'%(computeDir, len(genomes)))
    for genome in genomes:
        key = 'complete load genome %s'%genome
        if getKVCacheValue(computeDir, key):
            continue
        startTime = time.time()
        ids = BioUtilities.getIdsForDbPath(roundup_common.makeDbPath(genome, dir=getGenomesDirFromComputeDir(computeDir)))
        roundup_db.loadGenome(genome, ids)
        totalTime = time.time() - startTime
        putKVCacheValue(computeDir, key, totalTime)
        

def completeComputationLoadResults(computeDir, pairs):
    logging.debug('completeComputationLoadResults %s %s'%(computeDir, len(pairs)))
    seqIdMap = {} # optimize load with seqIdMap.
    for qdb, sdb in pairs:
        key = 'complete load pair %s %s'%(qdb, sdb)
        if getKVCacheValue(computeDir, key):
            continue
        startTime = time.time()
        for div, evalue in roundup_common.genDivEvalueParams():
            path = roundup_common.makeRoundupResultsCachePath(qdb, sdb, div, evalue, dir=computeDir)
            for conn in roundup_db.withRoundupDbConn():
                roundup_db.loadResultsFile(resultsFile=path, seqIdMap=seqIdMap)
        totalTime = time.time() - startTime
        putKVCacheValue(computeDir, key, totalTime)
                

def completeComputation1(computeDir, pairs=None):
    '''
    run this only after checking that there are no empty results files in the roundup results dir and in the computation dir.
    e.g. find /groups/rodeo/compute/roundup/compute/2007_09_13_01_46_36_hm8i-h -empty
    do not complete computation until any dependency computation is completed.
    if all pairs have been completed and look valid, their results are added to the mysql db, copied to the current roundup result dir
    and the updated genomes are copied the the current roundup genomes dir.
    '''
    # copy updated genomes to current and possibly remove updated genomes in parallel
    # insert results into mysql efficiently.
    
    logging.log(roundup_common.ROUNDUP_LOG_LEVEL, 'completeComputation():  computeDir=%s, pairs=%s'%(computeDir, pairs))
    util.writeToFile('completeComputation: computeDir='+str(computeDir)+'\npairs='+str(pairs)+'\n',
                     os.path.join(computeDir, makeUniqueDatetimeName(prefix='roundup_compute_history_')))

    if pairs is None:
        pairs = getPairs(computeDir)

    # double check that this computation is complete and that the results look valid.
    for pair in pairs:
        if not isPairComplete(computeDir, pair):
            raise Exception('completeComputation: incomplete or invalid pair: %s.  computeDir: %s' % (pair, computeDir))

    # any depends computations (that exist) must also be complete.
    metadata = loadComputationMetadata(computeDir)
    depends = metadata.get('depends', [])
    if depends and os.path.exists(depends) and not isComputationComplete(depends):
        raise Exception('completeComputation: incomplete dependency computation.  computeDir: %s  depends: %s'%(computeDir, depends))

    lsfOptions = ['-q all_unlimited', '-J %s'%getComputationJobName(computeDir)]
    # copy results files to current in parallel
    for group in util.groupsOfN(pairs, 1000):
        kw = {'computeDir': computeDir, 'pairs': group}
        print lsfdispatch.dispatch('roundup_compute.completeComputationCopyResults', keywords=kw, lsfOptions=lsfOptions)

    # copy updated genomes to current and possibly remove updated genomes in parallel
    genomes = getGenomesFromComputeDir(computeDir)
    for group in util.groupsOfN(genomes, 100):
        kw = {'computeDir': computeDir, 'genomes': group}
        print lsfdispatch.dispatch('roundup_compute.completeComputationCopyGenomes', keywords=kw, lsfOptions=lsfOptions)

    # copy load genomes to database.
    for group in util.groupsOfN(genomes, 100):
        kw = {'computeDir': computeDir, 'genomes': group}
        print lsfdispatch.dispatch('roundup_compute.completeComputationLoadGenomes', keywords=kw, lsfOptions=lsfOptions)



def completeComputation2(computeDir, pairs=None):
    '''
    run after completeComputation()
    run this only after checking that there are no empty results files in the roundup results dir and in the computation dir.
    e.g. find /groups/rodeo/compute/roundup/compute/2007_09_13_01_46_36_hm8i-h -empty
    do not complete computation until any dependency computation is completed.
    if all pairs have been completed and look valid, their results are added to the mysql db, copied to the current roundup result dir
    and the updated genomes are copied the the current roundup genomes dir.
    '''
    # copy updated genomes to current and possibly remove updated genomes in parallel
    # insert results into mysql efficiently.
    
    logging.log(roundup_common.ROUNDUP_LOG_LEVEL, 'completeComputation2():  computeDir=%s, pairs=%s'%(computeDir, pairs))
    util.writeToFile('completeComputation: computeDir='+str(computeDir)+'\npairs='+str(pairs)+'\n',
                     os.path.join(computeDir, makeUniqueDatetimeName(prefix='roundup_compute_history_')))

    if pairs is None:
        pairs = getPairs(computeDir)

    for pair in pairs:
        if not isPairComplete(computeDir, pair):
            raise Exception('completeComputation: incomplete or invalid pair: %s.  computeDir: %s' % (pair, computeDir))

    # any depends computations (that exist) must also be complete.
    metadata = loadComputationMetadata(computeDir)
    depends = metadata.get('depends', [])
    if depends and os.path.exists(depends) and not isComputationComplete(depends):
        raise Exception('completeComputation: incomplete dependency computation.  computeDir: %s  depends: %s'%(computeDir, depends))

    lsfOptions = ['-q all_unlimited', '-J %s'%getComputationJobName(computeDir)]

    # insert results into mysql efficiently.
    print 'submitting loading results jobs'
    startTime = time.time()
    for group in util.groupsOfN(pairs, 1000):
        kw = {'computeDir': computeDir, 'pairs': group}
        print lsfdispatch.dispatch('roundup_compute.completeComputationLoadResults', keywords=kw, lsfOptions=lsfOptions)
    totalTime = time.time() - startTime
    print 'finished in %s seconds'%int(totalTime)
    

def completeComputation3(computeDir, pairs=None):
    '''
    run after completeComputation()
    run this only after checking that there are no empty results files in the roundup results dir and in the computation dir.
    e.g. find /groups/rodeo/compute/roundup/compute/2007_09_13_01_46_36_hm8i-h -empty
    do not complete computation until any dependency computation is completed.
    if all pairs have been completed and look valid, their results are added to the mysql db, copied to the current roundup result dir
    and the updated genomes are copied the the current roundup genomes dir.
    '''
    # copy updated genomes to current and possibly remove updated genomes in parallel
    # insert results into mysql efficiently.
    
    logging.log(roundup_common.ROUNDUP_LOG_LEVEL, 'completeComputation3():  computeDir=%s, pairs=%s'%(computeDir, pairs))
    util.writeToFile('completeComputation: computeDir='+str(computeDir)+'\npairs='+str(pairs)+'\n',
                     os.path.join(computeDir, makeUniqueDatetimeName(prefix='roundup_compute_history_')))

    if pairs is None:
        pairs = getPairs(computeDir)

    for pair in pairs:
        if not isPairComplete(computeDir, pair):
            raise Exception('completeComputation: incomplete or invalid pair: %s.  computeDir: %s' % (pair, computeDir))

    # any depends computations (that exist) must also be complete.
    metadata = loadComputationMetadata(computeDir)
    depends = metadata.get('depends', [])
    if depends and os.path.exists(depends) and not isComputationComplete(depends):
        raise Exception('completeComputation: incomplete dependency computation.  computeDir: %s  depends: %s'%(computeDir, depends))

    print 'updatingRoundupDb()'
    startTime = time.time()
    for conn in roundup_db.withRoundupDbConn():
        roundup_db.updateRoundupDb()
    totalTime = time.time() - startTime
    print 'finished in %s seconds'%int(totalTime)

    # clear all cached roundup results
    # ideally this would only target roundup query cached data involving the results that have been computed.
    print 'clearing cached roundup results.'
    startTime = time.time()
    execute.run("find "+nested.DEFAULT_TMP_DIR+" -name 'roundup_web_result*' -type f -exec rm -f {} \;")
    totalTime = time.time() - startTime
    print 'finished in %s seconds'%int(totalTime)

    # store the new stats
    print 'updating current roundup data set stats'
    genomes = getGenomesFromComputeDir(computeDir)
    numGenomes = len(genomes)
    numGenomePairs = len(roundup_common.getPairs(genomes))
    numOrthologs = roundup_db.numOrthologs()
    util.dumpObject({'numGenomes': numGenomes, 'numGenomePairs': numGenomePairs, 'numOrthologs': numOrthologs}, roundup_common.STATS_PATH)
    totalTime = time.time() - startTime
    print 'finished in %s seconds'%int(totalTime)

    print 'dumping metadata'
    metadata['updatedPairs'] = pairs
    dumpComputationMetadata(computeDir, metadata)
    # markComputationComplete(computeDir) # not marking complete, b/c async jobs may not be done successfully yet.
    logging.info('completeComputation(): done. computeDir='+str(computeDir))


#################
# RUN COMPUTATION
#################

def computePairs(computeDir, pairs=None, numPairs=NUM_PAIRS_DEFAULT):
    '''
    numPairs: submit to LSF at most this many additional pairs. Used to avoid submitting more jobs to LSF than LSF can handle.  A value of None means submit all pairs.
    compute all pairs that are not completed and not running on LSF.
    '''
    if pairs is None:
        pairs = getPairs(computeDir)
    util.writeToFile('computePairs: computeDir='+str(computeDir)+'\nnumPairs='+str(numPairs)+'\npairs='+str(pairs)+'\n',
                     os.path.join(computeDir, makeUniqueDatetimeName(prefix='roundup_compute_history_')))
    if not pairs:
        raise Exception('runComputePairsProcess: Error, no pairs!  computeDir=%s, pairs=%s'%(computeDir, pairs))

    pairs = [pair for pair in pairs if not isPairComplete(computeDir, pair)]
    if numPairs is not None:
        pairs = pairs[:numPairs]
        
    for pair in pairs:
        if not isPairComplete(computeDir, pair):
            print 'submitting computePair %s'%(pair,)
            funcName = 'roundup_compute.computePair'
            keywords = {'computeDir': computeDir, 'pair': pair}
            # request that /scratch has at least ~1GB free space to avoid nodes where someone, not naming any names, has been a bad neighbor.
            lsfOptions = ['-R "scratch > 1000"', '-q '+LSF.LSF_LONG_QUEUE, roundup_common.ROUNDUP_LSF_OUTPUT_OPTION, '-J '+getComputePairJobName(computeDir, pair)]
            jobid = lsfdispatch.dispatch(funcName, keywords=keywords, lsfOptions=lsfOptions)
            msg = 'computePairs(): running pair on grid.  jobid=%s, computeDir=%s, pair=%s'%(jobid, computeDir, pair)
            logging.log(roundup_common.ROUNDUP_LOG_LEVEL, msg)
    

def computePair(computeDir, pair):
    '''
    ignore complete or running/locked pair
    precompute blast hits for pair.
    compute orthologs for pair
    '''
    if isPairComplete(computeDir, pair):
        return
    if isPairLocked(computeDir, pair):
        return

    lockPair(computeDir, pair)
    try:
        startTime = time.time()
        qdb, sdb = pair
        tmpDir = None
        with nested.NestedTempDir(dir=roundup_common.LOCAL_DIR) as tmpDir:
            qdbPath = roundup_common.makeDbPath(qdb, dir=getGenomesDirFromComputeDir(computeDir))
            sdbPath = roundup_common.makeDbPath(sdb, dir=getGenomesDirFromComputeDir(computeDir))
        
            # create local disk copies of genome fasta and blast indexes for blasting
            if roundup_common.ROUNDUP_LOCAL:
                queryDbPath = roundup_common.copyDbPathToDir(qdbPath, tmpDir)
                subjectDbPath = roundup_common.copyDbPathToDir(sdbPath, tmpDir)
            else:
                queryDbPath = qdbPath
                subjectDbPath = sdbPath
            dbToDbPath = {qdb: queryDbPath, sdb: subjectDbPath}
        
            # run blast if not complete
            for qdb, sdb in roundup_common.genBlastParams(*pair):
                if not isBlastComplete(computeDir, qdb, sdb):
                    computeBlast(computeDir=computeDir, qdb=qdb, sdb=sdb, dbToDbPath=dbToDbPath, workingDir=tmpDir)
                
            # run roundup if not complete
            qdb, sdb = pair
            if False in [isRoundupComplete(computeDir, qdb, sdb, div, evalue) for div, evalue in roundup_common.genDivEvalueParams()]:
                computeRoundup(computeDir, qdb, sdb, list(roundup_common.genDivEvalueParams()), tmpDir)

        # complete pair computation
        endTime = time.time()
        # print 'computePair', pair, datetime.datetime.fromtimestamp(endTime) - datetime.datetime.fromtimestamp(startTime)
        storePairStats(computeDir, pair, startTime, endTime)
        markPairComplete(computeDir, pair)
    finally:
        unlockPair(computeDir, pair)
    

def computeRoundup(computeDir, qdb, sdb, divEvalueParams, workingDir):
    '''
    divEvalueParams: e.g. [('0.2', '1e-20'), ('0.2', '1e-15'), ...]
    '''
    startTime = time.time()
    qdbpath = roundup_common.makeDbPath(qdb, dir=getGenomesDirFromComputeDir(computeDir))
    sdbpath = roundup_common.makeDbPath(sdb, dir=getGenomesDirFromComputeDir(computeDir))
    queryFastaPath = roundup_common.fastaFileForDbPath(qdbpath)
    subjectFastaPath = roundup_common.fastaFileForDbPath(sdbpath)
    resultsPaths = [roundup_common.makeRoundupResultsCachePath(qdb, sdb, div, evalue, dir=computeDir) for div, evalue in divEvalueParams]
    paramsAndRoundupResultsPaths = [(div, evalue, path) for (div, evalue), path in zip(divEvalueParams, resultsPaths)]
    forwardBlastHitsPath = roundup_common.makeBlastResultsCachePath(qdb, sdb, dir=computeDir)
    reverseBlastHitsPath = roundup_common.makeBlastResultsCachePath(sdb, qdb, dir=computeDir)
    message = 'RoundUp.roundup params: %s %s %s %s %s'%(queryFastaPath, subjectFastaPath, paramsAndRoundupResultsPaths, forwardBlastHitsPath, reverseBlastHitsPath)
    logging.log(roundup_common.ROUNDUP_LOG_LEVEL, message)
    RoundUp.roundup(queryFastaPath, subjectFastaPath, paramsAndRoundupResultsPaths, forwardBlastHitsPath, reverseBlastHitsPath, workingDir)
    endTime = time.time()
    # print 'computeRoundup', qdb, sdb, datetime.datetime.fromtimestamp(endTime) - datetime.datetime.fromtimestamp(startTime)
    for div, evalue in divEvalueParams:
        storeRoundupStats(computeDir, qdb, sdb, div, evalue, startTime=startTime, endTime=endTime)
        markRoundupComplete(computeDir, qdb, sdb, div, evalue)
    

def computeBlast(computeDir, qdb, sdb, dbToDbPath, workingDir):
    startTime = time.time()
    outpath = roundup_common.makeBlastResultsCachePath(qdb, sdb, dir=computeDir)
    qdbpath = dbToDbPath[qdb]
    sdbpath = dbToDbPath[sdb]
    queryFastaPath = roundup_common.fastaFileForDbPath(qdbpath)
    subjectIndexPath = roundup_common.fastaFileForDbPath(sdbpath)
    logging.log(roundup_common.ROUNDUP_LOG_LEVEL, 'computeBlastHits params: %s %s %s'%(qdbpath, sdbpath, outpath))
    maxEvalue = max([float(evalue) for evalue in roundup_common.EVALUES]) # evalues are strings like '1e-5'
    blast_results_db.computeBlastHits(queryFastaPath, subjectIndexPath, outpath, maxEvalue, workingDir=workingDir)
    endTime = time.time()
    # print 'computeBlast', qdb, sdb, datetime.datetime.fromtimestamp(endTime) - datetime.datetime.fromtimestamp(startTime)
    storeBlastStats(computeDir, qdb, sdb, startTime=startTime, endTime=endTime)
    markBlastComplete(computeDir, qdb, sdb)


#######
# LOCKS
#######
# primitive, non-ACID locking semantics so no more than one process will compute a pair at a time.
# previously roundup_compute checked if pair was complete and if not checked with lsf if a pair was running.
#  this avoided resubmitting a job when rerunning computePairs(), but took a long time b/c of filesystem slowness (checking for completes) and lsf slowness.
# current approach is to store completes in mysql, avoiding filesys slowness, and just resubmit incomplete jobs,
#  avoiding lsf slowness when submitting pairs in favor of running unnecessary jobs.

DEFAULT_LOCK_TIMEOUT = 3 * 24 * 3600 # 3 days in seconds

def lockPair(computeDir, pair, timeout=DEFAULT_LOCK_TIMEOUT):
    path = pairLockPath(computeDir, pair)
    lockedUntil = time.time() + timeout
    util.dumpObject(lockedUntil, path)


def unlockPair(computeDir, pair):
    path = pairLockPath(computeDir, pair)
    if os.path.exists(path):
        os.remove(path)


def isPairLocked(computeDir, pair):
    path = pairLockPath(computeDir, pair)
    if os.path.exists(path):
        lockedUntil = util.loadObject(path)
        if time.time() < lockedUntil:
            return True
    return False


def pairLockPath(computeDir, pair):
    qdb, sdb = pair
    name = '_'.join([qdb, sdb, 'pair.lock'])
    return roundup_common.makeCachePath(pair, name, dir=computeDir)
    

###########
# COMPLETES
###########

def isPairComplete(computeDir, pair):
    attrs = ['pair', pair[0], pair[1], 'done']
    key = ' '.join(attrs)
    return bool(int(getKVCacheValue(computeDir, key, 0)))

def markPairComplete(computeDir, pair):
    attrs = ['pair', pair[0], pair[1], 'done']
    key = ' '.join(attrs)
    putKVCacheValue(computeDir, key, 1)

def isBlastComplete(computeDir, qdb, sdb):
    attrs = ['blast', qdb, sdb, 'done']
    key = ' '.join(attrs)
    return bool(int(getKVCacheValue(computeDir, key, 0)))

def markBlastComplete(computeDir, qdb, sdb):
    attrs = ['blast', qdb, sdb, 'done']
    key = ' '.join(attrs)
    putKVCacheValue(computeDir, key, 1)

def isRoundupComplete(computeDir, qdb, sdb, div, evalue):
    attrs = ['rsd', qdb, sdb, div, evalue, 'done']
    key = ' '.join(attrs)
    return bool(int(getKVCacheValue(computeDir, key, 0)))

def markRoundupComplete(computeDir, qdb, sdb, div, evalue):
    attrs = ['rsd', qdb, sdb, div, evalue, 'done']
    key = ' '.join(attrs)
    putKVCacheValue(computeDir, key, 1)

def isComputationComplete(computeDir):
    attrs = ['computation', 'done']
    key = ' '.join(attrs)
    return bool(int(getKVCacheValue(computeDir, key, 0)))

def markComputationComplete(computeDir):
    attrs = ['computation', 'done']
    key = ' '.join(attrs)
    putKVCacheValue(computeDir, key, 1)


#################
# KEY-VALUE CACHE
#################
# HACK.  Should use a mysql table or some other full featured key-value store.
# this is a limited key value store, where a keys and values are strings separated by an = sign.
# Warning: put in an = sign in a key or value and see what happens
# Why? Implement a key-value store this way?
# It uses the filesystem, so is simple.  (No server.)
# It appends a key=value as a single line.  So as long as multiple processes can append a line, it can handle concurrency.
# For roundup, the computePair processes mark things complete, so concurrency is needed.
# It keeps all the data in one file, so it can be read quickly.
# Previous implementation had millions of complete files spread through filesys.  Took forever to iterate through them.
# Limitation: upon first calling getKVCacheValue(), the cache is, ah, cached in memory.  It will be oblivious to any puts that happen until it is next read into memory.

def getKVCacheValue(computeDir, key, default=None):
    return getKVCache(computeDir).get(key, default)

    
def putKVCacheValue(computeDir, key, value):
    getKVCache(computeDir).put(key, str(value))


KEY_VALUE_CACHE = {}
def getKVCache(computeDir):
    if KEY_VALUE_CACHE.has_key(computeDir):
        return KEY_VALUE_CACHE[computeDir]
    computeId = getComputeIdFromComputeDir(computeDir)
    # kv = kvstore.KVStore(util.ClosingFactoryCM(config.openDbConn), table='key_value_store_%s'%computeId, create=True)
    # HACK: give kvstore a conn object that never gets closed.
    kv = kvstore.KVStore(util.NoopCM(config.openDbConn()), table='key_value_store_%s'%computeId, create=True)
    KEY_VALUE_CACHE[computeDir] = kv
    return kv


#######
# PAIRS
#######

PAIRS_CACHE = {}
def getPairs(computeDir):
    if not PAIRS_CACHE.has_key(computeDir):
        pairs = []
        if os.path.exists(pairsCacheFile(computeDir)):
            with open(pairsCacheFile(computeDir)) as fh:
                for line in fh:
                    if line.strip():
                        pairs.append(line.split())
        PAIRS_CACHE[computeDir] = roundup_common.normalizePairs(pairs)
    return PAIRS_CACHE[computeDir]


def setPairs(computeDir, pairs):
    PAIRS_CACHE[computeDir] = pairs
    with open(pairsCacheFile(computeDir), 'w') as fh:
        for qdb, sdb in pairs:
            fh.write('%s %s\n'%(qdb, sdb))
    
        
def pairsCacheFile(computeDir):
    return os.path.join(computeDir, 'pairs.txt')    


##################
# HELPER FUNCTIONS
##################

def makeUniqueDatetimeName(datetimeObj=None, prefix='', suffix=''):
    '''
    prefix: e.g. 'results_'
    suffix: e.g. '.txt'
    datetimeObj: provide a datetime object if do not want to use the current date and time.
    returns: a unique name stamped with and sortable by current date and time, e.g. 'results_20090212_155450_e547be40-bca8-4a98-8a3e-1ed923dd97de.txt'
    '''
    if not datetimeObj:
        datetimeObj = datetime.datetime.now()
    return prefix + datetimeObj.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex + suffix


def getComputationJobName(computeDir):
    return '_'.join(['roundup', getComputeIdFromComputeDir(computeDir)])

    
def getComputePairJobName(computeDir, pair):
    return '_'.join(['roundup', getComputeIdFromComputeDir(computeDir), pair[0], pair[1]])
    
    
def getComputeIdFromComputeDir(computeDir):
    '''
    /groups/rodeo/compute/roundup/compute/20090327_115318_fede852da99f43f9b63a0ba6c0c58e59 -> 20090327_115318_fede852da99f43f9b63a0ba6c0c58e59
    '''
    return os.path.basename(computeDir)


#########
# GENOMES
#########

def getGenomesDirFromComputeDir(computeDir):
    return os.path.join(computeDir, 'genomes')


def getComputeGenomePath(computeDir, genome):
    return roundup_common.makeDbPath(genome, dir=getGenomesDirFromComputeDir(computeDir))


def getGenomesFromComputeDir(computeDir):
    return roundup_common.getGenomes(dir=getGenomesDirFromComputeDir(computeDir))


##########
# METADATA
##########

def dumpComputationMetadata(computeDir, metadata):
    util.dumpObject(metadata, os.path.join(computeDir, 'metadata.pickle'))
    

def loadComputationMetadata(computeDir):
    return util.loadObject(os.path.join(computeDir, 'metadata.pickle'))
    

#################
# STATS FUNCTIONS
#################
    
def storeBlastStats(computeDir, qdb, sdb, startTime, endTime):
    stats = {'qdb': qdb, 'sdb': sdb, 'startTime': startTime, 'endTime': endTime}
    pair = roundup_common.makePair(qdb, sdb)
    name = '_'.join([qdb, sdb, 'blast.stats.pickle'])
    path = roundup_common.makeCachePath(pair, name, dir=computeDir)
    util.dumpObject(stats, path)

    
def storeRoundupStats(computeDir, qdb, sdb, div, evalue, startTime, endTime):
    stats = {'qdb': qdb, 'sdb': sdb, 'div': div, 'evalue': evalue, 'startTime': startTime, 'endTime': endTime}
    pair = roundup_common.makePair(qdb, sdb)
    name = '_'.join([qdb, sdb, div, evalue, 'roundup.stats.pickle'])
    path = roundup_common.makeCachePath(pair, name, dir=computeDir)
    util.dumpObject(stats, path)


def storePairStats(computeDir, pair, startTime, endTime):
    qdb, sdb = pair
    qdbpath = roundup_common.makeBlastDbPath(roundup_common.makeDbPath(qdb, dir=getGenomesDirFromComputeDir(computeDir)))
    sdbpath = roundup_common.makeBlastDbPath(roundup_common.makeDbPath(sdb, dir=getGenomesDirFromComputeDir(computeDir)))
    qdbBytes = os.path.getsize(qdbpath)
    sdbBytes = os.path.getsize(sdbpath)
    qdbSeqs = fasta.numSeqsInPath(qdbpath)
    sdbSeqs = fasta.numSeqsInPath(sdbpath)
    stats = {'qdb': qdb, 'sdb': sdb, 'startTime': startTime, 'endTime': endTime,
             'qdbBytes': qdbBytes, 'sdbBytes': sdbBytes, 'qdbSeqs': qdbSeqs, 'sdbSeqs': sdbSeqs}
    name = '_'.join([qdb, sdb, 'pair.stats.pickle'])
    path = roundup_common.makeCachePath(pair, name, dir=computeDir)
    util.dumpObject(stats, path)


################################
# COMPUTATION CREATION FUNCTIONS
################################
    
def prepareComputeDir(dir=roundup_common.COMPUTE_DIR, computeId=None):
    '''
    dir: parent directory containing the created compute dir.
    computeId: if None, a unique id is created.  If not none, computeId is used to create the computeDir.
    creates the directories needed for a computation, ones for genomes, etc., all underneath a unique path.
    '''
    # make unique directory structure for computation.  Use the date as a prefix for human readability and sortability.
    if computeId is None:
        computeId = makeUniqueDatetimeName()
    computeDir = os.path.join(dir, computeId)
    os.makedirs(computeDir, 0770)
    genomesDir = getGenomesDirFromComputeDir(computeDir)
    os.makedirs(genomesDir, 0770)
    return computeDir


def getEachGenomesAndPaths(depends):
    # get genomes and their locations
    currentGenomesAndPaths = roundup_common.getGenomesAndPaths(roundup_common.CURRENT_GENOMES_DIR)
    if depends and os.path.exists(depends) and not isComputationComplete(depends):
        dependsGenomesAndPaths = roundup_common.getGenomesAndPaths(getGenomesDirFromComputeDir(depends))
        print 'dependsGenomesAndPaths', dependsGenomesAndPaths
    else:
        dependsGenomesAndPaths = {}
    updatedGenomesAndPaths = roundup_common.getGenomesAndPaths(roundup_common.UPDATED_GENOMES_DIR)
    return updatedGenomesAndPaths, dependsGenomesAndPaths, currentGenomesAndPaths


def prepareUpdatedComputation(computeDir, updatedGenomesAndPaths, dependsGenomesAndPaths, currentGenomesAndPaths):
    # collect genomes and paths, with updated taking precedence over depends and depends taking precedence over current.
    allGenomesAndPaths = {}
    allGenomesAndPaths.update(currentGenomesAndPaths)
    allGenomesAndPaths.update(dependsGenomesAndPaths)
    allGenomesAndPaths.update(updatedGenomesAndPaths)
    # move genomes into computeDir
    for genome in allGenomesAndPaths:
        sourceGenomePath = allGenomesAndPaths[genome]
        computeGenomePath = getComputeGenomePath(computeDir, genome)
        roundup_common.copyDbPath(sourceGenomePath, computeGenomePath)
    # prepare pairs directories for every pair of genomes that contains at least one genome from the updated genomes.
    allGenomes = allGenomesAndPaths.keys()
    allPairs = roundup_common.getPairs(allGenomes)
    pairs = [pair for pair in allPairs if pair[0] in updatedGenomesAndPaths or pair[1] in updatedGenomesAndPaths]
    setPairs(computeDir, pairs)
    return pairs



########################
# DEPRECATED / UNUSED
########################

# last line - python emacs bug fix
