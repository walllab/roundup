
'''
This module allows one to distribute a batch of tasks on lsf and restart a
failed or partially failed batch of tasks.  It avoiding submitting tasks that
are done or already on lsf.  This allows one to pick up where one left off.

Every task (either a command line or a function call) has a name assigned to
it, which should be unique within a given namespace.  This namespace and
name combination is used to track which tasks are done and which are on lsf.
'''

import subprocess
import logging
import argparse

import cliutil
import dones
import lsf
import util
import filemsg


def lsf_job_name(ns, name):
    '''
    The combination of ns and name should be a globally unique string useful
    for identifying the job by name on lsf.
    '''
    return '{}_{}'.format(ns, name)


def reset(ns):
    '''
    Unmark all the jobs currently marked done.
    '''
    dones.get(ns).clear()



##########################
# RUN COMMAND LINES ON LSF

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


class FuncTask(object):
    def __init__(self, name, func, args=None, kws=None):
        self.name = name
        self.func = func
        self.args = args if args is not None else []
        self.kws = kws if kws is not None else {}

    def run(self):
        return util.dispatch(self.func, self.args, self.kws)

    def __repr__(self):
        msg = '{}(name={name!r}, func={func!r}, args={args!r}, kws={kws!r})'
        return msg.format(self.__class__.__name__, **vars(self))

    def __eq__(self, other):
        return (self.func == other.func and self.args == other.args and 
                self.kws == other.kws and self.name == other.name)

    def __ne__(self, other):
        return not self.__eq__(other)


def run_tasks(ns, tasks, lsfopts, devnull=True):
    '''
    Submit each task to lsf, unless the task is marked done or is already on
    lsf.
    '''
    # The names of every job currently on the lsf queue
    onJobNames = set(lsf.getOnJobNames())

    for task in tasks:
        if dones.get(ns).done(task.name):
            print 'Done. ns={}, name={}'.format(ns, task.name)
        elif lsf_job_name(ns, task.name) in onJobNames: 
            print 'Running. ns={}, name={}'.format(ns, task.name)
        else:
            print 'Submitting. ns={}, name={}'.format(ns, task.name)
            jobid = _bsub_task(ns, task, lsfopts, devnull=devnull)
            print 'Job id={}'.format(jobid)

    return all_done(ns, tasks)


def all_done(ns, tasks):
    names = [task.name for task in tasks]
    return dones.get(ns).all_done(names)


def _bsub_task(ns, task, lsfopts, devnull=True):
    '''
    Submit a task to lsf
    '''
    filename = filemsg.dump([ns, task])
    cmd = cliutil.args(__file__) + ['run_task', filename]
    devnull_option = ['-o', '/dev/null'] if devnull else []
    jobname_option = ['-J', lsf_job_name(ns, task.name)]
    lsfopts = devnull_option + list(lsfopts) + jobname_option
    return lsf.bsub(cmd, lsfopts)


def _run_task(ns, task):
    '''
    If task is not done, run task synchronously in the current process and
    then mark it done.
    '''
    if not dones.get(ns).done(task.name):
        task.run()
        dones.get(ns).mark(task.name)


def _cli_run_task(filename):
    ns, task = filemsg.load(filename)
    _run_task(ns, task)


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



