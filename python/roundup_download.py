#!/usr/bin/env python

'''
What is going on here?

a roundup/genome database path is a directory containing a roundup fasta file, blast indices, and metadata files.
a genome database is downloaded, formatted, processed, etc, in a temp dir area to create the necessary files.
a genome database path is then copied to the updated dir if it is "newer" than the current version of that database
  or discarded otherwise.

a current genome database path is one that has had its roundup results computed and loaded into mysql
an updated genome database path is one that has been downloaded and is newer than the current version, but has not
  yet been computed completely and loaded into mysql.
a new genome database path is one that is being downloaded and will be moved to updated if it is newer than other versions, or discarded otherwise.


'''

import itertools
import os
import shutil
import datetime
import xml_util
import urlparse
import re
import logging

import config
import execute
import fasta
import util
import nested
import update_dbs
import database_update_common
import roundup_common
import alias_fasta_name


DATABASE_DOWNLOAD_EXCEPTION_TAG = 'DatabaseDownloadException'


####################
# METADATA FUNCTIONS
####################

    
def formatDbForDesc(dbInfo):
    '''
    dbInfo: configuration of genome to download, process into a fasta file, and then format into a roundup fasta file with blast indices
    return a string summarizing dbInfo for database description file.
    '''
    desc = 'Database Id: '+str(update_dbs.getId(dbInfo))+'\n'
    for (name, key) in (('Label', database_update_common.LABEL), ('Description', database_update_common.DESCRIPTION), ('Notes', database_update_common.NOTES), ('Type', database_update_common.TYPE), ('Database Type', database_update_common.DB_TYPE), ('Download Date', database_update_common.DOWNLOAD_TIME)):
        if update_dbs.hasParam(dbInfo, key):
            desc += '\t'+name+': '+str(update_dbs.getParam(dbInfo, key))+'\n'
        # if dbInfo.has_key(key):
        #     desc += '\t'+name+': '+str(dbInfo[key])+'\n'
    if update_dbs.hasSourcesAndModTimes(dbInfo):
        sAndMs = update_dbs.getSourcesAndModTimes(dbInfo)
        # if dbInfo.has_key(database_update_common.SOURCES_AND_MODTIMES):
        # sAndMs = dbInfo[database_update_common.SOURCES_AND_MODTIMES]
        for (source, modTime) in sAndMs:
            desc += '\tSource: '+str(source)+'\n\t\tLast Modified: '+str(modTime)+'\n'
    return desc


def saveMetadata(dbInfo, dbPath):
    '''
    dbInfo: configuration of genome to download, process into a fasta file, and then format into a roundup fasta file with blast indices
    save metadata and description files to the specified path.
    '''
    dbId = roundup_common.getIdFromDbPath(dbPath)
    path = os.path.join(dbPath, '%s.metadata'%dbId)
    util.dumpObject(database_update_common.dbToString(dbInfo), path)

    desc = formatDbForDesc(dbInfo)+'\n'
    descPath = roundup_common.getDbDescriptionPathFromDbPath(dbPath)
    util.writeToFile(desc, descPath)

    
def loadMetadata(dbPath):
    '''
    returns: dbInfo object saved under metadataPath
    '''
    dbId = roundup_common.getIdFromDbPath(dbPath)
    path = os.path.join(metadataPath, '%s.metadata'%dbId)
    return database_update_common.dbFromString(util.loadObject(path))
    

#####################
# DB UPDATE FUNCTIONS
#####################

