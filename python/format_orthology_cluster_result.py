#!/usr/bin/env python

import re
import string
import sys
import pickle #for hamming result stuff
import urllib
import os
import math
import StringIO
import logging

import config
import util
import nested
import logging
import execute
import roundup_common
import fasta
import BioUtilities

TERM_PROMISCUITY_LIMIT = 100
BEST_GENOMES_FOR_GENE_NAMES = ['Homo_sapiens.aa', 'Mus_musculus.aa', 'Drosophila_melanogaster.aa', 'Caenorhabditis_elegans.aa', 'Saccharomyces_cerevisiae.aa']


def resultExists(resultId):
    '''
    boolean function that returns True iff the results file exists for the result id.
    '''
    return os.path.exists(getResultFilenameFromId(resultId))


def getResult(resultId):
    '''
    returns a result object for a result id.
    '''
    if resultExists(resultId):
        return util.loadObject(getResultFilenameFromId(resultId))
    else:
        return None


def getResultFilenameFromId(resultId):
    '''
    returns: the filename of the results file for this result id.
    '''
    return nested.makeNestedPath(name='roundup_web_result_'+resultId)


def makeResultUrl(resultId, resultType='roundup_test_result', templateType='roundup_wide_template', jobId=None, count=0, otherUrlParams=None):
    '''
    otherUrlParams: a dict of url key value pairs.
    HACK: this function is an inexact duplicate of result_util.php function makeResultUrl().  If these functions get out of sync...
    '''
    url = '/roundup/result.php?result_id=%s&result_type=%s&template_type=%s&job_id=%s&count=%s'%(resultId, resultType, templateType, jobId, count)
    if otherUrlParams:
        url += '&'+urllib.urlencode(otherUrlParams)
    return url


def _clustersToPhyleticPattern(clusters):
    '''
    clusters: list of lists of lists of genes.  So each cell in the 2-d clusters array is a list of genes.
    returns: list of lists of ones and zeros.  Each cell contains a one if the list of genes was non-empty or zero if the list was empty.
    '''
    pattern = []
    for row in clusters:
        pattern.append([str(int(bool(genes))) for genes in row])
    return pattern


def _clusterResultToGenomesAndTransposedPhyleticPattern(result):
    '''
    result: result from running a ortholog_query cluster query.
    returns: tuple of list of genomes and phyletic pattern (where each row is a genome not a gene cluster)
    '''
    # make a list of human-readable genomes
    genomes = result['headers'][:-1] # last header is Distance
    genomes = [g.strip() for g in genomes]
    genomes = [re.sub('\.aa', '', g) for g in genomes]
    # transpose clusters
    clusters = result['rows'] # each row is a gene cluster, each column is a genome (except the last column, which is avg cluster distances).
    genomeClusters =  zip(*clusters)[:-1] # each row a genome, each col a gene, after removing last row containing avg cluster distances
    # make phyletic pattern
    pattern = _clustersToPhyleticPattern(genomeClusters)
    return (genomes, pattern)

	
def clusterResultToNexus(resultId):
    '''
    result: result from running a ortholog_query cluster query.
    returns: gene clusters in nexus format
    '''
    result = getResult(resultId)
    genomes, pattern = _clusterResultToGenomesAndTransposedPhyleticPattern(result)
    numClusters = len(result['rows'])
    
    # matrix
    matrix = ''
    for genome, genomePattern in zip(genomes, pattern):
        matrix += '\t'.join([genome]+genomePattern) + '\n'

    nexusMatrix = "#Nexus\nbegin data;\ndimensions\nntax = %s\nnchar = %s;\nformat symbols = \"01\";\nmatrix\n"%(len(genomes), numClusters) + matrix +";End;\n"
    return nexusMatrix


def clusterResultToPhylip(resultId):
    '''
    result: result from running a ortholog_query cluster query.
    returns: gene clusters in nexus format
    '''
    result = getResult(resultId)
    genomes, pattern = _clusterResultToGenomesAndTransposedPhyleticPattern(result)
    numClusters = len(result['rows'])
    
    phylip = '%s %s\n' % (len(genomes), numClusters)
    for genome, genomePattern in zip(genomes, pattern):
        phylip += '%-10s %s\n' % (genome[:10], ' '.join(genomePattern))
        
    return phylip


def clusterResultToPhylogeneticProfile(resultId):
    result = getResult(resultId)
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})
    
    profile = ''
    headers = result['headers']
    newHeaders = headers[:-1]
    newHeaders.append('Cluster Info')
    profile += '\t'.join(newHeaders) + '\n'
    
    if result['type'] == 'clusters':
        for row in result['rows']:
            arr = []
            for seqIds in row[:-1]:
                if seqIds:
                    arr.append('1')
                else:
                    arr.append('0')
            clusterInfo = ['', '', '']
            for seqIds in row:
                for seqId in seqIds:
                    newClusterInfo = makePhyleticClusterInfo(seqId, seqIdToDataMap, termMap)
                    clusterInfo = chooseBetterPhyleticClusterInfo(clusterInfo, newClusterInfo)
            arr.append(','.join(clusterInfo))
            profile += '\t'.join(arr) + '\n'
    return profile


def clusterResultToPhylogeneticProfileWithoutCaching(resultDict):
    '''This is a revised version of clusterResultToPhylogeneticProfile()
    The result dictionary is passed to this method w/o the caching step.
    Purpose of this revision is to get the PhylogeneticProfile w/o going
    through the web. This revision is added by Jike Cui'''
    result = resultDict
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})

    profile = ''
    headers = result['headers']
    newHeaders = headers[:-1]
    newHeaders.append('Cluster Info')
    profile += '\t'.join(newHeaders) + '\n'

    if result['type'] == 'clusters':
        for row in result['rows']:
            arr = []
            for seqIds in row[:-1]:
                if seqIds:
                    arr.append('1')
                else:
                    arr.append('0')
            clusterInfo = ['', '', '']
            for seqIds in row:
                for seqId in seqIds:
                    newClusterInfo = makePhyleticClusterInfo(seqId, seqIdToDataMap, termMap)
                    clusterInfo = chooseBetterPhyleticClusterInfo(clusterInfo, newClusterInfo)
            arr.append(','.join(clusterInfo))
            profile += '\t'.join(arr) + '\n'
    return profile



