def clustalToPhylip(alignment):
    '''
    optimized for roundup.  makes some assumptions about alignment to avoid using regular expressions.
    replaces clustal2phylip perl script, to increase conversion speed by not executing an external process.

    Phylip format: http://www.clfs.umd.edu/labs/delwiche/MSyst/lec/phylip.html
    The first line is the number of taxa and length of the sequences
    The rest of the lines: the first 10 characters (exactly!) are the taxon name, the rest of the line is the sequence.
    '''
    # print 'alignment', alignment
    START_STATE = 1
    PARSE_STATE = 2
    PHYLIP_NAME_LEN = 10
    PHYLIP_TAXON_STR = '{: <'+str(PHYLIP_NAME_LEN)+'}{}\n' # used to format phylip taxon data lines.
    state = START_STATE
    seqIds = []
    seqIdToSeq = {}
    for line in alignment.splitlines():
        if state == START_STATE:
            if line.upper().find('CLUSTAL') != -1:
                state = PARSE_STATE
            else:
                pass
        else: # state == PARSE_STATE:
            if line.find('Clustal Tree') != -1:
                break
            if not line or line[0] == ' ': # lines of interest start with a sequence identifier
                continue
            splits = line.split() # lines of interest have two tokens: a sequence id, and sequence characters.
            if len(splits) == 2:
                seqId = splits[0][:PHYLIP_NAME_LEN]
                if seqId not in seqIdToSeq:
                    seqIds.append(seqId)
                    seqIdToSeq[seqId] = ''
                seqIdToSeq[seqId] += splits[1]
    phylip = ''
    # all sequences must be the same length.
    phylip += '%s %s\n'%(len(seqIds), len(seqIdToSeq[seqIds[0]]))
    for seqId in seqIds:
        # right-pad the seqId with spaces.  Phylip taxon names are exactly 10 chars long (spaces OK for shorter names)
        phylip += PHYLIP_TAXON_STR.format(seqId, seqIdToSeq[seqId]) 
    return phylip


def runClustal(fasta, path):
    '''
    fasta: fasta formatted sequences to be aligned.
    path: working directory where fasta will be written and clustal will write output files.
    runs clustalw
    Returns: alignment
    '''
    clustalFastaPath = os.path.join(path, CLUSTAL_INPUT_FILENAME)
    clustalAlignmentPath = os.path.join(path, CLUSTAL_ALIGNMENT_FILENAME)
    util.writeToFile(fasta, clustalFastaPath)
    try:
        subprocess.check_call('clustalw -infile=%s -outfile=%s 2>&1 >/dev/null'%(clustalFastaPath, clustalAlignmentPath), shell=True)
    except Exception:
        logging.exception('runClustal Error:  clustalFastaPath data = %s'%open(clustalFastaPath).read())
        raise
    alignment = util.readFromFile(clustalAlignmentPath)
    return alignment


