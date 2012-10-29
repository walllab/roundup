'''
Usage examples

Deploy code to development environment on orchestra:

    fab -R dev deploy

Deploy code to a specific roundup dataset (e.g. 3)

    fab -R dataset --set dsdir=/groups/cbi/roundup/dataset/3 deploy
   
Deploy code to a dataset directory 
e.g. /groups/cbi/roundup/quest_for_orthologs/2012_04

    fab dsdir:/groups/cbi/roundup/quest_for_orthologs/2012_04 deploy

Do a clean deployment of code to production

    fab -R prod all

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
from fabric.api import env, task, run, cd, lcd, execute, put

import diabric.venv
import diabric.pyapp
import diabric.config
import diabric.files


HERE = os.path.abspath(os.path.dirname(__file__))

# location of a pip requirements.txt file.
# used to persist package volumes or recreate a virtual environment.
REQUIREMENTS_PATH = os.path.join(HERE, 'requirements.txt')


####################
# ROLE CONFUGURATION

env.roledefs = {
    'prod': ['orchestra.med.harvard.edu'],
    'local': ['localhost'],
    'dev': ['orchestra.med.harvard.edu'],
    'dataset': ['orchestra.med.harvard.edu'],
}

# default role
if not env.roles and not env.hosts:
    env.roles = ['local']


######################################
# DEPLOYMENT ENVIRONMENT CONFIGURATION

# role configuration.
config = diabric.config.ContextConfig(diabric.config.role_context)
# config = collections.defaultdict(AttrDict)

config['local']['system_python'] = '/usr/local/bin/python'
config['local']['deploy_dir'] = os.path.expanduser('~/www/local.roundup.hms.harvard.edu')
config['local']['deploy_env'] = 'local'
config['local']['current_release'] = 'test_dataset'
config['local']['proj_dir'] = os.path.expanduser('~/local.roundup')

config['dev']['system_python'] = '/groups/cbi/bin/python2.7'
config['dev']['deploy_dir'] = '/www/dev.roundup.hms.harvard.edu'
config['dev']['deploy_env'] = 'dev'
config['dev']['current_release'] = 'test_dataset'
config['dev']['proj_dir'] = '/groups/cbi/dev.roundup'

config['prod']['system_python'] = '/groups/cbi/bin/python2.7'
config['prod']['deploy_dir'] = '/www/roundup.hms.harvard.edu'
config['prod']['deploy_env'] = 'prod'
config['prod']['current_release'] = '3'
config['prod']['proj_dir'] = '/groups/cbi/roundup'

if 'dataset' in env.roles:
    # dataset role must have a deployment dir.
    if not env.get('dsdir'):
        raise Exception('if role=dataset, env.dsdir must be set, e.g. by --set dsdir=PATH_TO_DS')

    config['dataset']['system_python'] = '/groups/cbi/bin/python2.7'
    config['dataset']['deploy_dir'] = env.dsdir
    config['dataset']['deploy_env'] = 'dataset'
    config['dataset']['current_release'] = os.path.basename(env.dsdir)
    config['dataset']['proj_dir'] = '/groups/cbi/roundup'

for c in config.values():
    app = diabric.pyapp.App(c['deploy_dir'])
    c['venv'] = app.venvdir()
    c['log'] = app.logdir()
    c['conf'] = app.confdir()
    c['bin'] = app.bindir()
    c['app'] = app.appdir()
    c['python_exe'] = os.path.join(c['venv'], 'bin', 'python')



#######
# TASKS


@task
def create_venv():
    '''
    Create a virtual environment in the deployment location using
    requirements.txt
    '''
    diabric.venv.create(config()['venv'], python=config()['system_python'])


@task
def install_venv():
    diabric.venv.install(config()['venv'], REQUIREMENTS_PATH)


@task
def remove_venv():
    diabric.venv.remove(config()['venv'])


@task
def init_deploy_env():
    '''
    sets up the directories used to contain code and the project data that persists
    across changes to the codebase, like results and log files.
    this should be called once per deployment environment, not every time code is deployed.
    '''
    dirs = [os.path.join(config()['proj_dir'], d) for d in ['datasets', 'log', 'tmp']]
    print dirs
    cmd1 = 'mkdir -p ' + ' '.join(dirs)
    cmd2 = 'mkdir -p ' + config()['deploy_dir']
    run(cmd1)
    run(cmd2)


@task
def clean():
    '''
    If host is specified, user should also be specified, and vice versa.
    Remove deployed code, dirs and link.  Remake dirs and link.
    '''
    cmds = ['rm -rf webapp/* docroot', # clean code dir and link
            'mkdir -p webapp/public', # make code dir (and dir to link to)
            'ln -s webapp/public docroot' # make link (b/c apache likes docroot and passenger likes webapp/public).
            ]
    with cd(config()['deploy_dir']):
        for cmd in cmds:
            run(cmd)


@task
def deploy():
    '''
    If host is specified, user should also be specified, and vice versa.
    Copy files from src to deployment dir, including renaming one file.
    '''

    deploy_env = config()['deploy_env']
    deploy_dir = config()['deploy_dir']

    # copy files to remote destintation, excluding backups, .svn dirs, etc.
    # do not deploy these files/dirs.
    deployExcludes = ['**/old', '**/old/**', '**/semantic.cache', '**/.svn', '**/.svn/**', '**/*.pyc',
                      '**/*.pyo', '**/.DS_Store', '**/*~', 'html_video_test/']
    filterArgs = []
    for e in deployExcludes:
        filterArgs += ['-f', '- {}'.format(e)]
    options = ['--delete', '-avz'] + filterArgs
    diabric.files.rsync(options, src='webapp', dest=deploy_dir, cwd=HERE, user=env.user, host=env.host)

    # instantiate template files with concrete variable values for this
    # deployment environment.
    # infile = os.path.join(HERE, 'deploy/.htaccess.template')
    # outfile = os.path.join(HERE, 'webapp/public/.htaccess')
    # diabric.files.file_format(infile, outfile, kws={'deploy_dir': deploy_dir})

    infile = os.path.join(HERE, 'deploy/.htaccess.template')
    outfile = os.path.join(deploy_dir, 'webapp/public/.htaccess')
    diabric.files.upload_format(infile, outfile,
                                kws={'deploy_dir': deploy_dir})

    infile = os.path.join(HERE, 'deploy/passenger_wsgi.py.template')
    outfile = os.path.join(deploy_dir, 'webapp/passenger_wsgi.py')
    diabric.files.upload_format(infile, outfile, 
            kws={'python_exe': config()['python_exe']})

    infile = os.path.join(HERE, 'deploy/generated.py.template')
    outfile = os.path.join(deploy_dir, 'webapp/config/generated.py')
    diabric.files.upload_format(infile, outfile, 
            kws={'deploy_env': deploy_env, 'proj_dir': config()['proj_dir'],
                 'current_release': config()['current_release']})

    # copy secrets files
    srcfile = os.path.join(HERE, 'deploy/secrets/defaults.py')
    dest = os.path.join(deploy_dir, 'webapp/config/secrets')
    put(srcfile, dest)
    srcfile = os.path.join(HERE, 'deploy/secrets/{}.py'.format(deploy_env))
    dest = os.path.join(deploy_dir, 'webapp/config/secrets/env.py')
    put(srcfile, dest)

    # copy configution files
    srcfile = os.path.join(HERE, 'deploy/config/defaults.py')
    dest = os.path.join(deploy_dir, 'webapp/config')
    put(srcfile, dest)
    srcfile = os.path.join(HERE, 'deploy/config/{}.py'.format(deploy_env))
    dest = os.path.join(deploy_dir, 'webapp/config/env.py')
    put(srcfile, dest)

    # upload and fix the shebang for scripts
    diabric.files.upload_shebang(
        os.path.join(HERE, 'webapp/roundup/dataset.py'),
        os.path.join(config()['deploy_dir'], 'webapp/roundup/dataset.py'),
        config()['python_exe'],
        mode=0770)


@task
def run_app():
    # touch passenger restart.txt, so passenger will pick up the changes.
    with cd(config()['deploy_dir']):
        run ('touch webapp/tmp/restart.txt')


@task
def all():
    execute(clean)
    execute(deploy)
    execute(run_app)


if __name__ == '__main__':
    main()


# pass

