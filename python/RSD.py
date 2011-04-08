#!/usr/bin/env python
# THE RSD ALGORITHM
# original author: Dennis P. Wall -- Department of Biological Sciences, Stanford University.
# contributions by I-Hsien Wu and Todd F Deluca of the Computational Biology Initiative, Harvard Medical School
# the purpose of this program is to detect putative orthologues between two genomes.
# the algorithm is called the reciprocal smallest distance algorithm and works as follows:
#

# to run this program you need to have (downloaded to root and in addition to the latest version of python):

# 1. NCBI BLAST.  
# 2. paml3.13
# 3. clustalw_1.83
# see README FOR FULL DETAILS

import re
import os
import shutil
import subprocess
import logging
import time

import config
import nested
import fasta
import blast_results_db
import execute
import util


PAML_ERROR_MSG = 'paml_error'
FORWARD_DIRECTION = 0
REVERSE_DIRECTION = 1
# should correspond to $name_length in clustal2phylip.
# roundup fasta seq name lines should not exceed this length, including the '>' at the beginning of the line, I think. [td23]
ROUNDUP_SEQ_NAME_LENGTH = 22
CLUSTAL_INPUT_FILENAME = 'clustal_fasta.faa'
CLUSTAL_ALIGNMENT_FILENAME = 'clustal_fasta.aln'
DASHLEN_RE = re.compile('^(-*)(.*?)(-*)$')

DEBUG = util.getBoolFromEnv('ROUNDUP_RSD_DEBUG', False)


def pamlRunAll(path):
    return execute.run("cd %s/; echo '0' | codeml" %path)


def pamlGetDistance(path):
    filename = '%s/2AA.t'%path
    
    # adding a pause on the off-chance that the filesystem might be lagging a bit, causing the open() to fail below.
    # I think it is more likely that codeml in runPaml_all() is failing before writing the file.
    if not os.path.isfile(filename):
        import time
        time.sleep(0.5)

    with open(filename) as rst:
        get_rst = rst.readlines()
    os.unlink(filename)
        
    if not get_rst:
        raise Exception(PAML_ERROR_MSG, path)
        		
    str = ''
    for line in get_rst[1:]:
        cd1 = line.split()
        if not len(cd1) > 1:
            str += "%s "%(line.split('\n')[0])
            continue
        if len(cd1) > 1:
            str+="%s %s"%(cd1[0], cd1[1])

    dist = float(str.split()[2])
    return dist


def getIdsForFastaPath(fastaPath):
    '''
    fastaPath: path to a genome fasta file
    '''
    ids = []
    with open(fastaPath) as fh:
        for nameline, seq in fasta.readFastaIter(fh, ignoreParseError=True):
            ids.append(convertNamelineToId(nameline)) # e.g. >lcl|12345 becomes 12345
    return ids


def convertIdToNameline(seqId):
    return '>lcl|'+seqId


def convertNamelineToId(nameline):
    return nameline.replace('>lcl|', '')


def clustalToPhylip(alignment):
    '''
    optimized for roundup.  makes some assumptions about alignment to avoid using regular expressions.
    replaces clustal2phylip perl script, to increase conversion speed by not executing an external process.
    '''
    # print 'alignment', alignment
    START_STATE = 1
    PARSE_STATE = 2
    state = START_STATE
    seqIds = []
    seqIdToSeq = {}
    for line in alignment.splitlines():
        if state == START_STATE:
            if line.find('CLUSTAL') != -1:
                state = PARSE_STATE
            else:
                pass
        else: # state == PARSE_STATE:
            if line.find('Clustal Tree') != -1:
                break
            if not line or line[0] == ' ':
                continue
            splits = line.split()
            if len(splits) == 2:
                seqId = splits[0][:ROUNDUP_SEQ_NAME_LENGTH]
                if seqId not in seqIdToSeq:
                    seqIds.append(seqId)
                    seqIdToSeq[seqId] = ''
                seqIdToSeq[seqId] += splits[1]
    phylip = ''
    # all sequences must be the same length.
    phylip += '%s %s\n'%(len(seqIds), len(seqIdToSeq[seqIds[0]]))
    for seqId in seqIds:
        padding = ' '*(ROUNDUP_SEQ_NAME_LENGTH - len(seqId))
        phylip += '%s%s%s\n'%(seqId, padding, seqIdToSeq[seqId])
    return phylip


