'''
Module rules:
Do not import any other roundup modules or modules that depend on roundup modules, so that this module is independent of other roundup modules.
The module defines constants and and functions used by other roundup modules.
It implements functions for normalizing pairs and getting RSD parameters.
'''


import os


#####################################
# CONSTANTS AND ENVIRONMENT VARIABLES

# logging verbosity
# DEBUG=10, WARNING=30, ERROR=40, IMPORTANT=ERROR+5
ROUNDUP_LOG_LEVEL = int(os.environ.get('ROUNDUP_LOG_LEVEL', 0))

# RSD PARAMETERS.  These are the parameter for which each pair is rounded up.
EVALUES = ['1e-5', '1e-10', '1e-15', '1e-20']
DIVERGENCES = ['0.8', '0.5', '0.2']

# orthology query result keys.  short to save space.
EXTERNAL_SEQUENCE_ID_KEY = 'a'
GENOME_ID_KEY = 'g'
GENE_NAME_KEY = 'n'
TERMS_KEY = 't'


class RoundupException(Exception):
    '''
    used when want to handle/catch roundup specific exceptions
    '''
    pass


#################
# PAIRS FUNCTIONS
#################

def normalizePairs(pairs):
    '''
    pairs: a list of pairs of genomes.
    returns: a sorted list of sorted pairs of genomes, with no duplicate pairs.
    '''
    return sorted(set([tuple(sorted(p)) for p in pairs]))


def makePair(qdb, sdb):
    '''
    a pair is a sorted tuple of genomes, where a genome is an ascii-encoded string .
    '''
    # convert to ascii, genome ids come from django, etc.
    if type(qdb) == unicode:
        qdb = qdb.encode('ascii')
    if type(sdb) == unicode:
        sdb = sdb.encode('ascii')
        
    return tuple(sorted((qdb, sdb)))


def isSortedPair(qdb, sdb):
    '''
    used to check if (qdb, sdb) is a sorted pair.
    '''
    return makePair(qdb, sdb) == (qdb, sdb)


################################
# PARAMETER GENERATING FUNCTIONS
################################


def genDivEvalueParams():
    ''' used for simultaneously rounding up multiple param combinations for a pair.'''
    params = []
    for div in DIVERGENCES:
        for evalue in EVALUES:
            params.append((div, evalue))
    return params


