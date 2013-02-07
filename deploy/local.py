

'''
configuration which varies by environment.
configuration in this file overrides configuration in defaults.py
'''


CURRENT_DATASET = '~/sites/local.roundup/datasets/test_dataset'
MAIL_SERVICE_TYPE = 'amazon_ses'
BLAST_BIN_DIR = '/usr/local/bin' # location of blastp
PROJ_BIN_DIR = '/usr/local/bin' # location of kalign
NO_LSF = True
LOG_FROM_ADDR = 'todddeluca@yahoo.com'
SITE_URL_ROOT = 'http://localhost:8000'
HTTP_HOST = 'localhost'
# never deploy django in production with DEBUG==True
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DJANGO_DEBUG = True

