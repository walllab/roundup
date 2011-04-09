#!/usr/bin/env python
 
# test getGenomes()
# test splitting source files
# test preparing computation.  are the jobs and pair files created?
#   are the new_pairs.txt and old_pairs.txt created?
# test blast_results_db copyToWorking functionality

'''
'''


import os
import datetime
import shutil
import time
import uuid
import logging
import urlparse
import subprocess
import random

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


def main(ds):
    prepareDataset(ds)
    downloadCurrentUniprot(ds)
    splitUniprotIntoGenomes(ds)


def _getDatasetId(ds):
    return 'roundup_' + os.path.basename(ds)


def getGenomesDir(ds):
    return os.path.join(ds, 'genomes')


def getJobsDir(ds):
    return os.path.join(ds, 'jobs')

    
def getOrthologsDir(ds):
    return os.path.join(ds, 'orthologs')

    
def getSourcesDir(ds):
    return os.path.join(ds, 'sources')

    
def prepareDataset(ds):
    if os.path.exists(ds) and isDatasetPrepared(ds):
        print 'dataset already prepared. {}'.format(ds)
    os.makedirs(getGenomesDir(ds), 0770)
    os.makedirs(getOrthologsDir(ds), 0770)
    os.makedirs(getJobsDir(ds), 0770)
    os.makedirs(getSourcesDir(ds), 0770)
    markDatasetPrepared(ds)
    

def getPairs(ds):
    return roundup_common.getPairs(getGenomes(ds))


def getGenomes(ds, refreshCache=False):
    '''
    returns genomes in the dataset.  caches genomes in genomes.txt if they have not already been cached, b/c the isilon is wicked slow at listing dirs.
    '''
    path = os.path.join(ds, 'genomes.txt')
    if refreshCache or not os.path.exists(path):
        genomes = os.listdir(getGenomesDir())
        with open(path, 'w') as fh:
            for genome in genomes:
                fh.write('{}\n'.format(genome))
    else:
        genomes = []
        with open(path) as fh:
            for line in fh:
                if line.strip():
                    genomes.append(line.strip())
    return genomes

    
def getGenomesAndPaths(ds):
    '''
    returns: a dict mapping every genome in the dataset to its genomePath.
    '''
    genomesAndPaths = {}
    genomesDir = getGenomesDir(ds)
    for genome in getGenomes(ds):
        genomesAndPaths[genome] = os.path.join(genomesDir, genome)
    return genomesAndPaths


def getGenomePath(genome, ds):
    '''
    a genomePath is a directory containing genome fasta files and blast indexes.
    '''
    return os.path.join(getGenomesDir(ds), genome)


def getGenomeFastaPath(genome, ds):
    return os.path.join(getGenomePath(genome, ds), genome+'.aa')


def getGenomeIndexPath(genome, ds):
    '''
    location of blast index files
    '''
    return os.path.join(getGenomePath(genome, ds), genome+'.aa')
    
    
def downloadCurrentUniprot(ds):
    '''
    Download uniprot files containing protein fasta sequences and associated meta data (gene names, go annotations, dbxrefs, etc.)
    '''
    print 'downloadCurrentUniprot: {}'.format(ds)
    if isSourcesComplete(ds):
        print 'already complete'
        return
    
    sprotDatUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.dat.gz'
    sprotXmlUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.xml.gz'
    tremblDatUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.dat.gz'
    tremblXmlUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.xml.gz'
    idMappingUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping.dat.gz'
    idMappingSelectedUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping_selected.tab.gz'

    sourcesDir = getSourcesDir(ds)
    for url in [sprotDatUrl, sprotXmlUrl, tremblDatUrl, tremblXmlUrl, idMappingUrl, idMappingSelectedUrl]:
        dest = os.path.join(sourcesDir, os.path.basename(urlparse.urlparse(url).path))
        print 'downloading {} to {}...'.format(url, dest)
        if isFileComplete(dest):
            print '...skipping because already downloaded.'
            continue
        cmd = 'curl --remote-time --output '+dest+' '+url
        subprocess.check_call(cmd, shell=True)
        print
        # execute.run(cmd)
        markFileComplete(dest)
        print '...done.'
        time.sleep(5)
    markSourcesComplete(ds)
    print 'done downloading sources.'


