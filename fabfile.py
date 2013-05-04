'''
# Usage examples:

Quickly deploy code to development environment on orchestra:

    fab dev deploy

Push new configuration values to a deployment:

    fab dev conf

The first time starting a website, you need a fresh install of all code and
packages in the virtualenv.

    fab ds:4 full

Do a clean deployment of code and config to production website:

    fab prod most

Get the virtualenv up and running for a deployment environment:

    fab local venv_create venv_install

Remove and recreate the virtualenv:

    fab dev venv_remove venv_create venv_install

Save the requirements of a virtualenv to requirements.txt:

    fab dev venv_freeze

The file allows deployment to remote hosts, assuming key pairs and permissions
are good.
'''


import StringIO
import os
import sys

from fabric.api import cd, env, execute, put, require, run, task
from fabric.contrib.files import upload_template
from fabric.contrib.project import rsync_project

import diabric.venv
import diabric.config
import diabric.files


HERE = os.path.abspath(os.path.dirname(__file__))
# deploy envs options
DEPLOY_OPTS = ['local', 'dev', 'prod', 'dataset']

REQUIREMENTS = os.path.join(HERE, 'requirements.txt')


###############
# CONFIGURATION


# a global configuration "dictionary" (actually an attribute namespace).
# an alternative to fabric.api.env, which IMHO is a bad place to store
# application configuration, since that can conflict with fabric internals and
# it is not flexible enough to store per-host configuration.
config = diabric.config.Namespace()


def post_config(config):
    '''
    Called by one of the deployment environment configuration tasks: dev, prod,
    etc.  Sets some values in `config`.
    '''
    config.log = os.path.join(config.site_dir, 'log')
    config.tmp = os.path.join(config.site_dir, 'tmp')
    config.venv = os.path.join(config.deploy_dir, 'venv')
    config.app = os.path.join(config.deploy_dir, 'app')
    config.python = os.path.join(config.venv, 'bin', 'python')
    env.configured = True
    return config


@task
def local():
    '''
    Configure tasks for local deployment.
    '''
    env.hosts = ['localhost']
    config.deploy_env = 'local'
    config.website = True
    config.system_python = '/usr/local/bin/python'
    config.deploy_dir = os.path.expanduser('~/www/local.roundup.hms.harvard.edu')
    config.site_dir = os.path.expanduser('~/sites/local.roundup')
    config.archive_datasets = [os.path.expanduser('~/sites/local.roundup/datasets/test_dataset')]
    config.current_dataset = config.archive_datasets[0]
    config.mail_service_type = 'amazon_ses'
    config.blast_bin_dir = '/usr/local/bin'
    config.kalign_bin_dir = '/usr/local/bin'
    config.no_lsf = True
    config.log_from_addr = 'todddeluca@yahoo.com'
    config.django_debug = True

    post_config(config)


@task
def dev():
    '''
    Configure tasks for development deployment.
    '''
    env.hosts = ['orchestra.med.harvard.edu']
    config.deploy_env = 'dev'
    config.website = True
    config.system_python = '/groups/cbi/bin/python2.7'
    config.deploy_dir = '/www/dev.roundup.hms.harvard.edu'
    config.site_dir = '/groups/public+cbi/sites/dev.roundup'
    config.archive_datasets = ['/groups/public+cbi/sites/roundup/datasets/4',
                               '/groups/public+cbi/sites/roundup/datasets/3',
                               '/groups/public+cbi/sites/roundup/datasets/2',
                               '/groups/public+cbi/sites/roundup/datasets/qfo_2011_04']
    config.current_dataset = config.archive_datasets[0]
    config.mail_service_type = 'orchestra'
    config.blast_bin_dir = '/opt/blast-2.2.24/bin'
    config.kalign_bin_dir = '/home/td23/bin'
    config.no_lsf = False
    config.log_from_addr = 'roundup-noreply@hms.harvard.edu'
    config.django_debug = False

    post_config(config)


