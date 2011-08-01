'''
Module for loading a dataset into the database.

loadDatabase():  Drops and creates and loads the genomes, divergences, evalues, sequence, and sequence_to_go_terms tables by writing temp files that are loaded with LOAD DATA INFILE.
initLoadOrthDatas(): Drops and creates the results table.  Also drops and creates the dones table, which tracks what orthologs files have been loaded.
loadOrthDatas():  Loads orthologs into the results table.  uses INSERT INTO.  LOAD DATA INFILE not used for a few reasons:
 - because compressed results (how they are stored in the db) do not fit on a single line, so they do not fit into the LOAD DATA INFILE schema easily (one row per line).
  I want them compressed to save space in the db and network transfer time (though that might not be an issue).
 - it takes a long time to load results and if the job is suspended on lsf, the db connection will be load, causing the load job to fail.

bad?: Currently knows implementation details of roundup_db.  Most of this code could be in roundup_db, but I do not want roundup_db to depend on roundup_dataset.
'''


import os
import itertools

import roundup_common
import roundup_dataset
import roundup_db
import workflow
import nested
import orthologs


#################################
# LOADING DATASET INTO DATABASE
#################################


def loadDatabase(ds, dropCreate=True, writeLookups=True, writeSeqs=True, readSeqsMetadata=True, loadTables=True):
    '''
    Drop and create the genomes, divergences, evalues, sequence, and sequence_to_go_terms tables
    Write files for each table that can be loaded with LOAD DATA INFILE.
    Why use LOAD DATA INFILE?  Because it is very fast relative to insert.  a discussion of insertion speed: http://dev.mysql.com/doc/refman/5.1/en/insert-speed.html
    Load the files into the tables.
    The flags are for use during testing and debugging, when you do not want to spend the time required to, e.g. read in the sequence metadata.
    '''
    
    version = roundup_dataset.getDatasetId(ds)

    if dropCreate:
        print 'dropping and creating tables'
        roundup_db.dropVersion(version)
        roundup_db.createVersion(version)

    print 'creating unique ids for genes, genomes, divs, and evalues'
    print '...loading genomeToGenes'
    genomeToGenes = roundup_dataset.getGenomeToGenes(ds)
    print '...creating ids'
    genomes = roundup_dataset.getGenomes(ds)
    genomeToId = dict([(genome, i) for i, genome in enumerate(genomes, 1)])
    # only use genes from genomes used by dataset, not all genomes.
    # sometimes a dataset does not compute orthologs for all genomes in the genomes dir, e.g. if you are running a test computation.
    genes = list(itertools.chain.from_iterable([genomeToGenes[genome] for genome in genomes])) 
    geneToId = dict([(gene, i) for i, gene in enumerate(genes, 1)])
    divs = roundup_common.DIVERGENCES
    divToId = dict([(div, i) for i, div in enumerate(divs, 1)])
    evalues = roundup_common.EVALUES
    evalueToId = dict([(evalue, i) for i, evalue in enumerate(evalues, 1)])

    if readSeqsMetadata:
        print 'reading in metadata about genomes, terms, and genes'
        print '...genomeToGenes'
        genomeToGenes = roundup_dataset.getGenomeToGenes(ds)
        print '...geneToName'
        geneToName = roundup_dataset.getGeneToName(ds)
        print '...geneToGenome'
        geneToGenome = roundup_dataset.getGeneToGenome(ds)
        print '...geneToGoTerms'
        geneToGoTerms = roundup_dataset.getGeneToGoTerms(ds)
        print '...geneToGeneIds'
        geneToGeneIds = roundup_dataset.getGeneToGeneIds(ds)
        print '...termToData'
        termToData = roundup_dataset.getTermToData(ds)



    with nested.NestedTempDir() as tmpDir:
        genomesFile = os.path.join(tmpDir, 'genomes.txt')
        divsFile = os.path.join(tmpDir, 'divs.txt')
        evaluesFile = os.path.join(tmpDir, 'evalues.txt')
        seqsFile = os.path.join(tmpDir, 'seqs.txt')
        seqToGoTermsFile = os.path.join(tmpDir, 'seqToGoTerms.txt')

        if writeLookups:
            print 'writing lookup tables'
            genomeToName = roundup_dataset.getGenomeToName(ds)
            genomeToTaxon = roundup_dataset.getGenomeToTaxon(ds)
            genomeToCount = roundup_dataset.getGenomeToCount(ds)
            taxonToData = roundup_dataset.getTaxonToData(ds)
            writeGenomesTable(genomes, genomeToId, genomeToName, genomeToTaxon, genomeToCount, taxonToData, genomesFile)
            writeLookupTable(divs, divToId, divsFile)
            writeLookupTable(evalues, evalueToId, evaluesFile)

        if writeSeqs:
            print 'writing seqToGoTerms table'
            writeSeqToGoTermsTable(genes, geneToId, geneToGoTerms, termToData, seqToGoTermsFile)
            print 'writing seqs table'
            writeSeqsTable(genes, geneToId, geneToName, geneToGeneIds, geneToGenome, genomeToId, seqsFile)

        if loadTables:
            print 'loading tables'
            roundup_db.loadVersion(version, genomesFile, divsFile, evaluesFile, seqsFile, seqToGoTermsFile)


