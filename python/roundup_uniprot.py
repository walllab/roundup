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

def downloadCurrentUniprot(workDir):
    sprotUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.dat.gz'
    tremblUrl = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.dat.gz'
    

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

