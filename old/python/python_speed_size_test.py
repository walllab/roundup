import random
import cPickle
import os

'''
Testing speed and picke size of basic data types: tuple, list, dict, and classes constructed two different ways.

Whether or not large or small data, tuple comes out first in size and speed
List follows closely behind
Dict is bigger and slower
And both classes are much bigger and slower.

Here are results for smallDataGen with cPickle dumping  
testTuple()
/Users/td23/foo.txt size: 1888906
         500011 function calls in 0.723 CPU seconds

testList()
/Users/td23/foo.txt size: 2188906
         500011 function calls in 0.811 CPU seconds

testDict()
/Users/td23/foo.txt size: 3288960
         500011 function calls in 1.209 CPU seconds

testAttribute()
/Users/td23/foo.txt size: 7288960
         500011 function calls in 2.049 CPU seconds

testConstructor()
/Users/td23/foo.txt size: 7388960
         600011 function calls in 2.309 CPU seconds

Here are the results without cPickle dumping
testTuple()
         500005 function calls in 0.349 CPU seconds
testList()
         500005 function calls in 0.382 CPU seconds
testDict()
         500005 function calls in 0.433 CPU seconds
testAttribute()
         500005 function calls in 0.531 CPU seconds
testConstructor()
         600005 function calls in 0.645 CPU seconds
         
         '''

DUMMY_FILE = '/Users/td23/foo.txt'
NUM = 100000
DATA_GEN = random.random

def smallDataGen():
    return 1


class TestClassAttributes:
    pass


class TestClassConstructor:

    def __init__(self, x, longName, reallyLongAndDescriptiveName):
        self.x = x
        self.longName = longName
        self.reallyLongAndDescriptiveName = reallyLongAndDescriptiveName



def testDumpSize(obj):
    fh = open(DUMMY_FILE, 'w')
    cPickle.dump(obj, fh)
    fh.close()
    print DUMMY_FILE, 'size:', os.path.getsize(DUMMY_FILE)


def profileAndPrint(funcStr):
    print funcStr
    
    import cProfile, pstats
    prof = cProfile.Profile()
    prof = prof.runctx(funcStr, globals(), locals())

    stats = pstats.Stats(prof)
    stats.sort_stats("time")  # Or cumulative
    stats.print_stats(50)  # how many to print


def testSub(num, testFactory):
    tests = []
    for i in range(num):
        tests.append(testFactory())
    # testDumpSize(tests)


def tupleFactory():
    return (DATA_GEN(), DATA_GEN(), DATA_GEN())
    
def listFactory():
    return [DATA_GEN(), DATA_GEN(), DATA_GEN()]
    
def dictFactory():
    return {'x': DATA_GEN(), 'longName': DATA_GEN(), 'reallyLongAndDescriptiveName': DATA_GEN()}

def constructorFactory():
    return TestClassConstructor(DATA_GEN(), DATA_GEN(), DATA_GEN())

def attributeFactory():
    test = TestClassAttributes()
    test.x = DATA_GEN()
    test.longName=DATA_GEN()
    test.reallyLongAndDescriptiveName = DATA_GEN()
    return test

def testTuple():
    testSub(NUM, tupleFactory)

def testList():
    testSub(NUM, listFactory)

def testDict():
    testSub(NUM, dictFactory)
    
def testConstructor():
    testSub(NUM, constructorFactory)
    
def testAttribute():
    testSub(NUM, attributeFactory)
    
def main():

    global DATA_GEN
    DATA_GEN = smallDataGen # random.random
    profileAndPrint('testTuple()')
    profileAndPrint('testList()')
    profileAndPrint('testDict()')
    profileAndPrint('testAttribute()')
    profileAndPrint('testConstructor()')


if __name__ == '__main__':
    main()

    
