#!/usr/bin/env python

'''
See orchmysql.py for non-project specific credentials and connections functions.
See dbutil.py for non-project, non-orchestra specific functions for executing sql statements.

This module contains:
Functions for connecting to the orchestra mysql database for the rodeo portal project.  Also used by Roundup project.
Functions for selecting, inserting, creating tables, and more.
'''

import os
import datetime
import MySQLdb


# constants used in table info configurations
TABLE_INFO = 'table_info'
TABLE_NAME = 'table_name'
DB_NAME = 'db_name'
COLUMNS = 'columns'
COLUMN_NAME = 'column_name'
COLUMN_TYPE = 'column_type'
INDICES = 'indices'
INDEX_NAME = 'index_name'
INDEX_COLUMN_NAMES = 'index_column_names'
INDEX_PREFIX = 'index_prefix' # e.g. UNIQUE, FULLTEXT

# constants for configuring a database connection from the environment
RODEO_MYSQL_DB = 'RODEO_MYSQL_DB'
RODEO_MYSQL_PASSWORD = 'RODEO_MYSQL_PASSWORD'
RODEO_MYSQL_SERVER = 'RODEO_MYSQL_SERVER'
RODEO_MYSQL_USER = 'RODEO_MYSQL_USER'


####################
# DATABASE FUNCTIONS
####################


def withConnFromAnywhere(env=None, commit=True, host=None, db=None, username=None, password=None):
    '''
    env: environment dict containing host, db name, username, and password. defaults to os.environ
    host, db, username, password: overrides for the same values taken from env or anywhere.
    Opens a database connection with credentials taken from anywhere.
    commit: if True, will commit connection after yield returns and rollback connection if an exception occurs.
    yields: open database connection.  Closes connection after returning from yield, whether or not an exception occurs.
    (This will work properly once it is migrated to python2.5.)
    '''
    conn = None
    try:
        conn = getConnFromAnywhere(env=env, host=host, db=db, username=username, password=password)
        yield conn
        if commit == True:
            conn.commit()
        conn.close()
    except:
        if conn:
            if commit == True:
                conn.rollback()
            conn.close()
        raise

    
def getConnFromAnywhere(env=None, host=None, db=None, username=None, password=None):
    '''
    env: environment dict containing host, db name, username, and password. defaults to os.environ
    host, db, username, password: overrides for the same values taken from env or anywhere.
    Opens a database connection with credentials gotten from anywhere.
    returns: open database connection.
    '''
    return getDatabaseFromAnywhere(env=env, host=host, db=db, username=username, password=password).openConn()


def getDatabaseFromAnywhere(env=None, host=None, db=None, username=None, password=None):
    '''
    env: environment dict containing host, db name, username, and password. defaults to os.environ
    host, db, username, password: overrides for the same values taken from env or anywhere.
    Creates a new Database object with credentials gotten from anywhere.
    returns: database object.
    '''
    creds = getCredsFromAnywhere(env=env)
    for key, param in zip(['host', 'db', 'username', 'password'], [host, db, username, password]):
        if param is not None:
            creds[key] = param
    return Database(**creds)


def getCredsFromAnywhere(env=None, host=None, db=None, username=None, password=None):
    '''
    env: environment dict containing host, db name, username, and password. defaults to os.environ
    Tries to get credentials from the environment and if that fails from a .my.cnf file. 
    returns: dict with keywords needed to initialize Database object.
    '''
    try:
        return getCredsFromEnv(env=env)
    except:
        return getCredsFromMyCnfFileAndEnv(env=env)

    
def getCredsFromEnv(env=None):
    '''
    env: environment dict containing host, db name, username, and password. defaults to os.environ
    returns: dict with keywords needed to initialize Database object.
    throws: Exception if there are any missing values.
    '''
    if env == None:
        env = os.environ
    credKeys = ['host', 'db', 'username', 'password']
    envKeys = [RODEO_MYSQL_SERVER, RODEO_MYSQL_DB, RODEO_MYSQL_USER, RODEO_MYSQL_PASSWORD]
    creds = {}
    for credKey, envKey in zip(credKeys, envKeys):
        if not env.has_key(envKey):
            raise Exception('Environment variable not defined: '+envKeys[i])
        else:
            creds[credKey] = env[envKey]
    return creds


