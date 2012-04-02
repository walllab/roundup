import contextlib
import os
import sys
import getpass
import ConfigParser
import platform


import logging.config
import mailutil
import orchmysql
import lsf


###############################################
# DEPLOYMENT ENVIRONMENT SPECIFIC CONFIGURATION
###############################################
# Variables from defaults, env, and generated.
# BLAST_BIN_DIR, LOG_FROM_ADDR, SITE_URL_ROOT NO_LSF, CURRENT_RELEASE,
# PROJ_DIR, HTTP_HOST PROJ_BIN_DIR
# DJANGO_DEBUG
from config.defaults import *
from config.env import *
from config.generated import *
import config.secrets



LSF_SHORT_QUEUE = 'shared_15m'
LSF_MEDIUM_QUEUE = 'shared_2h'
LSF_LONG_QUEUE = os.environ.get('ROUNDUP_LSF_LONG_QUEUE', 'shared_unlimited')

CURRENT_DATASET = os.path.join(PROJ_DIR, 'datasets', CURRENT_RELEASE)
LOG_FILE = os.path.join(PROJ_DIR, 'log/app.log')
TMP_DIR = os.path.join(PROJ_DIR, 'tmp') 

# used for contact page
RT_EMAIL = 'submit-cbi@rt.med.harvard.edu'

# Configure environment to run python and blastp
pathDirs = [BLAST_BIN_DIR, PROJ_BIN_DIR]
os.environ['PATH'] = ':'.join(pathDirs + [os.environ.get('PATH', '')]) if os.environ.has_key('PATH') else pathDirs

# Configure environment to run LSF commands
lsf.setEnviron('/opt/lsf/7.0/linux2.6-glibc2.3-x86_64', '/opt/lsf/conf')

# QUEST FOR ORTHOLOGS
QFO_VERSIONS = ['2011_04']

# Mailing
# function for sending a single text email
sendtextmail = mailutil.make_sendtextmail(sendmail)


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
#########
LOG_TO_ADDRS = ['todddeluca@gmail.com']
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
            'class': 'loggingutil.MailHandler',
            'formatter': 'default',
            'fromaddr': LOG_FROM_ADDR,
            'toaddrs': LOG_TO_ADDRS,
            'subject': LOG_SUBJECT,
            'sendmail': config.sendmail,
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

# host comes from env or config file
MYSQL_HOST = os.environ.get('ROUNDUP_MYSQL_SERVER') if os.environ.has_key('ROUNDUP_MYSQL_SERVER') \
             else config.secrets.MYSQL_HOST if hasattr(config.secrets, 'MYSQL_HOST') else None
# db comes from env or config file
MYSQL_DB = os.environ.get('ROUNDUP_MYSQL_DB') if os.environ.has_key('ROUNDUP_MYSQL_DB') \
           else config.secrets.MYSQL_DATABASE if hasattr(config.secrets, 'MYSQL_DATABASE') else None
# user comes from env or config file or the current user
MYSQL_USER = os.environ.get('ROUNDUP_MYSQL_USER') if os.environ.has_key('ROUNDUP_MYSQL_USER') \
             else config.secrets.MYSQL_USER if hasattr(config.secrets, 'MYSQL_USER') else getpass.getuser()
# password comes vrom env or config file or .my.cnf
MYSQL_PASSWORD = os.environ.get('ROUNDUP_MYSQL_PASSWORD') if os.environ.has_key('ROUNDUP_MYSQL_PASSWORD') \
                 else config.secrets.MYSQL_PASSWORD if hasattr(config.secrets, 'MYSQL_PASSWORD') else orchmysql.getCnf()['password']


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

