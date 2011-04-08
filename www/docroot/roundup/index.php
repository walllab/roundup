<?php

// USAGE: How to add a query_
// 1. Add makeXInfo() function, including $xExampleData.
// 2. Add to roundupControlFlow() an action for displaying query X and submitting it. 
// 3. Add query validation function
// 4. Add query to the splash page
// 5. Add the query documentation to roundup_usage_doc.php
// 6. Add echo/make content for query page
// 7. Add to roundup_util.php a function for displaying query results and a result type constant
// 8. Add to result_util.php a mapping from result type to the result displaying function.
// 
// require_once('authentication.php');
require_once('roundup/roundup_util.php');
require_once('roundup/common.php');
require_once('roundup/validation.php');
require_once('roundup/forms.php');
require_once('roundup/roundup_template.php');
require_once('roundup/waiting.php');
require_once('roundup/result_util.php');
require_once('roundup/fasta.php');

// ini_set("max_execution_time", "3600");
// ini_set("max_input_time", "1800");

logDebug('roundup/index.php REQUEST='.serialize($_REQUEST));

define('SEQ_ID_LOOKUP_TITLE', 'Lookup a Sequence Id for a FASTA Sequence');

// BEGIN CONTROL FLOW
$action = getValueInMaps('action', array($_REQUEST));
logDebug('roundup/index.php $action='.$action);
roundupControlFlow($action, $genomes, $divergences, $evalues, $browse_id_types);


// BROWSE FORM
function makeBrowseInfo($useDefaults=false) {
  //$params = array('genome', 'seq_ids', 'limit_genomes[]', 'gene_name', 'go_term', 'divergence', 'evalue', 'distance_lower_limit', 'distance_upper_limit');
  $params = array('genome', 'browse_id', 'browse_id_type', 'limit_genomes[]', 'gene_name', 'go_term', 'divergence', 'evalue', 'distance_lower_limit', 'distance_upper_limit');
  if ($useDefaults) {
    $defaults = array('gene_name' => 'true',
		      'go_term' => 'true');
  } else {
    $defaults = array();
  }
  $exampleData = array('genome' => 'Arabidopsis_thaliana.aa',
		       //'seq_ids' => "18390992\n18402218\n", 
		       'browse_id' => "18402218", 
		       'browse_id_type' => 'seq_id_type',
		       'limit_genomes[]' => array("Homo_sapiens.aa", 'Mus_musculus.aa'));
  $info = makeFormInfo('input_form', $params, $_REQUEST, $exampleData, $defaults);

  $eukaryotesExampleData = array('genome' => 'Homo_sapiens.aa',
				 'browse_id' => "UBE3A", 
				 'browse_id_type' => 'gene_name_type',
				 'limit_genomes[]' => array('Apis_mellifera.aa', 'Arabidopsis_thaliana.aa', 'Bos_taurus.aa', 'Caenorhabditis_elegans.aa', 'Candida_albicans.aa', 'Canis_familiaris.aa', 'Ciona_intestinalis.aa', 'Danio_rerio.aa', 'Drosophila_melanogaster.aa', 'Encephalitozoon_cuniculi.aa', 'Gallus_gallus.aa', 'Macaca_mulatta.aa', 'Monodelphis_domestica.aa', 'Mus_musculus.aa', 'Pan_troglodytes.aa', 'Rattus_norvegicus.aa', 'Saccharomyces_bayanus.aa', 'Saccharomyces_castellii.aa', 'Saccharomyces_cerevisiae.aa', 'Saccharomyces_kluyveri.aa', 'Saccharomyces_kudriavzevii.aa', 'Saccharomyces_mikatae.aa', 'Saccharomyces_paradoxus.aa', 'Schizosaccharomyces_pombe.aa', 'Strongylocentrotus_purpuratus.aa', 'Tetraodon_nigroviridis.aa', 'Xenopus_tropicalis.aa'));
  $eukaryotesExample = makeForm($eukaryotesExampleData, $params, $defaults);
  $info['eukaryotes_example'] = $eukaryotesExample;

  return $info;
}

// RAW FORM
function makeRawInfo() {
  $exampleData = array('query_genome' => 'Mus_musculus.aa',
			  'subject_genome' => 'Homo_sapiens.aa', 
			  'divergence' => '0.2',
			  'evalue' => '1e-20');
  return makeFormInfo('input_form', array('query_genome', 'subject_genome', 'divergence', 'evalue'), $_REQUEST, $exampleData);
}

// ADD GENOME FORM
function makeAddGenomeInfo() {
  $exampleData = array('genome_name' => 'Mus musculus',
			  'genome_urls' => 'ftp://bio-mirror.net/biomirror//ncbigenomes/M_musculus/protein/protein.fa.gz', 
			  EMAIL_PARAM => 'your_name@example.com',
		       'message' => '');
  return makeFormInfo('input_form', array('genome_name', 'genome_urls', EMAIL_PARAM, 'message'), $_REQUEST, $exampleData);
}

// CLUSTER FORM
function makeClusterInfo($useDefaults=false) {
  $params = array('genomes[]', 'tc_only', 'gene_name', 'go_term', 'divergence', 'evalue', 'distance_lower_limit', 'distance_upper_limit');
  if ($useDefaults) {
    $defaults = array('gene_name' => 'true',
		      'go_term' => 'true');
  } else {
    $defaults = array();
  }
  $exampleData = array('genomes[]' => array("Homo_sapiens.aa", 'Mus_musculus.aa', 'Arabidopsis_thaliana.aa'));
  $info = makeFormInfo('input_form', $params, $_REQUEST, $exampleData, $defaults);

  $eukaryotesExampleData = array('genomes[]' => array('Anopheles_gambiae.aa', 'Apis_mellifera.aa', 'Arabidopsis_thaliana.aa', 'Bos_taurus.aa', 'Caenorhabditis_elegans.aa', 'Candida_albicans.aa', 'Candida_glabrata.aa', 'Canis_familiaris.aa', 'Ciona_intestinalis.aa', 'Danio_rerio.aa', 'Drosophila_melanogaster.aa', 'Encephalitozoon_cuniculi.aa', 'Fugu_rubripes.aa', 'Gallus_gallus.aa', 'Homo_sapiens.aa', 'Macaca_mulatta.aa', 'Monodelphis_domestica.aa', 'Mus_musculus.aa', 'Pan_troglodytes.aa', 'Rattus_norvegicus.aa', 'Saccharomyces_bayanus.aa', 'Saccharomyces_castellii.aa', 'Saccharomyces_cerevisiae.aa', 'Saccharomyces_kluyveri.aa', 'Saccharomyces_kudriavzevii.aa', 'Saccharomyces_mikatae.aa', 'Saccharomyces_paradoxus.aa', 'Schizosaccharomyces_pombe.aa', 'Strongylocentrotus_purpuratus.aa', 'Tetraodon_nigroviridis.aa', 'Xenopus_tropicalis.aa'));
  $eukaryotesExample = makeForm($eukaryotesExampleData, $params, $defaults);
  $info['eukaryotes_example'] = $eukaryotesExample;

  return $info;
}

