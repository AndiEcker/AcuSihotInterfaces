import threading

from ae.console_app import main_app_instance, uprint, _logger


class NamedLocks:
    """
    allow to create named lock(s) within the same app (migrate from https://stackoverflow.com/users/355230/martineau
    answer in stackoverflow on the question https://stackoverflow.com/questions/37624289/value-based-thread-lock.

    Currently the sys_lock feature is not implemented. Use either ae.lockfile or the github extension portalocker (see
    https://github.com/WoLpH/portalocker) or the encapsulating extension ilock (https://github.com/symonsoft/ilock).
    More on system wide named locking: https://stackoverflow.com/questions/6931342/system-wide-mutex-in-python-on-linux.
    """
    locks_change_lock = threading.Lock()
    active_locks = dict()
    active_lock_counters = dict()

    def __init__(self, *lock_names, reentrant_locks=True, sys_lock=False):
        self._lock_names = lock_names
        self._lock_class = threading.RLock if reentrant_locks else threading.Lock
        assert not sys_lock, "sys_lock is currently not implemented"
        self._sys_lock = sys_lock
        # map class intern dprint method to cae.dprint() or to global dprint (referencing the module method dprint())
        cae = main_app_instance()
        self.print_func = cae.dprint if cae and getattr(cae, 'startup_end', False) else uprint

        self.dprint("NamedLocks.__init__", lock_names)

    def __enter__(self):
        self.dprint("NamedLocks.__enter__")
        for lock_name in self._lock_names:
            self.dprint("NamedLocks.__enter__ b4 acquire ", lock_name)
            self.acquire(lock_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dprint("NamedLocks __exit__", exc_type, exc_val, exc_tb)
        for lock_name in self._lock_names:
            self.dprint("NamedLocks.__exit__ b4 release ", lock_name)
            self.release(lock_name)

    def dprint(self, *args, **kwargs):
        if 'logger' not in kwargs:
            kwargs['logger'] = _logger
        return self.print_func(*args, **kwargs)

    def acquire(self, lock_name, *args, **kwargs):
        self.dprint("NamedLocks.acquire", lock_name, 'START')

        while True:     # break at the end - needed for to retry after conflicted add/del of same lock name in threads
            with self.locks_change_lock:
                lock_exists = lock_name in self.active_locks
                lock_instance = self.active_locks[lock_name] if lock_exists else self._lock_class()

            # request the lock - out of locks_change_lock context, for to not block other instances of this class
            lock_acquired = lock_instance.acquire(*args, **kwargs)

            if lock_acquired:
                with self.locks_change_lock:
                    if lock_exists != (lock_name in self.active_locks):  # if lock state has changed, then redo/retry
                        self.dprint("NamedLocks.acquire", lock_name, 'RETRY')
                        lock_instance.release()
                        continue
                    if lock_exists:
                        self.active_lock_counters[lock_name] += 1
                    else:
                        self.active_locks[lock_name] = lock_instance
                        self.active_lock_counters[lock_name] = 1
            break

        self.dprint("NamedLocks.acquire", lock_name, 'END')

        return lock_acquired

    def release(self, lock_name, *args, **kwargs):
        self.dprint("NamedLocks.release", lock_name, 'START')

        with self.locks_change_lock:
            if lock_name not in self.active_lock_counters or lock_name not in self.active_locks:
                self.dprint("NamedLocks.release", lock_name, 'IDX-ERR')
                return
            elif self.active_lock_counters[lock_name] == 1:
                self.active_lock_counters.pop(lock_name)
                lock = self.active_locks.pop(lock_name)
            else:
                self.active_lock_counters[lock_name] -= 1
                lock = self.active_locks[lock_name]

        lock.release(*args, **kwargs)

        self.dprint("NamedLocks.release", lock_name, 'END')
