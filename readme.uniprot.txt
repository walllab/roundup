==========
2010-07-15
==========

[todo] roundup download: source of new proteomes.  found via OMABrowser.  UniProtKB.  Combines non-redundant proteins from many sources, including Ensembl, NBCI, 
[done] UniProtKB rocks!
http://www.expasy.org/sprot/hamap/proteomes.html
UniProtKB-GOA (http://www.ebi.ac.uk/GOA/goaHelp.html):
Additional species-specific sets are available from the proteomes sets, which include separate annotation files for all species whose genome has been fully sequenced, where the sequence is publicly available, and where the proteome contains >25% GO annotation. 
# downloading UniProtKB from http://www.uniprot.org/downloads
# fasta file contains sequence information and information about seq (or is it gene) id and organism
# dat file contains sequence and detailed annotation information.
# xml file contains sequence and detailed annotation info.
# OS = organism scientific (name)?
td23@todd-mac:~/Downloads$ grep -c '>' uniprot_sprot.fasta
518415
td23@todd-mac:~/Downloads$ grep -ce '^ID' uniprot_sprot.dat
518415
# download swissprot and trembl fasta and xml
bsub -q cbi_2h curl -o uniprot_sprot.xml.gz ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.xml.gz
bsub -q cbi_2h curl -o uniprot_trembl.xml.gz ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.xml.gz
bsub -q cbi_2h curl -o uniprot_sprot.fasta.gz ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.fasta.gz
bsub -q cbi_2h curl -o uniprot_trembl.fasta.gz ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.fasta.gz
bsi
gunzip *.gz
# NOTE: some seqs in dat file from mulitple organisms.  e.g. from release1.0. 14KD_MYCTU, OS   Mycobacterium tuberculosis, and OS   Mycobacterium bovis.

# are all sequences unique?
# are all sequences: non-dna? long enough? 
# all seqs non-redundant? (swissprot: one seq per gene, trembl: no identical seqs in same species, but possibly multiple transcriptions/translations per gene.
# separate sequences into individual file per genome.  
# there are non-genome sequences.  e.g. in trembl, OS=uncultured archaeon.
# are there non-fully sequenced genomes?
The list of complete proteome sets in UniProt: http://www.uniprot.org/taxonomy/?query=complete:yes
From http://www.uniprot.org/faq/15: "For the complete proteomes entirely stored in UniProtKB, all entries have been tagged with the keyword 'Complete proteome' allowing their easy retrieval directly from the database."
# how are strains handled?
# Where do the UniProtKB protein sequences come from?
http://www.uniprot.org/faq/37
More than 99% of the protein sequences provided by UniProtKB come from the translations of coding sequences (CDS) submitted to the EMBL-Bank/GenBank/DDBJ
In addition to translated CDS, UniProtKB protein sequences may come from:
  the PDB database.
  sequences experimentally obtained by direct protein sequencing, by Edman degradation or MS/MS experiments and submitted to UniProtKB/Swiss-Prot. Less than 6% of the UniProtKB/Swiss-Prot entries contain sequence data obtained by direct protein sequencing (list of entries with the keywords 'Direct protein sequencing') and some entries contain sequences exclusively obtained by that means (list of entries).
  sequences scanned from the literature (i.g. PRF or other journal scan project).
  sequences derived from gene prediction, not submitted to EMBL-Bank/GenBank/DDBJ (Ensembl, RefSeq, CCDS, etc). These data are restricted to some organisms, e.g. homo sapiens
  sequences derived from in-house gene prediction, in very specific cases.


==========
2010-09-02
==========


[todo] download historical versions of uniprotkb for past few years to guage growth in size and number of complete genomes
[done] sent email to parul and vince with the data.  Basically number of Uniprot complete proteomes has been doubling almost every year, though it has slowed down considerably the last 2 years.
# download uniprot versions like 1.0
cd /groups/cbi/td23/uniprot
python -c'import subprocess
for release in ("%s.0"%r for r in range(1, 16)):
  url = "ftp://ftp.uniprot.org/pub/databases/uniprot/previous_releases"
  cmd = "bsub -q cbi_unlimited curl -o knowledgebase%(r)s.tar.gz %(url)s/release%(r)s/knowledgebase/knowledgebase%(r)s.tar.gz"%{"r": release, "url": url}
  print cmd
  print subprocess.call(cmd, shell=True)
'
# download more uniprot versions.  These ones like 2010_01, b/c they changed their naming scheme in 2010.
python -c'import subprocess
for release in ("2010_0%s"%r for r in range(1, 9)):
  url = "ftp://ftp.uniprot.org/pub/databases/uniprot/previous_releases"
  cmd = "bsub -q cbi_unlimited curl -o knowledgebase%(r)s.tar.gz %(url)s/release-%(r)s/knowledgebase/knowledgebase%(r)s.tar.gz"%{"r": release, "url": url}
  print cmd
  print subprocess.call(cmd, shell=True)
'
# unpack to separate dirs
mkdir versions
python -c'import glob, subprocess, os;
for path in glob.glob("*.tar.gz"):
  cwd = os.getcwd()
  abspath = os.path.abspath(path)
  print abspath
  name = os.path.basename(abspath)[:-7] # remove .tar.gz
  unpackDir = os.path.join(cwd, "versions/%s"%name)
  cmd = "mkdir -p %(u)s && cd %(u)s && bsub -q cbi_unlimited tar xzf %(a)s && cd %(c)s"%{"u": unpackDir, "a": abspath, "c": cwd}
  print cmd
  print subprocess.call(cmd, shell=True)
'
# unzip dat files in each dir
td23@orchestra:/groups/cbi/td23/uniprot$ find versions -name '*.gz' | xargs -l1 bsub -q all_unlimited gunzip

# every dir in versions/ has a reldate.txt file that contains 3 lines.  the 2nd and 3rd line each end in a date like 01-Jun-2010 and they should be the same date.
# that is the date to plot the number of complete proteomes against.
# example taxon lines: (some seqs belong to >1 taxon)
OX   NCBI_TaxID=7227;
OX   NCBI_TaxID=9606, 10090, 10116, 9913, 9940;
# extract date and number of completed genomes from each version.
bsub -q all_unlimited python /groups/cbi/td23/uniprot/count_complete_taxons.py
Job <556839> is submitted to queue <all_unlimited>.
# copied data from lsf job report into /groups/cbi/td23/uniprot/taxon.table

cat /groups/cbi/td23/uniprot/taxon.table | sort
2003-12-15      155     knowledgebase1.0
2004-07-05      222     knowledgebase2.0
2004-10-25      169     knowledgebase3.0
2005-02-01      192     knowledgebase4.0
2005-05-10      217     knowledgebase5.0
2005-09-13      232     knowledgebase6.0
2006-02-07      274     knowledgebase7.0
2006-05-30      314     knowledgebase8.0
2006-10-31      362     knowledgebase9.0
2007-03-06      436     knowledgebase10.0
2007-05-29      475     knowledgebase11.0
2007-07-24      501     knowledgebase12.0
2008-02-26      858     knowledgebase13.0
2008-07-22      1130    knowledgebase14.0
2009-03-24      1242    knowledgebase15.0
2010-01-19      1480    knowledgebase2010_01
2010-02-09      1493    knowledgebase2010_02
2010-03-02      1536    knowledgebase2010_03
2010-03-23      1549    knowledgebase2010_04
2010-04-20      1562    knowledgebase2010_05
2010-05-18      1579    knowledgebase2010_06
2010-06-15      1598    knowledgebase2010_07
2010-07-13      1621    knowledgebase2010_08

# copy to laptop
scp orchestra.med.harvard.edu:/groups/cbi/td23/uniprot/taxon.table ~
sort -n taxon.table > foo && cat foo > taxon.table
# visualize in R
taxon <- read.table("/Users/td23/taxon.table", header=F)
summary(taxon)
# attach(taxon)
# names(taxon)
# taxon$V1 <- as.Date(taxon$V1, "%Y-%m-%d")
x = as.Date(taxon$V1, "%Y-%m-%d")
taxon = cbind(taxon, x)
# V1 <- as.Date(V1) 
sapply(taxon, mode) # to see that dates are being read in as numeric.
plot(taxon$x, taxon$V2, main="Proliferation of Complete Genomes in Uniprot", xlab="Date", ylab="Number of Complete Genomes")
my.lm <- lm(taxon$V2 ~ taxon$x)
abline(my.lm)
my.exp <- lm(log(taxon$V2) ~ taxon$x)
abline(my.exp)

