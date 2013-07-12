import datetime
import os
import sys
import traceback

# Add to sys.path the location of user-defined modules.  Assume user-defined
# modules (e.g. index.py) are located with passenger_wsgi.py, this file.
HERE = os.path.abspath(os.path.dirname(__file__))
# the app dir is added using a .pth file in the virtualenv.
# sys.path.append(HERE)

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

# Debugging stuff to figure out why the venv python was not working

# def log(msg):
    # import datetime
    # fn = os.path.expanduser('~/passenger_wsgi.log')
    # fh = open(fn, 'a')
    # fh.write(str(datetime.datetime.now()) + '\n')
    # fh.write(str(msg) + '\n')
    # fh.flush()
    # fh.close()

# def logcmd(cmd):
    # import subprocess
    # p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # out, err = p.communicate()
    # log('out='+out)
    # log('err='+err)
    # log('returncode='+str(p.returncode))

# log(os.environ)
# log(sys.executable)
# log(sys.argv)

# log('PYTHON='+PYTHON)
# logcmd(['date'])
# logcmd([PYTHON, '-c', ''])

# def application(environ, start_response):
    # start_response('200 OK', [('Content-type', 'text/plain')])
    # return ["Hello, world!"]

