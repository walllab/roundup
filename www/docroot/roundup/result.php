<?php

// Retrieve and display results of various types.  Possibly wait for result to be finished.

require_once('roundup/result_util.php');
require_once('roundup/forms.php');
require_once('roundup/common.php');
//require_once('roundup/roundup_template.php');

// some results take a long time to render
ini_set("max_execution_time", "3600");

$resultData = makeForm($_REQUEST, 
		       array('result_id', 'job_id', 'result_type', 'template_type', 'count'));
		       //		       array('job_id' => NULL, 'template_type' => ROUNDUP_WIDE_TEMPLATE, 'count' => 0));
$otherParams = rodeo_array_diff_key(makeForm($_REQUEST), $resultData);
logDebug('roundup/result.php otherParams='.serialize($otherParams));

resultPageControlFlow($resultData['result_type'], $resultData['result_id'], $resultData['job_id'], $resultData['template_type'], $resultData['count'], $otherParams);


?>