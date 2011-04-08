#!/usr/bin/env python

'''
Use to precompute blasting of genomes for later use by RSD algorithm
'''

import os
import shutil
import logging
import glob

import config
import util
import execute
import nested


def getHitName(hit):
    return hit[0]


def getHitEvalue(hit):
    return hit[1]


def loadBlastHits(path):
    '''
    path: location of stored blast hits computed by computeBlastHits()
    returns: mapping object from query id to hits.  used to be a bsddb, now is a dict.
    '''
    return util.loadObject(path)


def _runBlast(**keywords):
    ''' helper function for running ncbi blast with a variety of options.'''
    cmd = 'blastp '
    options = ['outfmt', 'evalue', 'query', 'db', 'out']
    cmd += ' '.join(['-'+option+' '+keywords[option] for option in options if keywords.has_key(option)])
    return execute.run(cmd, stdin=keywords.get('stdin'))


def getBlastHits(queryFastaPath, subjectIndexPath, evalue, workingDir='.', limitHits=config.MAX_HITS, copyToWorking=False):
    '''
    queryFastaPath: location of fasta file of query sequences
    subjectIndexPath: location and name of blast-formatted indexes.
    workingDir: creates, uses, and removes a directory under workingDir.
    copyToWorking: if True, copy query fasta path and subject index files to within the working directory and use the copies to blast.
      useful for performance if the working directory is local and the files are on a network.
    blasts every sequence in query agaist subject, adding hits that are better than evalue to a list stored in a dict keyed on the query id.
    '''
    # work in a nested tmp dir to avoid junking up the working dir.
    with nested.NestedTempDir(dir=workingDir, nesting=0) as tmpDir:
        if copyToWorking:
            localFastaPath = os.path.join(tmpDir, 'query.fa')
            shutil.copyfile(queryFastaPath, localFastaPath)
            localIndexDir = os.path.join(tmpDir, 'local_blast')
            os.makedirs(localIndexDir, 0770)
            localIndexPath = os.path.join(localIndexDir, os.path.basename(subjectIndexPath))
            for path in glob.glob(subjectIndexPath+'*'):
                if os.path.isfile:
                    shutil.copy(path, localIndexDir)
            queryFastaPath = localFastaPath
            subjectIndexPath = localIndexPath
        blastResultsPath = os.path.join(tmpDir, 'blast_results')
        # blast query vs subject, using /opt/blast-2.2.22/bin/blastp
        cmd = 'blastp -outfmt 6 -evalue %s -query %s -db %s -out %s'%(evalue, queryFastaPath, subjectIndexPath, blastResultsPath)
        execute.run(cmd)
        # parse results
        hitsMap = parseResults(blastResultsPath, limitHits)
    return hitsMap


def computeBlastHits(queryFastaPath, subjectIndexPath, outPath, evalue, workingDir='.', limitHits=config.MAX_HITS, copyToWorking=False):
    '''
    queryFastaPath: location of fasta file of query sequences
    subjectIndexPath: location and name of blast-formatted indexes.
    outPath: location of file where blast hits are saved.
    workingDir: creates, uses, and removes a directory under workingDir.  
    copyToWorking: if True, copy query fasta path and subject index files to within the working directory and use the copies to blast.
      useful for performance if the working directory is local and the files are on a network.
    blasts every sequence in query agaist subject, adding hits that are better than evalue to a list stored in a dict keyed on the query id.
    Persists hits dict to outPath.
    '''
    hitsMap = getBlastHits(queryFastaPath, subjectIndexPath, evalue, workingDir, limitHits)
    util.dumpObject(hitsMap, outPath)


def parseResults(blastResultsPath, limitHits=config.MAX_HITS):
    # parse tabular results into hits.  thank you, ncbi, for creating results this easy to parse.
    hitsMap = {}
    hitsCountMap = {}
    prevSeqName = None
    prevHitName = None
    fh = open(blastResultsPath)
    for line in fh:
        splits = line.split()
        seqName = splits[0][4:] # remove 'lcl|'
        hitName = splits[1] # lcl| is already removed.  go figure.  that is just how ncbi does it.
        hitEvalue = float(splits[10])
        # results table reports multiple "alignments" per "hit" in ascending order by evalue
        # we only store the top hits.
        if prevSeqName != seqName or prevHitName != hitName:
            prevSeqName = seqName
            prevHitName = hitName
            if seqName not in hitsCountMap:
                hitsCountMap[seqName] = 0
                hitsMap[seqName] = []
            if not limitHits or hitsCountMap[seqName] < limitHits:
                hitsCountMap[seqName] += 1                
                hitsMap[seqName].append((hitName, hitEvalue))
    fh.close()
    return hitsMap
    
    
# if called as a script
if __name__ == '__main__':
    pass


# last line emacs python mode bug fix

