#!/usr/bin/env python

'''
Central place for code which accesses the mysql RDBMS that contains the roundup results data.
Defines an API for accessing and storing roundup results in the db.

DATABASES:
go
(dev)roundup
                                           
'''

import MySQLdb.cursors
import os
import re
import zlib
import cPickle
import logging

import config
import util
import execute
import roundup_common
import dbutil


# get mysql server/host and database from deployment location, defaulting to dev.  override if defined in environment.
ROUNDUP_MYSQL_DB = config.MYSQL_DB


###############################
# DATABASE CONNECTION FUNCTIONS
###############################

def withRoundupDbConn(conn=None, commit=True):
    if conn == None:
        with config.dbConnCM() as conn:
            if commit:
                with dbutil.doTransaction(conn) as conn:
                    yield conn
            else:
                yield conn
    else:
        try:
            yield conn
        except:
            if commit:
                conn.rollback()
        else:
            if commit:
                conn.commit()


#################################
# TABLE CREATE AND DROP FUNCTIONS
#################################

# tables downloaded from ncbi: gene2accessin, gene2go, gene_info
# tables downloaded from gene ontology: go.term, ...


def dropRoundupResultsTable(conn=None):
    sql = 'DROP TABLE IF EXISTS '+ROUNDUP_MYSQL_DB+'.roundup_results'
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def createRoundupResultsTable(conn=None):
    sql = '''CREATE TABLE IF NOT EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_results
    (id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    query_db SMALLINT UNSIGNED NOT NULL,
    subject_db SMALLINT UNSIGNED NOT NULL,
    divergence TINYINT UNSIGNED NOT NULL,
    evalue TINYINT UNSIGNED NOT NULL,
    filename TEXT,
    mod_time DATETIME DEFAULT NULL,
    orthologs LONGBLOB,
    num_orthologs INT UNSIGNED NOT NULL,
    KEY query_db_index (query_db),
    KEY subject_db_index (subject_db),
    UNIQUE KEY params_key (query_db, subject_db, divergence, evalue) ) ENGINE = InnoDB'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def dropRoundupSequenceTable(conn=None):
    sql = '''DROP TABLE IF EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def createRoundupSequenceTable(conn=None):
    sql = '''CREATE TABLE IF NOT EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence
        (id int unsigned auto_increment primary key,
        external_sequence_id varchar(100) NOT NULL,
        genome_id smallint(5) unsigned NOT NULL,
        gene_name varchar(20),
        gene_id int,
        KEY genome_index (genome_id),
        UNIQUE KEY sequence_and_genome (external_sequence_id, genome_id) ) ENGINE = InnoDB'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def dropRoundupSequenceToGoTermTable(conn=None):
    sql = '''DROP TABLE IF EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence_to_go_term'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def createRoundupSequenceToGoTermTable(conn=None):
    sql ='''CREATE TABLE IF NOT EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence_to_go_term
        (id int unsigned auto_increment primary key,
        sequence_id int unsigned NOT NULL,
        go_term_acc varchar(255) NOT NULL,
        go_term_name varchar(255) NOT NULL,
        go_term_type varchar(55) NOT NULL,
        KEY sequence_index (sequence_id),
        UNIQUE KEY sequence_and_acc_index (sequence_id, go_term_acc) ) ENGINE = InnoDB'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def dropRoundupGenomesTable(conn=None):
    sql = '''DROP TABLE IF EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_genomes'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def createRoundupGenomesTable(conn=None):
    sql = '''CREATE TABLE IF NOT EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_genomes
        (id smallint unsigned auto_increment primary key, name varchar(100) NOT NULL) ENGINE = InnoDB'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def dropRoundupDivergencesTable(conn=None):
    sql = '''DROP TABLE IF EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_divergences'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def createRoundupDivergencesTable(conn=None):
    sql = '''CREATE TABLE IF NOT EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_divergences
        (id tinyint unsigned auto_increment primary key, name varchar(100) NOT NULL) ENGINE = InnoDB'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def dropRoundupEvaluesTable(conn=None):
    sql = '''DROP TABLE IF EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_evalues'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def createRoundupEvaluesTable(conn=None):
    sql = '''CREATE TABLE IF NOT EXISTS '''+ROUNDUP_MYSQL_DB+'''.roundup_evalues
        (id tinyint unsigned auto_increment primary key, name varchar(100) NOT NULL) ENGINE = InnoDB'''
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def dropRoundupDb(conn=None):
    '''
    Drop all roundup database tables
    '''
    for conn in withRoundupDbConn(conn=conn):
        dropRoundupSequenceTable(conn=conn)
        dropRoundupGenomesTable(conn=conn)
        dropRoundupDivergencesTable(conn=conn)
        dropRoundupEvaluesTable(conn=conn)
        dropRoundupResultsTable(conn=conn)
        dropRoundupSequenceToGoTermTable(conn=conn)

    
