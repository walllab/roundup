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


def getGenomesDir(dsDir):
    return os.path.join(dsDir, 'genomes')


def getJobsDir(dsDir):
    return os.path.join(dsDir, 'jobs')

    
def getResultsDir(dsDir):
    return os.path.join(dsDir, 'results')

    
def getSourcesDir(dsDir):
    return os.path.join(dsDir, 'sources')

    
def prepareDataset(dsDir):
    os.makedirs(getGenomesDir(dsDir), 0770)
    os.makedirs(getResultsDir(dsDir), 0770)
    os.makedirs(getJobsDir(dsDir), 0770)
    os.makedirs(getSourcesDir(dsDir), 0770)


####################
# COMPLETE FUNCTIONS
####################

def isFileComplete(path):
    return os.path.exists(path+'.complete.txt')


def markFileComplete(path):
    util.writeToFile(path, os.path.exists(path+'.complete.txt'))


def isSourcesComplete(dsDir):
    return os.path.exists(os.path.join(dsDir, 'sources.complete.txt'))

    
def markSourcesComplete(dsDir):
    util.writeToFile('sources complete', os.path.exists(os.path.join(dsDir, 'sources.complete.txt')))

    
def isGenomesComplete(dsDir):
    return os.path.exists(os.path.join(dsDir, 'genomes.complete.txt'))

    
def markGenomesComplete(dsDir):
    util.writeToFile('genomes complete', os.path.exists(os.path.join(dsDir, 'genomes.complete.txt')))

        
def downloadCurrentUniprot(dsDir):
    '''
    Download uniprot files containing protein fasta sequences and associated meta data (gene names, go annotations, dbxrefs, etc.)
    '''
    if isSourcesComplete(dsDir):
        return
    
    sprotDatUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.dat.gz'
    sprotXmlUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.xml.gz'
    tremblDatUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.dat.gz'
    tremblXmlUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.xml.gz'
    idMappingUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping.dat.gz'
    idMappingSelectedUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping_selected.tab.gz'

    sourcesDir = getSourcesDir(dsDir)
    for url in [sprotDatUrl, sprotXmlUrl, tremblDatUrl, tremblXmlUrl, idMappingUrl, idMappingSelectedUrl]:
        dest = os.path.join(sourcesDir, os.path.basename(urlparse.urlparse(sprotUrl).path))
        if isFileComplete(dest)
            continue
        cmd = 'curl --remote-time --output '+dest+' '+url
        execute.run(cmd)
        markFileComplete(dest)
    markSourcesComplete(dsDir)


def splitUniprotIntoGenomes(dsDir):
    if isGenomesComplete(dsDir):
        return

    taxons = set()
    import Bio.SeqIO, cPickle, sys, os
    sourceFiles = [os.path.join(getSourcesDir(dsDir), f) for f in ('uniprot_sprot.dat', 'uniprot_trembl.dat')]
    for file in sourceFiles:
        for i, record in enumerate(Bio.SeqIO.parse(file, "swiss")):
            if record.annotations.has_key("keywords") and "Complete proteome" in record.annotations["keywords"]:
                taxon = record.annotations["ncbi_taxid"][0]
                if taxon not in taxons:
                    # first time a taxon is seen, start a fresh genome file.
                    taxons.add(taxon)
                    with open("foo", "w") as fh:
                        pass
                fasta = ">%s\n%s\n"%(record.id, record.seq)
                with open("%s.aa"%taxon, "a") as fh:
                    fh.write(fasta)
    markSourcesComplete(dsDir)
    
    
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
                

            if tokens and tokens[0] == '//':
                

            if tokens and tokens[0] == 'KW':
                

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

