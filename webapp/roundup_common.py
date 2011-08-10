'''
Module rules:
Do not import any other roundup modules or modules that depend on roundup modules, so that this module is independent of other roundup modules.
The module defines constants and and functions used by other roundup modules.
It implements functions for normalizing pairs and getting RSD parameters.
'''


import os

import config
import util


####################################################
# CONFIGURE CONSTANTS AND ENVIRONMENT VARIABLES
####################################################

# logging verbosity
# DEBUG=10, WARNING=30, ERROR=40, IMPORTANT=ERROR+5
ROUNDUP_LOG_LEVEL = int(os.environ.get('ROUNDUP_LOG_LEVEL', 0))

LSF_LONG_QUEUE = os.environ.get('ROUNDUP_LSF_LONG_QUEUE', 'shared_unlimited')

# use local disk or networked storage
# because the cluster can put such a heavy load on the NAS, using local disk during computation is generally preferred.
ROUNDUP_LOCAL = util.getBoolFromEnv('ROUNDUP_LOCAL', True)
# LOCAL_DIR = '/scratch' # always use local disk for local dir.
# only use local disk for local dir if ROUNDUP_LOCAL == true.
if ROUNDUP_LOCAL:
    # LOCAL_DIR = '/scratch'
    LOCAL_DIR = '/tmp'
else:
    LOCAL_DIR = config.TMP_DIR

# RSD PARAMETERS.  These are the parameter for which each pair is rounded up.
EVALUES = ['1e-5', '1e-10', '1e-15', '1e-20']
DIVERGENCES = ['0.2', '0.5', '0.8']

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


#########################################
# ORTHDATAS SERIALIZATION AND PERSISTANCE
#########################################

# orthData: a tuple of params, orthologs.
# params: a tuple of query genome, subject genome, divergence, and evalue.
# orthologs: a list of query id, subject id, and distance.


class OrthData(object):

    def __init__(self, params, orthologs):
        self.params = params
        self.orthologs = orthologs


def orthDatasFromFile(path):
    return [orthData for orthData in orthDatasFromFileGen(path)]


def orthDatasFromFileGen(path):
    '''
    path: contains zero or more orthDatas.  must exist.
    yields: every orthData, a pair of params and orthologs, in path.
    '''
    with open(path) as fh:
        for line in fh:
            if line.startswith('PA'):
                lineType, qdb, sdb, div, evalue = line.strip().split('\t')
                orthologs = []
            elif line.startswith('OR'):
                lineType, qid, sid, dist = line.strip().split('\t')                        
                orthologs.append((qid, sid, dist))
            elif line.startswith('//'):
                yield ((qdb, sdb, div, evalue), orthologs)


def orthDatasFromFilesGen(paths):
    '''
    paths: a list of file paths containing orthDatas.
    yields: every orthData in every file in paths
    '''
    for path in paths:
        for orthData in orthDatasFromFile(path):
            yield orthData


def orthDatasToFile(orthDatas, path, mode='w'):
    '''
    orthDatas: a list of rsd orthDatas. orthData is a pair of params and orthologs
    path: where to save the orthDatas
    mode: change to 'a' to append to an existing file
    serializes orthDatas and persists them to path
    Inspired by the Uniprot dat files, a set of orthologs starts with a params row, then has 0 or more ortholog rows, then has an end row.
    Easy to parse.  Can represent a set of parameters with no orthologs.
    Example:
    PA\tLACJO\tYEAS7\t0.2\t1e-15
    OR\tQ74IU0\tA6ZM40\t1.7016
    OR\tQ74K17\tA6ZKK5\t0.8215
    //
    PA      MYCGE   MYCHP   0.2     1e-15
    //
    '''
    with open(path, mode) as fh:
        for (qdb, sdb, div, evalue), orthologs in orthDatas:
            fh.write('PA\t{}\t{}\t{}\t{}\n'.format(qdb, sdb, div, evalue))
            for ortholog in orthologs:
                fh.write('OR\t{}\t{}\t{}\n'.format(*ortholog))
            fh.write('//\n')
    
                    
##########################
# DEPRECATED / UNUSED CODE
##########################

import re
matchDb = '.*\.aa'

def makeRoundupRE():
    '''
    returns a regular expression string that should match a roundup results file name
    this regular expression groups roundup names into qdb,sdb,div,evalue.
    [HACK] the regular expression is LIMITED in that it assumes dbs end in '.aa'.  Can you do better?
    '''
    matchDiv = '|'.join([re.sub('\.', '\\.', d) for d in DIVERGENCES])
    matchEvalue = '|'.join([t for t in EVALUES])
    matchRoundup = '^('+matchDb+')_('+matchDb+')_('+matchDiv+')_('+matchEvalue+')$'
    return matchRoundup


roundupRE = re.compile(makeRoundupRE())
    
    
def splitRoundupFilename(path):
    '''
    path: base filename or absolute path of filename
    returns list of qdb, sdb, divergence, evalue
    or None if path does not parse to a Roundup Filename
    '''
    match = roundupRE.search(os.path.basename(path))
    if not match:
        return None
    else:
        return list(match.groups())
                            
                            
def isRoundupFile(path):
    '''
    path: path to roundup file
    return: True iff path is a roundup results file name, like qdb_sdb_div_evalue
    '''
    return roundupRE.search(os.path.basename(path))
    

# last line emacs python mode bug fix
