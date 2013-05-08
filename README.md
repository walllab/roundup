# CREATED: 2004/11/18 td23
# MODIFIED: 2009/03/19 td23
# MODIFIED: 2011/08/02 td23

This file explains the structures and processes of Roundup.
There is no guarantee that this file is up-to-date and complete!
But read it anyway.


###################################
# HOW TO MAKE A NEW ROUNDUP RELEASE
###################################

Create a new dataset by following the steps in roundup_dataset.py.  Computing orthologs should take weeks.
Load the dataset into the database using roundup_load.py
Change config.py so the CURRENT_RELEASE is the new one.


##################
# WHAT IS ROUNDUP?
##################

Roundup is a database of orthologous sequences/genes between many genomes.
Roundup uses the Reciprocal Shortest Distance (RSD) algorithm to compute orthologs between a pair of genomes.
Roundup is a website that queries a database loaded with orthologous genes to return phylogenetic profiles and other multi-genome perspectives on the database.
Roundup is code for downloading genomes for a dataset, computing orthologs for the dataset, and loading the dataset into mysql for the web queries.


#############################
# Where is the code and data?
#############################

There are (at least) two kinds of roundup code and data, dev and prod, i.e. development and production.
Dev code is code deployed to /www/dev.roundup.hms.harvard.edu/webapp
Prod code is code deployed to /www/roundup.hms.harvard.edu/webapp
Dev code by default uses the dev database.
Prod code by default uses the prod database.
Dev code can be made to use the prod database by setting various environment variables.  See examples in this file.
Prod code could run on the dev database, but why would you do that?
Prod data is located in /groups/cbi/roundup and mysql.cl.med.harvard.edu in the roundup database.
Dev data is located in /groups/cbi/dev.roundup and dev.mysql.cl.med.harvard.edu in the devroundup database.


###########################################
# What are some of the concepts in roundup?
###########################################

GENOMES: A genome refers to several things: a id, like HUMAN or MYCGE;  a directory (named after the id) that contains fasta files and blast-formatted indices.
For historical reasons genomes are sometimes referred to as qdb and sdb, which stand for query database and subject database, where database means genome.

GENES: genes are sequences from the fasta files of the genomes.  Each gene has an id.  These ids are sometimes referred to as qid or sid (query id, subject id).

PAIRS: RSD computes orthologs for a pair of genomes.  A pair is a tuple of genome ids.  The lexicographically smaller id is always the first in the tuple.  In a dataset, all pairs for all genomes are computed.  If there are n genomes, there are n(n-1)/2 pairs.

PARAMS: RSD computes orthologs for a pair of genomes, a divergence threshold and an evalue threshold.  These collectively are the parameters of RSD and are referred to as params.  They are a tuple of (qdb, sdb, div, evalue).

ORTHOLOGS: a list of orthologs.  an ortholog is a gene from a genome, a gene from another genome, and the maximum-likelihood distance between the genes, a measure of similarity.  orthologs are computed using rsd for each pair of genomes combined with 3 divergences (0.2, 0.5, 0.8) and 4 evalues (1e-20, 1e-15, 1e-10, 1e-5).  Therefore for every pair of genomes there are 12 sets of params and 12 corresponding lists of orthologs.

ORTHDATA: is a tuple of params and the associated orthologs.  These are persisted to files, many orthdatas per file, in the orthologs directory of a dataset.

QUERY and SUBJECT: RSD takes as input two genomes.  The first one is called the query genome or qdb, the second is called the subject genome or sdb.  In Roundup, the query genome is always chosen so that its id is lexicographically (that's a fancy way of saying alphabetically) smaller than the subject genome id.

DATASET: A dataset contains all the data for a specific release of roundup: the genomes, the orthologs computed for each set of params for all pairs of genomes, the source files, the metadata extracted from the source files (like gene names, the number of genomes), and other metadata (like the number of orthologs).  The dataset also stores information about the computation of orthologs.  It splits the computation into some number of jobs and tracks which jobs are complete using a "dones" table in the database.

JOBS: are directories in a dataset which organize how orthologs are computed.  All pairs for the dataset are split among the jobs.  For each job, a job is run on LSF, which computes orthologs for the pairs assigned to that job and then saves the orthologs (as orthDatas) to a file in the orthologs dir.

DATABASE: most of the roundup website uses data from a mysql database.  Tables for the dataset are loaded with data from a dataset.  

RELEASE: Each dataset is called a release on the website and in the code.  Releases are named with a number.  Release 1 is from May 2010.  And so on.


########################################
# WHAT ARE SOME OF THE FILES IN ROUNDUP?
########################################

config.py contains a lot of configuration that is specific to the dev or prod environments.

roundup_common.py contains code shared in common across other files and for abstracting some of the concepts in roundup.

roundup_dataset.py contains code to prepare a new dataset for the next release of roundup, by creating the directory structure, downloading source files, creating genomes from those sources, extracting metadata (genome names, go terms for genes, etc., etc., etc.) from source files, preparing jobs for computation, computing jobs (which run RSD on the pairs of genomes), and extracting more metadata (number of orthologs found, etc.).  

roundup_load.py contains code for loading a dataset into mysql.


roundup_download.py contains code for downloading genomes based on configurations, checking if the downloaded genomes are new and moving the new ones to the set of updated genomes.

roundup_db.py contains code to manage orthologs, genomes, etc., in the mysql database.  (Almost) everything having to do with SQL or mysql is in here.

roundup_util.py contains some code used by the web and other code.

orthquery.py and clustering.py are used by the web to generate phylogenetic profiles and other results of web queries.

rsd.py implements the RSD algorithm used to compute orthologs for all genome pairs in Roundup.