def splitUniprotIntoGenomes(ds):
    '''
    create separate fasta files for each complete genome in the uniprot (sprot and trembl) data.
    '''
    print 'splitUniprotIntoGenomes: {}'.format(ds)
    if isGenomesComplete(ds):
        print 'already complete'
        return

    genomes = set()
    import Bio.SeqIO, cPickle, sys, os
    sourceFiles = [os.path.join(getSourcesDir(ds), f) for f in ('uniprot_sprot.dat', 'uniprot_trembl.dat')]
    for file in sourceFiles[:1]:
        print 'splitting {} into genomes'.format(file)
        for i, record in enumerate(Bio.SeqIO.parse(file, "swiss")):
            if record.annotations.has_key("keywords") and "Complete proteome" in record.annotations["keywords"]:
                genome = record.annotations["ncbi_taxid"][0]
                if genome not in genomes:
                    # first time a genome is seen, start a fresh genome file.
                    genomes.add(genome)
                    with open("foo", "w") as fh:
                        pass
                fasta = ">%s\n%s\n"%(record.id, record.seq)
                fastaPath = getGenomeFastaPath(genome, ds)
                with open(fastaPath, "a") as fh:
                    fh.write(fasta)
    # markSourcesComplete(ds)
    print 'done splitting sources.'
    

def getNewAndDonePairs(ds, oldDs):
    '''
    ds: current dataset, containing genomes
    oldDs: a previous dataset.
    Sort all pairs of genomes in the current dataset into todo and done pairs:
      new pairs need to be computed because each pair contains at least one genome that does not exist in or is different from the genomes of the old dataset.
      done pairs do not need to be computed because the genomes of each pair are the same as the old dataset, so the old orthologs are still valid.
    returns: the tuple, (newPairs, donePairs)
    '''
    raise Exception('untested')
    genomesAndPaths = getGenomesAndPaths(ds)
    oldGenomesAndPaths = getGenomesAndPaths(oldDs)
    # a new genome is one not in the old genomes or different from the old genome.
    newGenomes = set()
    for genome in genomesAndPaths:
        if genome not in oldGenomesAndPaths or not roundup_common.genomePathsEqual(genomesAndPaths[genome], oldGenomesAndPaths[genome]):
            newGenomes.add(genome)

    pairs = roundup_common.getPairs(genomesAndPaths.keys())
    newPairs = []
    oldPairs = []
    for pair in pairs:
        if pair[0] in newGenomes or pair[1] in newGenomes:
            newPairs.append(pair)
        else:
            oldPairs.append(pair)

    return (newPairs, oldPairs)


def moveOldOrthologs(ds, oldDs, pairs):
    '''
    pairs: the pairs that do not need to be computed because their genomes have not changed.
    Move orthologs files from the old dataset to the new dataset.
    '''
    raise Exception('unimplemented')


def prepareComputation(ds, oldDs=None, numJobs=10000):
    if oldDs:
        # get new and old pairs
        newPairs, oldPairs = getNewAndDonePairs(ds, oldDs)
        # get orthologs for old pairs and dump them into a orthologs file.
    else:
        newPairs = getPairs(ds)
        oldPairs = []
    # save the pairs to be computed and the pairs whose orthologs need to be moved.
    setNewPairs(ds, newPairs)
    setOldPairs(ds, oldPairs)
    # create up to N jobs for the pairs to be computed.
    # each job contain len(pairs)/N pairs, except if N does not divide len(pairs) evenly, some jobs get an extra pair.
    # permute the pairs so (on average) each job will have about the same running time.  Ideally job running time would be explictly balanced.
    random.shuffle(newPairs)
    numJobs = min(numJobs, len(newPairs))
    jobSize = len(newPairs) // numJobs
    numExtraPairs = len(newPairs) % numJobs
    start = 0
    end = jobSize
    for i in range(min(numJobs, len(pairs))):
        job = 'job_{}'.format(i)
        if i < numExtraPairs:
            end += 1
        jobPairs = newPairs[start:end]
        getJobDir(ds, job)
        os.makedirs(getJobDir(ds, job), 0770)
        setJobPairs(ds, job, jobPairs)


######
# JOBS
######

def getJobs(ds, refreshCache=False):
    '''
    returns jobs in the dataset.  caches jobs in jobs.txt if they have not already been cached, b/c the isilon is wicked slow at listing dirs.
    '''
    path = os.path.join(ds, 'jobs.txt')
    if refreshCache or not os.path.exists(path):
        jobs = os.listdir(getJobsDir())
        with open(path, 'w') as fh:
            for genome in jobs:
                fh.write('{}\n'.format(genome))
    else:
        jobs = []
        with open(path) as fh:
            for line in fh:
                if line.strip():
                    jobs.append(line.strip())
    return jobs


