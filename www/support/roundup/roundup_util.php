<?php
// GOAL: This file should contain all shared roundup code.
//   Especially code to manipulate the objects representing the roundup semantic model.
//
// params: a 4-tuple of query db, subject db, divergence, and evalue, in that order.  qdb and subject db should be sorted alphabetically.
// paramsList: a list of params tuples.
// pair: a pair of query db and subject db, sorted.
// pairs: a list of db pairs.
// orthQuery: a description of parameters needed to run a query using orthology_query.py and get result back, either orthologs or clusters.
//
// There is a lot of stuff in here, used by numerous web pages.  Fairly disorganized.


require_once('roundup/common.php');
require_once('roundup/roundup_template.php');


define('GENOMES', 'GENOMES');
// GET GENOME DBS
//if (!isset($_SESSION[GENOMES])) {
if (true) {
  list($genomes, $exitcode) = python_dispatch('roundup_common.getGenomes');
  $_SESSION[GENOMES] = $genomes;
} else {
  ##if this is not a new session, just list the file names from the registered vars
  $genomes = $_SESSION[GENOMES];
}
usort($genomes, 'strcasecmp'); //case insensitive sorting

$divergences = array('0.2', '0.5', '0.8');
$thresholds = array("1e-20", "1e-15", "1e-10", "1e-5");
$evalues = $thresholds;
$browse_id_types = array('gene_name_type', 'seq_id_type');
$search_types = array('contains', 'equals', 'starts_with', 'ends_with');

define('ROUNDUP_TERMS_SUMMARY_RESULT_TYPE', 'roundup_terms_summary_result');
define('ROUNDUP_TERM_RESULT_TYPE', 'roundup_term_result');
define('ROUNDUP_GENE_RESULT_TYPE', 'roundup_gene_result');
define('ROUNDUP_TEST_RESULT_TYPE', 'roundup_test_result');
define('ROUNDUP_RAW_RESULT_TYPE', 'roundup_raw_result');
define('ROUNDUP_ORTHOLOGY_RESULT_TYPE', 'roundup_orthology_result');
define('ROUNDUP_HAMMING_DISTANCE_RESULT_TYPE', 'roundup_hamming_distance_result');
define('ROUNDUP_TEXT_RESULT_TYPE', 'roundup_text_result');
define('ROUNDUP_PHYLETIC_PATTERN_RESULT_TYPE', 'roundup_phyletic_pattern_result');
define('ROUNDUP_PHYLIP_MATRIX_RESULT_TYPE', 'roundup_phylip_matrix_result');
define('ROUNDUP_NEXUS_MATRIX_RESULT_TYPE', 'roundup_nexus_matrix_result');
define('ROUNDUP_COMPUTE_PAIRS_RESULT_TYPE', 'roundup_compute_pairs_result');

define('MAX_NUM_COMPUTE_ROUNDUP_PAIRS', 50);
define('ROUNDUP_GENOMES_LIMIT', 1000000);
define('UPPER_ROUNDUP_DISTANCE_LIMIT', 19.0);
define('LOWER_ROUNDUP_DISTANCE_LIMIT', 0.0);
define('ROUNDUP_DEFAULT_PAGE_NUM', 1);
define('ROUNDUP_DEFAULT_PAGE_SIZE', 100);

define('DIVERGENCE_PARAM', 'divergence');
define('EVALUE_PARAM', 'evalue');
define('DISTANCE_LOWER_LIMIT_PARAM', 'distance_lower_limit');
define('DISTANCE_UPPER_LIMIT_PARAM', 'distance_upper_limit');
define('GENOME_PARAM', 'genome');
define('GENOMES_PARAM', 'genomes[]');
define('LIMIT_GENOMES_PARAM', 'limit_genomes[]');
define('EMAIL_PARAM', 'email');
define('GENOME_NAME_PARAM', 'genome_name');
define('GENOME_URLS_PARAM', 'genome_urls');
define('BROWSE_ID_TYPE_PARAM', 'browse_id_type');
define('BROWSE_ID_PARAM', 'browse_id');
define('SEARCH_TYPE_PARAM', 'search_type');
define('SUBSTRING_PARAM', 'substring');


