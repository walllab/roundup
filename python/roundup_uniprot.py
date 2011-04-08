'''
Download UniProtKB.  Save for future reference, e.g. if metadata needs to be acquired or fasta files recreated.
Split uniprot into separate fasta files for each complete genome.
Check the quality of the fasta files.  Enough sequences?  Non-redundant sequences?
Generate Ids for each genome.  Are all ids unique?  Taxon name, ncbi taxon id, uniprot 5 character id.
Format fasta files for roundup.
Generate metadata for genomes.

Why use dat files and not fasta files?  Because dat file has much more metadata (including which seqs are part of complete genome.
Description of dat files, aka swissprot format, http://arep.med.harvard.edu/labgc/jong/Fetch/SwissProtAll.html.
'''


import os
import urlparse
import subprocess
import time

import util


def getGenomesDir(ds):
    return os.path.join(ds, 'genomes')


def getJobsDir(ds):
    return os.path.join(ds, 'jobs')

    
def getResultsDir(ds):
    return os.path.join(ds, 'results')

    
def getSourcesDir(ds):
    return os.path.join(ds, 'sources')

    
def prepareDataset(ds):
    os.makedirs(getGenomesDir(ds), 0770)
    os.makedirs(getResultsDir(ds), 0770)
    os.makedirs(getJobsDir(ds), 0770)
    os.makedirs(getSourcesDir(ds), 0770)


def getPairs(ds):
    return roundup_common.getPairs(getGenomes(ds))


def getGenomes(ds):
    return getGenomesAndPaths.keys()

    
def getGenomesAndPaths(ds):
    '''
    returns: a dict mapping every genome in the dataset to its genomePath.
    '''
    genomesAndPaths = {}
    genomesDir = getGenomesDir(ds)
    for genome in set(os.listdir(genomesDir)):
        genomesAndPaths[genome] = os.path.join(genomesDir, genome)
    return genomesAndPaths


def getGenomeFastaFile(genome, ds):
    return os.path.join(getGenomesDir(ds), genome, genome+'.aa')


def getGenomeBlastIndex(genome, ds):
    return os.path.join(getGenomesDir(ds), genome, genome+'.aa')
    
    
####################
# COMPLETE FUNCTIONS
####################

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

        
#######
# PAIRS
#######

PAIRS_CACHE = {}
def getPairs(ds):
    '''
    get the pairs that need computing.
    '''
    if not PAIRS_CACHE.has_key(ds):
        pairs = []
        if os.path.exists(pairsCacheFile(ds)):
            with open(pairsCacheFile(ds)) as fh:
                for line in fh:
                    if line.strip():
                        pairs.append(line.split())
        PAIRS_CACHE[ds] = roundup_common.normalizePairs(pairs)
    return PAIRS_CACHE[ds]


def setPairs(ds, pairs):
    '''
    cache the set of pairs that need computing.
    '''
    PAIRS_CACHE[ds] = pairs
    with open(pairsCacheFile(ds), 'w') as fh:
        for qdb, sdb in pairs:
            fh.write('%s %s\n'%(qdb, sdb))
    
        
def pairsCacheFile(ds):
    '''
    A file containing pairs of genomes that need to be computed.
    '''
    return os.path.join(ds, 'pairs.txt')    


def downloadCurrentUniprot(ds):
    '''
    Download uniprot files containing protein fasta sequences and associated meta data (gene names, go annotations, dbxrefs, etc.)
    '''
    if isSourcesComplete(ds):
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


def splitUniprotIntoGenomes(ds):
    '''
    create separate fasta files for each complete genome in the uniprot (sprot and trembl) data.
    '''
    if isGenomesComplete(ds):
        return

    taxons = set()
    import Bio.SeqIO, cPickle, sys, os
    sourceFiles = [os.path.join(getSourcesDir(ds), f) for f in ('uniprot_sprot.dat', 'uniprot_trembl.dat')]
    for file in sourceFiles[:1]:
        print 'splitting {} into genomes'.format(file)
        for i, record in enumerate(Bio.SeqIO.parse(file, "swiss")):
            if record.annotations.has_key("keywords") and "Complete proteome" in record.annotations["keywords"]:
                taxon = record.annotations["ncbi_taxid"][0]
                if taxon not in taxons:
                    # first time a taxon is seen, start a fresh genome file.
                    taxons.add(taxon)
                    with open("foo", "w") as fh:
                        pass
                fasta = ">%s\n%s\n"%(record.id, record.seq)
                fastaFile = getGenomeFastaFile(taxon, ds)
                with open(fastaFile, "a") as fh:
                    fh.write(fasta)
    markSourcesComplete(ds)


