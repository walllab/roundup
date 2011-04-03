<?php
// GOAL: PUT COMMONLY USED FUNCTIONALITY IN ONE FILE
//
// Does not do authentication
// Does start session management
// Does abstract database access and logging.
// Does define some request parameters
// Does have a string formatting function



// HACK: this cheap hack assumes that dev instances all have a ROUNDUP_MYSQL_DB value starting with 'dev'
// and that otherwise we are in a prod instance.
if ($_SERVER['ROUNDUP_MYSQL_DB'] == 'roundup') {
  //prod
  $CACHE_MYSQL_DB = 'roundup';
  define('HTTP_HOST', 'roundup.hms.harvard.edu'); // used in common.php
  define('PHP_LOG_FILE', '/groups/rodeo/roundup/log/php_roundup.log'); // used in logging.php
  define('ROUNDUP_ROOT', '/groups/rodeo/roundup/python'); // used in common.php
  define('RODEO_LOGGING_MAIL_FROM_ADDR', 'rodeo-noreply@med.harvard.edu'); // used in common.php and logging.php
  define('RODEO_LOGGING_MAIL_SUBJECT', 'Prod Roundup Logging Message'); // common.php and logging.php
  define('RODEO_LOGGING_MAIL_TO_ADDRS', 'kristian_stgabriel@hms.harvard.edu,todd_deluca@hms.harvard.edu,dennis_wall@hms.harvard.edu,tom_monaghan@hms.harvard.edu'); //common.php and logging.php
  define('RODEO_LSF_EMAIL_TO_ADDR', 'kristian_stgabriel@hms.harvard.edu'); //used in LSF.php
  define('TMP_ROOT', '/groups/rodeo/roundup/tmp'); // result_util.php
  putenv("ROUNDUP_RESULTS_DIR=/groups/rodeo/roundup/results");
  putenv("ROUNDUP_GENOMES_DIR=/groups/rodeo/roundup/genomes");
} else {
  //dev
  $CACHE_MYSQL_DB = 'devroundup'; 
  define('HTTP_HOST', 'dev.roundup.hms.harvard.edu'); // used in common.php
  define('PHP_LOG_FILE', '/groups/rodeo/dev.roundup/log/php_roundup.log'); // used in logging.php
  define('ROUNDUP_ROOT', '/groups/rodeo/dev.roundup/python'); // used in common.php
  define('RODEO_LOGGING_MAIL_FROM_ADDR', 'rodeo-noreply@med.harvard.edu'); // used in common.php and logging.php
  define('RODEO_LOGGING_MAIL_SUBJECT', 'Dev Roundup Logging Message'); // common.php and logging.php
  define('RODEO_LOGGING_MAIL_TO_ADDRS', 'kristian_stgabriel@hms.harvard.edu,todd_deluca@hms.harvard.edu'); //common.php and logging.php
  define('RODEO_LSF_EMAIL_TO_ADDR', 'kristian_stgabriel@hms.harvard.edu'); //used in LSF.php
  define('TMP_ROOT', '/groups/rodeo/dev.roundup/tmp'); // result_util.php
  putenv("ROUNDUP_RESULTS_DIR=/groups/rodeo/dev.roundup/results");
  putenv("ROUNDUP_GENOMES_DIR=/groups/rodeo/dev.roundup/genomes");
}




####################
# SESSION MANAGEMENT
####################
// Fix for IE 6 session - post issues
session_cache_limiter('private');
session_start();
// Fix for IE 6 session - post issues
// header("Cache-Control: private"); 
isset($_SESSION['userid']) ? $userid = $_SESSION['userid'] : $userid = NULL;

###############################
# DEBUGGING AND ERROR REPORTING
###############################
// Report all PHP errors (bitwise 63 may be used in PHP 3)
error_reporting(E_ALL);



###########
# CONSTANTS
###########

define('READ_FLAG', 1);
define('FORM', 'FORM');
define('ERRORS', 'ERRORS');
define('RESET_FORM', 'RESET_FORM');
define('RODEO_LOGGING_LEVEL', 10); // used in logging.php
define('ROUNDUP_TOOL_TITLE', 'RoundUp Orthology Database'); // roundup_util.php


####################################
# ADD PYTHON ROOT TO THE PYTHON PATH
####################################
putenv("PYTHONPATH=".ROUNDUP_ROOT);
// HACK: all modifications of PATH are in LSF.php, since using getenv and putenv to modify
// an env var multiple times overwrites previous modifications.





####################
# REQUEST PARAMETERS
###################

define('TYPE', 'type');
define('JOBID', 'jobid');
define('SEQID', 'seqid');
define('IMG', 'img');


##############################
# PYTHON INTERACTION FUNCTIONS
##############################


