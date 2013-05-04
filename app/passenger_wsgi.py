import datetime
import os
import sys
import traceback

# Add to sys.path the location of user-defined modules.  Assume user-defined
# modules (e.g. index.py) are located with passenger_wsgi.py, this file.
HERE = os.path.abspath(os.path.dirname(__file__))
sys.path.append(HERE)

# Replace python interpreter from apache with the project virtualenv python
PYTHON = os.path.abspath(os.path.join(HERE, '..', 'venv', 'bin', 'python'))
if sys.executable != PYTHON:
    os.execl(PYTHON, PYTHON, *sys.argv)


def exceptionLoggingMiddleware(application, logfile):
    def logApp(environ, start_response):
        try:
            return application(environ, start_response)
        except:
            fh = open(logfile, 'a')
            fh.write(datetime.datetime.now().isoformat()+'\n'+traceback.format_exc())
            fh.close()
            raise
    return logApp


# RUNNING A WSGI-APP USING PASSENGER requires setting 'application' to a wsgi-app
# run a django wsgi-application using phusion passenger: https://github.com/kwe/passenger-django-wsgi-example/tree/django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
# add middleware to log some exceptions
application = exceptionLoggingMiddleware(application, os.path.expanduser('~/passenger_wsgi.log'))