def createDb(dbInfo, rootDir):
    '''
    dbInfo: configuration of genome to download, process into a fasta file, and then format into a roundup fasta file with blast indices
    rootDir: empty dir under which all the work is done and the results are placed.
    Download, process, format, and generate metadata for a genome, storing it all under the rootDir directory
    returns: dir below rootDir named after the db id containing the formatted blast index files and fasta file for the database.
    throws: DATABASE_DOWNLOAD_EXCEPTION_TAG if an exception occurs while downloading.  Might throw some other exception if one occurs when not downloading.
    '''
    id = update_dbs.getId(dbInfo)

    print 'rootDir %s'%rootDir
    downloadDir = os.path.join(rootDir, 'download')
    processDir = os.path.join(rootDir, 'process')
    fastaDir = os.path.join(rootDir, 'fasta')
    formatDir = os.path.join(rootDir, 'format')
    dbPath = os.path.join(rootDir, 'final', id)
    for d in [downloadDir, processDir, fastaDir, dbPath]:
        if not os.path.isdir(d):
            os.makedirs(d, 0775)

    # download, process, and format db
    print 'downloading...'
    # since downloading failures are so common, handle them separately from other kinds of failures.
    try:
        update_dbs.downloadDb(dbInfo, downloadDir=downloadDir)
    except:
        logging.exception('Download Error.')
        raise
    
    print 'processing...'
    fastaFile = update_dbs.processFastaDb(dbInfo, downloadDir=downloadDir, processDir=processDir, fastaDir=fastaDir)
    
    print 'formatting...'
    # format fasta file for roundup and generate blast indices
    newRoundupFastaFile = formatGenomeForRoundup(fastaFile, dbPath)
    
    print 'saving metadata...'
    update_dbs.setSourcesAndModTimes(dbInfo, downloadDir=downloadDir)
    update_dbs.setParam(dbInfo, database_update_common.DOWNLOAD_TIME, str(datetime.datetime.now()))
    saveMetadata(dbInfo, dbPath)
        
    return dbPath


def formatGenomeForRoundup(sourceDbPath, destDir):
    '''
    sourceDbPath: path to fasta formatted database
    destDir: location to put the name-mangled fasta db and the blast index files
    Creates a copy of sourceDb in destDir which has shortened name lines.
    Then formats new db in destdir for wu (washington university) blast.
    returns: path to formatted fasta file (in the same dir as the wublast indices)
    '''
    destFastaPath = os.path.join(destDir, os.path.basename(sourceDbPath))
    newDb = None
    fs = None
    try:
        newDb=open(destFastaPath, 'w')

        # Open the unformatted NCBI (or other source) proteomic, fasta-formatted file to be chopped and xdformatted
        fs = open(sourceDbPath)
        # ignoring parse errors, since some of the files we get are sometimes poorly formatted.
        for (name, seq) in fasta.readFastaIter(fs, ignoreParseError=True):
            # name has '>', so does alias
            alias = alias_fasta_name.aliasName(name)
            newDb.write("%s\n%s\n"%(alias, seq))
    finally:
        if newDb:
            newDb.close()
        if fs:
            fs.close()
    
    # format for WU BLAST
    # import BioUtilities
    # BioUtilities.runXDformat('p', destFastaPath, destFastaPath)

    # format for NCBI BLAST
    os.chdir(os.path.dirname(destFastaPath))
    cmd = 'formatdb -p -o -i'+os.path.basename(destFastaPath)
    execute.run(cmd)

    return destFastaPath