// Call a python function 'directly' from php.  Now you can write more python and less php.
// Limitations: slower than a native function call.  Must pass all params as keywords.
// $fullyQualifiedFuncName: full name of function to call, e.g. 'mypackage.mymodule.myclassinstance.myfunc'
// $keywords: array of keyword parameters to function, e.g. array('username' => 'foo', 'isSpecial' => true, 'numResults' => 30)
function python_dispatch($fullyQualifiedFuncName, $keywords=NULL) {
  if ($keywords === NULL) {
    $stdin = '';
  } else {
    $stdin = serialize($keywords);
  }
  $cmd = ROUNDUP_ROOT."/phpdispatch.py ";
  $cmd .= escapeshellarg($fullyQualifiedFuncName); 
  list($exitcode, $stdout, $stderr) = runCommand($cmd, $stdin);
  $retval = unserialize($stdout);
  return array($retval, $exitcode);
}

// Instead of returning the result of fullyQualifiedFuncName(), saves it to a file and adds the file to the rodeo_cache.  
// Useful for caching expensive functions with big/weird keys.
// E.g. roundup orthology query results are saved to a file and the serialized query itself is used as the key.
// Note: fullyQualifiedFuncName() output is pickled (python serialized) and stored in $cacheFilename.
function add_cache_dispatch($fullyQualifiedFuncName, $keywords, $cacheKey, $cacheFilename) {
  $newKeywords = array('fullyQualifiedFuncName' => $fullyQualifiedFuncName, 'keywords' => $keywords, 'cacheKey' => $cacheKey, 'outputPath' => $cacheFilename);
  $newFullyQualifiedFuncName = 'roundup_util.cacheDispatch';
  return array($newFullyQualifiedFuncName, $newKeywords);  
}

// Run an expensive function on the LSF cluster.
// Use in combination with add_cache_dispatching() to save results.
function add_lsf_dispatch($fullyQualifiedFuncName, $keywords, $lsfOptions) {
  $newKeywords = array('fullyQualifiedFuncName' => $fullyQualifiedFuncName, 'keywords' => $keywords, 'lsfOptions' => $lsfOptions);
  $newFullyQualifiedFuncName = 'lsfdispatch.dispatch';
  return array($newFullyQualifiedFuncName, $newKeywords);  
}  

// use to create a func, keywords pair for python_dispatch() that runs a function on lsf, caching its output in a file and storing a cache key in the rodeo_cache.
function add_lsf_and_cache_dispatch($fullyQualifiedFuncName, $keywords, $lsfOptions, $cacheKey, $cacheFilename) {
  list($fullyQualifiedFuncName, $keywords) = add_cache_dispatch($fullyQualifiedFuncName, $keywords, $cacheKey, $cacheFilename);
  return add_lsf_dispatch($fullyQualifiedFuncName, $keywords, $lsfOptions);
}  


##########################
# PROCESS/SCRIPT EXECUTION
##########################
// $cmd is the command to execute
// $stdin is the input to the command, if any
// returns an array of the exitcode of command, its standard output, and standard error 
function runCommand($cmd, $stdin='') {
  $stdout = '';
  $stderr = '';
  $exitcode = 1; //defaults to generic error code.

  logDebug('runCommand: $cmd='.$cmd);

  $descriptorspec = array(0 => array("pipe", "r"),  
                          1 => array("pipe", "w"),  
                          2 => array("pipe", "w"));
  $process = proc_open($cmd, $descriptorspec, $pipes);
  if (is_resource($process)) {
    // $pipes now looks like this:
    // 0 => writeable handle connected to child stdin
    // 1 => readable handle connected to child stdout
    // 2 => readable handle connected to child stderr

    //write the input
    fwrite($pipes[0], $stdin);
    fclose($pipes[0]);
    
    //read the output
    while (!feof($pipes[1])) {
      $stdout .= fgets($pipes[1], 1024);
    }
    fclose($pipes[1]);

    while (!feof($pipes[2])) {
      $stderr .= fgets($pipes[2], 1024);
    }
    fclose($pipes[2]);

    // It is important that you close any pipes before calling
    // proc_close in order to avoid a deadlock
    $exitcode = proc_close($process);
  } else {
    logError("[ERROR] proc_open call failed to create a resource.");
    $exitcode = 1; // error running command
  }
  if ($exitcode != 0) {
    logError("runCommand(): non-zero exit code\n\texitcode=".$exitcode."\n\tstdout=".$stdout."\n\tstderr=".$stderr);
  }
  return array($exitcode, $stdout, $stderr);
}


################################
//    Uses mysql UUID() function to generate a universally unique string, like 41c2804e-9911-1028-8d31-000d601ab426.
//    returns: universally unique string or 0 if an error occurs.
################################

function makeUUID($link=0) {
  if (!$link) {
    $link = connectAndSelectRodeoDb();
    $closeLink = 1;
  } else {
    $closeLink = 0;
  }

  //returns true on success, false on error.
  $result = mysql_query('SELECT UUID()', $link);
  if (!$result) {
    logError("[ERROR] makeUUID().  SQL query failed.n. mysql_error=".mysql_error($link));
    $uuid = 0;
  } else {
    list($uuid) = mysql_fetch_row($result);
  }

  if ($closeLink) {
    mysql_close($link);
  }

  return $uuid;
}



#################
# ARRAY FUNCTIONS
#################

