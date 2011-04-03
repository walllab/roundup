#!/usr/bin/env python

import subprocess

def run(args, stdin=None, shell=True):
    '''
    args: commandline string treated as a one element list, or list containing command and arguments.
    stdin: string to be sent to stdin of command.

    Basically, if you want to run a command line, pass it as a string via args, and let shell=True.
    e.g. 'ls databases/fasta'
    If you do not want shell interpretation, break up the commandline and args into a list and let shell=False.
    e.g. ['ls', 'databases/fasta']
    Runs command, sending stdin to command (if any is given).  If shell=True, executes command through shell,
    interpreting shell characters in command and arguments.  If args is a string, runs args like a command line run
    on the shell.  If shell=False, executes command (the first item in args) with the other items in args as arguments.
    If args is a string, it is executed as a command.  If the string includes arguments, strange behavior will ensue.
    This is a convenience function wrapped around the subprocess module.

    Returns stdout of cmd (as string) 
    Throws an Exception with returncode and stderr of cmd attached as properties of the exception,
    with the names returncode and stderr respectively, if cmd returns a non-zero return code.
    '''
    p = subprocess.Popen(args, shell=shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate(stdin)
    if p.returncode != 0:
        e = Exception('Error running command.  args='+str(args)+' returncode='+str(p.returncode)+'\nstdin='+str(stdin)+'\nstderr='+str(error))
        e.returncode = p.returncode
        e.stderr = error
        raise e
    else:
        return output

# last line emacs python mode bug fix -- do not cross
