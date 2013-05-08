
'''
This module allows one to distribute a batch of tasks on lsf and restart a
failed or partially failed batch of tasks.  It avoiding submitting tasks that
are done or already on lsf.  This allows one to pick up where one left off.

Every task (either a command line or a function call) has a name assigned to
it, which should be unique within a given namespace.  This namespace and
name combination is used to track which tasks are done and which are on lsf.
'''

import argparse
import logging
import subprocess
import time

import cliutil
import dones
import lsf
import util
import filemsg


# Seconds to pause between polling lsf to see if jobs are done.
DEFAULT_PAUSE = 10


def echo(msg):
    ''' Print msg.  Used for testing. '''
    print msg


class NotDoneError(Exception):
    pass


##############
# TASK CLASSES

class CmdTask(object):
    def __init__(self, name, cmd, shell=False):
        self.name = name
        self.cmd = cmd
        self.shell = shell

    def run(self):
        return subprocess.check_call(self.cmd, shell=self.shell)

    def __repr__(self):
        return '{}(name={name!r}, cmd={cmd!r}, shell={shell!r})'.format(
            self.__class__.__name__, **vars(self))

    def __eq__(self, other):
        return (self.cmd == other.cmd and self.name == other.name and
                self.shell == other.shell)

    def __ne__(self, other):
        return not self.__eq__(other)


class FuncNameTask(object):
    def __init__(self, name, funcname, args=None, kws=None):
        '''
        funcname: string.  The fully-qualified function name of a module-level
        function.
        '''
        self.name = name
        self.funcname = funcname
        self.args = args if args is not None else []
        self.kws = kws if kws is not None else {}

    def run(self):
        return util.dispatch(self.funcname, self.args, self.kws)

    def __repr__(self):
        msg = '{}(name={name!r}, funcname={funcname!r}, args={args!r}, kws={kws!r})'
        return msg.format(self.__class__.__name__, **vars(self))

    def __eq__(self, other):
        return (self.funcname == other.funcname and self.args == other.args and
                self.kws == other.kws and self.name == other.name)

    def __ne__(self, other):
        return not self.__eq__(other)


class FuncTask(object):
    def __init__(self, name, func, args=None, kws=None):
        '''
        func: a module-level (hence pickleable) function object to run.
        '''
        self.name = name
        self.func = func
        self.args = args if args is not None else []
        self.kws = kws if kws is not None else {}

    def run(self):
        return self.func(*self.args, **self.kws)

    def __repr__(self):
        msg = '{}(name={name!r}, func={func!r}, args={args!r}, kws={kws!r})'
        return msg.format(self.__class__.__name__, **vars(self))

    def __eq__(self, other):
        return (self.func == other.func and self.args == other.args and 
                self.kws == other.kws and self.name == other.name)

    def __ne__(self, other):
        return not self.__eq__(other)


class MethodTask(object):
    '''
    Since an instance method can not be pickled directly, to run an instance
    method pickle the instance and method name.
    '''
    def __init__(self, name, obj, method, args=None, kws=None):
        '''
        obj: a module-level class instance that must be pickleable.
        method: string.  The name of the method to invoke on obj.
        '''
        self.name = name
        self.obj = obj
        self.method = method
        self.args = args if args is not None else []
        self.kws = kws if kws is not None else {}
        # at the minimum, assert that obj has an attribute named by method.
        assert getattr(self.obj, self.method)

    def run(self):
        return getattr(self.obj, self.methodname)(*self.args, **self.kws)

    def __repr__(self):
        msg = '{}(name={name!r}, func={func!r}, args={args!r}, kws={kws!r})'
        return msg.format(self.__class__.__name__, **vars(self))

    def __eq__(self, other):
        return (self.obj == other.obj and self.method == other.method and
                self.args == other.args and self.kws == other.kws and self.name
                == other.name)

    def __ne__(self, other):
        return not self.__eq__(other)


def do(ns, task):
    '''
    Use name to track whether or not task has been run.  If it has,
    skip it.  If it has not, run it synchronously in the current process and
    mark it done if it successfully completes.
    '''
    if not _get_dones(ns).done(task.name):
        print 'Doing', task.name
        task.run()
        _get_dones(ns).mark(task.name)

    print 'Done', task.name


