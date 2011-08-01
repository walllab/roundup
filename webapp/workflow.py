

'''
Functions for distributing jobs on lsf, keeping track of which jobs are complete, and which are running.
This allows one to restart a failed workflow and pick up where one left off.

Functions for storing what is done.  Useful even when not distributing jobs on lsf, for example, when running a long job that has many serial steps.
'''

import kvstore
import util
import config
import LSF
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
    

def testRunJobs():
    jobs = [('workflow.exampleFunc', {'msg': 'test {}'.format(i)}) for i in range(2)]
    runJobs('test_workflow_jobs', jobs, lsfOptions=['-q shared_15m'])


def cleanTestRunJobs():
    dropDones('test_workflow_jobs')


def testRunTasks():
    tasks = [('workflow.exampleFunc', {'msg': 'test {}'.format(i)}) for i in range(10)]
    runTasks('test_workflow_tasks', tasks, 2, lsfOptions=['-q shared_15m'])


def cleanTestRunTasks():
    dropDones('test_workflow_tasks')


###############
# JOB FUNCTIONS
###############

def runJobs(ns, jobs, names=None, lsfOptions=None):
    '''
    ns: a namespace to keep jobs organized.
    jobs: a list of tuples of func and keyword arguments
    names: a optional list of names for the jobs, one for each job.  Useful if you want descriptive names in the dones table.
    lsfOptions: a list of lsf options.  '-J <job_name>' and '-o /dev/null' are appended to the list.
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
        elif LSF.isJobNameRunning(lsfJobName):
            print 'already running job:', ns, name
        else:
            print 'starting job:', ns, name
            func = 'workflow.runJob'
            kw = {'ns': ns, 'job': job, 'name': name}
            lsfOptions += [' -o /dev/null', '-J {}'.format(lsfJobName)]
            print lsfdispatch.dispatch(func, keywords=kw, lsfOptions=lsfOptions)


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


#################
# TASKS FUNCTIONS
#################

def runTasks(ns, tasks, numJobs, taskNames=None, lsfOptions=None):
    '''
    ns: a namespace to keep tasks organized.
    tasks: a list of tuples of func and keyword arguments
    taskNames: a optional list of names for the tasks, one for each task.  Useful if you want descriptive names in the dones table.
    numJobs: break the tasks into up to this many equal sized groups.  fewer if there less tasks than numJobs.
    lsfOptions: a list of lsf options.  '-J <job_name>' and '-o /dev/null' are appended to the list.
    Split tasks into groups.  Each group of tasks is run as an lsf job that runs each task in the group.
    Tracks which jobs and tasks are done and are already running, so runTasks() can be rerun without rerunning finished or running tasks and jobs.
    This is useful if jobs fail and need to be rerun.  Does that ever happen? ;-)
    '''
    createDones(ns) # initialize the namespace, if needed.
    names = taskNames if taskNames is not None else ['task_{}'.format(i) for i in range(len(tasks))]
    if len(tasks) != len(set(names)):
        raise Exception('if taskNames parameter is given, it must have a unique name for each task.')
    lsfOptions = lsfOptions if lsfOptions else []
    for i, zippedGroup in enumerate(util.splitIntoN(zip(tasks, names), numJobs)):
        groupTasks, groupNames = zip(*zippedGroup) # unzip the tasks and names
        job = 'taskjob_{}'.format(i)
        lsfJobName = '{}_{}'.format(ns, job)
        if isDone(ns, job):
            print 'already done job:', ns, job
        elif LSF.isJobNameRunning(lsfJobName):
            print 'already running job:', ns, job
        else:
            print 'starting job:', ns, job
            func = 'workflow.runTasksJob'
            kw = {'ns': ns, 'job': job, 'tasks': groupTasks, 'names': groupNames}
            lsfOptions += [' -o /dev/null', '-J {}'.format(lsfJobName)]
            print lsfdispatch.dispatch(func, keywords=kw, lsfOptions=lsfOptions)


def runTasksJob(ns, job, tasks, names):
    '''
    ns: a namespace to keep tasks organized.
    job: a name to track if the job is done.  should be unique in the namespace.
    a job runs one or more tasks.  the job will not run if it is done already.
    '''
    if not isDone(ns, job):
        for task, name in zip(tasks, names):
            runTask(ns, task, name)
        markDone(ns, job)


def runTask(ns, task, name):
    '''
    ns: a namespace to keep tasks organized.
    task: a tuple of a fully qualified function name and keywords arguments.
    name: a name for the task, which should be unique in the namespace.
    the task will not run if it is done already.
    '''
    
    func, kw = task
    if not isDone(ns, name):
        util.dispatch(func, keywords=kw)
        markDone(ns, name)

    

###########
# DONES
###########
# isDone uses the mysql database.  Used for concurrent execution of jobs, pairs, and other large numbers of dones.
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
    getDonesStore(ns).drop().create()


DONES_CACHE = {}
def getDonesStore(ns):
    '''
    ns: namespace for these dones.  will become part of a table name, so use words, numbers, and underscores only
    '''
    if not DONES_CACHE:
        DONES_CACHE[ns] = kvstore.KStore(util.ClosingFactoryCM(config.openDbConn), ns='workflow_dones_{}'.format(ns))
    return DONES_CACHE[ns]
    