// convert a key, form parameter, option value, etc., to a name appropriate for displaying to user.
// $key: parameter to get display name for.
// $context: Unused, but the idea is that sometimes a key will have a different display name based on context.  This could be used to distinguish the context.
// If a display name for $key is not found, returns $key.
function roundupDisplayName($key, $context=NULL) {
  $map = array('fasta' => 'FASTA Sequence', 'fasta_genome' => 'Genome', 
	       'genome' => 'Primary Genome', 'limit_genomes' => 'Secondary Genomes', 'genomes' => 'Genomes', 
	       'query_genome' => 'First Genome', 'subject_genome' => 'Second Genome', 'divergence' => 'Divergence', 'evalue' => 'BLAST E-value',
	       'distance_lower_limit' => 'Distance Lower Limit', 'distance_upper_limit' => 'Distance Upper Limit', 
	       'gene_name' => 'Include Gene Names in Result', 'go_term' => 'Include GO Terms in Result', 
	       'tc_only' => 'Only Show Transitively Closed Gene Clusters', 
	       'browse_id' => 'Identifier', 'browse_id_type' => 'Identifier Type', 'gene_name_type' => 'Gene Name', 'seq_id_type' => 'Sequence Id',
	       'contains' => 'Contain', 'equals' => 'Equal', 'starts_with' => 'Start With', 'ends_with' => 'End With', 'substring' => 'Text Substring');
  if (array_key_exists($key, $map)) {
    return $map[$key];
  } else {
    return $key;
  }
}



// ==========
// VALIDATION
// ==========


function validateRoundupSearchType($form, $param=SEARCH_TYPE_PARAM) {
  global $search_types;
  $errors = array();

  if (!validateExists($form, $param)) {
    $errors[] = roundupDisplayName($param).' is required.  Please select one.';
  } elseif (!validateExistsIn($form, $param, $search_types)) {
    $errors[] = 'The following '.roundupDisplayName($param).' is not a valid choice: '.$form[$param];
  }
  return $errors;
}


function validateRoundupSearchSubstring($form, $param=SUBSTRING_PARAM) {
  global $browse_id_types;
  $errors = array();

  if (!validateExists($form, $param)) {
    $errors[] = roundupDisplayName($param).' is required.  Please enter one.';
  } 

  return $errors;
}


function validateRoundupBrowseIdType($form, $param=BROWSE_ID_TYPE_PARAM) {
  global $browse_id_types;
  $errors = array();
  // browse id type must exist and be in browse id type
  if (!validateExists($form, $param)) {
    $errors[] = roundupDisplayName($param).' is required.  Please select one.';
  } elseif (!validateExistsIn($form, $param, $browse_id_types)) {
    $errors[] = 'The following '.roundupDisplayName($param).' is not a valid choice: '.$form[$param];
  }
  return $errors;
}


function validateRoundupDivergence($form, $param=DIVERGENCE_PARAM) {
  global $divergences;
  $errors = array();
  // divergence must exist and be in divergences                                                                                                               
  if (!validateExists($form, $param)) {
    $errors[] = 'Divergence is required.  Please select one.';
  } elseif (!validateExistsIn($form, $param, $divergences)) {
    $errors[] = 'The following Divergence is not a valid choice: '.$form[$param];
  }
  return $errors;
}

function validateRoundupEvalue($form, $param=EVALUE_PARAM) {
  global $evalues;
  $errors = array();
  // evalue must exist and be in evalues                                                                                                               
  if (!validateExists($form, $param)) {
    $errors[] = 'E-value is required.  Please select one.';
  } elseif (!validateExistsIn($form, $param, $evalues)) {
    $errors[] = 'The following E-value is not a valid choice: '.$form[$param];
  }
  return $errors;
}

function validateRoundupDistanceLowerLimit($form, $param=DISTANCE_LOWER_LIMIT_PARAM) {
  $errors = array();
  // if exists, must be a number in [0.0, 19.0]
  if (validateExists($form, $param)) {
    $val = $form[$param];
    if (!is_numeric($val)) {
      $errors[] = "Distance Lower Limit must be a number.";
    } elseif (floatval($val) > UPPER_ROUNDUP_DISTANCE_LIMIT || floatval($val) < LOWER_ROUNDUP_DISTANCE_LIMIT) {
      $errors[] = "Distance Lower Limit must be a number in the range ".LOWER_ROUNDUP_DISTANCE_LIMIT." to ".UPPER_ROUNDUP_DISTANCE_LIMIT.".";
    }
  }
  return $errors;
}