def getCredsFromMyCnfFileAndEnv(env=None):
    '''
    gets username from the environment, and host, database, and password from .my.cnf file
    in home dir of user.
    returns: dict with keywords needed to initialize Database object.
    throws: Exception if there are any missing values.
    '''
    if env == None:
        env = os.environ

    configFileName = '.my.cnf'
    usage = 'HOME and (USER or LOGNAME) must be defined in the environment; '+configFileName+' must be defined in the HOME dir; and "database", "password", and "host" variables must be defined in '+configFileName+' file.'
    if not env.has_key('HOME'):
        raise Exception('Missing HOME env var. '+usage)
    if env.has_key('USER'):
        username = env['USER']
    elif env.has_key('LOGNAME'):
        username = env['LOGNAME']
    else:
        raise Exception('Missing USER and LOGNAME env vars. '+usage)


    myCnfFile = os.path.join(env['HOME'], configFileName)
    # read cnf config file into a dict
    cnf = {}
    if os.path.isfile(myCnfFile):
        for line in open(myCnfFile):
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            if '=' in line:
                key, value = [piece.strip() for piece in line.split('=', 1)]
                cnf[key] = value

    if not cnf.has_key('database'):
        raise Exception(configFileName+' missing database key.')
    if not cnf.has_key('password'):
        raise Exception(configFileName+' missing password key.')
    if not cnf.has_key('host'):
        raise Exception(configFileName+' missing host key.')

    creds = {'host': cnf['host'], 'db': cnf['database'], 'password': cnf['password'], 'username': username}
    return creds


class Database:
    '''
    generic database class, useful for getting connections, and executing arbitrary queries
    '''

    def __init__(self, host, db, username, password):
        self.host = host
        self.db = db
        self.username = username
        self.password = password


    def initFromEnv(cls, env=None):
        '''
        Class Method Constructor
        env: environment dict containing host, db name, username, and password. optional.
        os.environ used if env is not specified.
        returns Database object.
        throws Exception if an environment variable is missing.
        '''

        creds = getCredsFromEnv(env)
        return Database(**creds)
    initFromEnv = classmethod(initFromEnv)


    def openConn(self):
        # logging.debug('openConn() host, db, username, passwordlen: %s %s %s %d'%(self.host, self.db, self.username, len(self.password)))
        return MySQLdb.connect(host=self.host, user=self.username, passwd=self.password, db=self.db)

    
    def withConn(self):
        '''usage: for conn in db.withConn():
        opens a connection to the db which is closed after the scope
        of the for block.  hacked up, since python only offers yield
        in for blocks, unlike lisp or ruby.  In ruby it would look more
        like: db.withConn() { |conn| "do stuff with conn" }
        '''
        
        conn = self.openConn()
        yield conn
        conn.commit()
        conn.close()


    def execQuery(self, query):
        ''' open a connection to the db, execute a query'''

        # logging.debug('query='+query)
        for conn in self.withConn():
            # create a cursor
            cursor = conn.cursor()
            
            # execute SQL statement
            cursor.execute(query)
            
            # get the resultset as a tuple of tuples
            results = cursor.fetchall()
            # logging.debug('results='+str(results))
            cursor.close()
        return results




def doWithConn(func, conn=None, commit=True):
    '''
    func: function which takes one argument, a connection.
    conn: a mysql db connection.  If none given, one will be opened, used, and closed.
    commit: if True, the connection will be committed after func() is called.
    returns: return value of func
    '''
    if conn == None:
        conn = getConnFromAnywhere()
        closeConn = True
    else:
        closeConn = False

    try:
        retval = func(conn)
        
        if commit and conn:
            conn.commit()
        if closeConn and conn:
            conn.close()

        return retval
    except:
        if closeConn and conn:
            conn.rollback()
            conn.close()
        raise


def selectSQL(sql, conn=None, args=None, commit=True):
    '''
    sql: a select statement
    args: if sql has parameters defined with either %s or %(key)s then args should be a either list or dict of parameter
    values respectively.
    returns a tuple of rows, each of which is a tuple.
    '''
    def func(conn):
        # logging.debug('selectSQL: sql='+str(sql)+' args='+str(args))
        cursor = conn.cursor()
        cursor.execute(sql, args)
        results = cursor.fetchall()
        cursor.close()
        return results

    return doWithConn(func, conn, commit)


