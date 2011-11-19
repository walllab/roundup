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
import contextlib
import json
import itertools

import config
import util
import roundup_common
import dbutil


# get mysql server/host and database from deployment location, defaulting to dev.  override if defined in environment.
ROUNDUP_MYSQL_DB = config.MYSQL_DB


###############################
# DATABASE CONNECTION FUNCTIONS
###############################

@contextlib.contextmanager
def connCM(conn=None, commit=True):
    if conn == None:
        with config.dbConnCM() as conn:
            if commit:
                with dbutil.doTransaction(conn) as conn:
                    yield conn
            else:
                yield conn
    else:
        if commit:
            with dbutil.doTransaction(conn) as conn:
                yield conn
        else:
            yield conn
        

#################################
# TABLE CREATE AND DROP FUNCTIONS
#################################

def releaseTable(release, table):
    '''
    table: e.g. 'genomes', 'sequence', or 'results'.  
    creates the database-scoped, correct name for a table in the roundup database.
    basically, it fills in this template: 'roundup.roundup_<release>_<table>'.
    returns: the full table name e.g. 'roundup.roundup_201106_dataset_genomes'
    '''
    return '{}.roundup_{}_{}'.format(ROUNDUP_MYSQL_DB, release, table)


def dropGenomes(release):
    sql = 'DROP TABLE IF EXISTS {}'.format(releaseTable(release, 'genomes'))
    with connCM() as conn:
        print sql
        dbutil.executeSQL(sql=sql, conn=conn)
    

def createGenomes(release):
    sql = '''CREATE TABLE IF NOT EXISTS {}
            (id smallint unsigned auto_increment primary key,
            acc varchar(100) NOT NULL,
            name varchar(255) NOT NULL,
            ncbi_taxon varchar(20) NOT NULL,
            taxon_name varchar(255) NOT NULL,
            taxon_category_code varchar(10) NOT NULL,
            taxon_category_name varchar(255) NOT NULL,
            num_seqs int unsigned NOT NULL,
            UNIQUE KEY genome_acc_key (acc)) ENGINE = InnoDB'''.format(releaseTable(release, 'genomes'))
    with connCM() as conn:
        print sql
        dbutil.executeSQL(sql=sql, conn=conn)


def dropRelease(release):
    sqls = ['DROP TABLE IF EXISTS {}'.format(releaseTable(release, 'divergences')), 
            'DROP TABLE IF EXISTS {}'.format(releaseTable(release, 'evalues')), 
            'DROP TABLE IF EXISTS {}'.format(releaseTable(release, 'sequence')), 
            'DROP TABLE IF EXISTS {}'.format(releaseTable(release, 'sequence_to_go_term')), 
            ]
    dropGenomes(release)
    with connCM() as conn:
        for sql in sqls:
            print sql
            dbutil.executeSQL(sql=sql, conn=conn)


def createRelease(release):
    sqls = ['''CREATE TABLE IF NOT EXISTS {}
            (id tinyint unsigned auto_increment primary key, name varchar(100) NOT NULL) ENGINE = InnoDB'''.format(releaseTable(release, 'divergences')),
            '''CREATE TABLE IF NOT EXISTS {}
            (id tinyint unsigned auto_increment primary key, name varchar(100) NOT NULL) ENGINE = InnoDB'''.format(releaseTable(release, 'evalues')),
            '''CREATE TABLE IF NOT EXISTS {}
            (id int unsigned auto_increment primary key,
            external_sequence_id varchar(100) NOT NULL,
            genome_id smallint(5) unsigned NOT NULL,
            gene_name varchar(100),
            gene_id int,
            KEY genome_index (genome_id),
            UNIQUE KEY sequence_index (external_sequence_id),
            UNIQUE KEY sequence_and_genome (external_sequence_id, genome_id) ) ENGINE = InnoDB'''.format(releaseTable(release, 'sequence')),
            '''CREATE TABLE IF NOT EXISTS {}
            (id int unsigned auto_increment primary key,
            sequence_id int unsigned NOT NULL,
            go_term_acc varchar(255) NOT NULL,
            go_term_name varchar(255) NOT NULL,
            go_term_type varchar(55) NOT NULL,
            KEY sequence_index (sequence_id),
            UNIQUE KEY sequence_and_acc_index (sequence_id, go_term_acc) ) ENGINE = InnoDB'''.format(releaseTable(release, 'sequence_to_go_term')),
            ]
    createGenomes(release)
    with connCM() as conn:
        for sql in sqls:
            print sql
            dbutil.executeSQL(sql=sql, conn=conn)


