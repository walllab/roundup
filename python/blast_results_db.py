#!/usr/bin/env python

'''
Use to precompute blasting of genomes for later use by RSD algorithm
'''

import os
import shutil
import logging

import config
import util
import execute
import nested
import roundup_common


def findSeqIdWithFasta(fasta, genome):
    ''' return first hit '''
    subjectIndexPath = roundup_common.fastaFileForDbPath(roundup_common.makeDbPath(genome))
    try:
        path = nested.makeTempPath()
        util.writeToFile(fasta, path)
        cmd = 'blastp -outfmt 6 -query %s -db %s'%(path, subjectIndexPath)
        results = execute.run(cmd)
    finally:
        os.remove(path)        
    hitName = None
    for line in results.splitlines():
        splits = line.split()
        hitName = splits[1] # lcl| is already removed.  go figure.  that is just how ncbi does it.
        break
    return hitName


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


def getBlastHits(queryFastaPath, subjectIndexPath, evalue, workingDir='.', limitHits=roundup_common.MAX_GOOD_EVALUE_HITS):
    '''
    queryFastaPath: location of fasta file of query sequences
    subjectIndexPath: location and name of blast-formatted indexes.
    workingDir: creates, uses, and removes a directory under workingDir.  
    blasts every sequence in query agaist subject, adding hits that are better than evalue to a list stored in a dict keyed on the query id.
    '''
    with nested.NestedTempDir(dir=workingDir, nesting=0) as tmpDir:
        blastResultsPath = os.path.join(tmpDir, 'blast_results')
        # blast query vs subject, using /opt/blast-2.2.22/bin/blastp
        cmd = 'blastp -outfmt 6 -evalue %s -query %s -db %s -out %s'%(evalue, queryFastaPath, subjectIndexPath, blastResultsPath)
        execute.run(cmd)
        # parse results
        hitsMap = parseResults(blastResultsPath, limitHits)
    return hitsMap


def computeBlastHits(queryFastaPath, subjectIndexPath, outPath, evalue, workingDir='.', limitHits=roundup_common.MAX_GOOD_EVALUE_HITS):
    '''
    queryFastaPath: location of fasta file of query sequences
    subjectIndexPath: location and name of blast-formatted indexes.
    outPath: location of file where blast hits are saved.
    workingDir: creates, uses, and removes a directory under workingDir.  
    blasts every sequence in query agaist subject, adding hits that are better than evalue to a list stored in a dict keyed on the query id.
    Persists hits dict to outPath.
    '''
    hitsMap = getBlastHits(queryFastaPath, subjectIndexPath, evalue, workingDir, limitHits)
    util.dumpObject(hitsMap, outPath)


def parseResults(blastResultsPath, limitHits=roundup_common.MAX_GOOD_EVALUE_HITS):
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
        # we only store the top MAX_GOOD_EVALUE_HITS hits.
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