def updateDb(dbInfo):
    '''
    Does all the downloading, processing, formatting, etc. to create a database and its associated metadata.
    Then compares the database to any existing versions of the database in the current or updated areas to see if this
    one is different and should be put into the updated area.
    returns: nothing
    '''
    
    id = update_dbs.getId(dbInfo)
    tempDir = None
    try:
        print '\nroundup_update for %s'%id
        # create temp dir
        tempDir = nested.makeTempDir(prefix=id+'_')
        print 'tempDir %s'%tempDir
        
        # create new database dir containing formatted files, metadata, etc., for db info
        newDbPath = createDb(dbInfo, tempDir)
        
        # if the new db is different from the current (if any) and different from the updated (if any), copy it to updated.
        # track update history.
        currentDbPath = roundup_common.currentDbPath(id)
        updatedDbPath = roundup_common.updatedDbPath(id)
        print 'newDbPath: ', newDbPath
        print 'currentDbPath: ', currentDbPath
        print 'updatedDbPath: ', updatedDbPath
        if not os.path.exists(currentDbPath):
            if not os.path.exists(updatedDbPath):
                print 'new genome.  add to updated.  '+str(id)
                roundup_common.copyDbPath(newDbPath, updatedDbPath)
                roundup_common.logHistory('download new_and_add_updated genome=%s\n'%(id))
            elif not roundup_common.dbPathsEqual(newDbPath, updatedDbPath):
                print 'new genome.  replace updated.  '+str(id)
                roundup_common.copyDbPath(newDbPath, updatedDbPath)
                roundup_common.logHistory('download new_and_replace_updated genome=%s\n'%(id))
            else:
                pass # downloaded genome == updated genome.  do nothing.
        elif not roundup_common.dbPathsEqual(newDbPath, currentDbPath):
            if not os.path.exists(updatedDbPath):
                print 'existing genome.  add to updated.  '+str(id)
                roundup_common.copyDbPath(newDbPath, updatedDbPath)
                roundup_common.logHistory('download existing_and_add_updated genome=%s\n'%(id))
            elif not roundup_common.dbPathsEqual(newDbPath, updatedDbPath):
                print 'existing genome.  replace updated.  '+str(id)
                roundup_common.copyDbPath(newDbPath, updatedDbPath)
                roundup_common.logHistory('download existing_and_replace_updated genome=%s\n'%(id))
            else:
                pass # downloaded genome == updated genome.  do nothing.
        else:
            pass # downloaded genome == current genome.  do nothing.

        print 'deleting tempDir...'
        shutil.rmtree(tempDir)
    except Exception, e:
        # log and ignore errors, except to clean up temp dir.
        logging.exception('Error.')
        # delete temp dir
        if tempDir:
            print 'deleting tempDir in except block...'
            shutil.rmtree(tempDir)
        # download failures are so common we log and then continue with other dbs
        # if e.args and e.args[0] == DATABASE_DOWNLOAD_EXCEPTION_TAG:
        #     logging.exception('Error.')
        # any other failure we abort the entire process.
        # else:
        #     raise
                
    print 'done updating %s\n'%id


######################################
# CHECKING AND ADDING GENOME FUNCTIONS
######################################

def getBaseUrl(urls):
    '''
    urls: list of urls.
    returns: the deepest common path of all the urls.
    e.g. ['ftp://foo.com/foo/bar/dog', 'ftp://foo.com/foo/bar/cat/bat'] -> 'ftp://foo.com/foo/bar' 
    '''
    if not urls:
        raise Exception('baseUrl: no urls')
    splitUrls = [url.split('/') for url in urls]
    baseUrlComponents = []
    for i in range(len(splitUrls[0])):
        component = splitUrls[0][i]
        for split in splitUrls:
            if split[i] != component:
                return '/'.join(baseUrlComponents)
        baseUrlComponents.append(component)
    return '/'.join(baseUrlComponents)


def checkConfig(dbInfo):
    '''
    check the urls of the config against the possible protein genome urls.
    returns: lines of data, including a warning if the config urls do not match exactly the possible urls.
    '''
    id = update_dbs.getId(dbInfo)
    print id
    lines = ['check config for '+str(id)]
    # file urls
    urls = update_dbs.dbUrls(dbInfo)
    print urls
    # dir urls: strip off the last component in the path.
    dirUrls = ['/'.join(url.split('/')[:-1]) for url in urls]
    print dirUrls
    baseUrl = getBaseUrl(dirUrls)
    possibleUrls = searchForPossibleUrls(baseUrl)
    for url in urls:
        if url not in possibleUrls:
            lines.append('warning: url missing from possibleUrls.')
            lines.append('    id='+str(id))
            lines.append('    baseUrl='+str(baseUrl))
            lines.append('    url='+str(url))
            lines.append('    urls='+str(urls))
            lines.append('    possibleUrls='+str(possibleUrls))
            break
    for possibleUrl in possibleUrls:
        if possibleUrl not in urls:
            lines.append('warning: possibleUrl missing from urls.')
            lines.append('    id='+str(id))
            lines.append('    possibleUrl='+str(possibleUrl))
            lines.append('    urls='+str(urls))
            lines.append('    possibleUrls='+str(possibleUrls))
            break
    return lines
    # check that all possibleUrls are in urls and vice versa.
    
    
