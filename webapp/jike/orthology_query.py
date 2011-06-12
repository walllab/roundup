#!/usr/bin/env python

#############################################
# DEPRECATED DEPRECATED DEPRECATED DEPRECATED 
# DEPRECATED DEPRECATED DEPRECATED DEPRECATED 
# DEPRECATED DEPRECATED DEPRECATED DEPRECATED 
#############################################
# SEE orthologyquery.py
# maintained b/c it has a lot of jike code in it.
# will be removed eventually.

'''
used by roundup web site to retrieve, cluster, and return orthology data, including annotations like gene names and go terms.
'''
import itertools
import logging

import config
import util
import rodeo_db
import clustering
import roundup_db
import roundup_common


DEFAULT_DB_CURSOR_READ_BUFFER_SIZE = 100

def makeLowerAndUpperLimitFilterFuncs(distance_lower_limit, distance_upper_limit):
    if distance_lower_limit is not None:
        float_distance_lower_limit = float(distance_lower_limit)
        def lowerFunc(ortholog):
            return ortholog[2] >= float_distance_lower_limit
    else:
        def lowerFunc(ortholog):
            return True
    if distance_upper_limit is not None:
        float_distance_upper_limit = float(distance_upper_limit)
        def upperFunc(ortholog):
            return ortholog[2] <= float_distance_upper_limit
    else:
        def upperFunc(ortholog):
            return True
    return (lowerFunc, upperFunc)


def makePairsForGenomeParams(genome=None, limit_genomes=None, genomes=None):
        # all genomes
        allGenomes = []
        if genome:
            allGenomes.append(genome)
        if genomes:
            allGenomes.extend(genomes)
        if limit_genomes:
            allGenomes.extend(limit_genomes)
        allGenomes = list(set(allGenomes))
        # all pairs of genomes
        pairs = roundup_common.normalizePairs(util.choose(allGenomes, 2))
        if genome:
            pairs = [pair for pair in pairs if pair[0] == genome or pair[1] == genome]
        if limit_genomes:
            pairs = [pair for pair in pairs if pair[0] in limit_genomes or pair[1] in limit_genomes]
        if genomes:
            pairs = [pair for pair in pairs if pair[0] in genomes and pair[1] in genomes]
        return pairs
    

