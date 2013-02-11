'''
Code for parsing uniprot files.
'''

import datetime
import re


COMPLETE_PROTEOME_KW = 'Complete proteome'
REFERENCE_PROTEOME_KW = 'Reference proteome'


def parseRelease(path):
    '''
    path: location of reldate.txt file for this UniProtKB release
    returns: the release name, e.g. '2011_06'
    '''
    # release is in the first line of reldate.txt file.
    with open(path) as fh:
        # line e.g: 'UniProt Knowledgebase Release 2011_06 consists of:'
        line = fh.readline()
        match = re.search(r'\b(\d{4}_\d{2})\b', line) # raw string b/c '\b' is the ASCII backspace character.
        if not match:
            raise ValueError('No release found in line: {}'.format(line))
        return match.group(1)


def genDatEntries(path):
    '''
    path: uniprot dat file
    parses a uniprot dat file, yielding data about each entry.
    '''
    # http://web.expasy.org/docs/userman.html is indispensible for parsing Uniprot DAT files

    # regular expressions for parsing dat lines
    # includes 'DE   ' to avoid matching rec names from 'Includes' or 'Contains' lines.
    # See http://web.expasy.org/docs/userman.html#DE_line.
    descRE = re.compile('^DE   RecName: Full=([^;]+)')
    # python -c 'import re; descRE = re.compile("RecName\: Full=([^;]+)"); print descRE.search("DE   RecName: Full=Uncharacterized protein 010R;").groups()'

    # Gene Name is optional.  There can only be one.
    # ORFNames is optional.  There can be one or more.
    nameRE = re.compile('Name=([^;]+)')
    # orfNamesRE = re.compile('ORFNames=([^;,]+)') # match only the first ORF name.
    # python -c "import re; nameRE = re.compile('Name=([^;]+)'); print nameRE.search('GN   Name=GRF7; OrderedLocusNames=At3g02520; ORFNames=F16B3.15;\n').groups()"
    # python -c "import re; orfNamesRE = re.compile('ORFNames=([^;,]+)'); print orfNamesRE.search('GN   Name=BMH1; Synonyms=BMH; ORFNames=CaO19.3014, CaO19.10532;\n').groups()"

    # From http://web.expasy.org/docs/userman.html#DR_line, format of the DR line is:
    # DR   RESOURCE_ABBREVIATION; RESOURCE_IDENTIFIER; OPTIONAL_INFORMATION_1[; OPTIONAL_INFORMATION_2][; OPTIONAL_INFORMATION_3].    
    taxonRE = re.compile('^OX   NCBI_TaxID=([^;]+)')
    # python -c "import re; taxonRE = re.compile('NCBI_TaxID=([^;]+)'); print taxonRE.search('OX   NCBI_TaxID=390236;').group(1)"
    
    surprises = [] # exceptions to my assumptions about DAT format.
    
    # dat file entries have numerous lines describing fields in the entry.
    # an entry always starts with one ID line and ends with one // line.
    # some lines can occur 0 or 1 times, some 0+ times, some 1+ times, some exactly 1 time.
    # take this into account when parsing lines.
    print 'gathering ids in {}...'.format(path), datetime.datetime.now()
    with open(path) as fh:
        inEntry = False
        entryNum = 0 # count entries
        for i, line in enumerate(fh):
            code = line[:2]
            if code == 'ID': # occurs 1 time.
                inEntry = True
                entryNum += 1
                if entryNum % 100000 == 0: print 'entry count:', entryNum

                # initialize entry vars
                fastaNS = '' # namespace for ids used in uniprot fasta files
                entryId = ''
                orgCode = '' # uniprot organism code.  subspecies sometimes share this, e.g. TRYCR.  http://www.uniprot.org/docs/speclist
                acc = '' # uniprot entry primary accession number, used as our sequence id.
                taxon = '' # ncbi taxon id.  should be unique to an organism.
                evidence = ''
                seqVersion = ''
                geneDesc = ''
                geneName = ''
                osLines = []
                complete = False # complete proteome
                reference = False # reference proteome. should be a subset of complete proteomes. http://www.uniprot.org/faq/47
                geneIds = []
                goTerms = []
                seqLines = []
                
                # e.g. ID   1A01_HUMAN              Reviewed;         365 AA.
                # e.g. ID   A1XWB5_9EURY            Unreviewed;       133 AA.
                splits = line.split()
                fastaNS = 'sp' if splits[2] == 'Reviewed;' else 'tr' # namespace of fasta name line for this seq.
                entryId = splits[1]
                orgCode = entryId.split('_')[1]
            elif code == 'AC' and not acc: # occurs 1+ times
                # e.g. AC   Q16653; O00713; O00714; O00715; Q13054; Q13055; Q14855; Q92891;
                # get first accession from first line.
                if not acc:
                    acc = line.split()[1].split(';')[0]
            elif code == 'OX': # occurs exactly one time?
                # e.g. OX   NCBI_TaxID=9606;
                match = taxonRE.search(line)
                if not taxon:
                    taxon = match.group(1) if match else ''
                else:
                    surprises.append('\t'.join(('many_OX_lines',
                                                acc, orgCode, path, i, '')))
            elif code == 'PE': # occurs exactly 1 time?
                # e.g. PE   2: Evidence at transcript level;
                if evidence:
                    surprises.append('\t'.join(('many_PE_lines',
                                                acc, orgCode, path, i, '')))
                evidence = line.split()[1][:-1] # remove trailing colon
            elif code == 'DT': # occurs 3 times?
                # e.g. DT   01-DEC-2001, sequence version 1.
                if 'sequence version' in line:
                    if not seqVersion:
                        seqVersion = line.rsplit(None, 1)[1][:-1] # remove trailing period.
                    else:
                        surprises.append('\t'.join(('many_sequence_version_lines',
                                                    acc, orgCode, path, i, '')))
            elif code == 'DE': # can occur >1 times
                # http://web.expasy.org/docs/userman.html#DE_line
                # e.g. DE   RecName: Full=Uncharacterized protein 002R;
                if not geneDesc and line.startswith('DE   RecName: Full='):
                    match = descRE.search(line)
                    geneDesc = match.group(1) if match else ''
            elif code == 'GN': # can occur >1 times
                if not geneName: # collect first gene name
                    match = nameRE.search(line)
                    geneName = match.group(1) if match else ''
            elif code == 'OS': # can occur >1 times
                # e.g. 1 line: OS   Homo sapiens (Human).
                # or >1 lines: OS   Chlorobaculum parvum (strain NCIB 8327) (Chlorobium vibrioforme subsp.
                #              OS   thiosulfatophilum (strain DSM 263 / NCIB 8327)).
                osLines.append(line[5:].strip()) # remove the 'OS   ' code from the line.
            elif code == 'KW': # occurs 0+ times
                # can be zero or more KW lines, which can have multiple keywords per line
                if COMPLETE_PROTEOME_KW in line: 
                    complete = True
                if REFERENCE_PROTEOME_KW in line:
                    reference = True
            elif code == 'DR': # occurs 0+ times
                # e.g. DR   GO; GO:0006351; P:transcription, DNA-dependent; IEA:UniProtKB-KW.
                # e.g. DR   GeneID; 2947774; -.
                # e.g. DR   RefSeq; YP_654574.1; NC_008187.1.
                if line.startswith('DR   GeneID;'):
                    geneIds.append(line.split("; ")[1])
                elif line.startswith('DR   GO;'):
                    goTerms.append(line.split("; ")[1])
            elif code == '  ': # occurs 1+ times
                # e.g. "     MTMDKSELVQ KAKLAEQAER YDDMAAAMKA VTEQGHELSN EERNLLSVAY KNVVGARRSS\n"
                # remove whitespace b/c uniprot fasta file does not have whitespace and b/c rsd (blast, kalign, codeml) not tested w/ whitespace
                seqLine = ''.join(line.split())
                if seqLine:
                    seqLines.append(seqLine+'\n') # "MTMDKSELVQKAKLAEQAERYDDMAAAMKAVTEQGHELSNEERNLLSVAYKNVVGARRSS\n"
                else:
                    surprises.append('\t'.join(('empty_seq_line',
                                                acc, orgCode, path, i, '')))
            elif code == '//': # occurs 1 time.  end of sequence
                if not inEntry:
                    surprises.append('\t'.join(('end_without_beginning',
                                                acc, orgCode, path, i, '// line with unmatched ID line found.')))
                inEntry == False

                orgName = parseParens(' '.join(osLines))
               
                # construct fasta nameline
                # e.g. >sp|Q197F8|002R_IIV3 Uncharacterized protein 002R OS=Invertebrate iridescent virus 3 GN=IIV3-002R PE=4 SV=1
                # generic: >{source}|{accession}|{entry_id} {gene_desc} OS={organism_name}[ GN={gene_name}] PE={protein_evidence} SV={seq_version}
                nameline = '>{}|{}|{}'
                args = [fastaNS, acc, entryId]
                if geneDesc:
                    nameline += ' {}'
                    args.append(geneDesc)
                if orgName:
                    nameline += ' OS={}'
                    args.append(orgName)
                if geneName:
                    nameline += ' GN={}'
                    args.append(geneName)
                if evidence:
                    nameline += ' PE={}'
                    args.append(evidence)
                if seqVersion:
                    nameline += ' SE={}'
                    args.append(seqVersion)
                # if complete:
                #     nameline += ' KW='+COMPLETE_PROTEOME_KW
                # if reference:
                #     nameline += ' KW='+REFERENCE_PROTEOME_KW
                nameline += '\n'
                nameline = nameline.format(*args)
                fastaLines = [nameline] + seqLines
                
                if False:
                    print 'orgCode ', orgCode 
                    print 'orgName', orgName
                    print 'acc ', acc 
                    print 'taxon ', taxon 
                    print 'geneDesc ', geneDesc 
                    print 'geneName ', geneName 
                    # print 'fastaNS', fastaNS
                    # print 'osLines ', osLines 
                    # print 'seqLines', seqLines
                    # print 'evidence ', evidence 
                    # print 'seqVersion', seqVersion
                    print 'complete ', complete 
                    print 'reference', reference
                    print 'geneIds  ', geneIds  
                    print 'goTerms ', goTerms 
                    print 'fastaLines ', fastaLines

                yield (fastaNS, acc, orgCode, orgName, taxon, geneName, geneDesc, complete,
                       reference, geneIds, goTerms, fastaLines, surprises)


