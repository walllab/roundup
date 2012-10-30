#useful program wrappers that are employed in the implementation of the RSD algorithm
import os
import sys
import string
import re
import shutil

import nested
import roundup_common
import util
import fasta


def findSeqIdWithFasta(fastaSeq, subjectIndexPath):
    ''' return first hit '''
    try:
        path = nested.makeTempPath()
        util.writeToFile(fastaSeq, path)
        cmd = 'blastp -outfmt 6 -query %s -db %s'%(path, subjectIndexPath)
        results = util.run(cmd, shell=True)
    finally:
        os.remove(path)        
    hitId = None
    for line in results.splitlines():
        # example line: foo sp|P39709|SEO1_YEAST 100.00 40 0 0 1 40 1 40 3e-1884.7
        # the second field is from the hit nameline.
        hitId = fasta.idFromName(line.split()[1])
        break # grab the first hit
    return hitId


def getFastaForId(id, indexPath):
    '''
    assumes fastacmd executable is in PATH
    indexPath: location of blast-formatted index files.  e.g. /groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa
    e.g. BioUtilities.getFastaForId("4504291", "/groups/rodeo/roundup/genomes/current/Homo_sapiens.aa/Homo_sapiens.aa")
    >lcl|4504291 unnamed protein product
    MARTKQTARKSTGGKAPRKQLATKAARKSAPATGGVKKPHRYRPGTVALREIRRYQKSTELLIRKLPFQRLVREIAQDFK
    TDLRFQSSAVMALQEACEAYLVGLFEDTNLCAIHAKRVTIMPKDIQLARRIRGERA
    
    '''
    # return util.run('fastacmd -d %s -s "lcl|%s"'%(indexPath, id), shell=True)
    return util.run('blastdbcmd -db %s -entry "%s"'%(indexPath, id), shell=True)

