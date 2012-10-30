'''
# Usage examples:

Deploy code to development environment on orchestra:

    fab --set de=dev deploy

Deploy code to a specific roundup dataset (e.g. 3).  This is useful for
creating an install of roundup for use in computing a large dataset without
depending on other code that might change/break during the time of the 
computation:

    fab --set de=dataset,dsdir=/groups/cbi/roundup/dataset/3 deploy

Do a clean deployment of code to production:

    fab --set de=prod all

Initialize the project directories (e.g. In /groups/cbi/dev.roundup) for local
environment:

    fab --set de=local init_deploy_env

Get the virtualenv up and running for a deployment environment:

    fab --set de=dev create_venv install_venv

The file allows deployment to remote hosts, assuming key pairs and permissions
are good.
'''


import os
import sys

from fabric.api import env, task, run, cd, lcd, execute, put
from fabric.contrib.files import upload_template
from fabric.contrib.project import rsync_project

import diabric.venv
import diabric.pyapp
import diabric.config
import diabric.files


HERE = os.path.abspath(os.path.dirname(__file__))
# deploy envs options
DEPLOY_OPTS = ['local', 'dev', 'prod', 'dataset']


def configure():
    '''
    There are a lot of configuration values that the tasks in this fabfile use.
    This function sets those values according to the deployment environment 
    specified on the `fab` command line.

    The configuration is placed in a diabric.config.Namespace object, which is
    also the return value.
    '''
    config = diabric.config.Namespace()

    # location of a pip requirements.txt file.
    # used to persist package volumes or recreate a virtual environment.
    config.requirements = os.path.join(HERE, 'requirements.txt')
    config.db_prefix = 'ROUNDUP'
    # get deployment enviroment flag
    config.deploy_env = env.get('de', 'local')
    if config.deploy_env not in DEPLOY_OPTS:
        raise Exception('Unrecognized deployment configuration flag: {}'.format(config.deploy_env))

    if 'local' == config.deploy_env:
        env.hosts = ['localhost']
        config.system_python = '/usr/local/bin/python'
        config.deploy_dir = os.path.expanduser('~/www/local.roundup.hms.harvard.edu')
        config.current_release = 'test_dataset'
        config.proj_dir = os.path.expanduser('~/local.roundup')
    elif 'dev' == config.deploy_env:
        env.hosts = ['orchestra.med.harvard.edu']
        config.system_python = '/groups/cbi/bin/python2.7'
        config.deploy_dir = '/www/dev.roundup.hms.harvard.edu'
        config.current_release = 'test_dataset'
        config.proj_dir = '/groups/cbi/dev.roundup'
    elif 'prod' == config.deploy_env:
        env.hosts = ['orchestra.med.harvard.edu']
        config.system_python = '/groups/cbi/bin/python2.7'
        config.deploy_dir = '/www/roundup.hms.harvard.edu'
        config.current_release = '3'
        config.proj_dir = '/groups/cbi/roundup'
    elif 'dataset' == config.deploy_env:
        # get the dataset dir (where the dataset will be deployed.
        if not env.get('dsdir'):
            raise Exception('For dataset deployment environments, env.dsdir must be set, e.g. by --set dsdir=PATH_TO_DS')
        env.hosts = ['orchestra.med.harvard.edu']
        config.system_python = '/groups/cbi/bin/python2.7'
        config.deploy_dir = env.dsdir
        config.current_release = os.path.basename(env.dsdir)
        config.proj_dir = '/groups/cbi/roundup'

    app = diabric.pyapp.App(config.deploy_dir)
    config.venv = app.venvdir()
    config.log = app.logdir()
    config.conf = app.confdir()
    config.bin = app.bindir()
    config.app = app.appdir()
    config.python_exe = os.path.join(config.venv, 'bin', 'python')

    return config

config = configure()



#######
# TASKS

create_venv = diabric.venv.CreateVenv(config.venv, config.system_python)
install_venv = diabric.venv.InstallVenv(config.venv, config.requirements)
remove_venv = diabric.venv.RemoveVenv(config.venv)
freeze_venv = diabric.venv.FreezeVenv(config.venv, config.requirements)


@task
def init_deploy_env():
    '''
    sets up the directories used to contain code and the project data that persists
    across changes to the codebase, like results and log files.
    this should be called once per deployment environment, not every time code is deployed.
    '''
    dirs = [os.path.join(config.proj_dir, d) for d in ['datasets', 'log', 'tmp']]
    print dirs
    cmd1 = 'mkdir -p ' + ' '.join(dirs)
    cmd2 = 'mkdir -p ' + config.deploy_dir
    run(cmd1)
    run(cmd2)


@task
def clean():
    '''
    If host is specified, user should also be specified, and vice versa.
    Remove deployed code, dirs and link.  Remake dirs and link.
    '''
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
        context={'python_exe': config.python_exe,
                 'db_prefix': config.db_prefix},
        mode=0664)

    upload_template(
        os.path.join(HERE, 'deploy/generated.template.py'),
        os.path.join(config.app, 'config/generated.py'),
        context={'deploy_env': config.deploy_env,
                 'proj_dir': config.proj_dir,
                 'current_release': config.current_release},
        mode=0664)

    # copy secrets files
    put(os.path.join(HERE, 'deploy/secrets/defaults.py'),
        os.path.join(config.app, 'config/secrets'))
    put(os.path.join(HERE, 'deploy/secrets/{}.py'.format(config.deploy_env)),
        os.path.join(config.app, 'config/secrets/env.py'))
    # copy configution files
    put(os.path.join(HERE, 'deploy/config/defaults.py'),
        os.path.join(config.app, 'config'))
    put(os.path.join(HERE, 'deploy/config/{}.py'.format(config.deploy_env)),
        os.path.join(config.app, 'config/env.py'))
    # upload and fix the shebang for scripts
    diabric.files.upload_shebang(
        os.path.join(HERE, 'app/roundup/dataset.py'),
        os.path.join(config.app, 'roundup/dataset.py'),
        config.python_exe,
        mode=0770)


@task
def restart():
    # touch passenger restart.txt, so passenger will pick up the changes.
    with cd(config.app):
        run ('touch tmp/restart.txt')


@task
def all():
    execute(install_venv)
    execute(clean)
    execute(deploy)
    execute(restart)


if __name__ == '__main__':
    main()


# pass