def createRoundupDb(conn=None):
    '''
    Create any roundup tables that do not yet exist.
    '''
    for conn in withRoundupDbConn(conn=conn):
        createRoundupSequenceTable(conn=conn)
        createRoundupGenomesTable(conn=conn)
        createRoundupDivergencesTable(conn=conn)
        createRoundupEvaluesTable(conn=conn)
        createRoundupResultsTable(conn=conn)
        createRoundupSequenceToGoTermTable(conn=conn)


def updateRoundupSequenceToGoTermTable(conn=None):
    sql = '''REPLACE INTO '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence_to_go_term (sequence_id, go_term_acc, go_term_name, go_term_type)
        SELECT DISTINCT rs.id, t.acc, t.name, t.term_type FROM '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence rs JOIN go.gene2go g2g JOIN go.term t
        WHERE rs.gene_id = g2g.geneid AND g2g.goid = t.acc
        AND t.is_obsolete = 0 AND t.term_type = 'biological_process' '''
    logging.debug(sql)
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def updateRoundupSequenceTable(conn=None):
    '''
    This query does not insert sequences.  Instead it updates sequences with gene name and gene id info.
    To insert sequences, add roundup results files to the mysql db.
    '''
    sql = '''UPDATE '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence rs
    JOIN go.gene2accession g2a ON rs.external_sequence_id = g2a.prot_gi
    JOIN go.gene_info gi ON g2a.geneid = gi.geneid
    SET rs.gene_name = gi.symbol, rs.gene_id = gi.geneid
    '''
    logging.debug(sql)
    for conn in withRoundupDbConn(conn=conn):
        dbutil.executeSQL(sql=sql, conn=conn)


def updateRoundupDb(conn=None):
    '''
    this updates only some of the tables.  and to be properly updated they should be dropped and created first.
    '''
    for conn in withRoundupDbConn(conn=conn):
        updateRoundupSequenceTable(conn=conn)
        updateRoundupSequenceToGoTermTable(conn=conn)    


###########################
# VALUE-ID LOOKUP FUNCTIONS
###########################

def getValueForId(id, conn, tableName, idCol='id', valueCol='value', dbName=None):
    '''
    id: id for a table row.
    returns: value found in valueCol for the first row identified with id.
    '''
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
        sql = 'SELECT '+idCol+' FROM '+dbName+'.'+tableName+' WHERE '+valueCol+' = %s'
        rowset = dbutil.selectSQL(sql=sql, conn=conn, args=[value])
        if rowset:
            return rowset[0][0]
        else:
            return None

    id = getId()
    if id is None and insertMissing:
        sql = 'INSERT INTO '+dbName+'.'+tableName+' ('+valueCol+') VALUES (%s)'
        dbutil.executeSQL(sql=sql, conn=conn, args=[value])
        id = getId()
    return id


#############################
# ROUNDUP PARAMETER FUNCTIONS
#############################

