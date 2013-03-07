'''
Uses RDBMS (e.g. MySQL) to implement the ultimate in distributed, persistent, atomic and concurrent experiences.
Simple key value store.
Keys are strings.
Values are serialized as json, which supports lists, dicts, strings, numbers, None, and booleans.  http://www.json.org/

goal: no dependency on a specific RDBMS.  
goal: atomic, process-level concurrency-safe.
warning: no thread-safety guarantees.
future: replace with a real key-value store. 

usage:
Wrap a connection or a factory function in a context manager like cmutil.Noop or cmutil.ClosingFactory.

The following code illustrates creating a queue which gets a new connection for each operation by using the ClosingFactoryCM context manager.
It demonstrates putting, getting, removing, and checking for the existence of keys and values.
kv.put("hi", "test")
print kv.get("bye")
print kv.get("hi")
print kv.exists("hi")
print kv.exists("bye")
print kv.remove("hi")
print kv.exists("hi")
print kv.get("hi", "missing")
print kv.remove("bye")
'''

import contextlib
import json

import dbutil


def make_closing_connect(open_conn):
    '''
    Return a function which opens a connection and then returns a context
    manager that returns that connection when entering a context and then
    closes it when the context is exited.

    open_conn: a function which returns an open DBAPI 2.0 connection.
    '''
    def connect():
        return contextlib.closing(open_conn())


def make_reusing_connect(open_conn):
    '''
    Return a function which opens a connection the first time it is called (and
    reuses the connection in subsequent calls) and then returns a context
    manager that returns the connection when entering a context and then closes
    it when the context is exited.

    open_conn: a function which returns an open DBAPI 2.0 connection.
    '''

    conn = []
    def connect():
        if not conn:
            conn.append(open_conn())
        return conn[0]


class KVStore(object):
    '''
    A key-value store backed by a relational database. e.g. mysql.
    Upon first using a namespace, call create() to initialize the table.
    When done using a namespace, call drop() to drop the table.
    '''
    def __init__(self, connect, ns='key_value_store'):
        '''
        connect: A function which returns a context manager for getting a
        DBAPI 2.0 connection.  Typically the manager would either open and
        close a connection (to avoid maintaining a persistent connection to the
        database) or return the same open connection every time (to avoid
        opening and closing connections too rapidly) or return a connection
        from a connection pool (to avoid having too many open connections).
        ns: The "namespace" of the keys.  Should be a valid mysql table name.
        Defaults to 'key_value_store'.
        '''
        self.connect = connect
        self.table = ns


    def create(self):
        sql = '''CREATE TABLE IF NOT EXISTS ''' + self.table + ''' ( 
                 id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                 name VARCHAR(255) NOT NULL UNIQUE KEY,
                 value blob,
                 create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 INDEX key_index (name) 
                 ) ENGINE = InnoDB '''
        with self.connect() as conn:
            with dbutil.doTransaction(conn):
                dbutil.executeSQL(conn, sql)
        return self
    
        
    def drop(self):
        with self.connect() as conn:
            with dbutil.doTransaction(conn):
                dbutil.executeSQL(conn, 'DROP TABLE IF EXISTS ' + self.table)
        return self


    def reset(self):
        return self.drop().create()
    

    def get(self, key, default=None):
        encodedKey = json.dumps(key)
        with self.connect() as conn:
            sql = 'SELECT value FROM ' + self.table + ' WHERE name = %s'
            results = dbutil.selectSQL(conn, sql, args=[encodedKey])
            if results:
                value = json.loads(results[0][0])
            else:
                value = default
            return value


    def put(self, key, value):
        encodedKey = json.dumps(key)
        encodedValue = json.dumps(value)
        with self.connect() as conn:
            with dbutil.doTransaction(conn):
                sql = 'INSERT INTO ' + self.table + ' (name, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value=%s'
                return dbutil.insertSQL(conn, sql, args=[encodedKey, encodedValue, encodedValue])


    def exists(self, key):
        encodedKey = json.dumps(key)
        with self.connect() as conn:
            sql = 'SELECT id FROM ' + self.table + ' WHERE name = %s'
            results = dbutil.selectSQL(conn, sql, args=[encodedKey])
            return bool(results) # True if there are any results, False otherwise.


    def remove(self, key):
        encodedKey = json.dumps(key)
        sql = 'DELETE FROM ' + self.table + ' WHERE name = %s'
        with self.connect() as conn:
            with dbutil.doTransaction(conn):
                return dbutil.executeSQL(conn, sql, args=[encodedKey])


class KStore(object):
    '''
    Uses KVStore to manage a set of keys in a namespace.
    '''

    def __init__(self, connect, ns='key_store'):
        '''
        connect: A function which returns a context manager for getting a
        DBAPI 2.0 connection.  Typically the manager would either open and
        close a connection (to avoid maintaining a persistent connection to the
        database) or return the same open connection every time (to avoid
        opening and closing connections too rapidly) or return a connection
        from a connection pool (to avoid having too many open connections).
        ns: The "namespace" of the keys.  Should be a valid mysql table name.
        Defaults to 'key_store'.
        '''
        self.kv = KVStore(connect, ns=ns)

    def exists(self, key):
        '''
        returns: True if the key is in the namespace.  False otherwise.
        '''
        return self.kv.exists(key)

    def add(self, key):
        '''
        add key to the namespace.  it is fine to add a key multiple times.
        '''
        self.kv.put(key, True)

    def remove(self, key):
        '''
        remove key from the namespace.  it is fine to remove a key multiple times.
        '''
        self.kv.remove(key)

    def create(self):
        '''
        readies the namespace for new marks
        '''
        self.kv.create()
        return self

    def reset(self):
        '''
        clears all marks from the namespace and readies it for new marks
        '''
        self.kv.reset()
        return self

    def drop(self):
        '''
        clears all marks from the namespace and cleans it up.
        '''
        self.kv.drop()
        return self


# last line



