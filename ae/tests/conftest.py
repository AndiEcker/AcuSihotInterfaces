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

        def _tear_down():       # using yield instead of finalizer does not execute the teardown part
            os.remove(file_name)
        request.addfinalizer(_tear_down)

        return file_name, var_name, var_value

    return _setup_and_teardown


@pytest.fixture()
def sys_argv_restore():
    old_argv = sys.argv
    app_key = 'pyTstSysArgv0Mock'
    sys.argv = [app_key, ]    # pytest has empty command line args
    yield old_argv
    _ = _app_instances.pop(app_key, None)
    sys.argv = old_argv
