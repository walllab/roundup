'''
# usage:
TMPDIR=/scratch bsub -q cbi_1d time python -c 'import sys; sys.path.append("/groups/rodeo/deploy/prod/database_update"); import update_dbs; update_dbs.updateDatabasesFromConfig("/groups/rodeo/deploy/prod/database_update/conf/uniprot_dbs.xml");'

# When downloading fails, and it will fail, the typical way to continue downloading the failed databases, after fixing whatever is wrong,
# is to copy the xml configs of the databases that still need to be updated into a file, e.g. /home/td23/test.xml, and rerun with that file:
# note: If you changed the code and are testing it in a dev env, change the sys.path.append() command.
# note: You should eventually redeploy/copy any changed code or config files to prod, assuming you are running cron jobs from prod.
TMPDIR=/scratch bsub -q cbi_1d time python -c 'import sys; sys.path.append("/groups/rodeo/deploy/prod/database_update"); import update_dbs; update_dbs.updateDatabasesFromConfig("/home/td23/test.xml");'

'''

# for each dbInfo in config file:
#   download db: location, download type, files
#   format db: unzipping, combining, formatting, untarring, copying
#   update html, etc., w/ db mod time, description, name/id
#   report any errors


import os
import re
import datetime
import stat
import tempfile
import ftplib
import urlparse
import uuid
import logging

import config
from database_update_common import *
import database_update_common
import execute
import xml_util
import util


################################
# ftp url functions
################################

def getMatchingFileUrls(url, pattern):
    '''
    url: url of ensembl ftp dir for a species and database type, e.g. 'ftp://ftp.ensembl.org/pub/current_xenopus_tropicalis/data/fasta/pep'
    pattern: regular expression string fed to re module, e.g.'Xenopus_tropicalis.*?\.pep\.all\.fa\.gz'
    returns: list of absolute urls to files in the directory of url which match pattern
    '''
    if url.endswith('/'):
        url = url[:-1]
    lenUrl = len(url)
    urls = []
    for (subUrl, dirs, files) in genFTPDirsAndFiles(url):
        urls.extend(['/'.join([subUrl, f]) for f in files])
    filteredUrls = [url for url in urls if re.search(pattern, url)]
    return filteredUrls


def genFTPDirsAndFiles(url, depth=10, conn=None, pause=1.0):
    '''
    For traversing a directory tree rooted at url.
    depth: search <depth> levels beneath this one.  if 0, only search directly in url dir.  if < 0, search completely beneath url.
    yields: (currentUrl, dirs, files), where currentUrl is url or a subdir of url, dirs is a list of dirnames in currentUrl and
    files is a list of filenames in currentUrl.
    e.g. ('ftp://bio-mirror.net/biomirror/ensembl/current_fasta', ['aedes_aegypti', 'bos_taurus', ...], ['.listing'])
    '''
    if url.endswith('/'):
        url = url[:-1]
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    # username:password@host:port -> host
    host = netloc.split('@')[-1].split(':')[0]

    closeConn = False
    if conn is None:
        conn = ftplib.FTP(host)
        conn.login()
        closeConn = True
        
    conn.cwd(path)
    files = []
    dirs = []
    if pause:
        import time
        time.sleep(pause)
    conn.retrlines('LIST', gatherDirsAndFiles(dirs, files))
    yield (url, dirs, files)
    if depth != 0:
        for dirname in dirs:
            subUrl = '/'.join([url, dirname])
            for retval in genFTPDirsAndFiles(subUrl, (depth-1), conn, pause):
                yield retval
    
    if closeConn:
        conn.quit()


def gatherDirsAndFiles(dirs, files):
    '''
    accumulator function to be used with ftplib.FTP.retrlines()
    '''
    def sub(line):
        if line.startswith('d'):
            dirname = line.split(None, 8)[8]
            if not dirname.startswith('.'):
                dirs.append(dirname)
        elif line.startswith('-'):
            filename = line.split(None, 8)[8]
            files.append(filename)
    return sub