// This is an implementation of the standard library function array_diff_key
// for php versions < 5.1.0RC1.
function rodeo_array_diff_key($arr1, $arr2) {
  $keys1 = array_keys($arr1);
  $keys2 = array_keys($arr2);
  $diffKeys = array_diff($keys1, $keys2);
  $diffArr = array();
  foreach ($diffKeys as $key) {
    $diffArr[$key] = $arr1[$key];
  }
  return $diffArr;
}


// similar to php standard library array_unique, except whereas array_unique
// test equality with (string) $elem1 === (string) $elem2, this function uses
// in_array(), which probably does something more like $elem1 == $elem2.  
// This allows array elements of $arr to be compared reasonably.
// The motivation for this function:
// $foo = array(array(1), array(1), array(2), array(3));
// print_r(array_unique($foo));
// print_r(common_array_unique($foo));
function common_array_unique($arr) {
  $set = array();
  foreach ($arr as $key => $val) {
    if (!in_array($val, $set)) {
      $set[$key] = $val;
    }
  }
  return $set;
}


// $set: array of values
// returns: every unique (unordered) combination of two different values from $set. 
//   Each pair is sorted and the list of pairs is sorted.
// e.g. $set = array(3, 2, 5, 4). result is array(array(2,3), array(2,4), array(2,5), array(3,4), array(3,5), array(4,5))
function choose2($set) {
  $pairs = array();
  // call unique before set, b/c unique sort of preserves keys, but sort renumbers the array consecutively
  // and that is what the for loops require.
  $set = array_unique($set);
  sort($set);
  for ($i = 0; $i < count($set) - 1; $i++) {
    for ($j = $i+1; $j < count($set); $j++) {
      $pair = array($set[$i], $set[$j]);
      sort($pair);
      $pairs[] = $pair;
    }
  }
  return $pairs;
}

#################
# JAVASCRIPT CODE
#################


// DEPRECATED. USE javascriptSerialize().
function makeList($list) {
  return javascriptSerialize($list);
}


// turns php variable into a javascript literal.  Works for scalars and arrays.  Does not handle cycles or DAGs.
// If the array keys are integers from 0 to n-1, assumes the array is a list and serializes it as a javascript Array.
// Otherwise it serializes a php array as a javascript object/map/dict.
// e.g. array('foo', 'bar') -> ['foo', 'bar']
// e.g. array(array("Johnny's Foodmaster", "Rock\Style")) -> [['Johnny\'s Foodmaster', 'Rock\\Style']]
function javascriptSerialize($item) {
  if (!isset($item)) {
    return 'null';
  } elseif (is_scalar($item)) {
    return javascriptSerializeAtom($item);
  } elseif (is_array($item)) {
    $keys = array_keys($item);
    sort($keys);
    // assume an empty array or an array with only integer keys from 0..n-1 is a list
    if ((!in_array(false, array_map('is_int', $keys))) && (count($keys) == 0 || count($keys) == $keys[count($keys)-1]+1)) {
      return "[" . join(", ", array_map('javascriptSerialize', $item)) . "]";
    } else {
      return '{' . join(", ", array_map(create_function('$k,$v','return javascriptSerialize($k).": ".javascriptSerialize($v);'), array_keys($item), array_values($item))) . '}';
    }
  } else {
    return 'null';
  }
}

// $atom: a scalar value
// returns a javascript literal equivalent to the scalar value.  Attempts to escape strings into a correct javascript literal, 
//   but might not be very robust.  You are warned.
function javascriptSerializeAtom($atom) {
  if (is_null($atom)) {
    return 'null';
  } elseif (is_string($atom)) {
    $str = strval($atom);
    $str = str_replace("\\", "\\\\", $str);
    $str = str_replace("'", "\\'", $str);
    $str = str_replace("\"", "\\\"", $str);
    $str = str_replace("\n", '\n', $str);
    $str = str_replace("\r", '\r', $str);
    $str = str_replace("\t", '\t', $str);
    return "'".$str."'";
  } elseif (is_numeric($atom)) {
    return strval($atom);
  } elseif (is_bool($atom)) {
    return $atom ? 'true' : 'false';
  } else {
    return 'null';
  }
}


#################
# DATABASE ACCESS
#################

function dbEscapeString($str, $link=0) {
  if (!$link) {
    $link = connectAndSelectRodeoDb();
    $closeLink = 1;
  } else {
    $closeLink = 0;
  }

  //returns true on success, false on error.
  $safeStr = mysql_real_escape_string($str, $link);
  if ($closeLink) {
    mysql_close($link);
  }

  return $safeStr;
}


function connectToRodeoDb() {
  return mysql_connect($_SERVER['ROUNDUP_MYSQL_SERVER'], $_SERVER['ROUNDUP_MYSQL_USER'], $_SERVER['ROUNDUP_MYSQL_PASSWORD']);
}

function selectRodeoDb() {
  return mysql_select_db($_SERVER['ROUNDUP_MYSQL_DB']);
}

