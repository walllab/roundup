'''
Usage examples

Deploy code to development environment on orchestra:

    fab dev deploy

Do a clean deployment of code to production

    fab prod all

Initialize the project directories (e.g. In /groups/cbi/dev.roundup) for local environment

    fab initProject

The file allows deployment to remote hosts, assuming key pairs and permissions are good.
e.g. deploy from laptop to dev.genotator on orchestra.  or to an aws instance.
When deploying to a remote host (e.g. ec2 or orchestra), it is assumed that you can do passwordless authentication.
For example, on orchestra for user td23, I have id_dsa.pub added to ~/.ssh/authorized_keys, and on my laptop I have ~/.ssh/id_dsa
On the ec2-instance for user ec2-user, I have in ~/.ssh/authorized_keys, the cbi-AWS-US-East key.  On my laptop, I added
~/.ssh/cbi-AWS-US-East.pem to the ssh-agent, like so: ssh-add ~/.ssh/cbi-AWS-US-East.pem
'''


import os
import subprocess
import sys
import getpass
import glob
import argparse

from fabric.api import env, task, run, cd, local, lcd, execute

# the only remote host we use right now is roundup
env.hosts = ['orchestra.med.harvard.edu']

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
HOME_DIR = os.path.expanduser('~')
deploy_env_kw = {
    'local': {'deployRoot': os.path.join(HOME_DIR, 'www/dev.roundup.hms.harvard.edu'),
              'projectRoot': os.path.join(HOME_DIR, 'local.roundup'), },
    'ds3': {'deployRoot': '/groups/cbi/roundup/datasets/3/code',
            'projectRoot': '/groups/cbi/roundup', },
    'dev': {'deployRoot': '/www/dev.roundup.hms.harvard.edu',
            'projectRoot': '/groups/cbi/dev.roundup', },
    'prod': {'deployRoot': '/www/roundup.hms.harvard.edu',
            'projectRoot': '/groups/cbi/roundup', },
    }
DEPLOY_ENV = 'local'


#######
# TASKS
#######

@task
def ds3():
    '''
    execute this task first to do stuff on dev
    '''
    global DEPLOY_ENV
    DEPLOY_ENV = 'ds3'

    
@task
def dev():
    '''
    execute this task first to do stuff on dev
    '''
    global DEPLOY_ENV
    DEPLOY_ENV = 'dev'

    
@task
def prod():
    '''
    execute this task first to do stuff on prod
    '''
    global DEPLOY_ENV
    DEPLOY_ENV = 'prod'

    
@task
def initProject():
    '''
    a project contains the data that persists across changes to the codebase.  Like results and log files.
    this should be called once, not every time code is deployed.
    '''
    cmd = 'mkdir -p datasets log tmp'
    if DEPLOY_ENV == 'local':
        with lcd(deploy_env_kw[DEPLOY_ENV]['projectRoot']):
            local(cmd)
    else:
        with cd(deploy_env_kw[DEPLOY_ENV]['projectRoot']):
            run(cmd)


@task
def clean():
    '''
    If host is specified, user should also be specified, and vice versa.
    Remove deployed code, dirs and link.  Remake dirs and link.
    '''
    if DEPLOY_ENV == 'local':
        return

    with cd(deploy_env_kw[DEPLOY_ENV]['deployRoot']):
        # clean code dir and link
        run('rm -rf webapp/* docroot')
        # make code dir (and dir to link to)
        run('mkdir -p webapp/public')
        # make link (b/c apache likes docroot and passenger likes webapp/public).
        run('ln -s webapp/public docroot')


@task
def deploy():
    '''
    If host is specified, user should also be specified, and vice versa.
    Copy files from src to deployment dir, including renaming one file.
    '''
    if DEPLOY_ENV == 'local':
        return

    deployRoot = deploy_env_kw[DEPLOY_ENV]['deployRoot']

    # copy files to remote destintation, excluding backups, .svn dirs, etc.
    # do not deploy these files/dirs.
    deployExcludes = ['**/old', '**/old/**', '**/semantic.cache', '**/.svn', '**/.svn/**', '**/*.pyc',
                      '**/*.pyo', '**/.DS_Store', '**/*~', 'html_video_test/']
    filterArgs = []
    for e in deployExcludes:
        filterArgs += ['-f', '- {}'.format(e)]
    options = ['--delete', '-avz'] + filterArgs
    rsync(options, src='webapp', dest=deployRoot, cwd=BASE_DIR, user=env.user, host=env.host)

    with cd(deployRoot):
        # rename the deployment specific .htacccess file
        run('cp -p webapp/public/.htaccess.{} webapp/public/.htaccess'.format(DEPLOY_ENV))
        # rename the deployment specific deploy_env.py file
        run('cp -p webapp/deploy_env.{}.py webapp/deploy_env.py'.format(DEPLOY_ENV))
        # tell passenger to restart
        run ('touch webapp/tmp/restart.txt')

    
@task
def all():
    execute(clean)
    execute(deploy)


#################
# OTHER FUNCTIONS
#################


def rsync(options, src, dest, user=None, host=None, cwd=None):
    '''
    options: list of rsync options, e.g. ['--delete', '-avz']
    src: source directory (or files).  Note: rsync behavior varies depending on whether or not src dir ends in '/'.
    dest: destination directory.
    cwd: change (using subprocess) to cwd before running rsync.
    This is a helper function for running rsync locally, via subprocess.  Note: shell=False.
    '''
    # if remote user and host specified, copy there instead of locally.
    if user and host:
        destStr = '{}@{}:{}'.format(user, host, dest)
    else:
        destStr = dest

    args = ['rsync'] + options + [src, destStr]
    print args
    subprocess.check_call(args, cwd=cwd)
    

if __name__ == '__main__':
    main()


# pass