def dropReleaseResults(release):
    sql = 'DROP TABLE IF EXISTS {}'.format(releaseTable(release, 'results'))
    with connCM() as conn:
        print sql
        dbutil.executeSQL(sql=sql, conn=conn)


def createReleaseResults(release):
    sql = '''CREATE TABLE IF NOT EXISTS {}
    (id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    query_db SMALLINT UNSIGNED NOT NULL,
    subject_db SMALLINT UNSIGNED NOT NULL,
    divergence TINYINT UNSIGNED NOT NULL,
    evalue TINYINT UNSIGNED NOT NULL,
    mod_time DATETIME DEFAULT NULL,
    orthologs LONGBLOB,
    num_orthologs INT UNSIGNED NOT NULL,
    KEY query_db_index (query_db),
    KEY subject_db_index (subject_db),
    UNIQUE KEY params_key (query_db, subject_db, divergence, evalue) ) ENGINE = InnoDB'''.format(releaseTable(release, 'results'))
    with connCM() as conn:
        print sql
        dbutil.executeSQL(sql=sql, conn=conn)


#########################
# TABLE LOADING FUNCTIONS
#########################

    
def loadGenomes(release, genomesFile):
    '''
    release: the id of the release being loaded
    genomesFile: each line contains a tab-separated id (integer) and external genome id/name (string).
    The ids should go from 1 to N (where N is the number of genomes.)  Genomes should be unique.
    Why use LOAD DATA INFILE?  Because it is very fast relative to insert.  a discussion of insertion speed: http://dev.mysql.com/doc/refman/5.1/en/insert-speed.html
    
    '''
    sql = 'LOAD DATA LOCAL INFILE %s INTO TABLE {}'.format(releaseTable(release, 'genomes'))
    args = [genomesFile]
    
    with connCM() as conn:
        print sql, args
        dbutil.executeSQL(sql=sql, conn=conn, args=args)


def loadRelease(release, genomesFile, divergencesFile, evaluesFile, seqsFile, seqToGoTermsFile):
    '''
    release: the id of the release being loaded
    genomesFile: each line contains a tab-separated id (integer) and external genome id/name (string).
    The ids should go from 1 to N (where N is the number of genomes.)  Genomes should be unique.
    Why use LOAD DATA INFILE?  Because it is very fast relative to insert.  a discussion of insertion speed: http://dev.mysql.com/doc/refman/5.1/en/insert-speed.html
    
    '''
    sqls = ['LOAD DATA LOCAL INFILE %s INTO TABLE {}'.format(releaseTable(release, 'divergences')), 
            'LOAD DATA LOCAL INFILE %s INTO TABLE {}'.format(releaseTable(release, 'evalues')), 
            'LOAD DATA LOCAL INFILE %s INTO TABLE {}'.format(releaseTable(release, 'sequence')), 
            'LOAD DATA LOCAL INFILE %s INTO TABLE {}'.format(releaseTable(release, 'sequence_to_go_term')), 
            ]
    argsList = [[genomesFile], [divergencesFile], [evaluesFile], [seqsFile], [seqToGoTermsFile]]
    loadGenomes(release, genomesFile)
    with connCM() as conn:
        for sql, args in zip(sqls, argsList):
            print sql, args
            dbutil.executeSQL(sql=sql, conn=conn, args=args)


