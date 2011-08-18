'''
dispatch python function call asynchronously on LSF grid.
CLI (command line interface) for unserializing inputs from stdin or a file and serializing the function output.
CLI is used by LSF to run functions and store results.
'''

import os
import sys
import cPickle
import logging

import config # configures logging
import nested
import lsf
import util


# requires python2.7 in the path
_LSF_DISPATCH_CMD = 'python2.7 '+os.path.abspath(os.path.join(os.path.dirname(__file__), 'lsfdispatch.py'))


def dispatch(fullyQualifiedFuncName=None, keywords=None, lsfOptions=None, path=None):
    '''
    fullyQualifiedFuncName: function name including modules, etc., e.g. 'foo_package.gee_package.bar_module.baz_class.wiz_func'
    keywords: dict of keyword parameters passed to the function
    path: seq of path components to use when dispatched function is imported.
    Use this to asynchronously distribute a function on the lsf cluster.  Defaults to the current sys.path.
    By default '-o /dev/null' is added as an option.  Including a -o option in lsfOptions will override this default.
    returns: lsf job id of dispatched function
    '''
    if fullyQualifiedFuncName is None:
        raise Exception('fullyQualifiedFuncName is a required parameter')
    if keywords is None:
        keywords = {}
    if lsfOptions is None:
        lsfOptions = []
    if path is None:
       path = sys.path 
    inputFilename = nested.makeTempPath(prefix='dispatch_tmp_')
    util.dumpObject((keywords, path), inputFilename)
    cmd = _LSF_DISPATCH_CMD
    cmd += ' --input '+inputFilename+' --delete-input '+fullyQualifiedFuncName
    return lsf.submitToLSF([cmd], ['-o /dev/null']+lsfOptions)


def main():
    '''
    reads a fully-qualified function name from the commandline and 
    reads serialized keywords for the given function from the commandline or stdin or an input file.
    calls the function with the given keywords
    writes the serialized results of the function call to an output file or stdout.
    '''
    import optparse
    parser = optparse.OptionParser(usage='%prog [options] <python function>')
    parser.add_option('-i', '--input', help='Input file containing serialized map of function keywords.  defaults to the commandline or stdin')
    parser.add_option('--delete-input', action='store_true', default=False, help='Any file specified with the --input option will be deleted.')
    parser.add_option('-o', '--output', help='output file to write python serialized results.  defaults to stdout.')
    options, args = parser.parse_args()

    # logging.debug('in lsfdispatch.py main():  args=%s'%(args,))

    # VALIDATION
    if not args:
        parser.error('a python function (e.g. my.module.myfunc) is a required argument')
        
    # GET FUNCTION NAME
    fullyQualifiedFuncName = args[0]

    # READ AND CLEAN UP INPUT
    input = sys.stdin
    if options.input:
        input = open(options.input)
    serialized_keywords_and_path = input.read()
    
    if options.input:
        input.close()
        if options.delete_input and os.path.isfile(options.input):
            os.remove(options.input)

    # UNSERIALIZE KEYWORDS AND PATH, EXECUTE FUNCTION, AND SERIALIZE RESULTS
    keywords, path = cPickle.loads(serialized_keywords)
    for item in path:
        if item not in sys.path:
            sys.path.append(item)
    retval = util.dispatch(fullyQualifiedFuncName, keywords=keywords)
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
        # logging.debug('in lsfdispatch.py')
        main()
    except:
        logging.exception('Error.')
        raise


# last line
