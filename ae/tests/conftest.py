import os
import sys
import pytest

from ae.core import _app_instances, _unregister_app_instance


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
def sys_argv_app_key_restore(tst_app_key):          # needed for tests using AppBase/ConsoleApp
    old_argv = sys.argv
    sys.argv = [tst_app_key, ]
    yield tst_app_key
    sys.argv = old_argv


@pytest.fixture
def restore_app_env():                  # needed for tests using AppBase/ConsoleApp
    yield "a,n,y"
    # added list because unregister does _app_instances.pop() calls
    app_keys = list(reversed(list(_app_instances.keys())))
    for key in app_keys:
        _unregister_app_instance(key)   # remove app from ae.core app register/dict
