


## Introduction


What is Roundup?  

- An automated pipeline for downloading genomes, computing orthologs
  using the Reciprocal Shortest Distance (RSD) algorithm, and loading the
  results into the database used by the website.
- A database of orthologous proteins among many organisms and information
  about those proteins and organisms.
- A website that queries the database to return phylogenetic
  profiles and other multi-genome analyses of the orthology data.


## Roundup Datasets

A dataset consists of:

- A set of genomes, downloaded from UniProt.
- Information about those genomes and the proteins within them, downloaded from UniProt, NCBI and Gene Ontology.
- Orthologs computed using the genomes.
- Download files containing the orthologs and genomes.

Roundup dataset are created periodically, given a version, and archived, so
scientists using Roundup can base their results on a well-defined and
reproducible set of information.

As of 2013, creation of a dataset required approximately 100 core-years.
This process occurs on the Harvard Medical School computational cluster,
Orchestra, which contains over 4000 CPU cores.  Using LSF to distribute and
parallelize the computation, allows a dataset to be produced in approximately 2
months.

Making a new dataset entails downloading the sources of the dataset from the
web, computing orthologs, loading the data into the database for the website,
and updating the website to point to the new dataset.

Each dataset has its own code deployment.  This allows the computation to
run undisturbed during the months it runs, even while the website code is 
being updated.  Previous versions of Roundup ran on a single codebase, which
would sometimes lead to cataclysmic LSF job failure when a bug was introduced
into the code while changes were being made.

### How to make a new dataset and release it on the website

Download the latest code from github:

    git clone git@github.com:walllab/roundup.git

Acquire a copy of the `secrets/` directory from a Roundup developer.  This
directory contains files with MySQL and Django credentials that vary by
deployment environment and should NEVER be version controlled.

First, figure out the number of the next dataset.  If the current dataset is
release 4, the next dataset is release 5.  Then add various values to your
environment (for the convenience of writing commands):

    export DSID=5
    export DSDIR=/groups/public+cbi/sites/roundup/datasets/$DSID
    # The previous dataset is presumably one less than this dataset
    export PREV_DS=/groups/public+cbi/sites/roundup/datasets/`dc -e "$DSID 1 - p"`
    export DSCODE=/groups/public+cbi/sites/roundup/code/$DSID
    echo $DSID $DSDIR $DSCODE

