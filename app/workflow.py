
'''
Functions for distributing jobs on lsf, keeping track of which jobs are complete, and which are running.
This allows one to restart a failed workflow and pick up where one left off.

Functions for storing what is done.  Useful even when not distributing jobs on lsf, for example, when running a long job that has many serial steps.
'''

import argparse
import functools
import os

import cliutil
import dones
import kvstore
import lsf
import mysqlutil
import util


###################################
# ENVIRONMENT VARIABLE DEPENDENCIES

DB_URL = os.environ['WORKFLOW_MYSQL_URL']


#########
# TESTING

import time

# cd /www/dev.roundup.hms.harvard.edu/webapp && python -c 'import workflow; workflow.testWorkflowSync()'
# cd /www/dev.roundup.hms.harvard.edu/webapp && python -c 'import workflow; workflow.testWorkflowAsync()'
# cd /www/dev.roundup.hms.harvard.edu/webapp && python -c 'import workflow; workflow.testCleanJobs()'

TEST_NS = 'test_workflow'

def testWorkflowSync():
    # start: no jobs are done.
    assert not testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    # run jobs with default names, asserting that they are done and 
    # jobs with non-default names are not done.
    assert testRunJobsSync()
    assert testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    # run jobs with non-default names, asserting that they are done
    assert testRunJobsSync(useNames=True)
    assert testJobsAllDone(useNames=True)
    # run Jobs with default and non-default names.
    # they should not be rerun.
    assert testRunJobsSync()
    assert testRunJobsSync(useNames=True)
    # clean up tables and make sure jobs are now not done.
    testCleanJobs()
    assert not testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    # finally, clean up tables.
    testCleanJobs()


def testWorkflowAsync(wait=60):
    '''
    wait: how long (in seconds) to wait before asserting that all jobs are
    done.  tune this so that lsf has time to finish all the jobs.
    '''
    # start: no jobs are done.
    assert not testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    # run jobs with default names.
    # assert that they are not yet done (since they are launching on the grid.)
    # Also jobs with non-default names are not done.
    assert not testRunJobsAsync()
    assert not testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    # wait for jobs to finish and assert that they are all done.
    time.sleep(wait)
    assert testJobsAllDone()
    # run jobs with non-default names
    # assert they are not yet done, since they just launched on lsf.
    assert not testRunJobsAsync(useNames=True)
    assert not testJobsAllDone(useNames=True)
    # wait for jobs to finish and assert that they are all done.
    time.sleep(wait)
    assert testJobsAllDone(useNames=True)
    # run Jobs with default and non-default names.
    # they should not be rerun and should return true, since
    # the jobs should be all done.
    assert testRunJobsAsync()
    assert testRunJobsAsync(useNames=True)
    # clean up tables and make sure jobs are now not done.
    testCleanJobs()
    assert not testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    # finally, clean up tables.
    testCleanJobs()


def testCleanJobs():
    return getDones(TEST_NS).clean() 


def testJobsAndNames(useNames=False):
    '''
    useNames: if true, names are different from the default job names, which
    tests the path of a user giving jobs their own names.
    '''
    numJobs = 2
    jobs = [('workflow.exampleFunc', {'msg': 'test {}'.format(i)}) for i in range(numJobs)]
    names = ['lovely_{}'.format(i) for i in range(numJobs)] if useNames else None
    return jobs, names


def testRunJobsSync(useNames=False):
    jobs, names = testJobsAndNames(useNames)
    return runJobsSyncLocal(TEST_NS, jobs, names)


def testRunJobsAsync(useNames=False):
    jobs, names = testJobsAndNames(useNames)
    return runJobsAsyncGrid(TEST_NS, jobs, names, lsf_options=['-q', 'short', '-W', '15'])


def testJobsAllDone(useNames=False):
    jobs, names = testJobsAndNames(useNames)
    return jobsAllDone(TEST_NS, jobs, names)


def testJobNamesAllDone():
    jobs, names = testJobsAndNames(useNames=True)
    return jobNamesAllDone(TEST_NS, names)


def exampleFunc(msg='hello world', secs=1):
    time.sleep(secs)
    print msg
    

###############
# JOB FUNCTIONS
###############

# the point of "jobs" functions is to run jobs on lsf (or locally).
# the functions keep track of which jobs are running and which are done.
# if a job fails or exits while running, it can be restarted.
# Only jobs which are not done or not already running will be restarted.

def runJobsSyncLocal(ns, jobs, names=None):
    '''
    ns: a namespace to keep jobs organized.
    jobs: a list of tuples of func and keyword arguments
    names: a optional list of names for the jobs.  There should be one name per job.  Names should be unique
      within the namespace.  Names are submitted as part of an lsf job name (-J option), so avoid funny characters.
      Names are useful if you want descriptive names in the dones table or on lsf.

    Run jobs locally and syncronously.  Return when all jobs are done (or if there is an exception).
    Done jobs will not be run.  This allows running multiple times without
    redoing done jobs, which can be useful when one or more jobs fail.
    If jobs fail (does that ever happen?) this function can be rerun and it
    will only rerun the not done jobs.
    Returns: True iff all jobs are done.
    '''
    names = _makeJobNames(jobs, names)
    if len(jobs) != len(set(names)):
        raise Exception('if names parameter is given, it must have a unique name for each job.')

    for job, name in zip(jobs, names):
        if getDones(ns).done(name):
            print 'job already done. ns={}, name={}'.format(ns, name)
        else:
            _runJob(ns, job, name)

    return jobsAllDone(ns, jobs, names)


