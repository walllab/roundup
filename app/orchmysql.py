'''
The module contains functionality to get mysql credentials and mysql connection objects on the orchestra system.
FromAnywhere means first checking in the environment and then looking in a credentials file.
An application using this module will typically do some of the following to get credentials:
  set up some credentials in a configuration file (e.g. host) an application specific and deployment environment specific manner;
  get some creds from the environment, like creds set up by a web server;
  get some creds from a DEFAULT_CREDS_FILE, especially when the application is not used via the web server.
Once credentials are obtained, an application will typically use them to get a connection to the mysql database.
'''

import contextlib
import MySQLdb
import os
import time
import logging


DEFAULT_CREDS_FILE = '.my.cnf' # in HOME dir.  

######################
# DATABASE CREDENTIALS
######################


def getCredsFromAnywhere(hostKey, dbKey, userKey, passwordKey, credsFile=None):
    host = getHostFromAnywhere(hostKey, credsFile)
    db = getDbFromAnywhere(dbKey, credsFile)
    user = getUserFromAnywhere(userKey, credsFile)
    password = getPasswordFromAnywhere(passwordKey, credsFile)
    return {'host': host, 'db': db, 'user': user, 'password': password}
    

def getHostFromAnywhere(key, credsFile=None):
    if os.environ.has_key(key):
        return os.environ[key]
    return getCnf(credsFile)['host']


def getDbFromAnywhere(key, credsFile=None):
    if os.environ.has_key(key):
        return os.environ[key]
    return getCnf(credsFile)['database']    


def getUserFromAnywhere(key, credsFile=None):
    if os.environ.has_key(key):
        return os.environ[key]
    if os.environ.has_key('USER'):
        return os.environ['USER']
    if os.environ.has_key('LOGNAME'):
        return os.environ['LOGNAME']
    else:
        raise Exception('Missing USER and LOGNAME env vars. ')


def getPasswordFromAnywhere(key, credsFile=None):
    if os.environ.has_key(key):
        return os.environ[key]
    return getCnf(credsFile)['password']


CNF_CACHE = []
def getCnf(credsFile=None):
    if not CNF_CACHE:
        if credsFile is None:
            credsFile = os.path.join(os.environ['HOME'], DEFAULT_CREDS_FILE)
        cnf = parseCnfFile(credsFile)
        CNF_CACHE.append(cnf)
    return CNF_CACHE[0]


def parseCnfFile(path):
    # read cnf config file into a dict
    cnf = {}
    if os.path.isfile(path):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            if '=' in line:
                key, value = [piece.strip() for piece in line.split('=', 1)]
                cnf[key] = value
    return cnf    


######################
# DATABASE CONNECTIONS
######################


@contextlib.contextmanager
def connCM(host, db, user, password):
    try:
        conn = openConn(host, db, user, password)
        yield conn
    finally:
        conn.close()
        

def openConn(host, db, user, password, retries=0, sleep=0.5):
    '''
    Return an open mysql db connection using the given credentials.  Use
    `retries` and `sleep` to be robust to the occassional transient connection
    failure.

    retries: if an exception when getting the connection, try again at most this many times.
    sleep: pause between retries for this many seconds.  a float >= 0.
    '''
    assert retries >= 0

    try:
        return MySQLdb.connect(host=host, user=user, passwd=password, db=db)
    except Exception:
        logging.exception('openConn(): exception trying to open connection.  will try again {} times.'.format(retries))
        if retries > 0:
            time.sleep(sleep)
            return openConn(host, db, user, password, retries - 1, sleep)
        else:
            raise


# last line
