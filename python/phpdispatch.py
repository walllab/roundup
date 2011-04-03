#!/usr/bin/env python

'''
Used by php web code to call python functions using php inputs and receive php output in return.
'''

import sys
import types
import logging


import config # configures logging
import util
import PHPSerialize
import PHPUnserialize



#############################################
# SERIALIZATION AND DESERIALIZATION FUNCTIONS
#############################################

def walkPHPArrayConvertHeuristically(data):
    '''
    Heuristically convert a php data value to a list if it looks like a list, or leave it unchanged otherwise.
    data: unserialized value from php, either a dict or an atom (string, int, double, boolean, ...) 
    warning: will wrongly convert a dict to a list if a) isPHPDataAList() returns true for the dict
    and b) it really is supposed to be a dict, not a list.
    return: data converted to list if it is a list, data if it is an atom or dict.  all the values of a list or dict are recursively converted too.
    '''
    if type(data) is types.DictType:
        if isPHPDataAList(data):
            lst = convertPHPArrayToList(data)
            return [walkPHPArrayConvertHeuristically(item) for item in lst]
        else:
            for k in data:
                data[k] = walkPHPArrayConvertHeuristically(data[k])
            return data
    else:
        return data


def convertPHPArrayToList(array):
    '''
    array: an "array" dict unserialized from php, which is represented as a dict with sequential keys.
    return: list of values in sequential order as determined by the keys of array.
    '''
    keys = array.keys()
    keys.sort()
    return [array[k] for k in keys]


def isPHPDataAList(data):
    '''
    data: unserialized value from php, either atom or dict.
    warning: will wrongly convert a dict to a list if that dict a) meets the conditions below
    and b) really is supposed to be a dict, not a list.
    return: true iff data is dict and all keys are sequential integers from 0..n-1, which is what php thinks is a list.
    '''
    if type(data) is types.DictType:
        i = 0
        for k in data.keys():
            if k != i:
                return False
            i += 1
        return True
    else:
        return False
    

def unserialize(data):
    return walkPHPArrayConvertHeuristically(PHPUnserialize.PHPUnserialize().unserialize(data))


def serialize(data):
    return PHPSerialize.PHPSerialize().serialize(data)


#######################
# DISPATCHING FUNCTIONS
#######################

def dispatch(fullyQualifiedFuncName, serializedKeywords=None):
    '''
    Adds php unserialization of function inputs and php serialization of function output to util.dispatch
    unserialize keywords, execute function, and serialize result
    '''

    if not fullyQualifiedFuncName:
        raise Exception('a python function (e.g. my.module.myfunc) is a required argument')
    if serializedKeywords:
        keywords = unserialize(serializedKeywords)
    else:
        keywords = {}

    output = util.dispatch(fullyQualifiedFuncName, keywords=keywords)
    return serialize(output)
        

def main():
    '''
    parse command line options and send to dispatch()
    '''
    
    import optparse
    parser = optparse.OptionParser(usage='%prog <python function>')
    options, args = parser.parse_args()

    # get function name
    if args:
        fullyQualifiedFuncName = args[0]
    else:
        fullyQualifiedFuncName = None

    # read serialized keywords
    serializedKeywords = sys.stdin.read()
    # dispatch function and keywords
    serializedOutput = dispatch(fullyQualifiedFuncName, serializedKeywords=serializedKeywords)
    # write serialized output
    sys.stdout.write(serializedOutput)


if __name__ == '__main__':
    try:
        main()
    except:
        logging.exception('Error.')
        raise



# last line fix for emacs python mode bug -- do not cross