def insertSQL(sql, conn=None, commit=True, args=None):
    '''
    args: if sql has parameters defined with either %s or %(key)s then args should be a either list or dict of parameter
    values respectively.
    returns the insert id
    '''
    def func(conn):
        # logging.debug('insertSQL: sql='+str(sql)+' args='+str(args))
        cursor = conn.cursor()
        cursor.execute(sql, args)
        id = conn.insert_id()
        cursor.close()
        return id

    return doWithConn(func, conn, commit)


def updateSQL(sql, conn=None, commit=True, args=None):
    '''
    args: if sql has parameters defined with either %s or %(key)s then args should be a either list or dict of parameter
    values respectively.
    returns the number of rows affected by the sql statement
    '''
    def func(conn):
        # logging.debug('updateSQL: sql='+str(sql)+' args='+str(args))
        cursor = conn.cursor()
        numRowsAffected = cursor.execute(sql, args)
        cursor.close()
        return numRowsAffected

    return doWithConn(func, conn, commit)


def executeSQL(sql, conn=None, commit=True, args=None):
    '''
    args: if sql has parameters defined with either %s or %(key)s then args should be a either list or dict of parameter
    values respectively.
    executes sql statement.  useful for executing statements like CREATE TABLE or RENAME TABLE,
    which do not have an result like insert id or a rowset.
    returns: the number of rows affected by the sql statement if any.
    '''
    def func(conn):
        # logging.debug('executeSQL: sql='+str(sql)+' args='+str(args))
        cursor = conn.cursor()
        numRowsAffected = cursor.execute(sql, args)
        cursor.close()
        return numRowsAffected

    return doWithConn(func, conn, commit)


def executeManySQL(sql, args=None, conn=None, commit=True):
    '''
    args: list of groups of arguments.  if sql has parameters defined with either %s or %(key)s then groups should be a either lists or dicts of parameter
    values respectively.
    returns: not sure.  perhaps number of rows affected.
    '''
    def func(conn):
        # logging.debug('insertSQL: sql='+str(sql)+' args='+str(args))
        cursor = conn.cursor()
        retval = cursor.executemany(sql, args)
        cursor.close()
        return retval

    return doWithConn(func, conn, commit)


def selectManySQL(sql, args=None, conn=None, commit=True):
    '''
    sql: a select statement
    args: a list of groups of args.  if sql has parameters defined with either %s or %(key)s then each group should be a either list or dict of parameter
    values respectively.
    runs sql query with each group of args.
    returns: all the rows from all the queries.
    '''
    def func(conn):
        cursor = conn.cursor()
        results = []
        for group in args:
            cursor.execute(sql, group)
            results.extend(cursor.fetchall())
        cursor.close()
        return results

    return doWithConn(func, conn, commit)


def insertManySQL(sql, conn=None, commit=True, args=None):
    '''
    args: a list of groups of args.  if sql has parameters defined with either %s or %(key)s then each group should be a either list or dict of parameter
    values respectively.
    returns: list of insert ids for each arg group in args.  FYI, the id of an ignored insert is 0.
    '''
    def func(conn):
        cursor = conn.cursor()
        insertIds = []
        for group in args:
            cursor.execute(sql, group)
            id = conn.insert_id()
            insertIds.append(id)
        cursor.close()
        return insertIds

    return doWithConn(func, conn, commit)


# use this function to escape strings being inserted into the db
# e.g. "blah 3' blah" -> "blah 3\' blah" (quotes get escaped)
escStr = MySQLdb.escape_string


def getNowInSQLFormat():
    '''
    returns date and hours,mins,secs: e.g. '2005-02-10 19:59:37'
    '''
    return str(datetime.datetime.now())[0:-7]


