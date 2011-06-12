<?php

// This page contains functions for manipulating the results of functions dispatched to python.  Currently these results 
// are temporary and can be obtained in synchronous or asynchronous fashion.
//
// USAGE: write a python function.  write a php page which creates the keyword parameters to invoke the python function.
// write a function to render the return value (the result) of the python function.  require_once the php page that
// contains the rendering function.  Create a unique name for the result type and add it and the rendering function to
// the getResultRenderer function below.
// Then from your page invoke either echoSyncResult or echoAsyncWaitingResult.

require_once('roundup/roundup_template.php');
require_once('roundup/waiting.php');
require_once('roundup/roundup_util.php'); // for rendering results


// $urlParamSuffix: map of parameters and values.  Will be url encoded and appended to the result url.
function makeResultUrl($resultType, $resultId, $jobId=NULL, $templateType=NULL, $count=0, $otherUrlParams=NULL) {
  if ($otherUrlParams) {
    $otherParamsStr = '';
    foreach ($otherUrlParams as $param => $value) {
      $otherParamsStr .= '&'.rawurlencode($param).'='.rawurlencode($value);
    }
  } else {
    $otherParamsStr = '';
  }

  return "/roundup/result.php?result_type=$resultType&result_id=$resultId&job_id=$jobId&template_type=$templateType&count=$count".$otherParamsStr;
}


function makeResultFormUrl() {
  return "/roundup/result.php";
}


function makeResultFormHiddenInputsHtml($resultType, $resultId, $jobId=NULL, $templateType=NULL, $count=0, $otherUrlParams=NULL) {
  $html = "";
  $html .= "<input type=\"hidden\" name=\"result_type\" value=\"$resultType\" />\n";
  $html .= "<input type=\"hidden\" name=\"result_id\" value=\"$resultId\" />\n";
  $html .= "<input type=\"hidden\" name=\"job_id\" value=\"$jobId\" />\n";
  $html .= "<input type=\"hidden\" name=\"template_type\" value=\"$templateType\" />\n";
  $html .= "<input type=\"hidden\" name=\"count\" value=\"$count\" />\n";
  if ($otherUrlParams) {
    foreach ($otherUrlParams as $param => $value) {
      $html .= "<input type=\"hidden\" name=\"$param\" value=\"$value\" />\n";
    }
  }
  return $html;
}


function getResultRenderer($resultType) {
  if ($resultType == ROUNDUP_ORTHOLOGY_RESULT_TYPE) {
    return 'makeOrthologyResultContent';
  } elseif ($resultType == ROUNDUP_HAMMING_DISTANCE_RESULT_TYPE) {
    return 'makeHammingResultContent';  
  } elseif ($resultType == ROUNDUP_TEXT_RESULT_TYPE) {
    return 'makeRoundupTextResultContent';
  } elseif ($resultType == ROUNDUP_PHYLETIC_PATTERN_RESULT_TYPE) {
    return 'makePhyleticPatternResultContent';
  } elseif ($resultType == ROUNDUP_NEXUS_MATRIX_RESULT_TYPE) {
    return 'makeNexusMatrixResultContent';
  } elseif ($resultType == ROUNDUP_PHYLIP_MATRIX_RESULT_TYPE) {
    return 'makePhylipMatrixResultContent';
  } elseif ($resultType == ROUNDUP_RAW_RESULT_TYPE) {
    return 'makeRoundupRawResultContent';
  } elseif ($resultType == ROUNDUP_TERMS_SUMMARY_RESULT_TYPE) {
    return 'makeRoundupTermsSummaryContent';
  } elseif ($resultType == ROUNDUP_GENE_RESULT_TYPE) {
    return 'makeRoundupGeneContent';
  } elseif ($resultType == ROUNDUP_TERM_RESULT_TYPE) {
    return 'makeRoundupTermContent';
  } elseif ($resultType == 'roundup_gene_summary_result') {
    return 'makeRoundupGenesSummaryContent';
  } elseif ($resultType == ROUNDUP_TEST_RESULT_TYPE) {
    return 'makeRoundupTestResultContent';
  } else {
    logError("getResultRenderer(): Unknown result type: $resultType");
    return NULL;
  }
}

// python function executed locally and synchronously.  use async call for long jobs to spare the web server.
// results saved and displayed on "result" page.
function echoSyncLocalResult($fullyQualifiedFuncName, $keywords, $resultType, $templateType=NULL, $otherUrlParams=NULL) {
  $resultId = makeResultId();
  $resultFilename = getResultFilename($resultId);
  $cacheKey = serialize($keywords);
  list($fullyQualifiedFuncName, $keywords) = add_cache_dispatch($fullyQualifiedFuncName, $keywords, $cacheKey, $resultFilename);
  list($result, $exitcode) = python_dispatch($fullyQualifiedFuncName, $keywords);
  if ($exitcode) {
    echoRunCommandErrorPage();
  } else {
    forwardToResultPage($resultType, $resultId, NULL, $templateType, $otherUrlParams);
  }
}