#############################
# xml config helper functions
#############################

def setParam(node, param, value):
    '''
    node: xml dom node
    param: tagName of child element of node whose value is to be set.
    A "param" for our purposes is assumed to be the first and only (but we do not check) child element of a node, a child which contains only a text element.
    value: string stored in the text element that is the child of the param node.
    e.g. <node><param>value</param></node>
    if node has param already, value replaces the current value of param.  otherwise param is created and value is added as a text element.
    '''
    # remove old param node
    if hasParam(node, param):
        paramNode = xml_util.getFirstChild(node, param)
        node.removeChild(paramNode)
        paramNode.unlink()
        
    # build new param node
    doc = xml_util.getDocument(node)
    paramNode = doc.createElement(param)
    paramText = doc.createTextNode(value)
    paramNode.appendChild(paramText)
    node.appendChild(paramNode)
                                                                                                                                    
    
def hasParam(node, param):
    try:
        value = getParam(node, param)
        return value != None
    except:
        return False

    
def getParam(node, param):
    '''
    node: xml dom node
    param: tagName of child element of node
    A "param" for our purposes is the first (and only but we do not check) child element of a node, a child which contains only a text element.
    e.g. <node><param>value</param></node>
    returns: the text value of param child.
    '''
    paramNode = xml_util.getFirstChild(node, param)
    return xml_util.getTextValue(paramNode)


def getId(dbInfo):
    '''
    returns the value of the id element of the db element.  id is a required element of db.
    '''
    return getParam(dbInfo, ID)


def hasSourcesAndModTimes(dbInfo):
    sAndM = xml_util.getFirstChild(dbInfo, SOURCES_AND_MODTIMES)
    return sAndM != None


def getSourcesAndModTimes(dbInfo):
    '''
    returns: sources and mod times formatted as a list of pairs of source and modification time.
    '''
    sAndM = []
    if hasSourcesAndModTimes(dbInfo):
        sAndMNode = xml_util.getFirstChild(dbInfo, SOURCES_AND_MODTIMES)
        for pairNode in xml_util.getChildren(sAndMNode, SOURCE_AND_MODTIME):
            sAndM.append([getParam(pairNode, SOURCE), getParam(pairNode, MODTIME)])
    return sAndM


def setSourcesAndModTimes(dbInfo, downloadDir=None):
    '''
    attempts to create pairs of [sourcefile, lastmodificationtime], one for
    each source file of dbInfo and add them to dbInfo under sources_and_modtimes node.
    '''
    sAndM = []
    if downloadDir == None:
        downloadDir = os.path.join(DOWNLOAD_DIR, getId(dbInfo))
    # urls to download
    urls = dbUrls(dbInfo)
    for url in urls:
        downloadFile = makeFilenameFromUrl(url, downloadDir)
        try:
            modTime = str(datetime.date.fromtimestamp(os.stat(downloadFile)[stat.ST_MTIME]))
        except:
            modTime = 'No date available'
            logging.exception('[ERROR] setSourcesAndModTimes(): failed to get mod time for downloadFile='+str(downloadFile))
        sAndM.append([url, modTime])

    # remove any pre-existing s and m node
    if hasSourcesAndModTimes(dbInfo):
        sAndMNode = xml_util.getFirstChild(dbInfo, SOURCES_AND_MODTIMES)
        # sAndMNode = getSourcesAndModTimes(dbInfo)
        dbInfo.removeChild(sAndMNode)
        sAndMNode.unlink()
    # build new s and m node
    doc = xml_util.getDocument(dbInfo)
    sAndMNode = doc.createElement(SOURCES_AND_MODTIMES)
    dbInfo.appendChild(sAndMNode)
    for pair in sAndM:
        pairNode = doc.createElement(SOURCE_AND_MODTIME)
        sourceNode = doc.createElement(SOURCE)
        modtimeNode = doc.createElement(MODTIME)
        sourceText = doc.createTextNode(pair[0])
        modtimeText = doc.createTextNode(pair[1])
        sourceNode.appendChild(sourceText)
        modtimeNode.appendChild(modtimeText)
        pairNode.appendChild(sourceNode)
        pairNode.appendChild(modtimeNode)
        sAndMNode.appendChild(pairNode)
        
    return dbInfo


