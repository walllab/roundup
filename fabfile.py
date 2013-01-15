'''
# Usage examples:

Deploy code to development environment on orchestra:

    fab dev deploy

Deploy code to a specific roundup dataset (e.g. 3).  This is useful for
creating an install of roundup for use in computing a large dataset without
depending on other code that might change/break during the time of the 
computation:

    fab ds:3 deploy

Do a clean deployment of code to production:

    fab prod all

Initialize the project directories (e.g. In /groups/cbi/dev.roundup) for local
environment:

    fab local init_deploy_env

Get the virtualenv up and running for a deployment environment:

    fab dev create_venv install_venv

The file allows deployment to remote hosts, assuming key pairs and permissions
are good.
'''


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


def dsdir_config(proj_dir, dsid):
    return os.path.join(proj_dir, 'datasets', dsid)


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
    config.proj_dir = os.path.expanduser('~/sites/local.roundup')
    config.dsdir = dsdir_config(config.proj_dir, 'test_dataset')
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
    config.proj_dir = '/groups/cbi/sites/dev.roundup'
    config.dsdir = dsdir_config(config.proj_dir, 'test_dataset')
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
    config.proj_dir = '/groups/cbi/sites/roundup'
    config.dsdir = dsdir_config(config.proj_dir, '3')
    post_config(config)


@task
def ds(dsid):
    '''
    Configure tasks for dataset deployment.

    dsid (string): The id of the dataset.  E.g. '3'.  This is used to derive
    a dataset directory.
    '''
    env.hosts = ['orchestra.med.harvard.edu']
    config.deploy_env = 'dataset'
    config.system_python = '/groups/cbi/bin/python2.7'
    config.proj_dir = '/groups/cbi/sites/roundup'
    config.dsdir = dsdir_config(config.proj_dir, dsid)
    config.deploy_dir = os.path.join(config.dsdir, 'code')
    post_config(config)


#######
# TASKS

@task
def create_venv():
    require('configured')
    diabric.venv.create(config.venv, config.system_python)


@task
def install_venv():
    require('configured')
    diabric.venv.install(config.venv, config.requirements)


@task
def freeze_venv():
    require('configured')
    diabric.venv.freeze(config.venv, config.requirements)


@task
def remove_venv():
    require('configured')
    diabric.venv.remove(config.venv)


@task
def init_dataset():
    require('configured')
    run('mkdir -p {dsdir}'.format(dsdir=config.dsdir))


@task
def prepare_dataset():
    require('configured')
    with cd(config.app):
        run('{python} roundup/dataset.py prepare_dataset {dsdir}'.format(
            python=config.python, dsdir=config.dsdir))


@task
def init_deploy_env():
    '''
    sets up the directories used to contain code and the project data that persists
    across changes to the codebase, like results and log files.
    this should be called once per deployment environment, not every time code is deployed.
    '''
    require('configured')
    dirs = [os.path.join(config.proj_dir, d) for d in ['datasets', 'log', 'tmp']]
    print dirs
    cmd1 = 'mkdir -p ' + ' '.join(dirs)
    cmd2 = 'mkdir -p ' + config.deploy_dir
    run(cmd1)
    run(cmd2)


@task
def clean():
    '''
    Remove deployed code, dirs and link.  Remake dirs and link.
    '''
    require('configured')
    cmds = ['rm -rf app/* docroot', # clean code dir and link
            'mkdir -p app/public', # make code dir (and dir to link to)
            'ln -s app/public docroot' # make link (b/c apache likes docroot and passenger likes app/public).
            ]
    with cd(config.deploy_dir):
        for cmd in cmds:
            run(cmd)


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
                      '**/*.pyo', '**/.DS_Store', '**/*~', 'html_video_test/']
    rsync_project(
        remote_dir=config.deploy_dir,
        local_dir=os.path.join(HERE, 'app'),
        exclude=deployExcludes,
        delete=True)

    upload_template(
        os.path.join(HERE, 'deploy/.htaccess.template'),
        os.path.join(config.app, 'public/.htaccess'),
        context={'app_dir': config.app}, mode=0664)

    upload_template(
        os.path.join(HERE, 'deploy/passenger_wsgi.template.py'),
        os.path.join(config.app, 'passenger_wsgi.py'),
        context={'python': config.python},
        mode=0664)

    upload_template(
        os.path.join(HERE, 'deploy/generated.template.py'),
        os.path.join(config.app, 'config/generated.py'),
        context={'deploy_env': config.deploy_env,
                 'proj_dir': config.proj_dir,
                 'current_dataset': config.dsdir},
        mode=0664)

    # copy secrets files
    put(os.path.join(HERE, 'deploy/secrets/defaults.py'),
        os.path.join(config.app, 'config/secrets'), mode=0660)
    put(os.path.join(HERE, 'deploy/secrets/{}.py'.format(config.deploy_env)),
        os.path.join(config.app, 'config/secrets/env.py'), mode=0660)
    # copy configution files
    put(os.path.join(HERE, 'deploy/config/defaults.py'),
        os.path.join(config.app, 'config'))
    put(os.path.join(HERE, 'deploy/config/{}.py'.format(config.deploy_env)),
        os.path.join(config.app, 'config/env.py'))
    # upload and fix the shebang for scripts
    diabric.files.upload_shebang(
        os.path.join(HERE, 'app/roundup/dataset.py'),
        os.path.join(config.app, 'roundup/dataset.py'),
        config.python,
        mode=0770)


@task
def restart():
    require('configured')
    # touch passenger restart.txt, so passenger will pick up the changes.
    with cd(config.app):
        run ('touch tmp/restart.txt')


@task
def all():
    require('configured')
    execute(install_venv)
    execute(clean)
    execute(deploy)
    execute(restart)


if __name__ == '__main__':
    main()


# pass

