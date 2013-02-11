

import json
import os


class Dones(object):
    '''
    Semantically, Dones can be used to mark whether a key is "done" and
    check whether a key has been marked, i.e. if the key is "done".
    Keys can also be unmarked, so that they are no longer "done".
    All keys can be unmarked by cleaning the Dones.
    Keys are kept in their own namespace to avoid conflicts with other
    sets of other keys and to make it easy to implement cleaning.

    Dones are implemented using a database-backed key store.  This means
    it should be relatively high performance, scale to millions of keys,
    and handle concurrent access well.
    '''
    def __init__(self, k):
        '''
        k: a kvstore.KStore object with a namespace used to keep these dones
        separate from other dones in the database.  Makes it easy to reset or
        drop the dones without affecting other dones.  Makes it easy to avoid
        these keys conflicting with another dones keys.
        '''
        self.k = k
        self.ready = False

    def _get_k(self):
        '''
        Accessing self.k indirectly allows for creating the kvstore table
        if necessary.
        '''
        if not self.ready:
            self.k.create() # create table if it does not exist.
            self.ready = True

        return self.k

    def clean(self):
        '''
        Remove all existing done markers.  Useful for resetting the dones or
        cleaning up when all done.
        '''
        self._get_k().drop()
        self.ready = False # _get_k() will create table next time.
        
    def done(self, key):
        '''
        return True iff key is marked done.
        '''
        return self._get_k().exists(key)

    def mark(self, key):
        '''
        Mark a key as done.
        '''
        return self._get_k().add(key)

    def unmark(self, key):
        return self._get_k().remove(key)

    def all_done(self, keys):
        '''
        Return: True iff all the keys are done.
        '''
        # implementation note: use generator b/c any/all are short-circuit functions
        return all(self.done(key) for key in keys)

    def any_done(self, keys):
        '''
        Return: True iff any of the keys are done.
        '''
        # implementation note: use generator b/c any/all are short-circuit functions
        return any(self.done(key) for key in keys)


class FileDones(object):
    '''
    Semantically, Dones can be used to mark whether a key is "done" and
    check whether a key has been marked, i.e. if the key is "done".
    Keys can also be unmarked, so that they are no longer "done".
    All keys can be unmarked by cleaning the Dones.
    Keys are kept in their own namespace to avoid conflicts with other
    sets of other keys and to make it easy to implement cleaning.

    FileDones are implemented using a flat file.  This means it should be
    relatively slow, handle concurrency poorly, and scale to thousands (not
    millions) of keys.  It is mostly useful for simple situations where you
    do not want to or can not set up a database.
    '''
    def __init__(self, filename):
        '''
        :param filename: where to store the dones.  This file represents a 
        namespace to keep these dones separate from other dones.  This makes it
        easy to clear out the dones without affecting other dones and to avoid
        conflicting keys.
        '''
        self.path = filename

    def _serialize(self, key):
        return json.dumps(key)

    def _done_line(self, key):
        return 'done ' + self._serialize(key) + '\n'

    def _undone_line(self, key):
        return 'undo ' + self._serialize(key) + '\n'

    def _persist(self, msg):
        with open(self.path, 'a') as fh:
            fh.write(msg)
            fh.flush()

    def compact(self):
        '''
        Not implemented.  This would rewrite the dones file removing any
        keys that have been marked undone (and not remarked as done.)
        '''
        pass

    def clear(self):
        '''
        Remove all existing done markers and the file used to store the dones.
        '''
        if os.path.exists(self.path):
            os.remove(self.path)

    def mark(self, key):
        '''
        Mark a key as done.

        :param key: a json-serializable object.
        '''
        self._persist(self._done_line(key))

    def unmark(self, key):
        '''
        Mark a key as not done.  This is useful after marking a key as done
        to indicate that it is no longer done, since by default a key is
        not done unless explicitly marked as done.

        :param key: a json-serializable object.
        '''
        self._persist(self._undone_line(key))

    def done(self, key):
        '''
        return True iff key is marked done.

        :param key: a json-serializable object.
        '''
        # key is not done b/c the file does not even exist yet
        if not os.path.exists(self.path):
            return False

        is_done = False
        done_line = self._done_line(key)
        undone_line = self._undone_line(key)
        with open(self.path) as fh:
            for line in fh:
                if line == done_line:
                    is_done = True
                elif line == undone_line:
                    is_done = False

        return is_done

    def are_done(self, keys):
        '''
        Return a list of boolean values corresponding to whether or not each
        key in keys is marked done.  This method can be faster than
        individually checking each key, depending on how many keys you
        want to check.

        :param keys: a list of json-serializable keys
        '''
        # No keys are done b/c the file does not even exist yet.
        if not os.path.exists(self.path):
            return [False] * len(keys)

        done_lines = set([self._done_line(key) for key in keys])
        undone_lines = set([self._undone_line(key) for key in keys])
        status = {}
        with open(self.path) as fh:
            for line in fh:
                if line in done_lines:
                    # extract serialized key
                    status[line[5:-1]] = True
                elif line in undone_lines:
                    status[line[5:-1]] = False
        serialized_keys = [self._serialize(key) for key in keys]
        return [status.get(sk, False) for sk in serialized_keys]

    def all_done(self, keys):
        '''
        Return: True iff all the keys are done.

        :param keys: a list of json-serializable keys
        '''
        return all(self.done(key) for key in keys)

    def any_done(self, keys):
        '''
        Return: True iff any of the keys are done.

        :param keys: a list of json-serializable keys
        '''
        return any(self.are_done(keys))