def bsubmany(ns, tasks, opts, pause=DEFAULT_PAUSE, timeout=-1):
    '''
    tasks: a list of Task objects which will be pickled.
    opts: list of lsf options, one for each task.
    pause: Number of seconds to wait between checking for running lsf jobs.
    timeout: Number of seconds to wait for tasks to finish running on lsf
    before giving up.  A timeout < 0 means wait until no more tasks are running
    on lsf.  A timeout of 0 means do not wait at all for jobs to finish.
    '''
    # Submit tasks that are neither done nor running to LSF.
    done = _done_names(ns, tasks)
    running = _running_names(ns, tasks)
    submitted = False
    for task, opt in zip(tasks, opts):
        if task.name not in done and task.name not in running:
            print 'Submitting task to LSF. ns={}, name={}'.format(ns, task.name)
            jobid = _bsub_task(ns, task, opt)
            submitted = True
            print 'Job id={}'.format(jobid)

    # Wait for tasks to finish running.
    if timeout != 0:
        start = time.time()

        # if timeout is less than pause, only pause for timeout time.
        if timeout > 0 and timeout < pause:
            pause = timeout

        # LSF takes a few seconds to realize you have submitted a job (eventually
        # consistent?), so give lsf time to catch up if a job was submitted. If you
        # check right away, lsf might say there are no running jobs when there are.
        if submitted:
            print 'Waiting {} seconds for tasks to finish running.'.format(pause)
            time.sleep(pause)

        while _any_running(ns, tasks):
            # stop waiting when enough time has elapsed
            elapsed_time = time.time() - start
            if timeout > 0 and elapsed_time >= timeout:
                break

            # avoid waiting past timeout
            remaining_time = timeout - elapsed_time
            if timeout > 0 and remaining_time < pause:
                pause = remaining_time

            print 'Waiting {} seconds for tasks to finish running.'.format(pause)
            time.sleep(pause)

    # Make sure all tasks are done.
    if not all_done(ns, tasks):
        raise NotDoneError('Not all tasks successfully done.', ns, tasks)


def reset(ns):
    '''
    Unmark all the dones for namespace ns.
    '''
    _get_dones(ns).clear()


def unmark(ns, task):
    '''
    Mark a task as not done, so that it can be run again.
    '''
    _get_dones(ns).unmark(task.name)


def all_done(ns, tasks):
    '''
    Return True iff each task in tasks is marked done.
    '''
    names = [task.name for task in tasks]
    return _get_dones(ns).all_done(names)


def _lsf_job_name(ns, name):
    '''
    The combination of ns and name should be a globally unique string useful
    for identifying the job by name on lsf.
    '''
    return '{}_{}'.format(ns, name)


def _running_names(ns, tasks):
    onJobNames = set(lsf.getOnJobNames())
    return set(t.name for t in tasks if _lsf_job_name(ns, t.name) in
               onJobNames)


def _any_running(ns, tasks):
    '''
    Return true iff any of the tasks are currently on LSF.
    '''
    return bool(_running_names(ns, tasks))


def _get_dones(ns):
    return dones.get(ns)


def _done_names(ns, tasks):
    d = _get_dones(ns)
    return set(t.name for t in tasks if d.done(t.name))


def _bsub_task(ns, task, lsfopts, devnull=True):
    '''
    Submit a task to lsf
    '''
    filename = filemsg.dump([ns, task])
    cmd = cliutil.args(__file__) + ['run_task', filename]
    devnull_option = ['-o', '/dev/null'] if devnull else []
    jobname_option = ['-J', _lsf_job_name(ns, task.name)]
    lsfopts = devnull_option + list(lsfopts) + jobname_option
    return lsf.bsub(cmd, lsfopts)


def _cli_run_task(filename):
    ns, task = filemsg.load(filename)
    do(ns, task)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('run_task')
    subparser.add_argument('filename')
    subparser.set_defaults(func=_cli_run_task)

    # parse command line arguments and invoke the appropriate handler.
    args = parser.parse_args()
    kws = dict(vars(args))
    del kws['func']
    return args.func(**kws)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('')
        raise