def clusterResultToPhylogeneticProfileWithoutCaching_wGiID(resultDict):
    '''
    Added all the giids of all the orthologs in that row to clusterInfo. 
    '''
    result = resultDict
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})

    profile = ''
    headers = result['headers']
    newHeaders = headers[:-1]
    newHeaders.append('Cluster Info')
    profile += '\t'.join(newHeaders) + '\n'

    if result['type'] == 'clusters':
        for row in result['rows']:
            giids=[]       #added by Jike
            arr = []
            for seqIds in row[:-1]:
                if seqIds:
                    arr.append('1')
                else:
                    arr.append('0')
            clusterInfo = ['', '', '']
            for seqIds in row:
                for seqId in seqIds:
                    newClusterInfo = makePhyleticClusterInfo(seqId, seqIdToDataMap, termMap)
                    if len(newClusterInfo[0])>0: giids.append(newClusterInfo[0])
		    clusterInfo = chooseBetterPhyleticClusterInfo(clusterInfo, newClusterInfo)
            giidsStr=','.join(giids)
            clusterInfo.append(giidsStr)
            arr.append('|'.join(clusterInfo))
            profile += '\t'.join(arr) + '\n'
    return profile


def clusterResultToPhylogeneticProfileWithoutCaching_wGiID_3(resultDict, ofileName,column1only):
    '''
    column1only: ClusterInfo only contain info of the 1st column
    otherwise Added all the giids of all the orthologs in that row to clusterInfo.
    write profile directly to a file    
    '''
    result = resultDict
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})

    headers = result['headers']
    newHeaders = headers[:-1]
    newHeaders.append('Cluster Info')

    ofile=open(ofileName,'w')  ##
    ofile.write('\t'.join(newHeaders) + '\n')

    if result['type'] == 'clusters':
        for row in result['rows']:
            giids=[]       #added by Jike
            arr = []
            for seqIds in row[:-1]:
                if seqIds:
                    arr.append('1')
                else:
                    arr.append('0')
            clusterInfo = ['', '', '']
            for seqIds in row[:-1]:
                for seqId in seqIds:
                    newClusterInfo = makePhyleticClusterInfo(seqId, seqIdToDataMap, termMap)
                    if len(newClusterInfo[0])>0: giids.append(newClusterInfo[0])
                    clusterInfo = chooseBetterPhyleticClusterInfo(clusterInfo, newClusterInfo)
                if column1only: break  #stop searching other columns
            giidsStr=','.join(giids)
            clusterInfo.append(giidsStr)
            arr.append('|'.join(clusterInfo))
            ofile.write('\t'.join(arr) + '\n')

    ofile.close()

def clusterResultToPhylogeneticProfileWithoutCaching_wGiID_3_newClustering(resultDict, ofileName, column1only):
    '''
    column1only: ClusterInfo only contain info of the 1st column
    otherwise Added all the giids of all the orthologs in that row to clusterInfo.
    write profile directly to a file    
    Use new clustering algorithm where each cluster contains one seed that others are compared to.
    New clustering is in orthology_query.doOrthologyQuery3
    '''
    result = resultDict
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})

    headers = result['headers']
    newHeaders = headers[:-1]
    newHeaders.append('Cluster Info')

    ofile=open(ofileName,'w')  ##
    ofile.write('\t'.join(newHeaders) + '\n')

    if result['type'] == 'clusters':
        for row in result['rows']:
            giids=[]       #added by Jike
            arr = []
            for seqIds in row: #removed[:-1] for orthology_query.doOrthologyQuery3
                if seqIds:
                    arr.append('1')
                else:
                    arr.append('0')
            clusterInfo = ['', '', '']
            for seqIds in row: #removed[:-1] for orthology_query.doOrthologyQuery3
                for seqId in seqIds:
                    newClusterInfo = makePhyleticClusterInfo(seqId, seqIdToDataMap, termMap)
                    if len(newClusterInfo[0])>0: giids.append(newClusterInfo[0])
                    clusterInfo = chooseBetterPhyleticClusterInfo(clusterInfo, newClusterInfo)
                if column1only: break  #stop searching other columns
            giidsStr=','.join(giids)
            clusterInfo.append(giidsStr)
            arr.append('|'.join(clusterInfo))
            ofile.write('\t'.join(arr) + '\n')

    ofile.close()



def clusterResultToPhylogeneticProfileWithoutCaching_wGoAcc(resultDict):
    '''
    Added Go Acc to clusterInfo. It includes all the Go Accs present
    in the row of the profile, i.e., the go accs of all the orthologs
    in that row of phylogenetic profile
    '''
    result = resultDict
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})

    profile = ''
    headers = result['headers']
    newHeaders = headers[:-1]
    newHeaders.append('Cluster Info')
    profile += '\t'.join(newHeaders) + '\n'

    if result['type'] == 'clusters':
        for row in result['rows']:
            allGoAccs=set() #added by Jike
            goAccs=[]       #added by Jike
            arr = []
            for seqIds in row[:-1]:
                if seqIds:
                    arr.append('1')
                else:
                    arr.append('0')
            clusterInfo = ['', '', '']
            for seqIds in row:
                for seqId in seqIds:
                    newClusterInfo,goAccs = makePhyleticClusterInfoWithGoAcc(seqId, seqIdToDataMap, termMap)
                    clusterInfo = chooseBetterPhyleticClusterInfo(clusterInfo, newClusterInfo)
                    if len(goAccs)>0:   #added by Jike
                        allGoAccs=allGoAccs | set(goAccs)  #added by Jike
            allGoAccStr=','.join(allGoAccs)
	    clusterInfo.append(allGoAccStr)
	    arr.append('|'.join(clusterInfo))
	    profile += '\t'.join(arr) + '\n'
    return profile



