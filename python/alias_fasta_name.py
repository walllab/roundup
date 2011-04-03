#!/usr/bin/env python

'''
utilities for aliasing fasta names for use with RoundUp.
For transforming fasta sequences with namelines which
differ from the name lines in a database into fasta sequences
which have the name lines from the database.
'''

import re
import string


PROTEIN = 'protein'
NUCLEOTIDE = 'nucleotide'

# ALIASING: CANDIDA ALBICANS
# example name lines:
# >orf19.1006 Contig19-10083 (379, 2) CDS, reverse complemented, translated using codon table 12  (126 residues)
# aliased to: >orf19.1006
# >CaalfMp01 COX2 CGDID:CAF0007359 Ca19-mtDNA (3275, 4063) CDS, translated using codon table 4 (262 residues)
# aliased to: >CaalfMp01
candidaNameLineRE = re.compile('^>(orf|Caal)\S+', re.IGNORECASE)

def isCandidaNameLine(line):
    '''
    line: fasta name line, with '>'
    '''
    return bool(candidaNameLineRE.search(line))

def candidaAlias(line):
    '''
    line: fasta name line, with '>'
    '''
    m = candidaNameLineRE.search(line)
    if m:
        return m.group(0)
    else:
        return None


# TIGR GENOMES
# example genome location: ftp://ftp.tigr.org/pub/data/Eukaryotic_Projects/o_sativa/annotation_dbs/pseudomolecules/version_4.0/all_chrs/all.pep
# example name lines:
# >LOC_Os01g01010.1|11971.m06748|protein RabGAP/TBC domain-containing protein, putative, expressed
# >LOC_Os01g01010.2|11971.m42814|protein RabGAP/TBC domain-containing protein, putative, expressed
# >LOC_Os01g01020.1|11971.m06749|protein cytochrome P450 family protein, putative
# example aliases:
# >TIGR_Os01g01010.1
# >TIGR_Os01g01010.2
# >TIGR_Os01g01020.1

tigrRE = re.compile('^>LOC_([^|]+)\|[0-9]+\.m[0-9]+\|.*')

def isTIGRNameLine(line):
    '''
    line: a tigr genome project name line, with '>'
    return True if the line matches the pattern of a tigr genome project name line.
    return False otherwise
    '''
    return bool(tigrRE.search(line))

def tigrAlias(line):
    '''
    line: a tigr genome project name line, with '>'
    return name line of the 'id' in the name line or none if line is not well-formed
    '''
    m = tigrRE.search(line)
    if m:
        return '>TIGR_' + ''.join(m.groups())
    else:
        return None




# JGI-PSF GENOMES
# genomes located at: e.g. ftp://ftp.jgi-psf.org/pub/JGI_data/Nematostella_vectensis/v1.0/annotation/proteins.Nemve1FilteredModels1.fasta.gz
# example name lines
# >jgi|Nemve1|18|gw.48.1.1
# >jgi|Nemve1|248885|estExt_fgenesh1_pg.C_76820001
# example aliases:
# >jgiNemve1248885

jgiRE = re.compile('^>(jgi)\|([^|]+)\|([0-9]+)\|.*')

def isJGINameLine(line):
    '''
    line: a jgi genome project name line, with '>'
    return True if the line matches the pattern of a jgi genome project name line.
    return False otherwise
    '''
    return bool(jgiRE.search(line))

def jgiAlias(line):
    '''
    line: a jgi genome project name line, with '>'
    return name line of the 'id' in the name line or none if line is not well-formed
    '''
    m = jgiRE.search(line)
    if m:
        return '>' + ''.join(m.groups())
    else:
        return None


# STANFORD YEAST GENOMES
# genomes located at: ftp://genome-ftp.stanford.edu/pub/yeast/sequence/fungal_genomes/
# fasta files at:
# ftp://genome-ftp.stanford.edu/pub/yeast/sequence/fungal_genomes/*/[WashU|MIT]/orf_protein/orf_trans.fasta.gz
# 6 species:
# S_bayanus, S_castellii, S_kluyveri, S_kudriavzevii, S_mikatae, S_paradoxus
# examples of stanford yeast genome project name lines from each species:
# >ORFP:24884 YPRCdelta24, Contig c301 81115-81443
# >ORFP:25548 , Contig c301 73540-73621
# >ORFP:Skud_Contig1052.2 YER161C, Contig c1052 1004-2005
# >ORFP:Sklu_Contig2423.11 YLR403W, Contig c2423 20879-22858 reverse complement
# >ORFP:Scas_Contig489.4 YBR291C, Contig c489 7920-8813
# >ORFP:Smik_Contig2239.1 YNL142W, Contig c2239 283-1782 reverse complement
# >ORFP:Sbay_Contig453.5 YMR090W, Contig c453 6144-6827 reverse complement

