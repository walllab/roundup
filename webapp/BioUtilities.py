#useful program wrappers that are employed in the implementation of the RSD algorithm
import os
import sys
import string
import re
import shutil

import nested
import roundup_common
import execute
import util
import fasta


def findSeqIdWithFasta(fasta, genome):
    ''' return first hit '''
    subjectIndexPath = roundup_common.fastaFileForDbPath(roundup_common.makeDbPath(genome))
    try:
        path = nested.makeTempPath()
        util.writeToFile(fasta, path)
        cmd = 'blastp -outfmt 6 -query %s -db %s'%(path, subjectIndexPath)
        results = execute.run(cmd)
    finally:
        os.remove(path)        
    hitName = None
    for line in results.splitlines():
        splits = line.split()
        hitName = splits[1] # lcl| is already removed.  go figure.  that is just how ncbi does it.
        break
    return hitName


def getFastaForId(id, indexPath):
    '''
    assumes fastacmd executable is in PATH
    indexPath: location of blast-formatted index files.  e.g. /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa
    e.g. BioUtilities.getFastaForId("4504291", "/groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa")
    >lcl|4504291 unnamed protein product
    MARTKQTARKSTGGKAPRKQLATKAARKSAPATGGVKKPHRYRPGTVALREIRRYQKSTELLIRKLPFQRLVREIAQDFK
    TDLRFQSSAVMALQEACEAYLVGLFEDTNLCAIHAKRVTIMPKDIQLARRIRGERA
    
    '''
    # return execute.run('fastacmd -d %s -s "lcl|%s"'%(indexPath, id))
    return execute.run('blastdbcmd -db %s -entry "lcl|%s"'%(indexPath, id))