def getRoundupParameterIds(qdb, sdb, divergence, evalue, conn=None, insertMissing=False):
    for conn in withRoundupDbConn(conn=conn):
        qdbId = getIdForDatabase(qdb, conn, insertMissing)
        sdbId = getIdForDatabase(sdb, conn, insertMissing)
        divId = getIdForDivergence(divergence, conn, insertMissing)
        evalueId = getIdForEvalue(evalue, conn, insertMissing)
        return qdbId, sdbId, divId, evalueId


def getDatabaseForId(id, conn=None):
    '''
    returns: name of database whose id is id.
    '''
    for conn in withRoundupDbConn(conn=conn):
        return getValueForId(id=id, conn=conn, tableName='roundup_genomes', dbName=ROUNDUP_MYSQL_DB, valueCol='name')


def getDivergenceForId(id, conn=None):
    '''
    returns: divergence value whose id is id.
    '''
    for conn in withRoundupDbConn(conn=conn):
        return getValueForId(id=id, conn=conn, tableName='roundup_divergences', dbName=ROUNDUP_MYSQL_DB, valueCol='name')


def getEvalueForId(id, conn=None):
    '''
    returns: evalue whose id is id.
    '''
    for conn in withRoundupDbConn(conn=conn):
        return getValueForId(id=id, conn=conn, tableName='roundup_evalues', dbName=ROUNDUP_MYSQL_DB, valueCol='name')


def getIdForDatabase(db, conn=None, insertMissing=False):
    '''
    db: name of roundup database registered in the mysql db lookup table.  e.g. Homo_sapiens.aa
    returns: id used to refer to that db in the roundup results table or None if db was not found.
    '''
    for conn in withRoundupDbConn(conn=conn):
        return getIdForValue(value=db, conn=conn, tableName='roundup_genomes', dbName=ROUNDUP_MYSQL_DB, valueCol='name', insertMissing=insertMissing)


def getIdForEvalue(evalue, conn=None, insertMissing=False):
    '''
    evalue: value of roundup evalue, e.g. 1e-5
    returns: id used to refer to evalue in the roundup results table or None if evalue was not found.
    '''
    for conn in withRoundupDbConn(conn=conn):
        return getIdForValue(value=evalue, conn=conn, tableName='roundup_evalues', dbName=ROUNDUP_MYSQL_DB, valueCol='name', insertMissing=insertMissing)


def getIdForDivergence(divergence, conn=None, insertMissing=False):
    '''
    divergence: value of roundup divergence, e.g. 0.2
    returns: id used to refer to divergence in the roundup results table or None if divergence was not found.
    '''
    for conn in withRoundupDbConn(conn=conn):
        return getIdForValue(value=divergence, conn=conn, tableName='roundup_divergences', dbName=ROUNDUP_MYSQL_DB, valueCol='name', insertMissing=insertMissing)


##########################
# ORTHOLOG CODEC FUNCTIONS
##########################
#
# used to compress and decompress orthologs so they take up less space in the database.
#

def encodeOrthologs(orthologs):
    return zlib.compress(cPickle.dumps(orthologs))


def decodeOrthologs(encodedOrthologs):
    return cPickle.loads(zlib.decompress(encodedOrthologs))



####################
# LOAD RESULTS FILES
####################


def loadGenome(genome, ids):
    '''
    ids: externalSequenceIds for genome.
    genome: identifier/name e.g. Homo_sapiens.aa
    loads the sequence identifiers into the roundup database, creating internal sequence identifiers for them which are later used when orthologs are loaded.
    '''
    for conn in withRoundupDbConn():
        sql = '''INSERT IGNORE INTO '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence (external_sequence_id, genome_id) VALUES (%s, %s)'''
        logging.debug('roundup_db.loadGenomeIds(), genome=%s'%genome)
        genomeId = getIdForDatabase(genome, conn=conn, insertMissing=True)
        # execute each sequence insert as a transaction.  slow but will it avoid deadlock?
        for seqId in ids:
            with dbutil.doTransaction(conn) as conn:
                dbutil.executeSQL(conn, sql, args=[seqId, genomeId])

            