def getJobPairs(ds, job):
    readPairsFile(os.path.join(getJobDir(ds, job), 'job_pairs.txt'))


def setJobPairs(ds, job, pairs):
    writePairsFile(pairs, os.path.join(getJobDir(ds, job), 'job_pairs.txt'))


def getJobDir(ds, job):
    return os.path.join(getJobsDir(ds), job)


def getJobOrthologsPath(ds, job):
    return os.path.join(getOrthologsDir(ds), 'job_{}.orthologs.txt'.format(job))


def getJobOrthologs(ds, job):
    readOrthologsFile(getJobOrthologsPath(ds, job))


def removeJobOrthologs(ds, job):
    writeOrthologsFile([], getJobOrthologsPath(ds, job))


def addJobOrthologs(ds, job, orthologs):
    writeOrthologsFile(orthologs, getJobOrthologsPath(ds, job), mode='a')


def getComputeJobName(ds, job):
    return _getDatasetId(ds) + '_' + job


def isJobRunning(ds, job):
    '''
    checks if job is running on LSF.
    returns: True if job is on LSF and has not ended.  False otherwise.
    '''
    jobName = getComputeJobName(ds, job)
    infos = LSF.getJobInfosByJobName(jobName)
    statuses = [s for s in [info[LSF.STATUS] for info in infos] if not LSF.isEndedStatus(s)]
    if len(statuses) > 1:
        msg = 'isJobRunning: more than one non-ended LSF job for '+jobName+'\ndataset='+str(ds)+'\nstatuses='+str(statuses)
        raise Exception(msg)
    if statuses:
        return True
    else:
        return False

                                                        

###########
# ORTHOLOGS
###########

def orthologFileGen(path):
    '''
    useful for iterating through the orthologs in a large file
    '''
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith('#'):
                    yield line.split('\t')
    

def readOrthologsFile(path):
    return list(orthologFileGen(path))


def writeOrthologsFile(orthologs, path, mode='w'):
    with open(path, mode) as fh:
        for ortholog in orthologs:
            fh.write('{}\n'.format('\t'.join(ortholog)))


#################
# RUN COMPUTATION
#################


def computeJobs(ds):
    '''
    submit all incomplete and non-running jobs to lsf, so they can compute their respective pairs.
    '''
    jobs = getJobs(ds)
    util.writeToFile('computeJobs: ds={}\njobs={}\n'.format(ds, jobs), os.path.join(ds, makeUniqueDatetimeName(prefix='roundup_compute_history_')))
    for job in jobs:
        if isComplete(ds, 'job', job) or isJobRunning(ds, job):
            continue
        funcName = 'roundup_dataset.computeJob'
        keywords = {'ds': ds, 'job': job}
        # request that /scratch has at least ~10GB free space to avoid nodes where someone, not naming any names, has been a bad neighbor.
        lsfOptions = ['-R "scratch > 10000"', '-q '+LSF.LSF_LONG_QUEUE, roundup_common.ROUNDUP_LSF_OUTPUT_OPTION, '-J '+getComputeJobName(ds, job)]
        jobid = lsfdispatch.dispatch(funcName, keywords=keywords, lsfOptions=lsfOptions)
        msg = 'computeJobs(): running job on grid.  jobid={}, ds={}, job={}'.format(jobid, computeDir, pair)
        logging.log(roundup_common.ROUNDUP_LOG_LEVEL, msg)


def computeJob(ds, job):
    '''
    job: identifies which job this is so it knows which pairs to compute.
    computes orthologs for every pair in the job.  merges the orthologs into a single file and puts that file in the dataset orthologs dir.
    '''
    if isComplete(ds, 'job', job):
        return
    # a job is complete when all of its pairs are complete and it has written all the orthologs for all the pairs to a file.
    pairs = getJobPairs(ds, job)
    jobDir = getJobDir(ds, job)
    # compute orthologs for pairs
    for pair in pairs:
        orthologsPath = os.path.join(jobDir, '{}_{}.pair.orthologs.txt'.format(*pair))
        computePair(ds, pair, jobDir, orthologsPath)
    if not isComplete(ds, 'job_ologs_merge', job):
        # merge orthologs into a single file
        removeJobOrthologs(ds, job) # remove any pre-existing stuff.  could happen if a job fails while writing orthologs to the file.
        for pair in pairs:
            orthologsPath = os.path.join(jobDir, '{}_{}.pair.orthologs.txt'.format(*pair))
            orthologs = readOrthologsFile(orthologsPath)
            addJobOrthologs(ds, job, orthologs)
        markComplete(ds, 'job_ologs_merge', job)
    # delete the individual pair olog files
    for pair in pairs:
        orthologsPath = os.path.join(jobDir, '{}_{}.pair.orthologs.txt'.format(*pair))
        os.remove(orthologsPath)
    markComplete(ds, 'job', job)
    
            