def getMysqlUniqueId(conn):
    '''
    Uses mysql UUID() function to generate a universally unique string, like 41c2804e-9911-1028-8d31-000d601ab426.
    Hyphens are replaced by underscores, so the string can be used as a unique variable name in python (and other
    programming languages which do not allow a minus sign in an identifier).  To use as a var name, one might have to prepend
    a letter if the uuid does not start with one, since var names are often required to start with a letter.
    returns: universally unique string.
    '''
    uuid = selectSQL('SELECT UUID()', conn)[0][0]
    uuid = uuid.replace('-', '_')
    return uuid


def tableExists(conn, tableInfo):
    '''
    tableInfo: dict containing table name and db name of table.
    checks for the existence of table in the database.
    returns: true iff the table exists
    '''
    dbName = tableInfo[DB_NAME]
    tableName = tableInfo[TABLE_NAME]
    return tableExistsByName(conn, [dbName, tableName])


def tableExistsByName(conn, namePair):
    '''
    namePair: pair of dbName, tableName.  dbName may be None
    '''
    dbName = namePair[0]
    tableName = namePair[1]
    sql = 'SHOW TABLES'
    if dbName:
        sql += ' FROM '+escStr(dbName)
    sql += ' LIKE %s'
    rows = selectSQL(sql, conn, [tableName])
    return bool(rows)


def makeDbAndTableName(tableInfo):
    return joinDbAndTableName(*makeDbAndTableNamePair(tableInfo))


def makeDbAndTableNamePair(tableInfo):
    dbName = None
    if tableInfo.has_key(DB_NAME):
        dbName = tableInfo[DB_NAME]
    return [dbName, tableInfo[TABLE_NAME]]


def joinDbAndTableName(dbName, tableName):
    if dbName:
        return dbName+'.'+tableName
    else:
        return tableName


def makeCreateTableSql(tableInfo):
    '''
    tableInfo: dict describing table
    '''
    createDescs = [col[COLUMN_NAME]+' '+col[COLUMN_TYPE] for col in tableInfo[COLUMNS]]
    if tableInfo.has_key(INDICES):
        createDescs += [makeCreateIndexDescSQL(index) for index in tableInfo[INDICES]]
    return 'CREATE TABLE IF NOT EXISTS '+makeDbAndTableName(tableInfo)+' ('+', '.join(createDescs)+')'


def makeCreateIndexDescSQL(indexInfo):
    '''
    indexInfo: dict containing index name, type and columns
    returns: mysql index create description fragment for a create table statement.
    '''
    if indexInfo.has_key(INDEX_PREFIX):
        sql = indexInfo[INDEX_PREFIX] + ' INDEX'
    else:
        sql = 'INDEX'
    
    if indexInfo.has_key(INDEX_NAME):
        sql += ' '+indexInfo[INDEX_NAME]
    sql += ' (' + ', '.join(indexInfo[INDEX_COLUMN_NAMES]) + ')'
    return sql


def dropTable(conn=None, tableInfo=None):
    if tableInfo:
        dropTableByName(conn, makeDbAndTableNamePair(tableInfo))


def dropTableByName(conn, namePair):
    '''
    namePair: pair of dbName, tableName.  dbName may be None
    '''
    sql = 'DROP TABLE IF EXISTS '+joinDbAndTableName(*namePair)
    retval = executeSQL(sql, conn)


def createTable(conn=None, tableInfo=None):
    if tableInfo:
        sql = makeCreateTableSql(tableInfo)
        retval = executeSQL(sql, conn)


def renameTables(conn, tableInfoPairs):
    '''
    tableInfoPairs: a list of pairs of table infos
    For each pair, renames the first table to the second table.
    The second table in the pair should not exist (or should have been renamed earlier.)
    '''
    renameTablesByNames(conn, [[makeDbAndTableNamePair(infoPair[0]), makeDbAndTableNamePair(infoPair[1])] for infoPair in tableInfoPairs])


def renameTablesByNames(conn, listOfPairsOfDbAndTableNamePairs):
    '''
    listOfPairsOfDbAndTableNamePairs: a list of "rename" pairs (rename foo to bar), where each element in the rename pair is a pair of (dbName, tableName).
      dbName may be None and it will default to the default db of conn.
      e.g. [[['go', 'temp'], ['go', 'term']], [['rodeo', 'users'], ['rodeo', 'backup_users']]]
    '''
    if listOfPairsOfDbAndTableNamePairs:
        renameClauses = [joinDbAndTableName(*renamePair[0])+' TO '+joinDbAndTableName(*renamePair[1]) for renamePair in listOfPairsOfDbAndTableNamePairs]
        sql = 'RENAME TABLE '+', '.join(renameClauses)
        retval = executeSQL(sql, conn)