def runClustal(fasta, path):
	'''
	fasta: fasta formatted sequences to be aligned.
	path: working directory where fasta will be written and clustal will write output files.
        runs clustalw, doing i/o using named pipes, which is why clustal process is started before writing out fasta.
	Returns: alignment
        '''
	clustalFastaPath = os.path.join(path, CLUSTAL_INPUT_FILENAME)
	clustalAlignmentPath = os.path.join(path, CLUSTAL_ALIGNMENT_FILENAME)
	util.writeToFile(fasta, clustalFastaPath)
        try:
            execute.run('clustalw -infile=%s -outfile=%s'%(clustalFastaPath, clustalAlignmentPath))
        except Exception:
            logging.exception('runClustal Error:  clustalFastaPath data = %s'%open(clustalFastaPath).read())
            raise
	alignment = util.readFromFile(clustalAlignmentPath)
	return alignment


def dashlen_check(seq):
    '''
    Objective: calculate the density of gaps in a sequence at 5' and 3' ends --  caused by poor alignment or by diff length seqs
    Arguments: sequence
    Result: the number of bases to be cut from the subjects 5' and 3' ends, and the divergence of the trimmed seq.
    '''
    seq = seq.strip()
    # trim the dashes from the front and end
    (frontDashes, trimmedSeq, endDashes) = DASHLEN_RE.search(seq).groups()
    # logging.debug('dashlen_check: seq=%s'%seq)
    # all dashes -- do not trim anything
    if not trimmedSeq:
        return (0, 0)

    # ignore trims < 10.
    frontTrim = len(frontDashes)
    if frontTrim < 10:
        frontTrim = 0
    endTrim = len(endDashes)
    if endTrim < 10:
        endTrim = 0

    trimmedSeqDivergence = (trimmedSeq.count('-') / float(len(trimmedSeq)))
    return (frontTrim, endTrim, trimmedSeqDivergence)


def makeGetSeqForId(genomeFastaPath):
    '''
    genomeFastaPath: location of fasta file.  also location/name of blast formatted indexes of the fasta file.
    '''
    # suck fasta file into memory, converting it into a map from id to sequence
    # in memory dict performs much better than on-disk retrieval with xdget or fastacmd.
    # and genome fasta files do not take much space (on a modern computer).
    fastaMap = {}
    fh = open(genomeFastaPath)
    for (seqNameline, seq) in fasta.readFastaIter(fh, ignoreParseError=True):
        seqId = convertNamelineToId(seqNameline)
        fastaMap[seqId] = seq
    fh.close()
    def getSeqForIdInMemory(seqId):
        return fastaMap[seqId]
    return getSeqForIdInMemory
    

def makeGetHitsOnTheFly(genomeIndexPath, evalue, workingDir='.'):
    '''
    genomeIndexPath: location of blast formatted indexes.  usually same directory/name as genome fasta path
    returns: a function that returns that takes as input a sequence id and sequence and returns the blast hits
    workingDir: a directory in which to create, use, and delete temporary files and dirs.
    '''
    def getHitsOnTheFly(seqname, seq):
        with nested.NestedTempDir(dir=workingDir, nesting=0) as tmpDir:
            queryFastaPath = os.path.join(tmpDir, 'query.faa')
            util.writeToFile('{0}\n{1}\n'.format(convertIdToNameline(seqname), seq), queryFastaPath)
            hitsDb = blast_results_db.getBlastHits(queryFastaPath, genomeIndexPath, evalue, workingDir)
        return hitsDb.get(seqname)
    return getHitsOnTheFly


def makeGetSavedHits(filename):
    '''
    returns a function which can be used to get the hits
    from a file containing pre-computed blast results
    '''
    # in memory retrieval is faster than on-disk retrieval with bsddb, but this has a minor impact on overall roundup performance.
    hitsDb = blast_results_db.loadBlastHits(filename)
    def getHitsInMemory(seqname, seq):
        return hitsDb.get(seqname)
    return getHitsInMemory