// SEQ ID LOOKUP FORM
function makeSeqIdLookupInfo() {
  $exampleData = array('fasta' => ">test\nMYSIVKEIIVDPYKRLKWGFIPVKRQVEDLPDDLNSTEIV\nTISNSIQSHETAENFITTTSEKDQLHFETSSYSEHKDNVN\nVTRSYEYRDEADRPWWRFFDEQEYRINEKERS
HNKWYSWF\nKQGTSFKEKKLLIKLDVLLAFYSCIAYWVKYLD", 
		       'fasta_genome' => 'Saccharomyces_cerevisiae.aa');
  return makeFormInfo('input_form', array('fasta', 'fasta_genome'), $_REQUEST, $exampleData);
}
 

// CONTROLLER:  VALIDATE FORMS, POSSIBLY PROCESS SOME ACTIONS, AND DECIDE WHICH PAGE TO RENDER NEXT.
function roundupControlFlow($action, $genomes, $divergences, $evalues, $browse_id_types) {
  $errors = array();

  if (FALSE) {
    echoMaintenancePage();
  } elseif ($action == 'search_gene_names') {
    doSearchGeneNamesAction();
  } elseif ($action == 'about') {
    echoAboutPage();
  } elseif ($action == 'news') {
    echoNewsPage();
  } elseif ($action == 'list_db_sources') {
    echoDbSourcesPage($genomes);
  } elseif ($action == 'input_browse') {
    $browseInfo = makeBrowseInfo(true);
    echoBrowsePage($browseInfo, $genomes, $divergences, $evalues, $browse_id_types, $errors);
  } elseif ($action == 'browse') {
    $browseInfo = makeBrowseInfo();
    // validate form
    logDebug('in browse: browseInfo='.serialize($browseInfo));
    $errors = validateBrowseForm($browseInfo);
    if (!$errors) {
      $browseId = getValueInMap('browse_id', $browseInfo['data']);
      $browseIdType = getValueInMap('browse_id_type', $browseInfo['data']);
      if ($browseId && $browseIdType == 'gene_name_type') {
	logDebug("browse by gene_name_type: browseId=$browseId");
	$geneName = $browseId;
	$genome = getValueInMap('genome', $browseInfo['data']);
	// check here if gene name has seq ids and if not forward to gene name lookup page.
	$keywords = array('geneName' => $geneName, 'database' => $genome);
	list($seq_ids, $exitcode) = python_dispatch('roundup_db.getSeqIdsForGeneName', $keywords);
	if ($exitcode) {
	  logError('roundupControlFlow(): exit code encountered when running roundup_db.getSeqIdsForGeneName(). keywords='.serialize($keywords));
	  // forward to generic error page.
	  echoRunCommandErrorPage();
	} else {
	  if ($seq_ids) {
	    $browseInfo['data']['seq_ids'] = $seq_ids;
	    $orthQuery = makeOrthQueryFromBrowseForm($browseInfo['data']);
	    orthologyQueryControlFlow($orthQuery);
	  } else {
	    // forward to "no seq ids for this gene name" page
	    $message = "Roundup failed to find the gene name '$geneName' in the genome '$genome'.  Please search through the available names.";
	    forwardToPage("/roundup/index.php?action=search_gene_names&substring=$geneName&search_type=contains&message=".rawurlencode($message));
	  }
	}
      } else {
	// default to 'seq_id_type'
	if ($browseId) {
	  $seqIds = preg_split('/\s+/', trim($browseId));
	  $browseInfo['data']['seq_ids'] = $seqIds;
	}
	$orthQuery = makeOrthQueryFromBrowseForm($browseInfo['data']);
	orthologyQueryControlFlow($orthQuery);
      }
    } else {
      logDebug('in browse.  errors = '.serialize($errors));
      // set errors, render query page.
      echoBrowsePage($browseInfo, $genomes, $divergences, $evalues, $browse_id_types, $errors);    
    }
  } elseif ($action == 'input_cluster') {
    $clusterInfo = makeClusterInfo(true);
    echoClusterPage($clusterInfo, $genomes, $divergences, $evalues, $errors);
  } elseif ($action == 'cluster') {
    $clusterInfo = makeClusterInfo();
    // validate
    $errors = validateClusterForm($clusterInfo, $genomes, $divergences, $evalues);
    if (!$errors) {
      $orthQuery = makeOrthQueryFromClusterForm($clusterInfo['data']);
      orthologyQueryControlFlow($orthQuery);
    } else {
      // set errors, render query page.
      echoClusterPage($clusterInfo, $genomes, $divergences, $evalues, $errors);    
    }
  } elseif ($action == 'input_add_genome') {
    $addGenomeInfo = makeAddGenomeInfo();
    echoAddGenomePage($addGenomeInfo, $errors);
  } elseif ($action == 'add_genome') {
    $addGenomeInfo = makeAddGenomeInfo();
    //validate email address and make sure url, genome name field are not empty.
    $errors = validateAddGenomeForm($addGenomeInfo);
    if (!$errors) {
      emailForm($addGenomeInfo['data']);
      echoAddGenomeReceiptPage($addGenomeInfo);
    } else {
      echoAddGenomePage($addGenomeInfo, $errors);
    }
  } elseif ($action == 'input_raw') {
    $rawInfo = makeRawInfo();
    echoRawPage($rawInfo, $genomes, $divergences, $evalues, $errors);
  } elseif ($action == 'raw') {
    $rawInfo = makeRawInfo();
    // validate form
    $errors = validateRawForm($rawInfo, $genomes, $divergences, $evalues);
    if (!$errors) {
      // check if result exist
      $params = makeRoundupParams($rawInfo['data']['query_genome'], $rawInfo['data']['subject_genome'], 
			    $rawInfo['data']['divergence'], $rawInfo['data']['evalue']);
      logDebug(serialize($params));

      //logDebug(serialize($params));
      list($exists, $exitcode) = python_dispatch('roundup_util.rawResultsExist', array('params' => $params));
      if ($exists) {
	$keywords = array('params' => $params);
	echoSyncLocalResult('roundup_util.getRawResults', $keywords, ROUNDUP_RAW_RESULT_TYPE, TEXT_DOWNLOAD_TEMPLATE);
      } else {
	$missingError = "missing raw result for parameters :\n".serialize($params);
	logError($missingError);
	echoRoundupErrorPage(array($missingError));
      }
      // if raw data is available
      //   get raw data and "display" it.
    } else {
      // set errors, render query page.
      echoRawPage($rawInfo, $genomes, $divergences, $evalues, $errors);    
    }
  } elseif ($action == 'input_seq_id_lookup') {
    $info = makeSeqIdLookupInfo();
    echoSeqIdLookupPage($info, $genomes, $errors);
  } elseif ($action == 'seq_id_lookup') {
    $info = makeSeqIdLookupInfo();
    // validate form
    $errors = validateSeqIdLookupForm($info, $genomes);
    if (!$errors) {
      $fasta = $info['data']['fasta'];
      $genome = $info['data']['fasta_genome'];
      $keywords = array('fasta' => $fasta, 'genome' => $genome);
      list($seqId, $exitcode) = python_dispatch('BioUtilities.findSeqIdWithFasta', $keywords);
      if ($exitcode) {
	logError('SeqIdLookup: exit code encountered when running BioUtilities.findSeqIdWithFasta. keywords='.serialize($keywords));
	// forward to generic error page.
	echoRunCommandErrorPage();
      } else {
	echoSeqIdLookupResultPage($fasta, $genome, $seqId);
      }
    } else {
      // set errors, render query page.
      echoSeqIdLookupPage($info, $genomes, $errors);
    }
  } elseif ($action == 'splash') {
    echoSplashPage();
  } else { // default action
    echoSplashPage();
  }
}


