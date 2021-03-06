# system-wide file locking
#
# code snippets inspired by module zc.lockfile (see https://pypi.python.org/pypi/zc.lockfile and
# https://github.com/zopefoundation/zc.lockfile)
#
# See also / maybe replace with https://github.com/WoLpH/portalocker (used e.g. by https://github.com/symonsoft/ilock)
import os
import datetime
import socket

from ae.base import DATE_TIME_ISO
from ae.literal import parse_date


try:                                        # unix
    import fcntl as file_lock_mod
    _lock_flags = file_lock_mod.LOCK_EX | file_lock_mod.LOCK_NB
    _unlock_flags = file_lock_mod.LOCK_UN
    _lock_func = file_lock_mod.lockf
except ImportError:                         # windows
    import msvcrt as file_lock_mod
    _lock_flags = file_lock_mod.LK_NBLCK
    _unlock_flags = file_lock_mod.LK_UNLCK
    _lock_func = file_lock_mod.locking


__version__ = '0.0.1'


_SEP_CHAR = '\n'
_LOCK_LEN = 1


class LockFile:
    def __init__(self, path, auto_unlock_timeout=datetime.timedelta(hours=6)):
        self._fp = None
        self._path = path
        self._auto_unlock_timeout = auto_unlock_timeout     # datetime.timedelta, pass None to disable
        self._timed_out = False
        self._lock_time = None

    def lock(self):
        try:
            # Try to open for writing without truncation:
            fp = open(self._path, 'r+')
        except IOError:
            # If the file doesn't exist, we'll get an IO error, try a+
            # Note that there may be a race here. Multiple processes could fail on the r+ open and open the file a+,
            # but only one will get the lock and write a pid.
            fp = open(self._path, 'a+')

        self._lock_time = datetime.datetime.now()
        lock_len = _LOCK_LEN
        fp.seek(0)
        try:
            _lock_func(fp.fileno(), _lock_flags, _LOCK_LEN)  # lock just the first _LOCK_LEN bytes
        except Exception as ex:
            fp.seek(_LOCK_LEN)
            pid, host, lock_time = fp.read().split(_SEP_CHAR)

            if self._auto_unlock_timeout is None or parse_date(lock_time) + self._auto_unlock_timeout > self._lock_time:
                fp.close()
                return "ae.lockfile.lock(): locking error (host={host}, file={path}, pid={pid}, time={time}, ex={ex})"\
                    .format(host=host, path=self._path, pid=pid, time=lock_time, ex=ex)

            self._timed_out = True
            # fp.seek(0)
            # _lock_func(fp.fileno(), _unlock_flags, _LOCK_LEN)
            fp.seek(_LOCK_LEN)
            lock_len = 0
            # _lock_func(fp.fileno(), _lock_flags, _LOCK_LEN)

        fp.write(" " * lock_len + str(os.getpid()) + _SEP_CHAR + str(socket.gethostname())
                 + _SEP_CHAR + datetime.datetime.strftime(self._lock_time, DATE_TIME_ISO))
        fp.truncate()
        fp.flush()
        self._fp = fp

        return ""                   # file lock was successful

    def unlock(self):
        if self._fp is not None:
            self._fp.seek(0)        # needed to prevent IOError/Permission denied
            try:
                _lock_func(self._fp.fileno(), _unlock_flags, _LOCK_LEN)
            except IOError:
                if not self._timed_out:     # hide error after auto_unlock_timeout
                    raise
            self._fp.close()
            self._fp = None
            if self._timed_out:
                os.rename(self._path, self._path + datetime.datetime.strftime(self._lock_time, '_%Y%m%d_%H%MS_%f'))