def makePhyleticClusterInfoWithGoAcc(seqId, seqIdToDataMap, termMap):
    '''
    returned Go Acc with clusetrInfo. Added by Jike
    '''
    data = seqIdToDataMap.get(seqId, {})
    acc = data.get(roundup_common.EXTERNAL_SEQUENCE_ID_KEY, '')
    geneName = data.get(roundup_common.GENE_NAME_KEY, '')
    terms = data.get(roundup_common.TERMS_KEY, [])
    termName = ''
    if terms:
        termName = termMap.get(terms[0], '')
    if acc is None:
        acc = ''
    if geneName is None:
        geneName = ''
    if termName is None:
        termName = ''
    info = [acc, geneName, termName]
    return info,terms



def clusterResultToHammingProfile(resultId):
    '''
    This is the magic function that will produce data more informatively.
    '''
    result = getResult(resultId)
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})
    
    hammingSource = ''
    headers = result['headers']
    newHeaders = headers[:-1]
    newHeaders.append('Cluster Info')
    hammingSource += '\t'.join(newHeaders) + '\n'
    	
    if result['type'] == 'clusters':
        # row has an element for each genome that contains 0 or more seq ids, and row has the distance of the cluster as its final element.
        for row in result['rows']:
            # transform presence or absence of seqIds into 1 or 0.
            phyleticPattern = [int(bool(seqIds)) for seqIds in row[:-1]]
            arr = []
            for seqIds in row[:-1]:
                if seqIds:
                    arr.append('1')
                else:
                    arr.append('0')
            clusterInfo = ['', '', '']
            for seqIds in row:
                for seqId in seqIds:
                    newClusterInfo = makePhyleticClusterInfo(seqId, seqIdToDataMap, termMap)
                    clusterInfo = chooseBetterPhyleticClusterInfo(clusterInfo, newClusterInfo)
            arr.append(','.join(clusterInfo))
            hammingSource += '\t'.join(arr) + '\n'

    hammingResult = {}
    #converted hammingSource into a list broken on \n
    hsNew = string.split(hammingSource, '\n')
    for line in hsNew[1:]:
        pp_strip = string.split(line, '\t')
        pp = pp_strip[:-1]
        pp = string.join(pp)
        pp_name = pp_strip[-1]
        # keep a count of each phyletic pattern and the cluster infos.
        if not hammingResult.has_key(pp):
            hammingResult[pp]=[1,[pp_name]]
        else:
            hammingResult[pp][0]+=1
            hammingResult[pp][1].append(pp_name)
            
    testString = ''
    testString+= "<p>your search returned %s unique phylogenetic profiles</p>"%len(hammingResult.keys())
    testString+= "<p>here they are you lovely evolutionary biologist</p>"
    for k in hammingResult.keys():
        testString += "<p>%s\t%s</p>"%(k,hammingResult[k][0]) 
    hamming = str(hammingResult)
    return testString


def getBestClusterGeneName(cluster, headers, seqIdToDataMap):
    '''
    headers: list of genome ids +'Average Distance', corresponding to the elements of cluster
    cluster: list of lists of sequence ids + the average distance of the cluster.
    returns: gene name of a sequence in cluster, looking first in bestGenomes and then anywhere in cluster.  returns None if no gene name found.
    '''
    # search for a gene name among (and in order of) the best genomes first.
    for genome in BEST_GENOMES_FOR_GENE_NAMES:
        if genome in headers:
            for seqId in cluster[headers.index(genome)]:
                seqName = seqIdToDataMap.get(seqId, {}).get(roundup_common.GENE_NAME_KEY)
                if seqName:
                    return seqName
    # search for any gene name
    for seqIds in cluster[:-1]:
        for seqId in seqIds:
            seqName = seqIdToDataMap.get(seqId, {}).get(roundup_common.GENE_NAME_KEY)
            if seqName:
                return seqName
    return None

def hammingDistanceForProfiles(profile1, profile2):
    '''
    profile1: a list of 1s and 0s representing presence or absence of a gene in a species.
    profile2: same length as profile1
    returns: number of places where profile1 differs from profile 2.
    '''
    return sum([1 for i in range(len(profile1)) if profile1[i] != profile2[i]])


def getProfileForCluster(cluster):
    '''
    cluster: row of orthology result.  row has an element for each genome that contains 0 or more seq ids,
    and row has the distance of the cluster as its final element.
    returns: list of 0s and 1s denoting absence of presence of sequences from each genome in the cluster. 
    '''
    return [int(bool(seqIds)) for seqIds in cluster[:-1]]


