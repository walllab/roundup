import contextlib
import os
import getpass
import platform


import logging.config
import lsf
import mailutil
import orchmysql
import util



###############################################
# DEPLOYMENT ENVIRONMENT SPECIFIC CONFIGURATION

from deployenv import (BLAST_BIN_DIR, ARCHIVE_DATASETS, CURRENT_DATASET, DJANGO_DEBUG, HTTP_HOST,
                       KALIGN_BIN_DIR, LOG_FROM_ADDR, MAIL_SERVICE_TYPE,
                       NO_LSF, SITE_DIR, SITE_URL_ROOT)
import secrets


# Silence pyflakes complaints about imports not being used. :-(
DJANGO_DEBUG, HTTP_HOST, NO_LSF, SITE_URL_ROOT

# Roundup Datasets and Releases
CURRENT_DATASET = os.path.expanduser(CURRENT_DATASET)
CURRENT_RELEASE = os.path.basename(CURRENT_DATASET)
ARCHIVE_RELEASES = [os.path.basename(ds) for ds in ARCHIVE_DATASETS]

# used for contact page
RT_EMAIL = 'submit-cbi@rt.med.harvard.edu'

# Configure environment to run python and blastp
pathDirs = [BLAST_BIN_DIR, KALIGN_BIN_DIR]
if 'PATH' in os.environ:
    pathDirs.append(os.environ['PATH'])
os.environ['PATH'] = ':'.join(pathDirs)

# Configure environment to run LSF commands
lsf.setEnviron('/opt/lsf/7.0/linux2.6-glibc2.3-x86_64', '/opt/lsf/conf')

# The physical location of static files served under the '/static/' url.
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'public/static'))


#########
# Mailing

# function for sending a single email
if MAIL_SERVICE_TYPE == 'amazon_ses':
    sendmail = mailutil.SMTPSSL(
        'smtp.orchestra', 25, username=secrets.AMAZON_SES_SMTP_USERNAME,
        password=secrets.AMAZON_SES_SMTP_PASSWORD).sendone
elif MAIL_SERVICE_TYPE == 'orchestra':
    sendmail = mailutil.SMTP('smtp.orchestra', 25).sendone
else:
    raise Exception('Unrecognized MAIL_SERVICE_TYPE', MAIL_SERVICE_TYPE)

# function for sending a single text email
sendtextmail = mailutil.make_sendtextmail(sendmail)


#######################################
# TMP DIRS, WORKING DIRS, SCRATCH SPACE

TMP_DIR = os.path.join(SITE_DIR, 'tmp') 
os.environ['NESTED_TMP_DIR'] = TMP_DIR


#####################
# CACHE CONFIGURATION
# warning: www/support/roundup/common.php implements identical caching functions as cacheutil.py that also use roundup_cache table.
#   common.php caching must be kept in sync with the python caching code.
CACHE_TABLE = 'roundup_cache'


#########
# LOGGING

LOG_FILE = os.path.join(SITE_DIR, 'log/app.log')
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
            'sendmail': sendmail,
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

# Get credentials from the environment
# MYSQL_HOST = os.environ.get('ROUNDUP_MYSQL_HOST')
# MYSQL_DB = os.environ.get('ROUNDUP_MYSQL_DB')
# MYSQL_USER = os.environ.get('ROUNDUP_MYSQL_USER')
# MYSQL_PASSWORD = os.environ.get('ROUNDUP_MYSQL_PASSWORD')
# Get credentials from a configuration file
MYSQL_HOST = secrets.MYSQL_HOST
MYSQL_DB = secrets.MYSQL_DATABASE
MYSQL_USER = secrets.MYSQL_USER
MYSQL_PASSWORD = secrets.MYSQL_PASSWORD
# Get credentials from a ~/.my.cnf file
if util.getBoolFromEnv('ROUNDUP_MYSQL_CREDS_FROM_CNF', False):
    MYSQL_USER = getpass.getuser()
    MYSQL_PASSWORD = orchmysql.getCnf()['password']

MYSQL_URL = 'mysql://{user}:{password}@{host}/{db}'.format(
    user=MYSQL_USER, password=MYSQL_PASSWORD, host=MYSQL_HOST, db=MYSQL_DB)
os.environ['ROUNDUP_MYSQL_URL'] = MYSQL_URL


def openDbConn(host=MYSQL_HOST, db=MYSQL_DB, user=MYSQL_USER, password=MYSQL_PASSWORD):
    '''
    returns: an open python DB API connection to the mysql host and db.  caller is responsible for closing the connection.
    '''
    # include one paused retry in case db is getting hammered.
    return orchmysql.openConn(host, db, user, password, retries=1, sleep=1)


@contextlib.contextmanager
def dbConnCM(host=MYSQL_HOST, db=MYSQL_DB, user=MYSQL_USER, password=MYSQL_PASSWORD):
    '''
    context manager for opening, yielding, and closing a db connection
    '''
    with orchmysql.connCM(host, db, user, password) as conn:
        yield conn

