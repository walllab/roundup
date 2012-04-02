

'''
configuration which varies by environment.
configuration in this file overrides configuration in defaults.py
'''


import config.secrets
import mailutil


BLAST_BIN_DIR = '/usr/local/ncbi/blast/bin'
PROJ_BIN_DIR = '/Users/td23/bin'
NO_LSF = True
SITE_URL_ROOT = 'http://localhost:8000'
HTTP_HOST = 'localhost'
LOG_FROM_ADDR = 'todddeluca@yahoo.com'

# never deploy django in production with DEBUG==True
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DJANGO_DEBUG = True

# function for sending a single email
sendmail = mailutil.SMTPSSL('smtp.orchestra', 25,
        username=config.secrets.AMAZON_SES_SMTP_USERNAME,
        password=config.secrets.AMAZON_SES_SMTP_PASSWORD).sendone

