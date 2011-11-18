

'''
Functions for distributing jobs on lsf, keeping track of which jobs are complete, and which are running.
This allows one to restart a failed workflow and pick up where one left off.

Functions for storing what is done.  Useful even when not distributing jobs on lsf, for example, when running a long job that has many serial steps.
'''

import kvstore
import util
import config
import lsf
import lsfdispatch


#########
# TESTING
#########

# cd /www/dev.roundup.hms.harvard.edu/webapp && python -c 'import workflow; workflow.testRunTasks()'
# cd /www/dev.roundup.hms.harvard.edu/webapp && python -c 'import workflow; workflow.cleanTestRunTasks()'

TEST_NS = 'test_workflow'

def testWorkflow(onGrid=False):
    assert not testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    assert testRunJobs(onGrid=onGrid)
    assert testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    assert testRunJobs(onGrid=onGrid)
    assert testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    assert testRunJobs(onGrid=onGrid, useNames=True)
    assert testJobsAllDone()
    assert testJobsAllDone(useNames=True)
    assert testRunJobs(onGrid=onGrid)
    testCleanJobs()
    assert not testJobsAllDone()
    assert not testJobsAllDone(useNames=True)
    testCleanJobs()
    unmarkDone(TEST_NS, 'foo')
    unmarkDone(TEST_NS, 'foo')
    testCleanJobs()

    
def testJobsAndNames(useNames=False):
    numJobs = 2
    jobs = [('workflow.exampleFunc', {'msg': 'test {}'.format(i)}) for i in range(numJobs)]
    names = ['lovely_{}'.format(i) for i in range(numJobs)] if useNames else None
    return jobs, names


def testRunJobs(onGrid=False, useNames=False):
    jobs, names = testJobsAndNames(useNames)
    return runJobs(TEST_NS, jobs, names, lsfOptions=['-q', 'shared_15m'], onGrid=onGrid)


def testCleanJobs():
    return dropDones(TEST_NS)


def testJobsAllDone(useNames=False):
    jobs, names = testJobsAndNames(useNames)
    return jobsAllDone(TEST_NS, jobs, names)


def testJobNamesAllDone():
    jobs, names = testJobsAndNames(useNames=True)
    return jobNamesAllDone(TEST_NS, names)


def exampleFunc(msg='hello world', secs=1):
    import time
    time.sleep(secs)
    print msg
    

###############
# JOB FUNCTIONS
###############

# the point of "jobs" functions is to run jobs on lsf.
# the functions keep track of which jobs are running and which are done.
# if a job fails or exits while running, it can be restarted.
# Only jobs which are not done or not already running will be restarted.

def runJobs(ns, jobs, names=None, lsfOptions=None, onGrid=False, devnull=False):
    '''
    ns: a namespace to keep jobs organized.
    jobs: a list of tuples of func and keyword arguments
    names: a optional list of names for the jobs.  There should be one name per job.  Names should be unique
      within the namespace.  Names are submitted as part of an lsf job name (-J option), so avoid funny characters.
      Names are useful if you want descriptive names in the dones table or on lsf.
    lsfOptions: a list of lsf options.  '-J <job_name>' and '-o /dev/null' are appended to the list by default.
    onGrid: if True, jobs are distributed on lsf.  Otherwise, jobs are executed serially in the current process.  defaults to True.
    devnull: if False, '-o /dev/null' is not appended to the lsf options.
    Run jobs, either on lsf or locally.  Done jobs will not be run.  Jobs already running on lsf will not be resubmitted.
    Otherwise the job will be run or submitted to lsf to be run.
    Tracks which jobs are done and are already running, so runJobs() can be rerun without rerunning finished or running jobs.
    If jobs fail (does that ever happen?) this function can be rerun to resubmit only the incomplete jobs that are not running.
    Returns: True iff all jobs are done.
    '''
    names = makeJobNames(jobs, names)
    lsfOptions = lsfOptions if lsfOptions else []
    if len(jobs) != len(set(names)):
        raise Exception('if names parameter is given, it must have a unique name for each job.')
    lsfJobNames = ['{}_{}'.format(ns, name) for name in names]

    # what job names are currently on lsf.
    if onGrid:
        onJobNames = set(lsf.getOnJobNames())
    
    for job, name, lsfJobName in zip(jobs, names, lsfJobNames):
        if isDone(ns, name):
            print 'job already done. ns={}, name={}'.format(ns, name)
        elif onGrid: # run async on grid
            if lsfJobName in onJobNames: # lsf.isJobNameOn(lsfJobName):
                print 'job already running. ns={}, name={}'.format(ns, name)
            else:
                print 'starting job. ns={}, name={}'.format(ns, name)
                func = 'workflow.runJob'
                kw = {'ns': ns, 'job': job, 'name': name}
                options = list(lsfOptions)+['-J', lsfJobName]
                print 'lsf job id:', lsfdispatch.dispatch(func, keywords=kw, lsfOptions=options, devnull=devnull)
        else: # run sync on
            runJob(ns, job, name)

    return jobsAllDone(ns, jobs, names)


