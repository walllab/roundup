#useful program wrappers that are employed in the implementation of the RSD algorithm
import os
import sys
import string
import re
import shutil


import Utility

import nested
import roundup_common
import execute
import util
import fasta


def getIdsForDbPath(dbPath):
    '''
    dbPath: path to a genome directory, aka a "dbPath".  e.g. /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa
    '''
    fastaPath = roundup_common.fastaFileForDbPath(dbPath)
    return getIdsForFastaPath(fastaPath)


def getIdsForFastaPath(fastaPath):
    '''
    fastaPath: path to a genome fasta file
    '''
    ids = []
    with open(fastaPath) as fh:
        for nameline, seq in fasta.readFastaIter(fh, ignoreParseError=True):
            ids.append(convertNamelineToId(nameline)) # e.g. >lcl|12345 becomes 12345
    return ids


def getFastaForId(id, indexPath):
    '''
    indexPath: location of blast-formatted index files.  e.g. /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa
    e.g. BioUtilities.getFastaForId("4504291", "/groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa")
    >lcl|4504291 unnamed protein product
    MARTKQTARKSTGGKAPRKQLATKAARKSAPATGGVKKPHRYRPGTVALREIRRYQKSTELLIRKLPFQRLVREIAQDFK
    TDLRFQSSAVMALQEACEAYLVGLFEDTNLCAIHAKRVTIMPKDIQLARRIRGERA
    '''
    return execute.run('/usr/bin/fastacmd -d %s -s "lcl|%s"'%(indexPath, id))


def convertIdToNameline(seqId):
    return '>lcl|'+seqId


def convertNamelineToId(nameline):
    return nameline.replace('>lcl|', '')


def getFastaForIdOld(id, dbPath):
    return execute.run("/opt/blast2/xdget -p %s '%s'" % (dbPath, id))
    
    
def convertNamelineToIdOld(nameline):
    return nameline.replace('>', '')


def getSeqForId(id, indexPath):
    '''
    id: id used to find sequence in db.  like '12345', not 'lcl|12345'.
    indexPath: location and name of blast index files for genome. e.g. '/groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa'
    uses fastacmd to lookup fasta sequence in a database formatted for ncbi blast.
    '''
    # retrieve hit sequence using fastacmd
    fasta = getFastaForId(id, indexPath)
    seq = re.sub('(>)(.+)(\n)', '', fasta)
    seq = re.sub('\n', '', seq)
    return seq


def newlineConvert( str ):
    """
    newlineConvert( string ) returns a string after converting 
    carriage returns or newline carriage return combinations to newlines
    for ClustalW file handling
    """
    str = re.sub( "\r\n", "\n", str )
    str = re.sub( "\n\r", "\n", str )
    str = re.sub( "\r", "\n", str )
    return str


def blast(prog,lib,seq,tempDir=None):
    '''
    Objective: Run blast program prog against library lib with sequence 'seq'
    (fasta). 
    Arguments:
        prog    Blast program name
        lib     library against which to search
        seq     the sequence to search (fasta or raw format)
        path    (optional) path to the search library.
    Returns:
        (1,result)  on success
        (0,error)   on failure
    '''
    
    results = ''
    # If sequence isn't fasta... it needs to be...
    headerposn = re.match('^>.*[\n\015]',seq )
    if headerposn == None:
        seq = ">test\n%s" % seq

    #
    # Run A Blast Job
    #
    query = nested.makeTempPath(dir=tempDir, nesting=0)
    fo = open(query, 'w+b')
    fo.write(seq)
    fo.flush()
    fo.close()

    try:
        cmd = "%s %s %s  " % (prog, lib, query)
        return execute.run(cmd)
    finally:
        os.unlink(query)

    # (ok, result) = Utility.runOrReportFailure("%s %s %s  " % (prog, lib, query))
    # os.unlink(query)
    # return (ok, result)


