<?php


//
// RODEO LOOK AND FEEL FUNCTIONS
// RODEO HTML RENDERING FUNCTIONS
//

// TEMPLATE TYPES: used to describe how you want the content of the page to be displayed/downloaded.
define('XLS_DOWNLOAD_TEMPLATE', 'xls_download_template');
define('TEXT_DOWNLOAD_TEMPLATE', 'text_download_template');
define('TEXT_PAGE_TEMPLATE', 'text_page_template');
define('SMALL_PAGE_TEMPLATE', 'small_page_template');
define('FULL_PAGE_TEMPLATE', 'full_page_template');
define('FULL_PAGE_NO_SIDEBAR_TEMPLATE', 'full_page_no_sidebar_template');
define('ROUNDUP_PAGE_TEMPLATE', 'roundup_page_template');
define('ROUNDUP_WIDE_TEMPLATE', 'roundup_wide_template');



// outputs to the response the rodeo header, footer, and sidebar menu, placing $content in normal section.
function echoTemplate($title, $content, $templateType=NULL) {
  
  if ($templateType == SMALL_PAGE_TEMPLATE || $templateType == NULL || $templateType == FULL_PAGE_TEMPLATE) {
    $small_page = ($templateType == SMALL_PAGE_TEMPLATE ? true : false);
    $pagetitle = $title;
    require('roundup/roundup_header.php');
    if (!$small_page) {
      require('rodeo_sidebar_header.php');
    }
    //logDebug('echoRodeoTemplate(): before echoing content ...');
    echo $content;
    //logDebug('echoRodeoTemplate(): after echoing content ...');
    if (!$small_page) {
      require('rodeo_sidebar_footer.php');
    }
   // require('roundup/roundup_footer.php');
  } elseif ($templateType == FULL_PAGE_NO_SIDEBAR_TEMPLATE) {
    $small_page = false;
    $pagetitle = $title;
    require('roundup/roundup_header.php');
    echo $content;
    require('roundup/roundup_footer.php');    
  } elseif ($templateType == ROUNDUP_WIDE_TEMPLATE) {
    $small_page = false;
    $pagetitle = $title;
    require('roundup/roundup_fluid_header.php');
    echo $content;
    require('roundup/roundup_fluid_footer.php');    
  } elseif ($templateType == ROUNDUP_PAGE_TEMPLATE) {
    $small_page = false;
    $pagetitle = $title;
    require('roundup/roundup_header.php');
    echo $content;
    require('roundup/roundup_footer.php');    
  } elseif ($templateType == TEXT_PAGE_TEMPLATE) {
    header("Content-type: text/plain");
    echo $content;
  } elseif ($templateType == XLS_DOWNLOAD_TEMPLATE) {
    header("Content-type: text/plain");
    header("Content-disposition: attachment; filename=data.txt");
    echo $content;
  } elseif ($templateType == TEXT_DOWNLOAD_TEMPLATE) {
    header("Content-type: text/plain");
    header("Content-disposition: attachment; filename=data.txt");
    echo $content; // oops! adds extra newline.
  } else {
    logError("echoRoundupTemplate(): unrecognized template type: $templateType");
  }
}


function makeErrorsDiv($errors) {
  $content = '';
  if ($errors) {
    $content .= "<div class=\"error\" style=\"color: red;\">\n";
    $content .= "<h3>The following errors were encountered:</h3>\n";
    $content .= "<ul>\n";
    foreach ($errors as $error) {
      $content .= "<li>$error</li>\n";
    }
    $content .= "</ul>\n";
    $content .= "</div>\n";
  }
  return $content;
}


?>
