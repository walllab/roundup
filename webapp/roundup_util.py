#!/usr/bin/env python

'''
acts as an interface between web code and other roundup code.
contain orchestra and roundup specific code.
'''

import os
import shutil
import re
import logging
import time
import json

import config
import cachedispatch
import lsfdispatch
import cacheutil
import execute
import orthresult
import roundup_common
import roundup_db
import roundup_dataset
import util


##########################
# USED BY ROUNDUP WEB PAGE
##########################


def getRawResults(params):
    '''
    params: a 4-tuple of roundup params like (qdb, sdb, div, evalue).
    returns: a string containing all the orthologs for the params. in the form external query sequence id, external subject sequence id, and distance
      or None if the results do not exist.
    '''
    qdb, sdb, div, evalue = params
    pair = roundup_common.makePair(qdb, sdb)
    # get orthologs from db
    orthologs = roundup_db.getOrthologs(qdb=pair[0], sdb=pair[1], divergence=div, evalue=evalue)
    # get a map to external sequence ids
    sequenceIds = set()
    for ortholog in orthologs:
        sequenceIds.add(ortholog[0])
        sequenceIds.add(ortholog[1])
    sequenceIds = list(sequenceIds)
    sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(sequenceIds)

    # format orthologs for download by mapping to external sequence ids.
    results = None
    if orthologs:
        results = ''.join(['{}\t{}\t{}\n'.format(sequenceIdToSequenceDataMap[qid][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                                 sequenceIdToSequenceDataMap[sid][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                                 dist) for qid, sid, dist in orthologs])
    return results
        

def getDatasetStats():
    return roundup_dataset.getDatasetStats(config.CURRENT_DATASET)
    

def getSourcesHtml(ds=config.CURRENT_DATASET):
    '''
    generate the sources page html div, and store it in the metadata.
    '''
    html = '''<div id="sources">
<p id="sources_desc">
Roundup Release {} uses the following sources:
<ul>
<li>
<a href="http://www.uniprot.org">UniProt</a>, specifically UniProtKB/Swiss-Prot and UniProtKB/TrEMBL from Release {}, is used as a source for protein sequences from complete genomes, for sequence annotations, and for genome annotations.
</li>
<li>
<a href="http://www.ncbi.nlm.nih.gov/taxonomy">The NCBI Taxonomy database</a> is used as a source for genome annotations.
</li>
<li>
<a href="http://geneontology.org/">Gene Ontology</a> is used for sequence annotations.
</li>
</ul>
</p>
<p id="source_urls">
The following is a comprehensive list of files that were downloaded for this Roundup release.  All sources are publicly available.
<ul>
'''.format(roundup_dataset.getReleaseName(ds), roundup_dataset.getUniprotRelease(ds))
    for url in roundup_dataset.getSourceUrls(ds):
        html += '<li><a href="{}">{}</a></li>\n'.format(url, url)
    html += '''
</ul>
</p>
</div>
'''
    return html


def getGenomesAndNames():
    '''
    return: list of pairs of genome and name.  used by website for dropdowns.  
    '''
    return roundup_db.getGenomesAndNames()


def getGenomeDescriptions():
    '''
    returns: a list of tuples with data describing each genome in roundup.
    '''
    genomesData = roundup_db.getGenomesData()
    return genomesData


#########
# CACHING
#########

#
# used to cache query results.
#

def cacheHasKey(key):
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn), table=config.CACHE_TABLE).has_key(key)


def cacheGet(key, default=None):
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn), table=config.CACHE_TABLE).get(key, default=default)


def cacheSet(key, value):
    '''
    value: serialized in the cache as json, so only strings as dict keys.
    '''
    return cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn), table=config.CACHE_TABLE).set(key, value)


def dropCreateCache():
    '''
    create a clean cache.  used when "refreshing" the roundup mysql database
    '''
    cache = cacheutil.Cache(manager=util.ClosingFactoryCM(config.openDbConn), table=config.CACHE_TABLE, drop=True, create=True)

    
def cacheDispatch(fullyQualifiedFuncName=None, keywords=None, cacheKey=None, outputPath=None):
    '''
    fullyQualifiedFuncName: required. function name including modules, etc., e.g. 'foo_package.gee_package.bar_module.baz_class.wiz_func'
    keywords: dict of keyword parameters passed to the function.  optional.  defaults to {}
    outputPath: required. function output is serialized and written to this file.
    cacheKey: required. outputPath is added to cache under this key.
    run function, saving its output in the file and caching the filename under the cache key in the roundup cache.
    returns: output of fullyQualifiedFuncName
    '''
    dispatcher = cachedispatch.Dispatcher(table=config.CACHE_TABLE, create=False, manager=util.ClosingFactoryCM(config.openDbConn))
    return dispatcher.dispatch(fullyQualifiedFuncName, keywords, cacheKey, outputPath)


def lsfDispatch(fullyQualifiedFuncName=None, keywords=None, jobName=None):
    '''
    fullyQualifiedFuncName: required. function name including modules, etc., e.g. 'foo_package.gee_package.bar_module.baz_class.wiz_func'
    keywords: dict of keyword parameters passed to the function.  optional.  defaults to {}
    outputPath: required. function output is serialized and written to this file.
    cacheKey: required. outputPath is added to cache under this key.
    jobName: optional.  submit the job to lsf with this name.
    returns: jobId of lsf job.
    '''
    lsfOptions = ['-N', '-q shared_2h']
    if jobName:
        lsfOptions.append('-J {}'.format(jobName))
    return lsfdispatch.dispatch(fullyQualifiedFuncName, keywords, lsfOptions)


def lsfAndCacheDispatch(fullyQualifiedFuncName=None, keywords=None, cacheKey=None, outputPath=None, jobName=None):
    '''
    run fullyQualifiedFuncName on lsf and cache its output.
    returns: jobId of lsf job.
    '''
    newFunc = 'roundup_util.cacheDispatch'
    newKw = {'fullyQualifiedFuncName': fullyQualifiedFuncName, 'keywords': keywords, 'cacheKey': cacheKey, 'outputPath': outputPath}
    return lsfDispatch(newFunc, newKw, jobName)


#################
# DEPRECATED CODE
#################

# last line python emacs semantic cache bug fix