def searchForPossibleUrls(url):
    '''
    url: ftp url directory
    search beneath url, including subdirs, for potential genome protein fasta filenames.
    return: a list containing a url for every matching file found under url dir.
    '''
    if url.endswith('/'):
        url = url[:-1]
    # possible genome protein fasta filenames pattern.
    pattern = '.*\.faa\.gz|.*\.pep\.all\.fa\.gz|protein\.fa\.gz|proteins\.[^.]+\.fasta\.gz|orf_trans\.fasta\.gz|all\.pep'
    urls = update_dbs.getMatchingFileUrls(url, pattern)
    # filteredFiles = update_dbs.filterFTPFiles(url, pattern, deep=True, pause=2.0)
    # print 'filteredFiles', filteredFiles
    # return ['/'.join([url, path]) for path in filteredFiles]
    return urls


def makeConfigsForMissingGenomes(dbInfos):
    '''
    searches bio-mirror ensembl, ncbi genomes, Fungi, Bacteria, and Protozoa dirs for genomes not in our config file.
    prints a config for any missing genomes.
    this function is not perfect.  I would check one url at a time.  In particular, ncbi genomes url has funky names like H_sapiens which
    appear to be missing from our genomes but are not.
    Basically, grabs the dirs under the url, transforms them to genome names, checks if we have them, and if not makes a config for that dir.
    Some filtering and transforming is involved.
    '''
    ourGenomes = [update_dbs.getId(dbInfo) for dbInfo in dbInfos]

    def simpleGenomeFromDirFunc(d):
        return d + '.aa'
    def simpleBaseUrlFromGenomeUrlFunc(url):
        return url
    def ensemblGenomeFromDirFunc(d):
        return d.capitalize() + '.aa'
    def ensemblBaseUrlFromGenomeUrlFunc(url):
        return '/'.join([url, 'pep'])
    def trueFunc(*args, **keywords):
        return True
    def betterDirFilter(d):
        return d != 'CLUSTERS' and not d.startswith('uncultured') and d[0].isupper() and d.find('_') > -1

    def sub(ourGenomes, url, makeGenomeFromDirFunc, makeBaseUrlFromGenomeUrlFunc, pattern, dirFilterFunc=trueFunc):
        theirGenomes = {}
        for (url, dirs, files) in  update_dbs.genFTPDirsAndFiles(url, depth=0):
            for d in dirs:
                if dirFilterFunc(d):
                    theirGenomes[makeGenomeFromDirFunc(d)] = '/'.join([url, d])
        keys = theirGenomes.keys()
        keys.sort()
        for g in keys:
            if g not in ourGenomes:
                # print g, 'missing from our genomes'
                print makeRoundupConfig(g, makeBaseUrlFromGenomeUrlFunc(theirGenomes[g]), pattern)

    # HEY! You need to uncomment one of these sub() lines to make this function work.
    # b/c ncbigenomes dir contains badly named genome dirs, like H_sapiens and R_norvegicus, these need to be added by hand.
    # sub(ourGenomes, 'ftp://bio-mirror.net/biomirror/ncbigenomes', simpleGenomeFromDirFunc, simpleBaseUrlFromGenomeUrlFunc,
    #     '\.faa\.gz$', betterDirFilter)
    # assumption: all dirs under url are named Genus_species, so the genome name is Genus_species.aa
    # sub(ourGenomes, 'ftp://bio-mirror.net/biomirror/ncbigenomes/Fungi', simpleGenomeFromDirFunc, simpleBaseUrlFromGenomeUrlFunc, '\.faa\.gz$')
    # assumption: all dirs under url are named Genus_species, so the genome name is Genus_species.aa
    # sub(ourGenomes, 'ftp://bio-mirror.net/biomirror/ncbigenomes/Protozoa', simpleGenomeFromDirFunc, simpleBaseUrlFromGenomeUrlFunc, '\.faa\.gz$')
    # assumption: all dirs under url are named genus_species, so the genome name is Genus_species.aa
    # sub(ourGenomes, 'ftp://bio-mirror.net/biomirror/ensembl/current_fasta', ensemblGenomeFromDirFunc, ensemblBaseUrlFromGenomeUrlFunc, '.pep\.all\.fa\.gz$')
    # under the dir are genome dirs and CLUSTERS and uncultured*.  And genome dirs are like Genus_species
    # sub(ourGenomes, 'ftp://bio-mirror.net/biomirror/ncbigenomes/Bacteria', simpleGenomeFromDirFunc, simpleBaseUrlFromGenomeUrlFunc, '\.faa\.gz$', betterDirFilter)

    
