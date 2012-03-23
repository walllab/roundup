
'''
Default configuration that varies by deployment environment.
These values will be overridden in some environments.
'''


import mailutil


BLAST_BIN_DIR = '/opt/blast-2.2.24/bin'
PROJ_BIN_DIR = '/home/td23/bin' # location of kalign
NO_LSF = False
LOG_FROM_ADDR = 'roundup-noreply@hms.harvard.edu'
SITE_URL_ROOT = 'http://roundup.hms.harvard.edu'
HTTP_HOST = 'roundup.hms.harvard.edu'


# function for sending a single email
sendmail = mailutil.SMTP('smtp.orchestra', 25).sendone


