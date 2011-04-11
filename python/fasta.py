#!/usr/bin/env python


import cStringIO
import re
import math

import execute

reId = re.compile("[^|]*[|]([^|]+)")
def idFromName(line):
    '''
    id => id
    >id => id
    >ns|id => id
    >ns|id| => id
    >ns|id|desc => id
    ns|id => id
    ns|id| => id
    ns|id|desc => id
    '''
    m = reId.search(line)
    if m:
        return m.group(1).strip()
    else:
        if line.startswith('>'):
            return line[1:].strip()
        else:
            return line.strip()
        

def prettySeq(seq, n=60):
    '''
    seq: one long bare (no nameline) sequence. e.g. MASNTVSAQGGSNRPVRDFSNIQDVAQFLLFDPIWNEQPGSIVPWKMNREQALAERYPELQTSEPSEDYSGPVESLELLPLEIKLDIMQYLSWEQISWCKHPWLWTRWYKDNVVRVSAITFED
    n: maximum length of sequence lines
    returns: seq split over multiple lines, all terminated by newlines.
    '''
    if len(seq) == 0:
        raise Exception('zero-length sequence', seq)
    seq = ''.join(seq.strip().split())
    chunks = int(math.ceil(len(seq)/float(n)))
    pretty = ''
    for i in range(chunks):
        pretty += seq[i*n:(i+1)*n] + '\n'
    return pretty


def numSeqsInFastaDb(path):
    return int(execute.run('grep  ">" %s | wc -l'%path))
    

def readFastaIter(filehandle, ignoreParseError=False):
    '''
    This is meant as a drop-in replacement for roundup/ReadFasta.ReadFasta class
    '''
    iterator = fastaSeqIter(filehandle, ignoreParseError)
    for seq in iterator:
        yield splitSeq(seq)


def splitSeq(seq):
    '''
    seq: string containing a single nameline, including '>' and sequence lines, and no other lines.
    returns: tuple of nameline, including '>', without a newline, and concatenated sequence lines, without newlines
    e.g. ['>blahname', 'AFADFDSAFAFAFAFFAFAF']
    '''
    lines = seq.splitlines()
    name = lines[0].strip()
    chars = ''.join([l.strip() for l in lines[1:]])
    return [name, chars]
    

def fastaSeqIterStrict(filehandle, ignoreParseError=False):
    '''
    Older function which treats blank lines as a potential source of fasta parsing errors.  Correct fasta format, according to this function,
    can only have blank lines between the end of a sequence and the start of a new nameline. (Not within sequence character lines
    or between a nameline and sequence character lines.)
    filehandle: file object containing fasta-formatted sequences.
    ignoreParseError: if True, parsing more flexibly handles whitespace and other deviations from the fasta "standard".  Any line which would have
    raised a parse exception now is ignored and parsing begins looking for a new fasta sequence with the next line (or current line if it is a name line.)
    Generator function yielding a string representing a single fasta sequence (name line including '>' and sequence lines)
    for each fasta sequence in filehandle.
    returns: a generator object.
    '''
    state = 'nameline'
    fasta = ''
    for line in filehandle:
        blankline = not bool(line.strip())
        if state == 'nameline' and blankline:
            continue
        elif state == 'nameline' and line.startswith('>'):
            state = 'seqline'
            fasta = line
        elif state == 'nameline':
            if ignoreParseError:
                state = 'nameline'
            else:
                raise Exception('FASTA parse error.  Looking for name line and found line which is neither blank nor nameline.  line=%s'%line)
        elif state == 'seqline' and blankline:
            if ignoreParseError:
                state = 'nameline'
            else:
                raise Exception('FASTA parse error.  Looking for sequence line and found blank line.  line=%s'%line)
        elif state == 'seqline' and line.startswith('>'):
            if ignoreParseError:
                state = 'seqline'
                fasta = line
            else:
                raise Exception('FASTA parse error.  Looking for sequence line and found name line.  line=%s'%line)
        elif state == 'seqline':
            state = 'in_seq'
            fasta += line
        elif state == 'in_seq' and blankline:
            yield fasta
            state = 'nameline'
            fasta = ''
        elif state == 'in_seq' and line.startswith('>'):
            yield fasta
            state = 'seqline'
            fasta = line
        elif state == 'in_seq':
            fasta += line
        else:
            raise Exception('FASTA parse error.  Unrecognized state.  state=%s, line=%s'%(state, line))

    if state == 'seqline':
        raise Exception('FASTA parse error.  Looking for sequence line and found end of file.')
    elif state == 'in_seq':
        yield fasta
    elif state == 'nameline' and fasta:
        yield fasta
    elif state == 'nameline':
        pass
    else:
        raise Exception('FASTA parse error.  Unrecognized state found at end of file.  state=%s'%state)