def trueFunc(*args, **keywords):
    return True


def makeConfigsForEnsembleGenomes(url='ftp://ftp.ensembl.org/pub/current_fasta'):
    def ensemblGenomeFromDirFunc(d):
        return d.capitalize() + '.aa'
    def ensemblBaseUrlFromGenomeUrlFunc(base):
        return '/'.join([base, 'pep'])
    configs = findConfigs(url, ensemblGenomeFromDirFunc, ensemblBaseUrlFromGenomeUrlFunc, '.pep\.all\.fa\.gz$')
    return configs

    
def findConfigs(url, makeGenomeFromDirFunc, makeBaseUrlFromGenomeUrlFunc, pattern, dirFilterFunc=trueFunc):
    theirGenomes = {}
    for (url, dirs, files) in  update_dbs.genFTPDirsAndFiles(url, depth=0):
        for d in dirs:
            if dirFilterFunc(d):
                theirGenomes[makeGenomeFromDirFunc(d)] = '/'.join([url, d])
    keys = theirGenomes.keys()
    keys.sort()
    configs = []
    for g in keys:
        xml = makeRoundupConfig(g, makeBaseUrlFromGenomeUrlFunc(theirGenomes[g]), pattern)
        configs.append(xml)
    return configs

    
def makeRoundupConfig(genome, url, pattern):
    '''
    genome: e.g. Bifidobacterium_longum.aa
    url: e.g. ftp://bio-mirror.net/biomirror//ncbigenomes/Bacteria/Bifidobacterium_longum
    pattern: e.g. \.faa\.gz$
    used to create configs for newly detected genomes.
    returns: roundup xml config string
    '''
    return '''<db>
    <id>'''+genome+'''</id>
    <description></description>
    <format>fasta</format>
    <db_type>genome</db_type>
    <processing>gunzip,concat</processing>
    <label></label>
    <type>protein</type>
    <urls>
      <dir_pattern>
        <url>
        '''+url+'''
        </url>
        <pattern>
        '''+pattern+'''
        </pattern>
      </dir_pattern>
    </urls>
</db>'''

def oneOffGetNonStandardConfigHosts(dbInfos):
    '''
    delete this one-off function.
    prints hosts of urls in dbInfo that are not ncbi or biomirror or ensembl
    used to see what genomes are being downloaded from tigr, japan, stanford, etc.
    '''
    for dbInfo in dbInfos:
        dbId = update_dbs.getId(dbInfo)
        urls = [xml_util.getTextValue(urlNode) for urlNode in dbInfo.getElementsByTagName('url')]
        hosts = [urlparse.urlsplit(url)[1].split('@')[-1].split(':')[0] for url in urls]
        hosts = [h for h in hosts if h not in ['ftp.ncbi.nih.gov', 'bio-mirror.net', 'ftp.ensembl.org']]
        if hosts:            
            print dbId+'    '+str(hosts)

def oneOffGetInfosWithMatchingUrl(dbInfos, regex='ncbi'):
    for dbInfo in dbInfos:
        dbId = update_dbs.getId(dbInfo)
        urls = [xml_util.getTextValue(urlNode) for urlNode in dbInfo.getElementsByTagName('url')]
        for url in urls:
            if re.search(regex, url):
                yield dbInfo
                break


