<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
<title>Rodeo Docs: FASTA Format</title>
<link href="/css/rodeo.css" rel="stylesheet" type="text/css">
</head>
<body>

<table width="550">
<tr><td>

<div align="center"><img src="../../../images/rodeo_header_popups.jpg"></div>

</td></tr>
<tr><td>

<div class="popuptitle">FASTA format description:</div>

<div class="item">
<div class="body">
A sequence in FASTA format begins with a single-line description,
followed by lines of sequence data. The description line is
distinguished from the sequence data by a greater-than (">") symbol in
the first column.  It is recommended that all lines of text be shorter
than 80 characters in length. An example sequence in FASTA format is:
</div>
</div>
<div class="item">
<pre>
>gi|129295|sp|P01013|OVAX_CHICK GENE X PROTEIN (OVALBUMIN-RELATED)
QIKDLLVSSSTDLDTTLVLVNAIYFKGMWKTAFNAEDTREMPFHVTKQESKPVQMMCMNNSFNVATLPAE
KMKILELPFASGDLSMLVLLPDEVSDLERIEKTINFEKLTEWTNPNTMEKRRVKVYLPQMKIEEKYNLTS
VLMALGMTDLFIPSANLTGISSAESLKISQAVHGAFMELSEDGIEMAGSTGVIEDIKHSPESEQFRADHP
FLFLIKHNPTNTIVYFGRYWSP
</pre>
</div>

<div class="item">
<div class="body">
Blank lines are not allowed in the middle of FASTA input.
</div>
</div>

<div class="item">
<div class="body">
Sequences are expected to be represented in the standard IUB/IUPAC
amino acid and nucleic acid codes, with these exceptions: lower-case
letters are accepted and are mapped into upper-case; a single hyphen or
dash can be used to represent a gap of indeterminate length; and in
amino acid sequences, U and * are acceptable letters (see below).
Before submitting a request, any numerical digits in the query sequence
should either be removed or replaced by appropriate letter codes (e.g.,
N for unknown nucleic acid residue or X for unknown amino acid
residue). The nucleic acid codes supported are:
</div>
</div>

<div class="item">

<blockquote>
<pre>
A --> adenosine           M --> A C (amino)
C --> cytidine            S --> G C (strong)
G --> guanine             W --> A T (weak)
T --> thymidine           B --> G T C
U --> uridine             D --> G A T
R --> G A (purine)        H --> A C T
Y --> T C (pyrimidine)    V --> G C A
K --> G T (keto)          N --> A G C T (any)
                          -  gap of indeterminate length
</pre>                                  
</blockquote>
</div>

<div class="item">
<div class="body">
For those programs that use amino acid query sequences (BLASTP and
TBLASTN), the accepted amino acid codes are:
</div>
</div>

<div class="item">
<blockquote>
<pre>
A  alanine                         P  proline
B  aspartate or asparagine         Q  glutamine
C  cystine                         R  arginine
D  aspartate                       S  serine
E  glutamate                       T  threonine
F  phenylalanine                   U  selenocysteine
G  glycine                         V  valine
H  histidine                       W  tryptophan
I  isoleucine                      Y  tyrosine
K  lysine                          Z  glutamate or glutamine
L  leucine                         X  any
M  methionine                      *  translation stop
N  asparagine                      -  gap of indeterminate length
</pre>
</blockquote>

</div>

<div class="item">
<div class="body">
Source: <a href="http://www.ncbi.nlm.nih.gov/blast/html/search.html" target="_new">NCBI Blast Search Documentation</a>
</div>
</div>

</td></tr>
<tr><td>








<DIV align="center" class="item">
<BR>
<form method="post">
<input type="button" value="Close Window"
onclick="window.close()">
</form>

</DIV>

</td>
<TR><TD><BR><img src="../../../images/rodeo_pop_up_footer_line.gif"></TD></TR>
<TR><TD>

<DIV align="center">

<a href="http://cbi.med.harvard.edu">Computational Biology Initiative</a>&nbsp;&nbsp;&nbsp;&nbsp;

			<a href="http://www.hms.harvard.edu/">Harvard Medical School</a>&nbsp;&nbsp;&nbsp;&nbsp;



			<a href="http://sysbio.med.harvard.edu/">Department of Systems Biology</a>



</DIV>

<DIV align="center" class="footer">Copyright (&copy;)2004 President and Fellows of Harvard College. All Rights

Reserved<BR>cbi.med.harvard.edu</DIV>


</TD></TR>
</tr>
</table>

</body>
</html>