def getGoodEvalueHits(seqName, seq, getHitsFunc, getSeqFunc, evalue):
    '''
    returns: a list of pairs of (seqname, sequence, evalue) that have an evalue below evalue
    '''
    goodhits = []
    
    hits = getHitsFunc(seqName, seq)
    
    # check for 3 or fewer blast hits below evalue threshold
    if hits:
        hitCount = 0
        for hit in hits:
            if hitCount >= config.MAX_HITS:
                break
            hitSeqName = blast_results_db.getHitName(hit)
            hitEvalue = blast_results_db.getHitEvalue(hit)
            if hitEvalue < evalue:
                hitCount += 1
                hitSeq = getSeqFunc(hitSeqName)
                goodhits.append((hitSeqName, hitSeq, hitEvalue))

    if DEBUG:
        for data in goodhits:
            print 'hit\t{0}\t{2}'.format(*data)
    return goodhits


def getDistanceForAlignedSeqPair(seqName, alignedSeq, hitSeqName, alignedHitSeq, workPath):

    # paranoid check: aligned and trimmed seqs need to be the same length.
    # if len(alignedSeq) != len(alignedHitSeq):
    #     raise Exception('getDistanceForAlignedSeqPairs: different lengths for seqs: '+str(((seqName, alignedSeq), (hitSeqName, alignedHitSeq))))

    dataFileName = 'datafile.seq'
    treeFileName = 'treefile.seq'
    outFileName = 'outfile.seq'
    dataFilePath = os.path.join(workPath, dataFileName)
    treeFilePath = os.path.join(workPath, treeFileName)
    outFilePath = os.path.join(workPath, outFileName)
    
    # heading is number of seqs and length of each seq (which all need to be the same len).
    heading = '2 %s\n'%len(alignedSeq)
    pamlData = heading + '%s\n%s\n'%(seqName, alignedSeq) + '%s\n%s\n'%(hitSeqName, alignedHitSeq)
    # logging.debug('pamlData=%s'%pamlData)
    util.writeToFile(pamlData, dataFilePath)
    
    # workPath is simply your folder that will contain codeml (Yang 2000), codeml.ctl (the codeml control file), and the jones.dat (Jones et. al, 1998)
    # write the codeml control file that will run codeml
    # run the codeml 
    
    try:
        # trying hardcoding codeml.ctl file to avoid writing it.
        pamlRunAll(workPath)
        distance = pamlGetDistance(workPath)
        if DEBUG:
            print 'dist\t{0}\t{1}'.format(hitSeqName, distance)
        return distance
    finally:
        for filePath in [dataFilePath, treeFilePath, outFilePath]:
            if os.path.exists(filePath):
                os.remove(filePath)
            

def getGoodDivergenceAlignedTrimmedSeqPair(seqName, seq, hitSeqName, hitSeq, workPath):
    '''
    aligns seq to hit.  trims aligned seq and hit seq.
    returns: pairs of pairs of name and aligned trimmed sequences for sequences in hits,
    and a predicate function that, given a divergence threshold, says if the divergence of the sequences exceeds the threshold.
    e.g. ((seqName, alignedTrimmedSeq), (hitSeqName, alignedTrimmedHitSeq), divergencePredicateFunc)
    '''
    # ALIGN SEQ and HIT
    # need to align the sequences so we'z can study the rate of evolution per site
    fasta = '>%s\n%s\n'%(seqName,seq)
    fasta += '>%s\n%s\n'%(hitSeqName,hitSeq)
    alignment = runClustal(fasta, workPath)
    
    # need to convert clustalw file format into a phylip readable format using this really fancy perl script.
    # this code is specific to phylip formatted matrix files
    # where the first line =  #taxa #characters
    # subsequent line = seqname seq
    output = clustalToPhylip(alignment)
    outputLines = output.split('\n')
    alignHeader = outputLines[0]
    (alignedNameAndSeq, alignedHitNameAndSeq) = [line.split() for line in outputLines[1:] if line]
    
    # CHECK FOR EXCESSIVE DIVERGENCE AND TRIMMING
    # find most diverged sequence
    # sort sequences by dash count.  why?
    divNameSeqs = []
    for name, seq in (alignedNameAndSeq, alignedHitNameAndSeq):
        dashCount = seq.count('-')
        div = dashCount / float(len(seq))
        g = (dashCount, div, name, seq)
        divNameSeqs.append(g)
    divNameSeqs.sort()

    if DEBUG:
        for data in divNameSeqs:
            if data[2] != seqName:
                print 'div\t{}\t{}'.format(data[2], data[1])
        
    # check for excessive divergence
    leastDivergedDashCount, leastDivergedDiv, leastDivergedName, leastDivergedSeq = divNameSeqs[0]
    # check for excessive divergence and generate dashtrim.
    mostDivergedDashCount, mostDivergedDiv, mostDivergedName, mostDivergedSeq = divNameSeqs[1]
    # dashtrim = dashlen_check(mostDivergedSeq, divergence)
    startTrim, endTrim, trimDivergence = dashlen_check(mostDivergedSeq)
    # logging.debug('dashtrim='+str(dashtrim))
    # trim and add seqs to output
    def divergencePredicate(divergenceThreshold):
        '''Why this logic?  Ask Dennis.  Function closed over local variables that returns whether or not the alignment of the sequences is too diverged.'''
        if leastDivergedSeq and leastDivergedDiv > divergenceThreshold:
            return True
        if (startTrim or endTrim) and trimDivergence >= divergenceThreshold:
            return True
        return False
            
    alignedTrimmedNameAndSeq, alignedTrimmedHitNameAndSeq = [(name, seq[startTrim:(len(seq)-endTrim)]) for name, seq in (alignedNameAndSeq, alignedHitNameAndSeq)]
    return alignedTrimmedNameAndSeq, alignedTrimmedHitNameAndSeq, divergencePredicate