function validateRoundupDistanceUpperLimit($form, $param=DISTANCE_UPPER_LIMIT_PARAM) {
  $errors = array();
  // if exists, must be a number in [0.0, 19.0]
  if (validateExists($form, $param)) {
    $val = $form[$param];
    if (!is_numeric($val)) {
      $errors[] = "Distance Upper Limit must be a number.";
    } elseif (floatval($val) > UPPER_ROUNDUP_DISTANCE_LIMIT || floatval($val) < LOWER_ROUNDUP_DISTANCE_LIMIT) {
      $errors[] = "Distance Upper Limit must be a number in the range ".LOWER_ROUNDUP_DISTANCE_LIMIT." to ".UPPER_ROUNDUP_DISTANCE_LIMIT.".";
    }
  }
  return $errors;
}

function validateRoundupDistanceRange($form, $lowerParam=DISTANCE_LOWER_LIMIT_PARAM, $upperParam=DISTANCE_UPPER_LIMIT_PARAM) {
  // both limits must be valid and the lower limit can not be greater than the upper limit.
  $errors = array();
  $errors = array_merge($errors, validateRoundupDistanceLowerLimit($form, $lowerParam));
  $errors = array_merge($errors, validateRoundupDistanceUpperLimit($form, $upperParam));
  if (!$errors) {
    if (validateExists($form, $lowerParam) && validateExists($form, $upperParam)) {
      if (floatval($form[$lowerParam]) > floatval($form[$upperParam])) {
	$errors[] = "Distance Lower Limit must not be greater than Distance Upper Limit.";
      }
    }
  }
  return $errors;
}

function validateRoundupGenomes($form, $param=GENOMES_PARAM) {
  global $genomes;
  $errors = array();
  // genomes must exist, must be valid genomes, and at least one must be different from the source genome.
  if (!validateExists($form, $param)) {
    $errors[] = 'Genomes is a required field.  Select two or more.';
  } elseif (!validateAllExistIn($form, $param, $genomes)) {
    $missingGenomes = array_diff($form[$param], $genomes);
    $errors[] = 'The following Genomes are not valid choices: ' . implode(', ', $missingGenomes);
  } elseif (count($form[$param]) < 2) {
    $errors[] = 'Select at least 2 Genomes.';
  } elseif (count($form[$param]) > ROUNDUP_GENOMES_LIMIT) {
    $errors[] = 'Select at most ' . ROUNDUP_GENOMES_LIMIT . ' Genomes.';
  }
  return $errors;
}

function validateRoundupGenomeAndLimitGenomes($form, $genomeParam=GENOME_PARAM, $limitGenomesParam=LIMIT_GENOMES_PARAM) {
  global $genomes;
  $errors = array();

  //limit genomes must exist, must be valid genomes, and at least one must be different from genome.
  $errors = array_merge($errors, validateRoundupGenome($form, $genomeParam));
  $errors = array_merge($errors, validateRoundupLimitGenomes($form, $limitGenomesParam));
  if (!$errors) {
    if (validateExists($form, $genomeParam) && in_array($form[$genomeParam], $form[$limitGenomesParam])) {
      $errors[] = 'Primary Genome must not also be one of the selected Secondary Genomes.';
    }
  }
  return $errors;
}

function validateRoundupLimitGenomes($form, $param=LIMIT_GENOMES_PARAM) {
  global $genomes;
  $errors = array();
  // limit genomes must exist, must be valid genomes
  if (!validateExists($form, $param)) {
    $errors[] = 'Please select one or more genomes from the Secondary Genomes list.';
  } elseif (!validateAllExistIn($form, $param, $genomes)) {
    $missingGenomes = array_diff($form[$param], $genomes);
    $errors[] = 'The following Secondary Genomes are not valid choices: ' . implode(', ', $missingGenomes);
  } elseif (count($form[$param]) > ROUNDUP_GENOMES_LIMIT) {
    $errors[] = 'Select at most ' . ROUNDUP_GENOMES_LIMIT . ' Secondary Genomes.';
  }

  return $errors;
}

function validateRoundupGenome($form, $param=GENOME_PARAM) {
  global $genomes;
  $errors = array();
  // genome must exist and must be a genome
  if (!validateExists($form, $param)) {
    $errors[] = 'Primary Genome is required.  Please select one.';
  } elseif (!validateExistsIn($form, $param, $genomes)) {
    $errors[] = 'The following Primary Genome is not a valid choice: '.$form[$param];
  }
  return $errors;
}

