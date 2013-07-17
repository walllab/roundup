
'''
Configuration that is specific to the website only, not dataset computation.
'''

import os

from webdeployenv import (ARCHIVE_DATASETS, CURRENT_DATASET, DJANGO_DEBUG,
                          NO_LSF, maintenance, maintenance_message)

# Silence pyflakes complaints about imports not being used. :-(
DJANGO_DEBUG, NO_LSF, ARCHIVE_DATASETS, maintenance, maintenance_message

# Roundup Datasets and Releases
CURRENT_DATASET = os.path.expanduser(CURRENT_DATASET)
CURRENT_RELEASE = os.path.basename(CURRENT_DATASET)

# Used for contact page
RT_EMAIL = 'submit-cbi@rt.med.harvard.edu'


# CACHE CONFIGURATION
CACHE_TABLE = 'roundup_cache'


# The physical location of static files served under the '/static/' url.
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'public/static'))



