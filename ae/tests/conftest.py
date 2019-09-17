import os
import sys
import pytest

from ae.core import _app_instances


@pytest.fixture
def config_fna_vna_vva(request):
    def _setup_and_teardown(file_name='test_config.cfg', var_name='test_config_var', var_value='test_value'):
        if os.path.sep not in file_name:
            file_name = os.path.join(os.getcwd(), file_name)
        with open(file_name, 'w') as f:
            f.write("[aeOptions]\n{} = {}".format(var_name, var_value))

        def _tear_down():               # using yield instead of finalizer does not execute the teardown part
            os.remove(file_name)
        request.addfinalizer(_tear_down)

        return file_name, var_name, var_value

    return _setup_and_teardown


@pytest.fixture
def tst_app_key():
    return 'pyTstSysArgv0Mock'


@pytest.fixture
def sys_argv_restore(tst_app_key):      # needed for tests using AppBase/ConsoleApp
    old_argv = sys.argv
    # if not sys.argv:                  # ensure proper command line args
    sys.argv = [tst_app_key, ]          # sys.argv is sometimes empty, sometimes showing _jb_pytest_runner
    yield old_argv
    _ = _app_instances.pop(tst_app_key, None)
    sys.argv = old_argv