def getDbDownloadDir(dbInfo):
    return os.path.join(DOWNLOAD_DIR, getId(dbInfo))


def getDbProcessDir(dbInfo):
    return os.path.join(PROCESS_DIR, getId(dbInfo))


def getDbFastaFile(dbInfo):
    return os.path.join(FASTA_DEST_DIR, getId(dbInfo))


def getNcbiBlastFilePattern(dbInfo):
    '''
    returns: a pattern used to find or delete files for a db.  e.g. /groups/rodeo/databases/blast/Homo_sapiens.aa*
    '''
    return os.path.join(NCBI_BLAST_DEST_DIR, getId(dbInfo))+'*'


def getWuBlastFilePattern(dbInfo):
    '''
    returns: a pattern used to find or delete files for a db.  e.g. /groups/rodeo/databases/wublast/Homo_sapiens.aa*
    '''
    return os.path.join(WU_BLAST_DEST_DIR, getId(dbInfo))+'*'



#
# DB INFO EXTRACTION
#
def getUrls(dbInfo):
    def getRelativePathsUrls(pathsNode):
        url = getParam(pathsNode, URL)
        files = dbList(pathsNode, FILES)
        return [os.path.join(url, f) for f in files]
    def getUrlUrls(urlNode):
        return [xml_util.getTextValue(urlNode)]
    def getDirPattern(node):
        url = getParam(node, URL)
        pattern = getParam(node, PATTERN)
        return getMatchingFileUrls(url, pattern)
        
    funcLookup = {URL: getUrlUrls, RELATIVE_PATHS: getRelativePathsUrls, DIR_PATTERN: getDirPattern}
    urlsNode = xml_util.getFirstChild(dbInfo, URLS)
    urls = []
    for kid in xml_util.getChildren(urlsNode):
        urls += funcLookup[kid.tagName](kid)
    # for url in urls:
    #     print url
    return urls


def testUrls(filename):
    dbs = parseConfig(filename)
    for dbInfo in dbs:
        urls = getUrls(dbInfo)
        print 'ID: %s' %getId(dbInfo)
        for url in urls:
            print '\turl: %s'%url

    
def dbProcesses(dbInfo):
    '''  returns the list of processes in a dbInfo config '''
    return dbList(dbInfo, PROCESS)


def splitList(listString):
    return [i.strip() for i in listString.strip().split(FILE_SEP)]


def dbList(node, param):
    ''' returns a list of the values in dbInfo for the param.
    e.g. "foo,bar,baz" -> ['foo','bar','baz']
    '''
    return splitList(getParam(node, param))


def dbFiles(dbInfo):
    ''' returns the list of files in a dbInfo config '''
    return dbList(dbInfo, FILES)


def dbUrls(dbInfo):
    ''' return: seq of urls from dbInfo. '''
    return getUrls(dbInfo)

    if hasParam(dbInfo, FILES):
        urls = [os.path.join(getParam(dbInfo, URL), f) for f in dbList(dbInfo, FILES)]
    else:
        urls = [getParam(dbInfo, URL)]
    return urls


def checkModTime(path):
    '''returns None if file path does not exist, the modification time otherwise. '''
    if not os.path.isfile(path):
        return None
    else:
        return os.stat(path)[stat.ST_MTIME]


def makeFilenameFromUrl(url, rootDir):
    '''
    rootDir: dir under which filename for url will be placed.
    return: filename derived from url, below rootDir
    '''
    # create download file name from url
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    # username:password@host:port -> host
    host = netloc.split('@')[-1].split(':')[0]
    # print 'rootDir:', rootDir
    # print 'host:', host
    # print 'path:', path
    # trim any leading slashes so join works correctly
    if path and path[0] == '/':
        path = path[1:]
    filename = os.path.join(rootDir, host, path)
    return filename


