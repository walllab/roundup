from django.conf.urls.defaults import patterns, url
from django.http import HttpResponse

urlpatterns = patterns(
    '',
    url(r'^$', 'home.views.home', name='home'),

    # Disallow robots from downloading huge files.
    # http://fredericiana.com/2010/06/09/three-ways-to-add-a-robots-txt-to-your-django-project/
    # https://docs.djangoproject.com/en/dev/topics/http/urls/#passing-callable-objects-instead-of-strings
    # http://www.robotstxt.org/robotstxt.html
    url(r'^robots.txt$', lambda r: HttpResponse('User-agent: *\nDisallow: /api/download/', mimetype="text/plain")),

    url(r'^documentation/$', 'home.views.documentation', name='documentation'),
    url(r'^contact/$', 'home.views.contact', name='contact'),
    url(r'^about/$', 'home.views.about', name='about'),
    url(r'^updates/$', 'home.views.updates', name='updates'),
    url(r'^genomes/$', 'home.views.genomes', name='genomes'),

    url(r'^download/$', 'home.views.download', name='download'),
    url(r'^download/raw/(?P<first_genome>[^/]+)/(?P<second_genome>[^/]+)/(?P<divergence>[^/]+)/(?P<evalue>[^/]+)/$',
        'home.views.raw_download', name='raw_download'),
    url(r'^api/download/raw/(?P<first_genome>[^/]+)/(?P<second_genome>[^/]+)/(?P<divergence>[^/]+)/(?P<evalue>[^/]+)/$',
        'home.views.api_raw_download', name='api_raw_download'),

    url(r'^lookup/$', 'home.views.lookup', name='lookup'),
    url(r'^lookup/result/(?P<key>[^/]+)/$', 'home.views.lookup_result', name='lookup_result'),
    url(r'^browse/$', 'home.views.browse', name='browse'),
    url(r'^retrieve/$', 'home.views.cluster', name='cluster'),
    url(r'^orth/query/(?P<queryId>[^/]+)/$', 'home.views.orth_query', name='orth_query'),
    url(r'^orth/result/(?P<resultId>[^/]+)/$', 'home.views.orth_result', name='orth_result'),
    url(r'^orth/wait/(?P<resultId>[^/]+)/$', 'home.views.orth_wait', name='orth_wait'),
    url(r'^api/job/ready/$', 'home.views.job_ready', name='job_ready'),
    url(r'^search_gene_names/$', 'home.views.search_gene_names', name='search_gene_names'),
    url(r'^search_gene_names/(?P<key>[^/]+)/$', 'home.views.search_gene_names', name='search_gene_names'),
    url(r'^search_gene_names/result/(?P<key>[^/]+)/$', 'home.views.search_gene_names_result', name='search_gene_names_result'),
)