def resultToTermsSummary(resultId):
    '''
    produces html content summarizing the data for each GO term.
    '''
    result = getResult(resultId)
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})
    clusterIndexToProfileMap = {}
    clusterIndexToBestGeneNameMap = {}
    termToClusterIndicesMap = {}
    headers = result['headers']
    
    for index in range(len(result['rows'])):
        # row has an element for each genome that contains 0 or more seq ids, and row has the distance of the cluster as its final element.
        row = result['rows'][index]
        clusterIndexToProfileMap[index] = getProfileForCluster(row)
        clusterIndexToBestGeneNameMap[index] = getBestClusterGeneName(row, headers, seqIdToDataMap)
        clusterTerms = getTermsForCluster(row, seqIdToDataMap)
        for term in clusterTerms:
            termToClusterIndicesMap.setdefault(term, []).append(index)

    termIds = termToClusterIndicesMap.keys()
    termIds.sort()

    # make list of distance, etc., info for each term.
    termDataList = []
    for termId in termIds:
        clusterIndices = termToClusterIndicesMap[termId]
        numClusters = len(clusterIndices)
        meanPairwiseHammingDistance = computeMeanPairwiseHammingDistance(result, clusterIndices, clusterIndexToProfileMap)
        # ignore terms associated with many clusters on the assumption that they are too general to be interesting.
        if meanPairwiseHammingDistance is None:
            continue
        termDataList.append((meanPairwiseHammingDistance, numClusters, termId))
    termDataList.sort()
    termResultUrl = makeResultUrl(resultId, resultType='roundup_term_result', templateType='roundup_wide_template')
    content = ''
    content += makeQueryDescHtml(result)
    content += '<h3>Result Description</h3>'
    content += '<pre>A list of Gene Ontology terms associated with genes in the search result.\n'
    content += 'Also reported:\n'
    content += '\tMean hamming distance between the phyletic profiles of each pair of gene clusters annotated with the GO term.\n'
    content += '\tNumber of gene clusters annotated with the GO term.\n'
    content += 'For GO terms with only one associated gene cluster, the mean pairwise hamming distance is defined as 0.\n'
    content += 'GO terms associated with more than '+str(TERM_PROMISCUITY_LIMIT)+' gene clusters are excluded as being too general to be interesting.\n'
    content += 'Click on table column headers to sort by that column.  Please be patient with large data sets.\n'
    content += '</pre>'
    content += '<h3>Result</h3>'
    content += '<table class="sortable" id="term_summary_table">'
    content += '<tr><th>GO&nbsp;Identifier</th><th>GO Term</th><th>Mean Pairwise Gene Hamming Distance</th><th>Number of Genes</th></tr>\n'
    for t in termDataList:
        content += '<tr><td><a href="%s">%s</a></td><td>%s</td><td>%.2f</td><td>%d</td></tr>\n'%(termResultUrl+'&term='+urllib.quote_plus(t[2]), t[2], termMap[t[2]], t[0], t[1])
    content += '</table>'
    return content


def roundupGenomeDisplayName(genome):
    '''
    Turn a genome id into something more human-readable.  E.g. Homo_sapiens.aa -> Homo sapiens
    '''
    if genome.endswith('.aa'):
        return genome[:-3].replace('_', ' ')
    else:
        return genome.replace('_', ' ')

    
def makeSeqIdLink(id):
    '''
    creates a link for NCBI and Ensembl identifiers to the corresponding page at NCBI or Ensembl.
    '''
    if isGINumber(id):
        idLink = "<a href=\"http://www.ncbi.nlm.nih.gov/entrez/viewer.fcgi?db=protein&val=%s\">%s</a>"%(id, id)
    elif isEnsemblId(id):
        idLink = "<a href=\"http://www.ensembl.org/common/psychic?site=&species=&q=%s\">%s</a>"%(id, id)
    else:
        idLink = id
    return idLink


def isEnsemblId(seqId):
    ''' heuristic for guessing if an id is from ensembl.'''
    return seqId.startswith('ENS') or seqId.startswith('NEWSIN') or seqId.startswith('GS')


def isGINumber(seqId):
    ''' heuristic for guessing if an id is from NCBI.'''
    return re.search('^\d+$', seqId)


def makeQueryDescHtml(result):
    ''' creates html describing the search that was run to produce this result. '''
    return '<h3>Search Description</h3>\n<pre>'+str(result.get('query_desc'))+'</pre>\n'
                                                    

def clusterResultToTest(resultId, otherParams):
    ''' Dummy function, used for testing new functionality. '''
    pass


def resultToGenesSummaryView(resultId):
    '''
    make a sortable table summarizing each cluster/gene/row.
    '''
    result = getResult(resultId)
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})
    headers = result['headers']
    rows = result['rows']

    # for each row, display cluster#, bestclustergenename, avgDist, numTerms, genome1, genome2, genome3, ...
    
    content = ''
    content += makeQueryDescHtml(result)
    content += '<h3>Result Description</h3>'
    content += '<a><p>Below is a sortable table displaying a summary of each gene cluster containing:</p></a>'
    content += '   (1) The id of the gene cluster in the result, '
    content += '   (2) A selected gene name, chosen from the gene names of the orthologous sequences of the gene cluster. '
    content += '(3) Gene names from '+', '.join([roundupGenomeDisplayName(g) for g in BEST_GENOMES_FOR_GENE_NAMES])+' are prioritized, if available.\n'
    content += '\t(4) The number of GO terms associated with the gene.\n'
    content += '\t(5) The phyletic pattern, the pattern of absence and presence of sequences from each genome.\n'
    content += '(6) And for each genome, the sequence identifiers for the orthologous sequences of the gene cluster. \n<p></p>'
    content += 'Click on table column headers to sort by that column.  Please be patient with large data sets.\n'
    content += '</p>'
    content += '<h3>Result</h3>'
    content += '<table class="sortable" id="term_summary_table">'
    content += '<tr><th>Gene Cluster #</th><th>Selected Gene Name</th><th>'+headers[-1]+'</th><th>Number of GO Terms</th><th>Phyletic Profile</th>'
    content += ''.join(['<th>'+roundupGenomeDisplayName(g)+'</th>' for g in headers[:-1]]) + '</tr>\n'
    geneResultUrl = makeResultUrl(resultId, resultType='roundup_gene_result', templateType='roundup_wide_template')
    for i in range(len(rows)):
        row = rows[i]
        clusterTerms = getTermsForCluster(row, seqIdToDataMap)
        phyleticProfile = getProfileForCluster(row)
        numTerms = len(clusterTerms)
        avgDist = row[-1]
        geneName = getBestClusterGeneName(row, headers, seqIdToDataMap)
        content += '<tr><td><a href="%s">%s</a></td>'%(geneResultUrl+'&gene_index='+urllib.quote_plus(str(i)), i+1)
        content += '<td>%s</td><td>%s</td><td>%d</td><td>%s</td>'%(geneName, avgDist, numTerms, ''.join([str(p) for p in phyleticProfile]))
        content += ''.join(['<td>'+', '.join([str(seqIdToDataMap.get(seqId,{}).get(roundup_common.EXTERNAL_SEQUENCE_ID_KEY)) for seqId in seqIds])+'</td>' for seqIds in row[:-1]]) + '</tr>\n'
    content += '</table>'
    return content