Fabric (http://fabfile.org) is used to copy code to the production host
(orchestra.med.harvard.edu), configure the application, create a virtualenv,
etc.  Deploy code for a new dataset from a Roundup git repository:
    
    cd ~/work/roundup
    fab ds:$DSID full

If your username on localhost is different from the username you use to log in
to the production host (orchestra.med.harvard.edu), then you should set the
environment variable `ROUNDUP_DEPLOY_USER` equal to the remote host username,
e.g. `ROUNDUP_DEPLOY_USER=td23`.  The fabfile will log in using this name if
it is defined.  Also, you should be set up for passwordless login to the host
using an ssh keypair.

Once the code is deployed and configured, log in to the remote host (orchestra)
and run the dataset workflow to compute the orthologs:

    cd $DSCODE && time venv/bin/python app/roundup/dataset.py workflow $DSDIR $PREV_DS

This last command actually does the following things:

- Creates a directory for the dataset and several subdirectories.
- Creates files containing dataset metadata.
- Creates database tables to track the progress of the workflow and statistics
  about the dataset and computation.
- Downloads source files from UniProt, NCBI and Gene Ontology.
- Extracts taxonomy, gene ontology, and other metadata about genomes and genes
  from the source files.
- Compiles a list of complete genomes to be used in the dataset.
- Creates FASTA protein files, formatted for use with BLAST, for each genome.
- Prepares thousands of LSF jobs, each of which will run thousands of RSD
  computations, one for each pair of genomes assigned to the job.
- Computes the jobs on the computational cluster.
- Makes a Change Log, which tracks which genomes have been added and removed
  from the previous dataset.
- Extracts and preserves statistics about the size of the dataset and the
  performance of the computation.
- Compiles orthologs and genomes into downloadable archive files.

The dataset workflow command will need to be periodically rerun as the
computation proceeds.  It is designed to fail if any individual step does
not succeed, and the computation of orthologs step will not "succeed" until
all ortholog jobs have completed successfully.  When jobs fail (and they will
fail because of transient filesystem, database, and networking errors),
rerunning the workflow will automatically detect failed jobs and rerun them.

You can manually track the progress of the workflow on LSF by seeing how
many jobs you have remaining:

    bjobs -w | grep 'roundup' | wc -l

Once all the LSF jobs have successfully completed, the workflow will proceed
with the remaining steps detailed above, once it is run again.

Once the dataset workflow is finished, it is time to load the orthologs into
the database.  First, use the Orchestra phpMyAdmin
(https://orchestra.med.harvard.edu/phpMyAdmin/index.php) to get a sense of the
size of the tables you will be inserting, by comparing the size of the previous
dataset to this one.  Hint: use the number of pairs to normalize the previous
dataset size.

Then, assuming the database has enough free space, load the orthologs, etc.:

    cd $DSCODE && time venv/bin/python app/roundup_load.py workflow $DSDIR

Finally, edit `fabfile.py` to publish the new dataset to the website:

    # Prepend the dataset dir to `config.archive_datasets` for the `dev` and `prod` tasks.
    vim fabfile.py
    # Deploy to the dev website.  Test it.
    fab dev most
    # Deploy to the production website.  Test it again.
    fab prod most
    # Commit the new dataset.
    git com -am 'Add newest dataset to website.'

When you are satisfied that the new dataset is functional, you should drop the
previous release from the database to save space.  Or perhaps you should drop
the antepenultimate release if you want to keep the previous release around to
easily roll back to.  First, figure out the number of the release you want to
drop.  Then:

```
cd $DSCODE && time venv/bin/python -c "import roundup_db
release = '1'
roundup_db.dropRelease(release)
roundup_db.dropReleaseResults(release)
"
```

### Run a test computation using only a few genomes in a dataset

When Roundup was less automated, there used to be a way to run a computation
using only a small set of genomes.  You can still do this, but you need to
manually break the workflow (perhaps by inserting a `sys.exit()` into the
workflow code) before the 'prepare_jobs' step.  Then manually set the genomes
to a few small genomes and then continue the workflow.  Here is how to manually
set the genomes:

```
cd $DSCODE && time venv/bin/python -c "import roundup.dataset
ds = '$DSDIR'
# Old UniProt organism names.  Now we use NCBI Taxon Ids.
# genomes = 'MYCGE MYCGF MYCGH MYCH1 MYCH2 MYCH7 MYCHH MYCHJ MYCHP'.split()
genomes = '9606 10090 7227'.split() # These are big genomes (human, mouse and fly).  Use small ones like Mycoplasma genitalium.
print genomes
roundup.dataset.setGenomes(ds, genomes) # this is the key step.  settting the genomes manually.
roundup.dataset.prepare_jobs(ds, numJobs=10) # use fewer jobs than the default 4000.
```


### How to build a Quest for Orthologs Dataset

Creating a QfO dataset is very similar to a normal dataset, except use a 
different source for genomes and it does not get loaded into the database.

Here is how the most recent Quest for Orthologs dataset, qfo_2013_04, was
created. 

Deploy the code for the first time, creating a virtual environment:

    cd ~work/roundup
    # Do a full deployment of code from scratch, including creating a virtual environment and installing requirements.
    fab ds:qfo_2013_04 full

Deploying the code all the rest of the time:

    # Alternatively, after creating the virtualenv, just deploy the code and config.
    fab ds:qfo_2013_04 most

On an orchestra compute node, run the quest for orthologs workflow.  Currently
this will "fail" when launching jobs on orchestra to format genomes or compute
orthologs.  This is fine.  Just wait for the lsf jobs to finish and rerun the
workflow and it will pick up where it left off:

    cd /groups/public+cbi/sites/roundup/code/qfo_2013_04
    ROUNDUP_MYSQL_CREDS_FROM_CNF=True venv/bin/python app/quest.py workflow /groups/public+cbi/sites/roundup/datasets/qfo_2013_04


## Where to look when errors happen?

The Apache access and error log files for the websites are available using the `httpdlogtail` and `httpdlogless` commands:

    httpdlogtail roundup
    httpdlogtail roundup error
    httpdlogtail dev.roundup
    httpdlogtail dev.roundup error

Like so many things, the location of the application log file is defined in
`fabfile.py`.  For production, this location is
`/www/roundup.hms.harvard.edu/log/app.log`.  When the python code imports the
`logging` and uses it to log messages and exceptions, they end up here.  All
errors and exceptions are also emailed to the list of addresses in `config.py`
assigned to the variable `LOG_TO_ADDRS`.

There is another log file, used by `app/passenger_wsgi.py`, which can sometimes
capture error that occur after Apache and before the application, when the
Phusion Passenger + Django stack is malfunctioning.  The location of this
file is `~/passenger_wsgi.log`.  It should log to the directory of the person
who owns the `passenger_wsg.py` file. 

On Orchestra, the filesystems on the web hosts are different from the
filesystems on the login hosts or cluster nodes.   Sometimes it is useful to
`ssh cornet` or `ssh tuba` to see if something that is working from a login
node also works from a web node.


## What are the development and production environments?

Roundup has a separate web domain and MySQL database for development and
production.  This allows one to develop and test changes to the website or
database in a non-critical environment before deploying to production.  

The MySQL credentials (username, password, server host and database name)
are defined in `secrets/prod.py` and `secrets/dev.py`.  During deployment,
one of these files is copied to the deployment root as `app/secrets.py`.  The
development host is `dev.mysql.orchestra` and the prod host is
`mysql.orchestra`.  The dev and prod databases are `devroundup` and `roundup`,
respectively.

The file `fabfile.py` defines the current dataset used by the deployment
environment and where the code is deployed.  As of 2013/08, these are
`/groups/public+cbi/sites/roundup/datasets/4` and
`/www/roundup.hms.harvard.edu` for production.

Note that by adjusting the settings in the secrets files and
fabfile.py, one can test code on the development website using the production
database.  This can be useful to do before rolling changes to production.


## What are some of the concepts in roundup?

GENOMES: A genome refers to several things: a id, like HUMAN or MYCGE;  a
directory (named after the id) that contains fasta files and blast-formatted
indices.  For historical reasons genomes are sometimes referred to as qdb and
sdb, which stand for query database and subject database, where database means
genome.

GENES: genes are sequences from the fasta files of the genomes.  Each gene has
an id.  These ids are sometimes referred to as qid or sid (query id, subject
id).

PAIRS: RSD computes orthologs for a pair of genomes.  A pair is a tuple of
genome ids.  The lexicographically smaller id is always the first in the tuple.
In a dataset, all pairs for all genomes are computed.  If there are n genomes,
there are n(n-1)/2 pairs.

PARAMS: RSD computes orthologs for a pair of genomes, a divergence threshold
and an evalue threshold.  These collectively are the parameters of RSD and are
referred to as params.  They are a tuple of (qdb, sdb, div, evalue).

ORTHOLOGS: a list of orthologs.  an ortholog is a gene from a genome, a gene
from another genome, and the maximum-likelihood distance between the genes, a
measure of similarity.  orthologs are computed using rsd for each pair of
genomes combined with 3 divergences (0.2, 0.5, 0.8) and 4 evalues (1e-20,
1e-15, 1e-10, 1e-5).  Therefore for every pair of genomes there are 12 sets of
params and 12 corresponding lists of orthologs.

ORTHDATA: is a tuple of params and the associated orthologs.  These are
persisted to files, many orthdatas per file, in the orthologs directory of a
dataset.

QUERY and SUBJECT: RSD takes as input two genomes.  The first one is called the
query genome or qdb, the second is called the subject genome or sdb.  In
Roundup, the query genome is always chosen so that its id is lexicographically
(that's a fancy way of saying alphabetically) smaller than the subject genome
id.

DATASET: A dataset contains all the data for a specific release of roundup: the
genomes, the orthologs computed for each set of params for all pairs of
genomes, the source files, the metadata extracted from the source files (like
gene names, the number of genomes), and other metadata (like the number of
orthologs).  The dataset also stores information about the computation of
orthologs.  It splits the computation into some number of jobs and tracks which
jobs are complete using a "dones" table in the database.

JOBS: are directories in a dataset which organize how orthologs are computed.
All pairs for the dataset are split among the jobs.  For each job, a job is run
on LSF, which computes orthologs for the pairs assigned to that job and then
saves the orthologs (as orthDatas) to a file in the orthologs dir.

DATABASE: most of the roundup website uses data from a mysql database.  Tables
for the dataset are loaded with data from a dataset.  

RELEASE: Each dataset is called a release on the website and in the code.
Releases are named with a number.  Release 1 is from May 2010.  And so on.


## What are some of the files in Roundup?

`fabfile.py` is a Fabric script that manages deployment of Roundup to environments like production (prod), development (dev), and datasets.  It also creates python virtual environments there, generates `deployenv.py` and `webdeployenv.py` files, and copies a secrets file to `secrets.py`.

`requirements.txt` is the Pip requirements file used determine what packages (and what versions) are installed in the virtualenv of a deployment.

`secrets/` is the directory that contains `secrets/prod.py`, etc., which define the MySQL credentials and Django secrets for different deployment environments.

`deploy/` contains template files that are filled out when `fabfile.py` is run and then copied to their destination on the remote host.  As of 2013/08, only `.htaccess_template` is there.

`app/config.py` contains a lot of configuration that is used by the website and workflow.

`app/webconfig.py` contains configuration that is specific to the website.

`app/deployenv.py` is a file generated by running `fabfile.py` (look for it on the remote host) that contains values that vary by deployment environment.  This file is mostly used by `config.py`.

`app/webdeployenv.py` is another autogenerated file that contains values used specifically by the website.

`app/roundup_common.py` contains code shared in common across other files and for abstracting some of the concepts in roundup.

`app/roundup/dataset.py` contains code to prepare a new dataset for the next release of roundup, by creating the directory structure, downloading source files, creating genomes from those sources, extracting metadata (genome names, go terms for genes, etc., etc., etc.) from source files, preparing jobs for computation, computing jobs (which run RSD on the pairs of genomes), and extracting more metadata (number of orthologs found, etc.).  

`app/roundup_load.py` contains code for loading a dataset into mysql.

`app/roundup_db.py` contains code to manage orthologs, genomes, etc., in the mysql database.  (Almost) everything having to do with SQL or mysql is in here.

`app/roundup_util.py` contains some code used by the web and other code.

`app/orthquery.py` and `app/clustering.py` are used by the web to generate phylogenetic profiles and other results of web queries.

`app/home` contains the Django views and models files.

`app/templates` contains the Django template files.



