'''
WARNING: not well abstracted from the implementation.

various statistical summaries of various aspects of roundup: computations, current results, genomes, etc.
many functions are distributed on lsf to speed gathering results.  this can make the control flow confusing.
'''


import os
import uuid
import time
import glob
import pickle

import config
import roundup_common
import messagequeue
import util
import lsfdispatch
import execute
import nested
import roundup_compute
import fasta


def collectComputationStats(computeDir, outDir):
    '''
    outDir: location to put combined stats of pairs from computeDir
    computation stats are spread out
    '''
    pairs = roundup_compute.getPairs(computeDir)[:10]
    groupIds = []
    for gid, group in enumerate(util.groupsOfN(pairs, 1000)):
        gid = str(gid)
        groupIds.append(gid)
        kw = {'computeDir': computeDir, 'pairs': group, 'jobId': gid, 'workDir': outDir}
        # lsfdispatch.dispatch('roundup_stats.collectComputationStatsJob', keywords=kw, lsfOptions=['-q all_2h'])
        collectComputationStatsJob(computeDir, group, gid, outDir)


def collectComputationStatsJob(computeDir, pairs, jobId, workDir):
    '''
    read in the existing stats pickles for each pair and store them all in one big pickle in the workDir.
    '''
    pairToStats = {}
    for pair in pairs:
        qdb, sdb = pair
        # forward blast hits stats path
        # name = '_'.join([qdb, sdb, 'blast.stats.pickle'])
        name = '_'.join([qdb, sdb, 'stats.pickle'])
        path = roundup_common.makeCachePath(pair, name, dir=computeDir)
        print path
        fbh = util.loadObject(path) if os.path.exists(path) else None
        # reverse blast hits stats path
        # name = '_'.join([sdb, qdb, 'blast.stats.pickle'])
        name = '_'.join([sdb, qdb, 'stats.pickle'])
        path = roundup_common.makeCachePath(pair, name, dir=computeDir)
        rbh = util.loadObject(path) if os.path.exists(path) else None
        # rsd stats path
        rsdList = []
        for div, evalue in roundup_common.genDivEvalueParams():
            # name = '_'.join([qdb, sdb, div, evalue, 'roundup.stats.pickle'])
            name = '_'.join([qdb, sdb, div, evalue, 'stats.pickle'])
            path = roundup_common.makeCachePath(pair, name, dir=computeDir)
            if os.path.exists(path):
                rsdList.append(util.loadObject(path))
        pairToStats[pair] = {'fbh': fbh, 'rbh': rbh, 'rsdList': rsdList}
    util.dumpObject(pairToStats, os.path.join(workDir, jobId))


def genomeSizes():
    '''
    returns a dict mapping each current genome to the number of sequences in its fasta file.
    '''
    genomes = roundup_common.getGenomes()
    genomeToSize = dict((g, fasta.numSeqsInFastaDb(roundup_common.fastaFileForDbPath(roundup_common.makeDbPath(g)))) for g in genomes)
    return genomeToSize


def computationSize(computeDir, apparent=False):
    '''
    return the size (in KB) of all the data (genomes, results files, statistics files, etc.) in a computation
    '''
    paths = [os.path.join(computeDir, p) for p in os.listdir(computeDir)]
    print computeDir, pathSizes(paths, apparent)


def resultsSize(resultsDir, apparent=False):
    '''
    resultsDir: location of nested results files
    parallelize/distribute on all 2 character hex dirs
    compute the size (in KB) of everything in results dir
    '''
    paths = [os.path.join(resultsDir, p) for p in os.listdir(computeDir)]
    print resultsDir, pathSizes(paths, apparent)


def pathSizes(paths, apparent=False):
    with nested.NestedTempDir() as workDir:
        jobIds = []
        # submit jobs to parallelize getting size of resultsDir
        for path in paths:
            jobId = os.path.basename(path)
            jobIds.append(jobId)
            lsfdispatch.dispatch('roundup_stats.pathSizeJob', keywords={'path': path, 'workDir': workDir, 'jobId': jobId, 'apparent': apparent}, lsfOptions=['-q all_15m'])
        # wait for all jobs to finish
        while len(os.listdir(workDir)) < len(jobIds):
            time.sleep(10)
        # calculate size of main dir
        totalSize = 0
        for jobId in jobIds:
            path, size, duration = util.loadObject(os.path.join(workDir, jobId))
            print path, size, duration
            totalSize += size
        return totalSize
    

def pathSizeJob(path, workDir, jobId, apparent=False):
    '''
    path: e.g. /groups/rodeo/roundup/results/current/00
    workDir: dir to write size to.
    jobId: id of this job
    apparent: calculate the apparent size of the path.
    '''
    startTime = time.time()
    apparentOption = '--apparent' if apparent else ''
    sizeAndPath = execute.run("du -s %s %s"%(apparentOption, path)) # --apparent shows the real size of the files, not including "backups" that isilon makes.
    size = int(sizeAndPath.split()[0])
    duration = time.time() - startTime # track duration to see what lsf queue the job could be submitted to.
    util.dumpObject((path, size, duration), os.path.join(workDir, jobId))


# DEPRECATED CODE
# DEPRECATED CODE
# DEPRECATED CODE
# DEPRECATED CODE
# DEPRECATED CODE


def doMQ(dir=roundup_common.CURRENT_RESULTS_DIR):
    qid = 'stats_results_size_%s'%uuid.uuid4().hex
    paths = glob.glob(os.path.join(dir, '[0-9a-f][0-9a-f]'))
    mq = messagequeue.MessageQueue(qid, util.ClosingFactoryCM(config.openDbConn), create=True)
    for path in paths:
        jobId = os.path.basename(path)
        lsfdispatch.dispatch('roundup_stats.doMQJob', keywords={'path': path, 'qid': qid}, lsfOptions=['-q all_15m'])
    totalSize = 0
    while paths:
        try:
            with mq.read() as message:
                path, size, duration = pickle.loads(message)
                print path, size, duration
                totalSize += size
                paths.remove(path)
        except messagequeue.EmptyQueueError:
            time.sleep(10)
    print totalSize, dir
    return totalSize


def doMQJob(path, qid):
    '''
    path: e.g. /groups/rodeo/roundup/results/current/00
    qid: id for message queue on which to write results.
    '''
    startTime = time.time()
    sizeAndPath = execute.run("du -s --apparent %s"%path) # --apparent shows the real size of the files, not including "backups" that isilon makes.
    size = int(sizeAndPath.split()[0])
    duration = time.time() - startTime # track duration to see what lsf queue the job could be submitted to.
    mq = messagequeue.MessageQueue(qid, util.ClosingFactoryCM(config.openDbConn))
    mq.send(pickle.dumps((path, size, duration)))



# last line