def loadResultsFile(resultsFile, seqIdMap=None):
    '''
    resultsFile: filename containing roundup results
    seqIdMap: a dict used to map seq ids to other data.  missing seq ids for genomes are added to the map.
    If loading multiple results files, create a dict variable (e.g. foo={}) and pass it to each function call as seqIdMap parameter to speed up loading.
    returns: Nothing.
    '''
    if seqIdMap is None:
        seqIdMap = {}

    for conn in withRoundupDbConn():
        logging.debug('loadResultsFile.  path=%s'%resultsFile)
        qdb, sdb, div, evalue = roundup_common.splitRoundupFilename(resultsFile)
        qdbId, sdbId, divId, evalueId = getRoundupParameterIds(conn=conn, insertMissing=True, qdb=qdb, sdb=sdb, divergence=div, evalue=evalue)
        print qdb, qdbId
        print sdb, sdbId
        print div, divId
        print evalue, evalueId
        # insert results into roundup_orthologs table

        # read orthologs from file
        externalSeqIdAndGenomeIdPairs = set()
        orthologs = []
        for result in resultsGenerator(resultsFile):
            queryId, subjectId, distance = result
            externalSeqIdAndGenomeIdPairs.add((queryId, qdbId))
            externalSeqIdAndGenomeIdPairs.add((subjectId, sdbId))
            orthologs.append(((queryId, qdbId), (subjectId, sdbId), distance))

        # update seqIdMap with sequences from orthologs
        # assume all sequences are in roundup_sequence, because the genomes were loaded using loadGenome()
        externalSeqIdAndGenomeIdPairsList = [pair for pair in externalSeqIdAndGenomeIdPairs if pair not in seqIdMap]
        # get ids for previously existing sequences in roundup_sequence and add to seqIdMap.
        sql = '''SELECT id FROM '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence WHERE external_sequence_id=%s AND genome_id=%s'''
        # logging.debug('sql='+sql)
        for pair in externalSeqIdAndGenomeIdPairsList:
            # get the unique seq id for each (external seq id, genome) pair, and add it to the map
            seqIdMap[pair] = dbutil.selectSQL(sql=sql, args=args, conn=conn)[0][0]

        # put orthologs in form for insertion into db
        normalizedOrthologs = []
        for queryPair, subjectPair, distance in orthologs:
            try:
                querySeqId = seqIdMap[queryPair]
            except:
                print resultsFile
                print seqIdMap
                raise
            subjectSeqId = seqIdMap[subjectPair]
            normalizedOrthologs.append((querySeqId, subjectSeqId, distance))

        # insert orthologs into db
        encodedOrthologs = encodeOrthologs(normalizedOrthologs)
        numOrthologs = len(normalizedOrthologs)
        sql = 'INSERT INTO '+ROUNDUP_MYSQL_DB+'.roundup_results (query_db, subject_db, divergence, evalue, filename, mod_time, orthologs, num_orthologs) '
        sql += ' VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s) '
        sql += ' ON DUPLICATE KEY UPDATE filename=%s, mod_time=NOW(), orthologs=%s, num_orthologs=%s '
        args = (qdbId, sdbId, divId, evalueId, resultsFile, encodedOrthologs, numOrthologs, resultsFile, encodedOrthologs, numOrthologs)
        # logging.debug('sql=%s, args=%s'%(sql, args))
        with dbutil.doTransaction(conn) as conn:
            fileLoadId = dbutil.insertSQL(conn, sql, args=args)


def resultsGenerator(resultsFilePath):
    '''
    yields: queryId, subjectId, distance for each ortholog in the resultsFileLines.
    '''
    for fh in util.withOpenFile(resultsFilePath):
        for line in fh:
            # remove whitespace from front and linebreak from end, to clean up data
            line = line.lstrip()
            line = line.rstrip('\n')
            
            # skip blank lines
            if not line:
                continue
            # and skip comment lines
            if line[0] == '#':
                continue
        
            # break line into fields
            subjectId, queryId, distance = line.split()
            distance = float(distance)
            
            # values to be inserted
            yield [queryId, subjectId, distance]


