#!/usr/bin/python

# usage: python build.py
# usage: python build.py [--deployenv=ec2_dev] [deploy]

# This file uses python, ssh, and rsync to replace ant/build.xml and to allow deployment to remote hosts and remove dependency on ant.
# allow deployment to remote hosts, assuming key pairs and perms are good.
#   e.g. deploy from laptop to dev.genotator on orchestra.  or to aws instance.
# poor man's Fabric deployment.

# When deploying to a remote host (e.g. ec2 or orchestra), it is assumed that you can do passwordless authentication.
#   For example, on orchestra for user td23, I have id_dsa.pub added to ~/.ssh/authorized_keys, and on my laptop I have ~/.ssh/id_dsa
#   On the ec2-instance for user ec2-user, I have in ~/.ssh/authorized_keys, the cbi-AWS-US-East key.  On my laptop, I added
#   ~/.ssh/cbi-AWS-US-East.pem to the ssh-agent, like so: ssh-add ~/.ssh/cbi-AWS-US-East.pem


import os
import subprocess
import sys
import getpass
import glob
import argparse


def main():
    '''
    Used to compile and deploy code to dev or prod, or to initialize a project (rare).
    The default target, all, builds/compiles the java code and does a clean deployment, if needed.
    The default deployEnv, local, does not deploy code, since the code is run from the src dir.
    Deployment for Genotator to /www/(dev.)genotator.hms.harvard.edu 
    '''
    # usage: python build.py [--deployenv=<deployment environment>] [target]
    # target: choose from: all, deploy, init, build.
    parser = argparse.ArgumentParser(description='Genotator webapp deployment/build script.')
    parser.add_argument('--deployenv', default='local', choices=('local', 'orch_dev', 'orch_prod'), help='deploy to this host/environment')
    parser.add_argument('target', default='all', nargs='?', choices=('init', 'build', 'deploy', 'all', 'init_project'))
    args = parser.parse_args()
    print args
    
    baseDir = '.'
    user = None
    host = None
    deployEnv = args.deployenv
    target = args.target
    
    # set up variables for targets
    user = user if user else getpass.getuser()    
    homeDir = os.path.expanduser('~')
    if deployEnv == 'local':
        deployRoot = os.path.join(homeDir, 'www/dev.roundup.hms.harvard.edu')
        projectRoot = os.path.join(homeDir, 'dev.roundup')
        host = None
    elif deployEnv == 'orch_dev':
        deployRoot = '/www/dev.roundup.hms.harvard.edu'
        projectRoot = '/groups/cbi/dev.roundup'
        host = host if host else 'orchestra.med.harvard.edu'
    elif deployEnv == 'orch_prod':
        deployRoot = '/www/roundup.hms.harvard.edu'
        projectRoot = '/groups/cbi/roundup'
        host = host if host else 'orchestra.med.harvard.edu'
    else:
        raise Exception('Unrecognized deployEnv={}'.format(deployEnv))

    # run targets.  Skip some targets for local deployEnv, which runs from the src dir.
    if target == 'init_project':
        initProject(projectRoot, user, host)
    if deployEnv != 'local': 
        if target in ('init', 'all'):
            init(deployRoot, projectRoot, user, host)
        if target in ('deploy', 'all'):
            deploy(baseDir, deployRoot, deployEnv, projectRoot, user, host)
            

def remote_check_call(args, user=None, host=None, **kw):
    prefix = []
    if host:
        prefix = ['ssh']
        if user:
            prefix += ['-l', user]
        prefix.append(host)
    print prefix + args
    return subprocess.check_call(prefix + args, **kw)


def remote_rsync(options, src, dest, user=None, host=None, **kw):
    # if remote user and host specified, copy there instead of locally.
    if user and host:
        destStr = '{}@{}:{}'.format(user, host, dest)
    else:
        destStr = dest

    args = ['rsync'] + options + [src, destStr]
    print args
    subprocess.check_call(args)
    

def initProject(projectRoot, user=None, host=None, **kw):
    '''
    a project contains the data that persists across changes to the codebase.  Like results and log files.
    this should be called once, not every time code is deployed.
    '''
    print 'initProject: projectRoot={}, user={}, host={}'.format(projectRoot, user, host)
    dirs = 'compute datasets  genomes  log  python  results  tmp'.split()
    for d in dirs:
        remote_check_call(['mkdir', '-p', os.path.join(projectRoot, d)], user=user, host=host)

    
def init(deployRoot, projectRoot, user=None, host=None, **kw):
    '''
    If host is specified, user should also be specified, and vice versa.
    Remove deployed code, dirs and link.  Remake dirs and link.
    '''
    print 'init: deployRoot={}, user={}, host={}'.format(deployRoot, user, host)
    # clean code dir
    args = ['rm', '-rf', os.path.join(deployRoot, 'webapp')]
    remote_check_call(args, user=user, host=host)
    # clean link
    args = ['rm', '-rf', os.path.join(deployRoot, 'docroot')]
    remote_check_call(args, user=user, host=host)
    # create code dir
    args = ['mkdir', '-p', os.path.join(deployRoot, 'webapp/public')]
    remote_check_call(args, user=user, host=host)
    # create link
    args = ['ln', '-s', os.path.join(deployRoot, 'webapp/public'), os.path.join(deployRoot, 'docroot')]
    remote_check_call(args, user=user, host=host)
    

def deploy(baseDir, deployRoot, deployEnv, projectRoot, user=None, host=None, **kw):
    '''
    If host is specified, user should also be specified, and vice versa.
    Copy files from src to deployment dir, including renaming one file.
    '''
    print 'deploy: baseDir={}, deployRoot={}, deployEnv={}, user={}, host={}'.format(baseDir, deployRoot, deployEnv, user, host)
    # do not deploy these files/dirs.
    deployExcludes = ['**/old', '**/old/**', '**/semantic.cache', '**/.svn', '**/.svn/**', '**/*.pyc', '**/*.pyo', '**/.DS_Store', '**/*~']
    filterArgs = []
    for e in deployExcludes:
        filterArgs += ['-f', '- {}'.format(e)]
    options = ['--delete', '-avz'] + filterArgs

    # copy files to remote destintation, excluding backups, .svn dirs, etc.
    remote_rsync(options, src=os.path.join(baseDir, 'webapp'), dest=deployRoot, user=user, host=host)

    # rename the deployment specific .htacccess file
    args = ['cp', '-p', os.path.join(deployRoot, 'webapp/public/.htaccess.{}'.format(deployEnv)), os.path.join(deployRoot, 'webapp/public/.htaccess')]
    remote_check_call(args, user=user, host=host)

    # rename the deployment specific deploy_env.py file
    args = ['cp', '-p', os.path.join(deployRoot, 'webapp/deploy_env.py.{}'.format(deployEnv)), os.path.join(deployRoot, 'webapp/deploy_env.py')]
    remote_check_call(args, user=user, host=host)

    
if __name__ == '__main__':
    main()


# pass

