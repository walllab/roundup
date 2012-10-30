'''
Adds "middleware" functionality to dispatch for serializing return value to the filesystem and adding a key and filename to the cache.
'''

import os

import cacheutil
import util


class Dispatcher(object):
    def __init__(self, table, create, manager):
        '''
        manager: context manager that yields a Connection.
          Typical managers are cmutil.Noop(conn) to reuse a connection or cmutil.ClosingFactory(getConnFunc) to use a new connection each time.
        '''
        self.cache = cacheutil.Cache(manager, table=table, create=create)

    def dispatch(self, fullyQualifiedFuncName=None, keywords=None, cacheKey=None, outputPath=None):
        '''
        fullyQualifiedFuncName: required. function name including modules, etc., e.g. 'foo_package.gee_package.bar_module.baz_class.wiz_func'
        keywords: dict of keyword parameters passed to the function.  optional.  defaults to {}
        outputPath: required. function output is serialized and written to this file.
        cacheKey: required. outputPath is added to cache under this key.
        '''
        if fullyQualifiedFuncName == None:
            raise Exception('fullyQualifiedFuncName is a required parameter')
        if cacheKey == None:
            raise Exception('cacheKey is a required parameter')
        if outputPath == None:
            raise Exception('outputPath is a required parameter')
        if keywords is None:
            keywords = {}

        output = util.dispatch(fullyQualifiedFuncName, keywords=keywords)
        util.dumpObject(output, outputPath)
        self.cache.set(cacheKey, outputPath)
        return output
    

# last line python emacs mode bug fix



