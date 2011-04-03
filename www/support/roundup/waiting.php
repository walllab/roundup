<?php

function makeWaitingContent($url, $delay=5000, $message="Processing.  Thank you for your patience.") {
  $content = <<<EOS
     <script language="javascript" type="text/javascript">

     var wait_count = 0;
  var wait_msg;

  function wait_on_load() {
    
    setTimeout("window.location.replace('$url');", $delay);
    wait_msg = document.getElementById("msg").firstChild.nodeValue;
    //document.getElementById("tk_div").style.backgroundImage = "url('http://rg.travelocity.com.edgesuite.net/graphics/wait_anim.gif')";
    setTimeout("wait_animate()", 500);
  }
  
  function wait_animate() {
    var suffix = "";
    for (var i = 0; i < wait_count; i++) {
      suffix += ".";
    }
    document.getElementById("msg").firstChild.nodeValue = wait_msg+suffix;
    wait_count = (wait_count+1) % 4;
    setTimeout("wait_animate();", 500);
  }
  
  addLoadEvent(wait_on_load);
  </script>
      <!-- <style type="text/css"> -->
        <!--
          .timekeeper {
            background-image:url('http://rg.travelocity.com.edgesuite.net/graphics/wait_anim.gif');
            background-repeat: no-repeat;height:320px;width:453px;}
        -->
      <!-- </style> -->
      <div class="timekeeper" id="tk_div">
        <div class="title" id="msg">$message</div>
      </div>
EOS;
    return $content;
}

?>