####################
# DELETION FUNCTIONS
####################


def deleteGenomeByName(genome, conn=None):
    '''
    genome: name of genome, like 'Takifugu_rubripes.aa'.  To make life interesting, this name is also called a database/genome id
      in the context of updating/downloading and dbInfo objects.
    deletes all roundup results in mysql containing this genome.
    returns: nothing.
    '''
    logging.debug('deleteGenomeByName(): genome=%s'%genome)
    for conn in withRoundupDbConn(conn=conn):        
        dbId = getIdForDatabase(genome, conn)
        if not dbId:
            return
        print 'dbId=%s'%dbId

        # remove from roundup_results
        sql = 'DELETE FROM '+ROUNDUP_MYSQL_DB+'.roundup_results WHERE query_db=%s OR subject_db=%s'
        print sql
        dbutil.executeSQL(sql=sql, conn=conn, args=[dbId, dbId])

        # delete sequences to term for the given genome
        sql = '''DELETE '''+ROUNDUP_MYSQL_DB+'''.rs2gt
        FROM '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence_to_go_term rs2gt
        JOIN '''+ROUNDUP_MYSQL_DB+'''.roundup_sequence rs1
        WHERE rs2gt.sequence_id = rs1.id AND rs1.genome_id=%s '''
        print sql
        dbutil.executeSQL(sql=sql, conn=conn, args=[dbId])

        # delete sequences from the genome.
        sql = 'DELETE FROM '+ROUNDUP_MYSQL_DB+'.roundup_sequence WHERE genome_id=%s'
        print sql
        dbutil.executeSQL(sql=sql, conn=conn, args=[dbId])
        
        # remove genome
        sql = 'DELETE FROM '+ROUNDUP_MYSQL_DB+'.roundup_genomes WHERE id=%s'
        print sql
        dbutil.executeSQL(sql=sql, conn=conn, args=[dbId])


##########################
# ORTHOLOG QUERY FUNCTIONS
##########################

def getSequenceIdToSequenceDataMap(sequenceIds, conn=None):
    '''
    returns: dict mapping sequence id to dict {'external_sequence_id':external_sequence_id, 'genome_id':genome_id, 'gene_name':gene_name} 
    '''
    map = {}
    
    for conn in withRoundupDbConn(conn=conn):        
        for group in util.groupsOfN(sequenceIds, 1000):
            # sql = 'SELECT id, external_sequence_id, genome_id, gene_name FROM '+ROUNDUP_MYSQL_DB+'.roundup_sequence WHERE id=%s'
            sql = 'SELECT id, external_sequence_id, genome_id, gene_name FROM '+ROUNDUP_MYSQL_DB+'.roundup_sequence '
            sql += ' WHERE id IN ('+', '.join([str(id) for id in group])+')'
            # logging.debug('sql='+sql)
            # logging.debug('sequenceIds='+str(sequenceIds))
            def selectSequenceDataRows():
                return dbutil.selectSQL(sql=sql, conn=conn)
            rows = selectSequenceDataRows()
            def buildSequenceDataMap():
                for id, external_sequence_id, genome_id, gene_name in rows:
                    map[id] = {roundup_common.EXTERNAL_SEQUENCE_ID_KEY:external_sequence_id, roundup_common.GENOME_ID_KEY:genome_id,
                               roundup_common.GENE_NAME_KEY:gene_name}
            buildSequenceDataMap()
    return map


