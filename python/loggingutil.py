'''
Utilities for using the logging module on Orchestra.
'''


import logging
import os


import sendmail


class ConcurrentFileHandler(logging.Handler):
    """
    A handler class which writes logging records to a file.  Every time it writes it opens, writes, flushes, and closes the file.
    So do not use in a tight loop.  This is an attempt to overcome concurrent write issues that the standard FileHandler has
    when multiple processes on the cluster try to log messages.
    """
    def __init__(self, filename, mode="a"):
        """
        Open the specified file and use it as the stream for logging.
        """
        logging.Handler.__init__(self)
        # keep the absolute path, otherwise derived classes which use this
        # may come a cropper when the current directory changes
        self.baseFilename = os.path.abspath(filename)
        self.mode = mode


    def openWriteClose(self, msg):
        f = open(self.baseFilename, self.mode)
        f.write(msg)
        f.flush() # improves consistency of writes in a concurrent environment (Orchestra cluster)
        f.close()

    
    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline
        [N.B. this may be removed depending on feedback]. If exception
        information is present, it is formatted using
        traceback.print_exception and appended to the stream.
        """
        try:
            msg = self.format(record)
            fs = "%s\n"
            self.openWriteClose(fs % msg)
        except:
            self.handleError(record)


class ClusterMailHandler(logging.Handler):
    '''email log messages using sendmail module, which can mail from orchestra and cluster nodes.'''

    def __init__(self, fromAddr, toAddrs, subject):
        logging.Handler.__init__(self)
        self.fromAddr = fromAddr
        self.toAddrs = toAddrs
        self.subject = subject

    def emit(self, record):
        """
        Emit a record.
        
        Format the record and send it to the specified addressees.
        """
        try:
            msg = self.format(record)
            sendmail.sendmail(self.fromAddr, self.toAddrs, self.subject, message=msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def deprecated_setupLogging(logFile, fromAddr, toAddrs, subject, loggingLevel, mailLoggingLevel=logging.WARNING, logger=None):
    if logger is None:
        logger = logging.getLogger()
        
    formatter = logging.Formatter('[%(asctime)s %(name)s %(levelname)s %(filename)s line %(lineno)d] %(message)s')

    # log DEBUG and higher messages to the log file
    # handler = logging.FileHandler(logFile, 'a')
    handler = ConcurrentFileHandler(logFile, 'a')
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    
    # log WARNING and higher messages to email
    handler = ClusterMailHandler(fromAddr, toAddrs, subject)
    handler.setFormatter(formatter)
    handler.setLevel(mailLoggingLevel)
    logger.addHandler(handler)

    # process all log messages (i.e. send them to handlers.)
    logger.setLevel(loggingLevel)
    
    return logger