def loadReleaseResults(release, genomeToId, divToId, evalueToId, geneToId, resultsGen):
    '''
    resultsGen: a generator that yields ((qdb, sdb, div, evalue), orthologs) tuples.
    convert the results into a rows, and insert them into the results table.
    `id` int(10) unsigned NOT NULL auto_increment,
    `query_db` smallint(5) unsigned NOT NULL,
    `subject_db` smallint(5) unsigned NOT NULL,
    `divergence` tinyint(3) unsigned NOT NULL,
    `evalue` tinyint(3) unsigned NOT NULL,
    `filename` text,
    `mod_time` datetime default NULL,
    `orthologs` longblob,
    `num_orthologs` int(10) unsigned NOT NULL,
    '''
    def convertForDb(result):
        # convert various items into the form the database table wants.  Change strings into database ids.  Encode orthologs, etc.
        (qdb, sdb, div, evalue), orthologs = result
        qdbId = genomeToId[qdb]
        sdbId = genomeToId[sdb]
        divId = divToId[div]
        evalueId = evalueToId[evalue]
        dbOrthologs = [(geneToId[qid], geneToId[sid], float(dist)) for qid, sid, dist in orthologs] # orthologs using db ids and floats, not strings.
        encodedOrthologs = encodeOrthologs(dbOrthologs)
        numOrthologs = len(orthologs)
        return qdbId, sdbId, divId, evalueId, encodedOrthologs, numOrthologs

    numPerGroup = 400 # not to huge, not to slow.
    sql1 = 'INSERT IGNORE INTO {} (query_db, subject_db, divergence, evalue, mod_time, orthologs, num_orthologs) VALUES '.format(releaseTable(release, 'results'))
    for i, group in enumerate(util.groupsOfN(resultsGen, numPerGroup)):
        sql = sql1 + ', '.join(['(%s, %s, %s, %s, NOW(), %s, %s) ' for j in range(len(group))]) # cannot just use numPerGroup, b/c last group can have fewer results.
        argsLists = [convertForDb(result) for result in group]
        args = list(itertools.chain.from_iterable(argsLists)) # flatten args into one long list for the sql
        with connCM() as conn:
            fileLoadId = dbutil.insertSQL(conn, sql, args=args)


#############################
# ROUNDUP PARAMETER FUNCTIONS
#############################
#
# Parameters: genomes, divergences, and evalues (and a little bit of sequences)
# 

def selectOne(conn, sql, args=None):
    '''
    helper function that selects the first column of the first row
    assumption: there is at least one row with one column.  expect an error otherwise.
    '''
    with connCM(conn=conn) as conn:
        return dbutil.selectSQL(sql=sql, conn=conn, args=args)[0][0]

    
def getGenomeForId(id, conn=None):
    '''
    returns: genome accession of genome whose id is id.
    '''
    sql = 'SELECT acc FROM {} WHERE id=%s'.format(releaseTable(config.CURRENT_RELEASE, 'genomes'))
    return selectOne(conn, sql, args=[id])


def getIdForGenome(genome, conn=None, release=config.CURRENT_RELEASE):
    '''
    genome: acc of roundup genome registered in the mysql db lookup table.  e.g. 9606
    returns: id used to refer to that genome in the roundup results table or None if genome was not found.
    '''
    sql = 'SELECT id FROM {} WHERE acc=%s'.format(releaseTable(release, 'genomes'))
    return selectOne(conn, sql, args=[genome])


def getDivergenceForId(id, conn=None):
    '''
    returns: divergence value whose id is id.
    '''
    return getNameForId(id=id, table=releaseTable(config.CURRENT_RELEASE, 'divergences'), conn=conn)


def getIdForDivergence(divergence, conn=None):
    '''
    divergence: value of roundup divergence, e.g. 0.2
    returns: id used to refer to divergence in the roundup results table or None if divergence was not found.
    '''
    return getIdForName(name=divergence, table=releaseTable(config.CURRENT_RELEASE, 'divergences'), conn=conn)


def getEvalueForId(id, conn=None):
    '''
    returns: evalue whose id is id.
    '''
    return getNameForId(id=id, table=releaseTable(config.CURRENT_RELEASE, 'evalues'), conn=conn)


def getIdForEvalue(evalue, conn=None):
    '''
    evalue: value of roundup evalue, e.g. 1e-5
    returns: id used to refer to evalue in the roundup results table or None if evalue was not found.
    '''
    return getIdForName(name=evalue, table=releaseTable(config.CURRENT_RELEASE, 'evalues'), conn=conn)


def getIdForName(name, table, conn=None):
    sql = 'SELECT id FROM {} WHERE name=%s'.format(table)
    with connCM(conn=conn) as conn:
        rowset = dbutil.selectSQL(sql=sql, conn=conn, args=[name])
        return rowset[0][0]
    

def getNameForId(id, table, conn=None):
    sql = 'SELECT name FROM {} WHERE id=%s'.format(table)
    with connCM(conn=conn) as conn:
        rowset = dbutil.selectSQL(sql=sql, conn=conn, args=[id])
        return rowset[0][0]
    