// control flow logic for executing an orthology query and displaying its result
// or displaying a missing orthologs computation form if orthologs are missing (which never happens anymore).
function orthologyQueryControlFlow($orthQuery) {
  //$computeInfo = makeComputeInfo();

  $otherUrlParams = array('page_num' => 1, 'page_size' => 100);
  // check if result exist
  $missingParams = getMissingRoundupResultParams($orthQuery);
  if (!$missingParams) {
    // check if cache is not being skipped.
    if (!isset($_REQUEST['get_from_cache']) || ($_REQUEST['get_from_cache'] != 'false')) {
    //if (false) {
      $key = serialize($orthQuery);
      logDebug("cache key $key\nhash=".cache_hash($key));
      if (cache_has_key($key)) {
	// logDebug("cache has key.\nhash=".cache_hash($key));
	$resultFilename = cache_get($key);
	$resultId = getResultIdFromFilename($resultFilename);
	logDebug("result filename: $resultFilename\nresult id: $resultId");
	if (resultExists($resultId)) {
	  logDebug("result exists");
	  // does not return
	  forwardToResultPage(ROUNDUP_ORTHOLOGY_RESULT_TYPE, $resultId, NULL, ROUNDUP_WIDE_TEMPLATE, $otherUrlParams);
	}
      } 
    }
    // choose to execute small queries synchronously (quickly) or large queries asynchronously (slowly on lsf).
    $numGenomes = count($orthQuery['genome']) + count($orthQuery['limit_genomes']) + count($orthQuery['genomes']);
    if ($numGenomes < 20) {
      echoSyncLocalResult('orthology_query.doOrthologyQuery', $orthQuery, ROUNDUP_ORTHOLOGY_RESULT_TYPE, ROUNDUP_WIDE_TEMPLATE, $otherUrlParams);
    } else {
      echoAsyncGridWaitingResult('orthology_query.doOrthologyQuery', $orthQuery, ROUNDUP_ORTHOLOGY_RESULT_TYPE, ROUNDUP_WIDE_TEMPLATE, $otherUrlParams);
    }
  } else {
    $missingError = "missing orthology query result for parameters:\n" . serialize($missingParams) . "\n orthology query:\n" . serialize($orthQuery);
    logError($missingError);
    echoRoundupErrorPage(array($missingError));
  }
}


function makeSearchGeneNamesInfo() {
  $params = array('message', 'search_type', 'substring');
  $exampleData = array('search_type' => 'contains',
		       'substring' => 'ata');
  return makeFormInfo('input_form', $params, $_REQUEST, $exampleData);
}


function doSearchGeneNamesAction() {
  $info = makeSearchGeneNamesInfo();
  $errors = validateSearchGeneNamesForm($info);
  $geneNameGenomePairs = array();
  if (!$errors) {
    $substring = getValueInMap('substring', $info['data']);
    $searchType = getValueInMap('search_type', $info['data']);
    $keywords = array('substring' => $substring, 'searchType' => $searchType);
    list($geneNameGenomePairs, $exitcode) = python_dispatch('roundup_db.findGeneNameGenomePairsLike', $keywords);
    if ($exitcode) {
      logError('doSearchGeneNamesAction(): exit code encountered when running roundup_db.findGeneNamesLike(). keywords='.serialize($keywords));
      // forward to generic error page.
      echoRunCommandErrorPage();
    } else {
      echoSearchGeneNamesPage($info, $geneNameGenomePairs);
    }
  } else {
    echoSearchGeneNamesPage($info, $geneNameGenomePairs, $errors);
  }	  
}


//function echoSearchGeneNamesPage($info, $geneNames=NULL, $errors=NULL) {
//  echoRoundupTemplate(makeSearchGeneNamesContent($info, $geneNames, $errors));
//}

function echoSearchGeneNamesPage($info, $geneNameGenomePairs=NULL, $errors=NULL) {
  echoRoundupTemplate(makeSearchGeneNamesContent($info, $geneNameGenomePairs, $errors));
}


//function makeSearchGeneNamesContent($info, $geneNames=NULL, $errors=NULL) {
function makeSearchGeneNamesContent($info, $geneNameGenomePairs=NULL, $errors=NULL) {
  global $search_types;

  $message = getValueInMap('message', $info['data']);
  $substring = getValueInMap('substring', $info['data']);
  $searchType = getValueInMap('search_type', $info['data']);

  $content = '';

  $exampleData = getValueInMaps('example_data', array($info));
  $data = $info['data'];
  $id = $info['id'];

  $content .= makeJSFormValuesScript($id, $data);
  $content .= makeJSFormValuesScript($id, $exampleData, 'example');
  $content .= makeJSFormLoadEvent($id);

  $content .= '<h2>Search For Gene Names</h2>'."\n";
  if ($message) {
    $content .= "<p class=\"roundup_message\">$message</p>\n";
  }
  $content .= '<p>Search the list of gene names and symbols used by the Roundup Orthology Database.</p>'."\n";
  $content .= '<div align="left"><a href="javascript:docWindow(\'roundup_usage_doc\', \'search_gene_names\')">Documentation</a> and '.makeJSSetFormLink($id, 'example', 'Example').'</div>'."\n";

  $content .= "<div class=\"roundup_form\"><form action=\"index.php\" method=\"post\" id=\"$id\">\n";

  $content .= makeErrorsDiv($errors);

  $content .= "<input type=\"hidden\" name=\"action\" value=\"search_gene_names\" />\n";
  $content .= "<div class=\"roundup_form_row\">Find all gene names that \n";
  $content .= "<select name=\"search_type\">\n";
  foreach($search_types as $type) {
    $content .= "<option value=\"$type\">".roundupDisplayName($type)."</option>\n";
  }
  $content .= "</select>\n";
  $content .= " the following text: <input name=\"substring\" type=\"text\" size=\"20\" maxlength=\"100\" />\n";
  $content .= "</div>\n";
  $content .= "<div class=\"roundup_form_row\"><input type=\"submit\"/><input type=\"reset\" /></div>\n";

  $content .= "</form></div>\n";

  if ($searchType && $substring) {
    $content .= "<div>Gene Name Search Results for gene names that ".roundupDisplayName($searchType)." the text '$substring':</div>\n";
    if ($geneNameGenomePairs) {
      $numNames = count($geneNameGenomePairs);
      $content .= "<div>$numNames matching combination".($numNames == 1 ? "" : "s")." of gene name and genome found.</div>";
      $content .= "<table>\n";
      $content .= "<tr><td>Gene Name</td><td>Genome</td></tr>\n";
      foreach ($geneNameGenomePairs as $pair) {
	$content .= "<tr><td>$pair[0]</td><td>".roundupGenomeDisplayName($pair[1])."</td></tr>\n";
      }
      $content .= "</table>\n";
    }
    //if ($geneNames) {
    if (false) {
      $numNames = count($geneNames);
      $content .= "<div>$numNames matching gene name".($numNames == 1 ? "" : "s")." found.</div>";
      $content .= "<pre>";
      foreach ($geneNames as $name) {
	$content .= "$name\n";
      }
      $content .= "</pre>";
    } else {
      $content .= "<div>No matching gene names found.</div>";
    }
  }
  return $content;

}