// should throw an exception if an error occurs.
function connectAndSelectRodeoDb() {
  $link = mysql_connect($_SERVER['ROUNDUP_MYSQL_SERVER'], $_SERVER['ROUNDUP_MYSQL_USER'], $_SERVER['ROUNDUP_MYSQL_PASSWORD']);
  mysql_select_db($_SERVER['ROUNDUP_MYSQL_DB']);
  return $link;
}


// Executes $query.
// returns: true iff $query was successfully executed.
function executeQuery($query,  $link=0) {
  if (!$link) {
    $link = connectAndSelectRodeoDb();
    $closeLink = 1;
  } else {
    $closeLink = 0;
  }

  //returns true on success, false on error.
  $success = (bool) mysql_query($query, $link);
  if (!$success) {
    logDebug("[ERROR] executeQuery.  query=$query, mysql_error=".mysql_error($link));
  } 

  if ($closeLink) {
    mysql_close($link);
  }

  return $success;
}


// returns: number of rows affected or -1 on error.
function updateQuery($query, $link=0) {
  if (!$link) {
    $link = connectAndSelectRodeoDb();
    $closeLink = 1;
  } else {
    $closeLink = 0;
  }

  //returns true on success, false on error.
  $result = mysql_query($query, $link);
  $numRows = mysql_affected_rows($link);
  if ($numRows == -1) {
    logDebug("[ERROR] updateQuery.  query=$query, mysql_error=".mysql_error($link));
  } 

  if ($closeLink) {
    mysql_close($link);
  }

  return $numRows;
}

// $query is a SQL INSERT statement (to insert a single row.)
// returns id of inserted query or 0 if there was a problem.
// If the table being inserted into doesn't have an autoincrement id column
// I do not know how this will behave.
function insertQuery($query, $link=0) {
  if (!$link) {
    $link = connectAndSelectRodeoDb();
    $closeLink = 1;
  } else {
    $closeLink = 0;
  }

  $result = mysql_query($query, $link);
  if (!$result) {
    logDebug("[ERROR] insertQuery().  Failed insertion. query=$query, mysql_error=".mysql_error($link));
    $insertid = 0;
  } else {
    $insertid = mysql_insert_id($link);
    if (!$insertid) {
      logDebug("[ERROR] insertQuery().  Bad insertid. insertid=$insertid, query=$query, mysql_error=".mysql_error($link));
    }
  }

  if ($closeLink) {
    mysql_close($link);
  }

  return $insertid;
}


// $query of form 'SELECT COUNT(*) FROM ...' 
// returns the count or -1 on error. (Should throw exception on error?)
function countQuery($query, $link=0) {
  if (!$link) {
    $link = connectAndSelectRodeoDb();
    $closeLink = 1;
  } else {
    $closeLink = 0;
  }

  // returns false on error
  $result = mysql_query($query, $link);
  if (!$result) {
    logDebug("[ERROR] countQuery().  query=$query, mysql_error=".mysql_error($link));
    $count = -1;
  } else {
    list($count) = mysql_fetch_row($result);
  }

  if ($closeLink) {
    mysql_close($link);
  }

  return $count;
}


// $query of form 'DELETE FROM ... WHERE ...'
// returns number of rows affected or -1 on error.
function deleteQuery($query, $link=0) {
  if (!$link) {
    $link = connectAndSelectRodeoDb();
    $closeLink = 1;
  } else {
    $closeLink = 0;
  }

  // returns false on error
  $result = mysql_query($query, $link);
  $numRows = mysql_affected_rows($link);
  if ($numRows == -1) {
    logDebug("[ERROR] deleteQuery.  query=$query, mysql_error=".mysql_error($link));
  } 

  if ($closeLink) {
    mysql_close($link);
  }

  return $numRows;
}


#############################
# STRING FORMATTING FUNCTIONS
#############################

function truncate($substring, $max = 30, $rep = '...') {
       if(strlen($substring) < 1){
           $string = $rep;
       }else{
           $string = $substring;
       }
      
       $leave = $max - strlen ($rep);
      
       if(strlen($string) > $max){
           return substr_replace($string, $rep, $leave);
       }else{
           return $string;
       }
      
   }


###########################
# NUMERIC UTILITY FUNCTIONS
###########################

// $var: string or number
// returns true if $var is a number or string that can be converted to a number (e.g. "1.56e-12") 
// and that number is an integer.
// this function is derived from http://us2.php.net/manual/en/function.is-numeric.php#55615, improved to handle scientific notation.

function is_integer_number($var) {
  return is_numeric($var) && (intval(floatval($var)) == floatval($var));
}


function is_counting_number($var) {
  return is_integer_number($var) && (intval($var) > 0);
}


##########################
# AUTHENTICATION CONSTANTS
##########################
define('LOGIN_FORM_URI', '/portal/login.php');
define('SUPPORT_FORM_URI', '/support/index.php');
define('REGISTRATION_FORM_URI', '/registration/index.php');
define('REGISTRATION_SUBMIT_URI', '/registration/register.php');
define('REGISTRATION_RECEIVED_URI', '/registration/received.php');