def getGenomeToId(release=config.CURRENT_RELEASE):
    sql = 'select acc, id from {}'.format(releaseTable(release, 'genomes'))
    with connCM() as conn:
        return dict(dbutil.selectSQL(sql=sql, conn=conn))


def getDivergenceToId(release=config.CURRENT_RELEASE):
    sql = 'select name, id from {}'.format(releaseTable(release, 'divergences'))
    with connCM() as conn:
        return dict(dbutil.selectSQL(sql=sql, conn=conn))


def getEvalueToId(release=config.CURRENT_RELEASE):
    sql = 'select name, id from {}'.format(releaseTable(release, 'evalues'))
    with connCM() as conn:
        return dict(dbutil.selectSQL(sql=sql, conn=conn))


def getSequenceToId(release=config.CURRENT_RELEASE):
    sql = 'select external_sequence_id, id from {}'.format(releaseTable(release, 'sequence'))
    with connCM() as conn:
        return dict(dbutil.selectSQL(sql=sql, conn=conn))


##########################
# ORTHOLOG CODEC FUNCTIONS
##########################
#
# used to compress and decompress orthologs so they take up less space in the database.
#

def encodeOrthologs(orthologs):
    return zlib.compress(cPickle.dumps(orthologs))
    # return json.dumps(orthologs) # since using 'LOAD DATA INFILE' to load the orthologs, the encoded orthologs must be on a single line with no tab-characters.

def decodeOrthologs(encodedOrthologs):
    return cPickle.loads(zlib.decompress(encodedOrthologs))
    # return json.loads(encodedOrthologs)


####################
# DELETION FUNCTIONS
####################


def deleteGenomeByName(genome, conn=None):
    '''
    genome: name of genome, like 'Takifugu_rubripes.aa'. 
    deletes all roundup results in mysql containing this genome.
    returns: nothing.
    '''
    # logging.debug('deleteGenomeByName(): genome=%s'%genome)
    with connCM(conn=conn) as conn:
        dbId = getIdForGenome(genome, conn)
        if not dbId:
            return
        print 'dbId=%s'%dbId

        # remove from roundup_results
        sql = 'DELETE FROM {} WHERE query_db=%s OR subject_db=%s'.format(releaseTable(config.CURRENT_RELEASE, 'results'))
        print sql
        dbutil.executeSQL(sql=sql, conn=conn, args=[dbId, dbId])

        # delete sequence to go term entries for the given genome
        sql = 'DELETE FROM rs2gt USING {} AS rs2gt INNER JOIN {} AS rs WHERE rs2gt.sequence_id = rs.id AND rs.genome_id=%s'
        sql = sql.format(releaseTable(config.CURRENT_RELEASE, 'sequence_to_go_term'), releaseTable(config.CURRENT_RELEASE, 'sequence'))
        print sql
        dbutil.executeSQL(sql=sql, conn=conn, args=[dbId])

        # delete sequences from the genome.
        sql = 'DELETE FROM {} WHERE genome_id=%s'.format(releaseTable(config.CURRENT_RELEASE, 'sequence'))
        print sql
        dbutil.executeSQL(sql=sql, conn=conn, args=[dbId])
        
        # remove genome
        sql = 'DELETE FROM {} WHERE id=%s'.format(releaseTable(config.CURRENT_RELEASE, 'genomes'))
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
    
    with connCM(conn=conn) as conn:        
        for group in util.groupsOfN(sequenceIds, 1000):
            # sql = 'SELECT id, external_sequence_id, genome_id, gene_name FROM '+ROUNDUP_MYSQL_DB+'.roundup_sequence WHERE id=%s'
            sql = 'SELECT id, external_sequence_id, genome_id, gene_name FROM {} '.format(releaseTable(config.CURRENT_RELEASE, 'sequence'))
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
        sql = 'SELECT rs2gt.sequence_id, rs2gt.go_term_acc, rs2gt.go_term_name'
        sql += ' FROM {} AS rs2gt'.format(releaseTable(config.CURRENT_RELEASE, 'sequence_to_go_term'))
        sql += ' WHERE rs2gt.sequence_id IN ('+', '.join([str(id) for id in group])+') '
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
    with connCM(conn=conn) as conn:
        qdbId = getIdForGenome(qdb, conn)
        sdbId = getIdForGenome(sdb, conn)
        divId = getIdForDivergence(divergence, conn)
        evalueId = getIdForEvalue(evalue, conn)
        sql = 'SELECT rr.orthologs '
        sql += ' FROM {} rr'.format(releaseTable(config.CURRENT_RELEASE, 'results'))
        sql += ' WHERE rr.query_db = %s AND rr.subject_db = %s AND rr.divergence = %s AND rr.evalue = %s '
        args = [qdbId, sdbId, divId, evalueId]
        logging.debug('sql='+sql)
        logging.debug('args='+str(args))
        rows = dbutil.selectSQL(sql=sql, args=args, conn=conn)
        return decodeOrthologs(rows[0][0])

    