def gunzipFile(path):
    '''
    path: filename to gunzip.  Should end in .gz, I think.
    return: the new name of the file (gunzip renames the file by removing the .gz extension.)
    throws: Exception if there is a problem gunzipping the file.
    '''
    execute.run('gunzip '+path)
    return re.sub('\.gz$', '', path)


def downloadUrl(url, destination=None, method=None):
    '''
    url: url to download
    destination: path to a file to download url to.
    method: if set to 'wget', will attempt to download url using wget.
    Downloads url to the destination.  If that filename exists or if destination is a file which exists,
    checks the modification date of the destination against the modification date of the url to see if destination has been modified.
    Currently the way it gets the url modification date is lame.  Be cautious.
    returns: Whether or not the destination has been modified, based on modification date comparison.
    raises: Exception if there is a problem downloading the url.
    '''
    
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)

    # create download file name from url
    if os.path.isdir(destination):
        raise Exception('Destination must not be a directory, which it was.  destination='+str(destination)+' and url='+str(url))
    
    # if file contains any path components, make sure they exist
    if not os.path.exists(os.path.dirname(destination)): os.makedirs(os.path.dirname(destination), 0770)
    
    oldModTime = checkModTime(destination)

    if method == WGET:
        cmd = 'wget --timestamping --passive-ftp --no-verbose --output-document='+destination+' '+url
        execute.run(cmd)
    elif scheme == RSYNC:
        cmd = 'rsync --archive --quiet '+url+' '+destination
        execute.run(cmd)
    else:
        cmd = 'curl --remote-time --output '+destination+' '+url
        execute.run(cmd)
            
    newModTime = checkModTime(destination)
    if oldModTime != newModTime:
        return True
    else:
        return False


def downloadUrls(urls, downloadDir, method=DEFAULT):
    '''
    urls: list of urls to download
    downloadDir: dir where url contents are saved.
    returns: tuple of list of downloaded files names and list of whether the download file is modified
    (based on the modification date of the existing download file.)
    '''
    modifieds = []
    downloadFiles = []
    
    for url in urls:
        logging.debug('downloading url: '+str(url))
        # create download file name from url
        # scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
        downloadFile = makeFilenameFromUrl(url, downloadDir)

        modified = downloadUrl(url, downloadFile, method)

        modifieds.append(modified)
        downloadFiles.append(downloadFile)
        
    return (downloadFiles, modifieds)


def downloadDb(dbInfo, downloadDir=None):
    '''
    dbInfo: a configuration dict
    download a database from its remote location to the download dir
    on error, throw UpdateError
    return whether or not db has been modified.
    '''

    if not downloadDir:
        downloadDir = getDbDownloadDir(dbInfo)

    # urls to download
    urls = dbUrls(dbInfo)
    # method of download
    if hasParam(dbInfo, METHOD) and getParam(dbInfo, METHOD):
        method = getParam(dbInfo, METHOD)
    else:
        method = DEFAULT

    downloadFiles, modifieds = downloadUrls(urls, downloadDir, method)

    if True in modifieds:
        return True
    else:
        return False


