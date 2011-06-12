
import os
import sys

# passenger: replace python2.5 interpreter from apache with python2.7
INTERP = "/home/td23/bin/python"
if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)

# add to sys.path the location of user-defined modules
# assume user-defined modules (e.g. index.py) are located with passenger_wsgi.py, this file.
sys.path.append(os.path.dirname(__file__))

# RUNNING A WSGI-APP USING PASSENGER requires setting 'application' to a wsgi-app

def putDbCredsInEnvWSGIMiddleware(application):
    '''
    application: a wsgi application (callable) that needs genotator msyql creds in os.environ
    return: a wsgi application callable that when called moves genotator mysql credentials from the wsgi environ to os.environ
    '''
    def putCredsApp(environ, start_response):
        for key in ('ROUNDUP_MYSQL_SERVER', 'ROUNDUP_MYSQL_DB', 'ROUNDUP_MYSQL_USER', 'ROUNDUP_MYSQL_PASSWORD'):
            if environ.has_key(key):
                os.environ[key] = environ[key]
        return application(environ, start_response)
    return putCredsApp


# run a django wsgi-application using phusion passenger: https://github.com/kwe/passenger-django-wsgi-example/tree/django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import django.core.handlers.wsgi
application = putDbCredsInEnvWSGIMiddleware(django.core.handlers.wsgi.WSGIHandler())