function validateRoundupEmail($form, $param=EMAIL_PARAM) {
  $errors = array();
  // if email must not exist or it must be well formed.
  if (validateExists($form, $param) && !isValidEmail($form[$param])) {
    $errors[] = "The email address received was not well formed.  Enter a valid email address or no email address.";
  }
  return $errors;
}


// params is a four-tuple of qdb, sdb, div, and evalue.
// this function makes sure qdb and sdb are in sorted order.
function makeRoundupParams($qdb, $sdb, $div, $evalue) {
  if ($qdb < $sdb) {
    return array($qdb, $sdb, $div, $evalue);
  } else {
    return array($sdb, $qdb, $div, $evalue);
  }
}


// $paramsList: list of 4-tuples of querydb, subjectdb, divergence, threshold
function roundupParamsListToPairs($paramsList) {
  $pairs = array_map(create_function('$p', '$a = array($p[0], $p[1]); sort($a); return $a;'), $paramsList);
  $pairs = common_array_unique($pairs);
  sort($pairs);
  return $pairs;
}


function stringToRoundupPair($str) {
  return preg_split("/ /", $str, -1, PREG_SPLIT_NO_EMPTY);
}


function roundupParamsToString($params) {
  return implode(' ', $params);
}


function stringToRoundupParams($str) {
  return preg_split("/ /", $str, -1, PREG_SPLIT_NO_EMPTY);
}


function stringToRoundupPairs($str) {
  $arr = preg_split("/\r?\n/", $str, -1, PREG_SPLIT_NO_EMPTY);
  $arr = array_map('stringToRoundupPair', $arr);
  return $arr;
}


function roundupParamsListToString($paramsList) {
  return implode("\n", array_map('roundupParamsToString', $paramsList));
}


function stringToRoundupParamsList($str) {
  $arr = preg_split("/\r?\n/", $str, -1, PREG_SPLIT_NO_EMPTY);
  $arr = array_map('stringToRoundupParams', $arr);
  return $arr;
}


// $pairs: array of 2 element arrays.
// $items: list of items.
// returns: array of pairs for which each pair contains at least one element in $items.
function filterPairsByItems($pairs, $items) {
  $filtered = array();
  foreach($pairs as $pair) {
    if (in_array($pair[0], $items) || in_array($pair[1], $items)) {
      $filtered[] = $pair;
    }
  }
  return $filtered;
}


