

'''
A module which creates a command suitable for running a module as a script.

Usage:

Typical usage looks something like:

    cmd = cliutil.args(__file__) + ['my', 'other', 'args']
    subprocess.call(cmd)

If you are having import problems b/c sys.path is wrong, consider adding a
'.pth' file to the site-packages directory of sys.executable.  See
http://docs.python.org/2/library/site.html for more details.
'''

import os
import re
import sys


#################################################
# Turning a Module File Into an Executable Script

def args(script, python=None, string=False):
    '''
    Return command args list suitable for running with the
    subprocess module that would run `script` using the current python
    executable.

    This might fail in the case where script refers to a '.pyc' file that is
    not in the same directory as its '.py' file or when using zipped python
    packages.

    script: The path to the script.  Typically __file__ from a module that
    wants to be run as a script.
    python: The python executable used to run script.  Defaults to the
    currently running python executable, sys.executable.
    string: Return args as a string, suitable for use with subprocess.Popen
    when shell=True.

    Example return value:

        ['/www/dev.roundup.hms.harvard.edu/venv/bin/python',
        '/www/dev.roundup.hms.harvard.edu/app/foo.py']
    '''
    # script is the path to a script .py or .pyc file to be executed.
    filename = os.path.abspath(re.sub(r'(.*\.py)(c|o)?', lambda m: m.group(1),
                                      script))

    # use the current python executable to run this script
    if python is None:
        python = os.path.abspath(sys.executable)

    return [python, filename]


