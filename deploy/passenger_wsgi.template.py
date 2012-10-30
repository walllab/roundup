import datetime
import os
import sys
import traceback


# add to sys.path the location of user-defined modules
# assume user-defined modules (e.g. index.py) are located with passenger_wsgi.py, this file.
sys.path.append(os.path.dirname(__file__))

# passenger: replace python interpreter from apache with python2.7
PYTHON_EXE = '%(python_exe)s'
if sys.executable != PYTHON_EXE:
    os.execl(PYTHON_EXE, PYTHON_EXE, *sys.argv)


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



