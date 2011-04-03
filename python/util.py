#!/usr/bin/env python

'''
general, widely applicable utilities
to fill in some gaps in the python language

ONLY DEPENDENCIES ON STANDARD LIBRARY MODULES ALLOWED.
'''

import datetime
import math
import hashlib # sha
import tempfile
import shutil
import time
import os
import sys


def dispatch(name, args=None, keywords=None):
    '''
    name: name of callable/function including modules, etc., e.g. 'foo_package.gee_package.bar_module.wiz_func'
    args: a list of arguments for the callable/function.
    keywords: a dict of keyword parameters for the callable/function.
    using the fully qualifed name, loads module, finds and calls function with the given args and keywords
    returns: the return value of the called callable.
    '''
    if args is None:
        args = []
    if keywords is None:
        keywords = {}
    modname, attrname = name.rsplit(".", 1)
    __import__(modname)
    mod = sys.modules[modname]
    attr = getattr(mod, attrname)
    return attr(*args, **keywords)


# remove at will.
def testing(msg='Hello, World.'):
    print msg
    return msg


def getBoolFromEnv(key, default=True):
    '''
    looks in os.environ for key.  If key is set to 'F', 'False', or '0' (case insensitive), returns false.  Otherwise, if key is set, returns True.
    Otherwise returns the default.
    '''
    if os.environ.has_key(key):
        value = os.environ[key].upper()
        return value not in ('F', 'FALSE', '0')
    else:
        return default


###########################
# CONTEXT MANAGER UTITLITES
###########################
# Generic context manager utilities.  Useful for turning objects or object factories into context managers.

class ClosingFactoryCM(object):
    '''
    context manager for creating a new obj from a factory function and closing the obj when done.  e.g. creating and closing a db connection each time.
    '''
    def __init__(self, factory):
        self.factory = factory
        self.obj = None
        
    def __enter__(self):
        self.obj = None
        self.obj = self.factory()
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.obj is not None:
            self.obj.close()


class FactoryCM(object):
    '''
    context manager for creating a new object from a factory function.  Might be useful for getting an object from a pool (e.g. a db connection pool).
    '''
    def __init__(self, factory):
        self.factory = factory

    def __enter__(self):
        return self.factory()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class NoopCM(object):
    '''
    context manager for getting an object.  Useful when a context manager is required instead of a simple object.  e.g. to reuse an existing db connection.
    '''
    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


#######################################
# 
#######################################

def truePred(*args, **keywords):
    return True


def retryErrorExecute(operation, args=[], keywords={}, pred=truePred, numTries=1, delay=0, backoff=1):
    '''
    pred: function takes Exception as arg, returns True to retry operation, False otherwise.  Default is to
      always return True.
    numTries: number of times to try, including the first time. numTries < 0 means try an infinite # of times
      if numTries == 0, does not execute operation.  Simply returns.
    delay: pause (in seconds) between tries.  default = 0 (no delay)
    backoff: delay is multiplied by this factor after every retry, so the length of successive delays are
      delay, delay*backoff, delay*backoff*backoff, etc. default = 1 (no backoff)
    execute operation.  if an exception occurs, pass it to the predicate.  if the
    predicate returns true, retry the operation if there are any tries left.  Otherwise, raise the exception.  
    '''
    # could make backoff a function, so delay = backoff(delay), for more flexibility than just an exponential relationship.
    error = None
    for i in xrange(numTries):
        try:
            return operation(*args, **keywords)
        except Exception, e:
            # re-raise exception if pred fails
            if not pred(e): raise
            # re-raise exception if that was the last try
            if i == (numTries-1): raise
            # else retry
            time.sleep(delay)
            delay *= backoff

# example:
# myFuncReturnValue = retryErrorExecute(myfunc, [param1, param2, param3], pred=customPred, numTries=10, delay=10, backoff=1.4)


##########################
# TEMPORARY DIRS AND FILES
##########################

def withTempDir(**keywords):
    '''
    keywords: accepts 'suffix', 'prefix', and 'dir' keywords with string values that are passed to tempfile.mkdtemp
    creates temporary directory, yields it, and deletes it after the yield returns or if an exception occurs.
    yields: path to a temporary directory.
    '''
    tempDir = None
    try:
        tempDir = tempfile.mkdtemp(**keywords)
        yield tempDir
        shutil.rmtree(tempDir)
    except:
        if tempDir:
            shutil.rmtree(tempDir)
        raise

def withOpenFile(name, mode='r', bufsize=-1):
    '''
    name, mode, and bufsize are the same as in the builtin function open().
    opens the file, yields it, and closes it after the yield returns, or after an exception occurs.
    yields: a filehandle for the open file.
    This implementation will not actually work correctly until code is ported to python2.5, since exception passing (control flow)
    is broken for yields prior to 2.5.
    '''
    fh = None
    try:
        fh = open(name, mode, bufsize)
        yield fh
        fh.close()
    except:
        if fh:
            fh.close()
        raise

################
# DATES AND TIME
################