def getSequenceIdToTermsMap(sequenceIds, conn=None):
    '''
    constructs a map from sequence id to a list of go term info dicts.
    note: if sequence id not in the database, it is not added to the map.
    returns: dict mapping sequence id to a (possibly empty) list of dicts like {'go_id': term accession number, 'go_name': term name}.
    '''
    seqIdToTermsMap = {}
    termMap = {}
    for group in util.groupsOfN(sequenceIds, 1000):
        # left join so sequence ids without go terms will return a null row.
        sql = 'SELECT rs2gt.sequence_id, rs2gt.go_term_acc, rs2gt.go_term_name'
        sql += ' FROM '+ROUNDUP_MYSQL_DB+'.roundup_sequence_to_go_term rs2gt'
        sql += ' WHERE rs2gt.sequence_id IN ('+', '.join([str(id) for id in group])+') '#AND rs2gt.go_term_type = \'biological_process\''
        # logging.debug('sql='+sql)
        # logging.debug('len sequenceIds='+str(len(sequenceIds)))
        def selectTermsRows():
            return dbutil.selectSQL(sql=sql, conn=conn)
        rows = selectTermsRows()
        # map sequence ids without any terms to [].  with terms to list of accs.
        def buildTermsMap():
            for id, acc, name in rows:
                seqIdToTermsMap.setdefault(id, [])
                termMap[acc] = name
                seqIdToTermsMap[id].append(acc)
        buildTermsMap()
    return (seqIdToTermsMap, termMap)


def getOrthologs(qdb, sdb, divergence='0.2', evalue='1e-20', conn=None):
    '''
    divergence: ortholog must have this divergence.  defaults to 0.2
    evalue: ortholog must have this evalue.  defaults to 1e-20.
    '''
    for conn in withRoundupDbConn(conn=conn):
        qdbId = getIdForDatabase(qdb, conn)
        sdbId = getIdForDatabase(sdb, conn)
        divId = getIdForDivergence(divergence, conn)
        evalueId = getIdForEvalue(evalue, conn)
        sql = 'SELECT rr.orthologs '
        sql += ' FROM '+ROUNDUP_MYSQL_DB+'.roundup_results rr'
        sql += ' WHERE rr.query_db = %s AND rr.subject_db = %s AND rr.divergence = %s AND rr.evalue = %s '
        args = [qdbId, sdbId, divId, evalueId]
        logging.debug('sql='+sql)
        logging.debug('args='+str(args))
        rows = dbutil.selectSQL(sql=sql, args=args, conn=conn)
        return decodeOrthologs(rows[0][0])

    
############################################
# WEB FUNCTIONS: MISSING RESULTS, GENE NAMES
############################################

def numOrthologs(conn=None):
    num = 0
    for conn in withRoundupDbConn(conn=conn):
        sql = 'SELECT num_orthologs FROM '+ROUNDUP_MYSQL_DB+'.roundup_results'
        rows = dbutil.selectSQL(sql=sql, conn=conn)
        num = sum(row[0] for row in rows)
    return num

    

def getNonLoadedResultsForParams(paramsList, conn=None):
    '''
    paramsList: list of tuples of roundup result params
    Checks every tuple of qdb, sdb, div, evalue to see if it has been loaded into the db.
    returns:  a list of tuples which have not been loaded into the db.
    '''
    for conn in withRoundupDbConn(conn=conn):
        nonLoadedParams = [params for params in paramsList if not isLoadedResultForParams(params=params, conn=conn)]
        return nonLoadedParams
    

def isLoadedResultForParams(params, conn=None):
    for conn in withRoundupDbConn(conn=conn):
        (qdb, sdb, div, evalue) = params
        qdbId, sdbId, divId, evalueId = getRoundupParameterIds(conn=conn, insertMissing=True, qdb=qdb, sdb=sdb, divergence=div, evalue=evalue)
        sql = ' SELECT rr.id FROM '+ROUNDUP_MYSQL_DB+'.roundup_results rr '
        sql += ' WHERE rr.query_db = %s AND rr.subject_db = %s AND rr.divergence = %s AND rr.evalue = %s '
        args = (qdbId, sdbId, divId, evalueId)
        results = dbutil.selectSQL(sql=sql, args=args, conn=conn)
        if results:
            return True
        else:
            return False

    
