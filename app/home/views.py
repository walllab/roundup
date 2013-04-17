# Creatt your views here.

# stdlib modules
import glob
import hashlib
import io
import json
import logging
import os
import sys
import uuid

# third party modules
import django.http
import django.shortcuts
import django.forms
import django.core.exceptions
import django.core.urlresolvers
import django.utils.html

# our modules
sys.path.append('..')
import BioUtilities
import config
import lsf
import orthresult
import orthutil
import roundup_common
import roundup.dataset
import roundup_db
import roundup_util
import util


USE_CACHE = True
SYNC_QUERY_LIMIT = 20 # run an asynchronous query (on lsf) if more than this many genomes are in the query.
GENOMES_AND_NAMES = roundup_util.getGenomesAndNames()
GENOME_TO_NAME = dict(GENOMES_AND_NAMES)
NAME_TO_GENOME = dict([(n, g) for g, n in GENOMES_AND_NAMES]) # assumes genomes and names are one-to-one.
GENOMES = [genome for genome, name in GENOMES_AND_NAMES]
GENOME_CHOICES = sorted(GENOMES_AND_NAMES, key=lambda gn: gn[1]) # sorted by name name
# tuples for each genome containing: acc, name, taxon, cat, categoryName, size
GENOME_DESCS = sorted(roundup_util.getGenomeDescriptions(), key=lambda d: d[1].lower()) # case-insensitive sort by name
CATS = ['E', 'B', 'A', 'V']
CAT_TO_NAME = {'E': 'Eukaryota', 'B': 'Bacteria', 'A': 'Archaea', 'V': 'Viruses'}
CAT_GENOMES = [(d[3], {'name': d[1] + ' -- ' + d[4], 'value': d[1]}) for d in GENOME_DESCS]
CAT_CHOICES = [(cat, CAT_TO_NAME[cat]) for cat in CATS]
DIVERGENCE_CHOICES = [(d, d) for d in roundup_common.DIVERGENCES]
EVALUE_CHOICES = [(d, d) for d in roundup_common.EVALUES] # 1e-20 .. 1e-5
IDENTIFIER_TYPE_CHOICES = [('gene_name_type', 'Gene Name'), ('seq_id_type', 'Sequence Id')]
SEARCH_GENE_NAMES_TYPE_CHOICES = [('contains', 'Contains'), ('equals', 'Equals'), ('starts_with', 'Starts with'), ('ends_with', 'Ends with')]

DISPLAY_NAME_MAP = {'fasta': 'FASTA Sequence', 'genome': 'Genome', 
                    'primary_genome': 'Primary Genome', 'secondary_genomes': 'Secondary Genomes', 'limit_genomes': 'Secondary Genomes', 'genomes': 'Genomes', 
                    'query_genome': 'First Genome', 'subject_genome': 'Second Genome', 'divergence': 'Divergence', 'evalue': 'BLAST E-value',
                    'distance_lower_limit': 'Distance Lower Limit', 'distance_upper_limit': 'Distance Upper Limit', 
                    'gene_name': 'Include Gene Names in Result', 'go_term': 'Include GO Terms in Result', 
                    'tc_only': 'Only Show Transitively Closed Gene Clusters', 
                    'identifier': 'Identifier', 'identifier_type': 'Identifier Type', 'gene_name_type': 'Gene Name', 'seq_id_type': 'Sequence Id',
                    'seq_ids': 'Sequence Identifiers',
                    'contains': 'Contain', 'equals': 'Equal', 'starts_with': 'Start With', 'ends_with': 'End With', 'substring': 'Text Substring'}

CT_XML = 'xml'
CT_TXT = 'txt'
RAW_CONTENT_TYPE_CHOICES = [(CT_XML, 'OrthoXML'), (CT_TXT, 'Text')]
RAW_CONTENT_TYPE_TO_NAME = dict(RAW_CONTENT_TYPE_CHOICES)
RAW_CONTENT_TYPES = RAW_CONTENT_TYPE_TO_NAME.keys()

DIST_LIMIT_HELP = 'from 0.0 to 19.0'

# Cache data about dataset/release download files
# maps a release to a list of data for each download file
RELEASE_DOWNLOAD_DATAS = {}
# maps a release to a list of each download filename
RELEASE_DOWNLOAD_FILES = {}


def displayName(key, nameMap=DISPLAY_NAME_MAP):
    return nameMap.get(key, key)


def home(request):
    stats = roundup_util.getDatasetStats() # keys: numGenomes, numPairs, numOrthologs
    release = roundup_util.getRelease()
    releaseDate = roundup_util.getReleaseDate()
    kw = {'nav_id': 'home', 'release': release, 'release_date': releaseDate}
    kw.update(stats)
    return django.shortcuts.render(request, 'home.html', kw)


def about(request):
    stats = roundup_util.getDatasetStats() # keys: numGenomes, numPairs, numOrthologs
    sourceUrls = roundup_util.getSourceUrls()
    release = roundup_util.getRelease()
    releaseDate = roundup_util.getReleaseDate()
    uniprotRelease = roundup_util.getUniprotRelease()
    # sources_html = roundup_util.getSourcesHtml()
    kw = {'nav_id': 'about', 'numGenomes': stats['numGenomes'], 'source_urls': sourceUrls,
          'release': release, 'release_date': releaseDate, 'uniprot_release': uniprotRelease}
    return django.shortcuts.render(request, 'about.html', kw)
    

def documentation(request):
    return django.shortcuts.render(request, 'documentation.html', {'nav_id': 'documentation'})


