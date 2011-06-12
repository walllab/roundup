<?php

require_once('common.php');

// params are strings
// returns 1 if $whole ends with $suffix, 0 otherwise.
function strEndsWith($whole, $suffix) {
  $sufLen = strlen($suffix);
  $wholeLen = strlen($whole);
  $offset = $wholeLen-$sufLen;
  $pos = strpos($whole, $suffix, $offset);
  if ($pos === false) {
    return 0;
  } else {
    return 1;
  }
}


// $id: html id of form
// $params: array of input parameter names of form
// $data: array mapping input parameter names to values
// $exampleData: array mapping input parameter names to example values.  optional.
function makeFormInfo($id, $params, $data, $exampleData=NULL, $defaults=NULL) {
  $formInfo = array();
  $formInfo['id'] = $id;
  $formInfo['params'] = $params;
  $formInfo['data'] = makeForm($data, $params, $defaults);
  if (is_array($exampleData)) {
    $formInfo['example_data'] = makeForm($exampleData, $params, $defaults);
  }
  return $formInfo;
}


// $request: array mapping mangled html form keys to values, either strings or arrays.  mangling is when php turns an input name like 'dbs[]' into 'dbs'.
// $keys: a list of unmangled keys.  optional.  If no list is given, it works as if the keys in $request are unmangled and used as $keys.
// $defaults: an array mapping unmangled keys to their default values.  If a key is present in $defaults and absent in $request, then the form value for
// the key is set to the value in $defaults.
// returns an array mapping the keys in $keys to the values of those keys (after mangling/unmangling) in $request.
function makeForm($request, $keys=NULL, $defaults=NULL) {
  $form = array();

  if ($defaults == NULL) {
    $defaults = array();
  }

  if (is_array($keys)) {
    foreach($keys as $key) {
      if (array_key_exists($key, $request)) {
	$form[$key] = $request[$key];
      } elseif (strEndsWith($key, '[]')) {
	// trim off [] and check for an array in the request
	$arrkey = substr($key, 0, strlen($key)-2);
	if (array_key_exists($arrkey, $request) && is_array($request[$arrkey])) {
	  $form[$key] = $request[$arrkey];
	} elseif (array_key_exists($key, $defaults)) {
	  $form[$key] = $defaults[$key];
	}
      } elseif (array_key_exists($key, $defaults)) {
	$form[$key] = $defaults[$key];
      }
    }
  } else {
    // use request keys as keys.
    foreach($request as $k => $v) {
      if (is_array($v)) {
	$k = $k.'[]';
      }
      $form[$k] = $v;
    }
  }
  return $form;
}


// $key: to look for in each map
// $maps: list of maps (a.k.a. arrays in php)
// return the value in the first map for which $key is set.
// if $key is not set in any map, returns null, so if you are searching
// for a value which could be null, better off checking for the presence
// of $key first.
function getValueInMaps($key, $maps, $default=NULL) {
  foreach($maps as $map) {
    if (array_key_exists($key, $map)) {
      return $map[$key];
    }
  }
  return $default;
}


function getValueInMap($key, $map, $default=NULL) {
  if (array_key_exists($key, $map)) {
    return $map[$key];
  } else {
    return $default;
  }
}


function isKeyInMaps($key, $maps) {
  foreach($maps as $map) {
    if (array_key_exists($key, $map)) {
      return true;
    }
  }
  return false;
}

// $pairs: list of pairs of key, map.
// echo a value clause for the first pair where key is in map.
// e.g. echoValueClauseComplexMaps(array(array(EMAIL, $form), array('useremail', $_SESSION)));
function echoValueClauseComplexMaps($pairs) {
  foreach($pairs as $pair) {
    $key = $pair[0];
    $map = $pair[1];
    if (array_key_exists($key, $map)) {
      echo makeValueClause($map[$key]);
      return;
    }
  }
}

function echoValueClauseFromMaps($param, $maps) {
  if (isKeyInMaps($param, $maps)) {
    echo makeValueClause(getValueInMaps($param, $maps));
  } 
}

function makeValueClause($value) {
  return 'value="'.$value.'"';
}

// if $param exists in $form, echos the value of $param in $form
// otherwise does nothing.
function echoValue($form, $param) {
  if (array_key_exists($param, $form)) {
    echo $form[$param];
  }
}

function isValueOfParam($value, $param, $form) {
  if (array_key_exists($param, $form)) {
    if (is_array($form[$param])) {
      return in_array($value, $form[$param]);
    } else {
      return $value == $form[$param];
    }
  } else {
    return false;
  }
}

// if $value is one of the values of $param in $form, echo checked.
function echoChecked($value, $param, $form) {
  if (isValueOfParam($value, $param, $form)) {
    echo "checked";
  }
}

function echoValueClause($form, $param) {
  if (array_key_exists($param, $form)) {
    echo makeValueClause($form[$param]);
  }
}

function isChecked($form, $param, $value) {
  if (isset($form[$param]) && is_array($form[$param])) {
    return in_array($value, $form[$param]);
  } else {
    return false;
  }
}


// $form: dict of parameter names and values, possibly array values.
// $formId: id of form on html page
// $exampleForm: dict of parameter names and example values, possibly array values. Optional. If not present, no example form values are written to the page.
/*
function makeJSFormValuesScript($form, $formId, $exampleForm=NULL) {
  $content = '';
  $content .= "<script><!--\n";
  $content .= "var ${formId}_values = ".javascriptSerialize($form).";\n";
  if (is_array($exampleForm)) {
    $content .= "var ${formId}_example_values = ".javascriptSerialize($exampleForm).";\n";
  }
  $content .= "addLoadEvent(function() { setFormValues(document.getElementById(".javascriptSerialize($formId)."), ${formId}_values); });\n";
  $content .= "// -->\n";
  $content .= "</script>\n";
  return $content;
}
*/


function makeJSFormValuesScript($formId, $formValues, $name=NULL) {
  $content = '';
  $content .= "<script><!--\n";
  if (is_array($formValues)) {
    $content .= "var ".makeJSFormValuesName($formId, $name)." = ".javascriptSerialize($formValues).";\n";
  }
  $content .= "// -->\n";
  $content .= "</script>\n";
  return $content;
}


function makeJSFormValuesName($formId, $name=NULL) {
  $varName = "${formId}_";
  if ($name != NULL) {
    $varName .= "${name}_";
  }
  $varName .= "values";
  return $varName;
}


function makeJSFormLoadEvent($formId, $name=NULL) {
  $content = '';
  $content .= "<script><!--\n";
  $content .= "addLoadEvent(function() { setFormValues(document.getElementById(".javascriptSerialize($formId)."), ".makeJSFormValuesName($formId, $name)."); });\n";
  $content .= "// -->\n";
  $content .= "</script>\n";
  return $content;
}


// $formId: id of form on html page
// $exampleForm: dict of parameter names and example values, possibly array values.
// writes a link to the page which sets the form $formId to the values in $exampleForm.
// if $exampleForm is not an array, nothing is written. 
function makeJSSetFormLink($formId, $name, $linkText) {
  return "<a href=\"javascript:setFormValues(document.getElementById(".javascriptSerialize($formId)."), ".makeJSFormValuesName($formId, $name).");\">$linkText</a>\n";
}

?>