function validateSearchGeneNamesForm($info) {
  $errors = array();
  $data = $info['data'];

  $errors = array_merge($errors, validateRoundupSearchType($data));
  $errors = array_merge($errors, validateRoundupSearchSubstring($data));

  return $errors;
}

function validateSeqIdLookupForm($formInfo, $genomes) {
  $errors = array();
  $data = $formInfo['data'];

  // query genome must exist and must be a genome
  if (!validateExists($data, 'fasta_genome')) {
    $errors[] = 'Genome is required.  Please select one.';
  } elseif (!validateExistsIn($data, 'fasta_genome', $genomes)) {
    $errors[] = 'The following Genome is not a valid choice: '.$data['query_genome'];
  }

  if (!validateExists($data, 'fasta')) {
    $errors[] = 'FASTA-formatted sequence is required.  Please enter one.';
  } elseif (!isFasta($data['fasta'])) {
    $errors[] = 'A non-valid FASTA sequence input was given.';
  } else {
    list($genomeDescs, $exitcode) = python_dispatch('roundup_util.getGenomeDescriptions', array('genomes' => $genomes));
    list($numSeqs, $exitcode) = python_dispatch('fasta.numSeqs', array('query' => $data['fasta']));
    if ($numSeqs != 1) {
      $errors[] = "Exactly one fasta sequence must be given.  $numSeqs were detected.";
    }
  }

  return $errors;
}

function echoDbSourcesPage($genomes) {
  echoRoundupTemplate(makeDbSourcesContent($genomes));
}

function makeDbSourcesContent($genomes) {
  $content = '<pre>';
  list($genomeDescs, $exitcode) = python_dispatch('roundup_util.getGenomeDescriptions', array('genomes' => $genomes));
  foreach($genomeDescs as $genomeDesc) {
    $content .= $genomeDesc;
  }
  $content .= '</pre>';
  return $content;
}


function echoAboutPage() {
  echoRoundupTemplate(makeAboutContent());
}

function makeAboutContent() {
  $content = '';

  $content .= "<h2>About the Roundup Orthology Database</h2>\n";
  $content .= "<p>Principal Investigator:  Dr. Dennis P. Wall</p>\n";
  $content .= "<p>Roundup was first developed by Todd F. DeLuca and is now being maintained and developed by Kristian St.Gabriel.</p>\n";
  $content .= "<p>This project would not have been possible without the hard work and sound advice of many people, including I-Hsien Wu, Jian Pu, Thomas Monaghan, Saurav Singh and Leon Peshkin</p>\n";
  $content .= "<p>In addition, we owe a great debt of gratitude Mark Komarinski, Andy Bergman, Bret Martin, Gregory Cavanagh and Marcos Athanasoulis of <a href=\"http://ritg.med.harvard.edu\">RITG</a>. Their group hosts the Roundup portal and maintains the vast linux cluster where our computation takes place.</p>\n";
  $content .= "<p>Contact us via the <a href=\"/roundup/contact_us.php\">Support Page</a>.</p>\n";
 return $content;
}


function echoNewsPage() {
  echoRoundupTemplate(makeNewsContent());
}

function getNews($filename) {
  $file = file_get_contents($filename);

  $bodypattern = ".*<body>";
  $bodyendpattern = "</body>.*";

  $noheader = eregi_replace($bodypattern, "", $file);

  $noheader = eregi_replace($bodyendpattern, "", $noheader);

  return $noheader;
}

function makeNewsContent() {
//  $content = '';
//  $content .= "<h2>Roundup News</h2>\n";
//  $content .= "<p><b>Here you can find the latest info about site updates and improvements.</b></p>\n";
//  $content .= "<p>March 13, 2008</p>\n";
//  $content .= "<p>A few days ago I added ten new requested genomes to the database. Computation has already begun, but it will take many, many weeks for computation to finish and for the results to be available in the Roundup database. In addition, we are also computing a few hundred of our genomes that have been updated in the past twelve months, so things will take a bit longer than usual. The newly added genomes include the African elephant, lesser hedgehog, common shrew, yellow fever mosquito, bush baby, rabbit, pika, guinea pig and the Japanese killifish. I also added one of the most compellingly unique organisms on earth: the Australian platypus. I'm expecting the computation for these genomes will be finished and available in the Roundup database by the end of march. Many more will be added each month.</p>\n";
//  $content .= "<p>--Kris St-Gabriel</p>\n\n";
//  $content .= "<p>February 26, 2008</p>\n";
//  $content .= "<p>There have been extensive changes to Roundup these past few months. The most obvious improvement is the site's look-and-feel, which I designed and implemented over Christmas 2007. The next step has been to move the Roundup code to its own domain - http://roundup.hms.harvard.edu. Roundup's new home makes it easier to deploy various improvements and upgrades.</p>\n";
//  $content .= "<p>Aside from these improvements, in the months ahead we will be adding  many more genomes to the database. Remember, if we're missing one you need, <a href=\"index.php?action=input_add_genome\">feel free to request it!</a></p>\n";
//  $content .= "<p>Computing new genomes against our existing (very large) database can take weeks or months, even on Harvard Medical School's high-performance linux cluster. Once again, we'd like to thank our friends in <a href=\"http://ritg.med.harvard.edu\">RITG</a> for their tireless efforts in maintaining the hosting and computational enviroment in which Roundup operates.</p> \n";
//  $content .="<p>--Kris St-Gabriel</p>";


// replacement code starts here
  $content = '';
  $content .= getNews("http://dev.roundup.hms.harvard.edu/roundup/news.html");

  return $content;
}