def makeIds(ds):
    print 'creating unique ids for genes, genomes, divs, and evalues'
    print '...loading genomeToGenes'
    genomeToGenes = roundup_dataset.getGenomeToGenes(ds)
    print '...creating ids'
    genomes = roundup_dataset.getGenomes(ds)
    genomeToId = dict([(genome, i) for i, genome in enumerate(genomes, 1)])
    # only use genes from genomes used by dataset, not all genomes.
    # sometimes a dataset does not compute orthologs for all genomes in the genomes dir, e.g. if you are running a test computation.
    genes = list(itertools.chain.from_iterable([genomeToGenes[genome] for genome in genomes])) 
    geneToId = dict([(gene, i) for i, gene in enumerate(genes, 1)])
    divs = roundup_common.DIVERGENCES
    divToId = dict([(div, i) for i, div in enumerate(divs, 1)])
    evalues = roundup_common.EVALUES
    evalueToId = dict([(evalue, i) for i, evalue in enumerate(evalues, 1)])
    return genomes, genomeToId, genes, geneToId, divs, divToId, evalues, evalueToId


def writeSeqToGoTermsTable(genes, geneToId, geneToGoTerms, termToData, seqToGoTermsFile):
    '''
    `id` int(10) unsigned NOT NULL auto_increment,
    `sequence_id` int(10) unsigned NOT NULL,
    `go_term_acc` varchar(255) NOT NULL,
    `go_term_name` varchar(255) NOT NULL,
    `go_term_type` varchar(55) NOT NULL,
    '''
    with open(seqToGoTermsFile, 'w') as fh:
        i = 0 # unique row id
        for gene in genes:
            for term in geneToGoTerms[gene]:
                if term in termToData: # terms can be missing b/c term to data only contains biological_process, not molecular_function terms.
                    i += 1
                    termName = termToData[term][roundup_dataset.NAME]
                    termType = termToData[term][roundup_dataset.TYPE]
                    fh.write('{}\t{}\t{}\t{}\t{}\n'.format(i, geneToId[gene], term, termName, termType))


def writeSeqsTable(genes, geneToId, geneToName, geneToGeneIds, geneToGenome, genomeToId, seqsFile):
    '''
    `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
    `external_sequence_id` varchar(100) NOT NULL,
    `genome_id` smallint(5) unsigned NOT NULL,
    `gene_name` varchar(20) DEFAULT NULL,
    `gene_id` int(11) DEFAULT NULL,      
    '''
    with open(seqsFile, 'w') as fh:
        for gene in genes:
            genomeId = genomeToId[geneToGenome[gene]]
            geneName = geneToName[gene]
            geneIds = geneToGeneIds[gene]
            geneId = geneIds[0] if geneIds else '\\N' # only use the first ncbi gene id if there are several. if no ids, use the mysql NULL character.
            fh.write('{}\t{}\t{}\t{}\t{}\n'.format(geneToId[gene], gene, genomeId, geneName, geneId))
                 

def writeGenomesTable(genomes, genomeToId, genomeToName, genomeToTaxon, genomeToCount, taxonToData, genomesFile):
    '''
    id smallint unsigned auto_increment primary key,
    acc varchar(100) NOT NULL,
    name varchar(255) NOT NULL,
    ncbi_taxon varchar(20) NOT NULL,
    taxon_category_code varchar(10) NOT NULL,
    taxon_category_name varchar(255) NOT NULL,
    taxon_division_code varchar(10) NOT NULL,
    taxon_division_name varchar(255) NOT NULL,
    num_seqs int NOT NULL,
    '''
    with open(genomesFile, 'w') as fh:
        for genome in genomes:
            gid = genomeToId[genome]
            name = genomeToName[genome]
            taxon = genomeToTaxon[genome]
            catCode = taxonToData[taxon][roundup_dataset.CAT_CODE]
            catName = taxonToData[taxon][roundup_dataset.CAT_NAME]
            divCode = taxonToData[taxon][roundup_dataset.DIV_CODE]
            divName = taxonToData[taxon][roundup_dataset.DIV_NAME]
            numSeqs = genomeToCount[genome]
            fh.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(gid, genome, name, taxon, catCode, catName, divCode, divName, numSeqs))
    
            
def writeLookupTable(items, itemToId, itemsFile):
    '''
    write a file appropriate for loading into mysql.  each line contains a tab-separated id and item.
    '''
    with open(itemsFile, 'w') as fh:
        for item in items:
            fh.write('{}\t{}\n'.format(itemToId[item], item))
    

########################
# LOAD ORTHDATAS FUNCTIONS
########################

def cleanOrthDatasDones(ds):
    version = roundup_dataset.getDatasetId(ds)
    ns = 'roundup_load_{}'.format(version)
    workflow.dropDones(ns)

    
def initLoadOrthDatas(ds):
    version = roundup_dataset.getDatasetId(ds)
    print 'dropping and creating results table'
    roundup_db.dropVersionResults(version)
    roundup_db.createVersionResults(version)
    print 'resetting dones'
    ns = 'roundup_load_{}'.format(version)
    workflow.resetDones(ns)

    
def loadOrthDatas(ds):
    '''
    load orthDatas serially.  takes a long time.  use dones to resume job if it dies.
    '''
    version = roundup_dataset.getDatasetId(ds)
    ns = 'roundup_{}'.format(version)

    print 'getting ids'
    genomeToId = roundup_db.getGenomeToId(version)
    divToId = roundup_db.getDivergenceToId(version)
    evalueToId = roundup_db.getEvalueToId(version)
    geneToId = roundup_db.getSequenceToId(version)

    print 'loading orthDatas'
    for path in roundup_dataset.getOrthologsFiles(ds):
        if workflow.isDone(ns, path):
            print 'already loaded:', path
        else:
            print 'loading', path
            orthDatasGen = orthologs.orthDatasFromFileGen(path)
            roundup_db.loadVersionResults(version, genomeToId, divToId, evalueToId, geneToId, orthDatasGen)
            workflow.markDone(ns, path)


