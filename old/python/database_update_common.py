#!/usr/bin/env python

import os
import xml.dom.minidom
import xml.dom

import xml_util
import util
import dbutil
import config


#######################
# GLOBALS AND CONSTANTS
#######################

DEV_MYSQL_HOST = 'dev.mysql.cl.med.harvard.edu'
PROD_MYSQL_HOST = 'mysql.cl.med.harvard.edu'

DATABASE_ROOT = '/groups/rodeo/databases'

# LOCATION OF METADATA ABOUT DOWNLOADED DBS
METADATA_DIR = '/groups/rodeo/databases/metadata'
METADATA_FILE = os.path.join(METADATA_DIR, 'metadata.bsddb')
NCBI_BLAST_PROT_DB_FILE = os.path.join(METADATA_DIR, 'ncbi_blast_protein_db_list')
NCBI_BLAST_NUCL_DB_FILE = os.path.join(METADATA_DIR, 'ncbi_blast_nucleotide_db_list')
WU_BLAST_PROT_DB_FILE = os.path.join(METADATA_DIR, 'wu_blast_protein_db_list')
WU_BLAST_NUCL_DB_FILE = os.path.join(METADATA_DIR, 'wu_blast_nucleotide_db_list')
DATABASE_README_FILE = os.path.join(DATABASE_ROOT, 'README')
WEB_DATABASE_INFO_FILE = os.path.join(METADATA_DIR, 'database_info.fhtml')

# LOCATION OF UPDATED DBS
NCBI_BLAST_DEST_DIR = os.path.join(DATABASE_ROOT, 'blast')
WU_BLAST_DEST_DIR = os.path.join(DATABASE_ROOT, 'wublast')
FASTA_DEST_DIR = os.path.join(DATABASE_ROOT, 'fasta')

# LOCATION OF WORKING DIRS FOR DOWNLOADING, UNPACKING, FORMATTING, ETC.
UPDATE_DIR = os.path.join(DATABASE_ROOT, 'update')
DOWNLOAD_DIR = os.path.join(UPDATE_DIR, 'download')
PROCESS_DIR = os.path.join(UPDATE_DIR, 'unpack')
BACKUP_DIR = os.path.join(UPDATE_DIR, 'backup')

FROM_EMAIL = 'database_update-no-reply@orchestra.med.harvard.edu'
ERR_EMAIL = 'todd_deluca@hms.harvard.edu'


#
# CONFIG ATTRIBUTE NAMES
#
ID = 'id'
LABEL = 'label'
DESCRIPTION = 'description'
NOTES = 'notes'
TYPE = 'type'
DB_TYPE = 'db_type'
METHOD = 'method'
URL = 'url'
URLS = 'urls'
HOST = 'host'
DIR = 'dir'
FILES = 'files'
PROCESS = 'processing'
FORMAT = 'format'
NCBI_BLAST_FORMAT_OPTIONS = 'ncbi_blast_format_options'
SOURCES_AND_MODTIMES = 'sources_and_modtimes'
SOURCE_AND_MODTIME = 'source_and_modtime'
SOURCE = 'source'
MODTIME = 'modtime'
RELATIVE_PATHS = 'relative_paths'
DIR_PATTERN = 'dir_pattern'
PATTERN = 'pattern'
DOWNLOAD_TIME = 'download_time' # when this version of the db was downloaded.

#
# ATTRIBUTE VALUES
#

# METHODS and SCHEMES
RSYNC = 'rsync'
FILE = 'file'
NONE = 'none'
LOCAL = 'local'
FTP = 'ftp'
WGET = 'wget'
DEFAULT = 'default'

# TYPES
PROTEIN = 'protein'
NUCLEOTIDE = 'nucleotide'

# DB_TYPES
# WHOLE_GENOME = 'whole_genome'
GENOME = 'genome'

# PROCESSING
TARZ = 'tarz'
GUNZIP = 'gunzip'
CONCAT = 'concat'

# DB FORMATS
FASTA = 'fasta'
NCBI_BLAST = 'ncbi_blast'

# FORMATTING OPTIONS
NO_DASH_O = 'no_dash_o'



# used in files attribute
FILE_SEP = ','

#
DOWNLOAD_TIMEOUT = 30
RETRY_DELAY = 3

GZIPPED = 'gz'
TAR = 'tar'

######################
# DATABASE CONNECTIONS
######################


def withUpdateDbConn(conn=None, commit=True, host=DEV_MYSQL_HOST):
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

    
###################################
# PARSE CONFIGURATION FROM XML FILE
###################################

def dbToString(dbInfo):
    return dbInfo.toxml()


def dbFromString(dbString):
    '''
    returns: dbInfo object encoded by dbString
    '''
    return xml.dom.minidom.parseString(dbString).documentElement


def parseConfig(filename):
    doc = xml.dom.minidom.parse(filename)
    dbs = xml_util.getChildren(doc.documentElement)
    return dbs


def xmlNormalize(infile, outfile):
    '''
    read in an xml config file, and print it out in such a way that the whitespace is normalized.
    '''
    doc = xml.dom.minidom.parse(infile)
    root = xml_util.cloneElemTree(doc.documentElement)
    with open(outfile, 'w') as fo:
        fo.write(root.toprettyxml(indent='  ', newl='\n'))

                     
def individualizeConfigFile(filename, dir):
    '''
    filename: bio_databases xml config file, with multiple genome dbs in it.
    dir: directory to write each individual db config file.
    splilts a bio_databases config file into individual config files for each db.
    reads in the db config file, and writes out an xml file for each db in the config file, where the root element is <db>, not <bio_databases>.
    the individual xml files are named after the id of the db, with a .config.xml suffix, e.g. <dir>/Homo_sapiens.aa.config.xml
    '''
    doc = xml.dom.minidom.parse(filename)
    impl = xml.dom.minidom.getDOMImplementation()

    dbInfos = parseConfig(filename)
    for dbInfo in dbInfos:
        # create new xml document with no root element (yet)
        newDoc = impl.createDocument(None, None, None)
        dbId = xml_util.getTextValue(xml_util.getFirstChild(dbInfo, ID))
        if not id:
            raise Exception("missing id for db info. filename=%s\ndbInfo=%s"%(filename, dbToString(dbInfo)))

        newDoc.appendChild(xml_util.cloneElemTree(dbInfo, newDoc))
        fo = open(os.path.join(dir, dbId+'.config.xml'), 'w')
        fo.write(newDoc.toprettyxml(indent='    '))
        fo.close()
        newDoc.unlink()
    doc.unlink()

    
    
    
                
# last line