// create a orthQuery object from a submitted form.
function makeOrthQueryFromClusterForm($form) {
  $orthQuery = makeDefaultOrthQuery();
  // split ids on whitespace
  $orthQuery['genomes'] = $form['genomes[]'];
  if (isset($form['tc_only'])) {
    $orthQuery['tc_only'] = (bool) $form['tc_only'];
  }
  $orthQuery['gene_name'] = (bool) getValueInMap('gene_name', $form);
  $orthQuery['go_term'] = (bool) getValueInMap('go_term', $form);
  $orthQuery['divergence'] = transformBlankToNull(getValueInMap('divergence', $form));
  $orthQuery['evalue'] = transformBlankToNull(getValueInMap('evalue', $form));
  $orthQuery['distance_lower_limit'] = transformBlankToNull(getValueInMap('distance_lower_limit', $form));
  $orthQuery['distance_upper_limit'] = transformBlankToNull(getValueInMap('distance_upper_limit', $form));

  $queryDesc = "Retrieve Query:\n";
  $queryDesc .= "\t" . roundupDisplayName('genomes') . "=" . implode(", ", array_map('roundupGenomeDisplayName', $orthQuery['genomes'])) . "\n";
  $queryDesc .= "\t" . roundupDisplayName('divergence') . "=" . $orthQuery['divergence'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('evalue') . "=" . $orthQuery['evalue'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('distance_lower_limit') . "=" . $orthQuery['distance_lower_limit'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('distance_upper_limit') . "=" . $orthQuery['distance_upper_limit'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('tc_only') . "=" . $orthQuery['tc_only'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('gene_name') . "=" . $orthQuery['gene_name'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('go_term') . "=" . $orthQuery['go_term'] . "\n";
  //  $queryDesc .= "\t" . roundupDisplayName('') . "=" . implode(", ", $orthQuery['']) . "\n";
  //  $queryDesc .= "\t" . roundupDisplayName('') . "=" . $orthQuery[''] . "\n";
  $orthQuery['query_desc'] = $queryDesc;

  return $orthQuery;
}


// create an ortholog query object from a search form object
function makeOrthQueryFromBrowseForm($form) {
  $orthQuery = makeDefaultOrthQuery();
  // split ids on whitespace
  // $orthQuery['seq_ids'] = preg_split("/\s+/", $form['seq_ids'], -1, PREG_SPLIT_NO_EMPTY);
  $orthQuery['seq_ids'] = getValueInMap('seq_ids', $form, array());
  $orthQuery['genome'] = $form['genome'];
  $orthQuery['limit_genomes'] = getValueInMap('limit_genomes[]', $form, array());
  $orthQuery['gene_name'] = (bool) getValueInMap('gene_name', $form);
  $orthQuery['go_term'] = (bool) getValueInMap('go_term', $form);
  $orthQuery['divergence'] = transformBlankToNull(getValueInMap('divergence', $form));
  $orthQuery['evalue'] = transformBlankToNull(getValueInMap('evalue', $form));
  $orthQuery['distance_lower_limit'] = transformBlankToNull(getValueInMap('distance_lower_limit', $form));
  $orthQuery['distance_upper_limit'] = transformBlankToNull(getValueInMap('distance_upper_limit', $form));

  $browseId = getValueInMap('browse_id', $form);
  $browseIdType = getValueInMap('browse_id_type', $form);
  $queryDesc = "Browse Query:\n";
  $queryDesc .= "\t" . roundupDisplayName('genome') . "=" . roundupGenomeDisplayName($orthQuery['genome']) . "\n";
  $queryDesc .= "\t" . roundupDisplayName($browseIdType) . "=" . $browseId . "\n";
  $queryDesc .= "\t" . "Sequence Identifiers=". implode(", ", $orthQuery['seq_ids']) . "\n";
  $queryDesc .= "\t" . roundupDisplayName('limit_genomes') . "=" . implode(", ", array_map('roundupGenomeDisplayName', $orthQuery['limit_genomes'])) . "\n";
  $queryDesc .= "\t" . roundupDisplayName('divergence') . "=" . $orthQuery['divergence'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('evalue') . "=" . $orthQuery['evalue'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('distance_lower_limit') . "=" . $orthQuery['distance_lower_limit'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('distance_upper_limit') . "=" . $orthQuery['distance_upper_limit'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('gene_name') . "=" . $orthQuery['gene_name'] . "\n";
  $queryDesc .= "\t" . roundupDisplayName('go_term') . "=" . $orthQuery['go_term'] . "\n";
  //  $queryDesc .= "\t" . roundupDisplayName('') . "=" . implode(", ", $orthQuery['']) . "\n";
  //  $queryDesc .= "\t" . roundupDisplayName('') . "=" . $orthQuery[''] . "\n";
  $orthQuery['query_desc'] = $queryDesc;

  return $orthQuery;
}


function transformBlankToNull($str) {
  return $str == '' ? NULL : $str; 
}


// Helper function.  creates an array that contains orthology query data initialized to default
// values.  Note, this is not a valid orthology query until it contains 
// more non empty values for ids, genomes, etc.
function makeDefaultOrthQuery() {
  $orthQuery = array();
  $orthQuery['seq_ids'] = array();
  $orthQuery['genome'] = NULL;
  $orthQuery['genomes'] = array();
  $orthQuery['limit_genomes'] = array();
  $orthQuery['divergence'] = '0.2';
  $orthQuery['evalue'] = '1e-20';
  $orthQuery['tc_only'] = false;
  $orthQuery['gene_name'] = false;
  $orthQuery['go_term'] = false;
  $orthQuery['distance_lower_limit'] = NULL;
  $orthQuery['distance_upper_limit'] = NULL;
  return $orthQuery;
}

// =====================
// ROUNDUP RESULT VIEWS
// =====================

function makePhylipMatrixResultContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.clusterResultToPhylip', array('resultId' => $resultId));
  return $retval;
}


function makeHammingResultContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  logDebug('start makeHammingResultContent()');
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.clusterResultToHammingProfile', array('resultId' => $resultId));
  return $retval;
}


function makeRoundupGenesSummaryContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.resultToGenesSummaryView', array('resultId' => $resultId));
  return $retval;
}


function makeRoundupTestResultContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.clusterResultToTest', 
					     array('resultId' => $resultId, 'otherParams' => $otherUrlParams));
  return $retval;
}


function makeRoundupTermsSummaryContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.resultToTermsSummary', 
					     array('resultId' => $resultId));
  return $retval;
}


function makeRoundupTermContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.resultToSingleTermView', 
					     array('resultId' => $resultId, 'otherParams' => $otherUrlParams));
  return $retval;
}


function makeRoundupGeneContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.resultToGeneView', 
					     array('resultId' => $resultId, 'otherParams' => $otherUrlParams));
  return $retval;
}


function makeNexusMatrixResultContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.clusterResultToNexus', array('resultId' => $resultId));
  return $retval;
}


function makePhyleticPatternResultContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.clusterResultToPhylogeneticProfile', array('resultId' => $resultId));
  return $retval;
}


function makeRoundupTextResultContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  $queryResult = getResult($resultId);

  $str = "";
  $str .= "Roundup Orthology Database Search Results\n";
  $str .= "\n";

  // orthologs result type not currently supported, only clusters.
  if ($queryResult['type'] == 'orthologs') {
    $str = 'ERROR: unsupported result type, \'orthologs\'.';
    return $str;
  }

  if (isset($queryResult['seq_id_to_data_map'])) {
    $seqIdToDataMap = $queryResult['seq_id_to_data_map'];
  } else {
    $seqIdToDataMap = array();
  }
  if (isset($queryResult['term_map'])) {
    $termMap = $queryResult['term_map'];
  } else {
    $termMap = array();
  }
  if (isset($queryResult['has_gene_names'])) {
    $hasGeneNames = $queryResult['has_gene_names'];
  } else {
    $hasGeneNames = False;
  }
  if (isset($queryResult['has_go_terms'])) {
    $hasGoTerms = $queryResult['has_go_terms'];
  } else {
    $hasGoTerms = False;
  }

  $numRows = count($queryResult['rows']);
  $numCols = count($queryResult['headers']);

  if ($numRows == 0) {
    $str .= "No results found for your search.\n";
  } elseif ($numRows == 1) {
    $str .= "1 result found for your search.\n";
  } else {
    $str .= "$numRows results found for your search.\n";
  }
  $str .= "\n";

  $headers = $queryResult['headers'];

  for ($rowIndex = 0; $rowIndex < $numRows; $rowIndex++) {
    $row = $queryResult['rows'][$rowIndex];
    $avgDist = $row[$numCols-1];
    $str .= "Gene Cluster #".($rowIndex+1)." | Average Evolutionary Distance: $avgDist\n";
    $str .= "Id\tGenome\tGene Name\tGO Terms\n";
    for ($colIndex = 0; $colIndex < $numCols-1; $colIndex++) {
      $ids = $row[$colIndex];
      if (!$ids) {
	$str .= "-\t".roundupGenomeDisplayName($headers[$colIndex])."\t-\t-\n";
      } else {
	foreach ($ids as $id) {
	  $geneName = '-';
	  $goTermsStr = '-';
	  if (isset($seqIdToDataMap[$id]['n'])) {
	    $geneName = $seqIdToDataMap[$id]['n'];
	  }
	  if (isset($seqIdToDataMap[$id]['t'])) {
	    $goTermNames = array();
	    foreach ($seqIdToDataMap[$id]['t'] as $term) {
	      $goTermNames[] = $termMap[$term];
	    }
	    if ($goTermNames) {
	      $goTermsStr = implode(', ', $goTermNames);
	    }
	  }
	  $str .= $seqIdToDataMap[$id]['a']."\t".roundupGenomeDisplayName($headers[$colIndex])."\t$geneName\t$goTermsStr\n";
	}
      }
    }
    $str .= "\n";
  }
  return $str;
}


function makeOrthologyResultContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  list($retval, $exitcode) = python_dispatch('format_orthology_cluster_result.resultToAllGenesView', 
					     array('resultId' => $resultId, 'otherParams' => $otherUrlParams));
  return $retval;
}


function makeSeqIdLink($id) {
  if (isGINumber($id)) {
    $idLink = "<a href=\"http://www.ncbi.nlm.nih.gov/entrez/viewer.fcgi?db=protein&val=$id\">$id</a>";
  } elseif (isEnsemblId($id)) {
    $idLink = "<a href=\"http://www.ensembl.org/Homo_sapiens/searchview?_q=$id\">$id</a>";
  } else {
    $idLink = "$id";
  }
  return $idLink;
}


