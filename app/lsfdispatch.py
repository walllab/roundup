'''
dispatch python function call asynchronously on LSF grid.
CLI (command line interface) for unserializing inputs from stdin or a file and serializing the function output.
CLI is used by LSF to run functions and store results.
'''

import os
import re
import sys
import cPickle
import logging

import config # configures logging
import nested
import lsf
import util


# __file__ is e.g. lsfdispatch.py or lsfdispatch.pyc
_FILE_PATH = os.path.abspath(re.sub(r'(.*\.py)(c|o)?', lambda m: m.group(1), __file__))
# use the current python executable to run this module
_LSF_DISPATCH_CMD = [sys.executable, _FILE_PATH]

# print _LSF_DISPATCH_CMD


def dispatch(func, args=None, keywords=None, path=None, lsfOptions=None, devnull=True, outfile=None):
    '''
    func: function name including modules, etc., e.g. 'foo_package.gee_package.bar_module.baz_object.wiz_func'
    args: seq of arguments passed to the function.
    keywords: dict of keyword parameters passed to the function
    path: seq of path components to add to sys.path before dispatched function is imported.  Defaults to the current sys.path.
    lsfOptions: a list of tokenized options for the lsf bsub command.  e.g. ['-q', 'shared_2h', '-J', 'myjob']
    devnull: default to True.  if True, ['-o', '/dev/null'] will be prepended to lsfOptions, redirecting the job output to dev null.
    outfile: a file to store the serialized return value of the function.  by default, the serialized output is sent to stdout.
    if False, lsf job output will behave normally, emailing or redirecting to a file.
    Use this to asynchronously distribute a function on LSF.
    returns: lsf job id of dispatched function
    '''
    if func is None:
        raise Exception('func is a required parameter')
    if args is None:
        args = []
    if keywords is None:
        keywords = {}
    if lsfOptions is None:
        lsfOptions = []
    if path is None:
        path = sys.path
    if devnull:
        lsfOptions = ['-o', '/dev/null'] + list(lsfOptions)
    inputFilename = nested.makeTempPath(prefix='lsfdispatch_')
    util.dumpObject((args, keywords, path), inputFilename)
    cmd = _LSF_DISPATCH_CMD + ['--input', inputFilename, '--delete-input']
    if outfile is not None:
        cmd += ['--output', outfile]
    cmd.append(func)
    return lsf.bsub(cmd, lsfOptions)


def main():
    '''
    reads a fully-qualified function name from the commandline and 
    reads serialized args, keywords, and path components for the given function from an input file or stdin.
    calls the function with the given keywords
    writes the serialized results of the function call to an output file or stdout.
    '''
    import optparse
    parser = optparse.OptionParser(usage='%prog [options] <python function>')
    parser.add_option('-i', '--input', help='Input file containing serialized args, keywords, and path components.  Defaults to stdin.')
    parser.add_option('--delete-input', action='store_true', default=False, help='Any file specified with the --input option will be deleted.')
    parser.add_option('-o', '--output', help='Output file to write python serialized results.  Defaults to stdout.')
    options, args = parser.parse_args()

    # logging.debug('in lsfdispatch.py main():  args=%s'%(args,))

    # VALIDATION
    if not args:
        parser.error('a python function (e.g. my.module.myfunc) is a required argument')
        
    # GET FUNCTION NAME
    func = args[0]

    # READ AND CLEAN UP INPUT
    input = sys.stdin
    if options.input:
        input = open(options.input)
    serialized_data = input.read()
    if options.input:
        input.close()
        if options.delete_input and os.path.isfile(options.input):
            os.remove(options.input)

    # UNSERIALIZE ARGS, KEYWORDS AND PATH, EXECUTE FUNCTION, AND SERIALIZE RESULTS
    args, keywords, path = cPickle.loads(serialized_data)
    for item in path:
        if item not in sys.path:
            sys.path.append(item)
    retval = util.dispatch(func, args=args, keywords=keywords)
    serialized_retval = cPickle.dumps(retval, -1)

    # WRITE AND CLEAN UP OUTPUT
    output = sys.stdout
    try:
        if options.output:
            output = open(options.output, 'wb')
        output.write(serialized_retval)
    finally:
        if options.output:
            output.close()
        

if __name__ == '__main__':
    try:
        main()
    except:
        logging.exception('Error.')
        raise


# last line
