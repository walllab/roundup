
import datetime
import os
import sys

# add to sys.path the location of user-defined modules
# assume user-defined modules (e.g. index.py) are located with passenger_wsgi.py, this file.
sys.path.append(os.path.dirname(__file__))

import deploy_env

INTERP = deploy_env.PYTHON_EXE # = "/home/td23/bin/python"
if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)

def exceptionLoggingMiddleware(application, logfile):
    import traceback
    def logApp(environ, start_response):
        try:
            return application(environ, start_response)
        except:
            with open(logfile, 'a') as fh:
                fh.write(datetime.datetime.now().isoformat()+'\n'+traceback.format_exc())
            raise
    return logApp
            

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

# RUNNING A WSGI-APP USING PASSENGER requires setting 'application' to a wsgi-app

application = django.core.handlers.wsgi.WSGIHandler()
application = putDbCredsInEnvWSGIMiddleware(application)
application = exceptionLoggingMiddleware(application, os.path.expanduser('~/passenger_wsgi.log'))

# # simple wsgi apps for testing
# def application(environ, start_response):
#     status = '200 OK'
#     headers = [('Content-type', 'text/html')]
#     start_response(status, headers)
#     parts = ['<html><head></head><body><img src="/wsgi-snake.jpg"/><pre>'] # image tests serving static content
#     parts += ['%s: %s\n' % (key, value) for key, value in environ.iteritems()]
#     parts += ['</pre></body></html>']
#     return parts
# def application(environ, start_response):
#     start_response('200 OK', [('Content-type', 'text/plain')])
#     return ["Hello, world!"]




