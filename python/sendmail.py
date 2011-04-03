#!/usr/bin/env python

import subprocess


def mailFromGrid(fromAddr, toAddrs, subject, message):
    # implementation moved to sendmail and old sendmail implementation deprecated, since the new implementation does everything we have needed
    # from everywhere we have needed it.
    return sendmail(fromAddr, toAddrs, subject, message)

    
def sendmail(fromAddr, toAddrs, subject, message):
    '''
    Using qmail, can send mail from cluster nodes, orchestra, and trumpet.
    '''
    # logging.debug('email msg: '+msg)
    mailUser, mailHost = fromAddr.split('@')
    cmd = 'MAILUSER='+str(mailUser)+' MAILHOST='+str(mailHost)+' QMAILINJECT=f mail -s "'+subject+'" '+' '+(' '.join('"'+email+'"' for email in toAddrs))
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
    p.communicate(str(message)+'\n')


def sendmailOld(fromAddr, toAddrs, subject, message, subtype=None):
    '''
    Deprecated.
    simple function to send an email.  Does not work from cluster nodes.  Use mailFromGrid() for that.
    from: email address
    to: list of email addresses
    '''
    
    
    # Import smtplib for the actual sending function
    import smtplib
    
    # Import the email modules we'll need
    import email.MIMEText
    
    # Create a text/plain message
    if subtype == None:
        msg = email.MIMEText.MIMEText(message)
    else:
        msg = email.MIMEText.MIMEText(message, subtype)

    msg['Subject'] = subject
    msg['From'] = fromAddr
    msg['To'] = ', '.join(toAddrs)
    
    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP()
    s.connect()
    s.sendmail(fromAddr, toAddrs, msg.as_string())
    s.close()


# last line emacs python mode bug fix
