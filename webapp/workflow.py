

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


def exampleFunc(msg='hello world'):
    import time
    time.sleep(10)
    print msg
    

def testRunJobs(onGrid=True):
    jobs = [('workflow.exampleFunc', {'msg': 'test {}'.format(i)}) for i in range(2)]
    runJobs('test_workflow_jobs', jobs, lsfOptions=['-q shared_15m'], onGrid=onGrid)


def cleanTestRunJobs():
    dropDones('test_workflow_jobs')


###############
# JOB FUNCTIONS
###############

# the point of "jobs" functions is to run jobs on lsf.
# the functions keep track of which jobs are running and which are done.
# if a job fails or exits while running, it can be restarted.
# Only jobs which are not done or not already running will be restarted.

def runJobs(ns, jobs, names=None, lsfOptions=None, onGrid=True):
    '''
    ns: a namespace to keep jobs organized.
    jobs: a list of tuples of func and keyword arguments
    names: a optional list of names for the jobs, one for each job.  Useful if you want descriptive names in the dones table.
    lsfOptions: a list of lsf options.  '-J <job_name>' and '-o /dev/null' are appended to the list.
    onGrid: if True, jobs are distributed on lsf.  Otherwise, jobs are executed serially in the current process.  defaults to True.
    An lsf job is run for each job.
    Tracks which jobs are done and are already running, so runJobs() can be rerun without rerunning finished or running jobs.
    This is useful if jobs fail and need to be rerun.  Does that ever happen? ;-)
    '''
    names = names if names else ['job_{}'.format(i) for i in range(len(jobs))]
    lsfOptions = lsfOptions if lsfOptions else []
    if len(jobs) != len(set(names)):
        raise Exception('if names parameter is given, it must have a unique name for each job.')

    createDones(ns) # initialize the namespace, if needed.

    for job, name in zip(jobs, names):
        lsfJobName = '{}_{}'.format(ns, name)
        if isDone(ns, name):
            print 'already done job:', ns, name
        elif onGrid:
            if lsf.isJobNameOn(lsfJobName):
                print 'already running job:', ns, name
            else:
                print 'starting job:', ns, name
                func = 'workflow.runJob'
                kw = {'ns': ns, 'job': job, 'name': name}
                print lsfdispatch.dispatch(func, keywords=kw, lsfOptions=list(lsfOptions)+['-J', lsfJobName], devnull=True)
        else:
            runJob(ns, job, name)
            

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


###########
# DONES
###########

# "done" functions use the mysql database to track which jobs are done.
# Tracking jobs is useful to avoid rerunning jobs that are already done.
# pros: concurrency. fast even with millions of dones.
# cons: different mysql db for dev and prod, so must use the prod code on a prod dataset.

def isDone(ns, key):
    return getDonesStore(ns).exists(key)

 
def markDone(ns, key):
    return getDonesStore(ns).add(key)


def unmarkDone(ns, key):
    return getDonesStore(ns).remove(key)


def createDones(ns):
    getDonesStore(ns).create()


def dropDones(ns):
    getDonesStore(ns).drop()


def resetDones(ns):
    getDonesStore(ns).reset()


DONES_CACHE = {}
def getDonesStore(ns):
    '''
    ns: namespace for these dones.  will become part of a table name, so use words, numbers, and underscores only
    '''
    if ns not in DONES_CACHE:
        DONES_CACHE[ns] = kvstore.KStore(util.ClosingFactoryCM(config.openDbConn), ns='workflow_dones_{}'.format(ns))
    return DONES_CACHE[ns]
    
