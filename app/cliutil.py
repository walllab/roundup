

import os
import re
import sys

import temps
import util


def pythonpath():
    '''
    Transform sys.path into a string for use with the PYTHONPATH environent
    variable.
    '''
    return os.pathsep.join(sys.path)


def set_pythonpath():
    '''
    Set the PYTHONPATH environment variable to the current value of sys.path.
    This can be useful for running a script that needs to import modules that
    would not be on sys.path by default, like a third-party module that is
    in its own directory.
    '''
    os.environ['PYTHONPATH'] = pythonpath()


def script_list(script):
    '''
    Return a command arg list suitable for running with the
    subprocess module that would run script using the current python
    executable.  This might fail in the case where script refers to a '.pyc'
    file that is not in the same directory as its '.py' file or when using
    zipped python packages.

    script: The path to the script.  Typically __file__ from a module that
    wants to be run as a script.

    Example return value:

        ['/www/dev.roundup.hms.harvard.edu/venv/bin/python',
        '/www/dev.roundup.hms.harvard.edu/app/foo.py']
    '''
    # script is the path to a script .py or .pyc file to be executed.
    filename = os.path.abspath(re.sub(r'(.*\.py)(c|o)?', lambda m: m.group(1),
                                      script))
    # use the current python executable to run this script
    return [os.path.abspath(sys.executable), filename]


def params_to_file(args=None, kws=None, filename=None):
    '''
    Serialize args, kws, and write them to filename.  If filename
    is None, use temps to create a temporary file.  Return the filename the
    parameters were stored in.

    args: a list of function arguments.  If None (default), an empty list will
    be used.
    kws: a dict of function keyword arguments  If None (default), an empty
    dict will be used.
    filename: where to store the serialized args and kws.  If None (default),
    the temps module will be used to create a unique filename in which to
    store the params.
    '''
    args = [] if args is None else args
    kws = {} if kws is None else kws
    if filename is None:
        filename = temps.tmppath(prefix='params_')
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


