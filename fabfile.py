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

import fabvenv


HERE = os.path.abspath(os.path.dirname(__file__))
# deploy envs options
DEPLOY_OPTS = ['local', 'dev', 'prod', 'dataset']


def write_attr(fh, ns, attr, default=None, upper=False):
    value = getattr(ns, attr) if hasattr(ns, attr) else default
    name = attr if not upper else attr.upper()
    fh.write('{name} = {value!r}\n'.format(name=name, value=value))



###############
# CONFIGURATION


# 'config' is an alterantive to fabric.api.env, which does not risk having
# application configuration conflict with fabric internals, like 'port'.
class Namespace(object):
    ''' An iterable attribute namespace '''
    def __iter__(self):
        return iter(self.__dict__)

config = Namespace()


def post_config(config):
    '''
    Called by one of the deployment environment configuration tasks: dev, prod,
    etc.  Sets some values in `config`.
    '''
    config.log = os.path.join(config.deploy_dir, 'log')
    config.tmp = os.path.join(config.deploy_dir, 'tmp')
    config.venv = os.path.join(config.deploy_dir, 'venv')
    config.app = os.path.join(config.deploy_dir, 'app')
    config.code = config.app
    config.requirements = os.path.join(HERE, 'requirements.txt')
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
    config.archive_datasets = [os.path.expanduser('~/sites/local.roundup/datasets/test_dataset')]
    config.current_dataset = config.archive_datasets[0]
    config.mail_service_type = 'amazon_ses'
    config.blast_bin_dir = '/usr/local/bin'
    config.kalign_bin_dir = '/usr/local/bin'
    config.no_lsf = True
    config.log_from_addr = 'todddeluca@yahoo.com'
    config.django_debug = True
    config.use_mycnf = False
    config.maintenance = False
    config.maintenance_message = ''

    post_config(config)


@task
def dev():
    '''
    Configure tasks for development deployment.
    '''
    env.hosts = ['orchestra.med.harvard.edu']
    env.user = os.environ.get('ROUNDUP_DEPLOY_USER') or os.environ['USER']
    config.deploy_env = 'dev'
    config.website = True
    # config.system_python = '/groups/cbi/bin/python2.7'
    config.system_python = '/home/td23/bin/python2.7'
    config.deploy_dir = '/www/dev.roundup.hms.harvard.edu'
    config.archive_datasets = ['/groups/public+cbi/sites/roundup/datasets/4',
                               '/groups/public+cbi/sites/roundup/datasets/3',
                               '/groups/public+cbi/sites/roundup/datasets/2',
                               '/groups/public+cbi/sites/roundup/datasets/qfo_2013_04',
                               '/groups/public+cbi/sites/roundup/datasets/qfo_2011_04']
    config.current_dataset = config.archive_datasets[0]
    config.mail_service_type = 'orchestra'
    config.blast_bin_dir = '/opt/blast-2.2.24/bin'
    config.kalign_bin_dir = '/home/td23/bin'
    config.no_lsf = False
    config.log_from_addr = 'roundup-noreply@hms.harvard.edu'
    config.django_debug = False
    config.use_mycnf = False
    config.maintenance = False
    config.maintenance_message = ''

    post_config(config)


@task
def prod():
    '''
    Configure tasks for production deployment.
    '''
    env.hosts = ['orchestra.med.harvard.edu']
    env.user = os.environ.get('ROUNDUP_DEPLOY_USER') or os.environ['USER']
    config.website = True
    config.deploy_env = 'prod'
    config.system_python = '/home/td23/bin/python2.7'
    config.deploy_dir = '/www/roundup.hms.harvard.edu'
    config.archive_datasets = ['/groups/public+cbi/sites/roundup/datasets/4',
                               '/groups/public+cbi/sites/roundup/datasets/3',
                               '/groups/public+cbi/sites/roundup/datasets/2',
                               '/groups/public+cbi/sites/roundup/datasets/qfo_2013_04',
                               '/groups/public+cbi/sites/roundup/datasets/qfo_2011_04']
    config.current_dataset = config.archive_datasets[0]
    config.mail_service_type = 'orchestra'
    config.blast_bin_dir = '/opt/blast-2.2.24/bin'
    config.kalign_bin_dir = '/home/td23/bin'
    config.no_lsf = True
    config.log_from_addr = 'roundup-noreply@hms.harvard.edu'
    config.django_debug = False
    config.use_mycnf = False
    config.maintenance = False
    config.maintenance_message = '''Roundup is currently experiencing technical
    difficulties.  Thank you for your patience while the site is
    unavailable.'''
    # config.maintenance_message = '''Roundup is currently undergoing
    # maintenance.  Thank you for your patience while the site is
    # unavailable.'''
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
    config.system_python = '/home/td23/bin/python2.7'
    config.deploy_dir = '/groups/public+cbi/sites/roundup/code/{}'.format(dsid)
    config.mail_service_type = 'orchestra'
    config.blast_bin_dir = '/opt/blast-2.2.24/bin'
    config.kalign_bin_dir = '/home/td23/bin'
    config.log_from_addr = 'roundup-noreply@hms.harvard.edu'
    # Default to using mysql username and password from ~/.my.cnf because
    # orchestra dev/prod roundup db user does not have create table privileges.
    config.use_mycnf = True

    post_config(config)


############
# VENV TASKS

@task
def venv_create():
    require('configured')
    venv = fabvenv.Venv(config.venv, config.requirements)
    if not venv.exists():
        venv.create(config.system_python)


@task
def venv_install():
    require('configured')
    fabvenv.Venv(config.venv, config.requirements).install()


@task
def venv_upgrade():
    require('configured')
    fabvenv.Venv(config.venv, config.requirements).upgrade()


@task
def venv_freeze():
    require('configured')
    fabvenv.Venv(config.venv, config.requirements).freeze()


@task
def venv_remove():
    require('configured')
    venv = fabvenv.Venv(config.venv, config.requirements)
    if venv.exists():
        venv.remove()


@task
def venv_pth():
    '''
    Add the code directory to the virtualenv sys.path.
    '''
    require('configured')
    fabvenv.Venv(config.venv, config.requirements).venv_pth([config.code])


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
    for attr in ['mail_service_type', 'blast_bin_dir', 'kalign_bin_dir',
                 'log_from_addr', 'use_mycnf']:
        write_attr(text, config, attr, upper=True)
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
        text.write('# Autogenerated file.  Do not modify.\n')
        text.write('# Web-specific configuration which varies by environment.\n')
        text.write('\n')
        text.write('# never deploy django in production with DEBUG==True\n')
        text.write('# https://docs.djangoproject.com/en/dev/ref/settings/#debug\n')
        for attr in ['django_debug', 'archive_datasets', 'current_dataset',
                     'no_lsf']:
            write_attr(text, config, attr, upper=True)
        for attr in ['maintenance', 'maintenance_message']:
            write_attr(text, config, attr)
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
    execute(venv_pth)
    execute(clean)
    execute(init)
    execute(conf)
    execute(deploy)
    
    if config.website:
        execute(link_downloads)
        execute(restart)