# SEARCH TYPES FOR findGeneNamesLike()
CONTAINS_TYPE = 'contains'
STARTS_WITH_TYPE = 'starts_with'
ENDS_WITH_TYPE = 'ends_with'
EQUALS_TYPE = 'equals'


def findGeneNamesLike(substring, searchType=CONTAINS_TYPE, conn=None):
    '''
    substring: search for gene names containing this string somehow.
    searchType: specify how the gene name should contain substring
    returns: list of every gene name containing substring according to the searchType.
    '''
    sql = ' SELECT DISTINCT rs.gene_name FROM '+ROUNDUP_MYSQL_DB+'.roundup_sequence rs '
    sql += ' WHERE rs.gene_name LIKE %s'
    if searchType == CONTAINS_TYPE:
        args = ['%' + substring + '%']
    elif searchType == STARTS_WITH_TYPE:
        args = [substring + '%']
    elif searchType == ENDS_WITH_TYPE:
        args = ['%' + substring]
    elif searchType == EQUALS_TYPE:
        args = [substring]
    else:
        raise Exception('Unrecognized searchType.  searchType=%s'%searchType)

    # results are a tuple of tuples which containing an id.  convert to a list of ids.
    for conn in withRoundupDbConn(conn=conn):
        return [row[0] for row in dbutil.selectSQL(sql=sql, args=args, conn=conn)]

    
def findGeneNameGenomePairsLike(substring, searchType=CONTAINS_TYPE, conn=None):
    '''
    substring: search for gene names containing this string somehow.
    searchType: specify how the gene name should contain substring
    genomes names are like Homo_sapiens.aa
    returns: list of unique pairs of gene name and genome names for every gene name containing substring according to the searchType
    mapped to all genomes that contain a seq id that has that gene name.
    '''
    sql = ' SELECT DISTINCT rs.gene_name, rg.name'
    sql += ' FROM '+ROUNDUP_MYSQL_DB+'.roundup_sequence rs JOIN '+ROUNDUP_MYSQL_DB+'.roundup_genomes rg '
    sql += ' WHERE rs.gene_name LIKE %s'
    if searchType == CONTAINS_TYPE:
        args = ['%' + substring + '%']
    elif searchType == STARTS_WITH_TYPE:
        args = [substring + '%']
    elif searchType == ENDS_WITH_TYPE:
        args = ['%' + substring]
    elif searchType == EQUALS_TYPE:
        args = [substring]
    else:
        raise Exception('Unrecognized searchType.  searchType=%s'%searchType)
    sql += ' AND rs.genome_id = rg.id '
    sql += ' ORDER BY rg.name, rs.gene_name '
    
    # results are a tuple of tuples which containing an gene name and genome.
    for conn in withRoundupDbConn(conn=conn):
        return [(row[0], row[1]) for row in dbutil.selectSQL(sql=sql, args=args, conn=conn)]


def getSeqIdsForGeneName(geneName, database=None, conn=None):
    '''
    geneName: gene name or symbol, e.g. 'acsC'
    database: genome database id, e.g. 'Homo_sapiens.aa'.  If None, all seq ids with the gene name are returned.
    conn: db connection to use.  If None, one will be created.
    returns: list of sequence ids, i.e. a GI, ensembl id, etc., which have the given gene name.
    '''
    for conn in withRoundupDbConn(conn=conn):
        sql = 'SELECT DISTINCT rs.external_sequence_id '
        sql += ' FROM '+ROUNDUP_MYSQL_DB+'.roundup_sequence rs '
        sql += ' WHERE rs.gene_name = %s '
        params = [geneName]
        if database:
            dbId = getIdForDatabase(database, conn)
            sql += ' AND rs.genome_id = %s '
            params.append(dbId)

        # results are a tuple of tuples which containing an id.  convert to a list of ids.
        return [row[0] for row in dbutil.selectSQL(sql=sql, args=params, conn=conn)]


#################
#
#################


# last line fix for emacs python mode bug -- do not cross
