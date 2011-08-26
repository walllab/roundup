2011/08/25 Todd F. DeLuca, Scientific Programmer, Wall Laboratory, Center for Biomedical Informatics, Harvard Medical School, USA, Earth, Sol System, etc.
http://roundup.hms.harvard.edu
http://wall.hms.harvard.edu

This directory contains the scripts needed to run the Reciprocal Smallest Distance (RSD) ortholog detection algorithm as well as examples of input and output files.

README.txt:  the file you are reading now
rsd.py:  the main script which executes the RSD -- reciprocal smallest distance -- ortholog detection alogorithm
fasta.py, util.py, nested.py:  modules defining a helpful functions used by rsd.py
jones.dat, codeml.ctl:  used by codeml/paml to compute the evolutionary distance between two sequences.
examples:  a directory containing examples of inputs and outputs to rsd.py, including fasta-formatted genome sequence files, BLAST formatted index files, 
 a query sequence id file (for --ids), and an orthologs output file.


##########################
# RUNNING RSD USING rsd.py
##########################

The following example commands demonstrate the main ways to run rsd.py.  
Every invocation requires specifying the location of a FASTA-formatted sequence file for two genomes, called the query and subject genomes.  
Their order is arbitrary, but if you use the --ids option, the ids must come from the query genome.
You must also specify a file to write the results of the orthologs found by the RSD algorithm.  This file contains one ortholog per line.  
Each line contains the query sequence id, subject sequence id, and distance (calculated by codeml) between the sequences.
You can optionally specify a file containing ids using the --ids option.  Then rsd.py will only search for orthologs for those ids.
Using --divergence and --evalue, you have the option of using different thresholds from the defaults.


# Get help on how to run rsd.py
./rsd.py -h


# Compute orthologs between all the sequences in the query and subject genomes.

./rsd.py -d 0.2 -e 1e-20 -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt


# Compute orthologs using non-default divergence and evalue thresholds

./rsd.py -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.8_1e-5.orthologs.txt \
-d 0.8 -e 1e-5


# Compute orthologs between all the sequences in the query and subject genomes using genomes that have already been formatted for blast.

./rsd.py -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.8_1e-5.orthologs.txt \
--no-format


# Compute orthologs for only a few sequences in the query genome. When used with --no-blast-cache, this speeds up RSD when only a few orthologs are being computed.

./rsd.py -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.8_1e-5.orthologs.txt \
--ids examples/Mycoplasma_genitalium.aa.ids.txt --no-blast-cache


##################################
# FORMATTING FASTA FILES FOR BLAST
##################################

It is not necessary to format a fasta file for BLAST, because rsd.py does it for you.  However should you find yourself running
the program multiple times, especially for large genomes, preformatting the fasta files and using --no-format can save you time.
Here is how rsd.py formats fasta files:

python -c 'import rsd; rsd.formatForBlast("examples/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa")'
python -c 'import rsd; rsd.formatForBlast("examples/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa")'


########
# EXTRAS
########

Additionals:
A user may also care to change the alpha shape parameter for the gamma distribution used in the likelihood calculations of the codeml package of paml.  This must be done in the codeml.ctl