def parseBlastSummary(text, evalue=None):    
    '''
        Objective: Given a blast result as text, return a list of the top hits
        Arguments: text    - string of blast result
        evalue: float evalue threshold.  Stop parsing when prob >= evalue.  If None, parse everything.
        Returns: blastHits   - list (accNo, name, frame, score, prob, N)
    '''
    lines = string.splitfields(text, '\n')
    stage = 0
    start = 1
    blastHits = [] 
    findblast = 1
    blast = None
    for line in lines:
        # get rid of html if there is any
        line =  re.sub('<[^>]*>','',line)
        #
        # Found first line of importance
        if stage == 0:
            if string.find(line, 'Sequences producing') > -1:
                stage = 1
            if findblast: 
                if line[:6] ==  'BLASTX':
                    blast = 'BLASTX'
                    findblast = 0
                if line[:6] ==  'BLASTN':
                    blast = 'BLASTN'
                    findblast = 0
                if line[:6] ==  'BLASTP':
                    blast = 'BLASTP'
                    findblast = 0
                if line[:7] ==  'TBLASTN':
                    blast = 'TBLASTN'
                    findblast = 0
                if line[:7] ==  'TBLASTX':
                    blast = 'TBLASTX'
                    findbst = 0
                
        #
        # Look for blank lines after in the description area.
        elif stage == 1:
            # get rid of blankline
            if start and (len(string.strip(line)) == 0):
                start = 0
            else:
                if len(string.strip(line)) == 0:
                    #
                    # end of stage 1 
                    #
                    stage = 2
                else:
                
                    data = string.split(line) 
                    accNo = data[0]

                    # this works with regular accessions (NCBI), but does not work well with personalized accessions.
                    # if string.find(accNo, 'gi') > -1 or string.find(accNo, 'sp') > -1 or string.find(accNo, 'ex|') > -1 :
                    #    if string.find(accNo[4:], '|') > -1:
                    #        pipe = string.find(accNo[4:], '|')
                    #        accNo = accNo[:4+pipe]
                    try:
                        prob = float(data[-2])
                    except ValueError:
                        #
                        # Hack to get around cases where the number is too
                        # small for python's atof code to work
                        # Don't do this by default - probably much slower.
                        prob = eval(data[-2])

                    # stop parsing when prob meets or exceeds evalue
                    if evalue != None:
                        if prob >= evalue:
                            break
                        
                    if blast == None:
                        return None
                    else:
                        blastHits.append( (accNo, prob) )
    
        elif stage == 2:
            break
                
    return blastHits

def parseBlastSummaryOld(text, evalue=None):    
    '''
        Objective: Given a blast result as text, return a list of the top hits
        Arguments: text    - string of blast result
        evalue: float evalue threshold.  Stop parsing when prob >= evalue.  If None, parse everything.
        Returns: blastHits   - list (accNo, name, frame, score, prob, N)
    '''
    lines = string.splitfields(text, '\n')
    stage = 0
    start = 1
    blastHits = [] 
    findblast = 1
    blast = None
    for line in lines:
        # get rid of html if there is any
        line =  re.sub('<[^>]*>','',line)
        #
        # Found first line of importance
        if stage == 0:
            if string.find(line, 'Sequences producing') > -1:
                stage = 1
            if findblast: 
                if line[:6] ==  'BLASTX':
                    blast = 'BLASTX'
                    findblast = 0
                if line[:6] ==  'BLASTN':
                    blast = 'BLASTN'
                    findblast = 0
                if line[:6] ==  'BLASTP':
                    blast = 'BLASTP'
                    findblast = 0
                if line[:7] ==  'TBLASTN':
                    blast = 'TBLASTN'
                    findblast = 0
                if line[:7] ==  'TBLASTX':
                    blast = 'TBLASTX'
                    findbst = 0
                
        #
        # Look for blank lines after in the description area.
        elif stage == 1:
            # get rid of blankline
            if start and (len(string.strip(line)) == 0):
                start = 0
            else:
                if len(string.strip(line)) == 0:
                    #
                    # end of stage 1 
                    #
                    stage = 2
                else:
                
                    data = string.split(line) 
                    accNo = data[0]

                    # this works with regular accessions (NCBI), but does not work well with personalized accessions.
                    # if string.find(accNo, 'gi') > -1 or string.find(accNo, 'sp') > -1 or string.find(accNo, 'ex|') > -1 :
                    #    if string.find(accNo[4:], '|') > -1:
                    #        pipe = string.find(accNo[4:], '|')
                    #        accNo = accNo[:4+pipe]
                    try:
                        N = int(data[-1])
                    except Exception:
                        # print "Weird line '%s'" % `data`
                        return
                    try:
                        prob = float(data[-2])
                    except ValueError:
                        #
                        # Hack to get around cases where the number is too
                        # small for python's atof code to work
                        # Don't do this by default - probably much slower.
                        prob = eval(data[-2])

                    # stop parsing when prob meets or exceeds evalue
                    if evalue != None:
                        if prob >= evalue:
                            break
                        
                    score = int(data[-3])
                    if blast == None:
                        return None
                    elif blast == "BLASTX" or blast == "TBLASTN" or blast == 'TBLASTX':
                        frame = data[-4]
                        name = string.join(data[1:-4])
                        blastHits.append( (accNo, name, frame, score, prob, N) )
                    else:
                        name = string.join(data[1:-3])
                        blastHits.append( (accNo, name, 'N/A', score, prob, N) )
    
        elif stage == 2:
            break
                
    return blastHits