def runJobsAsyncGrid(ns, jobs, names=None, lsf_options=None, devnull=False):
    '''
    ns: a namespace to keep jobs organized.
    jobs: a list of tuples of func and keyword arguments
    names: a optional list of names for the jobs.  There should be one name per job.  Names should be unique
      within the namespace.  Names are submitted as part of an lsf job name (-J option), so avoid funny characters.
      Names are useful if you want descriptive names in the dones table or on lsf.
    lsf_options: a list of lsf options.  '-J <job_name>' and '-o /dev/null' are appended to the list by default.
    devnull: if False, '-o /dev/null' is not appended to the lsf options.

    Run jobs asynchronously on lsf.  I.e. Submit them to LSF and then return.
    Track which jobs are done or running.  
    To see when all jobs are finished, poll with this function or jobsAllDone().
    If jobs fail (does that ever happen?) this function can be rerun to
    resubmit only the incomplete jobs that are not currently running.
    Returns: True iff all jobs are done.
    '''
    names = _makeJobNames(jobs, names)
    lsf_options = lsf_options if lsf_options else []
    if len(jobs) != len(set(names)):
        raise Exception('if names parameter is given, it must have a unique name for each job.')
    lsf_job_names = ['{}_{}'.format(ns, name) for name in names]
    onJobNames = set(lsf.getOnJobNames())
    
    for job, name, lsf_job_name in zip(jobs, names, lsf_job_names):
        if getDones(ns).done(name):
            print 'job already done. ns={}, name={}'.format(ns, name)
        elif lsf_job_name in onJobNames: 
                print 'job already running. ns={}, name={}'.format(ns, name)
        else:
            print 'starting job. ns={}, name={}'.format(ns, name)
            jobid = bsub_runjob(ns, job, name, lsf_options, lsf_job_name,
                                devnull=devnull)
            print 'lsf job id:', jobid

    return jobsAllDone(ns, jobs, names)


def reset(ns):
    '''
    Unmark all the jobs currently marked done.
    '''
    getDones(ns).clean()


def jobsAllDone(ns, jobs, names=None):
    '''
    Returns True iff all the jobs in the namespace are marked done.
    '''
    return getDones(ns).all_done(_makeJobNames(jobs, names))
    

def jobNamesAllDone(ns, names):
    '''
    Returns True iff all the names in the namespace are marked done.
    This function is useful if you do not want to pass all the jobs as a parameter,
    when all you need are their names.
    '''
    return getDones(ns).all_done(names)
    

def _runJob(ns, job, name):
    '''
    ns: a namespace to keep jobs organized.
    job: a tuple of a fully qualified function name and keywords arguments.
    name: a name for the job, which should be unique in the namespace.
    Run a single job synchronously and locally.  Used by the runJobs*()
    functions.
    Will not run if it is done already.
    '''
    
    func, kw = job
    if not getDones(ns).done(name):
        util.dispatch(func, keywords=kw)
        getDones(ns).mark(name)


def _makeJobNames(jobs, names=None):
    '''
    jobs: a list of jobs
    names: if not None, names must be as long as jobs.
    Returns: names, if names is given, otherwise a list of simple names is, one
    for each job.
    '''
    names = names if names else ['job_{}'.format(i) for i in range(len(jobs))]
    assert len(names) == len(jobs)
    return names


###########
# DONES
###########

# "done" functions use the mysql database to track which jobs are done.
# Tracking jobs is useful to avoid rerunning jobs that are already done.
# pros: concurrency. fast even with millions of dones.
# cons: different mysql db for dev and prod, so must use the prod code on a prod dataset.

DONES_CACHE = {}
def getDones(ns):
    if ns not in DONES_CACHE:
        # create a contextmanager that opens a db connection and
        # closes it when exiting the context.
        conn_cm = util.ClosingFactoryCM(functools.partial(mysqlutil.open_url,
                                                          DB_URL, retries=1,
                                                          sleep=1.0))
        kns = 'workflow_dones_{}'.format(ns)
        k = kvstore.KStore(conn_cm, ns=kns)
        DONES_CACHE[ns] = dones.Dones(k)
    return DONES_CACHE[ns]


########################
# COMMAND LINE INTERFACE


def cli_runjob(args):
    # function args and kws
    fargs, fkws = cliutil.params_from_file(args.params)
    _runJob(*fargs, **fkws)


def bsub_runjob(ns, job, name, lsf_options, lsf_job_name, devnull=True):
    lsf_options = list(lsf_options) + ['-J', lsf_job_name]
    if devnull:
        lsf_options = ['-o', '/dev/null'] + lsf_options
    filename = cliutil.params_to_file(kws={'ns': ns, 'job': job, 'name': name})
    cmd = cliutil.script_argv(__file__) + ['runjob', '--params', filename]
    jobid = lsf.bsub(cmd, lsf_options)
    return jobid


def main():
    parser = argparse.ArgumentParser(description='')
    subparsers = parser.add_subparsers(dest='action')

    # do_orthology_query
    subparser = subparsers.add_parser('runjob')
    subparser.add_argument('--params', required=True, help='A file of '
                           'serialized parameters.')
    subparser.set_defaults(func=cli_runjob)

    # parse command line arguments and invoke the appropriate handler.
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()



