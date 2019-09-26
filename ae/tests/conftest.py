import os
import sys
import glob
import pytest

from ae.core import app_inst_lock, _app_instances, _unregister_app_instance
from ae.console import MAIN_SECTION_DEF


@pytest.fixture
def config_fna_vna_vva(request):
    def _setup_and_teardown(file_name='test_config.cfg', var_name='test_config_var', var_value='test_value'):
        if os.path.sep not in file_name:
            file_name = os.path.join(os.getcwd(), file_name)
        with open(file_name, 'w') as f:
            f.write(f"[{MAIN_SECTION_DEF}]\n{var_name} = {var_value}")

        def _tear_down():               # using yield instead of finalizer does not execute the teardown part
            os.remove(file_name)
        request.addfinalizer(_tear_down)

        return file_name, var_name, var_value

    return _setup_and_teardown


@pytest.fixture
def tst_app_key():
    return 'pyTstSysArgv0Mock'


@pytest.fixture
def sys_argv_app_key_restore(tst_app_key):          # needed for tests using sys.argv/get_opt() of ConsoleApp
    old_argv = sys.argv
    sys.argv = [tst_app_key, ]
    yield tst_app_key
    sys.argv = old_argv


@pytest.fixture
def restore_app_env():                              # needed for tests instantiating AppBase/ConsoleApp
    yield "a,n,y"
    # added outer list() because unregister does _app_instances.pop() calls
    # and added inner list() because the .keys() 'generator' object is not reversible
    with app_inst_lock:
        app_keys = list(reversed(list(_app_instances.keys())))
        for key in app_keys:
            _unregister_app_instance(key)   # remove app from ae.core app register/dict


def delete_files(file_name, keep_ext=False, ret_type='count'):
    if keep_ext:
        fp, fe = os.path.splitext(file_name)
        file_mask = fp + '*' + fe
    else:
        file_mask = file_name + '*'
    cnt = 0
    ret = list()
    for fn in glob.glob(file_mask):
        if ret_type == 'contents':
            with open(fn) as fd:
                fc = fd.read()
            ret.append(fc)
        elif ret_type == 'names':
            ret.append(fn)
        os.remove(fn)
        cnt += 1
    return cnt if ret_type == 'count' else ret
