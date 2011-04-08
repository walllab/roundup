import contextlib
import os
import sys


import loggingutil
import orchmysql


###############################################
# DEPLOYMENT ENVIRONMENT SPECIFIC CONFIGURATION
###############################################

# are we in development or production environment?
if os.path.dirname(os.path.abspath(__file__)).startswith('/groups/rodeo/roundup/'):
    DEPLOY_ENV = 'prod'
else:
    DEPLOY_ENV = 'dev'

if DEPLOY_ENV == 'prod':
    LOG_FILE = os.path.join('/groups/rodeo/roundup/log/python_roundup.log')
    CONFIG_DIR = '/groups/rodeo/roundup/config' # contains roundup_genomes.xml genome download xml config, and codeml.ctl and jones.dat used by RoundUp.py
    RESULTS_DIR = '/groups/rodeo/roundup/results'
    GENOMES_DIR = '/groups/rodeo/roundup/genomes'
    MYSQL_HOST = 'mysql.cl.med.harvard.edu'
    MYSQL_DB = 'roundup'
    TMP_DIR = '/groups/rodeo/roundup/tmp'
    COMPUTE_DIR = '/groups/rodeo/roundup/compute'
else: # default to dev
    LOG_FILE = os.path.join('/groups/rodeo/dev.roundup/log/python_roundup.log')
    CONFIG_DIR = '/groups/rodeo/dev.roundup/config' # contains roundup_genomes.xml genome download xml config, and codeml.ctl and jones.dat used by RoundUp.py
    RESULTS_DIR = '/groups/rodeo/dev.roundup/results'
    GENOMES_DIR = '/groups/rodeo/dev.roundup/genomes'
    MYSQL_HOST = 'dev.mysql.cl.med.harvard.edu'
    MYSQL_DB = 'devroundup'
    TMP_DIR = '/groups/rodeo/dev.roundup/tmp'
    COMPUTE_DIR = '/groups/rodeo/dev.roundup/compute'


#####
# RSD
#####

MAX_HITS = 3
MATRIX_PATH = os.path.join(CONFIG_DIR, 'jones.dat')
CODEML_CONTROL_PATH = os.path.join(CONFIG_DIR, 'codeml.ctl')


#######################################
# TMP DIRS, WORKING DIRS, SCRATCH SPACE
#######################################

os.environ['NESTED_TMP_DIR'] = TMP_DIR


#####################
# CACHE CONFIGURATION
#####################
# warning: www/support/roundup/common.php implements identical caching functions as cacheutil.py that also use roundup_cache table.
#   common.php caching must be kept in sync with the python caching code.
CACHE_TABLE = 'roundup_cache'


#########
# LOGGING
#########
LOG_TO_ADDRS = ['todddeluca@gmail.com']
LOG_FROM_ADDR = 'roundup-noreply@hms.harvard.edu'
LOG_SUBJECT = 'Roundup Logging Message'
LOG_LEVEL = 10
loggingutil.setupLogging(logFile=LOG_FILE, fromAddr=LOG_FROM_ADDR, toAddrs=LOG_TO_ADDRS, subject=LOG_SUBJECT, loggingLevel=LOG_LEVEL)

# last line



##########
# DATABASE
##########

# CAN OVERRIDE CREDS USING THESE ENV VARS
if os.environ.has_key('ROUNDUP_MYSQL_DB'):
    MYSQL_DB = os.environ.get('ROUNDUP_MYSQL_DB')
if os.environ.has_key('ROUNDUP_MYSQL_SERVER'):
    MYSQL_HOST = os.environ.get('ROUNDUP_MYSQL_SERVER')
MYSQL_USER = orchmysql.getUserFromAnywhere('ROUNDUP_MYSQL_USER')
MYSQL_PASSWORD = orchmysql.getPasswordFromAnywhere('ROUNDUP_MYSQL_PASSWORD')

def openDbConn(host=MYSQL_HOST, db=MYSQL_DB, user=MYSQL_USER, password=MYSQL_PASSWORD):
    '''
    returns: an open python DB API connection to the mysql host and db.  caller is responsible for closing the connection.
    '''
    return orchmysql.openConn(host, db, user, password)

@contextlib.contextmanager
def dbConnCM(host=MYSQL_HOST, db=MYSQL_DB, user=MYSQL_USER, password=MYSQL_PASSWORD):
    '''
    context manager for opening, yielding, and closing a db connection
    '''
    with orchmysql.connCM(host, db, user, password) as conn:
        yield conn