stanfordYeastRE = re.compile('^>ORFP:([^0-9,]*)([0-9.]+)[^,]*,.*')

def stanfordAlias(line):
    '''
    line: a stanford yeast genome project name line, with '>'
    return name line of the 'id' in the name line or none if line is not well-formed
    '''
    m = stanfordYeastRE.search(line)
    if m:
        if m.groups()[0]:
            alias = re.sub('Contig', '', ''.join(m.groups()[0:2]))
        else:
            alias = 'Spar_'+m.groups()[1]
        return '>'+alias
    else:
        return None


def isStanfordNameLine(line):
    '''
    line: a stanford yeast genome project name line, with '>'
    return True if the line matches the pattern of a stanford yeast genome project name line.
    return False otherwise
    '''
    return bool(stanfordYeastRE.search(line))

# specific for ensembl dbs
# Fugu_rubripes.aa:
# >NEWSINFRUP00000174366 pep:novel scaffold:FUGU4:scaffold_1:154772:156167:1 gene:NEWSINFRUG00000124912 transcript:NEWSINFRUT00000177763
# Danio_rerio.aa:
# >ENSDARP00000017955 pep:novel chromosome:ZFISH5:9:212642:250841:1 gene:ENSDARG00000019409 transcript:ENSDART00000012641
# Tetraodon_nigroviridis.aa:
# >GSTENP00010356001 pep:known chromosome:TETRAODON7:Un_random:20050:23432:1 gene:GSTENG00010356001 transcript:GSTENT00010356001
# Takifugu_rubripes.aa:
# >SINFRUP00000181809 pep:novel scaffold:FUGU4:scaffold_15515:707:1148:-1 gene:SINFRUG00000162338 transcript:SINFRUT00000182379


ensemblre = re.compile('^>(ENS|NEWSIN|GS|SIN)')

def ensemblalias(line):
    '''
    line: fasta name line, with '>'
    '''
    m = ensemblre.search(line)
    if m:
 	alias = string.split(line)[0]
        return alias
    else:
        return None


def isensembl(line):
    '''
    line: fasta name line, with '>'
    '''
    return bool(ensemblre.search(line))


def aliasName(nameLine):
    '''
    nameLine: fasta name line, with '>'
    Generate name aliases for use in roundup database formatting.
    return the alias of nameLine, with '>'
    e.g.: '>gi|10047090|ref|NP_055147.1| small muscle protein' -> '>10047090'
    e.g.: '>gi|54309266|ref|YP_130286.1| putative UDP-glucose 4-epimerase gi|28899174|ref|NP_798779.1| UDP-glucose 4-epimerase [Photobacterium profundum SS9]'
      -> '>54309266'
    '''
    # try for a stanford alias first
    if isStanfordNameLine(nameLine):
        alias = stanfordAlias(nameLine)
        if not alias:
            raise Exception('[Error] stanford yeast genome aliasing.  nameLine='+str(nameLine)+' alias='+str(alias))
    elif isCandidaNameLine(nameLine):
        alias = candidaAlias(nameLine)
        if not alias:
            raise Exception('[Error] candida aliasing.  nameLine='+str(nameLine)+' alias='+str(alias))
    elif isensembl(nameLine):
	alias = ensemblalias(nameLine)
        if not alias:
	    raise Exception('[Error] ensembl aliasing.  nameLine='+str(nameLine)+' alias='+str(alias))
    elif isJGINameLine(nameLine):
        alias = jgiAlias(nameLine)
        if not alias:
	    raise Exception('[Error] jgi aliasing.  nameLine='+str(nameLine)+' alias='+str(alias))            
    elif isTIGRNameLine(nameLine):
        alias = tigrAlias(nameLine)
        if not alias:
	    raise Exception('[Error] tigr aliasing.  nameLine='+str(nameLine)+' alias='+str(alias))            
    # otherwise use gi number as alias
    else:
        alias = nameLine.strip()[1:] # remove '>'
        alias = re.sub('.*?gi\|','', alias, 1) # only nullify up to the first gi|, in case there are multiple gi| in the nameline.
        alias = re.sub('\|.*', '', alias)
        alias = '>'+alias.strip().split()[0]

    # alias is a fasta name line, starting with '>'.  add lcl| if it is not already there.  this is to comply with ncbi formatting rules that fastacmd wants.
    # lcl is ncbi-speak for local namespace, I think.
    if not alias.startswith('>lcl|'):
        alias = '>lcl|' + alias[1:]
    return alias

                            
def main():
    pass

if __name__ == '__main__':
    main()
