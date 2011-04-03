<?php
// definition of fasta format from NCBI: http://www.ncbi.nlm.nih.gov/blast/html/search.html
//
// a sequence is a nameline followed by one or more sequence lines.
// blank/whitespace lines are ok between sequences.
// all lines may have trailing whitespace
// no lines may have leading whitespace except blank lines.
// a name line starts with a '>'
// a sequence line only has permissible protein chars or only permissible nucleotide characters
//
// fact for the curious: isNucleotideSeqLine() -> isProteinSeqLine(), because the permissible protein characters
// are a superset of the nucleotide ones.

require_once('string_util.php'); //has splitlines() function


#########################
# SEQUENCE TYPE CONSTANTS
#########################
define('PROTEIN', 'protein');
define('NUCLEOTIDE', 'nucleotide');
define('UNKNOWN', 'unknown');


// $seqs: a string of fasta formatted sequences.
// returns: a string, one line per fasta sequence, where each line 
// contains the concatenated sequence lines of the 
// corresponding fasta sequence. for example:
// >foo
// ATCG
// GGCA
// >bar
// TTTA
// TTGT
// becomes:
// ATCGGGCA
// TTTATTGT
function fastaToOneSeqPerLine($seqs) {
  $plainSeqs = "";
  $seq = "";
  $lines = splitlines($seqs);
  foreach ($lines as $line) {
    if (isBlankLine($line)) {
      //do nothing
    } elseif (isNameLine($line)) {
      if ($seq) {
	$plainSeqs .= $seq . "\n";
	$seq = "";
      }
    } elseif (isProteinSeqLine($line) || isNucleotideSeqLine($line)) {
      $seq .= trim($line);
    }
  }
  if ($seq) {
    $plainSeqs .= $seq . "\n";
  }
  return $plainSeqs;
}

// $seqs is a string adhering to the NCBI definition of fasta format.  see link above.
// returns true if $seqs is fasta formatted.  false otherwise.
//
// state machine:
// outsidestate: blankline -> outside, nameline -> namestate, seqline|else -> failed
// namestate: seqline -> seqstate, nameline|blankline|else -> failed
// seqstate: seqline -> seqstate, nameline -> namestate, blankline -> outsidestate, else -> failed
function isFasta($seqs) {
  //logDebug('isFasta $seqs=|'.$seqs.'|');
  // states: outside, name, seq
  $OUTSIDE = 'OUTSIDE';
  $NAME = 'NAME';
  $SEQ = 'SEQ';
  $state = $OUTSIDE;

  // note to self: test for blanklines before protein or nucl seq lines, 
  // since a blank line is vacuously truly a seq line.
  $lines = splitlines($seqs);
  foreach ($lines as $line) {
    //logDebug('isFasta $line=|'.$line.'|');
    //echo "<br/> state=$state line=$line";
    if ($state == $OUTSIDE) {
      if (isBlankLine($line)) {
	// no state change. not illegal line type in this state.
      } elseif (isNameLine($line)) {
	$state = $NAME;
      } else { //sequence lines or anything else are not ok.
	logDebug('fasta validation failure: OUTSIDE: line encounted which is not blank or name line. $line='.$line);
	return false;
      }
    } elseif ($state == $NAME) {
      if (isBlankLine($line) || isNameLine($line)) {
	logDebug('fasta validation failure: NAME: blank or name line encountered. $line='.$line);
	return false;
      } elseif (isProteinSeqLine($line) || isNucleotideSeqLine($line)) {
	$state = $SEQ;
      } else { // only sequence lines are ok after a name line.
	logDebug('fasta validation failure: NAME: non-sequence line encountered. $line='.$line);
	return false;
      }
    } elseif ($state == $SEQ) {
      if (isBlankLine($line)) {
	$state = $OUTSIDE;
      } elseif (isProteinSeqLine($line) || isNucleotideSeqLine($line)) {
	// stay in the sequence state.
      } elseif (isNameLine($line)) {
	$state = $NAME;
      } else {
	logDebug('fasta validation failure: SEQ: line is not blank, seq, or name line. $line='.$line);
	return false;
      }
    }
  }
  // not ok to have a name line without a seq line, which is what ending with $state == $NAME means.
  if ($state == $NAME) { 
    logDebug('fasta validation failure: end of fasta sequences in NAME state.');
    return false; 
  }
  return true;
}