def computePair(ds, pair, workingDir, orthologsPath):
    '''
    ds: the roundup dataset.
    pair: find orthologs for this pair of genomes.
    workingDir: where to save blast hits and orthologs as they get completed.
    orthologsPath: where to write the orthologs.
    precompute blast hits for pair.
    compute orthologs for pair.
    write orthologs to a file and clean up other files.
    '''
    # a pair is complete when it has written its orthologs to a file and cleaned up its other data files.
    if isComplete(ds, 'pair', pair):
        return
    pairStartTime = time.time()
    queryGenome, subjectGenome = pair
    queryGenomePath = getGenomePath(queryGenome, ds)
    subjectGenomePath = getGenomePath(subjectGenome, ds)
    queryFastaPath = getGenomeFastaPath(queryGenome, ds)
    subjectFastaPath = getGenomeFastaPath(subjectGenome, ds)
    queryIndexPath = getGenomeIndexPath(queryGenome, ds)
    subjectIndexPath = getGenomeIndexPath(subjectGenome, ds)
    forwardHitsPath = os.path.join(workingDir, '{}_{}.forward_hits.pickle'.format(*pair))
    reverseHitsPath = os.path.join(workingDir, '{}_{}.reverse_hits.pickle'.format(*pair))
    maxEvalue = max([float(evalue) for evalue in roundup_common.EVALUES]) # evalues are strings like '1e-5'
    divEvalues = list(roundup_common.genDivEvalueParams())    
    with nested.NestedTempDir(dir=roundup_common.LOCAL_DIR) as tmpDir:
        if not isComplete(ds, 'blast', queryGenome, subjectGenome):
            blast_results_db.computeBlastHits(queryFastaPath, subjectIndexPath, forwardHitsPath, maxEvalue, tmpDir, copyToWorking=roundup_common.ROUNDUP_LOCAL)
            markComplete(ds, 'blast', queryGenome, subjectGenome)

        if not isComplete(ds, 'blast', subjectGenome, queryGenome):
            blast_results_db.computeBlastHits(subjectFastaPath, queryIndexPath, reverseHitsPath, maxEvalue, tmpDir, copyToWorking=roundup_common.ROUNDUP_LOCAL)
            markComplete(ds, 'blast', subjectGenome, queryGenome)

        if not isComplete(ds, 'roundup', pair):
            divEvalueToOrthologs =  RSD.roundup(queryFastaPath, subjectFastaPath, divEvalues, forwardHitsPath, reverseHitsPath, tmpDir)
            # convert orthologs from a map to a table.
            orthologs = []
            for (div, evalue), partialOrthologs in divEvalueToOrthologs.items():
                for query, subject, distance in partialOrthologs:
                    orthologs.append((queryGenome, subjectGenome, div, evalue, query, subject, distance))
            writeOrthologsFile(orthologs, orthologsPath)
            markComplete(ds, 'roundup', pair)
    os.remove(forwardHitsPath)
    os.remove(reverseHitsPath)
    # complete pair computation
    pairEndTime = time.time()
    storePairStats(ds, pair, pairStartTime, pairEndTime)
    markComplete(ds, 'pair', pair)


###########
# COMPLETES
###########

def isComplete(ds, *key):
    return bool(int(getKVCacheValue(ds, str(key), 0)))

def markComplete(ds, *key):
    putKVCacheValue(ds, str(key), 1)

def isFileComplete(path):
    return os.path.exists(path+'.complete.txt')

def markFileComplete(path):
    util.writeToFile(path, path+'.complete.txt')

def isSourcesComplete(ds):
    return os.path.exists(os.path.join(ds, 'sources.complete.txt'))
    
def markSourcesComplete(ds):
    util.writeToFile('sources complete', os.path.join(ds, 'sources.complete.txt'))
    