define('AUTH_REGISTERED', 'AUTH_REGISTERED');
define('AUTH_AUTHENTICATED', 'AUTH_AUTHENTICATED');
define('AUTH_LOGGED_IN', 'AUTH_LOGGED_IN');
define('AUTH_SETUP', 'AUTH_SETUP');
define('AUTH_ECOMMONS_ID', 'AUTH_ECOMMONS_ID');
define('AUTH_USER_ID', 'AUTH_USER_ID');
define('AUTH_USER_EMAIL', 'AUTH_USER_EMAIL');

######################################
# AUTHENTICATION PREDICATES AND CHECKS
######################################

// predicate: returns true if the current session is logged in.
// if a user is logged in, then AUTH_ECOMMONS_ID, AUTH_USER_ID, and 
// AUTH_USER_EMAIL are all defined.
function isLoggedIn() {
  return isset($_SESSION[AUTH_LOGGED_IN]) && $_SESSION[AUTH_LOGGED_IN];
}

function isAuthenticated() {
  if (!isset($_SESSION[AUTH_AUTHENTICATED])) {
    $_SESSION[AUTH_AUTHENTICATED] = (isLoggedIn() && isSetup());
  }
  return $_SESSION[AUTH_AUTHENTICATED];
}

function isSetup() {
  if (!isset($_SESSION[AUTH_SETUP])) {
    checkDbForSetup();
  }
  return isset($_SESSION[AUTH_SETUP]) && $_SESSION[AUTH_SETUP];
}


// if the user is logged in
// sets the session session variable to true or false
// depending on whether the setup column for the user is 'ye' or 'no'
function checkDbForSetup() {
  if (!isLoggedIn()) { return; }

  $userid = $_SESSION[AUTH_USER_ID];

  $link = connectAndSelectRodeoDb();

  $query = "SELECT setup FROM rodeo_users WHERE userid = $userid";
  $results = mysql_query($query) or die("Could not access the database: " . mysql_error());
  if (mysql_num_rows($results)) {
    list($setup) = mysql_fetch_row($results);
    if ($setup == 'ye') { 
      $_SESSION[AUTH_SETUP] = true;
    } elseif ($setup = 'no') {
      $_SESSION[AUTH_SETUP] = false;
    } else {
      unset($_SESSION[AUTH_SETUP]);
    }
  } else {
    logDebug("[WARNING] checkDbForSetup(): failed to get setup info from db for userid=$userid");
  }
  mysql_close($link);

  return;
}


function isRegistered() {
  if (!isset($_SESSION[AUTH_REGISTERED])) {
    checkDbForRegistration();
  }
  return isset($_SESSION[AUTH_REGISTERED]) && $_SESSION[AUTH_REGISTERED];
}

// if the user is logged in
// sets the registration session variable to true or false
// depending on whether there is a registration for that user (ecommonsid)
function checkDbForRegistration() {
  if (!isLoggedIn()) { return; }

  $ecommons = strtolower($_SESSION[AUTH_ECOMMONS_ID]);

  $query = "SELECT count(*) FROM rodeo_registration r WHERE r.ecommons = '$ecommons'";
  $numRegistrations = countQuery($query);

  // blatantly ignore errors.
  if ($numRegistrations < 0) {
    $numRegistrations = 0; 
  }

  $_SESSION[AUTH_REGISTERED] = $numRegistrations;
  return $numRegistrations;
}


#################
# PAGE FORWARDING
#################

define('BLAST_QUERY_PAGE', '/tools/blast/query.php');
define('REGISTRATION_FORM_PAGE', '/registration/index.php');
define('SUPPORT_PAGE', '/support');

// Forwards to the login page.  
// THIS FUNCTION DOES NOT RETURN!
function forwardToLogin() {
  forwardToPage("/portal/login.php");
}

// Forwards to the registration page.  
// THIS FUNCTION DOES NOT RETURN!
function forwardToRegistration() {
  forwardToPage("/registration/index.php");
}

// THIS FUNCTION DOES NOT RETURN!
function forwardToReceivedRegistration() {
  forwardToPage("/registration/received.php");
}

// $page should be a docroot absolute address
// e.g. "/registration/index.php"
// THIS FUNCTION DOES NOT RETURN!
function forwardToPage($page) {
  header("Location: http://{$_SERVER['HTTP_HOST']}$page");
  # Make sure that code below does not get executed when we redirect.
  exit;
}


###################
# SHARING FUNCTIONS
###################

function isShared($userid, $objectid) {
  $link = connectAndSelectRodeoDb();

  $query = "SELECT count(*) FROM rodeo_shares c WHERE c.objectid = $objectid AND c.userid = $userid";
  $results = mysql_query($query) or die("Could not access the database: " . mysql_error());
  list($shared) = mysql_fetch_row($results);
  mysql_close($link);

  return $shared;
}

