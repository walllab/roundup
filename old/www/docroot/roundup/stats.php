<?PHP

require_once('roundup/common.php');

print display_statistics();

function display_statistics(){

list($stats, $exitcode) = python_dispatch('roundup_util.getRoundupDataStats');
 $prettyNumGenomes = number_format($stats['numGenomes']);
 $prettyNumGenomePairs = number_format($stats['numGenomePairs']);
 $prettyNumOrthologs = number_format($stats['numOrthologs']);
 
 $output = "<p> Around $prettyNumGenomes (and growing) updated monthly.</p>
<p>$prettyNumGenomePairs unique pair-wise genome orthology comparisons
completed.</p>
<p>$prettyNumOrthologs orthologous pairs of genes predicted in total
(for all parameter combinations) and growing as more pairs of genomes
are compared.</p>"; 
 return $output;
}

?>