def resultToAllGenesView(resultId, otherParams):
    # this fixes a bug, where an empty php array is deserialized as a list, not a dict.  In this context it should be a dict.
    if not otherParams:
        otherParams = {}
        
    result = getResult(resultId)  
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})
    clusterIndexToProfileMap = {}
    clusterIndexToBestGeneNameMap = {}
    termToClusterIndicesMap = {}
    headers = result['headers']

    numRows = len(result['rows'])
    numCols = len(result['headers'])

    # PAGING
    # get the number of items per page.  see below for default
    # if pageSize < 1 or > numRows, display every item on one page.
    try:
        pageSize = int(str(otherParams.get('page_size')))
    except ValueError:
        pageSize = 100
    if pageSize < 1:
        pageSize = numRows+1 # show all
    elif pageSize > numRows:
        pageSize = numRows+1
    # total number of pages
    numPages = int(math.ceil(numRows/float(pageSize)))
    if numPages == 0:
        numPages = 1
    # get the page number to display.  default to 1.  min == 1, max == numPages.
    try:
        pageNum = int(str(otherParams.get('page_num')))
    except ValueError:
        pageNum = 1
    if pageNum < 1:
        pageNum = 1
    elif pageNum > numPages:
        pageNum = numPages

    pagingResultUrl = makeResultUrl(resultId, resultType='roundup_orthology_result', templateType='roundup_wide_template')
    def pagingControls(resultUrl):
        pagingCode = '<form action="' + resultUrl + '" method="post">'
        pagingCode += "<table class=\"paging_table\"><tr>\n"
        if pageNum > 1:
            pagingCode += '<td class="left"><a href="' + resultUrl + '&page_num='+str(pageNum-1)+'&page_size='+str(pageSize)+'">&lt;&lt;&lt;</a></td>'
        else:
            pagingCode += '<td class="left"> &lt;&lt;&lt;</td>'
        pagingCode += '<td>Page <input type="text" size="3" name="page_num" value="'+str(pageNum)+'"/> of '+str(numPages)+' pages.'
        pagingCode += '<input type="text" size="3" name="page_size" value="' + str(pageSize) + '"/> items per page.'
        pagingCode += str(numRows) + ' total items. <input type="submit" value="Show Page" /></td>'
        if pageNum < numPages:
            pagingCode += '<td class="right"><a href="' + resultUrl + '&page_num='+str(pageNum+1)+'&page_size='+str(pageSize)+'">&gt;&gt;&gt;</a></td>'
        else:
            pagingCode += '<td class="right">&gt;&gt;&gt;</td>'
        pagingCode += '</tr></table></form> '
        return pagingCode
                        
    content = ''
    content += "<div class=\"title\">Roundup Orthology Database Search Result</div>\n"
    content += makeQueryDescHtml(result)
    if numRows == 0:
        content += "<div>No gene clusters matched your search.</div>\n"
    elif numRows == 1:
        content += "<div>1 gene cluster matched your search.</div>\n"
    else:
        content += "<div>%s gene clusters matched your search.</div>\n"%numRows

    if numRows > 0:
        content += "<div>View result as: "
        content += "<a href=\"" + makeResultUrl(resultId, 'roundup_gene_summary_result', 'roundup_wide_template') + "\">Gene Clusters Summary</a>\n"
        content += ", <a href=\"" + makeResultUrl(resultId, 'roundup_terms_summary_result', 'roundup_wide_template') + "\">GO Terms Summary</a>\n"
        # content += ", <a href=\"" + makeResultUrl(resultId, 'roundup_hamming_distance_result', 'roundup_wide_template') + "\">phyletic profile and hamming distances<b><i>(new and experimental)</i></b></a>\n"
        content += "</div>"
        content += "<div>Download result as: "
        content += "<a href=\"" + makeResultUrl(resultId, 'roundup_text_result', 'text_download_template') + "\">Text</a>, \n"
        content += "<a href=\"" + makeResultUrl(resultId, 'roundup_phyletic_pattern_result', 'xls_download_template') + "\">Phylogenetic Profile Matrix</a>, \n"
        content += "<a href=\"" + makeResultUrl(resultId, 'roundup_phylip_matrix_result', 'xls_download_template') + "\">PHYLIP-formatted Matrix</a>, or \n"
        content += "<a href=\"" + makeResultUrl(resultId, 'roundup_nexus_matrix_result', 'xls_download_template') + "\">NEXUS-formatted Matrix</a>\n"
        content += "</div>"

        content += pagingControls(pagingResultUrl)
        content += makeSequenceClustersTable(result, resultId, startIndex=(pageNum-1)*pageSize, endIndex=pageNum*pageSize)
        content += pagingControls(pagingResultUrl)

    return content

    
# def resultToTermsView(resultId, otherParams):
#     '''
#     dispatches to single term view, terms summary view, or gene view.
#     '''
#     termParam = otherParams.get('term')
#     geneIndex = otherParams.get('gene_index')
#     if termParam is not None:
#         return resultToSingleTermView(resultId, otherParams)
#     elif geneIndex is not None:
#         return resultToGeneView(resultId, otherParams)
#     else:
#         return resultToTermsSummary(resultId)


