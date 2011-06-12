<?php 

require_once('roundup/roundup_template.php');
require_once('roundup/forms.php');
require_once('roundup/common.php');

//logDebug("roundup/get_doc.php: Here I am at the beginning!");

function isValidId($id) {
  return preg_match('/^\w*$/', $id);
}

$form = makeForm($_REQUEST, array('id', 'full'));

// get content and page title from documentation referred to by id
$content = '';
$pagetitle = 'Roundup Documentation';

$id = getValueInMap('id', $form);
logDebug("roundup/get_doc.php: id=$id");
$smallpage = !getValueInMap('full', $form);
if ($id && isValidId($id)) {
  //require_once("/docs/$id.php");
  require_once("$id.php");
  $content = getDocumentationContent();
  $pagetitle .= ' - '.getDocumentationTitle();
}


echoTemplate($pagetitle, $content, $smallpage);
?>