def fastaSeqIter(filehandle, ignoreParseError=False):
    '''
    filehandle: file object containing fasta-formatted sequences.
    ignoreParseError: if True, parsing ignores namelines that do not have sequence character lines.  For example, '>foo\n>bar\nABCD\n'
    would yield the 'bar' sequence, ignoring the 'foo' sequence that has no sequence characters associated with it.
    In all cases blank lines are ignored, no matter where they occur.
    Generator function yielding a string representing a single fasta sequence (name line including '>' and sequence lines)
    for each fasta sequence in filehandle.
    returns: a generator.
    notes:
    This function was modified from fastaSeqIterStrict to handle bogus fasta input like this:
    >ORFP:20136 YOL048C, Contig c378 4079-4399 reverse complement
    MLFKVSNFTSLTLLSLIPIVGPILANQLMAPKRTFTYLQRYFLLKGFSKKQAKDFQYEHYASFICFGMSAGLLELIPFFTIVTISSNTVGAAKWCSSLLKGERKKD*
    >ORFP:18671 , Contig c238 100299-100300 reverse complement

    >ORFP:20137 , Contig c378 4878-5189 reverse complement
    MKVGIELISHSQTSHGTHVNSTVLAEKTPQPLEKPSKEHSISKESNINRWLKI

    LRRQFDIWFPETIPTMKVRYELLKKNFIKEIFNSRAFIYPFLVSILYYLY*
    The old function, even with error handling turned on, would not concatenate all the sequence characters of the 3rd sequence
    since they are separated by a blank line.
    '''
    # states: seeking_nameline, seeking_seqline, in_seq.  
    state = 'seeking_nameline'
    fasta = ''
    for line in filehandle:
        # ignore all blank lines
        if not line.strip():
            continue
        elif state == 'seeking_nameline' and line.startswith('>'):
            state = 'seeking_seqline'
            fasta = line
        elif state == 'seeking_nameline' and not ignoreParseError:
            raise Exception('FASTA parse error.  Looking for name line and found line which is neither blank nor nameline.  line=%s'%line)
        elif state == 'seeking_seqline' and line.startswith('>'):
            if ignoreParseError:
                # skip nameline without sequence and restart with this nameline.
                state = 'seeking_seqline'
                fasta = line
            else:
                raise Exception('FASTA parse error.  Looking for sequence line and found name line.  line=%s'%line)
        elif state == 'seeking_seqline':
            state = 'in_seq'
            fasta += line
        elif state == 'in_seq' and line.startswith('>'):
            yield fasta
            state = 'seeking_seqline'
            fasta = line
        elif state == 'in_seq':
            fasta += line
        else:
            raise Exception('FASTA parse error.  Unrecognized state.  state=%s, line=%s'%(state, line))

    if state == 'in_seq':
        yield fasta
    elif state == 'seeking_seqline' and not ignoreParseError:
        raise Exception('FASTA parse error.  Looking for sequence line and found end of file.')
    elif state == 'seeking_nameline':
        pass
    else:
        raise Exception('FASTA parse error.  Unrecognized state found at end of file.  state=%s'%state)


def isNameLine(line):
    return line.startswith('>')


def _tern(comp, trueVal, falseVal):
    ''' a tawdry ternary operator '''
    if comp:
        return trueVal
    return falseVal


def head(query, n):
    '''returns the first n sequences in query.'''
    count = 0
    headstr = ''
    for line in query.splitlines(keepends=1):
        if line.startswith('>'):
            count += 1
            if count > n: break
        headstr += line
    return headstr


def dbSize(query):
    '''returns the number of sequence characters'''
    size = 0
    for line in query.splitlines():
        if isNameLine(line):
            continue
        size += len(line.strip())
    return size


def numChars(query):
    '''
    synonym for dbSize().  returns the number of character (e.g. bases or residues for nucleotide or protein sequences).
    '''
    return dbSize(query)
    

def numSeqs(query):
    '''
    synonym for size(), whose name is a little more specific as to what is being measured: the number of sequences.
    '''
    return size(query)


def size(query):
    '''
    query: string containing fasta formatted seqeunces
    returns: the number of sequences
    '''
    fh = cStringIO.StringIO(query)
    size = numSeqsInFile(fh)
    fh.close()
    return size
    # return sum([1 for line in query.splitlines() if isNameLine(line.strip())])


def numSeqsInFile(file):
    '''
    file: file like object containing fasta formatted sequences
    '''
    return sum([1 for line in file if isNameLine(line.strip())])


def numSeqsInPath(path):
    '''
    path: path to fasta formatted db
    returns: number of sequences in fasta db
    '''
    fh = open(path)
    size = numSeqsInFile(fh)
    fh.close()
    return size


def main():
    pass

        
if __name__ == '__main__':
    main()
                        