def getTermsForCluster(cluster, seqIdToDataMap):
    '''
    return a set of terms associated with the cluster/gene
    '''
    clusterTerms = set()
    for seqIds in cluster[:-1]:
        for seqId in seqIds:
            for term in seqIdToDataMap.get(seqId, {}).get(roundup_common.TERMS_KEY, []):
                clusterTerms.add(term)
    return clusterTerms


def computeMeanPairwiseHammingDistance(result, clusterIndices, clusterIndexToProfileMap=None):
    '''
    clusterIndices: list of indices for which pairs are created.
    clusterIndexToProfileMap: a map from cluster index to precomputed cluster profiles.
    if there are more clusterIndices than the TERM_PROMISCUITY_LIMIT, return None.
    if there is only one cluster index, return 0.
    otherwise, return the mean of the hamming distances of every pair of clusterIndices.  n choose 2 pairs.
    '''
    numClusters = len(clusterIndices)
    # ignore terms associated with many clusters on the assumption that they are too general to be interesting.
    if numClusters > TERM_PROMISCUITY_LIMIT:
        return None
    numPairs = 0
    totalHammingDistance = 0
    for indexPair in util.choose(clusterIndices, 2):
        numPairs += 1
        # hamming distance is the number of differences in two equal length bit strings.
        if clusterIndexToProfileMap:
            profile0 = clusterIndexToProfileMap[indexPair[0]]
            profile1 = clusterIndexToProfileMap[indexPair[1]]
        else:
            profile0 = getProfileForCluster(result['rows'][indexPair[0]])
            profile1 = getProfileForCluster(result['rows'][indexPair[1]])
        totalHammingDistance += hammingDistanceForProfiles(profile0, profile1)
    if numPairs > 0:
        meanPairwiseHammingDistance = totalHammingDistance / float(numPairs)
    else:
        meanPairwiseHammingDistance = 0
    return meanPairwiseHammingDistance

    
def resultToGeneView(resultId, otherParams):
    '''
    geneIndex: index of gene/cluster row in result to view.
    for the cluster, get its terms, then get all the clusters associated with those terms and compute the pairwise profile distance of those terms.
    also compute the mean distance of the cluster and every other cluster in each term.
    report each term in the cluster, the mean pairwise hamming distance and the mean distance between cluster and every other cluster of the term.
    '''
    result = getResult(resultId)
    geneIndex = otherParams.get('gene_index')
    if not util.isInteger(geneIndex):
        raise Exception('format_orthology_cluster_result.resultToGeneView(): geneIndex is not an integer. geneIndex=%s'%geneIndex)
    geneIndex = int(geneIndex)
    selectedRow = result['rows'][geneIndex]
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})
    clusterIndexToProfileMap = {}
    clusterIndexToBestGeneNameMap = {}
    termToClusterIndicesMap = {}
    headers = result['headers']
    genomes = headers[:-1]
    genomeIdToGenomeMap = result.get('genome_id_to_genome_map', {})
    orthologs = result['orthologs'][geneIndex] # orthologs is a list of lists of orthologs for each row.
    
    # get terms to clusters map, etc.
    for index in range(len(result['rows'])):
        # row has an element for each genome that contains 0 or more seq ids, and row has the distance of the cluster as its final element.
        row = result['rows'][index]
        clusterIndexToProfileMap[index] = getProfileForCluster(row)
        clusterIndexToBestGeneNameMap[index] = getBestClusterGeneName(row, headers, seqIdToDataMap)
        clusterTerms = getTermsForCluster(row, seqIdToDataMap)
        for term in clusterTerms:
            termToClusterIndicesMap.setdefault(term, []).append(index)
    # get terms for geneIndex cluster.
    geneTerms = getTermsForCluster(selectedRow, seqIdToDataMap)

    # generate list of mean distance information for each term.
    termDataList = []
    for termId in geneTerms:
        clusterIndices = termToClusterIndicesMap[termId]
        numClusters = len(clusterIndices)
        meanPairwiseHammingDistance = computeMeanPairwiseHammingDistance(result, clusterIndices, clusterIndexToProfileMap)
        # ignore terms associated with many clusters on the assumption that they are too general to be interesting.
        if meanPairwiseHammingDistance is None:
            continue
        totalHammingDistanceFromGene = 0
        num = 0
        for index in clusterIndices:
            num += 1
            if index != geneIndex:
                totalHammingDistanceFromGene += hammingDistanceForProfiles(clusterIndexToProfileMap[index], clusterIndexToProfileMap[geneIndex])
        if num > 1:
            meanHammingDistanceFromGene = totalHammingDistanceFromGene / float(num)
        else:
            meanHammingDistanceFromGene = 0            
        termDataList.append((meanHammingDistanceFromGene, meanPairwiseHammingDistance, numClusters, termId))
    termDataList.sort()

    termResultUrl = makeResultUrl(resultId, resultType='roundup_term_result', templateType='roundup_wide_template')
    content = ''
    content += makeQueryDescHtml(result)
    content += '<h3>Result Description</h3>'
    content += '<pre>A table displays the orthologous sequences, '+headers[-1]+', and Phyletic Profile for the selected gene cluster.\n'
    content += 'Another table lists all the Gene Ontology terms associated with the selected gene.\n'
    content += 'That sortable table includes the following columns:\n'
    content += '\tThe mean hamming distance between the profile of the selected gene cluster and each profile of the other gene clusters in the result annotated with the GO term\n'
    content += '\tThe mean hamming distance between each pair of profiles of all gene clusters in the result annotated with the GO term\n'
    content += '\tNumber of gene clusters in the result annotated with each GO term.\n'
    content += 'For GO terms with only one associated gene cluster, the mean pairwise hamming distance is defined as 0.\n'
    content += 'GO terms associated with more than '+str(TERM_PROMISCUITY_LIMIT)+' gene clusters are excluded as being too general to be interesting.\n'
    content += 'Click on table column headers to sort by that column.  Please be patient with large data sets.\n'
    content += '</pre>'
    content += '<h3>Result</h3>'
    content += '<h4>Gene Cluster Information</h4>'
    content += makeSequenceClustersTable(result, resultId, clusterIndices=[geneIndex])
    content += '<h4>GO Term Information</h4>'
    content += '<table class="sortable" id="term_summary_table">'
    content += '<tr><th>GO&nbsp;Identifier</th><th>GO Term</th><th>Mean Gene Hamming Distance From Selected Gene</th>'
    content += '<th>Mean Pairwise Gene Hamming Distance</th><th>Number of Genes</th></tr>\n'
    for t in termDataList:
        content += '<tr><td><a href="%s">%s</a></td><td>%s</td>'%(termResultUrl+'&term='+urllib.quote_plus(t[3]), t[3], termMap[t[3]])
        content += '<td>%.2f</td><td>%.2f</td><td>%d</td></tr>\n'%(t[0], t[1], t[2])
    content += '</table>'
    content += '<h4>FASTA Sequence Information</h4>'
    content += '<ul>'
    for i in range(len(genomes)):
        genome = genomes[i]
        content += '<li>'+roundupGenomeDisplayName(genome)+'<br/><pre>'
        for seqId in selectedRow[i]:
            try:
                fastaPath = roundup_common.fastaFileForDbPath(roundup_common.makeDbPath(genome))
                content += BioUtilities.getFastaForId(seqIdToDataMap.get(seqId, {}).get(roundup_common.EXTERNAL_SEQUENCE_ID_KEY), fastaPath)
            except:
                logging.exception('Error. genome=%s, seqId=%s'%(genome, seqId))
                content += 'Failed to get FASTA for sequence %s\n'%(seqIdToDataMap.get(seqId, {}).get(roundup_common.EXTERNAL_SEQUENCE_ID_KEY))
        content += '</pre>'
    content += '</ul>'
    content += '<h4>Gene Cluster Orthologs</h4>'
    content += '<table class="sortable" id="ortholog_table">'
    content += '<tr><th>Sequence 1</th><th>Genome 1</th><th>Sequence 2</th><th>Genome 2</th><th>Evolutionary Distance</th></tr>\n'
    for (seqId1, seqId2, distance) in orthologs:
        acc1 = seqIdToDataMap.get(seqId1, {}).get(roundup_common.EXTERNAL_SEQUENCE_ID_KEY)
        genome1 = genomeIdToGenomeMap.get(seqIdToDataMap.get(seqId1, {}).get(roundup_common.GENOME_ID_KEY))
        acc2 = seqIdToDataMap.get(seqId2, {}).get(roundup_common.EXTERNAL_SEQUENCE_ID_KEY)
        genome2 = genomeIdToGenomeMap.get(seqIdToDataMap.get(seqId2, {}).get(roundup_common.GENOME_ID_KEY))
        content += '<tr><td>%s</td><td>%s</td>'%(acc1, roundupGenomeDisplayName(genome1))
        content += '<td>%s</td><td>%s</td>'%(acc2, roundupGenomeDisplayName(genome2))
        content += '<td>%.3f</td></tr>'%distance
    content += '</table>'
    return content