def minimumDicts(dicts, key):
    '''
    dicts: list of dictionaries.
    key: a key present in every dict in dicts.
    returns: list of d in dicts, s.t. d[key] <= e[key] for every d, e in dicts.
    e.g.: [{'a':4, 'b':1}, {'a':5, 'b':0}, {'b': 0, 'a': 3}], 'b' -> [{'a':5, 'b':0} and {'b': 0, 'a': 3}] (not necessarily in that order)
    '''
    if not dicts:
        return []
    sortedDicts = sorted(dicts, key=lambda x: x[key])
    minValue = sortedDicts[0][key]
    return [d for d in sortedDicts if d[key] == minValue]


def roundupSome(querySeqIds, queryFastaPath, subjectFastaPath, div, evalue, outFile, workingDir='.'):
    '''
    querySeqIds: a list of sequence ids from query genome to find orthologs for.
    queryFastaPath: location and name of of fasta file and blast indexes of the query genome. e.g. /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa
    subjectFastaPath: location and name of of fasta file and blast indexes of the subject genome.
    workingDir: a directory in which to create, use, and delete temporary files and dirs.
    This computes blast hits on-the-fly, so it slower than roundup() for computing orthologs for full genomes.
    '''
    # get the sequence ids to find orthologs for.
    if querySeqIds is None:
        querySeqIds = getIdsForFastaPath(queryFastaPath)

    if DEBUG:
        print
        print 'query_genome\t'+os.path.basename(queryFastaPath)
        print 'subject_genome\t'+os.path.basename(subjectFastaPath)
    with nested.NestedTempDir(dir=workingDir, nesting=0) as tmpDir:
        divEvalues = [(div, evalue)]

        # make functions to look up a sequence from a sequence id.
        getQuerySeqFunc = makeGetSeqForId(queryFastaPath)
        getSubjectSeqFunc = makeGetSeqForId(subjectFastaPath)
        getForwardHits = makeGetHitsOnTheFly(subjectFastaPath, evalue, workingDir)
        getReverseHits = makeGetHitsOnTheFly(queryFastaPath, evalue, workingDir)
        
        # get orthologs for every query seq id and (div, evalue) combination
        divEvalueToOrthologs = roundupSubSub(querySeqIds, getQuerySeqFunc, getSubjectSeqFunc, divEvalues, getForwardHits, getReverseHits, tmpDir)

        # write orthologs to file
        orthologs = divEvalueToOrthologs[(div, evalue)]
        data = ''.join(['%s %s %s\n'%(subject, query, distance) for query, subject, distance in orthologs])
        util.writeToFile(data, outFile)