def genomes(request):
    # tuples for each genome containing: acc, name, taxon, cat, catName, size
    eukaryota = [desc for desc in GENOME_DESCS if desc[3] == 'E']
    archaea = [desc for desc in GENOME_DESCS if desc[3] == 'A']
    bacteria = [desc for desc in GENOME_DESCS if desc[3] == 'B']
    viruses = [desc for desc in GENOME_DESCS if desc[3] == 'V']
    unclassified = [desc for desc in GENOME_DESCS if desc[3] == 'U']
    if unclassified:
        logging.error(u'There are unclassified genomes: {}'.format(unclassified))
    num_eukaryota, num_archaea, num_bacteria, num_viruses = [len(g) for g in (eukaryota, archaea, bacteria, viruses)]
    num_genomes = num_eukaryota + num_archaea + num_bacteria + num_viruses
    kw = {'nav_id': 'genomes', 'descGroups': [eukaryota, archaea, bacteria, viruses], 'num_genomes': num_genomes,
          'num_eukaryota': num_eukaryota, 'num_archaea': num_archaea, 
          'num_bacteria': num_bacteria, 'num_viruses': num_viruses,
          'min_genome_size': roundup.dataset.MIN_GENOME_SIZE}
    return django.shortcuts.render(request, 'genomes.html', kw)


def updates(request):
    return django.shortcuts.render(request, 'updates.html', {'nav_id': 'updates'})
    

###################
# CONTACT FUNCTIONS
###################

class ContactForm(django.forms.Form):
    name = django.forms.CharField(max_length=100, required=False, widget=django.forms.TextInput(attrs={'size': '60'}))
    affiliation = django.forms.CharField(max_length=100, required=False, widget=django.forms.TextInput(attrs={'size': '60'}))
    email = django.forms.EmailField(widget=django.forms.TextInput(attrs={'size': '60'}))
    subject = django.forms.CharField(max_length=100, widget=django.forms.TextInput(attrs={'size': '60'}))
    message = django.forms.CharField(help_text='Please be detailed', widget=django.forms.Textarea(attrs={'cols': '60', 'rows': '10', 'wrap': 'physical'}))

    
def contact(request):
    if request.method == 'POST': # If the form has been submitted...
        form = ContactForm(request.POST, auto_id=False) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            form.cleaned_data['host'] = request.get_host()
            logging.debug(form.cleaned_data)
            rtEmail = config.RT_EMAIL
            message = '''This ticket was submitted via http://%(host)s.
-------------------------------------------------------------------------------
Requestor contact information:
	Name: %(name)s
        Email: %(email)s
	Organization/Group: %(affiliation)s
        Subject: %(subject)s
-------------------------------------------------------------------------------

%(message)s
'''%form.cleaned_data
            config.sendtextmail(form.cleaned_data['email'], [rtEmail], form.cleaned_data['subject'], message) 
            # redirect the post to a get.  http://en.wikipedia.org/wiki/Post/Redirect/Get
            return django.shortcuts.redirect(django.core.urlresolvers.reverse(contact_thanks))
    else:
        form = ContactForm(auto_id=False) # An unbound form

    return django.shortcuts.render(request, 'contact.html', {'form': form, 'nav_id': 'contact', 'form_doc_id': None,
                                                         'form_action': django.core.urlresolvers.reverse(contact)})


def contact_thanks(request):
    page = '<div><h2>Thank you for contacting us!</h2><p>Your submission has been received and you should receive a confirmation email shortly.</p></div>'
    return django.shortcuts.render(request, 'regular.html', {'html': page, 'nav_id': 'contact'})
    

####################
# DOWNLOAD FUNCTIONS
####################


def download_quest_for_orthologs(request, version):
    # validate params
    if version in config.QFO_VERSIONS:
        kw = {'version': version}
        desc = 'Downloading orthologs for Quest for Orthologs Reference Proteomes version {}'.format(version)
        data = {'desc': desc, 'download_url': django.core.urlresolvers.reverse(api_download_quest_for_orthologs, kwargs=kw)}
        return django.shortcuts.render(request, 'download_inform.html', data)        
    else:
        raise django.http.Http404


def get_qfo_path_and_size(version):
    path = os.path.join(config.QUEST_FOR_ORTHOLOGS_DIR, version, 'download', 'roundup_qfo_{}_orthologs.xml.gz'.format(version))
    size = os.path.getsize(path)
    return path, size


def api_download_quest_for_orthologs(request, version):
    # validate params
    if version in config.QFO_VERSIONS:
        path, size = get_qfo_path_and_size(version)
        filename = os.path.basename(path)
        response = django.http.HttpResponse(open(path, 'rb'), content_type='application/x-gzip')
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        response['Content-Length'] = str(size)
        return response
    else:
        raise django.http.Http404
    

class RawForm(django.forms.Form):
    first_genome = django.forms.ChoiceField(choices=GENOME_CHOICES)
    second_genome = django.forms.ChoiceField(choices=GENOME_CHOICES)
    divergence = django.forms.ChoiceField(choices=DIVERGENCE_CHOICES)
    evalue = django.forms.ChoiceField(choices=EVALUE_CHOICES, label='BLAST E-value')
    format = django.forms.ChoiceField(choices=RAW_CONTENT_TYPE_CHOICES, required=False)

    def clean_format(self):
        '''
        If format is not specified, it defaults to CT_TXT.
        '''
        logging.debug('clean_format={}'.format(self.cleaned_data['format']))
        data = self.cleaned_data['format']
        if data:
            return data
        else:
            return CT_TXT
            
    def clean(self):
        first_genome = self.cleaned_data.get('first_genome')
        second_genome = self.cleaned_data.get('second_genome')
        if first_genome == second_genome:
            raise django.forms.ValidationError('First genome and Second genome must be different.')
        return self.cleaned_data