function getOwnerIdForSharedObj($objectid) {
  $link = connectAndSelectRodeoDb();

  //seqid gets me the share, join with seqs join with jobs, get owner userid
  $query = "SELECT j.userid FROM bs_results_jobs j, rodeo_shares c, bs_results_seqs s";
  $query .= " WHERE c.objectid = $objectid AND c.objectid = s.seqid AND s.jobid = j.jobid";
  $results = mysql_query($query) or die("Could not access the database: " . mysql_error());
  list($ownerid) = mysql_fetch_row($results);
  mysql_close($link);

  return $ownerid;
}

function markSeqAsRead($seqid) {
  $link = connectAndSelectRodeoDb();
  logDebug("READ_FLAG=".READ_FLAG);

  $query = "UPDATE bs_results_seqs s SET s.marked = ".READ_FLAG." WHERE s.seqid = $seqid";
  $results = mysql_query($query) or die("Could not access the database: " . mysql_error());
  if (!$results) {
    logDebug("[ERROR] markSeqAsRead(): failed to update db. query=$query");
  }

  mysql_close($link);
}

function markSharedObjAsRead($userid, $objectid) {
  $link = connectAndSelectRodeoDb();

  $query = "UPDATE rodeo_shares c SET c.marked = ".READ_FLAG." WHERE c.objectid = $objectid AND c.userid = $userid";  
  $results = mysql_query($query) or die("Could not access the database: " . mysql_error());
  if (!$results) {
    logDebug("[ERROR] markShareAsRead(): failed to update db. query=$query");
  }

  mysql_close($link);
}

#################
# LOGOUT FORWARD
#################

if (isset($_REQUEST['action']) && $_REQUEST['action'] == 'logout') {
  logout();
  forwardToLogin();
}

#################
# LOGIN FORWARD
#################

if (isset($_REQUEST['action']) && $_REQUEST['action'] == 'login') {
  clearSession();
  login();
}

#################
# GET FULL NAME
#################

function getFullName($ecommons) {
  $link = connectAndSelectRodeoDb();
  
  $query = "SELECT firstname, lastname FROM rodeo_registration WHERE ecommons = '$ecommons'";
  $results = mysql_query($query) or die("Could not access the database: " . mysql_error());
  list ($firstname, $lastname) = mysql_fetch_row($results);
  mysql_close($link);

$_SESSION['firstname'] = $firstname;
$_SESSION['lastname'] = $lastname;

  return;
}

// getProps()
// $str: string of lines of the form 'key=value\n'
// splits $str into lines.  creates an array of the key and value from each line.
// ignores lines which do not have an '=' char.  ignores lines whose first non-whitespace
// character is '#'
function getProps($str) {
  $props = array();
  $lines = explode("\n", $str);
  foreach($lines as $line){
    // ignore comment lines and lines not containing '='.
    if ((strpos(ltrim($line), '#') !== 0) and (strpos($line, '=') !== false)) {
      list($key, $value) = explode("=", $line);
      $props[$key] = $value;
    }
  }
  return $props;
}

##############################
# BIO DATABASE MODEL FUNCTIONS
##############################

function getDbNameOrId($dbId) {
  $name = getDbName($dbId);
  return ($name ? $name : $dbId);
}
  
function getDbName($dbId) {
  $safeId = dbEscapeString($dbId);
  connectAndSelectRodeoDb();
  $resultsquery = "SELECT uud.dbname FROM uploaded_user_dbs uud WHERE uud.filepath = '$safeId'";
  $resultsoutput = mysql_query($resultsquery);
  if ($row = mysql_fetch_assoc($resultsoutput)) {
    return $row['dbname'];
  } else {
    return NULL;
  }
}

// $form: array of keys and values to be mailed.
// $subject: description/explanation of the form
// $toAddrs: comma separated string of addresses of who to mail the form to.
// This helper function is used to mail form data to us in one easy step.
// returns: nothing.
function emailForm($form, $subject, $toAddrs=RODEO_LOGGING_MAIL_TO_ADDRS) {
  $msg = print_r($form, TRUE);
  $fromAddr = "From: rodeo-noreply@rodeo.med.harvard.edu";
  mail($toAddrs, stripslashes($subject), stripslashes($msg), $fromAddr);
}


#########
# CACHING
#########

# cache stores a map from key strings to value strings.
# if you want to use non-string values in the cache, consider serializing them.
# cache uses mysql.

function cache_has_key($key) {
  global $CACHE_MYSQL_DB;
  $safeKey = dbEscapeString(cache_hash($key));
  $sql = " SELECT COUNT(*) FROM $CACHE_MYSQL_DB.roundup_cache WHERE id='$safeKey' ";
  $count = countQuery($sql);
  return $count > 0;
}


function cache_get($key) {
  global $CACHE_MYSQL_DB;
  $safeKey = dbEscapeString(cache_hash($key));
  $sql = " SELECT value FROM $CACHE_MYSQL_DB.roundup_cache WHERE id='$safeKey' ";
  $link = connectAndSelectRodeoDb();
  $results = mysql_query($sql) or die("Could not access the database: " . mysql_error());
  $row = mysql_fetch_row($results);
  if ($row) {
    $value = $row[0];
  } else {
    $value = NULL;
  }
  mysql_close($link);

  cache_touch($key);

  return $value;
}