def isGenomesComplete(ds):
    return os.path.exists(os.path.join(ds, 'genomes.complete.txt'))
    
def markGenomesComplete(ds):
    util.writeToFile('genomes complete', os.path.join(ds, 'genomes.complete.txt'))

def isDatasetPrepared(ds):
    return os.path.exists(os.path.join(ds, 'prepared.complete.txt'))
    
def markDatasetPrepared(ds):
    util.writeToFile('dataset prepared', os.path.join(ds, 'prepared.complete.txt'))

        
#######
# PAIRS
#######

def getNewPairs(ds):
    return readPairsFile(os.path.join(ds, 'new_pairs.txt'))


def setNewPairs(pairs, ds):
    writePairsFile(pairs, os.path.join(ds, 'new_pairs.txt'))


def getOldPairs(ds):
    return readPairsFile(os.path.join(ds, 'old_pairs.txt'))


def setOldPairs(pairs, ds):
    writePairsFile(pairs, os.path.join(ds, 'old_pairs.txt'))


def writePairsFile(pairs, path):
    with open(path, 'w') as fh:
        for qdb, sdb in pairs:
            fh.write('%s\t%s\n'%(qdb, sdb))
            

def readPairsFile(path):
    pairs = []
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith('#'):
                    pairs.append(line.split('\t'))
    return pairs


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

def getKVCacheValue(ds, key, default=None):
    return getKVCache(ds).get(key, default)

    
def putKVCacheValue(ds, key, value):
    getKVCache(ds).put(key, str(value))


KEY_VALUE_CACHE = {}
def getKVCache(ds):
    if KEY_VALUE_CACHE.has_key(ds):
        return KEY_VALUE_CACHE[ds]
    dsId = _getDatasetId(ds)
    # kv = kvstore.KVStore(util.ClosingFactoryCM(config.openDbConn), table='key_value_store_%s'%dsId, create=True)
    # HACK: give kvstore a conn object that never gets closed.
    kv = kvstore.KVStore(util.NoopCM(config.openDbConn()), table='key_value_store_%s'%dsId, create=True)
    KEY_VALUE_CACHE[ds] = kv
    return kv


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


def getComputationJobName(ds):
    return '_'.join(['roundup', getComputeIdFromComputeDir(ds)])


def getComputeIdFromComputeDir(ds):
    '''
    /groups/rodeo/compute/roundup/compute/20090327_115318_fede852da99f43f9b63a0ba6c0c58e59 -> 20090327_115318_fede852da99f43f9b63a0ba6c0c58e59
    '''
    return os.path.basename(ds)


##########
# METADATA
##########

def dumpComputationMetadata(ds, metadata):
    util.dumpObject(metadata, os.path.join(ds, 'computation.metadata.pickle'))
    

def loadComputationMetadata(ds):
    return util.loadObject(os.path.join(ds, 'computation.metadata.pickle'))
    

#################
# STATS FUNCTIONS
#################
    
def makeBlastStats(ds, qdb, sdb, startTime, endTime):
    stats = {'type': 'blast', 'qdb': qdb, 'sdb': sdb, 'startTime': startTime, 'endTime': endTime}
    return stats

    
def makeRoundupStats(ds, qdb, sdb, div, evalue, startTime, endTime):
    stats = {'type': 'roundup', 'qdb': qdb, 'sdb': sdb, 'div': div, 'evalue': evalue, 'startTime': startTime, 'endTime': endTime}
    return stats


def makePairStats(ds, pair, startTime, endTime):
    qdb, sdb = pair
    qdbFastaPath = getGenomeFastaPath(qdb, ds)
    sdbFastaPath = getGenomeFastaPath(sdb, ds)
    qdbBytes = os.path.getsize(qdbFastaPath)
    sdbBytes = os.path.getsize(sdbFastaPath)
    qdbSeqs = fasta.numSeqsInPath(qdbFastaPath)
    sdbSeqs = fasta.numSeqsInPath(sdbFastaPath)
    stats = {'type': 'pair', 'qdb': qdb, 'sdb': sdb, 'startTime': startTime, 'endTime': endTime,
             'qdbBytes': qdbBytes, 'sdbBytes': sdbBytes, 'qdbSeqs': qdbSeqs, 'sdbSeqs': sdbSeqs}
    return stats


########################
# DEPRECATED / UNUSED
########################

# last line - python emacs bug fix
 
