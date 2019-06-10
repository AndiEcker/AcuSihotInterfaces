import glob

import pytest

# import datetime
import time

from ae.lockfile import *

LOCK_FILE_NAME = 'f.lock'


class TestLockFile:
    def test_lock_simple(self):
        lock_handle = LockFile(LOCK_FILE_NAME)
        ret = lock_handle.lock()
        lock_handle.unlock()
        assert ret == ""

    def test_lock_concurrent(self):
        lock_handle = LockFile(LOCK_FILE_NAME)
        assert lock_handle.lock() == ""
        lh2 = LockFile(LOCK_FILE_NAME)
        lock2_ret = lh2.lock()
        lock_handle.unlock()
        assert lock2_ret
        assert LOCK_FILE_NAME in lock2_ret

    def test_lock_release(self):
        lock_handle = LockFile(LOCK_FILE_NAME)
        assert lock_handle.lock() == ""
        lock_handle.unlock()

        lock_handle = LockFile(LOCK_FILE_NAME)
        assert lock_handle.lock() == ""
        lock_handle.unlock()

    def test_delete_lock_file(self):
        lock_handle = LockFile(LOCK_FILE_NAME)
        assert lock_handle.lock() == ""
        with pytest.raises(IOError):
            os.remove(LOCK_FILE_NAME)
        lock_handle.unlock()
        os.remove(LOCK_FILE_NAME)

    def test_unlock_by_file_close(self):
        lock_handle = LockFile(LOCK_FILE_NAME)
        assert lock_handle.lock() == ""
        lock_handle._fp.close()
        time.sleep(1)
        lock_handle = LockFile(LOCK_FILE_NAME)
        assert lock_handle.lock() == ""
        lock_handle.unlock()

    def test_timed_out_lock(self):
        lock_handle = LockFile(LOCK_FILE_NAME)
        assert lock_handle.lock() == ""
        time.sleep(.1)
        lh2 = LockFile(LOCK_FILE_NAME, auto_unlock_timeout=datetime.timedelta(microseconds=1))
        lock2_ret = lh2.lock()
        assert lock2_ret == ""
        # had to first call unlock on the first lock to prevent exception on os.rename in lh2.unlock() call
        lock_handle.unlock()
        time.sleep(1)
        lh2.unlock()
        lock_handle.unlock()
        timed_out_log_files = list(glob.glob(LOCK_FILE_NAME + "*"))
        assert len(timed_out_log_files) == 1
        for fn in timed_out_log_files:
            os.remove(fn)
        assert lock2_ret == ""