def get_dataset_download_datas(ds):
    '''
    Return a list containing the filename, path and size of the download files
    in dataset ds.

    Example output:

        [{'filename': '0.2_1e-10.orthologs.txt.gz',
        'size': '10.7GB',
        'path': '/groups/cbi/sites/roundup/datasets/4/download/0.2_1e-10.orthologs.txt.gz'},
        ...
        {'filename': 'genomes.tar.gz',
        'size': '2.2GB',
        'path': '/groups/cbi/sites/roundup/datasets/4/download/genomes.tar.gz'},
    '''
    datas = []
    paths = glob.glob(os.path.join(roundup.dataset.getDownloadDir(ds), '*'))
    files = sorted([p for p in paths if os.path.isfile(p)])
    for path in files:
        filename = os.path.basename(path)
        size = os.path.getsize(path)
        datas.append({'size': size, 'filename': filename, 'path': path})

    return datas


def cache_download_datas():
    '''
    Create lookup tables mapping dataset to a list of download file data of the
    dataset, release to the download file data, and release to just the 
    filename.
    '''
    for ds in config.ARCHIVE_DATASETS:
        release = roundup.dataset.getDatasetId(ds)
        datas = get_dataset_download_datas(ds)
        RELEASE_DOWNLOAD_DATAS[release] = datas
        RELEASE_DOWNLOAD_FILES[release] = [d['filename'] for d in datas]


def get_release_download_datas(release):
    '''
    Get the download datas (a dict of filename, size, and path) associated with
    the download directory of `release` dataset.
    '''
    if not RELEASE_DOWNLOAD_DATAS:
        cache_download_datas()

    return RELEASE_DOWNLOAD_DATAS[release]


def get_release_download_files(release):
    '''
    Get the download filenames associated with the download directory of
    `release` dataset.
    '''
    if not RELEASE_DOWNLOAD_FILES:
        cache_download_datas()

    return RELEASE_DOWNLOAD_FILES[release]


def download_release_file(request, release, filename):
    '''
    Redirect to a download page for a file in the "download" directory of the
    dataset identified by release.
    '''
    # validate params
    if release not in config.ARCHIVE_RELEASES or filename not in get_release_download_files(release):
        raise django.http.Http404

    kw = {'release': release, 'filename': filename}
    desc = 'Downloading archive file {} for Roundup release {}.'.format(filename, release)
    data = {'desc': desc, 'download_url': django.core.urlresolvers.reverse(api_download_release_file, kwargs=kw)}
    return django.shortcuts.render(request, 'download_inform.html', data)


def api_download_release_file(request, release, filename):
    '''
    Download a file in the "download" directory of the dataset identified by
    release.
    '''
    # validate params
    if release not in config.ARCHIVE_RELEASES or filename not in get_release_download_files(release):
        raise django.http.Http404

    data = [data for data in get_release_download_datas(release) if data['filename'] == filename][0]
    response = django.http.HttpResponse(open(data['path'], 'rb'), content_type='application/x-gzip')
    response['Content-Disposition'] = 'attachment; filename={}'.format(data['filename'])
    response['Content-Length'] = str(data['size']) # bytes
    return response


def download(request):
    '''
    get: render a form for user to request orthologs for a pair of genomes.
    post: redirect to a page which will download the ortholgos.
    '''
    if request.method == 'POST': # If the form has been submitted...
        form = RawForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            logging.debug(form.cleaned_data)
            first_genome, second_genome = sorted((form.cleaned_data['first_genome'], form.cleaned_data['second_genome']))
            contentType = form.cleaned_data['format']
            kwargs = {'first_genome': first_genome, 'second_genome': second_genome, 
                      'divergence': form.cleaned_data['divergence'], 'evalue': form.cleaned_data['evalue']}
            # redirect the post to a get.  http://en.wikipedia.org/wiki/Post/Redirect/Get
            return django.shortcuts.redirect(
                django.core.urlresolvers.reverse(
                    raw_download, kwargs=kwargs)+'?ct={}'.format(contentType))
    else:
        form = RawForm() # An unbound form

    # a list of releases and the download links associated with each release
    release_link_datas = []
    for ds in config.ARCHIVE_DATASETS:
        release = roundup.dataset.getDatasetId(ds)
        release_link_data = {'release': release, 'links': []}
        for data in get_release_download_datas(release):
            link =  django.core.urlresolvers.reverse(
                download_release_file,
                kwargs={'release': release, 'filename': data['filename']})
            release_link_data['links'].append(
                {'text': data['filename'], 'link': link, 
                 'size': util.humanBytes(data['size'])})
        release_link_datas.append(release_link_data)

    # orthologs for the quest for orthologs reference genomes
    qfoData = []
    for version in config.QFO_VERSIONS:
        path, size = get_qfo_path_and_size(version)
        qfoData.append((version, os.path.basename(path), util.humanBytes(size)))

    example = "{'first_genome': '9606', 'second_genome': '10090'}"
    return django.shortcuts.render(request, 'download.html', 
                                   {'form': form, 'nav_id': 'download', 
                                    'form_doc_id': 'download', 'form_action': 
                                    django.core.urlresolvers.reverse(download),
                                    'form_example': example, 
                                    'qfo_data': qfoData,
                                    'release_link_datas': release_link_datas})


