
'''
This module supports the following use case:

    Alice wants to communicate a message to Bob via a file on a shared
    filesystem.  Alice serializes the message to a temporary file and
    passes the filename to Bob.  Bob reads the message from the file,
    deleting the file in the process.

This is useful for:

- Avoiding creating a custom serialization format to pass a message on a 
  commmand line.  Instead, one passes the filename from `dump` and then
  use `load` to read the message.
- passing a very large message, one that is too big to (want to) put on a
  command line or in a database.
'''

import os
import cPickle as pickle

import temps


def dump(msg, filename=None):
    '''
    Write a message to a file.  If filename is None, a unique hexadecimal
    temporary filename will be used.  Either way, the filename is returned, so
    it can be communicated to whoever will read the file.
    '''
    if filename is None:
        filename = temps.tmppath()

    with open(filename, 'wb') as fh:
        pickle.dump(msg, fh, pickle.HIGHEST_PROTOCOL)

    return filename


def load(filename, delete=True):
    '''
    Read a message from a file.  Delete the file (by default) unless delete is
    False.  Return the message.
    '''
    with open(filename, 'rb') as fh:
        msg = pickle.load(fh)

    if delete:
        os.remove(filename)

    return msg

