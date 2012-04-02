'''
Usage examples

Deploy code to development environment on orchestra:

    fab dev deploy

Deploy code to a specific dataset (e.g. 3)

    fab ds:3 deploy
    
Do a clean deployment of code to production

    fab prod all

Initialize the project directories (e.g. In /groups/cbi/dev.roundup) for local environment

    fab init_deploy_env

The file allows deployment to remote hosts, assuming key pairs and permissions are good.
e.g. deploy from laptop to dev.genotator on orchestra.  or to an aws instance.
When deploying to a remote host (e.g. ec2 or orchestra), it is assumed that you can do passwordless authentication.
For example, on orchestra for user td23, I have id_dsa.pub added to ~/.ssh/authorized_keys, and on my laptop I have ~/.ssh/id_dsa
On the ec2-instance for user ec2-user, I have in ~/.ssh/authorized_keys, the cbi-AWS-US-East key.  On my laptop, I added
~/.ssh/cbi-AWS-US-East.pem to the ssh-agent, like so: ssh-add ~/.ssh/cbi-AWS-US-East.pem
'''


import functools
import getpass
import os
import shutil
import subprocess
import sys

import fabric
from fabric.api import env, task, run, cd, lcd, execute
from fabric.api import local as lrun

import fabutil

# set env.run, cd, rsync, and exists
fabutil.setremote()
# the defaults are to deploy remotely to orchestra.
env.hosts = ['orchestra.med.harvard.edu']

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


######################################
# DEPLOYMENT ENVIRONMENT CONFIGURATION
######################################

# true if one of the deployment environment tasks has been run.
env.is_deploy_set = False
env.is_local = False

# deploy_kw is used to fill in templates for .htaccess and config.py
# and set up other values used for deployment
deploy_kw = {
    'deploy_env': '',
    'current_release': '',
    'proj_dir': '',
    'deploy_dir': '',
    'python_exe': '/groups/cbi/virtualenvs/roundup-1.0/bin/python', # works on debian squeeze
    }


def setup_deploy_env(func):
    '''
    decorator used to make sure that at least one deployment enviroment setup task has been called.
    If none has been called, the local() environment will be called.
    '''
    @functools.wraps(func)
    def wrapper(*args, **kws):
        if not env.is_deploy_set:
            execute(local)
        return func(*args, **kws)
    return wrapper


@task
def local():
    '''
    execute this task first to do stuff on the local deployment environment
    '''
    deploy_kw.update({
        'deploy_env': 'local',
        'current_release': 'test_dataset',
        'proj_dir': os.path.expanduser('~/local.roundup'),
        'deploy_dir': os.path.expanduser('~/www/local.roundup.hms.harvard.edu'),
        'python_exe': '/Library/Frameworks/Python.framework/Versions/2.7/bin/python2.7',
        })
    env.is_deploy_set = True
    env.is_local = True
    
    fabutil.setlocal()
    env.hosts = ['localhost']

    
@task
def ds(dsid):
    '''
    dsid: id of the dataset, e.g. '3'
    '''
    deploy_kw.update({
        'deploy_env': 'dataset',
        'current_release': dsid,
        'proj_dir': '/groups/cbi/roundup',
        'deploy_dir': '/groups/cbi/roundup/datasets/{0}/code'.format(dsid),
        'python_exe': '/groups/cbi/virtualenvs/roundup-1.0/bin/python', # works on debian squeeze
        })
    env.is_deploy_set = True

    
@task
def dev():
    '''
    execute this task first to do stuff on dev
    '''
    deploy_kw.update({
        'deploy_env': 'dev',
        'current_release': 'test_dataset',
        'proj_dir': '/groups/cbi/dev.roundup',
        'deploy_dir': '/www/dev.roundup.hms.harvard.edu',
        'python_exe': '/groups/cbi/virtualenvs/roundup-1.0/bin/python', # works on debian squeeze
        })
    env.is_deploy_set = True


@task
def prod():
    '''
    execute this task first to do stuff on prod
    '''
    deploy_kw.update({
        'deploy_env': 'prod',
        'current_release': '3',
        'proj_dir': '/groups/cbi/roundup',
        'deploy_dir': '/www/roundup.hms.harvard.edu',
        'python_exe': '/groups/cbi/virtualenvs/roundup-1.0/bin/python', # works on debian squeeze
        })
    env.is_deploy_set = True