def processDbSub(dbInfo, downloadDir, processDir):

    # e.g. gunzip, concat
    processes = dbProcesses(dbInfo)

    # if process == NONE, do nothing.
    if processes and NONE in processes:
        return
    
    # clean the processing dir
    execute.run('rm -rf '+processDir)
    os.makedirs(processDir, 0770)

    urls = dbUrls(dbInfo)
    processFiles = []
    
    # copy files from download dir to process dir for processing
    # for file in files:
    for url in urls:
        downloadFile = makeFilenameFromUrl(url, downloadDir)
        processFile = makeFilenameFromUrl(url, processDir)

        # copy file to processing dir
        # downloadFile = os.path.join(downloadDir, file)
        # processFile = os.path.join(processDir, file)
        processFiles.append(processFile)
        
        # make sure all the path components of the file exist before copying it over.
        if not os.path.exists(os.path.dirname(processFile)): os.makedirs(os.path.dirname(processFile), 0770)

        execute.run('cp '+downloadFile+' '+processFile)

    # process database
    for process in processes:

        # process files
        if process == TARZ:
            # make empty and unique dir to unpack files
            tmpDir = os.path.join(processDir, uuid.uuid4().hex)
            os.makedirs(tmpDir, 0770)
            # unpack files to fresh dir
            for processFile in processFiles:
                # explode into processing dir
                execute.run('tar -xzf '+processFile+' -C'+tmpDir)
                # remove original file
                execute.run('rm -f '+processFile)
            processFiles = [os.path.join(tmpDir, f) for f in os.listdir(tmpDir)]
            
        elif process == GUNZIP:
            newFiles = []
            for processFile in processFiles:
                # unzip file
                execute.run('gunzip '+processFile)
                newFiles.append(re.sub('\.gz$', '', processFile))
            # gunzipping changes the file names.
            processFiles = newFiles
            
        elif process == CONCAT:
            # concatenate all process files into one file.
            # use tmpFile in case one of the process files has the same name as concatFile
            concatFile = os.path.join(processDir, getId(dbInfo))
            (fd, tmpFile) = tempfile.mkstemp(dir=processDir)
            os.close(fd)
            for processFile in processFiles:
                execute.run('cat '+processFile+' >>'+tmpFile)
                # remove original file
                execute.run('rm -f '+processFile)
            execute.run('mv '+tmpFile+' '+concatFile)
            # correct for incorrect mode of temp file.
            execute.run('chmod 664 '+concatFile)
            processFiles = [concatFile]

    return processFiles


def processDb(dbInfo, downloadDir=None, processDir=None):
    '''
    decompress, untar, and move database to their approriate location.
    throw UpdateException on error
    '''
    if not downloadDir:
        downloadDir = getDbDownloadDir(dbInfo)
    if not processDir:
        processDir = getDbProcessDir(dbInfo)

    if getParam(dbInfo, FORMAT) == FASTA:
        processFastaDb(dbInfo, downloadDir, processDir, FASTA_DEST_DIR)
    elif getParam(dbInfo, FORMAT) == NCBI_BLAST:
        processNCBIBlastDb(dbInfo, downloadDir, processDir, NCBI_BLAST_DEST_DIR)


def processFastaDb(dbInfo, downloadDir, processDir, fastaDir):
    '''
    downloadDir: contains source files for dbInfo
    processDir: directory is removed, created and removed. Therefore it should be a temporary dir.
    fastaDir: where the resulting fasta file will be copied.
    process downloaded files into a fasta-formatted database file named after the database id and located in the fastaDir.
    returns: path to fasta file
    '''
    processFiles = processDbSub(dbInfo, downloadDir, processDir)
    if len(processFiles) != 1:
        raise Exception('Expecting exactly one fasta file in processFiles.  processFiles=%s, dbInfo=%s'%(processFiles, dbInfo))
    fastaFilename = os.path.join(fastaDir, os.path.basename(processFiles[0]))
    execute.run('mv '+processFiles[0]+' '+fastaFilename)
    # clean the processing dir
    execute.run('rm -rf '+processDir)
    return fastaFilename

   
def processNCBIBlastDb(dbInfo, downloadDir, processDir, ncbiBlastDir):
    processFiles = processDbSub(dbInfo, downloadDir, processDir) 
    for f in processFiles:
        execute.run('mv '+f+' '+ncbiBlastDir)
    # clean the processing dir
    execute.run('rm -rf '+processDir)


def formatDb(dbInfo):
    '''
    format db info in ways appropriate for it based on its configuration.
    '''

    if getParam(dbInfo, FORMAT) == FASTA:
        formatFastaDb(dbInfo)


