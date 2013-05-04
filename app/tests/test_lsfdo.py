
import os
import time

import lsfdo


TEST_NS = 'test_lsfdo'

def setup():
    # ensure that lsfdo can import test_lsfdo.example_func
    os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))


def example_func(msg, msg2=None):
    '''
    Used to test running a python function on lsf.
    '''
    print msg
    if msg2 is not None:
        print msg2


def get_cmd_tasks():
    '''
    Return two CmdTask objects for testing.
    '''
    tasks = [
        lsfdo.CmdTask(name='test_cmd_task_1',
                      cmd='echo hello 1',
                      shell=True),
        lsfdo.CmdTask(name='test_cmd_task_2',
                      cmd=['echo', 'hello', '2'],
                      shell=False)
    ]
    return tasks


def get_func_tasks():
    '''
    Return two FuncTask objects for testing.
    '''
    return [lsfdo.FuncTask(name='test_func_task_{}'.format(i),
                           func='test_lsfdo.example_func',
                           args=['hello {}'.format(i)],
                           kws={'msg2': 'test {}'.format(i)}) for i in range(2)]


def test_task_classes():
    '''
    Test making a CmdTask and a FuncTask.
    Test that __eq__ and __ne__ are implemented s.t. different objects 
    constructed with the same arguments are equal to each other and with
    different arguments are not equal to each other.
    '''
    # equivalent objects
    t1 = lsfdo.CmdTask("foo", "cmd", True)
    t2 = lsfdo.CmdTask("foo", "cmd", True)
    # non-equivalent object
    t3 = lsfdo.CmdTask("bar", "cmd", True)

    # equivalent objects
    t4 = lsfdo.FuncTask("name1", "myfunc", ['arg1', 2], {'kw1': ['a', 'list']})
    t5 = lsfdo.FuncTask("name1", "myfunc", ['arg1', 2], {'kw1': ['a', 'list']})
    # non-equivalent object
    t6 = lsfdo.FuncTask("name1", "myfunc", ['arg1', 3], {'kw1': ['a', 'list']})

    for e1, e2, ne in [(t1, t2, t3), (t4, t5, t6)]:
        # test object identity
        assert e1 is not e2
        assert e1 is not ne

        # test object equality
        assert e1 == e2
        assert e2 == e1
        assert not e1 != e2

        # test object inequality
        assert e1 != ne
        assert ne != e2
        assert not ne == e1


def test_run_cmd_tasks():
    '''
    Test creating CmdTasks and running them synchronously in process.  This
    tests much of the code in the run-on-lsf code path without the time
    burden of running tasks on lsf.  I.e. it is good for finding some bugs
    quickly.
    '''
    tasks = get_cmd_tasks()
    ns = TEST_NS
    # make sure dones are reset before running the test.
    lsfdo.reset(ns)

    assert not lsfdo.all_done(ns, tasks)
    # run jobs
    for task in tasks:
        lsfdo._run_task(ns, task)
    # wait for jobs to finish and assert that they are all done.
    assert lsfdo.all_done(ns, tasks)
    # run_tasks again.  They should be marked done, so they should not run.
    for task in tasks:
        lsfdo._run_task(ns, task)

    # clean up dones and make sure jobs are now not done.
    lsfdo.reset(ns)
    assert not lsfdo.all_done(ns, tasks)
    # finally, clean up tables.
    lsfdo.reset(ns)

def test_run_func_tasks():
    '''
    Test creating FuncTasks and running them synchronously in process.  This
    tests much of the code in the run-on-lsf code path without the time
    burden of running tasks on lsf.  I.e. it is good for finding some bugs
    quickly.
    '''
    tasks = get_func_tasks()
    ns = TEST_NS
    # make sure dones are reset before running the test.
    lsfdo.reset(ns)

    assert not lsfdo.all_done(ns, tasks)
    # run jobs
    for task in tasks:
        lsfdo._run_task(ns, task)
    # wait for jobs to finish and assert that they are all done.
    assert lsfdo.all_done(ns, tasks)
    # run_tasks again.  They should be marked done, so they should not run.
    for task in tasks:
        lsfdo._run_task(ns, task)

    # clean up dones and make sure jobs are now not done.
    lsfdo.reset(ns)
    assert not lsfdo.all_done(ns, tasks)
    # finally, clean up tables.
    lsfdo.reset(ns)


def test_run_lsf_tasks(wait=50, queue='cbi_12h'):
    '''
    Test running some functions on lsf.

    wait: how long (in seconds) to wait before asserting that all jobs are
    done.  tune this so that lsf has time to finish all the jobs.
    queue: An LSF queue name.  For testing, choose a queue name that jobs will
    start quickly on.
    '''
    wait = int(os.environ.get('TEST_LSFDO_WAIT', wait))
    queue = os.environ.get('TEST_LSFDO_QUEUE', queue)

    tasks = get_func_tasks()
    ns = TEST_NS
    # make sure dones are reset before running the test.
    lsfdo.reset(ns)

    # lsf options
    lsfopts = ['-q', queue, '-W', '2']

    assert not lsfdo.all_done(ns, tasks)
    # Run tasks on lsf.  Since they are just starting they should not be done.
    assert not lsfdo.run_tasks(ns, tasks, lsfopts, devnull=False)
    # Wait for jobs to finish.
    time.sleep(wait)
    # Now all tasks should be done.
    assert lsfdo.all_done(ns, tasks)
    # Now try running the tasks again.  This should return True because
    # all the tasks are done.
    assert lsfdo.run_tasks(ns, tasks, lsfopts)
    # Clean up dones and make sure jobs are now not done.
    lsfdo.reset(ns)
    assert not lsfdo.all_done(ns, tasks)
    # finally, clean up tables.
    lsfdo.reset(ns)


