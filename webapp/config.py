import contextlib
import os
import sys
import getpass
import ConfigParser
import platform


import logging.config
import orchmysql
import lsf


###############################################
# DEPLOYMENT ENVIRONMENT SPECIFIC CONFIGURATION
###############################################

# NOTE: deployment magic.  when code is deployed to, e.g. production, deploy_env.py.prod -> deploy_env.py.
import deploy_env
DEPLOY_ENV = deploy_env.DEPLOY_ENV
PYTHON_EXE = deploy_env.PYTHON_EXE
os.environ['ROUNDUP_DEPLOY_ENV'] = DEPLOY_ENV # put deployment env in the environment for the java pipeline.

WEBAPP_PATH = os.path.dirname(os.path.abspath(__file__))
LSF_SHORT_QUEUE = 'shared_15m'
LSF_MEDIUM_QUEUE = 'shared_2h'
LSF_LONG_QUEUE = os.environ.get('ROUNDUP_LSF_LONG_QUEUE', 'shared_2h')


if DEPLOY_ENV == 'prod':
    CURRENT_RELEASE = '2'
    PROJ_DIR = '/groups/cbi/roundup'
    MAIL_METHOD = 'qmail'
    HTTP_HOST = 'roundup.hms.harvard.edu'
    SITE_URL_ROOT = 'http://{}'.format(HTTP_HOST)
    BLAST_BIN_DIR = '/opt/blast-2.2.24/bin'
    PROJ_BIN_DIR = '/home/td23/bin' # location of kalign
    NO_LSF = False
    LSF_SHORT_QUEUE = 'shared_lenny'
    LSF_MEDIUM_QUEUE = 'shared_lenny'
    LSF_LONG_QUEUE = 'shared_lenny'
elif DEPLOY_ENV == 'dev': 
    CURRENT_RELEASE = 'test_dataset'
    PROJ_DIR = '/groups/cbi/dev.roundup'
    MAIL_METHOD = 'qmail'
    HTTP_HOST = 'dev.roundup.hms.harvard.edu'
    SITE_URL_ROOT = 'http://{}'.format(HTTP_HOST)
    BLAST_BIN_DIR = '/opt/blast-2.2.24/bin'
    PROJ_BIN_DIR = '/home/td23/bin' # location of kalign
    NO_LSF = False
elif DEPLOY_ENV == 'local': 
    CURRENT_RELEASE = 'test_dataset'
    PROJ_DIR = os.path.expanduser('~/local.roundup')
    MAIL_METHOD = '' # not sure how to get postfix working.
    HTTP_HOST = 'localhost'
    SITE_URL_ROOT = 'http://{}:8000'.format(HTTP_HOST)
    BLAST_BIN_DIR = '/usr/local/ncbi/blast/bin'
    PROJ_BIN_DIR = '/Users/td23/bin' # location of kalign
    NO_LSF = True

CURRENT_DATASET = os.path.join(PROJ_DIR, 'datasets', CURRENT_RELEASE)
LOG_FILE = os.path.join(PROJ_DIR, 'log/app.log')
CONFIG_DIR = os.path.join(PROJ_DIR, 'config') # contains roundup_genomes.xml genome download xml config, and codeml.ctl and jones.dat used by RoundUp.py
RESULTS_DIR = os.path.join(PROJ_DIR, 'results')
GENOMES_DIR = os.path.join(PROJ_DIR, 'genomes')
TMP_DIR = os.path.join(PROJ_DIR, 'tmp')
COMPUTE_DIR = os.path.join(PROJ_DIR, 'compute')

# used for contact page
RT_EMAIL = 'submit-cbi@rt.med.harvard.edu'

# Configure environment to run python and blastp
pathDirs = [BLAST_BIN_DIR, os.path.dirname(PYTHON_EXE), PROJ_BIN_DIR]
os.environ['PATH'] = ':'.join(pathDirs + [os.environ.get('PATH', '')]) if os.environ.has_key('PATH') else pathDirs

# Configure environment to run LSF commands
lsf.setEnviron('/opt/lsf/7.0/linux2.6-glibc2.3-x86_64', '/opt/lsf/conf')


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

# configure the root logger to log all messages (>= DEBUG) to a file and email messages (>= WARNING) to admins.
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[' + platform.node() + ' %(asctime)s %(name)s %(levelname)s %(filename)s %(funcName)s line %(lineno)d] %(message)s',
            },
        },
    'handlers': {
        'file_msg': {
            'level': 'DEBUG',
            'class': 'loggingutil.ConcurrentFileHandler',
            'formatter': 'default',
            'filename': LOG_FILE,
            },
        'mail_msg': {
            'level': 'WARNING',
            'class': 'loggingutil.ClusterMailHandler',
            'formatter': 'default',
            'fromAddr': LOG_FROM_ADDR,
            'toAddrs': LOG_TO_ADDRS,
            'subject': LOG_SUBJECT,
            'method': MAIL_METHOD,
            },
        },
    'loggers': {
        '': {
            'handlers': ['file_msg', 'mail_msg'],
            'level': 'DEBUG',
            'propagate': True,
            },
        },
    }
logging.config.dictConfig(LOGGING_CONFIG)


######################################
# DATABASE CREDENTIALS AND CONNECTIONS
######################################

# read database config file
cp = ConfigParser.ConfigParser()
cp.read(os.path.join(WEBAPP_PATH, "database.ini"))
# host comes from env or config file
MYSQL_HOST = os.environ.get('ROUNDUP_MYSQL_SERVER') if os.environ.has_key('ROUNDUP_MYSQL_SERVER') \
             else cp.get(DEPLOY_ENV, 'host') if cp.has_option(DEPLOY_ENV, 'host') else None
# db comes from env or config file
MYSQL_DB = os.environ.get('ROUNDUP_MYSQL_DB') if os.environ.has_key('ROUNDUP_MYSQL_DB') \
           else cp.get(DEPLOY_ENV, 'database') if cp.has_option(DEPLOY_ENV, 'database') else None
# user comes from env or config file or the current user
MYSQL_USER = os.environ.get('ROUNDUP_MYSQL_USER') if os.environ.has_key('ROUNDUP_MYSQL_USER') \
             else cp.get(DEPLOY_ENV, 'user') if cp.has_option(DEPLOY_ENV, 'user') else getpass.getuser()
# password comes vrom env or config file or .my.cnf
MYSQL_PASSWORD = os.environ.get('ROUNDUP_MYSQL_PASSWORD') if os.environ.has_key('ROUNDUP_MYSQL_PASSWORD') \
                 else cp.get(DEPLOY_ENV, 'password') if cp.has_option(DEPLOY_ENV, 'password') else orchmysql.getCnf()['password']


def openDbConn(host=MYSQL_HOST, db=MYSQL_DB, user=MYSQL_USER, password=MYSQL_PASSWORD):
    '''
    returns: an open python DB API connection to the mysql host and db.  caller is responsible for closing the connection.
    '''
    return orchmysql.openConn(host, db, user, password, retries=1, sleep=1)


@contextlib.contextmanager
def dbConnCM(host=MYSQL_HOST, db=MYSQL_DB, user=MYSQL_USER, password=MYSQL_PASSWORD):
    '''
    context manager for opening, yielding, and closing a db connection
    '''
    with orchmysql.connCM(host, db, user, password) as conn:
        yield conn