// returns true iff all non-name, non-blank lines are protein sequence lines
function areProteinSequences($seqs) {
  return areSequencesOfType($seqs, PROTEIN);
}

// returns true iff all non-name, non-blank lines are nucleotide sequence lines
function areNucleotideSequences($seqs) {
}

// $type is a sequence type constant
function areSequencesOfType($seqs, $type) {
  if ($type == PROTEIN) {
    $predicate = 'isProteinSeqLine';
  } elseif ($type == NUCLEOTIDE) {
    $predicate = 'isNucleotideSeqLine';
  }
  $lines = splitlines($seqs);
  foreach($lines as $line) {
    if (!isBlankLine($line) && !isNameLine($line) && !$predicate($line)) {
      return false;
    }
  }
  return true;
}

function isBlankLine($line) {
  return !trim($line);
}

// a fasta name line is a line starting with '>'.  plain and simple.
function isNameLine($line) {
  return $line{0} == '>';
}

// protein sequence line is not a fasta name line
// and only contains protein sequence characters
// ignoring case and trailing whitespace.
function isProteinSeqLine($line) {
  global $fastaProteinCodes;
  return isSeqLine($line, $fastaProteinCodes);
}

// nucleotide sequence line is not a fasta name line
// and only contains nucleotide sequence characters
// ignoring case and trailing whitespace.
function isNucleotideSeqLine($line) {
  global $fastaNucleotideCodes;
  return isSeqLine($line, $fastaNucleotideCodes);
}

// a sequence line is a line which is not a name line and only
// contains allowable characters (case insensitive) (and trailing whitespace.)
// $allowableChars: a dictionary of allowable chars.
// If $allowableChars is not set, all characters are allowable.
function isSeqLine($line, $allowableChars=NULL) {
  if (isNameLine($line)) { return 0; }

  if (!isset($allowableChars)) { return 1; }

  $line = rtrim($line); //makes trailing whitespace ok
  $line = strtoupper($line); //allows lowercase characters
  for($i = 0; $i < strlen($line); $i++) {
    $char = $line{$i};
    if (!isset($allowableChars[$char])) {
      return 0;
    }
  }
  return 1;
}


$fastaNucleotideCodes = array('A' => 'adenosine', 
			      'C' => 'cytidine', 
			      'G' => 'guanine',
			      'T' => 'thymidine',
			      'U' => 'uridine',
			      'R' => 'G A (purine)',
			      'Y' => 'T C (pyrimidine)',
			      'K' => 'G T (keto)',
			      'M' => 'A C (amino)',
			      'S' => 'G C (strong)',
			      'W' => 'A T (weak)',
			      'B' => 'G T C',
			      'D' => 'G A T',
			      'H' => 'A C T',
			      'V' => 'G C A',
			      'N' => 'A G C T (any)',
			      '-' => 'gap of indeterminate length'
			      );
$fastaProteinCodes = array('A' => 'alanine',
			   'B' => 'aspartate or asparagine',
			   'C' => 'cystine',
			   'D' => 'aspartate',
			   'E' => 'glutamate',
			   'F' => 'phenylalanine',
			   'G' => 'glycine',
			   'H' => 'histidine',
			   'I' => 'isoleucine',
			   'K' => 'lysine',
			   'L' => 'leucine',
			   'M' => 'methionine',
			   'N' => 'asparagine',
			   'P' => 'proline',
			   'Q' => 'glutamine',
			   'R' => 'arginine',
			   'S' => 'serine',
			   'T' => 'threonine',
			   'U' => 'selenocysteine',
			   'V' => 'valine',
			   'W' => 'tryptophan',
			   'Y' => 'tyrosine',
			   'Z' => 'glutamate or glutamine',
			   'X' => 'any',
			   '*' => 'translation stop',
			   '-' => 'gap of indeterminate length'
			   );

?>