// python function executed asynchronously on cluster and results saved.
// useful for long running jobs or jobs you might want user to be able to access the result to multiple times.
function echoAsyncGridWaitingResult($fullyQualifiedFuncName, $keywords, $resultType, $templateType=NULL, $otherUrlParams=NULL) {
  $resultId = makeResultId();
  $resultFilename = getResultFilename($resultId);
  $cacheKey = serialize($keywords);
  $lsfOptions = array('-N', '-q rodeo_12h'); # do not send an email when the job is done.  run on a rodeo lsf queue.
  list($fullyQualifiedFuncName, $keywords) = add_lsf_and_cache_dispatch($fullyQualifiedFuncName, $keywords, $lsfOptions, $cacheKey, $resultFilename);
  list($jobId, $exitcode) = python_dispatch($fullyQualifiedFuncName, $keywords);
  if ($exitcode) {
    echoRunCommandErrorPage();
  } else {
    forwardToResultPage($resultType, $resultId, $jobId, $templateType, $otherUrlParams);
  }
}


function echoResultPage($resultType, $resultId=NULL, $jobId=NULL, $templateType=NULL, $otherUrlParams) {
  logDebug('echoResultPage() ...');
  $renderer = getResultRenderer($resultType);
  echoTemplate("Results", $renderer($resultType, $resultId, $jobId, $templateType, $otherUrlParams), $templateType);
  logDebug('echoResultPage() ...');
}


function echoRunCommandErrorPage($cmd=NULL, $exitcode=NULL, $error=NULL) {
  echoTemplate("Error", "Error running a command.  Please contact Support.", ROUNDUP_PAGE_TEMPLATE);
  logError('echoRunCommandErrorPage: cmd=$cmd, exitcode=$exitcode, error=$error');
}


// Forwards to the result page.  
// THIS FUNCTION DOES NOT RETURN!
function forwardToResultPage($resultType, $resultId, $jobId=NULL, $templateType=NULL, $otherUrlParams=NULL) {
  forwardToPage(makeResultUrl($resultType, $resultId, $jobId, $templateType, 0, $otherUrlParams));
}


// e.g. f350b7a8-eeb8-102c-aca1-001a64239a78
function makeResultId() {
  return makeUUID();
}


// e.g. f350b7a8-eeb8-102c-aca1-001a64239a78 -> /groups/rodeo/roundup/tmp/e6/f8/roundup_web_result_f350b7a8-eeb8-102c-aca1-001a64239a78
function getResultFilename($resultId) {
  $keywords = array('dir' => TMP_ROOT, 'name' => "roundup_web_result_$resultId");
  list($path, $exitcode) = python_dispatch('nested.makeNestedPath', $keywords);
  if ($exitcode) {
    logError('getResultFilename(): exit code encountered when running roundup_common.makeNestedPath(). keywords='.serialize($keywords));
    // forward to generic error page.                                                                                                                         
    echoRunCommandErrorPage();
  }
  return $path;
}


// e.g. /groups/rodeo/roundup/tmp/e6/f8/roundup_web_result_f350b7a8-eeb8-102c-aca1-001a64239a78 -> f350b7a8-eeb8-102c-aca1-001a64239a78
function getResultIdFromFilename($resultFilename) {
  return preg_replace("/roundup_web_result_/", "", basename($resultFilename));
}


function echoWaitingOnResultPage($resultType, $resultId, $jobId=NULL, $templateType=NULL, $count=0, $otherUrlParams=NULL) {
  $pageTitle = "Waiting for Results";
  //logDebug("echoWaitingOnResultPage(): count=$count");
  $count = intval($count) + 1;
  echoTemplate($pageTitle, makeWaitingContent(makeResultUrl($resultType, $resultId, $jobId, $templateType, $count, $otherUrlParams)), $templateType);

}


function echoUnavailableResultPage($resultType, $resultId, $jobId=NULL, $templateType=NULL, $count=0, $otherUrlParams=NULL) {
  echoTemplate("Unavailable Result", "The result page you requested is unavailable.  Please <a href=\"/support\">report this</a> if you think an error might have occurred.", $templateType);
}


// $resultId: id of the orthology query result.
// Before using this function, check if the result exists with orthologyResultExists()
// returns: the result associated with the result id.  If the result does not exist, the behavior of this function is undefined.
function getResult($resultId) {
  if (resultExists($resultId)) {
    $keywords = array('resultId' => $resultId);
    list($result, $exitcode) = python_dispatch('format_orthology_cluster_result.getResult', $keywords);
    return $result;
  } else {
    return NULL;
  }
}


function resultExists($resultId) {
  $resultFilename = getResultFilename($resultId);
  return (is_file($resultFilename) && is_readable($resultFilename));
}


function nonEmptyResultExists($resultId) {
  $resultFilename = getResultFilename($resultId);
  return (resultExists($resultId) && filesize($resultFilename));
}


// $otherUrlParams: map of params and values.
function resultPageControlFlow($resultType, $resultId, $jobId=NULL, $templateType=NULL, $count=0, $otherUrlParams) {
  if ($jobId && isLSFJobProcessing($jobId)) {
    echoWaitingOnResultPage($resultType, $resultId, $jobId, $templateType, $count, $otherUrlParams);
  } elseif (resultExists($resultId)) {
    echoResultPage($resultType, $resultId, $jobId, $templateType, $otherUrlParams);
  } else {
    echoUnavailableResultPage($resultType, $resultId, $jobId, $templateType, $count, $otherUrlParams);
  }
}


?>
