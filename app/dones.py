

import kvstore


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

    