def doOrthologyQuery(query_desc=None, tc_only=False, db_cursor_read_buffer_size=DEFAULT_DB_CURSOR_READ_BUFFER_SIZE,
                     genome=None, limit_genomes=None, genomes=None, seq_ids=None, divergence=None, evalue=None,
                     go_term=False, gene_name=False, outputPath=None, sortGenomes=True, distance_lower_limit=None, distance_upper_limit=None, **keywords):
    '''
    query_desc: string describing the query being run.  used by the web to let the user know what query was run to generate these results.
    tc_only: if true and cluster_orthologs is true, only transitively closed clusters are returned.
    seq_ids: a list of external_sequence_ids/accession numbers/GIs.  if not empty, it is used to restrict orthologs to only those that have either query_id or subject_id in seq_ids.
    genome: get orthologs with a sequence from this genome
    limit_genomes: get orthologs with a sequence in a genome from limit_genomes.
    genomes: get orthologs where both sequences are from genomes.
    divergence: get orthologs calculated with this divergence threshold.
    evalue: get orthologs calculated with this evalue threshold.
    go_term: if true, a mapping of seq ids to go terms is returned for the seq ids in the orthology results.
    gene_name: if true, a mapping of seq ids to gene names is returned for the seq ids in the orthology results.
    outputPath: if not None, the return value is pickled to this path, not returned, and None is returned.
    keywords: ignored.  here for historical compatibility reasons.
    This function queries the database to get a list of orthologs and possibly gene names and go terms associated with those orthologs.
    The orthologs are grouped into clusters (connected subgraphs).
    returns: a dict containing clusters, column headers, and possibly containing dicts for gene names, go terms, genome names, etc.
    '''
    
    if tc_only:
        cluster_orthologs = True
        
    tableDesc = {'query_desc': query_desc}

    distanceLowerLimitFilter, distanceUpperLimitFilter = makeLowerAndUpperLimitFilterFuncs(distance_lower_limit, distance_upper_limit)

    for conn in roundup_db.withRoundupDbConn():
        pairs = makePairsForGenomeParams(genome, limit_genomes, genomes)
        orthologsLists = []
        for pair in pairs:
            orthologs = roundup_db.getOrthologs(conn=conn, qdb=pair[0], sdb=pair[1], divergence=divergence, evalue=evalue)
            orthologsLists.append(orthologs)
        # orthologsLists is a list of lists of (query_sequence_id, subject_sequence_id, distance) tuples
        sequenceIds = set()
        for ortholog in itertools.chain(*orthologsLists): # orthologs:
            if distanceLowerLimitFilter(ortholog) and distanceUpperLimitFilter(ortholog):
                sequenceIds.add(ortholog[0])
                sequenceIds.add(ortholog[1])
        
        # get sequence data map from sequenceId to external_id, genome_id, gene_name.
        sequenceIds = list(sequenceIds)
        sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(sequenceIds, conn=conn)

        # cluster orthologs, limiting by seq_ids
        clusterer = clustering.EdgeClusterer(storeEdges=True)
        for ortholog in itertools.chain(*orthologsLists): # orthologs:
            if distanceLowerLimitFilter(ortholog) and distanceUpperLimitFilter(ortholog):
                # skip orthologs not in seq_ids
                if seq_ids:
                    if sequenceIdToSequenceDataMap[ortholog[0]][roundup_common.EXTERNAL_SEQUENCE_ID_KEY] not in seq_ids:
                        if sequenceIdToSequenceDataMap[ortholog[1]][roundup_common.EXTERNAL_SEQUENCE_ID_KEY] not in seq_ids:
                            continue
                clusterer.cluster(ortholog)
            pass

        # get genome database ids
        genomeIds = set([sequenceIdToSequenceDataMap[id][roundup_common.GENOME_ID_KEY] for id in sequenceIds])
        genomeIds = list(genomeIds)
        genomes = [roundup_db.getDatabaseForId(id=id, conn=conn) for id in genomeIds]
        # map genome to genomeId
        genomeToGenomeId = dict(zip(genomes, genomeIds))
        genomeIdToGenome = dict(zip(genomeIds, genomes))
        # sorted genomes, with genome keyword (if any) at front.
        if sortGenomes: genomes.sort() ### jike added 'if sortGenomes'
        if genome and genome in genomes:
            genomes.remove(genome)
            genomes.insert(0, genome)
        # map genomeId to column in result rows
        genomeIdToCol = dict([(genomeToGenomeId[genomes[col]], col) for col in range(len(genomes))])
        # genomeColToGenome = dict([(col, genomes[col]) for col in range(len(genomes))])
        # sort genomes and map genome ids to columns
        # sortedGenomeAndIdPairsList = zip(genomes, genomeIds)
        # sortedGenomeAndIdPairsList.sort()
        # genomeIdToCol = dict((sortedGenomeAndIdPairsList[col][1], col) for col in xrange(len(sortedGenomeAndIdPairsList)))
        
        # add each cluster to the cluster table
        # each row contains the genes for each genome in the correct column and the avg distance of the cluster edges.
        clusterTable = []
        clusterOrthologsList = []
        headerRow = genomes + ['Average Evolutionary Distance']
        for clusterId, cluster in clusterer.clusterIdToNodes.iteritems():
            clusterOrthologsList.append(clusterer.clusterIdToEdges[clusterId])
            numNodes = len(cluster)
            numClassesInCluster = len(set([sequenceIdToSequenceDataMap[gene][roundup_common.GENOME_ID_KEY] for gene in cluster]))
            # if tc_only, do not report non-transitively closed clusters or cluster-classes.
            if tc_only and (clusterer.clusterIdToNumEdges[clusterId] < ((numNodes * (numNodes - 1)) / 2) or numClassesInCluster != len(genomeIds)):
                continue
            # initialize lists for genes in each genome belonging to cluster
            clusterRow = [[]  for i in range(len(genomeIds))]
            # tack on avg dist to end of row.
            avgEdgeDist = clusterer.clusterIdToSumDistances[clusterId]/float(clusterer.clusterIdToNumEdges[clusterId])
            clusterRow.append('%.3f'%avgEdgeDist)
            try:
                for gene in cluster:
                    genomeId = sequenceIdToSequenceDataMap[gene][roundup_common.GENOME_ID_KEY]
                    clusterRow[genomeIdToCol[genomeId]].append(gene)
            except:
                logging.debug('gene: '+str(gene))
                logging.debug('genomes: '+str(genomes))
                logging.debug('genomeIds: '+str(genomeIds))
                logging.debug('sequenceIdToSequenceDataMap: '+str(sequenceIdToSequenceDataMap))
                logging.debug('genomeIdToCol: '+str(genomeIdToCol))
                raise
            clusterTable.append(clusterRow)
            
        tableDesc['type'] = 'clusters'
        tableDesc['headers'] = headerRow
        tableDesc['rows'] = clusterTable
        tableDesc['orthologs'] = clusterOrthologsList
        
        seqIdDataMap = dict([(id, {roundup_common.EXTERNAL_SEQUENCE_ID_KEY: sequenceIdToSequenceDataMap[id][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                   roundup_common.GENOME_ID_KEY: sequenceIdToSequenceDataMap[id][roundup_common.GENOME_ID_KEY]})
                             for id in sequenceIdToSequenceDataMap])
        if gene_name:
            tableDesc['has_gene_names'] = True
            for id in sequenceIdToSequenceDataMap:
                seqIdDataMap[id][roundup_common.GENE_NAME_KEY] = sequenceIdToSequenceDataMap[id][roundup_common.GENE_NAME_KEY]
        if go_term:
            tableDesc['has_go_terms'] = True
            (sequenceIdToTermsMap, termMap) = roundup_db.getSequenceIdToTermsMap(sequenceIds, conn=conn)
            for id in sequenceIdToSequenceDataMap:
                seqIdDataMap[id][roundup_common.TERMS_KEY] = sequenceIdToTermsMap.get(id, [])
            tableDesc['term_map'] = termMap
        tableDesc['seq_id_to_data_map'] = seqIdDataMap
        tableDesc['genome_id_to_genome_map'] = genomeIdToGenome
    if outputPath:
        util.dumpObject(tableDesc, outputPath)
        return None
    else:
        return tableDesc



def doOrthologyQuery2(query_desc=None, tc_only=False, db_cursor_read_buffer_size=DEFAULT_DB_CURSOR_READ_BUFFER_SIZE,
                     genome=None, limit_genomes=None, genomes=None, seq_ids=None, divergence=None, evalue=None,
                     go_term=False, gene_name=False, outputPath=None, sortGenomes=True, distance_lower_limit=None, distance_upper_limit=None, **keywords):
    '''
    query_desc: string describing the query being run.  used by the web to let the user know what query was run to generate these results.
    tc_only: if true and cluster_orthologs is true, only transitively closed clusters are returned.
    seq_ids: a list of external_sequence_ids/accession numbers/GIs.  if not empty, it is used to restrict orthologs to only those that have either query_id or subject_id in seq_ids.
    genome: get orthologs with a sequence from this genome
    limit_genomes: get orthologs with a sequence in a genome from limit_genomes.
    genomes: get orthologs where both sequences are from genomes.
    divergence: get orthologs calculated with this divergence threshold.
    evalue: get orthologs calculated with this evalue threshold.
    go_term: if true, a mapping of seq ids to go terms is returned for the seq ids in the orthology results.
    gene_name: if true, a mapping of seq ids to gene names is returned for the seq ids in the orthology results.
    outputPath: if not None, the return value is pickled to this path, not returned, and None is returned.
    keywords: ignored.  here for historical compatibility reasons.
    This function queries the database to get a list of orthologs and possibly gene names and go terms associated with those orthologs.
    The orthologs are grouped into clusters (connected subgraphs).
    returns: a dict containing clusters, column headers, and possibly containing dicts for gene names, go terms, genome names, etc.
    '''

    if tc_only:
        cluster_orthologs = True

    tableDesc = {'query_desc': query_desc}

    distanceLowerLimitFilter, distanceUpperLimitFilter = makeLowerAndUpperLimitFilterFuncs(distance_lower_limit, distance_upper_limit)

    for conn in roundup_db.withRoundupDbConn():
        pairs = makePairsForGenomeParams(genome, limit_genomes, genomes)
        orthologsLists = []
        for pair in pairs:
            orthologs = roundup_db.getOrthologs(conn=conn, qdb=pair[0], sdb=pair[1], divergence=divergence, evalue=evalue)
            orthologsLists.append(orthologs)
        
        # orthologsLists is a list of lists of (query_sequence_id, subject_sequence_id, distance) tuples
        sequenceIds = set()
        for ortholog in itertools.chain(*orthologsLists): # orthologs:
            if distanceLowerLimitFilter(ortholog) and distanceUpperLimitFilter(ortholog):
                sequenceIds.add(ortholog[0])
                sequenceIds.add(ortholog[1])
        
        # get sequence data map from sequenceId to external_id, genome_id, gene_name.
        sequenceIds = list(sequenceIds)
        sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(sequenceIds, conn=conn)

        # cluster orthologs, limiting by seq_ids
        clusterer = clustering.EdgeClusterer(storeEdges=True)
        for ortholog in itertools.chain(*orthologsLists): # orthologs:
            if distanceLowerLimitFilter(ortholog) and distanceUpperLimitFilter(ortholog):
                # skip orthologs not in seq_ids
                if seq_ids:
                    if sequenceIdToSequenceDataMap[ortholog[0]][roundup_common.EXTERNAL_SEQUENCE_ID_KEY] not in seq_ids:
                        if sequenceIdToSequenceDataMap[ortholog[1]][roundup_common.EXTERNAL_SEQUENCE_ID_KEY] not in seq_ids:
                            continue
                clusterer.cluster(ortholog)
            pass

        # get genome database ids
#        genomeIds = set([sequenceIdToSequenceDataMap[id][roundup_common.GENOME_ID_KEY] for id in sequenceIds])
#        genomeIds = list(genomeIds)
#        genomes = [roundup_db.getDatabaseForId(id=id, conn=conn) for id in genomeIds]
        genomeIds = [roundup_db.getIdForDatabase(db, conn) for db in genomes]
        # map genome to genomeId
        genomeToGenomeId = dict(zip(genomes, genomeIds))
        genomeIdToGenome = dict(zip(genomeIds, genomes))
        # sorted genomes, with genome keyword (if any) at front.
        if sortGenomes: genomes.sort() ### jike added 'if sortGenomes'
        # if genome and genome in genomes:
        #     genomes.remove(genome)
        #     genomes.insert(0, genome)
        # map genomeId to column in result rows
        genomeIdToCol = dict([(genomeToGenomeId[genomes[col]], col) for col in range(len(genomes))])
        # genomeColToGenome = dict([(col, genomes[col]) for col in range(len(genomes))])
        # sort genomes and map genome ids to columns
        # sortedGenomeAndIdPairsList = zip(genomes, genomeIds)
        # sortedGenomeAndIdPairsList.sort()
        # genomeIdToCol = dict((sortedGenomeAndIdPairsList[col][1], col) for col in xrange(len(sortedGenomeAndIdPairsList)))

        # add each cluster to the cluster table
        # each row contains the genes for each genome in the correct column and the avg distance of the cluster edges.
        clusterTable = []
        clusterOrthologsList = []
        headerRow = genomes + ['Average Evolutionary Distance']
        for clusterId, cluster in clusterer.clusterIdToNodes.iteritems():
            clusterOrthologsList.append(clusterer.clusterIdToEdges[clusterId])
            numNodes = len(cluster)
            numClassesInCluster = len(set([sequenceIdToSequenceDataMap[gene][roundup_common.GENOME_ID_KEY] for gene in cluster]))
            # if tc_only, do not report non-transitively closed clusters or cluster-classes.
            if tc_only and (clusterer.clusterIdToNumEdges[clusterId] < ((numNodes * (numNodes - 1)) / 2) or numClassesInCluster != len(genomeIds)):
                continue
            # initialize lists for genes in each genome belonging to cluster
            clusterRow = [[]  for i in range(len(genomeIds))]
            # tack on avg dist to end of row.
            avgEdgeDist = clusterer.clusterIdToSumDistances[clusterId]/float(clusterer.clusterIdToNumEdges[clusterId])
            clusterRow.append('%.3f'%avgEdgeDist)
            try:
                for gene in cluster:
                    genomeId = sequenceIdToSequenceDataMap[gene][roundup_common.GENOME_ID_KEY]
                    clusterRow[genomeIdToCol[genomeId]].append(gene)
            except:
                logging.debug('gene: '+str(gene))
                logging.debug('genomes: '+str(genomes))
                logging.debug('genomeIds: '+str(genomeIds))
                logging.debug('sequenceIdToSequenceDataMap: '+str(sequenceIdToSequenceDataMap))
                logging.debug('genomeIdToCol: '+str(genomeIdToCol))
                raise
            clusterTable.append(clusterRow)

        tableDesc['type'] = 'clusters'
        tableDesc['headers'] = headerRow
        tableDesc['rows'] = clusterTable
        tableDesc['orthologs'] = clusterOrthologsList

        seqIdDataMap = dict([(id, {roundup_common.EXTERNAL_SEQUENCE_ID_KEY: sequenceIdToSequenceDataMap[id][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                   roundup_common.GENOME_ID_KEY: sequenceIdToSequenceDataMap[id][roundup_common.GENOME_ID_KEY]})
                             for id in sequenceIdToSequenceDataMap])
        if gene_name:
            tableDesc['has_gene_names'] = True
            for id in sequenceIdToSequenceDataMap:
                seqIdDataMap[id][roundup_common.GENE_NAME_KEY] = sequenceIdToSequenceDataMap[id][roundup_common.GENE_NAME_KEY]
        if go_term:
            tableDesc['has_go_terms'] = True
            (sequenceIdToTermsMap, termMap) = roundup_db.getSequenceIdToTermsMap(sequenceIds, conn=conn)
            for id in sequenceIdToSequenceDataMap:
                seqIdDataMap[id][roundup_common.TERMS_KEY] = sequenceIdToTermsMap.get(id, [])
            tableDesc['term_map'] = termMap
        tableDesc['seq_id_to_data_map'] = seqIdDataMap
        tableDesc['genome_id_to_genome_map'] = genomeIdToGenome
    if outputPath:
        util.dumpObject(tableDesc, outputPath)
        return None
    else:
        return tableDesc

   
def doOrthologyQuery3(query_desc=None, tc_only=False, db_cursor_read_buffer_size=DEFAULT_DB_CURSOR_READ_BUFFER_SIZE,
                     genome=None, limit_genomes=None, genomes=None, seq_ids=None, divergence=None, evalue=None,
                     go_term=False, gene_name=False, outputPath=None, sortGenomes=True, distance_lower_limit=None, distance_upper_limit=None, **keywords):
    '''
    Implement a new clustering algorithm
    Orthohologs are clustered all around the genes in the 1st genome in genomes,
    then clustered around genes in the 2nd genome that are not present in the
    previous clusters, and so on.

    To save space, distance is removed from ortholog pair
    Added by Jike
    '''

    if tc_only:
        cluster_orthologs = True

    tableDesc = {'query_desc': query_desc}

    for conn in roundup_db.withRoundupDbConn():
        # 1. make genome pairs. Produce a set of genome pairs in tuple
        # format of pairs [('Caenorhabditis_elegans.aa', 'Dictyostelium_discoideum.aa'), ('Caenorhabditis_elegans.aa', 'Neurospora_crassa.aa')]
        clusterer = clustering.EdgeClusterer(storeEdges=True)
        sequenceIds = set()
        distanceHigh=float(distance_upper_limit)

        for g in xrange(len(genomes)):
            pairs=[(genomes[g],aGenome) for aGenome in genomes if aGenome!=genomes[g]]

            # 2. get ortholog pairs in each genome pair
            orthologsLists = []
            for pair in pairs:
                #qdb must be alphabetically smaller than sdb
                if pair[0]<pair[1]:
                    orthologs = [orth for orth in roundup_db.getOrthologs(conn=conn, qdb=pair[0], sdb=pair[1], divergence=divergence, evalue=evalue) if orth[2]<distanceHigh]
                    orthologs = [orth[:2] for orth in orthologs]
                else:
                    orthologs = [orth for orth in roundup_db.getOrthologs(conn=conn, qdb=pair[1], sdb=pair[0], divergence=divergence, evalue=evalue) if orth[2]<distanceHigh]
                    orthologs = [(orth[1],orth[0]) for orth in orthologs]
                orthologsLists.append(orthologs)

            # orthologsLists is a list of lists of (query_sequence_id, subject_sequence_id, distance) tuples
            # 3. get sequence IDs of ortholog pairs
            for ortholog in itertools.chain(*orthologsLists): # orthologs:
                sequenceIds.add(ortholog[0])
                sequenceIds.add(ortholog[1])
                clusterer.cluster_2(ortholog)

        # get sequence data map from sequenceId to external_id, genome_id, gene_name.
        sequenceIds = list(sequenceIds)
        sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(sequenceIds, conn=conn)

        # get genome database ids
        # genomeIds = set([sequenceIdToSequenceDataMap[id][roundup_common.GENOME_ID_KEY] for id in sequenceIds])
        # genomeIds = list(genomeIds)
        # genomes = [roundup_db.getDatabaseForId(id=id, conn=conn) for id in genomeIds]
        genomeIds = [roundup_db.getIdForDatabase(db, conn) for db in genomes]
        # map genome to genomeId
        genomeToGenomeId = dict(zip(genomes, genomeIds))
        genomeIdToGenome = dict(zip(genomeIds, genomes))
        # sorted genomes, with genome keyword (if any) at front.
        if sortGenomes: genomes.sort() ### jike added 'if sortGenomes'
        # if genome and genome in genomes:
        #     genomes.remove(genome)
        #     genomes.insert(0, genome)
        # map genomeId to column in result rows
        genomeIdToCol = dict([(genomeToGenomeId[genomes[col]], col) for col in range(len(genomes))])
        # genomeColToGenome = dict([(col, genomes[col]) for col in range(len(genomes))])
        # sort genomes and map genome ids to columns
        # sortedGenomeAndIdPairsList = zip(genomes, genomeIds)
        # sortedGenomeAndIdPairsList.sort()
        # genomeIdToCol = dict((sortedGenomeAndIdPairsList[col][1], col) for col in xrange(len(sortedGenomeAndIdPairsList)))

        # add each cluster to the cluster table
        # each row contains the genes for each genome in the correct column and the avg distance of the cluster edges.
        clusterTable = []
        clusterOrthologsList = []
        headerRow = genomes + ['Average Evolutionary Distance']
        for clusterId, cluster in clusterer.clusterIdToNodes.iteritems():
            clusterOrthologsList.append(clusterer.clusterIdToEdges[clusterId])
            numNodes = len(cluster)
            numClassesInCluster = len(set([sequenceIdToSequenceDataMap[gene][roundup_common.GENOME_ID_KEY] for gene in cluster]))
            # if tc_only, do not report non-transitively closed clusters or cluster-classes.
            if tc_only and (clusterer.clusterIdToNumEdges[clusterId] < ((numNodes * (numNodes - 1)) / 2) or numClassesInCluster != len(genomeIds)):
                continue
            # initialize lists for genes in each genome belonging to cluster
            clusterRow = [[]  for i in range(len(genomeIds))]
            # tack on avg dist to end of row.
            #--avgEdgeDist = clusterer.clusterIdToSumDistances[clusterId]/float(clusterer.clusterIdToNumEdges[clusterId])
            #--clusterRow.append('%.3f'%avgEdgeDist)
            #--clusterRow.append('1.3')  #--test, remove later
            try:
                for gene in cluster:
                    genomeId = sequenceIdToSequenceDataMap[gene][roundup_common.GENOME_ID_KEY]
                    clusterRow[genomeIdToCol[genomeId]].append(gene)
            except:
                logging.debug('gene: '+str(gene))
                logging.debug('genomes: '+str(genomes))
                logging.debug('genomeIds: '+str(genomeIds))
                logging.debug('sequenceIdToSequenceDataMap: '+str(sequenceIdToSequenceDataMap))
                logging.debug('genomeIdToCol: '+str(genomeIdToCol))
                raise
            clusterTable.append(clusterRow)

        tableDesc['type'] = 'clusters'
        tableDesc['headers'] = headerRow
        tableDesc['rows'] = clusterTable
        tableDesc['orthologs'] = clusterOrthologsList

        seqIdDataMap = dict([(id, {roundup_common.EXTERNAL_SEQUENCE_ID_KEY: sequenceIdToSequenceDataMap[id][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                   roundup_common.GENOME_ID_KEY: sequenceIdToSequenceDataMap[id][roundup_common.GENOME_ID_KEY]})
                             for id in sequenceIdToSequenceDataMap])
        if gene_name:
            tableDesc['has_gene_names'] = True
            for id in sequenceIdToSequenceDataMap:
                seqIdDataMap[id][roundup_common.GENE_NAME_KEY] = sequenceIdToSequenceDataMap[id][roundup_common.GENE_NAME_KEY]
        if go_term:
            tableDesc['has_go_terms'] = True
            (sequenceIdToTermsMap, termMap) = roundup_db.getSequenceIdToTermsMap(sequenceIds, conn=conn)
            for id in sequenceIdToSequenceDataMap:
                seqIdDataMap[id][roundup_common.TERMS_KEY] = sequenceIdToTermsMap.get(id, [])
            tableDesc['term_map'] = termMap
        tableDesc['seq_id_to_data_map'] = seqIdDataMap
        tableDesc['genome_id_to_genome_map'] = genomeIdToGenome
    if outputPath:
        util.dumpObject(tableDesc, outputPath)
        return None
    else:
        return tableDesc


def doOrthologyQuery4(query_desc=None, tc_only=False, db_cursor_read_buffer_size=DEFAULT_DB_CURSOR_READ_BUFFER_SIZE,
                     genome=None, limit_genomes=None, genomes=None, seq_ids=None, divergence=None, evalue=None,
                     go_term=False, gene_name=False, outputPath=None, sortGenomes=True, distance_lower_limit=None, distance_upper_limit=None, **keywords):
    '''
    Implement a new clustering algorithm
    Orthohologs are clustered all around the genes in the 1st genome in genomes,
    then clustered around genes in the 2nd genome that are not present in the
    previous clusters, and so on.

    change from version 3:
    In making pairs, use the original function, which have cases for genome
    and limit_genomes, and does not make duplicated pairs. Those are missed
    in version 3. But the duplicated pairs in ver. 3 does not cause problem
    because the new clustering algorithm ignore a duplicated edge.

    To save space, distance is removed from ortholog pair
    Added by Jike
    '''

    if tc_only:
        cluster_orthologs = True

    tableDesc = {'query_desc': query_desc}

    for conn in roundup_db.withRoundupDbConn():
        # 1. make genome pairs. Produce a set of genome pairs in tuple
        # format of pairs [('Caenorhabditis_elegans.aa', 'Dictyostelium_discoideum.aa'), ('Caenorhabditis_elegans.aa', 'Neurospora_crassa.aa')]
        clusterer = clustering.EdgeClusterer(storeEdges=True)
        sequenceIds = set()
        distanceHigh=float(distance_upper_limit)
        pairs = makePairsForGenomeParams(genome, limit_genomes, genomes)

        # 2. get ortholog pairs in each genome pair
        orthologsLists = []
        qdb,sdb="",""
        for pair in pairs:
            #qdb must be alphabetically smaller than sdb
            if pair[0]<pair[1]: (qdb,sdb)=pair
            else: (sdb,qdb)=pair

            orthologs = [orth for orth in roundup_db.getOrthologs(conn=conn, qdb=qdb, sdb=sdb, divergence=divergence, evalue=evalue) if orth[2]<distanceHigh]
            orthologs = [orth[:2] for orth in orthologs] #distance info is removed to save space.
            orthologsLists.append(orthologs)

        # orthologsLists is a list of lists of (query_sequence_id, subject_sequence_id, distance) tuples
        # 3. get sequence IDs of ortholog pairs
        for ortholog in itertools.chain(*orthologsLists): # orthologs:
            sequenceIds.add(ortholog[0])
            sequenceIds.add(ortholog[1])
            clusterer.cluster_3(ortholog)

        # get sequence data map from sequenceId to external_id, genome_id, gene_name.
        sequenceIds = list(sequenceIds)
        sequenceIdToSequenceDataMap = roundup_db.getSequenceIdToSequenceDataMap(sequenceIds, conn=conn)

        # get genome database ids
        # genomeIds = set([sequenceIdToSequenceDataMap[id][roundup_common.GENOME_ID_KEY] for id in sequenceIds])
        # genomeIds = list(genomeIds)
        # genomes = [roundup_db.getDatabaseForId(id=id, conn=conn) for id in genomeIds]
        genomeIds = [roundup_db.getIdForDatabase(db, conn) for db in genomes]
        # map genome to genomeId
        genomeToGenomeId = dict(zip(genomes, genomeIds))
        genomeIdToGenome = dict(zip(genomeIds, genomes))
        # sorted genomes, with genome keyword (if any) at front.
        if sortGenomes: genomes.sort() ### jike added 'if sortGenomes'
        # if genome and genome in genomes:
        #     genomes.remove(genome)
        #     genomes.insert(0, genome)
        # map genomeId to column in result rows
        genomeIdToCol = dict([(genomeToGenomeId[genomes[col]], col) for col in range(len(genomes))])
        # genomeColToGenome = dict([(col, genomes[col]) for col in range(len(genomes))])
        # sort genomes and map genome ids to columns
        # sortedGenomeAndIdPairsList = zip(genomes, genomeIds)
        # sortedGenomeAndIdPairsList.sort()
        # genomeIdToCol = dict((sortedGenomeAndIdPairsList[col][1], col) for col in xrange(len(sortedGenomeAndIdPairsList)))

        # add each cluster to the cluster table
        # each row contains the genes for each genome in the correct column and the avg distance of the cluster edges.
        clusterTable = []
        clusterOrthologsList = []
        headerRow = genomes + ['Average Evolutionary Distance']
        for clusterId, cluster in clusterer.clusterIdToNodes.iteritems():
            clusterOrthologsList.append(clusterer.clusterIdToEdges[clusterId])
            numNodes = len(cluster)
            numClassesInCluster = len(set([sequenceIdToSequenceDataMap[gene][roundup_common.GENOME_ID_KEY] for gene in cluster]))
            # if tc_only, do not report non-transitively closed clusters or cluster-classes.
            if tc_only and (clusterer.clusterIdToNumEdges[clusterId] < ((numNodes * (numNodes - 1)) / 2) or numClassesInCluster != len(genomeIds)):
                continue
            # initialize lists for genes in each genome belonging to cluster
            clusterRow = [[]  for i in range(len(genomeIds))]
            # tack on avg dist to end of row.
            #--avgEdgeDist = clusterer.clusterIdToSumDistances[clusterId]/float(clusterer.clusterIdToNumEdges[clusterId])
            #--clusterRow.append('%.3f'%avgEdgeDist)
            #--clusterRow.append('1.3')  #--test, remove later
            try:
                for gene in cluster:
                    genomeId = sequenceIdToSequenceDataMap[gene][roundup_common.GENOME_ID_KEY]
                    clusterRow[genomeIdToCol[genomeId]].append(gene)
            except:
                logging.debug('gene: '+str(gene))
                logging.debug('genomes: '+str(genomes))
                logging.debug('genomeIds: '+str(genomeIds))
                logging.debug('sequenceIdToSequenceDataMap: '+str(sequenceIdToSequenceDataMap))
                logging.debug('genomeIdToCol: '+str(genomeIdToCol))
                raise
            clusterTable.append(clusterRow)

        tableDesc['type'] = 'clusters'
        tableDesc['headers'] = headerRow
        tableDesc['rows'] = clusterTable
        tableDesc['orthologs'] = clusterOrthologsList

        seqIdDataMap = dict([(id, {roundup_common.EXTERNAL_SEQUENCE_ID_KEY: sequenceIdToSequenceDataMap[id][roundup_common.EXTERNAL_SEQUENCE_ID_KEY],
                                   roundup_common.GENOME_ID_KEY: sequenceIdToSequenceDataMap[id][roundup_common.GENOME_ID_KEY]})
                             for id in sequenceIdToSequenceDataMap])
        if gene_name:
            tableDesc['has_gene_names'] = True
            for id in sequenceIdToSequenceDataMap:
                seqIdDataMap[id][roundup_common.GENE_NAME_KEY] = sequenceIdToSequenceDataMap[id][roundup_common.GENE_NAME_KEY]
        if go_term:
            tableDesc['has_go_terms'] = True
            (sequenceIdToTermsMap, termMap) = roundup_db.getSequenceIdToTermsMap(sequenceIds, conn=conn)
            for id in sequenceIdToSequenceDataMap:
                seqIdDataMap[id][roundup_common.TERMS_KEY] = sequenceIdToTermsMap.get(id, [])
            tableDesc['term_map'] = termMap
        tableDesc['seq_id_to_data_map'] = seqIdDataMap
        tableDesc['genome_id_to_genome_map'] = genomeIdToGenome
    if outputPath:
        util.dumpObject(tableDesc, outputPath)
        return None
    else:
        return tableDesc



def main():
    pass

if __name__ == '__main__':
    try:
        main()
    except:
        logging.exception('Error.')
        raise


# last line fix for emacs python mode bug -- do not cross