def resultToSingleTermView(resultId, otherParams):
    result = getResult(resultId)
    termParam = otherParams.get('term')
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})
    clusterIndexToProfileMap = {}
    clusterIndexToBestGeneNameMap = {}
    termToClusterIndicesMap = {}
    headers = result['headers']

    # only get clusters associated with termParam
    for index in range(len(result['rows'])):
        # row has an element for each genome that contains 0 or more seq ids, and row has the distance of the cluster as its final element.
        row = result['rows'][index]
        # get terms in cluster
        clusterTerms = getTermsForCluster(row, seqIdToDataMap)
        if termParam not in clusterTerms:
            continue
        clusterIndexToProfileMap[index] = getProfileForCluster(row)
        clusterIndexToBestGeneNameMap[index] = getBestClusterGeneName(row, headers, seqIdToDataMap)
        termToClusterIndicesMap.setdefault(termParam, []).append(index)

    clusterIndices = termToClusterIndicesMap[termParam]
    numClusters = len(clusterIndices)
    meanPairwiseHammingDistance = computeMeanPairwiseHammingDistance(result, clusterIndices, clusterIndexToProfileMap)
    # ignore terms associated with many clusters on the assumption that they are too general to be interesting.

    content = ''
    content += makeQueryDescHtml(result)

    content += '<h3>Result Description</h3>'
    content += '<pre>A list of all genes associated with the GO term %s.\n'%termParam
    content += 'Also reported:\n'
    content += '\tMean hamming distance between each pair of profiles of the gene clusters annotated with the GO term\n'
    content += '\tNumber of gene clusters associated with the GO term.\n'
    content += 'For GO terms with only one associated gene cluster, the mean pairwise hamming distance is defined as 0.\n'
    content += 'GO terms associated with more than '+str(TERM_PROMISCUITY_LIMIT)+' gene clusters are excluded as being too general to be interesting.\n'
    content += 'Click on table column headers to sort by that column.\n'
    content += '</pre>'

    content += '<h3>Result</h3>'
    content += 'GO Id: %s<br />\n'%termParam
    content += 'GO Term: %s<br />\n'%termMap.get(termParam)
    content += 'Number of Gene Clusters Associated with GO Term: %d<br />\n'%numClusters
    if numClusters <= TERM_PROMISCUITY_LIMIT:
        content += 'Mean Pairwise Gene Profile Hamming Distance: %.2f<br />\n'%meanPairwiseHammingDistance
    else:
        content += 'Too many gene clusters associated with GO Term to compute Pairwise Gene Profile Hamming Distance.'
        content += '  Number of gene clusters must not be greater than %d.<br />\n'%TERM_PROMISCUITY_LIMIT
    content += '\n'
    content += '<h4> Gene Clusters Associated with GO Term</h4>\n'
    clusterIndices.sort()
    content += makeSequenceClustersTable(result, resultId, clusterIndices)
    return content


