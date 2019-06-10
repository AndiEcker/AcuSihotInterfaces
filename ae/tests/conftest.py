import sys
import pytest


@pytest.fixture()
def sys_argv_restore():
    old_argv = sys.argv
    yield old_argv
    sys.argv = old_argv