############################################
# WEB FUNCTIONS: MISSING RESULTS, GENE NAMES
############################################


def getGenomesData(release=config.CURRENT_RELEASE):
    '''
    returns a list of tuples, one for each genome, of acc, name, ncbi_taxon, taxon_category_code,
    taxon_category_name, and num_seqs.
    '''
    sql = '''SELECT acc, name, ncbi_taxon, taxon_category_code, taxon_category_name, num_seqs
    FROM {}'''.format(releaseTable(release, 'genomes'))
    # logging.debug(sql)
    with connCM() as conn:
        return dbutil.selectSQL(sql=sql, conn=conn)


def getGenomesAndNames(release=config.CURRENT_RELEASE):
    '''
    returns a list of pairs of genome (e.g. MYCGE) and name (e.g. Mycoplasma genitalium)
    '''
    sql = 'SELECT acc, name FROM {}'.format(releaseTable(release, 'genomes'))
    logging.debug(sql)
    with connCM() as conn:
        return dbutil.selectSQL(sql=sql, conn=conn)

    
def numOrthologs(conn=None):
    num = 0
    with connCM(conn=conn) as conn:
        sql = 'SELECT num_orthologs FROM {}'.format(releaseTable(config.CURRENT_RELEASE, 'results'))
        rows = dbutil.selectSQL(sql=sql, conn=conn)
        num = sum(row[0] for row in rows)
    return num

    
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
    sql = ' SELECT DISTINCT rs.gene_name FROM {} rs '.format(releaseTable(config.CURRENT_RELEASE, 'sequence'))
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
    with connCM(conn=conn) as conn:
        return [row[0] for row in dbutil.selectSQL(sql=sql, args=args, conn=conn)]

    
def findGeneNameGenomePairsLike(substring, searchType=CONTAINS_TYPE, conn=None):
    '''
    substring: search for gene names containing this string somehow.
    searchType: specify how the gene name should contain substring
    genomes names are like Homo_sapiens.aa
    returns: list of unique pairs of gene name and genome names for every gene name containing substring according to the searchType
    mapped to all genomes that contain a seq id that has that gene name.
    '''
    sql = ' SELECT DISTINCT rs.gene_name, rg.acc'
    sql += ' FROM {} rs JOIN {} rg '.format(releaseTable(config.CURRENT_RELEASE, 'sequence'), releaseTable(config.CURRENT_RELEASE, 'genomes'))
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
    sql += ' ORDER BY rg.acc, rs.gene_name '
    
    # results are a tuple of tuples which containing an gene name and genome and genome name.
    with connCM(conn=conn) as conn:
        return [tuple(row) for row in dbutil.selectSQL(sql=sql, args=args, conn=conn)]


def getSeqIdsForGeneName(geneName, genome=None, conn=None):
    '''
    geneName: gene name or symbol, e.g. 'acsC'
    genome: genome id, e.g. 'Homo_sapiens.aa'.  If None, all seq ids with the gene name are returned.
    conn: db connection to use.  If None, one will be created.
    returns: list of sequence ids, i.e. a GI, ensembl id, etc., which have the given gene name.
    '''
    with connCM(conn=conn) as conn:
        sql = 'SELECT DISTINCT rs.external_sequence_id '
        sql += ' FROM {} rs '.format(releaseTable(config.CURRENT_RELEASE, 'sequence'))
        sql += ' WHERE rs.gene_name = %s '
        params = [geneName]
        if genome:
            dbId = getIdForGenome(genome, conn)
            sql += ' AND rs.genome_id = %s '
            params.append(dbId)

        # results are a tuple of tuples which containing an id.  convert to a list of ids.
        return [row[0] for row in dbutil.selectSQL(sql=sql, args=params, conn=conn)]


##########################
# DEPRECATED / UNUSED CODE
##########################
