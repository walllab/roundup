<?php
require_once('common.php');
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
    <title>frontpage | roundup</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="robots" content="index,follow" />
<meta name="DC.title" content="roundup | a repository of orthologs" />
<style type="text/css" media="all">


div.panel-flexible div.panel-row-1 div.panel-col-1 { width: 98%; }
div.panel-flexible div.panel-row-2 div.panel-col-1 { width: 23%; }
div.panel-flexible div.panel-row-2 div.panel-col-2 { width: 50%; }
div.panel-flexible div.panel-row-2 div.panel-col-3 { width: 25%; }
div.panel-flexible div.panel-row-3 div.panel-col-1 { width: 98%; }
</style>

<link rel="shortcut icon" href="/site/sites/default/files/bluebird_favicon.ico" type="image/x-icon" />
    <link type="text/css" rel="stylesheet" media="all" href="/site/modules/node/node.css?N" />
<link type="text/css" rel="stylesheet" media="all" href="/site/modules/system/defaults.css?N" />
<link type="text/css" rel="stylesheet" media="all" href="/site/modules/system/system.css?N" />
<link type="text/css" rel="stylesheet" media="all" href="/site/modules/system/system-menus.css?N" />
<link type="text/css" rel="stylesheet" media="all" href="/site/modules/user/user.css?N" />
<link type="text/css" rel="stylesheet" media="all" href="/site/sites/all/modules/cck/theme/content-module.css?N" />
<link type="text/css" rel="stylesheet" media="all" href="/site/sites/all/modules/panels/css/panels.css?N" />
<link type="text/css" rel="stylesheet" media="all" href="/site/sites/all/modules/panels/plugins/layouts/flexible/flexible.css?N" />
<link type="text/css" rel="stylesheet" media="all" href="/site/sites/all/themes/bluebird/style.css?N" />
    <script type="text/javascript" src="/site/misc/jquery.js?N"></script>
<script type="text/javascript" src="/site/misc/drupal.js?N"></script>
<script src="/roundup/js/roundup.js"></script>
<script type="text/javascript" src="/roundup/js/sortable.js"></script>

<script type="text/javascript" src="/site/sites/all/modules/panels/js/panels.js?N"></script>
<script type="text/javascript"><!--

function chkAll(frm, arr, mark) {
  for (i = 0; i <= frm.elements.length; i++) {
    try{
      if(frm.elements[i].name == arr) {
        frm.elements[i].checked = mark;
      }
    } catch(er) {}
  }
}

function MM_swapImgRestore() { //v3.0
  var i,x,a=document.MM_sr; for(i=0;a&&i<a.length&&(x=a[i])&&x.oSrc;i++) x.src=x.oSrc;
}

function MM_preloadImages() { //v3.0
  var d=document; if(d.images){ if(!d.MM_p) d.MM_p=new Array();
    var i,j=d.MM_p.length,a=MM_preloadImages.arguments; for(i=0; i<a.length; i++)
    if (a[i].indexOf("#")!=0){ d.MM_p[j]=new Image; d.MM_p[j++].src=a[i];}}
}

function MM_findObj(n, d) { //v4.01
  var p,i,x;  if(!d) d=document; if((p=n.indexOf("?"))>0&&parent.frames.length) {
    d=parent.frames[n.substring(p+1)].document; n=n.substring(0,p);}
  if(!(x=d[n])&&d.all) x=d.all[n]; for (i=0;!x&&i<d.forms.length;i++) x=d.forms[i][n];
  for(i=0;!x&&d.layers&&i<d.layers.length;i++) x=MM_findObj(n,d.layers[i].document);
  if(!x && d.getElementById) x=d.getElementById(n); return x;
}

function MM_swapImage() { //v3.0
  var i,j=0,x,a=MM_swapImage.arguments; document.MM_sr=new Array; for(i=0;i<(a.length-2);i+=3)
   if ((x=MM_findObj(a[i]))!=null){document.MM_sr[j++]=x; if(!x.oSrc) x.oSrc=x.src; x.src=a[i+2];}
}
//-->
</script>

<!-- begin tabbing code -->
<?php

  echo '<title>CBI - '.$pagetitle.'</title></head>
		<body>'; 

//small page bit, for doc popups

if (isset($small_page) && $small_page) {
  echo '<table width="597" border="0" bgcolor=#FFFFFF>
<tr><td>
<div align="left"><img src="/roundup/images/roundup_header_popups.jpg"></div>
</td></tr>
<tr><td>'; 
} else 
//small page bit ends here.

  echo '
<body  class="sidebars">

<div id="navigation2">
<div id="navigation2-wrap">
<ul class="links" id="subnavlist">
<li class="menu-166 first"><a href="http://autworks.hms.harvard.edu" title="">autworks</a></li>
<li class="menu-231"><a href="http://cbmi.med.harvard.edu/" title="">CBMI</a></li>
<li class="menu-232"><a href="http://lpm.hms.harvard.edu/" title="">LPM</a></li>
<li class="menu-167"><a href="http://lpm.hms.harvard.edu/palaver/" title="">palaver</a></li>
<li class="menu-233"><a href="http://roundup.hms.harvard.edu/" title="">roundup</a></li>
<li class="menu-234 last"><a href="http://wall.hms.harvard.edu/" title="">Wall Lab</a></li>
</ul>
</div>
</div>

<div id="container">
<div id="container2">


<div id="header">


<div id="blogdesc">
 <div id="logocontainer">
 <a href="/site/" title="Home"><img src="/site/sites/all/themes/bluebird/logo.png" alt="Home" /></a>
 </div>
 </div>


<div id="finding">
	</div><!--search area, inside logo area-->
	
</div><!--header-->


<div id="undernavigation">
</div>

<div id="wrap">

<div id="content_top">

<div id="block-block-1" class="clear-block block block-block">
  <div class="content">
  <div id="navigation">
<ul>
<li class="home"><a href="/site">Home</a></li>
<li class="browse"><a href="/roundup/index.php?action=input_browse">Browse</a></li>
<li class="retrieve"><a href="/roundup/index.php?action=input_cluster">Retrieve</a></li>
<li class="download"><a href="/roundup/index.php?action=input_raw">Download</a></li>
<li class="proteomes"><a href="/site/genomes">Genomes</a></li>
<li class="about"><a href="/site/about">About</a></li>
</ul>
</div><!--navigation-->
</div><!--class content-->
</div><!--block-block-1-->
</div><!--content_top-->


<div id="mainpage">
';
  
?>