def runJob(ns, job, name):
    '''
    ns: a namespace to keep jobs organized.
    job: a tuple of a fully qualified function name and keywords arguments.
    name: a name for the job, which should be unique in the namespace.
    the job will not run if it is done already.
    '''
    
    func, kw = job
    if not isDone(ns, name):
        util.dispatch(func, keywords=kw)
        markDone(ns, name)


def makeJobNames(jobs, names=None):
    '''
    jobs: a list of jobs
    names: if not None, names must be as long as jobs.
    Returns: names, if names is given, otherwise a list of simple names is, one
    for each job.
    '''
    names = names if names else ['job_{}'.format(i) for i in range(len(jobs))]
    assert len(names) == len(jobs)
    return names


def jobsAllDone(ns, jobs, names=None):
    '''
    Returns True iff all the jobs in the namespace are marked done.
    '''
    return allDone(ns, makeJobNames(jobs, names))
    

def jobNamesAllDone(ns, names):
    '''
    Returns True iff all the names in the namespace are marked done.
    This function is useful if you do not want to pass all the jobs as a parameter,
    when all you need are their names.
    '''
    return allDone(ns, names)
    

###########
# DONES
###########

# "done" functions use the mysql database to track which jobs are done.
# Tracking jobs is useful to avoid rerunning jobs that are already done.
# pros: concurrency. fast even with millions of dones.
# cons: different mysql db for dev and prod, so must use the prod code on a prod dataset.

def allDone(ns, keys):
    '''
    Return: True iff all the keys are done.
    '''
    # implementation note: use generator b/c any/all are short-circuit functions
    return all(isDone(ns, key) for key in keys)


def anyDone(ns, keys):
    '''
    Return: True iff any of the keys are done.
    '''
    # implementation note: use generator b/c any/all are short-circuit functions
    return any(isDone(ns, key) for key in keys)


def isDone(ns, key):
    '''
    Return: True iff the key is done.
    '''
    return getDonesStore(ns).exists(key)

 
def markDone(ns, key):
    return getDonesStore(ns).add(key)


def unmarkDone(ns, key):
    return getDonesStore(ns).remove(key)


# def createDones(ns):
#     getDonesStore(ns).create()


def dropDones(ns):
    getDonesStore(ns).drop()
    del DONES_CACHE[ns]


def resetDones(ns):
    getDonesStore(ns).reset()


DONES_CACHE = {}
def getDonesStore(ns):
    '''
    ns: namespace for these dones.  will become part of a table name, so use letters, numbers, and underscores only
    '''
    if ns not in DONES_CACHE:
        DONES_CACHE[ns] = kvstore.KStore(util.ClosingFactoryCM(config.openDbConn), ns='workflow_dones_{}'.format(ns))
        DONES_CACHE[ns].create()
    return DONES_CACHE[ns]
    