def roundupFull(queryFastaPath, subjectFastaPath, divEvalueAndOutfileList, forwardhits, reversehits, workingDir='.'):
    '''
    Compute RSD orthologs for all sequences in query genome and subject genome.
    forwardhits: file containing precomputed blast hits for query seqs blasted against subject db
    reversehits: file containing precomputed blast hits for subject seqs blasted against query db
    workingDir: creates, uses, and removes a directory under workingDir.  
    '''
    with nested.NestedTempDir(dir=workingDir, nesting=0) as tmpDir:
        getForwardHits = makeGetSavedHits(forwardhits)
        getReverseHits = makeGetSavedHits(reversehits)
        divEvalues = [(div, evalue) for div, evalue, outfile in divEvalueAndOutfileList]
        genomeSwapOptimization = util.getBoolFromEnv('ROUNDUP_GENOME_SWAP_OPTIMIZATION', True)
        divEvalueToOrthologs = roundupSub(queryFastaPath, subjectFastaPath, divEvalues, getForwardHits, getReverseHits, tmpDir, genomeSwapOptimization)
        for div, evalue, outFile in divEvalueAndOutfileList:
            orthologs = divEvalueToOrthologs[(div, evalue)]
            data = ''.join(['%s %s %s\n'%(subject, query, distance) for query, subject, distance in orthologs])
            util.writeToFile(data, outFile)


def roundup(queryFastaPath, subjectFastaPath, divEvalues, forwardHitsPath, reverseHitsPath, workingDir='.'):
    '''
    returns: a mapping from (div, evalue) pairs to lists of orthologs.
    '''    
    with nested.NestedTempDir(dir=workingDir, nesting=0) as tmpDir:
        getForwardHits = makeGetSavedHits(forwardHitsPath)
        getReverseHits = makeGetSavedHits(reverseHitsPath)
        genomeSwapOptimization = util.getBoolFromEnv('ROUNDUP_GENOME_SWAP_OPTIMIZATION', True)
        divEvalueToOrthologs = roundupSub(queryFastaPath, subjectFastaPath, divEvalues, getForwardHits, getReverseHits, tmpDir, genomeSwapOptimization)
        return divEvalueToOrthologs
    
        
def roundupSub(queryFastaPath, subjectFastaPath, divEvalues, getForwardHits, getReverseHits, workingDir, genomeSwapOptimization=True):
    '''
    queryFastaPath: fasta file path.
    subjectFastaPath: fasta file path.
    divEvalueAndOutfileList: list of (div, evalue, outfile) tuples.  the orthologs for the given div and evalue are written to the outfile path.
    getForwardHits: a function mapping a query seq id to a list of subject genome blast hits
    getReverseHits: a function mapping a subject seq id to a list of query genome blast hits
    workingDir: a directory to work in -- creating, writing, reading, and deleting temp files and dirs.
    genomeSwapOptimization: if True and if the subject fasta is has fewer sequences than the query fasta, the genomes are swapped, orthologs computed,
      and the results are unswapped.
    returns: a mapping from (div, evalue) pairs to lists of orthologs.
    '''
    # internally reverse query and subject if subject has fewer sequences than query
    # roundup time complexity is roughly linear in the number of sequences in the query genome.
    if genomeSwapOptimization and fasta.numSeqsInFastaDb(subjectFastaPath) < fasta.numSeqsInFastaDb(queryFastaPath):
        # print 'roundup(): subject genome has fewer sequences than query genome.  internally swapping query and subject to improve speed.'
        isSwapped = True
        # swap query and subject, forward and reverse
        queryFastaPath, subjectFastaPath = subjectFastaPath, queryFastaPath
        getForwardHits, getReverseHits = getReverseHits, getForwardHits
    else:
        isSwapped = False

    # make functions to look up a sequence from a sequence id.
    getQuerySeqFunc = makeGetSeqForId(queryFastaPath)
    getSubjectSeqFunc = makeGetSeqForId(subjectFastaPath)

    # convert div and evalue from strings to floats.
    # divEvalueAndOutfileList = [(float(div), float(evalue), outfile) for div, evalue, outfile in divEvalueAndOutfileList]
    # divEvalues = [(div, evalue) for div, evalue, outfile in divEvalueAndOutfileList]

    querySeqIds = getIdsForFastaPath(queryFastaPath)
    # get orthologs for every query seq id and (div, evalue) combination
    divEvalueToOrthologs = roundupSubSub(querySeqIds, getQuerySeqFunc, getSubjectSeqFunc, divEvalues, getForwardHits, getReverseHits, workingDir)

    # if swapped query and subject genome, need to swap back the ids in orthologs before returning them.
    if isSwapped:
        swappedDivEvalueToOrthologs = divEvalueToOrthologs
        divEvalueToOrthologs = {}
        for divEvalue, swappedOrthologs in swappedDivEvalueToOrthologs.items():
            orthologs = [(query, subject, distance) for subject, query, distance in swappedOrthologs]
            divEvalueToOrthologs[divEvalue] = orthologs

    return divEvalueToOrthologs

    