function echoMaintenancePage() {
  $maintenance = '
<tr>
<td>
<div class="error">
Roundup is currently undergoing maintenance and is estimated to be unavailable until 2007/02/22.  Thank you for you patience.
</div>
</td>
</tr>
';
  echoRoundupTemplate(makeSplashContent($maintenance));
}

function echoSplashPage($message='') {
  echoRoundupTemplate(makeSplashContent($message));
}


function makeSplashContent($maintenance='') {
  $content = '';

  $content .= <<<EOT
<!--

<table>
<tr>
<td>
<div class="content_title">Roundup Orthology Database</div>
</td>
</tr>-->
EOT;

  $content .= $maintenance;

  $content .= <<<EOT
<div id="overview">
<div id="statistics">
<div id="statistics-text"><strong>Database Statistics</strong>
<p> Around 220 genomes (and growing) updated monthly.</p>
<p>24,090 unique pair-wise genome orthology comparisons completed.</p>
<p>183,935,606 orthologous pairs of genes predicted in total (for all parameter combinations) and growing as more pairs of genomes are compared.</p>
</div><!--close statistics-text-->
</div><!--close statistics-->

			<h2>Overview</h2>
<p>Roundup is a large-scale database of orthology covering over 220 publicly available genomes. The orthologs are computed using the Reciprocal Smallest Distance (RSD) algorithm. This algorithm detects more (and more accurate) orthologs than reciprocal best blast hits and gives each ortholog a score based on evolutionary distance.</p>

<p>Roundup results are integrated with terms from Gene Ontology and gene names from NCBI. Roundup is a living dataset: the underlying genomes and the orthologs computed from them are updated regularly.</p>
<p>Download the locally-installable version of the <a href="http://wall.hms.harvard.edu/software">RSD algorithm</a> used by Roundup to compute orthologs.  Included is a tutorial pdf.</p>
<p><a href="index.php?action=input_add_genome">Request a Genome!</a>  Is Roundup missing a genome you want? Let us know!</p>
</div> <!--end of overview-->	
			
			
			<!--middle menu-->
			<div id="middle-list-container">
<ul id="middle-list">
<li id="active"><a href="javascript:docWindow('roundup_usage_doc')">Documentation</a>     |</li>  
<li><a href="javascript:RodeoInfo('/roundup/docs/RoundUp_RECOMB.htm','windowName','toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,copyhistory=no,width=660,height=540')">Project Overview</a>     |</li>
<li><a href="index.php?action=list_db_sources">List of Genome Sources</a>     |</li>
<li><a href="http://bioinformatics.oxfordjournals.org/cgi/reprint/19/13/1710">About the RSD Algorithm</a></li>
</ul>
</div>
				
			<!--end menu-->
			
			
			<!--three boxes-->
			<!--remember to put a / in front of images when you paste into roundup code-->
			
		
<div id="browse-download-retrieve">
<div class="float"><div id="box">
  <a href="index.php?action=input_browse"><img src="/roundup/images/box_browse.jpg" width="240" height="215"
  alt="browse: find proteins orthologous to proteins in a genome of your choice." /><br /></a>
</div>
</div>
<div class="float"><div id="box">
  <a href="index.php?action=input_raw"><img src="/roundup/images/box_download.jpg" width="240" height="215"
  alt="download the orthologs computed by the RSD algorithm for a pair of genomes." /><br /></a>
</div>
</div>
<div class="float"><div id="box">
  <a href="index.php?action=input_cluster"><img src="/roundup/images/box_retrieve.jpg" width="240" height="215"
  alt="retrieve phylogenetic profiles for a set of genomes based on orthologous relationships among proteins." /><br /></a>
</div>
</div>
</div><!--close div called 'browse-download-retrieve'-->


			
			
			
			<div id="disclaimer">
		<p>This material is based upon work supported by the National Science Foundation under Grant No. 0543480 and the National Institutes of Health under Grant No. LM009261. Any opinions, findings, and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the National Science Foundation or National Institutes of Health.</p>
			</div>
			
			
		
			
			<!--end of the page-->

EOT;

  return $content;
}


function validateAddGenomeForm($formInfo) {
  $errors = array();
  $form = $formInfo['data'];

  if (!validateExists($form, EMAIL_PARAM)) {
    $errors[] = "Email Address is required.  Please enter an Email Address.";
  } elseif (!isValidEmail($form[EMAIL_PARAM])) {
    $errors[] = "The Email Address received was not valid.  Please enter a valid Email Address.";
  }

  if (!validateExists($form, GENOME_NAME_PARAM)) {
    $errors[] = "Genome Name is required.  Please enter a Genome Name.";
  }
  
  if (!validateExists($form, GENOME_URLS_PARAM)) {
    $errors[] = "Genome Source URL(s) is required.  Please enter a Genome Source URL(s).";
  }

  return $errors;  
}


function validateComputeForm($formInfo, $genomes) {
  $errors = array();
  $data = $formInfo['data'];

  $errors = array_merge($errors, validateRoundupEmail($data));

  return $errors;  
}


function validateClusterForm($formInfo, $genomes, $divergences, $evalues) {
  $errors = array();
  $data = $formInfo['data'];

  $errors = array_merge($errors, validateRoundupGenomes($data));
  $errors = array_merge($errors, validateRoundupDivergence($data));
  $errors = array_merge($errors, validateRoundupEvalue($data));
  $errors = array_merge($errors, validateRoundupDistanceRange($data));

  return $errors;
}


function validateBrowseForm($formInfo) {
  $errors = array();
  $data = $formInfo['data'];

  $errors = array_merge($errors, validateRoundupBrowseIdType($data));
  $errors = array_merge($errors, validateRoundupGenomeAndLimitGenomes($data));
  $errors = array_merge($errors, validateRoundupDivergence($data));
  $errors = array_merge($errors, validateRoundupEvalue($data));
  $errors = array_merge($errors, validateRoundupDistanceRange($data));

  return $errors;
}


function validateRawForm($formInfo, $genomes, $divergences, $evalues) {
  $errors = array();
  $data = $formInfo['data'];

  // query genome must exist and must be a genome
  if (!validateExists($data, 'query_genome')) {
    $errors[] = 'First Genome is required.  Please select one.';
  } elseif (!validateExistsIn($data, 'query_genome', $genomes)) {
    $errors[] = 'The following First Genome is not a valid choice: '.$data['query_genome'];
  }
  // subject genome must exist and must be a genome
  if (!validateExists($data, 'subject_genome')) {
    $errors[] = 'Second Genome is required.  Please select one.';
  } elseif (!validateExistsIn($data, 'subject_genome', $genomes)) {
    $errors[] = 'The following Second Genome is not a valid choice: '.$data['subject_genome'];
  }
  // query and subject genome must be different from each other.
  if (validateExists($data, 'query_genome') && validateExists($data, 'subject_genome') && validateEqual($data, 'query_genome', 'subject_genome')) {
    $errors[] = 'First Genome and Second Genome must be different.';
  }

  $errors = array_merge($errors, validateRoundupDivergence($data));
  $errors = array_merge($errors, validateRoundupEvalue($data));

  return $errors;
}