#######
# TASKS
#######

    
@task
@setup_deploy_env
def init_deploy_env():
    '''
    sets up the directories used to contain code and the project data that persists
    across changes to the codebase, like results and log files.
    this should be called once per deployment environment, not every time code is deployed.
    '''
    dirs = [os.path.join(deploy_kw['proj_dir'], d) for d in ['datasets', 'log', 'tmp']]
    print dirs
    cmd1 = 'mkdir -p ' + ' '.join(dirs)
    cmd2 = 'mkdir -p ' + deploy_kw['deploy_dir']
    env.run(cmd1)
    env.run(cmd2)


@task
@setup_deploy_env
def clean():
    '''
    If host is specified, user should also be specified, and vice versa.
    Remove deployed code, dirs and link.  Remake dirs and link.
    '''
    cmds = ['rm -rf webapp/* docroot', # clean code dir and link
            'mkdir -p webapp/public', # make code dir (and dir to link to)
            'ln -s webapp/public docroot' # make link (b/c apache likes docroot and passenger likes webapp/public).
            ]
    with env.cd(deploy_kw['deploy_dir']):
        for cmd in cmds:
            env.run(cmd)


@task
@setup_deploy_env
def deploy():
    '''
    If host is specified, user should also be specified, and vice versa.
    Copy files from src to deployment dir, including renaming one file.
    '''

    deploy_env = deploy_kw['deploy_env']
    deploy_dir = deploy_kw['deploy_dir']

    # instantiate template files with concrete variable values for this
    # deployment environment.
    infile = os.path.join(BASE_DIR, 'deploy/.htaccess.template')
    outfile = os.path.join(BASE_DIR, 'webapp/public/.htaccess')
    fabutil.file_format(infile, outfile, keywords={'deploy_dir': deploy_dir})
    
    infile = os.path.join(BASE_DIR, 'deploy/passenger_wsgi.py.template')
    outfile = os.path.join(BASE_DIR, 'webapp/passenger_wsgi.py')
    fabutil.file_format(infile, outfile, 
            keywords={'python_exe': deploy_kw['python_exe']})

    infile = os.path.join(BASE_DIR, 'deploy/generated.py.template')
    outfile = os.path.join(BASE_DIR, 'webapp/config/generated.py')
    fabutil.file_format(infile, outfile, 
            keywords={'deploy_env': deploy_env,
                      'proj_dir': deploy_kw['proj_dir'],
                      'current_release': deploy_kw['current_release']})

    # copy secrets files
    srcfile = os.path.join(BASE_DIR, 'deploy/secrets/defaults.py')
    dest = os.path.join(BASE_DIR, 'webapp/config/secrets')
    shutil.copy2(srcfile, dest)
    srcfile = os.path.join(BASE_DIR, 'deploy/secrets/{}.py'.format(deploy_env))
    dest = os.path.join(BASE_DIR, 'webapp/config/secrets/env.py')
    shutil.copy2(srcfile, dest)

    # copy configution files
    srcfile = os.path.join(BASE_DIR, 'deploy/config/defaults.py')
    dest = os.path.join(BASE_DIR, 'webapp/config')
    shutil.copy2(srcfile, dest)
    srcfile = os.path.join(BASE_DIR, 'deploy/config/{}.py'.format(deploy_env))
    dest = os.path.join(BASE_DIR, 'webapp/config/env.py')
    shutil.copy2(srcfile, dest)

    # copy files to remote destintation, excluding backups, .svn dirs, etc.
    # do not deploy these files/dirs.
    deployExcludes = ['**/old', '**/old/**', '**/semantic.cache', '**/.svn', '**/.svn/**', '**/*.pyc',
                      '**/*.pyo', '**/.DS_Store', '**/*~', 'html_video_test/']
    filterArgs = []
    for e in deployExcludes:
        filterArgs += ['-f', '- {}'.format(e)]
    options = ['--delete', '-avz'] + filterArgs
    env.rsync(options, src='webapp', dest=deploy_dir, cwd=BASE_DIR, user=env.user, host=env.host)

    # touch passenger restart.txt, so passenger will pick up the changes.
    with env.cd(deploy_dir):
        env.run ('touch webapp/tmp/restart.txt')

    
@task
@setup_deploy_env
def all():
    execute(clean)
    execute(deploy)


if __name__ == '__main__':
    main()


# pass