def roundupSubSub(querySeqIds, getQuerySeqFunc, getSubjectSeqFunc, divEvalues, getForwardHits, getReverseHits, workingDir):
    '''
    querySeqIds: a list of sequence ids from query genome.  Only orthologs for these ids are searched for.
    getQuerySeqFunc: a function that takes a seq id and returns the matching sequence from the query genome.
    getSubjectSeqFunc: a function that takes a seq id and returns the matching sequence from the subject genome.
    divEvalues: a list of (div, evalue) pairs which are thresholds for finding orthologs.  All pairs are searched simultaneously.
    getForwardHits: a function that takes a query seq id and a query seq and returns the blast hits in the subject genome.
    getReverseHits: a function that takes a subject seq id and a subject seq and returns the blast hits in the query genome.
    find orthologs for every sequence in querySeqIds and every (div, evalue) combination.
    return: a mapping from (div, evalue) pairs to lists of orthologs.
    '''
    # Note: the divs and evalues in divEvalues are strings which need to be converted to floats at the appropriate times below.
    
    # copy config files to working dir
    shutil.copy(config.MATRIX_PATH, workingDir)
    shutil.copy(config.CODEML_CONTROL_PATH, workingDir)

    divEvalueToOrthologs = dict(((div, evalue), list()) for div, evalue in divEvalues)
    maxEvalue = max(float(evalue) for div, evalue in divEvalues)
    maxDiv = max(float(div) for div, evalue in divEvalues)

    # get ortholog(s) for each query sequence
    for queryName in querySeqIds:
        if DEBUG:
            print
            print 'forward\t{0}'.format(queryName)
        querySeq = getQuerySeqFunc(queryName)
        # get forward hits, evalues, alignments, divergences, and distances that meet the loosest standards of all the divs and evalues.
        # get forward hits and evalues, filtered by max evalue
        nameSeqEvalueOfForwardHits = getGoodEvalueHits(queryName, querySeq, getForwardHits, getSubjectSeqFunc, maxEvalue)
        hitDataList = [{'hitName': hitName, 'hitSeq': hitSeq, 'hitEvalue': hitEvalue} for hitName, hitSeq, hitEvalue in nameSeqEvalueOfForwardHits]
        # get alignments and divergences
        for hitData in hitDataList:
            (queryName, alignedQuerySeq), (hitName, alignedHitSeq), tooDivergedPred = getGoodDivergenceAlignedTrimmedSeqPair(queryName, querySeq, hitData['hitName'], hitData['hitSeq'], workingDir)
            hitData['alignedQuerySeq'] = alignedQuerySeq
            hitData['alignedHitSeq'] = alignedHitSeq
            hitData['tooDivergedPred'] = tooDivergedPred
        # filter by max divergence.
        hitDataList = [hitData for hitData in hitDataList if not hitData['tooDivergedPred'](maxDiv)]
        # get distances of remaining hits, discarding hits for which paml generates no rst data.
        distancesHitDataList = []
        for hitData in hitDataList:
            try:
                hitData['distance'] = getDistanceForAlignedSeqPair(queryName, hitData['alignedQuerySeq'], hitData['hitName'], hitData['alignedHitSeq'], workingDir)
                distancesHitDataList.append(hitData)
            except Exception as e:
                if e.args and e.args[0] == PAML_ERROR_MSG:
                    continue
                else:
                    raise
                
        # filter hits by specific div and evalue combinations.
        divEvalueToMinimumDistanceHitDatas = {}
        minimumHitNameToDivEvalues = {}
        minimumHitNameToHitData = {}
        for divEvalue in divEvalues:
            div, evalue = divEvalue
            # collect hit datas that pass thresholds.
            goodHitDatas = []
            for hitData in distancesHitDataList:
                if hitData['hitEvalue'] < float(evalue) and not hitData['tooDivergedPred'](float(div)):
                    goodHitDatas.append(hitData)
            # get the minimum hit or hits.
            minimumHitDatas = minimumDicts(goodHitDatas, 'distance')
            divEvalueToMinimumDistanceHitDatas[divEvalue] = minimumHitDatas
            for hitData in minimumHitDatas:
                minimumHitNameToDivEvalues.setdefault(hitData['hitName'], []).append(divEvalue)
                minimumHitNameToHitData[hitData['hitName']] = hitData # possibly redundant, since if two divEvalues have same minimum hit, it gets inserted into dict twice.  
        
        # get reverese hits that meet the loosest standards of the divs and evalues associated with that minimum distance hit.
        # performance note: wasteful or necessary to realign and compute distance between minimum hit and query seq?
        for hitName in minimumHitNameToHitData:
            if DEBUG:
                print 'reverse\t{0}'.format(hitName)
            hitData = minimumHitNameToHitData[hitName]
            hitSeq = hitData['hitSeq']
            # since minimum hit might not be associated with all divs and evalues, need to find the loosest div and evalue associated with this minimum hit.
            maxHitEvalue = max(float(evalue) for div, evalue in minimumHitNameToDivEvalues[hitName])
            maxHitDiv = max(float(div) for div, evalue in minimumHitNameToDivEvalues[hitName])
            # get reverse hits and evalues, filtered by max evalue
            nameSeqEvalueOfReverseHits = getGoodEvalueHits(hitName, hitSeq, getReverseHits, getQuerySeqFunc, maxHitEvalue)
            revHitDataList = [{'revHitName': revHitName, 'revHitSeq': revHitSeq, 'revHitEvalue': revHitEvalue} for revHitName, revHitSeq, revHitEvalue in nameSeqEvalueOfReverseHits]
            # if the query is not in the reverese hits, there is no way we can find an ortholog
            if queryName not in [revHitData['revHitName'] for revHitData in revHitDataList]:
                continue
            for revHitData in revHitDataList:
                values = getGoodDivergenceAlignedTrimmedSeqPair(hitName, hitSeq, revHitData['revHitName'], revHitData['revHitSeq'], workingDir)
                (hitName, alignedHitSeq), (revHitName, alignedRevHitSeq), tooDivergedPred = values
                revHitData['alignedHitSeq'] = alignedHitSeq
                revHitData['alignedRevHitSeq'] = alignedRevHitSeq
                revHitData['tooDivergedPred'] = tooDivergedPred
            # filter by max divergence.
            revHitDataList = [revHitData for revHitData in revHitDataList if not revHitData['tooDivergedPred'](maxHitDiv)]
            # if the query is not in the reverese hits, there is no way we can find an ortholog
            if queryName not in [revHitData['revHitName'] for revHitData in revHitDataList]:
                continue
            # get distances of remaining reverse hits, discarding reverse hits for which paml generates no rst data.
            distancesRevHitDataList = []
            for revHitData in revHitDataList:
                try:
                    revHitData['distance'] = getDistanceForAlignedSeqPair(hitName, revHitData['alignedHitSeq'], revHitData['revHitName'], revHitData['alignedRevHitSeq'], workingDir)
                    distancesRevHitDataList.append(revHitData)
                except Exception as e:
                    if e.args and e.args[0] == PAML_ERROR_MSG:
                        continue
                    else:
                        raise


            # if passes div and evalue thresholds of the minimum hit and minimum reverse hit == query, write ortholog.
            # filter hits by specific div and evalue combinations.
            for divEvalue in minimumHitNameToDivEvalues[hitName]:
                div, evalue = divEvalue
                # collect hit datas that pass thresholds.
                goodRevHitDatas = []
                for revHitData in distancesRevHitDataList:
                    if revHitData['revHitEvalue'] < float(evalue) and not revHitData['tooDivergedPred'](float(div)):
                        goodRevHitDatas.append(revHitData)
                # get the minimum hit or hits.
                minimumRevHitDatas = minimumDicts(goodRevHitDatas, 'distance')
                if queryName in [revHitData['revHitName'] for revHitData in minimumRevHitDatas]:
                    divEvalueToOrthologs[divEvalue].append((queryName, hitName, hitData['distance']))
                    if DEBUG:
                        print 'ortholog\t{0}\t{1}\t{2}'.format(queryName, hitName, hitData['distance'])

    return divEvalueToOrthologs


if __name__ == '__main__':
    pass

    
#################
# DEPRECATED CODE
#################

      
# do not cross this line...or else.
