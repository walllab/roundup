# Create your views here.

import logging
import sys
import re
import os
import uuid
import hashlib
import json

import django.http
import django.shortcuts
import django.forms
import django.core.exceptions
import django.core.urlresolvers
import django.utils.html

sys.path.append('..')
import config
import sendmail
import models
import roundup_common
import roundup_util
import orthquery
import orthresult
import BioUtilities
import roundup_db


USE_CACHE = False
GENOMES = sorted(roundup_common.getGenomes())
GENOME_CHOICES = [(g, orthresult.genomeDisplayName(g)) for g in GENOMES] # pairs of genome id and display name
DIVERGENCE_CHOICES = [(d, d) for d in roundup_common.DIVERGENCES]
EVALUE_CHOICES = [(d, d) for d in reversed(roundup_common.EVALUES)] # 1e-20 .. 1e-5
IDENTIFIER_TYPE_CHOICES = [('gene_name_type', 'Gene Name'), ('seq_id_type', 'Sequence Id')]
DISPLAY_NAME_MAP = {'fasta': 'FASTA Sequence', 'genome': 'Genome', 
                    'primary_genome': 'Primary Genome', 'secondary_genomes': 'Secondary Genomes', 'limit_genomes': 'Secondary Genomes', 'genomes': 'Genomes', 
                    'query_genome': 'First Genome', 'subject_genome': 'Second Genome', 'divergence': 'Divergence', 'evalue': 'BLAST E-value',
                    'distance_lower_limit': 'Distance Lower Limit', 'distance_upper_limit': 'Distance Upper Limit', 
                    'gene_name': 'Include Gene Names in Result', 'go_term': 'Include GO Terms in Result', 
                    'tc_only': 'Only Show Transitively Closed Gene Clusters', 
                    'identifier': 'Identifier', 'identifier_type': 'Identifier Type', 'gene_name_type': 'Gene Name', 'seq_id_type': 'Sequence Id',
                    'seq_ids': 'Sequence Identifiers',
                    'contains': 'Contain', 'equals': 'Equal', 'starts_with': 'Start With', 'ends_with': 'End With', 'substring': 'Text Substring'}
DIST_LIMIT_HELP = 'from 0.0 to 19.0'
SYNC_QUERY_LIMIT = 20 # run an asynchronous query (on lsf) if more than this many genomes are in the query.

def displayName(key, nameMap=DISPLAY_NAME_MAP):
    return nameMap.get(key, key)


def home(request):
    stats = roundup_util.getRoundupDataStats() # keys: numGenomes, numGenomePairs, numOrthologs
    return django.shortcuts.render(request, 'home.html', dict([('nav_id', 'home')] + stats.items()))


def documentation(request):
    return django.shortcuts.render(request, 'documentation.html', {'nav_id': 'documentation'})


def project_overview(request):
    stats = roundup_util.getRoundupDataStats() # keys: numGenomes, numGenomePairs, numOrthologs
    return django.shortcuts.render(request, 'project_overview.html', dict([('nav_id', 'project_overview')] + stats.items()))


def about(request):
    return django.shortcuts.render(request, 'about.html', {'nav_id': 'about'})
    

def genomes(request):
    return django.shortcuts.render(request, 'genomes.html', {'nav_id': 'genomes'})


def sources(request):
    descs = roundup_util.getGenomeDescriptions(GENOMES)
    return django.shortcuts.render(request, 'sources.html', {'nav_id': 'sources', 'sources': descs})


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
            sendmail.sendmail(form.cleaned_data['email'], [rtEmail], form.cleaned_data['subject'], message, method=config.MAIL_METHOD)
            # redirect the post to a get.  http://en.wikipedia.org/wiki/Post/Redirect/Get
            return django.shortcuts.redirect(django.core.urlresolvers.reverse(contact_thanks))
    else:
        form = ContactForm(auto_id=False) # An unbound form

    # return django.shortcuts.render(request, 'contact.html', {'form': form, 'nav_id': 'contact'})
    return django.shortcuts.render(request, 'contact.html', {'form': form, 'nav_id': 'contact', 'form_doc_id': None,
                                                         'form_action': django.core.urlresolvers.reverse(contact)})


def contact_thanks(request):
    page = '<div><h2>Thank you for contacting us!</h2><p>Your submission has been received and you should receive a confirmation email shortly.</p></div>'
    return django.shortcuts.render(request, 'regular.html', {'html': page, 'nav_id': 'contact'})
    