// inserts key and value into cache setting mod_time and access_time.  if key was not already in cache, create_time is also set.
function cache_set($key, $value) {
  global $CACHE_MYSQL_DB;
  $safeKey = dbEscapeString(cache_hash($key));
  $safeValue = dbEscapeString($value);
  $sql = "INSERT INTO $CACHE_MYSQL_DB.roundup_cache (id, value, create_time, mod_time, access_time) VALUES ('$safeKey', '$safeValue', NOW(), NOW(), NOW()) ";
  $sql .= " ON DUPLICATE KEY UPDATE value='$safeValue', mod_time=NOW(), access_time=NOW() ";
  insertQuery($sql);
  return $value;
}


// removes key (and its value) completely from cache if it exists in cache.
function cache_remove($key) {
  global $CACHE_MYSQL_DB;
  $safeKey = dbEscapeString(cache_hash($key));
  $sql = "DELETE FROM $CACHE_MYSQL_DB.roundup_cache WHERE id='$safeKey' ";
  $count = deleteQuery($sql);
}


// update access_time in cache if key exists in cache.
function cache_touch($key) {
  global $CACHE_MYSQL_DB;
  $safeKey = dbEscapeString(cache_hash($key));
  $sql = "UPDATE $CACHE_MYSQL_DB.roundup_cache SET access_time=NOW() WHERE id='$safeKey'";
  updateQuery($sql);
}


function cache_hash($key) {
  $hash = sha1($key);
  logDebug("cache_hash: key=$key\nhash=$hash");
  return $hash;
}


function cache_create() {
  global $CACHE_MYSQL_DB;
  $sql = "CREATE TABLE IF NOT EXISTS $CACHE_MYSQL_DB.roundup_cache (id CHAR(40) NOT NULL PRIMARY KEY, value MEDIUMTEXT, 
create_time DATETIME, mod_time DATETIME, access_time DATETIME)";
  executeQuery($sql);
}


#################################
# LOGGING LOGGING LOGGING LOGGING 
#################################

class Logging {

  const NOTSET = 0;
  const DEBUG = 10;
  const INFO = 20;
  const WARNING = 30;
  const ERROR = 40;

  public $minLevel = self::NOTSET;
  public $handlers = array();

  public function __construct($handlers, $minLevel = NULL) {  
    if ($minLevel === NULL) {
      $this->minLevel = self::NOTSET;
    } else {
      $this->minLevel = $minLevel;
    }
    $this->handlers = $handlers;
  }
    
  public function debug($msg) {
    $this->message($msg, self::DEBUG);
  }
  public function info($msg) {
    $this->message($msg, self::INFO);
  }
  public function warning($msg) {
    $this->message($msg, self::WARNING);
  }
  public function error($msg) {
    $this->message($msg, self::ERROR);
  }
  public function message($msg, $level) {
    if ($level >= $this->minLevel) {
      foreach ($this->handlers as $handler) {
	$handler->handle($msg, $level);
      }
    }
  }
}

class LoggingHandler {
  public $minLevel = Logging::NOTSET;

  public function __construct($minLevel = NULL) {  
    if ($minLevel === NULL) {
      $this->minLevel = Logging::NOTSET;
    } else {
      $this->minLevel = $minLevel;
    }
  }

  public function handle($msg, $level) {
    if ($level >= $this->minLevel) {
      $this->subHandle($this->format($msg));
    }
  }

  protected function format($msg) {
    return date("c").": $msg\n";
  }

  protected function subHandle($msg) {
    return;
  }

}

class FileHandler extends LoggingHandler {
  public $filename = '/dev/null';

  public function __construct($filename, $minLevel = NULL) {  
    parent::__construct($minLevel);
    $this->filename = $filename;
  }

  protected function subHandle($msg) {
    $log = fopen($this->filename, 'ab');
    fwrite($log, $msg);
    fclose($log);
  }
}

class EmailHandler extends LoggingHandler {
  public $toAddrs = array();
  public $fromAddr = '';
  public $subject = '';

  public function __construct($fromAddr, $toAddrs, $subject, $minLevel = NULL) {  
    parent::__construct($minLevel);
    $this->toAddrs = $toAddrs;
    $this->fromAddr = $fromAddr;
    $this->subject = $subject;
  }

  protected function subHandle($msg) {
    $mailto = implode(', ', $this->toAddrs);
    mail($mailto, stripslashes($this->subject), stripslashes($msg), "From: ".$this->fromAddr);
  }
}

$logging = new Logging(array(new FileHandler(PHP_LOG_FILE), 
			     new EmailHandler(RODEO_LOGGING_MAIL_FROM_ADDR, 
					      explode(',', RODEO_LOGGING_MAIL_TO_ADDRS), 
					      RODEO_LOGGING_MAIL_SUBJECT,
					      Logging::ERROR)),
		       RODEO_LOGGING_LEVEL);


function logDebug($msg) {
  global $logging;
  $logging->debug($msg);
}

function logInfo($msg) {
  global $logging;
  $logging->info($msg);
}