#
#XDformat program wrapper
#
#
def runXDformat(seq_type, db, outputDbName=None):
	if outputDbName != None:
		outputOption = '-o '+outputDbName
	else:
		outputOption = ''
	# -k option skips 'J' amino acid codes which xdformat does not recognize as valid.  J stands for (leucine or isoleucine): http://en.wikipedia.org/wiki/Amino_acid
	cmd = 'xdformat -k -'+seq_type+' -I '+outputOption+' '+db
        return execute.run(cmd)


def runParsePaml(output):
	"""
	runParsePaml takes a paml standard output file and parses its important elements like dn/ds
        Arguments: paml output file
        Returns: (1, parsed paml output) or (0,error message)"""

        # Make temp directory
	tmpdir = nested.makeTempDir(dir=roundup_common.LOCAL_DIR, nesting=0) # scratch has more space then tmp on cluster nodes

        # Write clustal alignment to file in temp directory
        outf = open( "%s/output" % tmpdir, "w" )
        outf.write( output )
        outf.close()

        # cd to temp directory and run clustal2phylip
        ( ok, output ) = Utility.runOrReportFailure( "cd %s; perl parsepaml.pl < alignment" % tmpdir )

        # clean up
        shutil.rmtree(tmpdir)

        # return
        return ( ok, output )

def rundnaml(phylipfile):

	"""
	will take phylip file as argument (could be created using runClustal2Phylip( alignment ) included in this module.
	runs phylip's dnaml.  This program Estimates phylogenies from nucleotide sequences by maximum likelihood. The model employed allows for unequal expected frequencies of the four nucleotides, for unequal rates of transitions and transversions, and for different (prespecified) rates of change in different categories of sites, with the program inferring which sites have which rates. default parameters are :?? 
	"""

	treestr = ''
        ok = 0
	# Make temp directory
	tmpdir = nested.makeTempDir(dir=roundup_common.LOCAL_DIR) # scratch has more space then tmp on cluster nodes

        try:
            # Write phylip format alignment to file in temp directory.
            # protdist assumes file is called "infile".
            outf = open( "%s/infile" % tmpdir, "w" )
            outf.write( phylipfile )
            outf.close()
	
            # Run dnaml on the alignment.
            ( ok, output ) = Utility.runOrReportFailure( "cd %s; echo 'y' | dnaml" % tmpdir )
            
            # If successful, read output.
            if ok:
		# Examine output for error or warning messages. If any, the 
		# matrix is unsuitable for phylogenetic tree construction,
		# so return the diagnostic messages.
		if string.find( output, "ERROR" ) >= 0 or not string.find( output, "WARNING" ) >= 0:
                    ok = 0
		else:
                    output = util.readFromFile("%s/outfile" % tmpdir)
                tree = open("%s/treefile" % tmpdir)
		get_tree = tree.readlines()
		for line in get_tree:
                    treestr += line
        finally:
            shutil.rmtree(tmpdir)
            return ( ok, treestr )


def runPaml_all(path):
        #run codeml!
        return execute.run("cd %s/; echo '0' | codeml" %path)


def paml_GetDistance(path):
	filename = '%s/2AA.t'%path
	
	# adding a pause on the off-chance that the filesystem might be lagging a bit, causing the open() to fail below.
	# I think it is more likely that codeml in runPaml_all() is failing before writing the file.
	if not os.path.isfile(filename):
		import time
		time.sleep(0.5)
		
	rst = open(filename)
	get_rst =  rst.readlines()
        rst.close()
        os.unlink(filename)
        
	if not get_rst:
            raise roundup_common.RoundupException('paml_GetDistances(): no get_rst for path=%s'%(path))
        		
	str = ''
	for line in get_rst[1:]:
		cd1 = string.split(line)
		if not len(cd1) > 1:
			str += "%s "%(string.split(line, '\n')[0])
			continue
		
		if len(cd1) > 1:
			str+="%s %s"%(cd1[0], cd1[1])

	dist = string.split(str)
	return float(dist[2])


