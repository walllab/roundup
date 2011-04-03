'''
IMPLEMENTATION OF THE ROUNDUP DATA MODEL.

Module rules:
Do not import any other roundup modules.
The module defines constants used by other roundup modules and functions which implement semantics.
Since this file defines the roundup data model, it should not depend on any other roundup modules.
'''


import os
import re
import shutil
import datetime
import time
import logging

import config
import execute
import util
import nested


####################################################
# CONFIGURE CONSTANTS AND ENVIRONMENT VARIABLES
####################################################

# logging verbosity
# DEBUG=10, WARNING=30, ERROR=40, IMPORTANT=ERROR+5
ROUNDUP_LOG_LEVEL = int(os.environ.get('ROUNDUP_LOG_LEVEL', 0))

# use local disk or networked storage
# because the cluster can put such a heavy load on the NAS, using local disk during computation is generally preferred.
ROUNDUP_LOCAL = util.getBoolFromEnv('ROUNDUP_LOCAL', True)
# LOCAL_DIR = '/scratch' # always use local disk for local dir.
# only use local disk for local dir if ROUNDUP_LOCAL == true.
if ROUNDUP_LOCAL:
    LOCAL_DIR = '/scratch'
else:
    LOCAL_DIR = config.TMP_DIR

# get results files dir and genomes dir from deployment location.  override if defined in environment.
ROUNDUP_GENOMES_DIR = os.environ.get('ROUNDUP_GENOMES_DIR', config.GENOMES_DIR)
ROUNDUP_RESULTS_DIR = os.environ.get('ROUNDUP_RESULTS_DIR', config.RESULTS_DIR)

# more paths and directories.
CURRENT_RESULTS_DIR = os.path.join(ROUNDUP_RESULTS_DIR, 'current')
OLD_RESULTS_DIR = os.path.join(ROUNDUP_RESULTS_DIR, 'old')
CURRENT_GENOMES_DIR = os.path.join(ROUNDUP_GENOMES_DIR, 'current')
UPDATED_GENOMES_DIR = os.path.join(ROUNDUP_GENOMES_DIR, 'updated')
OLD_GENOMES_DIR = os.path.join(ROUNDUP_GENOMES_DIR, 'old')
COMPUTE_DIR = config.COMPUTE_DIR
HISTORY_PATH = os.path.join(ROUNDUP_RESULTS_DIR, 'history.txt')
STATS_PATH = os.path.join(ROUNDUP_RESULTS_DIR, 'stats.data')

# blasting
BLAST_RESULTS_EXTENSION = '.db'
BLAST_PROGRAM = '/opt/blast2/blastp'

# RSD PARAMETERS.  These are the parameter for which each pair is rounded up.
EVALUES = ['1e-5', '1e-10', '1e-15', '1e-20']
DIVERGENCES = ['0.2', '0.5', '0.8']

# running rsd
MATRIX_PATH = os.path.join(config.CONFIG_DIR, 'jones.dat')
CODEML_CONTROL_PATH = os.path.join(config.CONFIG_DIR, 'codeml.ctl')
MAX_GOOD_EVALUE_HITS = 3

# LSF OPTIONS
# You can override the default LSF.py short and long queues by using env vars.  setLSF_SHORT_QUEUE=cbi_15m and LSF_LONG_QUEUE=cbi_unlimited on command line.
# output option is where to store lsf job output files.  this output is not used.
ROUNDUP_LSF_OUTPUT_OPTION = ' -o /dev/null'
# ROUNDUP_LSF_OUTPUT_OPTION = ' -o /scratch/%J.out'

EXTERNAL_SEQUENCE_ID_KEY = 'a'
GENOME_ID_KEY = 'g'
GENE_NAME_KEY = 'n'
TERMS_KEY = 't'


class RoundupException(Exception):
    '''
    used when want to handle/catch roundup specific exceptions
    '''
    pass


#######################
# ROUNDUP HISTORY FUNCS
#######################