@task
def prod():
    '''
    Configure tasks for production deployment.
    '''
    env.hosts = ['orchestra.med.harvard.edu']
    config.website = True
    config.deploy_env = 'prod'
    config.system_python = '/groups/cbi/bin/python2.7'
    config.deploy_dir = '/www/roundup.hms.harvard.edu'
    config.site_dir = '/groups/public+cbi/sites/roundup'
    config.archive_datasets = ['/groups/public+cbi/sites/roundup/datasets/4',
                               '/groups/public+cbi/sites/roundup/datasets/3',
                               '/groups/public+cbi/sites/roundup/datasets/2',
                               '/groups/public+cbi/sites/roundup/datasets/qfo_2011_04']
    config.current_dataset = config.archive_datasets[0]
    config.mail_service_type = 'orchestra'
    config.blast_bin_dir = '/opt/blast-2.2.24/bin'
    config.kalign_bin_dir = '/home/td23/bin'
    config.no_lsf = False
    config.log_from_addr = 'roundup-noreply@hms.harvard.edu'
    config.django_debug = False

    post_config(config)


@task
def ds(dsid):
    '''
    Configure tasks for dataset deployment.  Code is deployed to a code
    directory parallel to the dataset directory, so a dataset can have its
    own code version independent of the websites and other datasets.

    dsid (string): The id of the dataset.  E.g. '4'.  This is used to derive
    a dataset directory.
    '''
    dsid = os.path.basename(dsid)
    assert dsid

    env.hosts = ['orchestra.med.harvard.edu']
    config.deploy_env = 'dataset'
    config.website = False
    config.system_python = '/groups/cbi/bin/python2.7'
    config.deploy_dir = '/groups/public+cbi/sites/roundup/code/{}'.format(dsid)
    config.site_dir = '/groups/public+cbi/sites/roundup'
    config.mail_service_type = 'orchestra'
    config.blast_bin_dir = '/opt/blast-2.2.24/bin'
    config.kalign_bin_dir = '/home/td23/bin'
    config.log_from_addr = 'roundup-noreply@hms.harvard.edu'

    post_config(config)


############
# VENV TASKS

@task
def venv_create():
    require('configured')
    diabric.venv.create(config.venv, config.system_python)


@task
def venv_install():
    require('configured')
    diabric.venv.install(config.venv, REQUIREMENTS)


@task
def venv_freeze():
    require('configured')
    diabric.venv.freeze(config.venv, REQUIREMENTS)


@task
def venv_remove():
    require('configured')
    diabric.venv.remove(config.venv)


############
# CODE TASKS

@task
def clean():
    '''
    Remove deployed configuration, code, dirs and link.  Does not remove 
    project data like log files and datasets.
    '''
    require('configured')
    targets = [config.app]
    if config.website:
        targets.append(os.path.join(config.deploy_dir, 'docroot'))

    with cd(config.deploy_dir):
        run('rm -rf ' + ' '.join(targets))


@task
def init():
    '''
    Make directory for deploying code and configuration.
    Make directories used by code, like the log dir and tmp dir.
    Make the link required by Phusion Passenger and Apache.
    '''
    require('configured')
    run('mkdir -p -m 2775 ' + ' '.join([config.log, config.tmp, config.app,
                                        config.deploy_dir]))

    if config.website:
        # passenger requires that docroot be a link to the webapp's public dir
        run('mkdir -p -m 2775 ' + os.path.join(config.deploy_dir, 'app', 'public'))
        with cd(config.deploy_dir):
            run('rm -f docroot')
            # make link b/c apache likes docroot and passenger likes app/public.
            run('ln -s app/public docroot')