def lastMonth(thisMonth=None):
    '''
    thisMonth: datetime or date obj.  defaults to today.
    returns: a date obj from the month before the month in thisMonth.  e.g. if this month is 2006/01/31, then 2005/12/01 is returned.
    '''
    if thisMonth == None:
        thisMonth = datetime.date.today()
    try:
        last = datetime.date(thisMonth.year, thisMonth.month-1, 1)
    except:
        last = datetime.date(thisMonth.year-1, 12, 1)
    return last


########
# RANDOM
########


class SimpleNamespace(object):
    '''
    use this if you want to instantiate an object to serve as a namespace.
    e.g. foo = SimpleNamespace(); foo.bar = 1; print foo.bar; # prints '1'
    '''
    pass


def mergeListOfLists(lists):
    '''
    lists: a list of lists
    returns: a list containing all the elements each list within lists
    '''
    merge = []
    for l in lists:
        merge.extend(l)
    return merge


def groupsOfN(iterable, n):
    '''
    iterable: some iterable collection
    n: length of lists to collect
    Iterates over iterable, returning lists of the next n element of iterable, until iterable runs out of elements.
    Last list may have less than n elements.
    returns: lists of n elements from iterable (except last list might have [0,n] elements.)
    '''
    seq = []
    count = 0
    it = iter(iterable)
    try:
        while 1:
            seq.append(it.next())
            count += 1
            if count == n:
                count = 0
                yield seq
                seq = []
    except StopIteration:
        if seq:
            yield seq
    

def isInteger(num):
    '''
    num: possibly an integer
    What is an integer?  In this case it is a thingy which can be converted to an integer and a float
    and when done so the two values are equal.
    Returns true if successful, false otherwise
    '''
    try:
        int(num)
        return int(num) == float(num)
    except (TypeError, ValueError):
        return False
    
def isNumber(num):
    '''
    num: possibly a number
    Attempts to convert num to a number.
    Returns true if successful, false otherwise
    '''
    try:
        float(num)
        return True
    except (TypeError, ValueError):
        return False
    

def makeCounter(n=0, i=1):
    '''
    n: number to start counting from
    i: increment
    This could be implemented the normal way using a closure, but python does not support writing to variables in a closure,
    forcing one to implement the function by wrapping the counter variable in a list.  I guess a generator is more pythonic.
    usage: counter = makeCounter(1); counter.next(); counter.next(); # etc.
    returns: a generator object which counts up from n by i, starting with n, when next() is called on the generator.
    '''
    while 1:
        yield n
        n = n + i

        
########################
# DESCRIPTIVE STATISTICS
########################

def mean(nums):
    return float(sum(nums))/len(nums)


def variance(nums):
    m = mean(nums)
    return sum([(n - m)**2 for n in nums]) / float(len(nums))


def stddev(nums):
    return math.sqrt(variance(nums))


#######################################
# COMBINATORICS FUNCTIONS
#######################################

def permute(set, n):
    ''' returns a list of lists every permutation of n elements from set '''
    if n == 0: return [[]]
    perms = []
    for x in set:
        subset = set[:]
        subset.remove(x)
        perms.extend([p+[x] for p in permute(subset, n-1)])
    return perms


def choose(set, n):
    '''
    set: a list
    returns: a list of lists of every combination of n elements from set
    warning: if len(set) > 998, python recursion limit exceeded.
    '''
    if len(set) < n: return []
    if n == 0: return [[]]
    return [set[0:1] + c for c in choose(set[1:], n-1)] + choose(set[1:], n)


def every(pred, seq):
    """ returns True iff pred is True for every element in seq """
    for x in seq:
        if not pred(x): return False
    return True


def any(pred, seq):
    """ returns False iff pred is False for every element in seq """
    for x in seq:
        if pred(x): return True
    return False


################################
# SERIALIZATION HELPER FUNCTIONS
################################

def loadObject(pickleFilename, protocol=-1):
    import cPickle
    fh = open(pickleFilename)
    obj = cPickle.load(fh)
    fh.close()
    return obj


def dumpObject(obj, pickleFilename, protocol=-1):
    import cPickle
    fh = open(pickleFilename, 'w')
    cPickle.dump(obj, fh, protocol=protocol)
    fh.close()
    return obj


################################
# FILE COMPARISION
################################


def writeToFile(data, filename, mode='w'):
    '''
    opens file, writes data, and closes file
    flushing used to improve consistency of writes in a concurrent environment.
    '''
    fh = open(filename, mode)
    fh.write(data)
    fh.flush()
    fh.close()


def readFromFile(filename, mode='r'):
    '''
    opens file, reads data, and closes file
    returns: contents of file
    '''
    fh = open(filename, mode)
    data = fh.read()
    fh.close()
    return data


def differentFiles(filename1, filename2):
    '''
    compares the contents of the two files using the SHA digest algorithm.
    returns: True if the contents of the files are different.  False otherwise.
    throws: an exception if either file does not exist.
    '''
    file1 = open(filename1)
    file2 = open(filename2)

    s1 = hashlib.sha1() # sha.new()
    s2 = hashlib.sha1() # sha.new()
    for l in file1:
        s1.update(l)
    for l in file2:
        s2.update(l)
    isDifferent = (s1.hexdigest() != s2.hexdigest())

    file1.close()
    file2.close()
    return isDifferent


if __name__ == '__main__':
    pass

