

'''
A module which creates a command suitable for running a module as a script.

Assuming the current sys.path is appropriate for running the module and its 
dependencies, this module can:

- set PYTHONPATH to the contents of sys.path
- return a command (a list of arguments suitable for subprocess.Popen) that
  contains the current python executable and the path the the module file.

This module will not work if:

- PYTHONPATH needs to be set to something different
- the module calling script_list() does not have an .py file for some reason.

'''

import os
import re
import sys


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


