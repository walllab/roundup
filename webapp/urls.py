from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
                       # Examples:
                       url(r'^$', 'home.views.home', name='home'),
                       url(r'^documentation/$', 'home.views.documentation', name='documentation'),
                       url(r'^contact/$', 'home.views.contact', name='contact'),
                       url(r'^contact/thanks/$', 'home.views.contact_thanks', name='contact_thanks'),
                       url(r'^project_overview/$', 'home.views.project_overview', name='project_overview'),
                       url(r'^about/$', 'home.views.about', name='about'),
                       url(r'^updates/$', 'home.views.updates', name='updates'),
                       url(r'^genomes/$', 'home.views.genomes', name='genomes'),
                       url(r'^raw/$', 'home.views.raw', name='raw'),
                       url(r'^raw/download/(?P<first_genome>[^/]+)/(?P<second_genome>[^/]+)/(?P<divergence>[^/]+)/(?P<evalue>[^/]+)/$',
                           'home.views.raw_download', name='raw_download'),
                       url(r'^api/raw/download/(?P<first_genome>[^/]+)/(?P<second_genome>[^/]+)/(?P<divergence>[^/]+)/(?P<evalue>[^/]+)/$',
                           'home.views.api_raw_download', name='api_raw_download'),
                       url(r'^lookup/$', 'home.views.lookup', name='lookup'),
                       url(r'^lookup/result/(?P<key>[^/]+)/$', 'home.views.lookup_result', name='lookup_result'),
                       url(r'^browse/$', 'home.views.browse', name='browse'),
                       url(r'^retrieve/$', 'home.views.cluster', name='cluster'),
                       url(r'^orth/result/(?P<result_id>[^/]+)/$', 'home.views.orth_result', name='orth_result'),
                       url(r'^orth/wait/(?P<result_id>[^/]+)/(?P<job_id>[^/]+)/$', 'home.views.orth_wait', name='orth_wait'),
                       url(r'^api/job/ready/$', 'home.views.job_ready', name='job_ready'),
                       url(r'^sources/$', 'home.views.sources', name='sources'),
                       url(r'^search_gene_names/$', 'home.views.search_gene_names', name='search_gene_names'),
                       url(r'^search_gene_names/(?P<key>[^/]+)/$', 'home.views.search_gene_names', name='search_gene_names'),
                       url(r'^search_gene_names/result/(?P<key>[^/]+)/$', 'home.views.search_gene_names_result', name='search_gene_names_result'),
                       # url(r'^webapp/', include('webapp.foo.urls')),
                       
                       # Uncomment the admin/doc line below to enable admin documentation:
                       # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
                       
                       # Uncomment the next line to enable the admin:
                       # url(r'^admin/', include(admin.site.urls)),
                       )
