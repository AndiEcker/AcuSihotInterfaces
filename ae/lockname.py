"""
simple usable threading locks
=============================

Named locks are used in multi-threaded applications and based on the python threading lock classes
:class:`threading.Lock` and :class:`threading.RLock`. The advantage of the named locks in contrary
to python threading locks is that a lock don't need to create and store a reference of a python
threading lock object - the :class:`NamedLocks` does this automatically for your application and
does keep track of all the named locks of your application in its class variables.

So a named lock get exclusively identified only by an unique string. And for to create other
blocking locks you only need a reference to the :class:`NamedLocks` class.

Named locks are very useful e.g. if you want to lock a certain record of database table. For this
you simply create a new instance of the :class:`NamedLocks` class and as unique string you can use
the table name followed by the primary key of the record to lock::

    named_lock = NamedLocks()
    if named_lock.acquire(table_name + primary_key)

        ...     # locked database transaction code goes here

        named_lock.release(table_name + primary_key)

If now any other process of your application want to lock the same record (same table name and primary
key) then it will be blocked until the process that acquired this named lock first is releasing the
table record lock.

Alternatively and especially if your application want to create multiple named locks you can use the
class :class:`NamedLocks` as a context manager, passing all the named lock strings to the constructor::

    with NamedLocks(table_name1 + primary_key1, table_name2 + primary_key2, ...):
        ...     # locked database transaction

"""
import threading
from typing import Dict, Union

from ae.core import main_app_instance, _logger, po


class NamedLocks:
    """ create new named lock(s) within the same app.

    Migrated from https://stackoverflow.com/users/355230/martineau answer in stackoverflow on the question
    https://stackoverflow.com/questions/37624289/value-based-thread-lock.

    Currently the sys_lock feature is not implemented. Use either ae.lockfile or the github extension portalocker (see
    https://github.com/WoLpH/portalocker) or the encapsulating extension ilock (https://github.com/symonsoft/ilock).
    More on system wide named locking: https://stackoverflow.com/questions/6931342/system-wide-mutex-in-python-on-linux.
    """
    locks_change_lock: threading.Lock = threading.Lock()    #: lock used for to change status of all NamedLock instances
    active_locks: Dict[str, Union[threading.Lock, threading.RLock]] = dict()    #: all active RLock/Lock instances
    active_lock_counters: Dict[str, int] = dict()                               #: lock counters for reentrant locks

    def __init__(self, *lock_names: str, reentrant_locks: bool = True, sys_lock: bool = False):
        """ prepare new named lock(s).

        :param lock_names:          unique lock strings to be prepared for to be locked by :meth:`.__enter__`.
        :param reentrant_locks:     pass False to use non-reentrant locks (True=reentrant locks).
        :param sys_lock:            pass True to prepare system lock (works for several independent applications).
                                    CURRENTLY NOT IMPLEMENTED.
        """
        self._lock_names = lock_names
        self._lock_class = threading.RLock if reentrant_locks else threading.Lock
        assert not sys_lock, "sys_lock is currently not implemented"
        self._sys_lock = sys_lock
        # map class intern dpo method to cae.dpo() or to global dpo (referencing the module method dpo())
        cae = main_app_instance()
        self._print_func = cae.dpo if cae and getattr(cae, 'startup_end', False) else po

        self.dpo("NamedLocks.__init__", lock_names)

    def __enter__(self):
        """ locking context enter method. """
        self.dpo("NamedLocks.__enter__")
        for lock_name in self._lock_names:
            self.dpo("NamedLocks.__enter__ b4 acquire ", lock_name)
            self.acquire(lock_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ locking context exit method. """
        self.dpo("NamedLocks __exit__", exc_type, exc_val, exc_tb)
        for lock_name in self._lock_names:
            self.dpo("NamedLocks.__exit__ b4 release ", lock_name)
            self.release(lock_name)

    def dpo(self, *args, **kwargs):
        """ print function which is suppressing printout if debug level is too low. """
        if 'logger' not in kwargs:
            kwargs['logger'] = _logger
        return self._print_func(*args, **kwargs)

    def acquire(self, lock_name: str, *args, **kwargs) -> bool:
        """ acquire the named lock specified by the `lock_name` argument.

        :param lock_name:   name of the lock to acquire.
        :param args:        args that will be passed to the acquire method of the underlying :class:`~threading.RLock`
                            / :class:`~threading.Lock` classes instance.
        :param kwargs:      kwargs that will be passed to the acquire method of the underlying :class:`~threading.RLock`
                            / :class:`~threading.Lock` classes instance.
        :return:            True if named lock got acquired successfully, else False.
        """
        self.dpo("NamedLocks.acquire", lock_name, 'START')

        while True:     # break at the end - needed for to retry after conflicted add/del of same lock name in threads
            with self.locks_change_lock:
                lock_exists = lock_name in self.active_locks
                lock_instance = self.active_locks[lock_name] if lock_exists else self._lock_class()

            # request the lock - out of locks_change_lock context, for to not block other instances of this class
            lock_acquired = lock_instance.acquire(*args, **kwargs)

            if lock_acquired:
                with self.locks_change_lock:
                    if lock_exists != (lock_name in self.active_locks):  # if lock state has changed, then redo/retry
                        self.dpo("NamedLocks.acquire", lock_name, 'RETRY')
                        lock_instance.release()
                        continue
                    if lock_exists:
                        self.active_lock_counters[lock_name] += 1
                    else:
                        self.active_locks[lock_name] = lock_instance
                        self.active_lock_counters[lock_name] = 1
            break

        self.dpo("NamedLocks.acquire", lock_name, 'END')

        return lock_acquired

    def release(self, lock_name: str):
        """ release the named lock specified by the `lock_name` argument.

        :param lock_name:   name of the lock to release.
        """
        self.dpo("NamedLocks.release", lock_name, 'START')

        with self.locks_change_lock:
            if lock_name not in self.active_lock_counters or lock_name not in self.active_locks:
                self.dpo("NamedLocks.release", lock_name, 'IDX-ERR')
                return
            elif self.active_lock_counters[lock_name] == 1:
                self.active_lock_counters.pop(lock_name)
                lock = self.active_locks.pop(lock_name)
            else:
                self.active_lock_counters[lock_name] -= 1
                lock = self.active_locks[lock_name]

        lock.release()

        self.dpo("NamedLocks.release", lock_name, 'END')