def testParseParens():
    goodStrings = ["foo (bar (baz)) (wiz)", "foo bar", "(foo) holla"]
    badStrings = ["foo bar (baz)) (wiz)", "foo bar ((baz) (wiz)", "foo bar))(baz)"]
    for string in goodStrings:
        print string, '=>', parseParens(string)
    for string in badStrings:
        try:
            parseParens(string)
            raise Exception('No exception when testing', string)
        except Exception:
            print string, 'Good: found exception'
            
        
def parseParens(string):
    '''
    Returns everything up to and including the first set of parentheses.
    Nested parens ok.  Mismatched parens raise an exception.
    Example: "Frog virus 3 (isolate Goorha) (FV-3)" -> "Frog virus 3 (isolate Goorha)"
    '''
    count = 0
    for i, c in enumerate(string):
        if c == '(':
            count += 1
        if c == ')':
            count -= 1
            if count == 0:
                return string[:i+1]
            elif count < 0:
                raise Exception('Mismatched parentheses', string, count)
    if count > 0:
        raise Exception('Mismatched parentheses', string, count)
    return string


def upToAndIncludingFirstBlock2(string, start='(', end=')'):
    # need different characters to start and end a block
    assert start != end
    lenStart = len(start)
    part = string[:]

    # if no start of a block or no end of a block return whole string
    i = part.find(start)
    j = part.find(end)
    if i == -1 or j == -1:
        return part
    
    # if and end comes before a start, die.
    assert i >= j

    # find the matching end
    while True:
        # the remaining part after the start of the block
        part = part[i+lenStart:]
        i = part.find(start)
        j = part.find(end)
        if i < j:
            pass
        if j <= i:
            pass
    
    pass
    
        