function echoRoundupErrorPage($errors) {
  echoRoundupTemplate(makeRoundupErrorContent($errors));
}

// $errors: array of error messages
function makeRoundupErrorContent($errors) {
  $content = makeErrorsDiv($errors);
  return $content;
}


function echoClusterPage($formInfo, $genomes, $divergences, $evalues, $errors=NULL) {
  echoRoundupTemplate(makeClusterContent($formInfo, $genomes, $divergences, $evalues, $errors));
}


// write html output for cluster form
// write an errors
// write javascript to set form values and example values
function makeClusterContent($formInfo, $genomes, $divergences, $evalues, $errors=NULL) {
  $content = '';

  $eukaryotesExampleData = getValueInMap('eukaryotes_example', $formInfo);
  $exampleData = getValueInMap('example_data', $formInfo);
  $data = $formInfo['data'];
  $id = $formInfo['id'];

  $content .= makeJSFormValuesScript($id, $data);
  $content .= makeJSFormValuesScript($id, $exampleData, 'example');
  $content .= makeJSFormValuesScript($id, $eukaryotesExampleData, 'eukaryotes_example');
  $content .= makeJSFormLoadEvent($id);

  $content .= '<h2>Retrieve Phylogenetic Profiles in the Roundup Orthology Database</h2>'."\n";
  $content .= '<a href="javascript:docWindow(\'roundup_usage_doc\', \'cluster\')">Documentation</a> and '.makeJSSetFormLink($id, 'example', 'Example')."\n";

  $content .= "<div><form action=\"index.php\" method=\"post\" id=\"$id\">";
  $content .= makeErrorsDiv($errors);
  $content .= "<input type=\"hidden\" name=\"action\" value=\"cluster\" /><table class=\"paramTable\">";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'genomes')\">".roundupDisplayName('genomes')."</a>:<br/>Select 2 or more. </td>";
  $content .= "<td><select name=\"genomes[]\" size=\"6\" multiple=\"multiple\">";
  foreach($genomes as $genome) {
    $content .= "<option value=\"$genome\">".roundupGenomeDisplayName($genome)."</option>\n";
  }
  $content .= "</select></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'divergence')\">".roundupDisplayName('divergence')."</a>: </td>";
  $content .= "<td><select name=\"divergence\">";
  foreach($divergences as $divergence) {
    $content .= "<option value=\"$divergence\">$divergence</option>\n";
  }
  $content .= "</select></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\">";
  $content .= "<a href=\"javascript:docWindow('roundup_usage_doc', 'evalue')\">".roundupDisplayName('evalue')."</a>: </td>";
  $content .= "<td><select name=\"evalue\">";
  foreach($evalues as $evalue) {
    $content .= "<option value=\"$evalue\">$evalue</option>\n";
  }
  $content .= "</select></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\">";
  $content .= "<a href=\"javascript:docWindow('roundup_usage_doc', 'distance_lower_limit')\">".roundupDisplayName('distance_lower_limit')."</a> (from 0.0 to 19.0): </td>";
  $content .= "<td><input name=\"distance_lower_limit\" type=\"text\" size=\"10\" maxlength=\"10\" /></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\">";
  $content .= "<a href=\"javascript:docWindow('roundup_usage_doc', 'distance_upper_limit')\">".roundupDisplayName('distance_upper_limit')."</a> (from 0.0 to 19.0): </td>";
  $content .= "<td><input name=\"distance_upper_limit\" type=\"text\" size=\"10\" maxlength=\"10\" /></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td><a href=\"javascript:docWindow('roundup_usage_doc', 'tc_only')\">".roundupDisplayName('tc_only')."</a>: </td>";
  $content .= "<td><input type=\"checkbox\" name=\"tc_only\" value=\"true\"></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td><a href=\"javascript:docWindow('roundup_usage_doc', 'gene_name')\">".roundupDisplayName('gene_name')."</a>: </td>";
  $content .= "<td><input type=\"checkbox\" name=\"gene_name\" value=\"true\"></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td><a href=\"javascript:docWindow('roundup_usage_doc', 'go_term')\">".roundupDisplayName('go_term')."</a>: </td>";
  $content .= "<td><input type=\"checkbox\" name=\"go_term\" value=\"true\"></td>";
  $content .= "</tr>\n";

  $content .= "</table><div><input type=\"submit\"/><input type=\"reset\" /></div></form></div>";

  return $content;

}


// make the browse form content and wrap in the rodeo page template.
// echoRodeoTemplate is an example of something that could be done better as a macro instead of a function
// since typically one would echo the content as it is created, not write it all to a string and then echo it,
// preventing reading a potentially huge string into memory.  Using a function requires evaluating the parameters
// of the function before the function execution, which would mean echoing the browse content, before the template header.
// Using a macro would delay evaluation of the makeBrowseContent function.  However, since this is not LISP...
function echoBrowsePage($formInfo, $genomes, $divergences, $evalues, $browse_id_types, $errors=NULL) {
  echoRoundupTemplate(makeBrowseContent($formInfo, $genomes, $divergences, $evalues, $browse_id_types, $errors));
}