def getValueForId(id, conn, tableName, idCol='id', valueCol='value', dbName=None):
    '''
    id: id for a table row.
    returns: value found in valueCol for the first row identified with id.
    '''
    # using getIdForValue, but that seems a little twisted.  Maybe should call it something different, or even better, use an existing O-R mapping module.
    return getIdForValue(value=id, conn=conn, tableName=tableName, idCol=valueCol, valueCol=idCol, dbName=dbName, insertMissing=False)


def getIdForValue(value, conn=None, tableName=None, idCol='id', valueCol='value', dbName=None, insertMissing=False):
    '''
    dbName: name of the database or schema the table is in.  if None, defaults to the current db or schema of the connection
    tableName: name of enumeration lookup table
    idCol: name of column which contains enumeration id
    valueCol: name of column which contains the value of the enumeration
    value: value to look up the id for.
    insertMissing: if True and the value is not found, 
    Searches the table for the id corresponding to the given value.
    If the value is not in the table, adds it, returning the id for the newly added enum value.
    return: id found in the idCol for the first row containing value in the valueCol.
    '''
    if tableName == None:
        return None
    def getId():
        sql = 'SELECT '+idCol+' FROM '+joinDbAndTableName(dbName, tableName)+' WHERE '+valueCol+' = %s'
        rowset = selectSQL(sql, conn, args=[value])
        if rowset:
            return rowset[0][0]
        else:
            return None

    id = getId()
    if id is None and insertMissing:
        sql = 'INSERT INTO '+joinDbAndTableName(dbName, tableName)+' ('+valueCol+') VALUES (%s)'
        insertId = insertSQL(sql, conn, args=[value])
        id = getId()
    return id


def getIdForValues(values, tableName, dbName=None, conn=None, idCol='id', valueCols=('value',), insertMissing=False):
    '''
    values: list of values to look up the id with
    tableName: name of table containing values and id
    dbName: db prefix for table
    conn: database connection, commit connection if insertMissing is true and you want any inserted missing values to be committed.
    valueCols: list of field names of the values (in the same order as the values list)
    insertMissing: if the id is not found, values will be inserted into the table and insertion id will be returned.
    '''
    # join all the value columns with AND
    def getId():
        sql = 'SELECT '+idCol+' FROM '+joinDbAndTableName(dbName, tableName)+' WHERE ' + ' AND '.join(valueCol+' = %s' for valueCol in valueCols)
        rowset = selectSQL(sql, conn, args=values)
        if rowset:
            return rowset[0][0]
        else:
            return None

    id = getId()
    if id is None and insertMissing:
        sql = 'INSERT INTO '+joinDbAndTableName(dbName, tableName)+' ('+', '.join(valueCols)+') VALUES ('+', '.join('%s' for v in values)+')'
        insertId = insertSQL(sql, conn, args=values)
        id = getId()
    return None    
    
    
class DbCursorIter:
    '''
    Iterator over the rows of a MySQLdb cursor.  Useful after a select statement has been executed.
    Reads rows N at a time, buffering them, for greater efficiency (I hope.)
    '''
    def __init__(self, cursor, bufferRows=1, close=True):
        '''
        cursor: MySQLdb cursor object after a select statement has been executed.
        bufferRows: number of rows to pull from the cursor at a time.  Defaults to one.  Should be >= 1.
        close: if True, close cursor when finished reading rows from it.  Defaults to True.
        '''
        self.close = close
        self.cursor = cursor
        self.buffer = []
        self.bufferRows = bufferRows

    def __iter__(self):
        return self

    def next(self):
        if not self.buffer:
            rows = self.cursor.fetchmany(self.bufferRows)
            if not rows:
                if self.close:
                    self.cursor.close()
                raise StopIteration()
            self.buffer = list(rows)
        return self.buffer.pop(0)


#############################
# MAIN COMMAND LINE FUNCTIONS
#############################


def main():
    pass

if __name__ == '__main__':
    main()