def logHistory(msg, dt=None):
    '''
    dt: datatime.datetime object.  defaults to the current time.
    append msg to the roundup history log.  prepends the current datetime to msg by default.
    '''
    if dt is None:
        dt = datetime.datetime.now()
    # write out the message with the time prepended
    # b/c python, prior to 2.6, can not parse milliseconds, restrict output to seconds.
    util.writeToFile(dt.strftime('%Y-%m-%dT%H:%M:%S') + ' ' + str(msg), HISTORY_PATH, mode='a')


def getHistory():
    '''
    returns history as a list of [dt, msg] pairs.
    '''
    history = []
    fo = open(HISTORY_PATH)
    for line in fo:
        line = line.strip()
        if not line:
            continue
        dtStr, msg = line.split(' ', 1)
        # example dtStr: 2009-04-23T15:06:32.554601
        dt = datetime.datetime(*(time.strptime(dtStr, '%Y-%m-%dT%H:%M:%S')[0:6]))
        history.append([dt, msg])
    fo.close()
    return history


##############################
# DB PATH AND GENOME FUNCTIONS
##############################

def getGenomeDescription(genome, dir=CURRENT_GENOMES_DIR):
    '''
    returns contents of genome description of genome located under dir.
    '''
    return util.readFromFile(getDbDescriptionPathFromDbPath(makeDbPath(genome, dir=dir)))

def getDbDescriptionPathFromDbPath(dbPath):
    '''
    dbPath: location of genome.
    returns location of genome description file.
    '''
    return os.path.join(dbPath, '%s.description'%getIdFromDbPath(dbPath))


def fastaFileForDbPath(dbPath):
    dbId = getIdFromDbPath(dbPath)
    return os.path.join(dbPath, dbId)


def getIdFromDbPath(dbPath):
    return os.path.basename(dbPath)


def makeDbPath(id, dir=CURRENT_GENOMES_DIR):
    return os.path.join(dir, id)


def currentDbPath(dbId, dir=CURRENT_GENOMES_DIR):
    return makeDbPath(dbId, dir)

def updatedDbPath(dbId, dir=UPDATED_GENOMES_DIR):
    return makeDbPath(dbId, dir)


def dbPathsEqual(dbPath1, dbPath2):
    '''
    test if the two fasta files of the given dbs are equal.  If either dbPath or fasta file is non-existent, False is returned.
    returns: True iff both paths exist, both fasta files exist, and the files have the same contents.
    '''
    if os.path.exists(dbPath1) and os.path.exists(dbPath2):
        fasta1 = fastaFileForDbPath(dbPath1)
        fasta2 = fastaFileForDbPath(dbPath2)
        if os.path.exists(fasta1) and os.path.exists(fasta2) and not util.differentFiles(fasta1, fasta2):
            return True
    return False


def copyDbPathToDir(fromDbPath, toDir):
    toDbPath = makeDbPath(getIdFromDbPath(fromDbPath), dir=toDir)
    copyDbPath(fromDbPath, toDbPath)
    return toDbPath


def copyDbPath(fromDbPath, toDbPath):
    '''
    fromDbPath: path of db dir.  e.g. /groups/rodeo/compute/roundup/compute/20090319_093358_46344707-e8b6-4eba-9185-1cd0ec6def55/genomes/Homo_sapiens.aa
    toDbPath: path to copy to.  e.g. /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa
    '''
    removeDbPath(toDbPath)
    shutil.copytree(fromDbPath, toDbPath)


def removeDbPath(dbPath):
    if os.path.exists(dbPath):
        shutil.rmtree(dbPath)
    

def getGenomes(dir=CURRENT_GENOMES_DIR):
    return list(set(os.listdir(dir)))

    
def getGenomesAndPaths(dir=CURRENT_GENOMES_DIR):
    '''
    dir: directory containing genomes, e.g. /groups/rodeo/roundup/genomes/current or /groups/rodeo/compute/roundup/compute/20100315_142123_305c3d3d23fa4e8185a4d8443e4d40da/genomes
    returns: a dict mapping every genome in genomesDir to its path.
    '''
    genomesAndPaths = {}
    for genome in getGenomes(dir=dir):
        genomesAndPaths[genome] = makeDbPath(genome, dir=dir)
    return genomesAndPaths
    
    