def formatFastaDb(dbInfo):
    '''
    format fasta files for processing by algorithms: blast, wublast, blast, etc.
    '''
    # what is the name of a fasta file, is it named after the files in dbFiles(dbInfo) or after getId(dbInfo)?
    fastaFile = getDbFastaFile(dbInfo)

    # Get the names of the fasta files
    # assumes fasta file is named after the db id!
    files = [getId(dbInfo)]


    #
    # NCBI BLAST
    #
    os.chdir(NCBI_BLAST_DEST_DIR)

    # SET PROTEIN FLAG
    dbType = getParam(dbInfo, TYPE).strip()
    if dbType == 'protein':
        proteinOption = 'T'
    elif dbType == 'nucleotide':
        proteinOption = 'F'
    else:
        raise Exception('Unrecognized database type for fasta processing: '+str(dbType))

    # SET -o OPTION
    oOption = '-o'
    if hasParam(dbInfo, NCBI_BLAST_FORMAT_OPTIONS):
        options = dbList(dbInfo, NCBI_BLAST_FORMAT_OPTIONS)
        if NO_DASH_O in options:
            oOption = ''
    # format each file.  since each formatted db name is taken fom getId(dbInfo), there should be only one file, since
    # the output of formatting the other files will get overwritten.
    cmd = 'formatdb -i'+fastaFile+' -p'+proteinOption+' -n'+getId(dbInfo)+' '+oOption
    # cmd += ' -v1000 ' # controlling the size of volumes produced by formatdb
    execute.run(cmd)

    #
    # WU BLAST
    #
    dbType = getParam(dbInfo, TYPE).strip()
    if dbType == 'protein':
        proteinOption = '-p'
    elif dbType == 'nucleotide':
        proteinOption = '-n'
    else:
        raise Exception('Unrecognized database type for fasta processing: '+str(dbType))

    # format the fasta db, naming and placing the output files in outputDb, and creating and index for xdget
    outputDb = os.path.join(WU_BLAST_DEST_DIR, getId(dbInfo))
    execute.run('xdformat -k -I '+proteinOption+' -o '+outputDb+' '+fastaFile)


##########################
# GENERATE FILES FUNCTIONS
##########################

def getFastaDbs(dir):
    files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
    return files


def getWuBlastDbs(dir):
    '''
    returns a list of all wu blast database ids inferred from the files in dir
    '''

    wuIndexRE = '(.*)\.(x[pn]d)$' # files ending in .xpd or .xnd
    # Do the following:
    # list the dir
    # filter out directories
    # only look and .xpd and .xnd files
    # remove the file type suffix
    files = [re.search(wuIndexRE, f).group(1) for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f)) and re.search(wuIndexRE, f)]

    return files


def getBlastDbs(dir):
    '''
    returns a list of blast database ids inferred from the files in the dir
    '''

    # all the files in dir
    files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]

    # just the nhr, phr, pal, and nal files
    pnhrRE = '(.*)\.([pn]hr|[pn]al)$' # file extensions that are nal, pal, nhr, phr
    files = [f for f in files if re.search(pnhrRE, f)]

    # strip the extension
    files = [re.search(pnhrRE, f).group(1) for f in  files]
    # map(lambda f: re.search(pnhrRE, f).group(1), files)

    # if file a matches (.*)\.\d+ and there exists another file b named $1, remove file a
    # e.g. this is meant to remove est.00.nhr when there exists est.nal
    # but not remove a database that happens to be named foo.1234
    fileMap = dict([(f, f) for f in files])
    dbPartRE = '(.*)\.\d+$' # file extensions that are numeric
    files = [f for f in files if not re.search(dbPartRE, f) or not fileMap.has_key(re.search(dbPartRE, f).group(1))]
    files = filter(lambda f: (not re.search(dbPartRE, f)) or not fileMap.has_key(re.search(dbPartRE, f).group(1)), files)

    # remove duplicates (if for some reason a db has a .nal and .nhr file, for example.)
    # real example: month.htgs has a nal and nhr file
    files = dict([(f,f) for f in files]).keys()

    return files