def oneOffGetConfigUrl(dbInfos):
    '''
    delete this one-off function.
    prints dbId and (attempts) to print the genome dir from the <url> elem in the config.
    used to check that the dbId corresponds to the genome and is not simplified, like Pseudomonas_syringae.aa <--> Pseudomonas_syringae_tomato_DC3000
    '''
    for dbInfo in dbInfos:
        dbId = update_dbs.getId(dbInfo)
        urls = [xml_util.getTextValue(urlNode) for urlNode in dbInfo.getElementsByTagName('url')]
        if urls:
            for url in urls:
                splits = url.split('/')
                splits = [s for s in splits if s.find('_') > -1]
            print dbId+'    '+'/'.join(splits)


def checkConfigs(dbConfigFiles, **keywords):
    '''
    check the urls of the configs for missing files.  (sometimes files are added over the years.)
    gets the urls of the config, calculates a "base" url, and searches for all possible protein urls located under the "base" url.
    the base url is guessed by grabbing the path that all the config urls have in common.  for some configs this will be too low
    in the dir tree.
    report if the possible urls and the config urls do not overlap perfectly.
    '''
    def sub(dbInfos):
        lines = []
        for dbInfo in dbInfos:
            import time
            time.sleep(5)
            lines += checkConfig(dbInfo)
        return  '\n'.join(lines) + '\n'
    return processConfigs(dbConfigFiles, sub, **keywords)



#########################
# MAIN DOWNLOAD FUNCTIONS
#########################


def processConfigs(dbConfigFiles, func, startIndex=0, endIndex=None, genomeIds=None, **keywords):
    '''
    func: a function that takes a list of dbInfos
    startIndex: begin downloading/updating databases starting here in the db list.  indices are zero indexed.  see printCount()
    endIndex: stop downloading dbs immediately before here in the list.  e.g. to process only the first config (config #0), endIndex=1.
    genomeIds: list of genome/db ids to process.  If None, process all.
    this meta function wraps the boiler-plate of reading dbConfigFiles and limiting them by the indices or genomeIds.
    runs func on the selected dbInfos in the dbConfigFiles.
    use either (startIndex and/or endIndex) or genomeIds.  Combining them is undefined.
    '''
    dbInfos = list(itertools.chain(*(database_update_common.parseConfig(file) for file in dbConfigFiles)))
    if genomeIds:
        dbInfos = [dbInfo for dbInfo in dbInfos if update_dbs.getId(dbInfo) in genomeIds]
        return func(dbInfos, **keywords)
    else:
        if endIndex == None:
            endIndex = len(dbInfos)
        return func(dbInfos[startIndex:endIndex], **keywords)


def printCount(dbConfigFiles):
    '''
    print out a table of index and database id, useful as a guide to figuring out which start and end indices to use.
    '''
    def sub(dbInfos):
        for i in xrange(len(dbInfos)):
            print i, update_dbs.getId(dbInfos[i])
    processConfigs(dbConfigFiles, sub)

    
def updateFromConfigs(dbConfigFiles, newOnly=False, **keywords):
    '''
    This is the function which downloads and updates genomes in the config file(s).
    dbConfigFiles: list of paths of xml config files, which are concatenated into a single list.
    newOnly: only attempt to update/download genomes for which we do not have a genome already.
    keywords: pass the startIndex and endIndex keywords to processConfigs()
    '''
    def sub(dbInfos):
        for dbInfo in dbInfos:
            import time
            time.sleep(10) # token courtesy pause.
            id = update_dbs.getId(dbInfo)
            currentDbPath = roundup_common.currentDbPath(id)
            updatedDbPath = roundup_common.updatedDbPath(id)
            if not newOnly or (not os.path.exists(currentDbPath) and not os.path.exists(updatedDbPath)):
                updateDb(dbInfo)
    processConfigs(dbConfigFiles, sub, **keywords)
    
    
if __name__ == '__main__':
    pass


# last line emacs bug fix