function logWarning($msg) {
  global $logging;
  $logging->warning($msg);
}

function logError($msg) {
  global $logging;
  $logging->error($msg);
}






##############################
# DATABASE ACCESS MODULE
##############################
# Formerly in dba.php
##############################

// ENVIRONMENT VARIABLES
// Allow scripts called by php to access database credentials from the environment
// Security warning: env vars are visible to other users with access to the cluster, I think.
//

// add database credentials to the environment
putenv("CACHE_MYSQL_DB=$CACHE_MYSQL_DB");
putenv("RODEO_MYSQL_SERVER={$_SERVER['ROUNDUP_MYSQL_SERVER']}");
putenv("RODEO_MYSQL_USER={$_SERVER['ROUNDUP_MYSQL_USER']}");
putenv("RODEO_MYSQL_PASSWORD={$_SERVER['ROUNDUP_MYSQL_PASSWORD']}");

putenv("ROUNDUP_MYSQL_SERVER={$_SERVER['ROUNDUP_MYSQL_SERVER']}");
putenv("ROUNDUP_MYSQL_DB={$_SERVER['ROUNDUP_MYSQL_DB']}");
putenv("ROUNDUP_MYSQL_USER={$_SERVER['ROUNDUP_MYSQL_USER']}");
putenv("ROUNDUP_MYSQL_PASSWORD={$_SERVER['ROUNDUP_MYSQL_PASSWORD']}");



##########################
# LSF Stuff
##########################

/*
sets up a user's environment to use LSF
reference: /home/td23/dev/python/LSF.py
*/

// LSF STATUS CONSTANTS                                                                                                                                      
define('LSF_DONE', 'DONE');
define('LSF_EXIT', 'EXIT');


// SETUP ENVIRONMENT TO USE LSF COMMANDS                                                                                                                     
$LSF_DIR = '/opt/lsf/6.0/linux2.4-glibc2.3-x86';
$BIN_DIR = $LSF_DIR.'/bin';
$CONF_DIR = '/opt/lsf/conf';
$LIB_DIR = $LSF_DIR.'/lib';
$SERVER_DIR = $LSF_DIR.'/etc';
putenv("LSF_BINDIR=$BIN_DIR");
putenv("LSF_ENVDIR=$CONF_DIR");
putenv("LSF_LIBDIR=$LIB_DIR");
putenv("LSF_SERVERDIR=$SERVER_DIR");
putenv("RODEO_LSF_EMAIL=".RODEO_LSF_EMAIL_TO_ADDR);

$path = getenv('PATH');
# hack: adding in /groups/rodeo/bin b/c of putenv problem -- can only modify an env var once with putenv, essentially.                                              
$newPath = implode(':', array("/home/td23/bin", "/opt/blast-2.2.22/bin", "/groups/rodeo/bin", $path, "/usr/local/bin", $BIN_DIR, "/opt/emboss/bin"));
putenv("PATH=$newPath");


// returns: true iff bjobs returns DONE or EXIT status for $jobId                                                                                            
function isLSFJobEnded($jobId) {
  $status = lsfJobStatus($jobId);
  return ($status == LSF_DONE || $status == LSF_EXIT);
}

// returns: true iff bjobs returns any status (e.g. DONE, EXIT, PEND, RUN, SUSP, etc.) for $jobId                                                            
function lsfJobExists($jobId) {
  $status = lsfJobStatus($jobId);
  return (bool)$status;
}

// returns: true iff bjobs returns EXIT status for $jobId                                                                                                    
function isLSFJobExited($jobId) {
  $status = lsfJobStatus($jobId);
  return ($status == LSF_EXIT);
}

// returns: true iff bjobs returns DONE status for $jobId                                                                                                    
function isLSFJobDone($jobId) {
  $status = lsfJobStatus($jobId);
  return ($status == LSF_DONE);
}

// returns: true iff bjobs returns any status except DONE or EXIT status for $jobId.  I.e. the job exists and is not ended.                                  
function isLSFJobProcessing($jobId) {
  $status = lsfJobStatus($jobId);
  // sometimes lsf status does not appear immediately after a job has been submitted.
  if (!$status) {
    sleep(4);
    $status = lsfJobStatus($jobId);
  }
  return ($status && $status != LSF_DONE && $status != LSF_EXIT);
}

// returns: the job status of $jobId or false if the job status can not be determined (e.g. if the command fails or the job has been cleared                 
// from the LSF bjobs memory.                                                                                                                                
function lsfJobStatus($jobId) {
  if (trim($jobId)) {
    $safeJobId = escapeshellarg($jobId);
    list($exitcode, $stdout, $stderr) = runCommand("bjobs -u all -a -w $safeJobId | tail -n +2"); # tail command skips the first line
    $splits = preg_split('/ +/', trim($stdout));
    if (count($splits) > 2) {
      $status = $splits[2];
    } else {
      $status = false;
    }
    logDebug("lsfJobStatus(): jobId=$jobId, status=$status");
    if (!$exitcode && $status) {
      return $status;
    } else {
      return false;
    }
  } else {
    return false;
  }
}

?>