def deleteMetadata(dbId):
    extensions = ['description', 'ncbi_blast_protein', 'ncbi_blast_nucleotide', 'wu_blast_protein', 'wu_blast_nucleotide']
    for path in [os.path.join(METADATA_DIR, '%s.%s'%(dbId, ext)) for ext in extensions]:
        if os.path.isfile(path):
            os.remove(path)

    
def saveMetadata(dbInfo):
    '''
    add sources and mod times to dbInfo and then persist the metadata.  Also generate description files used by website.
    '''
    dbId = getId(dbInfo)
    dbType = getParam(dbInfo, TYPE).strip()

    setSourcesAndModTimes(dbInfo)

    ncbiDbIds = getBlastDbs(NCBI_BLAST_DEST_DIR)
    wuDbIds = getWuBlastDbs(WU_BLAST_DEST_DIR)
    fastaDbIds = getFastaDbs(FASTA_DEST_DIR)

    descPath = os.path.join(METADATA_DIR, '%s.description'%dbId)
    ncbiProtPath = os.path.join(METADATA_DIR, '%s.ncbi_blast_protein'%dbId)
    ncbiNuclPath = os.path.join(METADATA_DIR, '%s.ncbi_blast_nucleotide'%dbId)
    wuProtPath = os.path.join(METADATA_DIR, '%s.wu_blast_protein'%dbId)
    wuNuclPath = os.path.join(METADATA_DIR, '%s.wu_blast_nucleotide'%dbId)

    desc = formatDbForDesc(dbInfo)
    if dbId in ncbiDbIds:
        desc += '\tAvailable for NCBI BLAST on Rodeo and on orchestra.med.harvard.edu at %s\n' % os.path.join(NCBI_BLAST_DEST_DIR, dbId)
        if dbType == PROTEIN:
            util.writeToFile(dbId+'\n', ncbiProtPath)
        if dbType == NUCLEOTIDE:
            util.writeToFile(dbId+'\n', ncbiNuclPath)
    if dbId in wuDbIds:
        desc += '\tAvailable for WU BLAST on Rodeo and on orchestra.med.harvard.edu at %s\n' % os.path.join(WU_BLAST_DEST_DIR, dbId)
        if dbType == PROTEIN:
            util.writeToFile(dbId+'\n', wuProtPath)
        if dbType == NUCLEOTIDE:
            util.writeToFile(dbId+'\n', wuNuclPath)
    if dbId in fastaDbIds:
        desc += '\tAvailable in FASTA format on orchestra.med.harvard.edu at %s\n' % os.path.join(FASTA_DEST_DIR, dbId)
    
    util.writeToFile('%s\n'%desc, descPath)
    
                        
def formatDbForDesc(dbInfo):
    '''
    return a string summarizing dbInfo for database description file.
    '''
    desc = 'Database Id: '+str(getId(dbInfo))+'\n'
    for (name, key) in (('Label', LABEL), ('Description', DESCRIPTION), ('Notes', NOTES), ('Type', TYPE), ('Database Type', DB_TYPE)):
        if hasParam(dbInfo, key):
            desc += '\t'+name+': '+str(getParam(dbInfo, key))+'\n'
    if hasSourcesAndModTimes(dbInfo):
        sAndMs = getSourcesAndModTimes(dbInfo)
        for (source, modTime) in sAndMs:
            desc += '\tSource: '+str(source)+'\n\t\tLast Modified: '+str(modTime)+'\n'
    return desc

    
############
# EXCEPTIONS
############

class UpdateError(StandardError):
    def __init__(self, errors):
        self.errs = errors
    def errors(self):
        return self.errs


############
# WORKFLOW
############

def rsyncTimeoutPred(error):
    '''
    error: UpdateError object
    returns True if error contains an error which matches an rsync connection timeout error.
    returns False otherwise.
    '''
    regex = r'rsync.*Connection timed out'
    try:
        for e in error.errors():
            if re.search(regex, e):
                return True
    finally:
        return False


