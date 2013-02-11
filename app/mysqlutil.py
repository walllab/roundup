

import contextlib
import logging
import time
import urlparse

import MySQLdb


@contextlib.contextmanager
def dbcreds(host, db, user, password, retries=0, sleep=0.5):
    '''
    A context manager for opening, yielding, and closing a DB API 2.0
    connection, given database credentials as parameters.
    '''
    conn = None
    try:
        conn = open_conn(host, db, user, password, retries=retries,
                         sleep=sleep)
        yield conn
    finally:
        if conn is not None:
            conn.close()


@contextlib.contextmanager
def dburl(url, retries=0, sleep=0.5):
    '''
    A context manager for opening, yielding, and closing a DB API 2.0
    connection, given database credentials as a url.
    '''
    conn = None
    try:
        conn = open_url(url, retries=retries, sleep=sleep)
        yield conn
    finally:
        if conn is not None:
            conn.close()


def open_conn(host, db, user, password, retries=0, sleep=0.5):
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
        logging.exception('open_conn(): Exception trying to open connection.  Trying again {} times.'.format(retries))
        if retries > 0:
            time.sleep(sleep)
            return open_conn(host, db, user, password, retries - 1, sleep)
        else:
            raise


def open_url(url, retries=0, sleep=0.5):
    '''
    Open a mysql connection to a url.  Note that if your password has
    punctuation characters, it might break the parsing of url.

    url: A string in the form "mysql://username:password@host.domain/database"
    '''
    return open_conn(retries=retries, sleep=sleep, **parse_url(url))


def parse_url(url):
    result = urlparse.urlsplit(url)
    # path is '', '/', or '/<database>'. Remove any leading slash to get the
    # database.
    db = result.path[1:]
    return {'host': result.hostname, 'db': db, 'user': result.username,
            'password': result.password}



