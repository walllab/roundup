#!/usr/bin/env python

'''
Dataset
Genomes
Pairs
Jobs
Sources
Orthologs
Database
Metadata
Completes
'''

# test getGenomes()
# test splitting source files
# test preparing computation.  are the jobs and pair files created?
#   are the new_pairs.txt and old_pairs.txt created?
# test blast_results_db copyToWorking functionality

'''
# Fiddling with completes and dataset state to get completed stuff to run again.
# remove existing orthologs
rm -rf /groups/cbi/td23/roundup_uniprot/test_dataset/orthologs/*
# remove existing jobs
rm -rf /groups/cbi/td23/roundup_uniprot/test_dataset/jobs/*
# drop completes table so jobs will run
echo 'drop table key_value_store_roundup_ds_test_dataset' | mysql devroundup
# remove prepare computation complete too
emacs /groups/cbi/td23/roundup_uniprot/test_dataset/steps.complete.txt
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
import gzip
import json

import config
import blast_results_db
import fasta
import LSF
import nested
import kvstore
import roundup_common
import util
import roundup_db
import lsfdispatch
import RSD


MIN_GENOME_SIZE = 200 # ignore genomes with fewer sequences


def main(ds):
    prepareDataset(ds)
    downloadCurrentUniprot(ds)
    splitUniprotIntoGenomes(ds)
    filterAndFormatGenomes(ds)
    prepareComputation(ds)


#######################
# MAIN DATASET PIPELINE
#######################

def prepareDataset(ds):
    if os.path.exists(ds) and isStepComplete(ds, 'prepare dataset'):
        print 'dataset already prepared. {}'.format(ds)
        return
    for path in (getGenomesDir(ds), getOrthologsDir(ds), getJobsDir(ds), getSourcesDir(ds)):
        if not os.path.exists(path):
            os.makedirs(path, 0770)
    markStepComplete(ds, 'prepare dataset')
    

def downloadCurrentUniprot(ds):
    '''
    Download uniprot files containing protein fasta sequences and associated meta data (gene names, go annotations, dbxrefs, etc.)
    '''
    print 'downloadCurrentUniprot: {}'.format(ds)
    if isStepComplete(ds, 'download current uniprot'):
        print 'already complete'
        return
    
    sprotDatUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.dat.gz'
    sprotFastaUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.fasta.gz'
    tremblDatUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.dat.gz'
    tremblFastaUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.fasta.gz'
    idMappingUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping.dat.gz'
    idMappingSelectedUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping_selected.tab.gz'
    releaseNotesUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/relnotes.txt'
    
    sourcesDir = getSourcesDir(ds)
    urls = [sprotDatUrl, sprotFastaUrl, tremblDatUrl, tremblFastaUrl, idMappingUrl, idMappingSelectedUrl, releaseNotesUrl]
    for url in urls:
        dest = os.path.join(sourcesDir, os.path.basename(urlparse.urlparse(url).path))
        print 'downloading {} to {}...'.format(url, dest)
        if isStepComplete(ds, 'download', url):
            print '...skipping because already downloaded.'
            continue
        cmd = 'curl --remote-time --output '+dest+' '+url
        subprocess.check_call(cmd, shell=True)
        print
        markStepComplete(ds, 'download', url)
        print '...done.'
        time.sleep(5)
    updateMetadata(ds, {'sources': {'download_time': str(datatime.datetime.now), 'urls': urls}})
    markStepComplete(ds, 'download current uniprot')
    print 'done downloading sources.'


def splitUniprotIntoGenomes(ds):
    '''
    create separate fasta files for each complete genome in the uniprot (sprot and trembl) data.
    '''
    print 'splitUniprotIntoGenomes: {}'.format(ds)
    if isStepComplete(ds, 'split sources into fasta genomes'):
        print 'already complete'
        return

    genomes = set()
    import Bio.SeqIO, cPickle, sys, os
    seqToGenome = {}
    dats = [os.path.join(getSourcesDir(ds), 'uniprot_sprot.dat.gz'), os.path.join(getSourcesDir(ds), 'uniprot_trembl.dat.gz')]
    fastas = [os.path.join(getSourcesDir(ds), 'uniprot_sprot.fasta.gz'), os.path.join(getSourcesDir(ds), 'uniprot_trembl.fasta.gz')]
    # dats = [os.path.join(getSourcesDir(ds), 'test_uniprot_sprot.dat.gz')]
    # fastas = [os.path.join(getSourcesDir(ds), 'test_uniprot_sprot.fasta.gz')]

    # gather which sequences belong to complete genomes.
    # the dats have all the info needed to make fasta files, but I am lazy and the namelines in the uniprot fasta files are nice.
    for path in dats:
        print 'gathering ids in {}'.format(path)
        for i, record in enumerate(Bio.SeqIO.parse(gzip.open(path), "swiss")):
            if i % 1e4 == 0: print i
            if record.annotations.has_key("keywords") and "Complete proteome" in record.annotations["keywords"]:
                seqToGenome[record.id] = record.annotations["ncbi_taxid"][0]
    # create individual fasta files for those sequences, one for each complete genome.
    for path in fastas:
        print 'splitting {} into genomes'.format(path)
        with gzip.open(path) as fh:
            for i, (nameline, seq) in enumerate(fasta.readFastaIter(fh)): # , ignoreParseError=True):
                if i % 1e4 == 0: print i
                seqId = fasta.idFromName(nameline)
                if seqId in seqToGenome:
                    genome = seqToGenome[seqId]
                    if genome not in genomes:
                        print 'new genome', genome
                        genomes.add(genome)
                        genomePath = getGenomePath(ds, genome)
                        if os.path.exists(genomePath):
                            shutil.rmtree(genomePath)
                        os.makedirs(genomePath, 0770)
                    fastaPath = getGenomeFastaPath(ds, genome)
                    with open(fastaPath, "a") as fh:
                        fh.write('{}\n{}'.format(nameline, fasta.prettySeq(seq)))
    markStepComplete(ds, 'split sources into fasta genomes')


def extractGeneIdsAndGoTerms(ds):
    '''
    ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/README
    2) idmapping_selected.tab
    We also provide this tab-delimited table which includes
    the following mappings delimited by tab:

        1. UniProtKB-AC
        2. UniProtKB-ID
        3. GeneID (EntrezGene)
        4. RefSeq
        5. GI
        6. PDB
        7. GO
        8. IPI
        9. UniRef100
        10. UniRef90
        11. UniRef50
        12. UniParc
        13. PIR
        14. NCBI-taxon
        15. MIM
        16. UniGene
        17. PubMed
        18. EMBL
        19. EMBL-CDS
        20. Ensembl
        21. Ensembl_TRS
        22. Ensembl_PRO
        23. Additional PubMed
    Writes two dicts to files, one mapping gene to go terms, the other mapping gene to ncbi gene id.
    '''
    geneToGoTerms = {}
    geneToGeneId = {}
    with gzip.open(os.path.join(getSourcesDir(ds), 'idmapping_selected.tab.gz')) as fh:
        for i, line in enumerate(fh):
            if i % 1000 == 0: print i
            seqId, b, geneId, d, e, f, goTerms, etc = line.split('\t', 7)
            goTerms = goTerms.split('; ')
            # print line
            # print (seqId, b, geneId, d, e, f, goTerms)
            geneToGoTerms[seqId] = goTerms
            geneToGeneId[seqId] = geneId
    with open(os.path.join(ds, 'gene_to_geneid.json'), 'w') as fh:
        json.dump(geneToGeneId, fh)
    with open(os.path.join(ds, 'gene_to_go_terms.json'), 'w') as fh:
        json.dump(geneToGoTerms, fh)
            

    
def extractGenomeAndGeneNames(ds):
    '''
    parse from the namelines the uniprot fasta files the gene name, genome/organism name, and genome/organism abbreviation.
    The organism name and abbreviation must be present in every nameline.  The gene name is optional.
    The org name and abbr must be the same in every nameline (for the same genome).
    The must exactly one nameline per sequence.
    example nameline: >sp|P38398|BRCA1_HUMAN Breast cancer type 1 susceptibility protein OS=Homo sapiens GN=BRCA1 PE=1 SV=2
    gene name: BRCA1, organism abbr: HUMAN, organism: Homo sapiens
    '''
    genomeToName = {}
    genomeToAbbr = {}
    geneToName = {}
    geneToDesc = {}
    
    # EXCEPTIONS to the exactly one name for a genome rule, found in UniProtKB release 2011_04.
    # taxonid | 2nd name found | 1st name found
    # 246196 | Mycobacterium smegmatis (strain ATCC 700084 / mc(2)155) | Mycobacterium smegmatis
    # 321332 | Synechococcus sp. (strain JA-2-3B'a(2-13)) | Synechococcus sp.
    # 771870 | Sordaria macrospora (strain ATCC MYA-333 / DSM 997 / K(L3346) / K-hell) | Sordaria macrospora
    # 290318 | Prosthecochloris vibrioformis (strain DSM 265) | Prosthecochloris vibrioformis (strain DSM 265) (strain DSM 265)
    # 710128 | Mycoplasma gallisepticum (strain R(high / passage 156)) | Mycoplasma gallisepticum
    # 375286 | Janthinobacterium sp. (strain Marseille) (Minibacterium massiliensis) | Janthinobacterium sp. (strain Marseille)
    # since the sprot/trembl data has genomes that have different names in sprot and trembl (see exceptions listed above),
    # ignore these bad genomes.
    badGenomes = set(['246196', '321332', '771870', '290318', '710128', '375286'])
    
    for i, genome in enumerate(getGenomes(ds)):
        path = getGenomeFastaPath(ds, genome)
        print '{}: extracting from {}'.format(i, path)
        with open(path) as fh:
            for nameline, seq in fasta.readFastaIter(fh):
                nameline = nameline.strip()

                # split apart nameline into seqId, genomeAbbr, genomeName, and geneName.
                # example: >sp|P38398|BRCA1_HUMAN Breast cancer type 1 susceptibility protein OS=Homo sapiens GN=BRCA1 PE=1 SV=2
                # sometimes no gene name: >sp|P38398|BRCA1_HUMAN Breast cancer type 1 susceptibility protein OS=Homo sapiens PE=1 SV=2
                try:
                    idAndAbbr, descOrgGNEtc = nameline.split(None, 1)
                    etc, seqId, almostAbbr = idAndAbbr.split('|')
                    etc, genomeAbbr = almostAbbr.rsplit('_', 1)
                    geneDesc, orgGNEtc = (s.strip() for s in descOrgGNEtc.split('OS=', 1))
                    orgGN, etc = orgGNEtc.split('PE=', 1)
                    if orgGN.find('GN=') == -1:
                        genomeName, geneName = (s.strip() for s in (orgGN, ''))
                    else:
                        genomeName, geneName = (s.strip() for s in orgGN.split('GN=', 1))
                    # print nameline
                    # print (seqId, genomeAbbr, geneDesc, genomeName, geneName)
                except:
                    print (i, genome, path, nameline)
                    raise

                if not geneDesc:
                    print ('no gene desc found', seqId, genome, path)
                if not geneName:
                    print ('no gene name found', seqId, genome, path)
                    
                # assert exactly one abbreviation for genome
                if not genomeToAbbr.has_key(genome):
                    genomeToAbbr[genome] = genomeAbbr
                elif genomeToAbbr[genome] != genomeAbbr:
                    raise Exception('More than one abbreviation found for a genome', genomeAbbr, genomeToAbbr[genome], nameline, genome, path, i)
                
                # do not assert exactly one name for genome, b/c some genomes have a different name in sprot and trembl.
                if not genomeToName.has_key(genome):
                    genomeToName[genome] = genomeName
                elif genomeToName[genome] != genomeName and genome not in badGenomes:
                    raise Exception('More than one name found for a genome', genomeName, genomeToName[genome], nameline, genome, path, i)

                # gene name and description are optional, but a sequence must be encountered only once.
                if geneToName.has_key(seqId):
                    raise Exception('Sequence encountered more than one time!', seqId, geneName, geneDesc, nameline, genome, path, i)
                geneToName[seqId] = geneName
                geneToDesc[seqId] = geneDesc

    with open(os.path.join(ds, 'genome_to_name.json'), 'w') as fh:
        json.dump(genomeToName, fh)
    with open(os.path.join(ds, 'genome_to_abbr.json'), 'w') as fh:
        json.dump(genomeToAbbr, fh)
    with open(os.path.join(ds, 'gene_to_name.json'), 'w') as fh:
        json.dump(geneToName, fh)
    with open(os.path.join(ds, 'gene_to_desc.json'), 'w') as fh:
        json.dump(geneToDesc, fh)
        
            
def filterAndFormatGenomes(ds):
    print 'filtering and formatting genomes. {}'.format(ds)
    if isStepComplete(ds, 'filter and format genomes'):
        print 'already complete'
        return

    genomes = getGenomes(ds)
    genomeToSize = {}
    preNum = len(genomes)
    print 'before: {} genomes in dataset.'.format(len(genomes))
    for genome in getGenomes(ds):
        print 'filter/format {}'.format(genome)
        fastaPath = getGenomeFastaPath(ds, genome)
        size = fasta.numSeqsInFastaDb(fastaPath)
        if size < MIN_GENOME_SIZE:
            # filter out genomes with too few sequences (mostly viruses, etc.)
            shutil.rmtree(getGenomePath(ds, genome))
        else:
            genomeToSize[genome] = size
            # format for blast genomes with enough sequences.
            os.chdir(os.path.dirname(fastaPath))
            cmd = 'formatdb -p -o -i'+os.path.basename(fastaPath)
            subprocess.check_call(cmd, shell=True)

    # since genomes might have been removed from the dataset, refresh the cached genomes in the metadata
    genomes = getGenomes(ds, refresh=True)
    postNum = len(genomes)
    print 'after: {} genomes in dataset.'.format(len(genomes))
    updateMetadata(ds, {'filter': {'num_genome_before': preNum, 'num_genomes_after': postNum}, 'genomeToSize': genomeToSize})

    print 'genome size'
    for genome, size in sorted(genomeToSize.items(), key=lambda x: (x[1], x[0])):
        print size, genome

    print 'done filtering and formatting genomes'
    markStepComplete(ds, 'filter and format genomes')


def prepareComputation(ds, oldDs=None, numJobs=4000):
    print 'preparint computations for {}'.format(ds)
    if isStepComplete(ds, 'prepare computation'):
        print 'already complete'
        return
    
    if oldDs:
        # get new and old pairs
        newPairs, oldPairs = getNewAndDonePairs(ds, oldDs)
        # get orthologs for old pairs and dump them into a orthologs file.
    else:
        newPairs = getPairs(ds)
        oldPairs = []
    # save the pairs to be computed and the pairs whose orthologs need to be moved.
    print 'saving new and old pairs'
    setNewPairs(ds, newPairs)
    setOldPairs(ds, oldPairs)
    print 'new pair count:', len(newPairs)
    print 'old pair count:', len(oldPairs)
    # create up to N jobs for the pairs to be computed.
    # each job contain len(pairs)/N pairs, except if N does not divide len(pairs) evenly, some jobs get an extra pair.
    # permute the pairs so (on average) each job will have about the same running time.  Ideally job running time would be explictly balanced.
    random.shuffle(newPairs)
    numJobs = min(numJobs, len(newPairs))
    jobSize = len(newPairs) // numJobs
    print 'jobSize = ', jobSize
    numExtraPairs = len(newPairs) % numJobs
    print 'numExtraPairs =',numExtraPairs
    start = 0
    end = jobSize
    # create jobs in multiple processes (i.e. using multiprocessing module) to speed up.
    for i in range(numJobs):
        if i % 100 == 0: print 'preparing job', i
        job = 'job_{}'.format(i)
        if i < numExtraPairs:
            end += 1
        print 'job =', job, 'start =', start, 'end =', end
        jobPairs = newPairs[start:end]
        print 'jobPairs=', jobPairs
        start = end
        end = end + jobSize
        getJobDir(ds, job)
        os.makedirs(getJobDir(ds, job), 0770)
        setJobPairs(ds, job, jobPairs)
    markStepComplete(ds, 'prepare computation')
    

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


#########
# TESTING
#########

def splitOrthologsIntoOldResultsFiles(ds, here='.'):
    '''
    This is useful for comparing new results, where orthologs for different pairs and parameter combinations are combined in a single file,
    against old results, where every pair x param combo has its own file for orthologs.
    '''
    for job in getJobs(ds):
        for (qdb, sdb, div, evalue, qhit, shit, dist) in getJobOrthologs(ds, job):
            with open(os.path.join(here, '{}.aa_{}.aa_{}_{}'.format(qdb, sdb, div, evalue)), 'a') as fh:
                fh.write('{} {} {}\n'.format(shit, qhit, dist))

        
###############
# DATASET STUFF
###############

def _getDatasetId(ds):
    return 'roundup_ds_' + os.path.basename(ds)


def getGenomesDir(ds):
    return os.path.join(ds, 'genomes')


def getJobsDir(ds):
    return os.path.join(ds, 'jobs')

    
def getOrthologsDir(ds):
    return os.path.join(ds, 'orthologs')

    
def getSourcesDir(ds):
    return os.path.join(ds, 'sources')


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
        if isComplete(ds, 'job', job):
            print 'job is already complete:', job
            continue
        if isJobRunning(ds, job):
            print 'job is already running:', job
            continue
        funcName = 'roundup_dataset.computeJob'
        keywords = {'ds': ds, 'job': job}
        # request that /scratch has at least ~10GB free space to avoid nodes where someone, not naming any names, has been a bad neighbor.
        lsfOptions = ['-R "scratch > 10000"', '-q '+LSF.LSF_LONG_QUEUE, roundup_common.ROUNDUP_LSF_OUTPUT_OPTION, '-J '+getComputeJobName(ds, job)]
        jobid = lsfdispatch.dispatch(funcName, keywords=keywords, lsfOptions=lsfOptions)
        msg = 'computeJobs(): running job on grid.  lsfjobid={}, ds={}, job={}'.format(jobid, ds, job)
        print msg
        logging.log(roundup_common.ROUNDUP_LOG_LEVEL, msg)


def computeJob(ds, job):
    '''
    job: identifies which job this is so it knows which pairs to compute.
    computes orthologs for every pair in the job.  merges the orthologs into a single file and puts that file in the dataset orthologs dir.
    '''
    if isComplete(ds, 'job', job):
        return
    # a job is complete when all of its pairs are complete and it has written all the orthologs for all the pairs to a file.
    print ds
    print job
    pairs = getJobPairs(ds, job)
    print pairs
    jobDir = getJobDir(ds, job)
    print jobDir
    # compute orthologs for pairs
    for pair in pairs:
        orthologsPath = os.path.join(jobDir, '{}_{}.pair.orthologs.txt'.format(*pair))
        print orthologsPath
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
        if os.path.exists(orthologsPath):
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
    queryGenomePath = getGenomePath(ds, queryGenome)
    subjectGenomePath = getGenomePath(ds, subjectGenome)
    queryFastaPath = getGenomeFastaPath(ds, queryGenome)
    subjectFastaPath = getGenomeFastaPath(ds, subjectGenome)
    queryIndexPath = getGenomeIndexPath(ds, queryGenome)
    subjectIndexPath = getGenomeIndexPath(ds, subjectGenome)
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
    # clean up files
    if os.path.exists(forwardHitsPath):
        os.remove(forwardHitsPath)
    if os.path.exists(reverseHitsPath):
        os.remove(reverseHitsPath)
    # complete pair computation
    pairEndTime = time.time()
    # storePairStats(ds, pair, pairStartTime, pairEndTime)
    markComplete(ds, 'pair', pair)


#################################
# LOADING DATASET INTO DATABASE
#################################

def loadDatabase(ds):
    # parse results files, getting a list of sequences.
    # get gene name from fasta lines.
    # get go ids from idmapping file.
    # get go name from ...
    
    # drop and create tables for dataset.
    pass


######
# JOBS
######

def getJobs(ds, refresh=False):
    '''
    caches jobs in the dataset metadata if they have not already been
    cached, b/c the isilon is wicked slow at listing dirs.
    returns: list of jobs in the dataset.
    '''
    if refresh:
        return updateMetadata(ds, {'jobs': os.listdir(getJobsDir(ds))})['jobs']
    else:
        jobs = loadMetadata(ds).get('jobs')
        if not jobs:
            return updateMetadata(ds, {'jobs': os.listdir(getJobsDir(ds))})['jobs']
        else:
            return jobs

def getJobPairs(ds, job):
    return readPairsFile(os.path.join(getJobDir(ds, job), 'job_pairs.txt'))


def setJobPairs(ds, job, pairs):
    writePairsFile(pairs, os.path.join(getJobDir(ds, job), 'job_pairs.txt'))


def getJobDir(ds, job):
    return os.path.join(getJobsDir(ds), job)


def getJobOrthologsPath(ds, job):
    return os.path.join(getOrthologsDir(ds), '{}.orthologs.txt'.format(job))


def getJobOrthologs(ds, job):
    return readOrthologsFile(getJobOrthologsPath(ds, job))


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
                                                        

#########
# GENOMES
#########

def getGenomes(ds, refresh=False):
    '''
    caches genomes in the dataset metadata if they have not already been
    cached, b/c the isilon is wicked slow at listing dirs.
    returns: list of genomes in the dataset.
    '''
    if refresh:
        return updateMetadata(ds, {'genomes': os.listdir(getGenomesDir(ds))})['genomes']
    else:
        genomes = loadMetadata(ds).get('genomes')
        if not genomes:
            return updateMetadata(ds, {'genomes': os.listdir(getGenomesDir(ds))})['genomes']
        else:
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


def getGenomePath(ds, genome):
    '''
    a genomePath is a directory containing genome fasta files and blast indexes.
    '''
    return os.path.join(getGenomesDir(ds), genome)


def getGenomeFastaPath(ds, genome):
    return os.path.join(getGenomePath(ds, genome), genome+'.faa')


def getGenomeIndexPath(ds, genome):
    '''
    location of blast index files
    '''
    return os.path.join(getGenomePath(ds, genome), genome+'.faa')

    

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
            fh.write('{}\n'.format('\t'.join([str(f) for f in ortholog])))


###########
# COMPLETES
###########
# two different completes: one better for many completes and concurrency, the other for hand editing and associated with the dataset.

# isComplete uses the mysql database.  Used for concurrent execution of jobs, pairs, and other large numbers of completes.
# pros: concurrency, fast even with millions of completes.  cons: different mysql db for dev and prod, so must use the prod code on a prod dataset.
def isComplete(ds, *key):
    return bool(int(getKVCacheValue(ds, str(key), 0)))


def markComplete(ds, *key):
    putKVCacheValue(ds, str(key), 1)


# isStepComplete uses a flat file in the dataset.  Used for downloading source files and other few completes executed serially.
# pros: completes associated with the dataset, not the code base.  easy to edit completes by hand.
# cons: very slow for many completes; concurrent writing of completes is unsafe.
def isStepComplete(ds, *key):
    stepsPath = os.path.join(ds, 'steps.complete.txt')
    keyStr = str(key)
    with open(stepsPath) as fh:
        completes = set(line.strip() for line in fh if line.strip())
        return keyStr in completes

    
def markStepComplete(ds, *key):
    stepsPath = os.path.join(ds, 'steps.complete.txt')
    with open(stepsPath, 'a') as fh:
        fh.write(str(key)+'\n')
        
        
#######
# PAIRS
#######

def getPairs(ds, genomes=None):
    '''
    returns: a sorted list of pairs, where every pair is a sorted list of each combination of two genomes.
    '''
    if genomes is None:
        genomes = getGenomes(ds)
    return sorted(set([tuple(sorted((g1, g2))) for g1 in genomes for g2 in genomes if g1 != g2]))


def getNewPairs(ds):
    return readPairsFile(os.path.join(ds, 'new_pairs.txt'))


def setNewPairs(ds, pairs):
    writePairsFile(pairs, os.path.join(ds, 'new_pairs.txt'))


def getOldPairs(ds):
    return readPairsFile(os.path.join(ds, 'old_pairs.txt'))


def setOldPairs(ds, pairs):
    writePairsFile(pairs, os.path.join(ds, 'old_pairs.txt'))


def writePairsFile(pairs, path):
    with open(path, 'w') as fh:
        json.dump(pairs, fh, indent=2)
            

def readPairsFile(path):
    pairs = []
    if os.path.exists(path):
        with open(path) as fh:
            pairs = json.load(fh)
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


##########
# METADATA
##########
# The metadata of a dataset is persistent information describing the dataset.
# It is stored in a file, so is not safe for concurrent updating.

def updateMetadata(ds, metadata):
    '''
    metadata: a dict containing information about the dataset.  e.g. source files, download times, genome names.
    update existing dataset metadata with the values in metadata.
    returns: the updated dataset metadata.
    '''
    md = loadMetadata(ds)
    md.update(metadata)
    return dumpMetadata(ds, md)

    
def loadMetadata(ds):
    '''
    returns: a dict, the existing persisted dataset metadata.
    '''
    path = os.path.join(ds, 'dataset.metadata.json')
    if os.path.exists(path):
        with open(os.path.join(ds, 'dataset.metadata.json')) as fh:
            return json.load(fh)
    else:
        return {}
    

def dumpMetadata(ds, metadata):
    with open(os.path.join(ds, 'dataset.metadata.json'), 'w') as fh:
        json.dump(metadata, fh, indent=2)
    return metadata


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
    qdbFastaPath = getGenomeFastaPath(ds, qdb)
    sdbFastaPath = getGenomeFastaPath(ds, sdb)
    qdbBytes = os.path.getsize(qdbFastaPath)
    sdbBytes = os.path.getsize(sdbFastaPath)
    genomeToSize = loadMetadata(ds)['genomeToSize']
    qdbSeqs = genomeToSize[qdb]
    sdbSeqs = genomeToSize[sdb]
    stats = {'type': 'pair', 'qdb': qdb, 'sdb': sdb, 'startTime': startTime, 'endTime': endTime,
             'qdbBytes': qdbBytes, 'sdbBytes': sdbBytes, 'qdbSeqs': qdbSeqs, 'sdbSeqs': sdbSeqs}
    return stats


########################
# DEPRECATED / UNUSED
########################

# last line - python emacs bug fix
 