def raw_download(request, first_genome, second_genome, divergence, evalue):
    '''
    get: render a page which lets the user know orthologs are being downloaded and then downloads the orthologs
    '''
    # validate parameters
    contentType = request.GET.get('ct', CT_TXT)
    kw = {'first_genome': first_genome, 'second_genome': second_genome, 'divergence': divergence, 'evalue': evalue}
    form = RawForm(kw)
    if form.is_valid() and contentType in RAW_CONTENT_TYPES:
        desc = 'Downloading orthologs for:<ul><li>First genome: {}</li><li>Second genome: {}</li><li>Divergence: {}</li><li>BLAST E-value: {}</li><li>Format: {}</li></ul>'
        desc = desc.format(GENOME_TO_NAME[first_genome], GENOME_TO_NAME[second_genome], divergence, evalue, RAW_CONTENT_TYPE_TO_NAME[contentType])
        data = {'desc': desc, 'download_url': django.core.urlresolvers.reverse(api_raw_download, kwargs=kw)+'?ct={}'.format(contentType)}
        return django.shortcuts.render(request, 'download_inform.html', data)
    else:
        raise django.http.Http404


def api_raw_download(request, first_genome, second_genome, divergence, evalue):
    '''
    get: send orthologs for a pair of genomes as a file download.
    '''
    # validate parameters
    contentType = request.GET.get('ct', CT_TXT)
    kw = {'first_genome': first_genome, 'second_genome': second_genome, 'divergence': divergence, 'evalue': evalue}
    form = RawForm(kw)
    if form.is_valid() and contentType in RAW_CONTENT_TYPES:
        if contentType == CT_TXT:
            orthData = roundup_util.getOrthData((first_genome, second_genome, divergence, evalue))
            orthologsTxt = orthutil.orthDatasToStr([orthData])
            response = django.http.HttpResponse(orthologsTxt, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename=roundup_orthologs_for_{}_{}_{}_{}.txt'.format(first_genome, second_genome, divergence, evalue)
            return response
        elif contentType == CT_XML:
            orthData = roundup_util.getOrthData((first_genome, second_genome, divergence, evalue))
            with io.BytesIO() as handle:
                roundup.dataset.convertOrthDatasToXml(config.CURRENT_DATASET, [orthData], [orthData], handle)
                orthologsXml = handle.getvalue()
            response = django.http.HttpResponse(orthologsXml, content_type='text/xml')
            response['Content-Disposition'] = 'attachment; filename=roundup_orthologs_for_{}_{}_{}_{}.xml'.format(first_genome, second_genome, divergence, evalue)
            return response
    else:
        raise django.http.Http404


##################
# LOOKUP FUNCTIONS
##################

class LookupForm(django.forms.Form):
    genome = django.forms.ChoiceField(choices=GENOME_CHOICES)
    fasta = django.forms.CharField(label='FASTA sequence', widget=django.forms.Textarea(attrs={'cols': '80', 'rows': '5', 'wrap': 'physical'}))


def lookup(request):
    '''
    get: render a form for user to lookup the sequence id for a fasta sequence from a genome.
    post: redirect to a page which will show the id.
    '''
    if request.method == 'POST': # If the form has been submitted...
        form = LookupForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            logging.debug(form.cleaned_data)
            genome, fasta = form.cleaned_data['genome'], form.cleaned_data['fasta'] 
            seqId = BioUtilities.findSeqIdWithFasta(fasta, roundup.dataset.getGenomeIndexPath(config.CURRENT_DATASET, genome))
            # store result in cache, so can do a redirect/get. 
            key = makeUniqueId()
            roundup_util.cacheSet(key, {'genome': genome, 'fasta': fasta, 'seqId': seqId})
            # redirect the post to a get.  http://en.wikipedia.org/wiki/Post/Redirect/Get
            return django.shortcuts.redirect(django.core.urlresolvers.reverse(lookup_result, kwargs={'key': key}))
    else:
        form = LookupForm() # An unbound form

    example = "{'fasta': '>example_nameline\\nMNFLWKGRRFLIAGILPTFEGAADEIVDKENKTYKAFLASKPPEETGLERLKQMFTIDEF', 'genome': '7227'}"
    return django.shortcuts.render(request, 'lookup.html', {'form': form, 'nav_id': 'lookup', 'form_doc_id': 'lookup',
                                                            'form_action': django.core.urlresolvers.reverse(lookup), 'form_example': example})

def lookup_result(request, key):
    if roundup_util.cacheHasKey(key):
        kw = roundup_util.cacheGet(key)
        page = '<h2>Lookup a Sequence Id for a FASTA Sequence Result</h2>\n<h3>Query</h3>Genome: <pre>{}</pre>'.format(GENOME_TO_NAME[kw['genome']])
        page += 'FASTA Sequence: <pre>{}</pre>'.format(kw['fasta'])
        page += u'<h3>Result</h3>Sequence Id: {}'.format(kw['seqId'])
        return django.shortcuts.render(request, 'regular.html', {'html': page, 'nav_id': 'contact'})
    else:
        raise django.http.Http404
        

#############################
# SEARCH_GENE_NAMES FUNCTIONS
#############################


class SearchGeneNamesForm(django.forms.Form):
    search_type = django.forms.ChoiceField(choices=SEARCH_GENE_NAMES_TYPE_CHOICES)
    query_string = django.forms.CharField()


def search_gene_names(request, key=None):
    '''
    get: render a form for user to search_gene_names the sequence id for a fasta sequence from a genome.
    post: redirect to a page which will show the id.
    key: used to pass a message (via the cache) 
    '''
    message = ''
    if request.method == 'POST': # If the form has been submitted...
        form = SearchGeneNamesForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            logging.debug(form.cleaned_data)
            search_type, query_string = form.cleaned_data['search_type'], form.cleaned_data['query_string']
            pairs = roundup_db.findGeneNameGenomePairsLike(
                config.CURRENT_RELEASE, substring=query_string,
                searchType=search_type)
            # store result in cache, so can do a redirect/get. 
            key = makeUniqueId()
            roundup_util.cacheSet(key, {'search_type': search_type, 'query_string': query_string, 'pairs': pairs})
            # redirect the post to a get.  http://en.wikipedia.org/wiki/Post/Redirect/Get
            return django.shortcuts.redirect(django.core.urlresolvers.reverse(search_gene_names_result, kwargs={'key': key}))
    else:
        if key and roundup_util.cacheHasKey(key):
            # a message for the search page can be passed via the cache.
            kw = roundup_util.cacheGet(key)
            message = kw['message']
            form = SearchGeneNamesForm(kw) # A bound form
        else:        
            form = SearchGeneNamesForm() # An unbound form

    example = "{'search_type': 'contains', 'query_string': 'ata'}" # javascript
    return django.shortcuts.render(request, 'search_gene_names.html', {'message': message, 'form': form, 'nav_id': 'search_gene_names', 'form_doc_id': 'search_gene_names',
                                                            'form_action': django.core.urlresolvers.reverse(search_gene_names), 'form_example': example})


def search_gene_names_result(request, key):
    '''
    search_type: e.g. starts with, contains, etc.
    query: the substring to search for
    '''
    if roundup_util.cacheHasKey(key):
        kw = roundup_util.cacheGet(key)
        pairs = kw['pairs']
        page = '<h2>Gene Names Search Result</h2>\n'
        page += u'<p>Gene names that &quot;{}&quot; the query string &quot;{}&quot;:</p>\n'.format(displayName(kw['search_type']), django.utils.html.escape(kw['query_string']))
        page += u'<div>{} matching combination{} of gene name and genome found.  Try another <a href="{}">search</a>.</div>'.format(len(pairs), '' if len(pairs) == 1 else 's', django.core.urlresolvers.reverse(search_gene_names))
        page += "<table>\n"
        page += "<tr><td>Gene Name</td><td>Genome</td></tr>\n"
        for geneName, genome in pairs:
            page += u'<tr><td>{}</td><td>{}: {}</td></tr>\n'.format(geneName, genome, GENOME_TO_NAME[genome])
        page += "</table>\n"
        return django.shortcuts.render(request, 'regular.html', {'html': page, 'nav_id': 'search_gene_names'})
    else:
        raise django.http.Http404


##################
# BROWSE FUNCTIONS
##################

class BrowseForm(django.forms.Form):
    primaryWidget = django.forms.CheckboxSelectMultiple()
    primary_genome_filter = django.forms.MultipleChoiceField(required=False, choices=CAT_CHOICES, widget=primaryWidget,
                                                      help_text='Filter which genomes appear in the Primary Genome list')
    primary_genome = django.forms.CharField(widget=django.forms.Select())
    identifier_type = django.forms.ChoiceField(choices=IDENTIFIER_TYPE_CHOICES)
    identifier = django.forms.CharField(required=False, max_length=100, widget=django.forms.TextInput(attrs={'size': '60'}))
    secondaryWidget = django.forms.CheckboxSelectMultiple()
    secondary_genomes_filter = django.forms.MultipleChoiceField(required=False, choices=CAT_CHOICES, widget=secondaryWidget,
                                                      help_text='Filter which genomes appear in the Secondary Genome Choices list')
    secondary_genome_choices = django.forms.CharField(required=False, help_text='Use to add a genome to Secondary Genomes box',
                                                      widget=django.forms.Select())
    secondary_genomes = django.forms.CharField(widget=django.forms.Textarea(), help_text='Enter one or more')
    divergence = django.forms.ChoiceField(choices=DIVERGENCE_CHOICES)
    evalue = django.forms.ChoiceField(choices=EVALUE_CHOICES, label='BLAST E-value')
    distance_lower_limit = django.forms.FloatField(help_text=DIST_LIMIT_HELP, required=False, max_value=19.0, min_value=0.0)
    distance_upper_limit = django.forms.FloatField(help_text=DIST_LIMIT_HELP, required=False, max_value=19.0, min_value=0.0)

    def clean_primary_genome(self):
        '''
        Transform name to genome.  Raise exception if a name is not valid.
        '''
        data = self.cleaned_data.get('primary_genome')
        if data not in NAME_TO_GENOME:
            msg = u'Please enter a Primary genome from our choices. {} is not.'.format(data)
            raise django.forms.ValidationError(msg)
        genome = NAME_TO_GENOME[data]
        return genome


    def clean_secondary_genomes(self):
        '''
        Transform names to genomes.  Raise exception if a name is not
        valid or there are not enough names.
        '''
        data = self.cleaned_data.get('secondary_genomes')
        names = [line.strip() for line in data.splitlines() if line.strip()]
        badNames = [n for n in names if n not in NAME_TO_GENOME]
        if badNames:
            msg = 'Please enter Secondary genomes only from our choices. The following are not: '+', '.join(badNames)
            raise django.forms.ValidationError(msg)
        if len(names) < 1:
            raise django.forms.ValidationError('At least one Secondary genomes must be entered.')
        # Always return the cleaned data, whether you have changed it or not.
        genomes = [NAME_TO_GENOME[n] for n in sorted(set(names))] # sort by name, remove duplicates
        return genomes

        
    def clean(self):
        '''
        make sure secondary genomes does not contain the primary genome
        '''
        primary_genome = self.cleaned_data.get('primary_genome')
        secondary_genomes = self.cleaned_data.get('secondary_genomes')
        if secondary_genomes and primary_genome in secondary_genomes:
            raise django.forms.ValidationError('Primary genome must not be among the selected Secondary genomes.')
        return self.cleaned_data
    

def browse(request):
    '''
    GET: send user the form to make a browse query
    POST: validate browse query and REDIRECT to result if it is good.
    '''
    if request.method == 'POST': # If the form has been submitted...
        form = BrowseForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            logging.debug(u'form.cleaned_data={}'.format(form.cleaned_data))
            orthQuery = makeOrthQueryFromBrowseForm(form)
            logging.debug(u'orthQuery={}'.format(orthQuery))

            # Process and add Browse Ids to the query
            # I would rather not have this complexity in here at all.  There must be a simpler and more powerful way.
            browseId = form.cleaned_data.get('identifier')
            browseIdType = form.cleaned_data.get('identifier_type')
            logging.debug(u'browseId={}, browseIdType={}'.format(browseId, browseIdType))
            if browseId and browseIdType == 'gene_name_type':
                genome = form.cleaned_data['primary_genome']
                seqIds = roundup_db.getSeqIdsForGeneName(
                    config.CURRENT_RELEASE, geneName=browseId, genome=genome)
                if not seqIds: # no seq ids matching the gene name were found.  oh no!
                    message = u'In your Browse query, Roundup did not find any gene named "{}" in the genome "{}".  Try searching for a gene name.'.format(browseId, GENOME_TO_NAME[genome])
                    # store result in cache, so can do a redirect/get. 
                    key = makeUniqueId()
                    roundup_util.cacheSet(key, {'message': message, 'search_type': 'contains', 'query_string': browseId})
                    return django.shortcuts.redirect(django.core.urlresolvers.reverse(search_gene_names, kwargs={'key': key}))
                else:
                    # remake orthQuery with seqIds
                    form.cleaned_data['seq_ids'] = seqIds
                    orthQuery = makeOrthQueryFromBrowseForm(form)
            elif browseId and browseIdType == 'seq_id_type':
                # remake orthQuery with seqIds
                form.cleaned_data['seq_ids'] = browseId.split() # split on whitespace
                orthQuery = makeOrthQueryFromBrowseForm(form)

            # cache the query and redirect to a page that will "get" the query result
            queryId = orthQueryHash(orthQuery)
            roundup_util.cacheSet(queryId, orthQuery)
            return django.shortcuts.redirect(django.core.urlresolvers.reverse(orth_query, kwargs={'queryId': queryId}))
    else:
        form = BrowseForm(initial={'primary_genome_filter': [value for value, name in CAT_CHOICES],
                                   'secondary_genomes_filter': [value for value, name in CAT_CHOICES]
                                   }) # An unbound form

    # example = json.dumps({'primary_genome': '559292', 'identifier': 'Q03834',
    #                       'identifier_type': 'seq_id_type', 'secondary_genomes': ['9606', '10090']})
    example = json.dumps({'primary_genome': 'Drosophila melanogaster',
                          'identifier': 'Q9VVT2', 'identifier_type': 'seq_id_type',
                          'secondary_genomes': 'Homo sapiens\nMus musculus\n'})
    # example = "{'primary_genome': 'MYCGE', 'secondary_genomes': ['MYCHH', 'MYCH1']}" # javascript
    # , 'include_gene_name': 'true', 'include_go_term': 'true'}" # javascript
    return django.shortcuts.render(request, 'browse.html',
                                   {'form': form, 'nav_id': 'browse', 'form_doc_id': 'browse', 'chosen_ids': ['id_primary_genome', 'id_secondary_genomes'],
                                    'form_action': django.core.urlresolvers.reverse(browse), 'form_example': example,
                                    'cat_genomes_json': json.dumps(CAT_GENOMES, indent=-1), })


###################
# CLUSTER FUNCTIONS
###################

class ClusterForm(django.forms.Form):
    genomesFilterWidget = django.forms.CheckboxSelectMultiple()
    genomes_filter = django.forms.MultipleChoiceField(required=False, choices=CAT_CHOICES, widget=genomesFilterWidget,
                                                      help_text='Filter which genomes appear in the Genome Choices list')
    genome_choices = django.forms.CharField(required=False, help_text='Use to add a genome to Genomes box',
                                                      widget=django.forms.Select())
    genomes = django.forms.CharField(widget=django.forms.Textarea(), help_text='Enter two or more')
    divergence = django.forms.ChoiceField(choices=DIVERGENCE_CHOICES)
    evalue = django.forms.ChoiceField(choices=EVALUE_CHOICES, label='BLAST E-value')
    distance_lower_limit = django.forms.FloatField(help_text=DIST_LIMIT_HELP, required=False, max_value=19.0, min_value=0.0)
    distance_upper_limit = django.forms.FloatField(help_text=DIST_LIMIT_HELP, required=False, max_value=19.0, min_value=0.0)
    tc_only = django.forms.BooleanField(label='Only Show Transitively Closed Gene Clusters', required=False, initial=False)
    
    def clean_genomes(self):
        '''
        Transform genome names to genome ids.  Raise exception if a name is not
        valid or there are not enough names.
        '''
        data = self.cleaned_data.get('genomes')
        names = [line.strip() for line in data.splitlines() if line.strip()]
        badNames = [n for n in names if n not in NAME_TO_GENOME]
        if badNames:
            raise django.forms.ValidationError('Please only enter genomes from our choices. These genomes are not: '+', '.join(badNames))
        if len(names) < 2:
            raise django.forms.ValidationError('At least two genomes must be entered.')
        # Always return the cleaned data, whether you have changed it or not.
        genomes = [NAME_TO_GENOME[n] for n in sorted(set(names))] # sort by name, remove duplicates
        return genomes


def cluster(request):
    '''
    GET: send user the form to make a cluster query
    POST: validate cluster query and REDIRECT to result if it is good.
    '''
    if request.method == 'POST': # If the form has been submitted...
        form = ClusterForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            orthQuery = makeOrthQueryFromClusterForm(form)
            queryId = orthQueryHash(orthQuery)
            roundup_util.cacheSet(queryId, orthQuery)
            # cache the query and redirect to a page that will run the query
            return django.shortcuts.redirect(django.core.urlresolvers.reverse(orth_query, kwargs={'queryId': queryId}))
    else:
        form = ClusterForm(initial={'genomes_filter': [value for value, name in CAT_CHOICES]}) # An unbound form

    example = json.dumps({'genomes': 'Homo sapiens\nMus musculus\nDrosophila melanogaster\n'})
    return django.shortcuts.render(request, 'cluster.html',
                                   {'form': form, 'nav_id': 'cluster', 'form_doc_id': 'cluster', 'chosen_ids': ['id_genomes'],
                                    'form_action': django.core.urlresolvers.reverse(cluster), 'form_example': example,
                                    'cat_genomes_json': json.dumps(CAT_GENOMES, indent=-1), })


###########################
# ORTHOLOGY QUERY FUNCTIONS
###########################

def getResultId(queryId):
    return '{}0'.format(queryId)


def makeUniqueId():
    '''
    create a new unique result id, like 17e038a69d604fb79028c85367727472.
    '''
    return uuid.uuid4().hex


def resultFilenameToId(filename):
    return os.path.basename(filename)[len('roundup_web_result_'):]


def makeDefaultOrthQuery():
    '''
    returns: a dict of orthology query keywords with sensible defaults for most query keywords.
    Some keywords, like genome and limit_genomes, or genomes, must be filled in before the query is valid.
    '''
    orthQuery = {}
    orthQuery['seq_ids'] = []
    orthQuery['genome'] = None
    orthQuery['genomes'] = []
    orthQuery['limit_genomes'] = []
    orthQuery['divergence'] = '0.2'
    orthQuery['evalue'] = '1e-20'
    orthQuery['tc_only'] = False
    orthQuery['gene_name'] = True
    orthQuery['go_term'] = True
    orthQuery['distance_lower_limit'] = None
    orthQuery['distance_upper_limit'] = None
    orthQuery['release'] = config.CURRENT_RELEASE # needed for orthquery
    orthQuery['dataset'] = config.CURRENT_DATASET # needed for orthresult
    return orthQuery


def makeOrthQueryFromBrowseForm(form):
    orthQuery = makeDefaultOrthQuery()
    orthQuery['seq_ids'] = form.cleaned_data.get('seq_ids', [])
    orthQuery['genome'] = form.cleaned_data.get('primary_genome')
    orthQuery['limit_genomes'] = form.cleaned_data.get('secondary_genomes', [])
    orthQuery['divergence'] = form.cleaned_data.get('divergence')
    orthQuery['evalue'] = form.cleaned_data.get('evalue')
    orthQuery['distance_lower_limit'] = form.cleaned_data.get('distance_lower_limit')
    orthQuery['distance_upper_limit'] = form.cleaned_data.get('distance_upper_limit')

    queryDesc = u'Browse Query:\n'
    queryDesc += u'\t{} = {}\n'.format(displayName('genome'), GENOME_TO_NAME[orthQuery['genome']])
    queryDesc += u'\t{} = {}\n'.format(displayName('identifier_type'), displayName(form.cleaned_data.get('identifier_type')))
    queryDesc += u'\t{} = {}\n'.format(displayName('identifier'), form.cleaned_data.get('identifier'))
    queryDesc += u'\t{} = {}\n'.format(displayName('limit_genomes'), '\n\t\t'.join([GENOME_TO_NAME[g] for g in orthQuery['limit_genomes']]))
    queryDesc += u'\t{} = {}\n'.format(displayName('divergence'), orthQuery['divergence'])
    queryDesc += u'\t{} = {}\n'.format(displayName('evalue'), orthQuery['evalue'])
    queryDesc += u'\t{} = {}\n'.format(displayName('distance_lower_limit'), orthQuery['distance_lower_limit'])
    queryDesc += u'\t{} = {}\n'.format(displayName('distance_upper_limit'), orthQuery['distance_upper_limit'])
    orthQuery['query_desc'] = queryDesc

    return orthQuery


def makeOrthQueryFromClusterForm(form):
    orthQuery = makeDefaultOrthQuery()
    orthQuery['genomes'] = form.cleaned_data.get('genomes', [])
    orthQuery['tc_only'] = form.cleaned_data.get('tc_only')
    orthQuery['divergence'] = form.cleaned_data.get('divergence')
    orthQuery['evalue'] = form.cleaned_data.get('evalue')
    orthQuery['distance_lower_limit'] = form.cleaned_data.get('distance_lower_limit')
    orthQuery['distance_upper_limit'] = form.cleaned_data.get('distance_upper_limit')

    queryDesc = u'Retrieve Query:\n'
    queryDesc += u'\t{} = {}\n'.format(displayName('genomes'), '\n\t\t'.join([GENOME_TO_NAME[g] for g in orthQuery['genomes']]))
    queryDesc += u'\t{} = {}\n'.format(displayName('divergence'), orthQuery['divergence'])
    queryDesc += u'\t{} = {}\n'.format(displayName('evalue'), orthQuery['evalue'])
    queryDesc += u'\t{} = {}\n'.format(displayName('distance_lower_limit'), orthQuery['distance_lower_limit'])
    queryDesc += u'\t{} = {}\n'.format(displayName('distance_upper_limit'), orthQuery['distance_upper_limit'])
    queryDesc += u'\t{} = {}\n'.format(displayName('tc_only'), orthQuery['tc_only'])
    orthQuery['query_desc'] = queryDesc

    return orthQuery


def orthQueryHash(query):
    '''
    return: a hash of query, i.e. a string which represents query compactly and is unlikely to collide with any other query.
    used as a cache key.
    unicode warning: uses ensure_ascii=False, so json.loads(json.dumps(obj)) == obj.
    '''
    return hashlib.sha1(json.dumps(query, ensure_ascii=False)).hexdigest()


def orth_result(request, resultId):
    '''
    GET: return an orthology result page
    '''
    logging.debug('orth_result resultId={}'.format(resultId))
    if orthresult.resultExists(resultId):
        resultType = request.GET.get('rt', orthresult.ORTH_RESULT)
        templateType = request.GET.get('tt', orthresult.WIDE_TEMPLATE)
        def urlFunc(resultId):
            return django.core.urlresolvers.reverse(orth_result, kwargs={'resultId': resultId})
        page = orthresult.renderResult(resultId, urlFunc, resultType=resultType, otherParams=request.GET)
        # page = orthresult.resultToAllGenesView(resultId)
        if templateType == orthresult.WIDE_TEMPLATE:
            return django.shortcuts.render(request, 'wide.html', {'html': page, 'nav_id': 'browse'})
        elif templateType == orthresult.DOWNLOAD_TEMPLATE:
            response = django.http.HttpResponse(page, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename=roundup_gene_clusters_for_result_{}.txt'.format(resultId)
            return response
        elif templateType == orthresult.DOWNLOAD_XML_TEMPLATE:
            response = django.http.HttpResponse(page, content_type='text/xml')
            response['Content-Disposition'] = 'attachment; filename=roundup_gene_clusters_for_result_{}.xml'.format(resultId)
            return response
        else:
            raise django.http.Http404
    else:
        raise django.http.Http404
    

def orth_query(request, queryId):
    '''
    run an orthology query to create a "result".
    GET: return a page which will get the result of the query.  either gets result from the cache or runs the query and stores the result in the cache.
    '''
    logging.debug('orth_query queryId={}'.format(queryId))

    if not roundup_util.cacheHasKey(queryId):
        raise django.http.Http404

    orthQuery = roundup_util.cacheGet(queryId)
    querySize = len(orthQuery['limit_genomes']) + len(orthQuery['genomes'])
    resultId = getResultId(queryId)
    resultPath = orthresult.getResultFilename(resultId)
    logging.debug(u'orth_query():\northQuery={}\nresultId={}\nqueryId={}\nresultPath={}'.format(orthQuery, resultId, queryId, resultPath))
    if USE_CACHE and roundup_util.cacheHasKey(resultId) and orthresult.resultExists(resultId):
        logging.debug('cache hit.')
        return django.shortcuts.redirect(django.core.urlresolvers.reverse(orth_result, kwargs={'resultId': resultId}))
    elif not config.NO_LSF and lsf.isJobNameOn(resultId, retry=True, delay=0.2):
        logging.debug('cache miss. job is already running.  go to waiting page.')
        return django.shortcuts.redirect(django.core.urlresolvers.reverse(orth_wait, kwargs={'resultId': resultId}))
    elif config.NO_LSF or querySize <= SYNC_QUERY_LIMIT:
        logging.debug('cache miss. run job sync.')
        # wait for query to run and store query
        roundup_util.do_orthology_query(cache_key=resultId,
                                        cache_file=resultPath,
                                        query_kws=orthQuery)
        return django.shortcuts.redirect(
            django.core.urlresolvers.reverse(orth_result,
                                             kwargs={'resultId': resultId}))
    else:
        logging.debug('cache miss. run job async.')
        # run on lsf and have result page poll for job completion
        roundup_util.bsub_orthology_query(cache_key=resultId,
                                          cache_file=resultPath,
                                          query_kws=orthQuery,
                                          job_name=resultId)
        return django.shortcuts.redirect(
            django.core.urlresolvers.reverse(orth_wait,
                                             kwargs={'resultId': resultId}))


def orth_wait(request, resultId):
    '''
    GET: return a page that waits until a result is ready and then displays it.
    '''
    url = django.core.urlresolvers.reverse(orth_result, kwargs={'resultId': resultId})
    message = 'Processing your request.  This might take a few minutes.  Thank you for your patience.'
    return django.shortcuts.render(request, 'wait.html', {'job': resultId, 'url': url, 'message': message})


def job_ready(request):
    '''
    a job is ready if job corresponds to an ended job.
    job parameter is a job name (it used to be a job id.)
    '''
    logging.debug('job_ready')
    # validate inputs to avoid malicious attacks
    job = request.GET.get('job')
    logging.debug('\tjob={}'.format(job))
    data = json.dumps({'ready': bool(not job or lsf.isJobNameOff(job, retry=True, delay=0.2))})
    logging.debug(u'\tdata={}'.format(data))
    # data = json.dumps({'ready': True})
    return django.http.HttpResponse(data, content_type='application/json')

