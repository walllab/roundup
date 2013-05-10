


# Introduction


What is Roundup?  Roundup is a database of orthologous proteins between many
organisms.  Roundup uses the Reciprocal Shortest Distance (RSD) algorithm to
compute orthologs between a pair of genomes.  Roundup is a website that queries
a database loaded with orthologous genes to return phylogenetic profiles and
other multi-genome perspectives on the database.  Roundup is code for
downloading genomes for a dataset, computing orthologs for the dataset, and
loading the dataset into mysql for the web queries.


# How to make a new Roundup dataset

Making a new dataset entails downloading the sources of the dataset from the
web, computing orthologs, loading the data into the database for the website,
and updating the website to point to the new dataset.

Each dataset has its own code deployment.  Since computing a dataset on
Orchestra is currently a multi-month process, it is important that the
computation has a stable set of code on which to run, while allowing the
website code to be updated independently if necessary.

First, figure out the number of the next dataset.  If the current dataset is
release 4, the next dataset is release 5.  Then add various values to your
environment (for the convenience of writing commands):

    export DSID=5
    export DSDIR=/groups/public+cbi/sites/roundup/datasets/$DSID
    # The previous dataset is presumably one less than this dataset
    export PREV_DS=/groups/public+cbi/sites/roundup/datasets/`dc -e "$DSID 1 - p"`
    export DSCODE=/groups/public+cbi/sites/roundup/code/$DSID
    echo $DSID $DSDIR $DSCODE


Deploy code for a new dataset from a roundup git repository:
    
    cd ~/work/roundup
    fab ds:$DSID full

Run the dataset workflow to compute the orthologs:

    cd $DSCODE && venv/bin/python app/roundup/dataset.py workflow $DSDIR $PREV_DS

Load the orthologs into the database for the website:

    cd $DSCODE && venv/bin/python app/roundup_load.py workflow $DSDIR

Publish the new dataset to the website:

    # Prepend the dataset dir to `config.archive_datasets` for the `dev` and `prod` tasks.
    vim fabfile.py
    # Deploy to the dev website.  Test it.
    fab dev most
    # Deploy to the production website.  Test it again.
    fab prod most
    # Commit the new dataset.
    git com -am 'Add newest dataset to website.'


# Where is the code and data?

There are (at least) two kinds of roundup code and data, dev and prod, i.e. development and production.
Dev code is code deployed to /www/dev.roundup.hms.harvard.edu/webapp
Prod code is code deployed to /www/roundup.hms.harvard.edu/webapp
Dev code by default uses the dev database.
Prod code by default uses the prod database.
Dev code can be made to use the prod database by setting various environment variables.  See examples in this file.
Prod code could run on the dev database, but why would you do that?
Prod data is located in /groups/public+cbi/sites/roundup and mysql.orchestra in the roundup database.
Dev data is located in /groups/public+cbi/sites/dev.roundup and dev.mysql.orchestra in the devroundup database.


# What are some of the concepts in roundup?

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


# WHAT ARE SOME OF THE FILES IN ROUNDUP?

config.py contains a lot of configuration that is specific to the dev or prod environments.

roundup_common.py contains code shared in common across other files and for abstracting some of the concepts in roundup.

roundup/dataset.py contains code to prepare a new dataset for the next release of roundup, by creating the directory structure, downloading source files, creating genomes from those sources, extracting metadata (genome names, go terms for genes, etc., etc., etc.) from source files, preparing jobs for computation, computing jobs (which run RSD on the pairs of genomes), and extracting more metadata (number of orthologs found, etc.).  

roundup_load.py contains code for loading a dataset into mysql.

roundup_db.py contains code to manage orthologs, genomes, etc., in the mysql database.  (Almost) everything having to do with SQL or mysql is in here.

roundup_util.py contains some code used by the web and other code.

orthquery.py and clustering.py are used by the web to generate phylogenetic profiles and other results of web queries.


