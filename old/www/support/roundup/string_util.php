<?php

// CONTAINS STRING UTILITY FUNCTIONS


// $str is a string containing one or more lines
// returns an array containing each line in $str.
// the line includes the line ending.
// splits on '\r\n', '\r', and '\n', so do
// not expect good behavior if any of these are not
// used to delimit the end of a line.
//
// e.g.: "one\r\ntwo\r\n" -> array("one\r\n", "two\r\n")
// e.g.: "one\rtwo" -> array("one\r", "two")
// e.g.: "one" -> array("one")
// e.g.: "" -> array()
function splitlines($str) {
  $lines = array();
  $start = 0; //the starting index of the current line
  $i = 0;

  for (; $i < strlen($str); $i++) {
    $char = $str{$i};
    // every time a line ending is encountered, a line is added to $lines
    if ($char == "\n" || $char == "\r") {
      if ($char == "\r" && ($i+1) < strlen($str) && $str{$i+1} == "\n") {
	$i++;
      }
      $lines[] = substr($str, $start, ($i+1-$start)); //the line including the line ending
      $start = $i+1;
    }
  }

  // if the last line did not end in a line ending, add one more line. e.g. "one\rtwo" -> array("one\r", "two")
  if ($start < $i) {
    $lines[] = substr($str, $start, ($i-$start));
  }

  return $lines;
}

