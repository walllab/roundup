#!/usr/bin/env python

'''
The module is a key value store with timestamps to trace creation, modification, and access of key-value pairs.

usage examples:
python -c 'import sys; sys.path.append("/groups/rodeo/dev.roundup/python"); import cacheutil, config, util;
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).set("Todd Francis DeLuca", "A swell fellow")
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).get("Todd Francis DeLuca")
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).get("Chana")
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).has_key("Chana")
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).has_key("Todd Francis DeLuca")
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).set("Todd Francis DeLuca", "Damn hot")
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).get("Todd Francis DeLuca")
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).remove("Todd Francis DeLuca")
print cacheutil.Cache(util.ClosingFactoryCM(config.openDbConn), table="roundup_cache", create=True).has_key("Todd Francis DeLuca")'
'''

import sha
import json

import dbutil


class Cache(object):
    def __init__(self, manager, table=None, drop=False, create=False):
        '''
        manager: context manager that yields a Connection.
          Typical managers are cmutil.Noop(conn) to reuse a connection or cmutil.ClosingFactory(getConnFunc) to use a new connection each time.
        table: name of table in mysql database.  should be a valid table name.  defaults to 'key_value_store'.
        '''
        self.manager = manager
        if table is None:
            self.table = 'cache'
        else:
            self.table = table
        if drop:
            self.drop()
        if create:
            self.create()


    def has_key(self, key):
        sql = " SELECT id FROM " + self.table + " WHERE id=%s"
        with self.manager as conn:
            results = dbutil.selectSQL(conn, sql, args=[self._cache_hash(key)])
            foundKey = bool(results)
            return foundKey


    def get(self, key, default=None):
        sql = " SELECT value FROM " + self.table + " WHERE id=%s"
        with self.manager as conn:
            results = dbutil.selectSQL(conn, sql, args=[self._cache_hash(key)])
            if results:
                value = json.loads(results[0][0])
            else:
                value = default

            # update access time
            sql = "UPDATE " + self.table + " SET access_time=NOW() WHERE id=%s"
            with dbutil.doTransaction(conn):
                dbutil.executeSQL(conn, sql, args=[self._cache_hash(key)])

            return value


    def set(self, key, value):
        encodedValue = json.dumps(value)
        sql = "INSERT INTO " + self.table + " (id, value, create_time, mod_time, access_time) VALUES (%s, %s, NOW(), NOW(), NOW()) "
        sql += " ON DUPLICATE KEY UPDATE value=%s, mod_time=NOW(), access_time=NOW() "
        with self.manager as conn:
            with dbutil.doTransaction(conn):
                dbutil.executeSQL(conn, sql, args=[self._cache_hash(key), encodedValue, encodedValue])


    def remove(self, key):
        sql = "DELETE FROM " + self.table + " WHERE id=%s"
        with self.manager as conn:
            with dbutil.doTransaction(conn):
                dbutil.executeSQL(conn, sql, args=[self._cache_hash(key)])


    def _cache_hash(self, key):
        '''
        the key is stored as a hash in the database.  this way any size key can fit in the column.
        the downside is the potential for key collisions.  Is this a bad design decision?
        '''
        h = sha.new(str(key)).hexdigest()
        return h


    def create(self):
        '''
        create the cache table in the database.  the table must be created before the cache functions (get, set, etc.) will work
        '''
        sql = '''CREATE TABLE IF NOT EXISTS ''' + self.table + ''' (
        `id` varchar(40) NOT NULL default '',
        `value` mediumtext,
        `create_time` datetime default NULL,
        `mod_time` datetime default NULL,
        `access_time` datetime default NULL,
        PRIMARY KEY  (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1'''
        with self.manager as conn:
            dbutil.executeSQL(conn, sql)


    def drop(self):
        '''
        drop the cache table in the database.
        '''
        sql = "DROP TABLE IF EXISTS " + self.table
        with self.manager as conn:
            dbutil.executeSQL(conn, sql)


# last line
