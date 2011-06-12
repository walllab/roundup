<?php 


###########################
# FORM VALIDATION FUNCTIONS
###########################

// $form is a dictionary of strings or arrays of strings
// like what you get from a web form.  e.g. $_REQUEST

// boilerplate.
// if not valid, adds the error message to the errors.  
// Either way returns the value of $valid.
function validateSub($valid, $errormsg, &$errors) {
  if (!$valid) {
    $errors[] = $errormsg;
  }
  return $valid;
}


function isValidEmail($address) {
  return preg_match("/^[a-zA-Z0-9]+[a-zA-Z0-9\._-]*@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/" , $address);
}


// does the form parameter exist AND is it in the array?
// good for testing if something belongs to a set of values.
function validateExistsIn($form, $param, $list) {
  return validateExists($form, $param) && in_array($form[$param], $list);
}

// $form: map of param name to values
// $param: param name of a value or a list of values (e.g. a multiselect dropdown)
// $list: array of values.  Each value in the list named by $param should be in $list.
// returns: true if $param exists and is in $list or is an array and each element is in $list
// essentially tests whether the form parameter is a subset of the list.
function validateAllExistIn($form, $param, $list) {
  if (!validateExists($form, $param)) {
    return false;
  }

  $paramValue = $form[$param];
  if (in_array($paramValue, $list)) {
    return true;
  } elseif (is_array($paramValue)) {
    foreach ($paramValue as $elem) {
      if (!in_array($elem, $list)) {
	return false;
      }
    }
    return true;
  }
  return false;    
}

// $predicate is the name of a function which takes $form and a $param and returns true or false.
// returns: xor of the predicate on param1 & param2
function eitherOrPredicate($form, $param1, $param2, $predicate) {
  $pred1 = $predicate($form, $param1);
  $pred2 = $predicate($form, $param2);
  return ($pred1 && !$pred2) || ($pred2 && !$pred1);
}

// here existence is defined as the key being set and the value not being the empty string or empty array.
function validateExists($form, $param) {
  if (isset($form[$param]) && ((is_array($form[$param]) && count($form[$param]) > 0) || (is_string($form[$param]) && strlen($form[$param]) > 0))) {
    return true;
  }
  return false;
}


// buyer beware: equality in php is a slippery notion.  you probably want to check that these params exist first.
function validateEqual($form, $param1, $param2) {
  return $form[$param1] == $form[$param2];
}


function isBlank($str) {
  return strlen(trim($str)) == 0;
}

?>