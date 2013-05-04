


import os

import filemsg


def echo(msg, msg2):
    print msg, msg2
    return msg, msg2


def test_msg():
    
    msg = ([1, 2], {'hi': 'bye'})

    # serialize msg to a file
    filename = filemsg.dump(msg)
    print filename

    # Confirm that the file was written
    assert os.path.exists(filename)

    # read msg and delete file
    out = filemsg.load(filename)

    # Test that the unserialized values equal the serialized ones.
    assert msg == out

    # Confirm that the file was deleted
    assert not os.path.exists(filename)

