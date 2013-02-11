

import os
import re
import sys

import nested
import util


def script_argv(script):
    '''
    Return a command arg list suitable for running with the subprocess module
    that would run script using the current python executable.

    script: typically __file__ from a script that wants to be run as a script.

    Example return value:

        ['/www/dev.roundup.hms.harvard.edu/venv/bin/python',
        '/www/dev.roundup.hms.harvard.edu/app/foo.py']
    '''
    # script is the path to a script .py or .pyc file to be executed.
    filename = os.path.abspath(re.sub(r'(.*\.py)(c|o)?', lambda m: m.group(1),
                                      script))
    # use the current python executable to run this script
    return [os.path.abspath(sys.executable), filename]


def script_cmd(script):
    '''
    Return a command string suitable for running with the subprocess module
    that would run script using the current python executable.

    script: typically __file__ from a script that wants to be run as a script.

    Example return value:

        '/www/dev.roundup.hms.harvard.edu/venv/bin/python /www/dev.roundup.hms.harvard.edu/app/foo.py'
    '''
    return ' '.join(script_argv(script))


def params_to_file(args=None, kws=None, filename=None):
    '''
    Serialize args, kws, and write them to filename.  If filename
    is None, use nested to create a temporary file.  Return the filename the
    parameters were stored in.

    args: a list of function arguments.  If None (default), an empty list will
    be used.
    kws: a dict of function keyword arguments  If None (default), an empty
    dict will be used.
    filename: where to store the serialized args and kws.  If None (default),
    the nested module will be used to create a unique filename in which to
    store the params.
    '''
    args = [] if args is None else args
    kws = {} if kws is None else kws
    if filename is None:
        filename = nested.makeTempPath(prefix='params_')
    util.dumpObject((args, kws), filename)
    return filename

def params_from_file(filename, delete=True):
    '''
    Read and unserialize parameters from a file and return a tuple of
    args and kws.  If delete is True (the default), remove 
    filename after reading the parameters.
    '''
    args, kws = util.loadObject(filename)
    if delete:
        os.remove(filename)
    return args, kws


