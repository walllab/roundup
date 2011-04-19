#!/usr/bin/env python

import subprocess
import os


def sendmail(fromAddr, toAddrs, subject, message):
    '''
    fromAddr: email string of who is the mail coming from.  e.g. roundup-noreply@roundup.hms.harvard.edu
    toAddrs: list of email addresses of who will get the mail.
    subject: string
    message: string
    Using qmail (the 'mail' unix command), can send mail from cluster nodes, orchestra, and trumpet.
    raises: exception if sending mail returns a non-zero return code.
    '''
    # can set who the mail comes from in the environment
    mailUser, mailHost = fromAddr.split('@')
    env = {}
    env.update(os.environ)
    env['MAILUSER'] = str(mailUser)
    env['MAILHOST'] = str(mailHost)
    env['QMAILINJECT'] = 'f'

    # command contains subject and who the mail goes to
    args = ['mail', '-s', subject] + toAddrs
    p = subprocess.Popen(args, env=env, stdin=subprocess.PIPE)

    # stdin contains the body of the mail.
    p.communicate(str(message)+'\n')
    if p.returncode != 0:
        raise Exception('Non-zero return code when sending mail', p.returncode)
    

# last line emacs python mode bug fix