def parseFastaNameline(nameline):
    '''
    Parse uniprot nameline to get the uniprot sequence accession, gene description, gene name, organism name and
    organism id (e.g. HUMAN or MYCGE)
    A uniprot nameline must have: acc, orgCode
    optional: geneDesc, geneName, orgName
    example nameline: >sp|P38398|BRCA1_HUMAN Breast cancer type 1 susceptibility protein OS=Homo sapiens GN=BRCA1 PE=1 SV=2
    example results: acc: P38398, geneName (GN): BRCA1, orgCode: HUMAN, orgName (OS): Homo sapiens, geneDesc: Breast cancer type 1 susceptibility protein
    returns: a dict containing keys for acc, geneDesc, geneName, orgName, and orgCode.  Some values 
    '''
    # split apart nameline into acc, orgName, and geneName.
    # example: >sp|P38398|BRCA1_HUMAN Breast cancer type 1 susceptibility protein OS=Homo sapiens GN=BRCA1 PE=1 SV=2
    # sometimes no gene name: >sp|P38398|BRCA1_HUMAN Breast cancer type 1 susceptibility protein OS=Homo sapiens PE=1 SV=2
    # '>sp|P38398|BRCA1_HUMAN', 'Breast cancer type 1 susceptibility protein OS=Homo sapiens GN=BRCA1 PE=1 SV=2'

    # None splits on whitespace.  Only do the first split. Remove leading '>'
    accAndOrgId, descOrgGNEtc = nameline.strip()[1:].split(None, 1) 
    # 'sp', 'P38398', 'BRCA1_HUMAN'
    ns, acc, entryId = accAndOrgId.split('|') # ns = namespace, either swissprot or trembl
    # 'BRCA1', 'HUMAN'
    etc, orgCode = entryId.rsplit('_', 1) # org abbr example: HUMAN.  i.e uniprot species id
    # 'Breast cancer type 1 susceptibility protein', 'Homo sapiens GN=BRCA1 PE=1 SV=2'
    geneDesc, orgGNEtc = (s.strip() for s in descOrgGNEtc.split('OS=', 1))
    # 'Homo sapiens GN=BRCA1 ', '1 SV=2'
    orgGN, etc = orgGNEtc.split('PE=', 1)
    if orgGN.find('GN=') == -1:
        orgName, geneName = (s.strip() for s in (orgGN, ''))
    else:
        # 'Homo sapiens', 'BRCA1'
        orgName, geneName = (s.strip() for s in orgGN.split('GN=', 1))

    return {'ns': ns, 'entryId': entryId, 'acc': acc, 'geneDesc': geneDesc, 'geneName': geneName, 'orgName': orgName, 'orgCode': orgCode}


def parseIdMapping(path):
    '''
    From ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/README:
    2) idmapping_selected.tab
    We also provide this tab-delimited table which includes
    the following mappings delimited by tab:

        1. UniProtKB-AC
        2. UniProtKB-ID
        3. GeneID (EntrezGene)
        4. RefSeq
        5. GI
        6. PDB
        7. GO
        8. IPI
        9. UniRef100
        10. UniRef90
        11. UniRef50
        12. UniParc
        13. PIR
        14. NCBI-taxon
        15. MIM
        16. UniGene
        17. PubMed
        18. EMBL
        19. EMBL-CDS
        20. Ensembl
        21. Ensembl_TRS
        22. Ensembl_PRO
        23. Additional PubMed
    Writes two dicts to files, one mapping gene to go terms, the other mapping gene to ncbi gene id.
    '''
    with open(path) as fh:
        for i, line in enumerate(fh):
            if i % 500000 == 0: print i
            seqId, b, geneIdsStr, d, e, f, goTermsStr, etc = line.split('\t', 7)
            goTerms = goTermsStr.split('; ') if goTermsStr else []
            geneIds = geneIdsStr.split('; ') if geneIdsStr else []
            yield seqId, geneIds, goTerms
