
'''
configuration which varies by environment.
'''

CURRENT_DATASET = '/groups/cbi/sites/dev.roundup/datasets/test_dataset'
MAIL_SERVICE_TYPE = 'orchestra'
BLAST_BIN_DIR = '/opt/blast-2.2.24/bin'
PROJ_BIN_DIR = '/home/td23/bin' # location of kalign
NO_LSF = False
LOG_FROM_ADDR = 'roundup-noreply@hms.harvard.edu'
SITE_URL_ROOT = 'http://dev.roundup.hms.harvard.edu'
HTTP_HOST = 'dev.roundup.hms.harvard.edu'
# never deploy django in production with DEBUG==True
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DJANGO_DEBUG = False