def getNewAndDonePairs(ds, oldDs):
    '''
    ds: current dataset, containing genomes
    oldDs: a previous dataset.
    Sort all pairs of genomes in the current dataset into todo and done pairs:
      new pairs need to be computed because each pair contains at least one genome that does not exist in or is different from the genomes of the old dataset.
      done pairs do not need to be computed because the genomes of each pair are the same as the old dataset, so the old results are still valid.
    returns: the tuple, (newPairs, donePairs)
    '''
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

    setPairs(computeDir, pairs)
    return pairs


def prepareComputation(ds, oldDs=None, numJobs=):
    if oldDs:
        # get new and old pairs
        pairs, oldPairs = getNewAndDonePairs(ds, oldDs)
        # get results for old pairs and dump them into a results file.
    else:
        pairs = getPairs(ds)
    # save the pairs to be computed.
    setPairs(ds, pairs)
    # create N jobs for the pairs to be computed.  
    


def parseUniprotDat(path):
    with open(path) as fh:
        for line in fh:
            tokens = line.strip().split()
            
            if tokens and tokens[0] == 'ID':
                seqId = tokens[1]
            if tokens and tokens[0] == 'AC':
                accNum = tokens[1]
            if tokens and tokens[0] == 'KW' and line.find('Complete genome') > -1:
                complete = True
            if tokens and tokens[0] == 'SQ':
                pass
            if tokens and tokens[0] == '//':
                pass
            if tokens and tokens[0] == 'KW':
                pass


def main(ds='.'):
    downloadCurrentUniprot(ds)
    splitUniprotIntoGenomes(ds)

    
if __name__ == '__main__':
    pass


example_dat_sequence = '''
ID   003L_IIV3               Reviewed;         156 AA.
AC   Q197F7;
DT   16-JUN-2009, integrated into UniProtKB/Swiss-Prot.
DT   11-JUL-2006, sequence version 1.
DT   28-JUL-2009, entry version 12.
DE   RecName: Full=Uncharacterized protein 003L;
GN   ORFNames=IIV3-003L;
OS   Invertebrate iridescent virus 3 (IIV-3) (Mosquito iridescent virus).
OC   Viruses; dsDNA viruses, no RNA stage; Iridoviridae; Chloriridovirus.
OX   NCBI_TaxID=345201;
OH   NCBI_TaxID=7163; Aedes vexans (Inland floodwater mosquito) (Culex vexans).
OH   NCBI_TaxID=42431; Culex territans.
OH   NCBI_TaxID=332058; Culiseta annulata.
OH   NCBI_TaxID=310513; Ochlerotatus sollicitans (eastern saltmarsh mosquito).
OH   NCBI_TaxID=329105; Ochlerotatus taeniorhynchus (Black salt marsh mosquito) (Aedes taeniorhynchus).
OH   NCBI_TaxID=7183; Psorophora ferox.
RN   [1]
RP   NUCLEOTIDE SEQUENCE [LARGE SCALE GENOMIC DNA].
RX   PubMed=16912294; DOI=10.1128/JVI.00464-06;
RA   Delhon G., Tulman E.R., Afonso C.L., Lu Z., Becnel J.J., Moser B.A.,
RA   Kutish G.F., Rock D.L.;
RT   "Genome of invertebrate iridescent virus type 3 (mosquito iridescent
RT   virus).";
RL   J. Virol. 80:8439-8449(2006).
CC   -----------------------------------------------------------------------
CC   Copyrighted by the UniProt Consortium, see http://www.uniprot.org/terms
CC   Distributed under the Creative Commons Attribution-NoDerivs License
CC   -----------------------------------------------------------------------
DR   EMBL; DQ643392; ABF82033.1; -; Genomic_DNA.
DR   RefSeq; YP_654575.1; -.
DR   GeneID; 4156252; -.
PE   4: Predicted;
KW   Complete proteome; Virus reference strain.
FT   CHAIN         1    156       Uncharacterized protein 003L.
FT                                /FTId=PRO_0000377939.
SQ   SEQUENCE   156 AA;  17043 MW;  D48A43940FF8C815 CRC64;
     MYQAINPCPQ SWYGSPQLER EIVCKMSGAP HYPNYYPVHP NALGGAWFDT SLNARSLTTT
     PSLTTCTPPS LAACTPPTSL GMVDSPPHIN PPRRIGTLCF DFGSAKSPQR CECVASDRPS
     TTSNTAPDTY RLLITNSKTR KNNYGTCRLE PLTYGI
//
'''

