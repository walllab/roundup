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
Here config.openDbConn is a function that returns a python db api v2 connection.
python -c'
import kvstore, util, config;
kv = kvstore.KVStore(util.ClosingFactoryCM(config.openDbConn), drop=True, create=True)
kv.put("hi", "test")
print kv.get("bye")
print kv.get("hi")
print kv.exists("hi")
print kv.exists("bye")
print kv.remove("hi")
print kv.exists("hi")
print kv.get("hi", "missing")
print kv.remove("bye")
'
'''

import json

import dbutil


class KVStore(object):
    def __init__(self, manager, table=None, drop=False, create=False):
        '''
        manager: context manager yielding a Connection.
          Typical managers are cmutil.Noop(conn) to reuse a connection or cmutil.ClosingFactory(getConnFunc) to use a new connection each time.
        table: name of table in mysql database.  should be a valid table name.  defaults to 'key_value_store'.
        '''
        self.manager = manager
        if table is None:
            self.table = 'key_value_store'
        else:
            self.table = table
        if drop:
            self._drop()
        if create:
            self._create()


    def _create(self):
        sql = '''CREATE TABLE IF NOT EXISTS ''' + self.table + ''' ( 
                 id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                 name VARCHAR(200) NOT NULL UNIQUE KEY,
                 value blob,
                 create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 INDEX key_index (name) 
                 ) ENGINE = InnoDB '''
        with self.manager as conn:
            with dbutil.doTransaction(conn):
                dbutil.executeSQL(conn, sql)

        
    def _drop(self):
        with self.manager as conn:
            with dbutil.doTransaction(conn):
                dbutil.executeSQL(conn, 'DROP TABLE IF EXISTS ' + self.table)
        

    def get(self, key, default=None):
        with self.manager as conn:
            sql = 'SELECT value FROM ' + self.table + ' WHERE name = %s'
            results = dbutil.selectSQL(conn, sql, args=[key])
            if results:
                value = json.loads(results[0][0])
            else:
                value = default
            return value


    def put(self, key, value):
        with self.manager as conn:
            with dbutil.doTransaction(conn):
                encodedValue = json.dumps(value)
                sql = 'INSERT INTO ' + self.table + ' (name, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value=%s'
                return dbutil.insertSQL(conn, sql, args=[key, encodedValue, encodedValue])


    def exists(self, key):
        with self.manager as conn:
            sql = 'SELECT id FROM ' + self.table + ' WHERE name = %s'
            results = dbutil.selectSQL(conn, sql, args=[key])
            return bool(results)


    def remove(self, key):
        sql = 'DELETE FROM ' + self.table + ' WHERE name = %s'
        with self.manager as conn:
            with dbutil.doTransaction(conn):
                return dbutil.executeSQL(conn, sql, args=[key])
            

# last line