function isEnsemblId($seqId) {
  return strpos($seqId, "ENS") === 0 || strpos($seqId, "NEWSIN") === 0 || strpos($seqId, "GS") === 0;
}


function isGINumber($seqId) {
  return preg_match('/^\d+$/', $seqId);
}


function makeRoundupRawResultContent($resultType, $resultId, $jobId, $templateType, $otherUrlParams) {
  return getResult($resultId);
}


function echoRoundupTemplate($content, $title=ROUNDUP_TOOL_TITLE, $templateType=ROUNDUP_PAGE_TEMPLATE) {
  return echoTemplate($title, $content, $templateType);
}


function roundupGenomeDisplayName($genomeId) {
  return preg_replace('/\.aa$/', '', str_replace('_', ' ', $genomeId));
}


// =====================================
// MISSING ROUNDUP RESULTS FUNCTIONALITY.  
// This functionality was relevant back when roundup did not have results computed for every genome pair, circa 2005.
// Surprisingly, it was used (as a result of an "error") in Spring 2010, when it took over a week to complete a roundup computation.
//   During that completion, the genomes showed up on the Roundup website before the results, because of the lag in loading results to the database.
// Most of this missing result functionality should be removed, but it does make sense to raise an error if all results are present.
// =====================================

// find out which files are needed and check to see which ones are missing
// returns: list of 4-tuples of params which have not had their results precomputed yet.
function getMissingRoundupResultParams($orthQuery) {
  $paramsList = orthQueryToParams($orthQuery);
  return getMissingRoundupResultParamsForParamsList($paramsList);
}


// $paramsList: an array of 4-tuples of querydb, subjectdb, divergence, evalue.
// returns: list of 4-tuples of params which have not had their results precomputed yet.
function getMissingRoundupResultParamsForParamsList($paramsList) {
  $keywords = array('paramsList' => $paramsList);
  list($missing, $exitcode) = python_dispatch('roundup_db.getNonLoadedResultsForParams', $keywords);
  if ($exitcode) {
    $errorMsg = 'getMissingRoundupResultParamsForParamsList: non-zero exit code=$exitcode.  missing=$missing.  paramsList=$paramsList';
    logError($errorMsg);
    throw new Exception($errorMsg);
  }
  return $missing;
}

// returns all pairs of genomes which need to be precomputed for this query to
// retrieve accurate results.
function orthQueryToPairs($orthQuery) {
  $pairs = array();
  // get pairs of genomes that results come from
  if ($orthQuery['genomes']) {
    $pairs = choose2($orthQuery['genomes']);
    // reduce pairs to only those containing a genome from genome or limit_genomes.
    $items = array();
    if ($orthQuery['genome']) {
      $items[] = $orthQuery['genome'];
    }
    if ($orthQuery['limit_genomes']) {
      $items = array_merge($items, $orthQuery['limit_genomes']);
    }
    if ($items) {
      $pairs = filterPairsByItems($pairs, $items);
    }
  } elseif ($orthQuery['genome'] && $orthQuery['limit_genomes']) {
    foreach ($orthQuery['limit_genomes'] as $g) {
      $pair = array($orthQuery['genome'], $g);
      sort($pair);
      $pairs[] = $pair;
    }
  }
  return $pairs;
}


// $pairs: list of pairs of genomes
// returns: list of 4-tuples of querydb, subjectdb, div, evalue, one for each pair in pairs.
function makeRoundupParamsForPairs($pairs, $div, $evalue) {
  // construct parameter list for each pair of genomes.
  $params = array();
  foreach ($pairs as $pair) {
    $params[] = array($pair[0], $pair[1], $div, $evalue);
  }
  return $params;                                    
}


// returns all 4-tuples of roundup results params which need to be precomputed for this query to
// retrieve accurate results.
function orthQueryToParams($orthQuery) {
  return makeRoundupParamsForPairs(orthQueryToPairs($orthQuery), $orthQuery['divergence'], $orthQuery['evalue']);
}


// UNUSED CODE
// UNUSED CODE
// UNUSED CODE

function roundupPairToString($pair) {
  return implode(' ', $pair);
}


function roundupPairsToString($pairs) {
  return implode("\n", array_map('roundupPairToString', $pairs));
}




?>
