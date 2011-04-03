#!/usr/bin/env python

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
import LSF
import util


_LSF_DISPATCH_CMD = os.path.abspath(os.path.join(os.path.dirname(__file__), 'lsfdispatch.py'))


def dispatchUpToOne(jobName, fullyQualifiedFuncName=None, keywords=None, lsfOptions=None):
    '''
    dispatch to lsf unless there is a job named jobName on lsf that is not ended.
    If you want to run at most (and at least) one job to execute a series of tasks, this will only run the job if it is not already running.
    warning: if this function is called several times in quick succession, multiple jobs can be submitted before lsf registers the presence of a job named jobName.
    '''
    infos = LSF.getJobInfosByJobName(jobName)
    if infos and not all(LSF.isEndedStatus(info[LSF.STATUS]) for info in infos):
        return
    if lsfOptions is None:
        lsfOptions = []
    dispatch(fullyQualifiedFuncName, keywords, ['-J %s'%jobName]+lsfOptions)


def dispatch(fullyQualifiedFuncName=None, keywords=None, lsfOptions=None):
    '''
    fullyQualifiedFuncName: function name including modules, etc., e.g. 'foo_package.gee_package.bar_module.baz_class.wiz_func'
    keywords: dict of keyword parameters passed to the function
    Use this to asynchronously distribute a function on the lsf cluster.
    By default '-o /dev/null' is added as an option.  Including a -o option in lsfOptions will override this default.
    returns: lsf job id of dispatched function
    '''
    if fullyQualifiedFuncName is None:
        raise Exception('fullyQualifiedFuncName is a required parameter')
    if keywords is None:
        keywords = {}
    if lsfOptions is None:
        lsfOptions = []
    inputFilename = nested.makeTempPath(prefix='dispatch_tmp_')
    util.dumpObject(keywords, inputFilename)
    cmd = _LSF_DISPATCH_CMD
    cmd += ' --input '+inputFilename+' --delete-input '+fullyQualifiedFuncName
    return LSF.submitToLSF([cmd], ['-o /dev/null']+lsfOptions)


def main():
    '''
    reads a fully-qualified function name from the commandline and 
    reads serialized keywords for the given function from the commandline or stdin or an input file.
    calls the function with the given keywords
    writes the serialized results of the function call to an output file or stdout.
    '''
    import optparse
    parser = optparse.OptionParser(usage='%prog [options] <python function> [<serialized_keywords>]')
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
    if len(args) == 2:
        serialized_keywords = args[1]
    else:
        input = sys.stdin
        if options.input:
            input = open(options.input)
        serialized_keywords = input.read()
    
        if options.input:
            input.close()
            if options.delete_input and os.path.isfile(options.input):
                os.remove(options.input)

    # UNSERIALIZE KEYWORDS, EXECUTE FUNCTION, AND SERIALIZE RESULTS
    retval = util.dispatch(fullyQualifiedFuncName, keywords=cPickle.loads(serialized_keywords))
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