def downloadOp(dbInfo, skip):
    '''
    dbInfo:
    skip: If true, skip downloading
    downloads a database based on the info in dbInfo.
    returns True if the database is modified (i.e. if the remote db is newer than the local db)
    '''
    if not skip:
        logging.debug('...downloading...')
        modified = downloadDb(dbInfo)
    else:
        modified = 0
    return modified


def processOp(dbInfo, force, modified):
    '''
    dbInfo:
    force: if true, process the db even if it is not modified.
    modified: whether or not the last step modified the db, and hence whether the db needs to be updated
    processes a database if it is modified or if force is true.  What is processing?  That is for me to know....
    returns None
    '''
    if modified or force:
        logging.debug('...processing...')
        processDb(dbInfo)
    else:
        logging.debug('skipping processing of unmodified db')


def formatOp(dbInfo, force, modified):
    '''
    dbInfo:
    force: if true, format the db even if it is not modified.
    modified: whether or not the last step modified the db, and hence whether the db needs to be updated
    format a database if it is modified or if force is true.  Format for blast, wublast, etc. based on dbInfo.
    returns None
    '''
    if modified or force:
        logging.debug('...formatting...')
        formatDb(dbInfo)
    else:
        logging.debug('skipping formatting of unmodified db')


def updateDatabases(dbInfos, skipDownload, forceProcess, forceFormat):
    for dbInfo in dbInfos:
        try:
            print getId(dbInfo)
            logging.debug('Updating '+getId(dbInfo)+' skipDownload='+str(skipDownload)+' forceProcess='+str(forceProcess)+' forceFormat='+str(forceFormat))
            try:
                modified = util.retryErrorExecute(operation=downloadOp, args=[dbInfo, skipDownload], pred=rsyncTimeoutPred, numTries=10, delay=10, backoff=1.4)
            except:
                logging.exception('Download Exception Found')
                raise Exception('DownloadException', 'download exception caught and logged.  Skipping the rest of the update of %s'%getId(dbInfo))
            processOp(dbInfo, forceProcess, modified)
            formatOp(dbInfo, forceFormat, modified)
            saveMetadata(dbInfo)
        except Exception, e:
            if 'DownloadException' in e.args:
                # exception already logged.  continue with next db update
                continue
            else:
                # escalate other exceptions
                raise

    
def updateDatabasesFromConfig(configPath, skipDownload=False, forceProcess=False, forceFormat=False):
    dbInfos = database_update_common.parseConfig(configPath)
    updateDatabases(dbInfos, skipDownload, forceProcess, forceFormat)

    
def deleteDatabase(dbInfo):
    '''
    Deletes database from metadata, downloads dir, processing dir, blast, wublast, fasta dirs.
    '''
    # remove the download, process, and fasta if they exist.
    downloadDir = getDbDownloadDir(dbInfo)
    processDir = getDbProcessDir(dbInfo)
    fastaFile = getDbFastaFile(dbInfo)
    for fileOrDir in [downloadDir, processDir, fastaFile]:
        if os.path.exists(fileOrDir):
            execute.run('rm -rf '+fileOrDir)

    # remove all the db indices created for blast, wublast
    ncbiBlastFilePattern = getNcbiBlastFilePattern(dbInfo)
    wuBlastFilePattern = getWuBlastFilePattern(dbInfo)
    for pattern in [ncbiBlastFilePattern, wuBlastFilePattern]:
        execute.run('rm -f '+pattern)

    # remove the metadata
    deleteMetadata(getId(dbInfo))


def deleteDatabases(dbInfos):
    '''
    Deletes database from metadata, downloads dir, processing dir, blast, wublast, fasta dirs.
    '''
    for dbInfo in dbInfos:
        deleteDatabase(dbInfo)


def deleteDatabasesFromConfig(configPath):
    '''
    example config file: database_update/conf/genomes.xml
    '''
    dbInfos = database_update_common.parseConfig(configPath)
    deleteDatabases(dbInfos)

    
if __name__ == '__main__':
    pass

# last line
