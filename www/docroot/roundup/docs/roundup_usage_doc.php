<?php 

require_once('roundup/roundup_util.php');

function getDocumentationTitle() {
  return 'Blast Databases';
}


function getDocumentationContent() {
  $content = '';

  // REPEATED CONTENT

  // BROWSE
  $content .= '<div id="doctext"><h3>Browse</h3>'."\n";
  $content .= '<p>Search the Roundup Orthology Database for orthologs between a Primary Genome and any of several other Genomes.  The results can be restricted to a set of Sequence Ids of interest.</p>'."\n";
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= '<b>Parameters</b>'."\n";
  $content .= '<ul>'."\n";
  $content .= '<li>'."\n";
  $content .= '<a id="genome"></a>'."\n";
  $content .= '<b>Primary Genome</b>'."\n";
  $content .= '<p>Required.  Search results must contain a gene from this genome to be returned.</p>'."\n";
  $content .= '</li>'."\n";

  //$content .= '<li>'."\n";
  //$content .= '<a id="seq_ids"></a>'."\n";
  //$content .= '<div class="subtitle">Sequence Ids</div>'."\n";
  //$content .= '<p>Currently only Protein GI numbers are allowed as protein sequence identifiers, one identifier per line.  Search results will be filtered so that only results containing one or more of the specified ids will be returned.  Sequence identifiers should all refer to genes from the Primary Genome.</p>'."\n";
  //$content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="browse_id_type"></a>'."\n";
  $content .= '<b>'.roundupDisplayName("browse_id_type").'</b>'."\n";
  $content .= '<p>Search results may be filtered so that they must contain a sequence matching an identifier.  An identifier may be either Gene Name or Sequence Id.  An example of a gene name is aatA1.  An example of a sequence id is the NCBI GI Number 18402218.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="browse_id"></a>'."\n";
  $content .= '<b>'.roundupDisplayName("browse_id").'</b>'."\n";
  $content .= '<p>Optional.  After selecting the appropriate '.roundupDisplayName("browse_id_type").', an identifier of the selected type may be entered.  Search results will be filtered so that only results containing sequences from the Primary Genome matching the identifier will be returned.  If this field is left blank, all results will be returned.  If '.roundupDisplayName("seq_id_type").' is chosen as the '.roundupDisplayName("browse_id_type").' then more than one identifier may be entered.  Separate each identifier with a space.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="limit_genomes"></a>'."\n";

  $content .= '<b>Secondary Genomes</b>'."\n";
  $content .= '<p>At least one is required.  Search results are filtered so that they contain one of the genomes selected (in addition to the Primary Genome selected.)</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<b><a href="#common_params">See also Common Parameters</a></b>'."\n";
  $content .= '</li>'."\n";

  $content .= '</ul>'."\n";



  // CLUSTER
  $content .= '<a id="cluster"></a>'."\n";
  $content .= '<h3>Retrieve All Orthologs</h3>'."\n";
  $content .= '<div id="doctext">Retrieve all gene clusters for a set of organisms.  Gene clusters are subgraphs in which the nodes are proteins from the genomes selected and the edges are undirected orthologous relationships computed by the reciprocal smallest distance (RSD) algorithm.</div>'."\n";
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= '<b>Parameters</b>'."\n";
  $content .= '<ul>'."\n";

  $content .= '<li>'."\n";
  $content .= ''."\n";
  $content .= '<a id="genomes"></a>'."\n";
  $content .= '<b>Genomes</b>'."\n";
  $content .= '<p>Two or more required.  Orthologs for all pairwise combinations of the Genomes selected are retrieved.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= ''."\n";
  $content .= '<a id="tc_only"></a>'."\n";
  $content .= '<b>Only Show Transitively Closed Gene Clusters</b>'."\n";
  $content .= '<p>If checked, only gene clusters where every protein is orthologous to every other protein are reported.  (These are the transitively closed subgraphs.)</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a href="#common_params">See also Common Parameters</a>'."\n";
  $content .= '</li>'."\n";

  $content .= '</ul>'."\n";



  // RAW DATA
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= '<a id="raw"></a>'."\n";
  $content .= '<h3>Download Raw Data</h3>'."\n";
  $content .= '<p>Download the raw data for a pair of genomes, choosing the parameters of the Reciprocal Smallest Distance (RSD) algorithm used to generate the data.  Raw data contains one row for every ortholog.  Each row contains 3 tab-separated values: the Second Genome Gene Id, the First Genome Gene Id, and the maximum likelihood estimation of evolutionary distance between those genes.  For more user-friendly results, consider using the Browse or Retrieve queries.</p>'."\n";
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= '<b>Parameters</b>'."\n";
  $content .= '<ul>'."\n";

  $content .= '<li>'."\n";
  $content .= ''."\n";
  $content .= '<a id="query_genome"></a>'."\n";
  $content .= '<b>First Genome</b>'."\n";
  $content .= '<p>Required.  Return orthologs between this genome and Second Genome.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="subject_genome"></a>'."\n";
  $content .= '<b>Second Genome</b>'."\n";
  $content .= ''."\n";
  $content .= '<p>Required.  Return orthologs between this genome and First Genome.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a href="#common_params">See also Common Parameters</a>'."\n";
  $content .= '</li>'."\n";

  $content .= '</ul>'."\n";


  
  // ADD GENOME
  $content .= ''."\n";
  $content .= '<a id="add_genome"></a>'."\n";
  $content .= '<h3>Request Addition of a Genome</h3>'."\n";
  $content .= '<p>Submit a request for a genome to be added to the Roundup database.  For a genome to be added, it must be completely sequenced and have publicly available whole genome protein annotations in FASTA format.</p>'."\n";
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= '<b>Parameters</b>'."\n";
  $content .= '<ul>'."\n";

  $content .= '<li>'."\n";
  $content .= ''."\n";
  $content .= '<a id="genome_name"></a>'."\n";
  $content .= '<b>Genome Name</b>'."\n";
  $content .= '<p>Required.  The name of the organism to be added.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="genome_urls"></a>'."\n";
  $content .= '<b>Genome Source URL(s)</b>'."\n";
  $content .= '<p>Required.  The location of the publicly accessible FASTA formatted protein sequence file(s) which comprise the whole genome annotations for the organism.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="email"></a>'."\n";
  $content .= '<b>Contact Email Address</b>'."\n";
  $content .= '<p>Required.  A valid email address used to confirm any details necessary to add the genome and/or to tell you when the genome has been added.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="message"></a>'."\n";
  $content .= '<b>Any Additional Message</b>'."\n";
  $content .= '<p>Optional.  Any additional message, information, notes, or questions you wish to provide.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '</ul>'."\n";


  
  // ADD GENOME
  $content .= ''."\n";
  $content .= '<a id="search_gene_names"></a>'."\n";
  $content .= '<h3>Search For Gene Names</h3>'."\n";
  $content .= '<p>Search the list of gene names in the Roundup system.  This is the same list that is used when running a Browse query or when orthology search results are reported with gene names.  Searching for gene names is a useful way to find a gene name with which to limit orthology search results when using the Browse query.  Using Search For Gene Names, one can find gene names which either contain, start with, end with, or are exactly equal to a given search text.</p>'."\n";
  $content .= '<p>After pressing Submit, any matching gene names in the Roundup system will be displayed at the bottom of the page.</p>'."\n";
  $content .= ''."\n";

  
  // COMMON PARAMETERS
  $content .= ''."\n";
  $content .= '<a id="common_params"></a>'."\n";
  $content .= '<h3>Common Parameters</h3>'."\n";
  $content .= '<p>These parameters occur in one or more of the various query types.</p>'."\n";
  $content .= ''."\n";
  $content .= ''."\n";
  $content .= '<b>Parameters</b>'."\n";
  $content .= '<ul>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="distance_lower_limit"></a>'."\n";
  $content .= '<b>Distance Lower Limit</b>'."\n";
  $content .= '<p>Optional.  Enter a number between 0.0 and 19.0, (and not greater than Distance Upper Limit if one was entered).  Orthologs with a distance value (as calculated by the RSD algorithm) LESS than this limit will not be returned.  If left blank, ortholog results will not be limited.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= ''."\n";
  $content .= '<a id="distance_upper_limit"></a>'."\n";
  $content .= '<b>Distance Upper Limit</b>'."\n";
  $content .= '<p>Optional.  Enter a number between 0.0 and 19.0, (and not less than Distance Lower Limit if one was entered).  Orthologs with a distance value (as calculated by the RSD algorithm) GREATER than this limit will not be returned.  If left blank, ortholog results will not be limited.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="divergence"></a>'."\n";
  $content .= '<b>Divergence</b>'."\n";
  $content .= '<p>Required.  Return orthologs calculated by RSD using this divergence as a threshold.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<a id="evalue"></a>'."\n";
  $content .= '<div class="subtitle">BLAST E-value</div>'."\n";
  $content .= '<p>Required.  Return orthologs calculated by RSD using this BLAST E-value as a threshold.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="gene_name"></a>'."\n";
  $content .= '<b>Include Gene Names in Results</b>'."\n";
  $content .= '<p>If checked, results will include the gene name (if any) for each gene.  NCBI is the source of gene names.  Some genes do not have a name.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '<li>'."\n";
  $content .= '<a id="go_term"></a>'."\n";
  $content .= '<b>Include Functional GO Terms in Results</b>'."\n";
  $content .= '<p>If checked, results will include any Molecular Function gene ontology terms associated with each gene.  The Gene Ontology Consortium and NCBI are the sources of these associations.  Some genes to not have any GO terms.</p>'."\n";
  $content .= '</li>'."\n";

  $content .= '</ul>'."\n";

  $content .= '</div>'."\n";// end doctext div

  
  return $content;
}

?>