// write html output for browse form
// write an errors
// write javascript to set form values and example values
function makeBrowseContent($formInfo, $genomes, $divergences, $evalues, $browse_id_types, $errors=NULL) {
  $content = '';


  $eukaryotesExampleData = getValueInMap('eukaryotes_example', $formInfo);
  $exampleData = getValueInMaps('example_data', array($formInfo));
  $data = $formInfo['data'];
  $id = $formInfo['id'];

  $content .= makeJSFormValuesScript($id, $data);
  $content .= makeJSFormValuesScript($id, $exampleData, 'example');
  $content .= makeJSFormValuesScript($id, $eukaryotesExampleData, 'eukaryotes_example');
  $content .= makeJSFormLoadEvent($id);

  $content .= '<h2>Browse the Roundup Orthology Database</h2>'."\n";
  $content .= '<div align="left"><a href="javascript:docWindow(\'roundup_usage_doc\', \'browse\')">Documentation</a> and '.makeJSSetFormLink($id, 'example', 'Example').' and <a href="index.php?action=input_seq_id_lookup">'.SEQ_ID_LOOKUP_TITLE.'</a></div>'."\n";

  $content .= "<div><form action=\"index.php\" method=\"post\" id=\"$id\">";
  $content .= makeErrorsDiv($errors);
  $content .= "<input type=\"hidden\" name=\"action\" value=\"browse\" /><table class=\"paramTable\">";

  $content .= "<tr><td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'genome')\">".roundupDisplayName('genome')."</a>: </td>";
  $content .= "<td><select name=\"genome\">";
  foreach($genomes as $genome) {
    $content .= "<option value=\"$genome\">".roundupGenomeDisplayName($genome)."</option>\n";
  }
  $content .= "</select></td></tr>";

  $content .= "<tr><td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'browse_id_type')\">".roundupDisplayName('browse_id_type')."</a>: </td>\n";
  $content .= "<td><select name=\"browse_id_type\">\n";
  foreach($browse_id_types as $type) {
    $content .= "<option value=\"$type\">".roundupDisplayName($type)."</option>\n";
  }
  $content .= "</select></td></tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'browse_id')\">".roundupDisplayName('browse_id')."</a> (optional): </td>\n";
  $content .= "<td><input name=\"browse_id\" type=\"text\" size=\"20\" maxlength=\"100\" /></td>\n";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'limit_genomes')\">".roundupDisplayName('limit_genomes')."</a>: </td>";
  $content .= "<td><select name=\"limit_genomes[]\" size=\"6\" multiple=\"multiple\">";
  foreach($genomes as $genome) {
    $content .= "<option value=\"$genome\">".roundupGenomeDisplayName($genome)."</option>\n";
  }
  $content .= "</select></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'divergence')\">".roundupDisplayName('divergence')."</a>: </td>";
  $content .= "<td><select name=\"divergence\">";
  foreach($divergences as $divergence) {
    $content .= "<option value=\"$divergence\">$divergence</option>\n";
  }
  $content .= "</select></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\">";
  $content .= "<a href=\"javascript:docWindow('roundup_usage_doc', 'evalue')\">".roundupDisplayName('evalue')."</a>: </td>";
  $content .= "<td><select name=\"evalue\">";
  foreach($evalues as $evalue) {
    $content .= "<option value=\"$evalue\">$evalue</option>\n";
  }
  $content .= "</select></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\">";
  $content .= "<a href=\"javascript:docWindow('roundup_usage_doc', 'distance_lower_limit')\">".roundupDisplayName('distance_lower_limit')."</a> (from 0.0 to 19.0): </td>";
  $content .= "<td><input name=\"distance_lower_limit\" type=\"text\" size=\"10\" maxlength=\"10\" /></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\">";
  $content .= "<a href=\"javascript:docWindow('roundup_usage_doc', 'distance_upper_limit')\">".roundupDisplayName('distance_upper_limit')."</a> (from 0.0 to 19.0): </td>";
  $content .= "<td><input name=\"distance_upper_limit\" type=\"text\" size=\"10\" maxlength=\"10\" /></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td><a href=\"javascript:docWindow('roundup_usage_doc', 'gene_name')\">".roundupDisplayName('gene_name')."</a>: </td>";
  $content .= "<td><input type=\"checkbox\" name=\"gene_name\" value=\"true\"></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td><a href=\"javascript:docWindow('roundup_usage_doc', 'go_term')\">".roundupDisplayName('go_term')."</a>: </td>";
  $content .= "<td><input type=\"checkbox\" name=\"go_term\" value=\"true\"></td>";
  $content .= "</tr>\n";

  $content .= "</table><div><input type=\"submit\"/><input type=\"reset\" /></div></form></div>";

  return $content;

}


function echoAddGenomeReceiptPage($formInfo) {
  echoRoundupTemplate(makeAddGenomeReceiptContent($formInfo));
}


function makeAddGenomeReceiptContent($formInfo) {
  $content = '';



  $data = $formInfo['data'];
  $id = $formInfo['id'];
  $content .= makeJSFormValuesScript($id, $data);
  $content .= makeJSFormLoadEvent($id);

  $content .= '<h2>Receipt of Genome Addition Request</h2>'."\n";
  $content .= '<p>Your request to add a genome to Roundup has been submitted.  You will be contacted shortly for more information or with the result of your request.  Please feel free to use the Support menu option above for any follow up inquiries.  The specifics of your request are below.</p>'."\n";

  $content .= '
<div>
<form action="/roundup/index.php" method="post" id="'.$id.'">
<input type="hidden" name="action" value="" />

<table class="paramTable">

<tr>
<td class="label"><a href="javascript:docWindow(\'roundup_usage_doc\', \'genome_name\')">Genome Name</a>: </td>
<td><pre>'.$data['genome_name'].'</pre></td>
</tr>

<tr>
<td class="label"><a href="javascript:docWindow(\'roundup_usage_doc\', \'genome_urls\')">Genome Source URL(s)</a>: </td>
<td><pre>'.$data['genome_urls'].'</pre></td>
</tr>

<tr>
<td class="label"><a href="javascript:docWindow(\'roundup_usage_doc\', \'email\')">Contact Email Address</a>: </td>
<td><pre>'.$data[EMAIL_PARAM].'</pre></td>
</tr>

<tr>
<td class="label"><a href="javascript:docWindow(\'roundup_usage_doc\', \'message\')">Any Additional Message</a>: </td>
<td><pre>'.$data['message'].'</pre></td>
</tr>

</table>
<p>
<input type="submit" value="Return to Roundup Home" />
</p>
</form>
</div>
';
  return $content;
}


function echoSeqIdLookupPage($formInfo, $genomes, $errors=NULL) {
  echoRoundupTemplate(makeSeqIdLookupContent($formInfo, $genomes, $errors));
}


function makeSeqIdLookupContent($formInfo, $genomes, $errors=NULL) {
  $content = '';

  $exampleData = getValueInMaps('example_data', array($formInfo));
  $data = $formInfo['data'];
  $id = $formInfo['id'];

  $content .= makeJSFormValuesScript($id, $data);
  $content .= makeJSFormValuesScript($id, $exampleData, 'example');
  $content .= makeJSFormLoadEvent($id);

  $content .= '<h2>'.SEQ_ID_LOOKUP_TITLE.'</h2>'."\n";
  $content .= '<div align="left"><a href="javascript:docWindow(\'roundup_usage_doc\', \'seq_id_lookup\')">Documentation</a> and ';
  $content .= makeJSSetFormLink($id, 'example', 'Example').'</div>'."\n";


  $content .= "<div><form action=\"index.php\" method=\"post\" id=\"$id\">";
  $content .= makeErrorsDiv($errors);
  $content .= "<input type=\"hidden\" name=\"action\" value=\"seq_id_lookup\" /><table class=\"paramTable\">";

  $content .= "<tr><td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'fasta_genome')\">";
  $content .= roundupDisplayName('fasta_genome')."</a>: </td>";
  $content .= "<td><select name=\"fasta_genome\">";
  foreach($genomes as $genome) {
    $content .= "<option value=\"$genome\">".roundupGenomeDisplayName($genome)."</option>\n";
  }
  $content .= "</select></td></tr>";

  $content .= "<tr><td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'fasta')\">".roundupDisplayName('fasta')."</a>: </td>";
  $content .= "<td><textarea name=\"fasta\" rows=\"5\" cols=\"80\"></textarea></td></tr>";

  $content .= "</table><div><input type=\"submit\"/><input type=\"reset\" /></div></form></div>";

  return $content;

}