##############################
# DOWNLOAD ORTHOLOGS FUNCTIONS
##############################
    
class RawForm(django.forms.Form):
    first_genome = django.forms.ChoiceField(choices=GENOME_CHOICES)
    second_genome = django.forms.ChoiceField(choices=GENOME_CHOICES)
    divergence = django.forms.ChoiceField(choices=DIVERGENCE_CHOICES)
    evalue = django.forms.ChoiceField(choices=EVALUE_CHOICES, label='BLAST E-value')

    def clean(self):
        first_genome = self.cleaned_data.get('first_genome')
        second_genome = self.cleaned_data.get('second_genome')
        if first_genome == second_genome:
            raise django.forms.ValidationError('First genome and Second genome must be different.')
        return self.cleaned_data


def raw(request):
    '''
    get: render a form for user to request orthologs for a pair of genomes.
    post: redirect to a page which will download the ortholgos.
    '''
    if request.method == 'POST': # If the form has been submitted...
        form = RawForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            logging.debug(form.cleaned_data)
            first_genome, second_genome = sorted((form.cleaned_data['first_genome'], form.cleaned_data['second_genome']))
            kwargs = {'first_genome': first_genome, 'second_genome': second_genome, 'divergence': form.cleaned_data['divergence'], 'evalue': form.cleaned_data['evalue']}
            # redirect the post to a get.  http://en.wikipedia.org/wiki/Post/Redirect/Get
            return django.shortcuts.redirect(django.core.urlresolvers.reverse(raw_download, kwargs=kwargs))
    else:
        form = RawForm() # An unbound form

    return django.shortcuts.render(request, 'raw.html', {'form': form, 'nav_id': 'raw', 'form_doc_id': 'raw',
                                                         'form_action': django.core.urlresolvers.reverse(raw)})


def raw_download(request, first_genome, second_genome, divergence, evalue):
    '''
    get: render a page which lets the user know orthologs are being downloaded and then downloads the orthologs
    '''

    # validate parameters
    kw = {'first_genome': first_genome, 'second_genome': second_genome, 'divergence': divergence, 'evalue': evalue}
    form = RawForm(kw)
    if form.is_valid():
        desc = 'Downloading orthologs for:<ul><li>First genome: {}</li><li>Second genome: {}</li><li>Divergence: {}</li><li>BLAST E-value: {}</li></ul>'
        desc = desc.format(first_genome, second_genome, divergence, evalue)
        data = {'desc': desc, 'download_url': django.core.urlresolvers.reverse(api_raw_download, kwargs=kw)}
        return django.shortcuts.render(request, 'download.html', data)
    else:
        raise django.http.Http404


