'''
# Usage examples:

Deploy code to development environment on orchestra:

    fab dev deploy

Push new configuration values to a deployment:

    fab dev conf

Deploy code to a specific roundup dataset (e.g. 4).  This is useful for
creating an install of roundup for use in computing a large dataset without
depending on other code that might change/break during the time of the 
computation:

    fab ds:4 deploy

Do a clean deployment of code to production:

    fab prod all

Initialize the project directories (e.g. In /groups/cbi/dev.roundup) for local
environment:

    fab local init_proj

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


###############
# CONFIGURATION

def pre_config(config):
    '''
    Called before the deployment environment configuration tasks.  Sets some
    values in `config` that do not depend on the deployment env.
    '''
    # location of a pip requirements.txt file.
    # used to persist package volumes or recreate a virtual environment.
    config.requirements = os.path.join(HERE, 'requirements.txt')
    return config


def post_config(config):
    '''
    Called by one of the deployment environment configuration tasks: dev, prod,
    etc.  Sets some values in `config`.
    '''
    config.venv = os.path.join(config.deploy_dir, 'venv')
    config.app = os.path.join(config.deploy_dir, 'app')
    config.python = os.path.join(config.venv, 'bin', 'python')
    env.configured = True
    return config


# a global configuration "dictionary" (actually an attribute namespace).
# an alternative to fabric.api.env, which IMHO is a bad place to store
# application configuration, since that can conflict with fabric internals and
# it is not flexible enough to store per-host configuration.
config = pre_config(diabric.config.Namespace())



@task
def local():
    '''
    Configure tasks for local deployment.
    '''
    env.hosts = ['localhost']
    config.deploy_env = 'local'
    config.system_python = '/usr/local/bin/python'
    config.deploy_dir = os.path.expanduser('~/www/local.roundup.hms.harvard.edu')
    config.site_dir = os.path.expanduser('~/sites/local.roundup')
    config.archive_datasets = [os.path.join(config.site_dir, 'datasets', 'test_dataset')]
    config.current_dataset = config.archive_datasets[0]
    config.mail_service_type = 'amazon_ses'
    config.blast_bin_dir = '/usr/local/bin'
    config.kalign_bin_dir = '/usr/local/bin'
    config.no_lsf = True
    config.log_from_addr = 'todddeluca@yahoo.com'
    config.site_url_root = 'http://localhost:8000'
    config.http_host = 'localhost'
    config.django_debug = True

    post_config(config)


@task
def dev():
    '''
    Configure tasks for development deployment.
    '''
    env.hosts = ['orchestra.med.harvard.edu']
    config.deploy_env = 'dev'
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
    config.site_url_root = 'http://dev.roundup.hms.harvard.edu'
    config.http_host = 'dev.roundup.hms.harvard.edu'
    config.django_debug = False

    post_config(config)


@task
def prod():
    '''
    Configure tasks for production deployment.
    '''
    env.hosts = ['orchestra.med.harvard.edu']
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
    config.site_url_root = 'http://roundup.hms.harvard.edu'
    config.http_host = 'roundup.hms.harvard.edu'
    config.django_debug = False

    post_config(config)


@task
def ds(dsid):
    '''
    Configure tasks for dataset deployment.

    dsid (string): The id of the dataset.  E.g. '4'.  This is used to derive
    a dataset directory.
    '''
    dsid = os.path.basename(dsid)
    assert dsid

    env.hosts = ['orchestra.med.harvard.edu']
    config.deploy_env = 'dataset'
    config.system_python = '/groups/cbi/bin/python2.7'
    config.site_dir = '/groups/public+cbi/sites/roundup'
    # bogus current_dataset, since not used during dataset computation/loading.
    config.archive_datasets = ['/groups/public+cbi/sites/roundup/datasets/test']
    config.current_dataset = config.archive_datasets[0]
    # associate the code used to compute the dataset with the dataset.
    config.deploy_dir = os.path.join(config.site_dir, 'datasets', dsid, 'code')
    config.mail_service_type = 'orchestra'
    config.blast_bin_dir = '/opt/blast-2.2.24/bin'
    config.kalign_bin_dir = '/home/td23/bin'
    config.no_lsf = False
    config.log_from_addr = 'roundup-noreply@hms.harvard.edu'
    config.site_url_root = 'http://roundup.hms.harvard.edu'
    config.http_host = 'roundup.hms.harvard.edu'
    config.django_debug = False

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
    diabric.venv.install(config.venv, config.requirements)


@task
def venv_freeze():
    require('configured')
    diabric.venv.freeze(config.venv, config.requirements)


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
    # remove app dir and docroot link
    with cd(config.deploy_dir):
        run('rm -rf ' + config.app + ' ' + os.path.join(config.deploy_dir,
                                                        'docroot'))


@task
def init():
    '''
    Make directory for deploying code and configuration, and the link required
    by Phusion Passenger and Apache.
    Make directories for data that persists across deployments like results and
    log files.
    '''
    require('configured')
    # passenger requires that docroot be a link to the webapp's public dir
    site_dirs = [os.path.join(config.site_dir, d) for d in ['datasets', 'log', 'tmp']]
    deploy_dirs = [os.path.join(config.deploy_dir, 'app', 'public')]
    run('mkdir -p -m 2775 ' + ' '.join(site_dirs + deploy_dirs))
    with cd(config.deploy_dir):
        # make link (b/c apache likes docroot and passenger likes app/public).
        run('ln -s app/public docroot')


@task
def conf():
    '''
    Deploy configuration files, files that vary by deployment environment.
    '''
    require('configured')

    # .htaccess specifies where to find passenger_wsgi.py
    upload_template(
        os.path.join(HERE, 'deploy/.htaccess.template'),
        os.path.join(config.app, 'public/.htaccess'),
        context={'app_dir': config.app}, mode=0664)

    # copy secrets files
    put(os.path.join(HERE, 'secrets/{}.py'.format(config.deploy_env)),
        os.path.join(config.app, 'secrets.py'), mode=0660)

    # Create deployenv.py file and upload it
    deployenv = StringIO.StringIO()
    deployenv.write("# Autogenerated file.  Do not modify.\n")
    deployenv.write("# Configuration which varies by environment.\n")
    deployenv.write("\n")
    deployenv.write("ARCHIVE_DATASETS = {!r}\n".format(config.archive_datasets))
    deployenv.write("CURRENT_DATASET = {!r}\n".format(config.current_dataset))
    deployenv.write("MAIL_SERVICE_TYPE = {!r}\n".format(config.mail_service_type))
    deployenv.write("BLAST_BIN_DIR = {!r}\n".format(config.blast_bin_dir))
    deployenv.write("KALIGN_BIN_DIR = {!r}\n".format(config.kalign_bin_dir))
    deployenv.write("NO_LSF = {!r}\n".format(config.no_lsf))
    deployenv.write("LOG_FROM_ADDR = {!r}\n".format(config.log_from_addr))
    deployenv.write("SITE_URL_ROOT = {!r}\n".format(config.site_url_root))
    deployenv.write("HTTP_HOST = {!r}\n".format(config.http_host))
    deployenv.write('# never deploy django in production with DEBUG==True\n')
    deployenv.write('# https://docs.djangoproject.com/en/dev/ref/settings/#debug\n')
    deployenv.write("DJANGO_DEBUG = {!r}\n".format(config.django_debug))
    deployenv.write("SITE_DIR = {!r}\n".format(config.site_dir))
    put(deployenv, os.path.join(config.app, 'deployenv.py'), mode=0664)


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


@task
def all():
    require('configured')
    execute(venv_install)
    execute(clean)
    execute(init)
    execute(conf)
    execute(deploy)
    execute(link_downloads)
    execute(restart)


if __name__ == '__main__':
    main()


# pass