function echoSeqIdLookupResultPage($fasta, $genome, $seqId) {
  echoRoundupTemplate(makeSeqIdLookupResultContent($fasta, $genome, $seqId));
}


function makeSeqIdLookupResultContent($fasta, $genome, $seqId) {
  $content .= '<h2>'.SEQ_ID_LOOKUP_TITLE.' Result</h2>'."\n";
  $content .= '<h3>Query</h3>';
  $content .= roundupDisplayName('fasta_genome') . ': ';
  $content .= '<pre>'. roundupGenomeDisplayName($genome).'</pre>';
  $content .= roundupDisplayName('fasta') . ': ';
  $content .= "<pre>$fasta</pre>";
  $content .= '<h3>Result</h3>';
  if (!$seqId) {
    $seqId = 'No match found.';
  }
  $content .= "Sequence Id: $seqId";
  return $content;
}


function echoAddGenomePage($formInfo, $errors=NULL) {
  echoRoundupTemplate(makeAddGenomeContent($formInfo, $errors));
}


function makeAddGenomeContent($formInfo, $errors=NULL) {
  $content = '';

  // fill in user email address.
  if (!validateExists($formInfo['data'], EMAIL_PARAM) && isset($_SESSION['useremail'])) {
    $formInfo['data'][EMAIL_PARAM] = $_SESSION['useremail'];
  }

  $exampleData = getValueInMaps('example_data', array($formInfo));
  $data = $formInfo['data'];
  $id = $formInfo['id'];

  $content .= makeJSFormValuesScript($id, $data);
  $content .= makeJSFormValuesScript($id, $exampleData, 'example');
  $content .= makeJSFormLoadEvent($id);

  $content .= '<h2>Request the Addition of a Genome to Roundup</h2>
<p>If you do not find a genome you want when using Roundup, you may request its addition.  Since Roundup uses <a href="javascript:RodeoInfo(\'/roundup/docs/fasta_format.php\',\'windowName\',\'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,copyhistory=no,width=660,height=540\')">FASTA formatted</a> protein sequence files to generate orthlogs, you must tell us the location (URL) of the publicly accessible FASTA formatted protein sequence file(s) for the whole genome.  Please see the Example below for help.  Or look at a complete <a href="index.php?action=list_db_sources">List of Genome Sources</a> for more example URLs.
</p>
<p>
Once you have requested a genome, we will add it to Roundup, contacting you once we are done.  Also, if we need to clarify anything we will contact you.
</p>
<div align="left"><a href="javascript:docWindow(\'roundup_usage_doc\', \'add_genome\')">Documentation</a> 
and '.makeJSSetFormLink($id, 'example', 'Example').'</div>
<div>
<form action="index.php" method="post" id="'.$id.'">
';

  $content .= makeErrorsDiv($errors);

  $content .= '
<input type="hidden" name="action" value="add_genome" />

<table class="paramTable">

<tr>
<td class="label"><a href="javascript:docWindow(\'roundup_usage_doc\', \'genome_name\')">Genome Name</a>: </td>
<td><input name="genome_name" type="text" size="50" maxlength="500" /></td>
</tr>

<tr>
<td class="label"><a href="javascript:docWindow(\'roundup_usage_doc\', \'genome_urls\')">Genome Source URL(s)</a>: </td>
<td><textarea rows="5" cols="50" name="genome_urls"></textarea></td>
</tr>

<tr>
<td class="label"><a href="javascript:docWindow(\'roundup_usage_doc\', \'email\')">Contact Email Address</a>: </td>
<td><input name="email" type="text" size="50" maxlength="300"/></td>
</tr>

<tr>
<td class="label"><a href="javascript:docWindow(\'roundup_usage_doc\', \'message\')">Any Additional Message</a>: </td>
<td><textarea rows="5" cols="50" name="message"></textarea></td>
</tr>

</table>

<div>
<input type="submit"/>
<input type="reset" />
</div>

</form>
</div>
';

  return $content;
}


function echoRawPage($formInfo, $genomes, $divergences, $evalues, $errors=NULL) {
  echoRoundupTemplate(makeRawContent($formInfo, $genomes, $divergences, $evalues, $errors));
}


function makeRawContent($formInfo, $genomes, $divergences, $evalues, $errors=NULL) {
  $content = '';

  $exampleData = getValueInMaps('example_data', array($formInfo));
  $data = $formInfo['data'];
  $id = $formInfo['id'];

  $content .= makeJSFormValuesScript($id, $data);
  $content .= makeJSFormValuesScript($id, $exampleData, 'example');
  $content .= makeJSFormLoadEvent($id);

  $content .= '<h2>Download Raw Data from the Roundup Orthology Database</h2>'."\n";
  $content .= '<div align="left"><a href="javascript:docWindow(\'roundup_usage_doc\', \'raw\')">Documentation</a> and '.makeJSSetFormLink($id, 'example', 'Example').'</div>'."\n";


  $content .= "<div><form action=\"index.php\" method=\"post\" id=\"$id\">";
  $content .= makeErrorsDiv($errors);
  $content .= "<input type=\"hidden\" name=\"action\" value=\"raw\" /><table class=\"paramTable\">";

  $content .= "<tr><td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'query_genome')\">".roundupDisplayName('query_genome')."</a>: </td>";
  $content .= "<td><select name=\"query_genome\">";
  foreach($genomes as $genome) {
    $content .= "<option value=\"$genome\">".roundupGenomeDisplayName($genome)."</option>\n";
  }
  $content .= "</select></td></tr>";

  $content .= "<tr><td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'subject_genome')\">".roundupDisplayName('subject_genome')."</a>: </td>";
  $content .= "<td><select name=\"subject_genome\">";
  foreach($genomes as $genome) {
    $content .= "<option value=\"$genome\">".roundupGenomeDisplayName($genome)."</option>\n";
  }
  $content .= "</select></td></tr>";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\"><a href=\"javascript:docWindow('roundup_usage_doc', 'divergence')\">".roundupDisplayName('divergence')."</a>: </td>";
  $content .= "<td><select name=\"divergence\">";
  foreach($divergences as $divergence) {
    $content .= "<option value=\"$divergence\">$divergence</option>\n";
  }
  $content .= "</select></td>";
  $content .= "</tr>\n";

  $content .= "<tr>\n";
  $content .= "<td class=\"label\">";
  $content .= "<a href=\"javascript:docWindow('roundup_usage_doc', 'evalue')\">".roundupDisplayName('evalue')."</a>: </td>";
  $content .= "<td><select name=\"evalue\">";
  foreach($evalues as $evalue) {
    $content .= "<option value=\"$evalue\">$evalue</option>\n";
  }
  $content .= "</select></td>";
  $content .= "</tr>\n";

  $content .= "</table><div><input type=\"submit\"/><input type=\"reset\" /></div></form></div>";

  return $content;

}


?>