def makeBlastDbPath(dbPath):
    '''
    dbPath: path where a genome subdir is located, e.g. /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa
    the blast index files, e.g. /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa.xpd,
    would be located at the path: /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa
    '''
    return os.path.join(dbPath, os.path.basename(dbPath))


####################################
# ROUNDUP RESULTS FILENAME FUNCTIONS
####################################

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


def splitPairDirname(path):
    '''
    path: base dirname or path to dirname of a pair dir.
    e.g. /path/to/Acinetobacter_sp_ADP1.aa_Colwellia_psychrerythraea_34H.aa
    returns: list of qdb, sdb or None if path does not parse.
    '''    
    match = re.search('^('+matchDb+')_('+matchDb+')$', os.path.basename(path))
    if not match:
        return None
    else:
        return list(match.groups())


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


def isValidRoundupFile(path):
    '''
    path: filename of existing file
    The file is valid iff it is an existing file, the name is a roundup results file name, and if the results are either empty or the first line has 3 columns.  All lines should have 3 columns, but this only checks the first.
    '''
    # not valid file
    if not isRoundupFile(path) or not os.path.isfile(path):
        logging.log(ROUNDUP_LOG_LEVEL, 'isValidRoundupFile(): not isRoundupFile or not isfile. path %s'%(path))
        return False

    # empty file
    if os.path.getsize(path) == 0:
        return True

    # superficial check for well-formed data
    handle = open(path)
    valid = (len(handle.readline().split()) == 3)
    handle.close()
    if not valid:
        logging.log(ROUNDUP_LOG_LEVEL, 'isValidRoundupFile(): not well-formed data. path %s'%(path))
    return valid


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
    a pair is a sorted tuple of genomes
    '''
    return tuple(sorted((qdb, sdb)))


def isSortedPair(qdb, sdb):
    '''
    used to check if (qdb, sdb) is a sorted pair.
    '''
    return makePair(qdb, sdb) == (qdb, sdb)


###################
# CACHING FUNCTIONS
###################
# some files are stored in a nested "cache" directory structure under dir.
# these functions map from the cache key to the file path.

def makeRoundupResultsCachePath(qdb, sdb, div, evalue, dir=CURRENT_RESULTS_DIR, create=True):
    '''
    create: if False, will not try to create missing directories.  Can be much faster.
    '''
    pair = makePair(qdb, sdb)
    name = pair[0]+'_'+pair[1]+'_'+div+'_'+evalue
    return makeCachePath(pair, name, dir=dir, create=create)


def makeBlastResultsCachePath(qdb, sdb, dir=CURRENT_RESULTS_DIR, create=True):
    '''
    for reversse blast hits, qdb and sdb are switched.
    create: if False, will not try to create missing directories.  Can be much faster.
    '''
    pair = makePair(qdb, sdb)
    name = pair[0]+'_'+pair[1]+'_blast'+BLAST_RESULTS_EXTENSION
    return makeCachePath(pair, name, dir=dir, create=create)


def makeCachePath(key, filename=None, dir=CURRENT_RESULTS_DIR, create=True):
    if filename is None:
        filename = key
    path = nested.getNestedSeedDir(str(key), dir=dir)
    if create and not os.path.isdir(path):
        logging.debug('roundup_common.makeCachePath: %s'%path)
        os.makedirs(path)
    return os.path.join(path, filename)
        
    
################################
# PARAMETER GENERATING FUNCTIONS
################################

def getPairs(genomes=None):
    '''
    returns a list of every unique combination of 2 genomes.
    Combination, not permutation.
    '''
    if genomes is None:
        genomes = getGenomes()
    pairs = util.choose(list(set(genomes)), 2)
    return normalizePairs(pairs)


def genBlastParams(qdb, sdb):
    ''' returns a list of pairs to be blasted '''
    return [[qdb, sdb], [sdb, qdb]]


def genDivEvalueParams():
    ''' used for simultaneously rounding up multiple param combinations for a pair.'''
    params = []
    for div in DIVERGENCES:
        for evalue in EVALUES:
            params.append((div, evalue))
    return params


# last line emacs python mode bug fix