def api_raw_download(request, first_genome, second_genome, divergence, evalue):
    '''
    get: send orthologs for a pair of genomes as a file download.
    '''
    # validate parameters
    kw = {'first_genome': first_genome, 'second_genome': second_genome, 'divergence': divergence, 'evalue': evalue}
    form = RawForm(kw)
    if form.is_valid():
        # get data
        orthologs = roundup_util.getRawResults((first_genome, second_genome, divergence, evalue))
        # send data to requestor
        contentType = request.GET.get('ct', 'txt')
        response = django.http.HttpResponse(orthologs, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename={}_{}_{}_{}.txt'.format(first_genome, second_genome, divergence, evalue)
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
            seqId = BioUtilities.findSeqIdWithFasta(fasta, genome)
            # store result in cache, so can do a redirect/get. 
            key = orthresult.makeResultId()
            roundup_util.cacheSet(key, {'genome': genome, 'fasta': fasta, 'seqId': seqId})
            # redirect the post to a get.  http://en.wikipedia.org/wiki/Post/Redirect/Get
            return django.shortcuts.redirect(django.core.urlresolvers.reverse(lookup_result, kwargs={'key': key}))
    else:
        form = LookupForm() # An unbound form

    return django.shortcuts.render(request, 'lookup.html', {'form': form, 'nav_id': 'lookup', 'form_doc_id': 'lookup',
                                                         'form_action': django.core.urlresolvers.reverse(lookup)})

def lookup_result(request, key):
    if roundup_util.cacheHasKey(key):
        kw = roundup_util.cacheGet(key)
        page = '<h2>Lookup a Sequence Id for a FASTA Sequence Result</h2>\n<h3>Query</h3>Genome: <pre>{}</pre>'.format(orthresult.genomeDisplayName(kw['genome']))
        page += 'FASTA Sequence: <pre>{}</pre>'.format(kw['fasta'])
        page += '<h3>Result</h3>Sequence Id: {}'.format(kw['seqId'])
        return django.shortcuts.render(request, 'regular.html', {'html': page, 'nav_id': 'contact'})
    else:
        raise django.http.Http404
        

#############################
# SEARCH_GENE_NAMES FUNCTIONS
#############################

def search_gene_names(request, kind, query):
    '''
    kind: the kind of search: starts with, contains, etc.
    query: the substring to search for
    '''
    logging.debug('search_gene_names: kind={}, query={}'.format(kind, query))
    pass


###########################
# ORTHOLOGY QUERY FUNCTIONS
###########################

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
    orthQuery['gene_name'] = False
    orthQuery['go_term'] = False
    orthQuery['distance_lower_limit'] = None
    orthQuery['distance_upper_limit'] = None
    return orthQuery


def makeOrthQueryFromBrowseForm(form):
    orthQuery = makeDefaultOrthQuery()
    orthQuery['seq_ids'] = form.cleaned_data.get('seq_ids', [])
    orthQuery['genome'] = form.cleaned_data.get('primary_genome')
    orthQuery['limit_genomes'] = form.cleaned_data.get('secondary_genomes', [])
    orthQuery['gene_name'] = form.cleaned_data.get('include_gene_names')
    orthQuery['go_term'] = form.cleaned_data.get('include_go_terms')
    orthQuery['divergence'] = form.cleaned_data.get('divergence')
    orthQuery['evalue'] = form.cleaned_data.get('evalue')
    orthQuery['distance_lower_limit'] = form.cleaned_data.get('distance_lower_limit')
    orthQuery['distance_upper_limit'] = form.cleaned_data.get('distance_upper_limit')
    
    browseId = form.cleaned_data.get('identifier')
    browseIdType = form.cleaned_data.get('identifier_type')
    queryDesc = 'Browse Query:\n'
    queryDesc += '\t{}={}\n'.format(displayName('genome'), orthresult.genomeDisplayName(orthQuery['genome']))
    
    queryDesc += '\t{}={}\n'.format(displayName('identifier_type'), displayName(form.cleaned_data.get('identifier_type')))
    queryDesc += '\t{}={}\n'.format(displayName('identifier'), form.cleaned_data.get('identifier'))
    # queryDesc += '\t{}={}\n'.format(displayName('seq_ids'), ', '.join(orthQuery['seq_ids']))
    queryDesc += '\t{}={}\n'.format(displayName('limit_genomes'), ', '.join([orthresult.genomeDisplayName(g) for g in orthQuery['limit_genomes']]))
    queryDesc += '\t{}={}\n'.format(displayName('divergence'), orthQuery['divergence'])
    queryDesc += '\t{}={}\n'.format(displayName('evalue'), orthQuery['evalue'])
    queryDesc += '\t{}={}\n'.format(displayName('distance_lower_limit'), orthQuery['distance_lower_limit'])
    queryDesc += '\t{}={}\n'.format(displayName('distance_upper_limit'), orthQuery['distance_upper_limit'])
    queryDesc += '\t{}={}\n'.format(displayName('gene_name'), orthQuery['gene_name'])
    queryDesc += '\t{}={}\n'.format(displayName('go_term'), orthQuery['go_term'])
    orthQuery['query_desc'] = queryDesc

    return orthQuery


def makeOrthQueryFromClusterForm(form):
    orthQuery = makeDefaultOrthQuery()
    orthQuery['genomes'] = form.cleaned_data.get('genomes', [])
    orthQuery['tc_only'] = form.cleaned_data.get('tc_only')
    orthQuery['gene_name'] = form.cleaned_data.get('include_gene_names')
    orthQuery['go_term'] = form.cleaned_data.get('include_go_terms')
    orthQuery['divergence'] = form.cleaned_data.get('divergence')
    orthQuery['evalue'] = form.cleaned_data.get('evalue')
    orthQuery['distance_lower_limit'] = form.cleaned_data.get('distance_lower_limit')
    orthQuery['distance_upper_limit'] = form.cleaned_data.get('distance_upper_limit')
    
    queryDesc = 'Retrieve Query:\n'
    queryDesc += '\t{}={}\n'.format(displayName('genomes'), ', '.join([orthresult.genomeDisplayName(g) for g in orthQuery['genomes']]))
    queryDesc += '\t{}={}\n'.format(displayName('divergence'), orthQuery['divergence'])
    queryDesc += '\t{}={}\n'.format(displayName('evalue'), orthQuery['evalue'])
    queryDesc += '\t{}={}\n'.format(displayName('distance_lower_limit'), orthQuery['distance_lower_limit'])
    queryDesc += '\t{}={}\n'.format(displayName('distance_upper_limit'), orthQuery['distance_upper_limit'])
    queryDesc += '\t{}={}\n'.format(displayName('tc_only'), orthQuery['tc_only'])
    queryDesc += '\t{}={}\n'.format(displayName('gene_name'), orthQuery['gene_name'])
    queryDesc += '\t{}={}\n'.format(displayName('go_term'), orthQuery['go_term'])
    orthQuery['query_desc'] = queryDesc

    return orthQuery


def orthQueryHash(query):
    '''
    return: a hash of query, i.e. a string which represents query compactly and is unlikely to collide with any other query.
    unicode warning: uses ensure_ascii=False, so json.loads(json.dumps(obj)) == obj.
    '''
    return hashlib.sha1(json.dumps(query, ensure_ascii=False)).hexdigest()


##################
# BROWSE FUNCTIONS
##################

class BrowseForm(django.forms.Form):
    primary_genome = django.forms.ChoiceField(choices=GENOME_CHOICES)
    identifier_type = django.forms.ChoiceField(choices=IDENTIFIER_TYPE_CHOICES)
    identifier = django.forms.CharField(required=False, max_length=100, widget=django.forms.TextInput(attrs={'size': '60'}))
    secondary_genomes = django.forms.MultipleChoiceField(required=False, choices=GENOME_CHOICES)
    divergence = django.forms.ChoiceField(choices=DIVERGENCE_CHOICES)
    evalue = django.forms.ChoiceField(choices=EVALUE_CHOICES, label='BLAST E-value')
    distance_lower_limit = django.forms.FloatField(help_text=DIST_LIMIT_HELP, required=False, max_value=19.0, min_value=0.0)
    distance_upper_limit = django.forms.FloatField(help_text=DIST_LIMIT_HELP, required=False, max_value=19.0, min_value=0.0)
    include_gene_names = django.forms.BooleanField(required=False, initial=True)
    include_go_terms = django.forms.BooleanField(required=False, initial=True)

    def clean(self):
        primary_genome = self.cleaned_data.get('primary_genome')
        secondary_genomes = self.cleaned_data.get('secondary_genomes')
        logging.debug('clean(): secondary_genomes={}'.format(secondary_genomes))
        if secondary_genomes and primary_genome in secondary_genomes:
            raise django.forms.ValidationError('Primary genome must not be among the selected Secondary genomes.')
        return self.cleaned_data


def browse(request):
    '''
    GET: send user the form to make a browse query
    POST: validate browse query and REDIRECT to results if it is good.
    '''
    if request.method == 'POST': # If the form has been submitted...
        form = BrowseForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            logging.debug('form.cleaned_data={}'.format(form.cleaned_data))
            orthQuery = makeOrthQueryFromBrowseForm(form)
            logging.debug('orthQuery={}'.format(orthQuery))
            cacheKey = orthQueryHash(orthQuery)
            logging.debug(dir(request))
            jobId = None
            if USE_CACHE and roundup_util.cacheHasKey(cacheKey):
                resultPath = roundup_util.cacheGet(cacheKey)
                resultId = orthresult.resultFilenameToId(resultPath)
                logging.debug('cache hit.\n\tcacheKey: {}\n\tresultId: {}\n\tresultPath: {}'.format(cacheKey, resultId, resultPath))
            else:
                resultId = orthresult.makeResultId()
                resultPath = orthresult.getResultFilename(resultId)
                logging.debug('cache miss.\n\tcacheKey: {}\n\tresultId: {}\n\tresultPath: {}'.format(cacheKey, resultId, resultPath))

                # handle browse ids.  I would rather not have this complexity in here at all.  it seems like there must be a more generic and powerful search mechanism.
                browseId = form.cleaned_data.get('identifier')
                browseIdType = form.cleaned_data.get('identifier_type')
                logging.debug('browseId={}, browseIdType={}'.format(browseId, browseIdType))
                if browseId and browseIdType == 'gene_name_type':
                    genome = form.cleaned_data['primary_genome']
                    seqIds = roundup_db.getSeqIdsForGeneName(geneName=browseId, database=genome)
                    if not seqIds: # no seq ids matching the gene name were found.  oh no!
                        return django.shortcuts.redirect(django.core.urlresolvers.reverse(search_gene_names, kwargs={'kind': 'contains', 'query': browseId}))
                    else:
                        # remake orthQuery with seqIds
                        form.cleaned_data['seq_ids'] = seqIds
                        orthQuery = makeOrthQueryFromBrowseForm(form)
                elif browseId and browseIdType == 'seq_id_type':
                    # remake orthQuery with seqIds
                    form.cleaned_data['seq_ids'] = browseId.split() # split on whitespace
                    orthQuery = makeOrthQueryFromBrowseForm(form)

                querySize = len(orthQuery['limit_genomes']) + len(orthQuery['genomes'])
                if (querySize <= SYNC_QUERY_LIMIT):
                    # wait for query to run and store query
                    roundup_util.cacheDispatch(fullyQualifiedFuncName='orthquery.doOrthologyQuery', keywords=orthQuery, cacheKey=cacheKey, outputPath=resultPath)
                else:
                    # run on lsf and have result page poll job id.
                    jobId = roundup_util.lsfAndCacheDispatch(fullyQualifiedFuncName='orthquery.doOrthologyQuery', keywords=orthQuery, cacheKey=cacheKey, outputPath=resultPath)

            if not jobId:
                return django.shortcuts.redirect(django.core.urlresolvers.reverse(orth_result, kwargs={'result_id': resultId}))
            else:
                return django.shortcuts.redirect(django.core.urlresolvers.reverse(orth_wait, kwargs={'result_id': resultId, 'job_id': jobId}))
            # generate key for query
            # look for query in cache
            # if not in cache
            #   if big query, run async on lsf, getting jobid
            #   if small query, run sync on localhost
            # redirect to result page with query key
            # submit sync or async orthology query
    else:
        form = BrowseForm() # An unbound form

    return django.shortcuts.render(request, 'browse.html',
                                   {'form': form, 'nav_id': 'browse', 'form_doc_id': 'browse', 'form_action': django.core.urlresolvers.reverse(browse)})

        
def orth_result(request, result_id):
    '''
    GET: send user a waiting page that will display results when ready.
    '''
    logging.debug('orth_result result_id={}'.format(result_id))
    if orthresult.resultExists(result_id):
        resultType = request.GET.get('rt', orthresult.ORTH_RESULT)
        templateType = request.GET.get('tt', orthresult.WIDE_TEMPLATE)
        def urlFunc(resultId):
            return django.core.urlresolvers.reverse(orth_result, kwargs={'result_id': resultId})
        page = orthresult.renderResult(result_id, urlFunc, resultType=resultType, otherParams=request.GET)
        # page = orthresult.resultToAllGenesView(result_id)
        if templateType == orthresult.WIDE_TEMPLATE:
            return django.shortcuts.render(request, 'wide.html', {'html': page, 'nav_id': 'browse'})
        elif templateType == orthresult.DOWNLOAD_TEMPLATE:
            response = django.http.HttpResponse(page, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename=roundup_{}_{}_result.txt'.format(resultType, result_id)
            return response
    # else:
    raise django.http.Http404
    

def orth_wait(request, result_id, job_id):
    '''
    GET: send user a waiting page that will display results when ready.
    '''
    # url = django.core.urlresolvers.reverse(browse_wait, kwargs={'result_id': result_id, 'job_id': job_id})
    # return django.shortcuts.render(request, 'wait.html', {'url': url, 'message': 'Processing your request.  This might take a few minutes.  Thank you for your patience.'})
    url = django.core.urlresolvers.reverse(orth_result, kwargs={'result_id': result_id})
    message = 'Processing your request.  This might take a few minutes.  Thank you for your patience.'
    return django.shortcuts.render(request, 'wait.html', {'job_id': job_id, 'url': url, 'message': message})


def job_ready(request):
    # validate inputs to avoid malicious attacks
    jobId = str(int(request.GET.get('jobid'))) 
    logging.debug('job_ready: jobid={}'.format(jobId))
    data = json.dumps({'ready': bool(not jobId or roundup_util.isEndedJob(jobId))})
    # data = json.dumps({'ready': True})
    return django.http.HttpResponse(data, content_type='application/json')


###################
# CLUSTER FUNCTIONS
###################

class ClusterForm(django.forms.Form):
    genomes = django.forms.MultipleChoiceField(choices=GENOME_CHOICES, help_text='Select two or more')
    divergence = django.forms.ChoiceField(choices=DIVERGENCE_CHOICES)
    evalue = django.forms.ChoiceField(choices=EVALUE_CHOICES, label='BLAST E-value')
    distance_lower_limit = django.forms.FloatField(help_text=DIST_LIMIT_HELP, required=False, max_value=19.0, min_value=0.0)
    distance_upper_limit = django.forms.FloatField(help_text=DIST_LIMIT_HELP, required=False, max_value=19.0, min_value=0.0)
    tc_only = django.forms.BooleanField(label='Only Show Transitively Closed Gene Clusters', required=False, initial=False)
    include_gene_names = django.forms.BooleanField(required=False, initial=True)
    include_go_terms = django.forms.BooleanField(required=False, initial=True)
    
    def clean_genomes(self):
        data = self.cleaned_data.get('genomes')
        logging.debug('clean_genomes(): data={}'.format(data))
        if data is None or len(data) < 2:
            raise django.forms.ValidationError('At least two Genomes must be selected.')
        # Always return the cleaned data, whether you have changed it or not.
        return data


def cluster(request):
    '''
    GET: send user the form to make a cluster query
    POST: validate cluster query and REDIRECT to results if it is good.
    '''
    if request.method == 'POST': # If the form has been submitted...
        form = ClusterForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            logging.debug('form.cleaned_data={}'.format(form.cleaned_data))
            orthQuery = makeOrthQueryFromClusterForm(form)
            logging.debug('orthQuery={}'.format(orthQuery))
            cacheKey = orthQueryHash(orthQuery)
            logging.debug(dir(request))
            jobId = None
            if USE_CACHE and roundup_util.cacheHasKey(cacheKey):
                resultPath = roundup_util.cacheGet(cacheKey)
                resultId = orthresult.resultFilenameToId(resultPath)
                logging.debug('cache hit.\n\tcacheKey: {}\n\tresultId: {}\n\tresultPath: {}'.format(cacheKey, resultId, resultPath))
            else:
                resultId = orthresult.makeResultId()
                resultPath = orthresult.getResultFilename(resultId)
                logging.debug('cache miss.\n\tcacheKey: {}\n\tresultId: {}\n\tresultPath: {}'.format(cacheKey, resultId, resultPath))
                querySize = len(orthQuery['limit_genomes']) + len(orthQuery['genomes'])
                if (querySize <= SYNC_QUERY_LIMIT):
                    # wait for query to run and store query
                    roundup_util.cacheDispatch(fullyQualifiedFuncName='orthquery.doOrthologyQuery', keywords=orthQuery, cacheKey=cacheKey, outputPath=resultPath)
                else:
                    # run on lsf and have result page poll job id.
                    jobId = roundup_util.lsfAndCacheDispatch(fullyQualifiedFuncName='orthquery.doOrthologyQuery', keywords=orthQuery, cacheKey=cacheKey, outputPath=resultPath)

            if not jobId:
                return django.shortcuts.redirect(django.core.urlresolvers.reverse(orth_result, kwargs={'result_id': resultId}))
            else:
                return django.shortcuts.redirect(django.core.urlresolvers.reverse(orth_wait, kwargs={'result_id': resultId, 'job_id': jobId}))
            # generate key for query
            # look for query in cache
            # if not in cache
            #   if big query, run async on lsf, getting jobid
            #   if small query, run sync on localhost
            # redirect to result page with query key
            # submit sync or async orthology query
    else:
        form = ClusterForm() # An unbound form

    return django.shortcuts.render(request, 'cluster.html',
                                   {'form': form, 'nav_id': 'cluster', 'form_doc_id': 'cluster', 'form_action': django.core.urlresolvers.reverse(cluster)})