def makeSequenceClustersTable(result, resultId, clusterIndices=None, startIndex=None, endIndex=None):
    '''
    clusterIndices: list of indices of result rows to put into table
    returns: html table for result gene clusters/rows.
    '''
    seqIdToDataMap = result.get('seq_id_to_data_map', {})
    termMap = result.get('term_map', {})
    headers = result['headers']

    if clusterIndices is None:
        numRows = len(result['rows'])
        if startIndex is None:
            startIndex = 0
        if endIndex is None or endIndex > numRows:
            endIndex = numRows
        clusterIndices = range(startIndex, endIndex)
        
    content = ''
    content += "<table class=\"roundup_cluster\">\n";
    displayGenomes = [roundupGenomeDisplayName(genome) for genome in headers[:-1]]
    geneResultUrl = makeResultUrl(resultId, resultType='roundup_gene_result', templateType='roundup_wide_template')
    for index in clusterIndices:
        row = result['rows'][index]
        phyleticProfile = getProfileForCluster(row)
        avgDist = row[-1]
        content += '<tr class="c_h"><td colspan="4"><a href="%s">Gene Cluster #%s</a>'%(geneResultUrl+'&gene_index='+urllib.quote_plus(str(index)), index+1)
        content += ' | '+headers[-1]+': %s | Phyletic Profile: %s</td></tr>\n'%(avgDist, ''.join([str(p) for p in phyleticProfile]))
        content += "<tr><td>Sequence Id</td><td>Genome</td><td>Gene Name</td><td>GO Terms</td></tr>\n"
        for colIndex in range(len(row)-1):
            seqIds = row[colIndex]
            if not seqIds:
                content += "<tr><td>-</td><td>%s</td><td>-</td><td>-</td></tr>\n"%displayGenomes[colIndex]
            else:
                for seqId in seqIds:
                    content += '<tr>'
                    content += '<td>%s</td>'%makeSeqIdLink(seqIdToDataMap[seqId][roundup_common.EXTERNAL_SEQUENCE_ID_KEY])
                    content += '<td>%s</td>'%displayGenomes[colIndex]
                    content += '<td>%s</td>'%seqIdToDataMap[seqId].get(roundup_common.GENE_NAME_KEY, '-')
                    terms = seqIdToDataMap[seqId].get(roundup_common.TERMS_KEY, [])
                    if terms:
                        content += '<td>%s</td>'%', '.join([termMap[t] for t in terms])
                    else:
                        content += '<td>-</td>'
                    content += '</tr>\n'
        content += "<tr class=\"c_f\"><td colspan=\"4\">&nbsp;</td></tr>\n";
    content += "</table>\n";
    return content


def chooseBetterPhyleticClusterInfo(clusterInfo1, clusterInfo2):
    # better in this case means the cluster info with later blank elements.
    # compare the nth blank element of each. choose the one such that
    # the index of the nth blank element is larger than the index of the others nth blank element for the smallest value of n.
    # E.g. choose ('a', 'b', '') over ('1', '', '3').  If all blank elements are in the same position, choose the first cluster info.
    if (clusterInfo1[0] and not clusterInfo2[0]): return clusterInfo1
    if (not clusterInfo1[0] and clusterInfo2[0]): return clusterInfo2
    if (clusterInfo1[1] and not clusterInfo2[1]): return clusterInfo1
    if (not clusterInfo1[1] and clusterInfo2[1]): return clusterInfo2
    if (clusterInfo1[2] and not clusterInfo2[2]): return clusterInfo1
    if (not clusterInfo1[2] and clusterInfo2[2]): return clusterInfo2
    return clusterInfo1


def makePhyleticClusterInfo(seqId, seqIdToDataMap, termMap):
    data = seqIdToDataMap.get(seqId, {})
    acc = data.get(roundup_common.EXTERNAL_SEQUENCE_ID_KEY, '')
    geneName = data.get(roundup_common.GENE_NAME_KEY, '')
    terms = data.get(roundup_common.TERMS_KEY, [])
    termName = ''
    if terms:
        termName = termMap.get(terms[0], '')
    if acc is None:
        acc = ''
    if geneName is None:
        geneName = ''
    if termName is None:
        termName = ''
    info = [acc, geneName, termName]
    return info


def flipmatrix(rec):
    '''
    Objective: flip a roundup matrix
    Parameters: the contents of the file read into list format
    Returns: a flipped matrix and a couple of useful stats for later
    '''
    fm = ''
    amatrix = []
    
    #[:-2] is to cut out the "cluster info" tag in the name row	
    genomes = string.split(rec[0], '\t')[:-1]
    
    print genomes
    
    # each row is a tuple of genome and list of genes.
    for genome in genomes:
        genome = re.sub('\n','', genome)
        genome = re.sub('.aa','', genome)
        row = (genome, [])
        amatrix.append(row)
        
    # we need to have a record of the number of genomes for later
    ntax = len(genomes)
    
    for l in rec[1:]:
        #[:-1] to cut out the last column, info we don't want
        col = string.split(l, '\t')[:-1]
        
        for i in range(0, ntax):
            c = re.sub('\n','',col[i])
            amatrix[i][1].append(c)

    # matrix is for each genome a line of tab-separated list of ones and zeros followed by a line containing genome name and
    matrix = ''
    for elem in amatrix:
        # a record of the number of characters (ntax) for later
        nchar = len(elem[1])
        r = ''
        otu = elem[0]
        for i in elem[1]:
            r += '%s\t'%i
        r += '\n'
        matrix += "%s\t%s"%(otu, r)
	
    return matrix, ntax, nchar



if __name__=='__main__':
    pass


#####################
# DEPRECATED/OLD CODE
#####################