@task
def conf():
    '''
    Deploy configuration files, files that vary by deployment environment.
    '''
    require('configured')

    # copy secrets files
    put(os.path.join(HERE, 'secrets/{}.py'.format(config.deploy_env)),
        os.path.join(config.app, 'secrets.py'), mode=0660)


    # Create app.pth to add app dir to sys.path when using the virtualenv.
    text = StringIO.StringIO()
    text.write("# Autogenerated file.  Do not modify.\n")
    text.write(config.app + '\n')
    put(text, os.path.join(config.venv, 'lib', 'python2.7', 'site-packages',
                           'app.pth'), mode=0664)

    # Create deployenv.py file and upload it
    text = StringIO.StringIO()
    text.write("# Autogenerated file.  Do not modify.\n")
    text.write("# Configuration which varies by environment.\n")
    text.write("\n")
    text.write("MAIL_SERVICE_TYPE = {!r}\n".format(config.mail_service_type))
    text.write("BLAST_BIN_DIR = {!r}\n".format(config.blast_bin_dir))
    text.write("KALIGN_BIN_DIR = {!r}\n".format(config.kalign_bin_dir))
    text.write("LOG_FROM_ADDR = {!r}\n".format(config.log_from_addr))
    text.write("TMP_DIR = {!r}\n".format(config.tmp))
    text.write("LOG_DIR = {!r}\n".format(config.log))
    put(text, os.path.join(config.app, 'deployenv.py'), mode=0664)

    if config.website:

        # .htaccess specifies where to find passenger_wsgi.py
        upload_template(
            os.path.join(HERE, 'deploy/.htaccess.template'),
            os.path.join(config.app, 'public/.htaccess'),
            context={'app_dir': config.app}, mode=0664)

        # Create webdeployenv.py file and upload it
        text = StringIO.StringIO()
        text.write("# Autogenerated file.  Do not modify.\n")
        text.write("# Web-specific configuration which varies by environment.\n")
        text.write("\n")
        text.write("ARCHIVE_DATASETS = {!r}\n".format(config.archive_datasets))
        text.write("CURRENT_DATASET = {!r}\n".format(config.current_dataset))
        text.write("NO_LSF = {!r}\n".format(config.no_lsf))
        text.write('# never deploy django in production with DEBUG==True\n')
        text.write('# https://docs.djangoproject.com/en/dev/ref/settings/#debug\n')
        text.write("DJANGO_DEBUG = {!r}\n".format(config.django_debug))
        put(text, os.path.join(config.app, 'webdeployenv.py'), mode=0664)


@task
def deploy():
    '''
    If host is specified, user should also be specified, and vice versa.
    Copy files from src to deployment dir, including renaming one file.
    '''
    require('configured')

    # copy files to remote destintation, excluding backups, .svn dirs, etc.
    # do not deploy these files/dirs.
    deployExcludes = ['**/old', '**/old/**', '**/semantic.cache', '**/.svn', '**/.svn/**', '**/*.pyc',
                      '**/*.pyo', '**/.DS_Store', '**/*~']
    rsync_project(
        remote_dir=config.deploy_dir,
        local_dir=os.path.join(HERE, 'app'),
        exclude=deployExcludes,
        delete=False)


@task
def link_downloads():
    '''
    Create links (and directories as needed) under the static web dir to the
    download files for various data sets.  This allows dataset files to be
    served statically (e.g. via apache) instead of through django.
    '''
    require('configured')

    with cd(config.app):
        run(config.python + ' roundup_util.py link_downloads')


@task
def restart():
    '''
    Restart Phusion Passenger webapp, so changes take effect on the website.
    '''
    require('configured')
    # touch passenger restart.txt, so passenger will pick up the changes.
    with cd(config.app):
        run ('touch tmp/restart.txt')


#########################################
# CONVENIENCE TASKS FOR DOING MANY THINGS


@task
def full():
    '''
    Do absolutely everything to deploy the code, including creating a virtual
    environment and installing packages.
    '''
    require('configured')
    execute(venv_remove)
    execute(venv_create)
    execute(most)


@task
def most():
    '''
    Do everything necessary for a clean deployment of code to the website.
    '''
    require('configured')
    execute(venv_install)
    execute(clean)
    execute(init)
    execute(conf)
    execute(deploy)
    
    if config.website:
        execute(link_downloads)
        execute(restart)


if __name__ == '__main__':
    main()


# pass

