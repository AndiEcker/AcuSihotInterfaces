# TODO: remove " or out == ''" as soon as capsys bug is fixed
import sys
import os
import datetime
import time
import logging
from argparse import ArgumentError

import pytest

from sys_data_ids import DEBUG_LEVEL_TIMESTAMPED, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE
from ae.console_app import (fix_encoding, round_traditional, reset_main_cae, sys_env_dict, to_ascii, full_stack_trace,
                            uprint, _ca_instance,
                            ConsoleApp, Progress, NamedLocks, Setting, _DuplicateSysOut,
                            ILLEGAL_XML_SUB, MAX_NUM_LOG_FILES, INI_EXT, calling_module, DATE_TIME_ISO, DATE_ISO,
                            )


@pytest.fixture
def config_fna_vna_vva_old():       # this does not tear down (os.remove does never be called)
    def _setup_and_teardown(file_name='test_config.cfg', var_name='test_config_var', var_value='test_value'):
        if os.path.sep not in file_name:
            file_name = os.path.join(os.getcwd(), file_name)
        with open(file_name, 'w') as f:
            f.write("[Settings]\n{} = {}".format(var_name, var_value))
        yield file_name, var_name, var_value
        os.remove(file_name)
    return _setup_and_teardown


@pytest.fixture
def config_fna_vna_vva(request):
    def _setup_and_teardown(file_name='test_config.cfg', var_name='test_config_var', var_value='test_value'):
        if os.path.sep not in file_name:
            file_name = os.path.join(os.getcwd(), file_name)
        with open(file_name, 'w') as f:
            f.write("[Settings]\n{} = {}".format(var_name, var_value))

        def _tear_down():
            os.remove(file_name)

        request.addfinalizer(_tear_down)
        return file_name, var_name, var_value

    return _setup_and_teardown


def test_logging_config_dict_basic_from_ini(config_fna_vna_vva):
    file_name, var_name, var_val = config_fna_vna_vva(
        var_name='py_logging_config_dict',
        var_value=dict(
            version=1,
            disable_existing_loggers=False))

    cae = ConsoleApp('0.0', 'test_python_logging_config_dict_basic_from_ini', additional_cfg_files=[file_name])

    cfg_val = cae.get_config(var_name)
    assert cfg_val == var_val

    assert cae.logging_conf_dict == var_val

    logging.shutdown()


class TestHelpers:
    def test_round_traditional(self):
        assert round_traditional(1.01) == 1
        assert round_traditional(10.1, -1) == 10
        assert round_traditional(1.123, 1) == 1.1
        assert round_traditional(0.5) == 1
        assert round_traditional(0.5001, 1) == 0.5

        assert round_traditional(0.075, 2) == 0.08
        assert round(0.075, 2) == 0.07

    def test_sys_env_dict(self):
        assert sys_env_dict().get('python_ver')
        assert sys_env_dict().get('cwd')
        assert sys_env_dict().get('frozen') is False

        assert sys_env_dict().get('bundle_dir') is None
        sys.frozen = True
        assert sys_env_dict().get('bundle_dir')
        del sys.__dict__['frozen']
        assert sys_env_dict().get('bundle_dir') is None

    def test_to_ascii(self):
        assert to_ascii('äöü') == 'aou'

    def test_calling_module(self):
        assert calling_module() == 'test_console_app'
        assert calling_module('') == 'test_console_app'
        assert calling_module('xxx_test') == 'test_console_app'
        assert calling_module(called_module=__name__) == '_pytest.python'
        assert calling_module(called_module=__name__, depth=2) == '_pytest.python'
        assert calling_module(called_module=__name__, depth=3) == 'pluggy.callers'
        assert calling_module(called_module=__name__, depth=4) == 'pluggy.manager'
        assert calling_module(called_module=__name__, depth=5) == 'pluggy.manager'
        assert calling_module(called_module=__name__, depth=6) == 'pluggy.hooks'
        assert calling_module(called_module=__name__, depth=7) == '_pytest.python'
        assert calling_module(called_module=__name__, depth=8) == '_pytest.runner'
        assert calling_module(called_module=__name__, depth=9) == 'pluggy.callers'
        assert calling_module(called_module=__name__, depth=10) == 'pluggy.manager'
        assert calling_module(called_module=__name__, depth=11) == 'pluggy.manager'
        assert calling_module(called_module=__name__, depth=12) == 'pluggy.hooks'
        assert calling_module(called_module=__name__, depth=13) == '_pytest.runner'
        assert calling_module(called_module=__name__, depth=14) == '_pytest.runner'
        assert calling_module(called_module=__name__, depth=15) == '_pytest.runner'
        assert calling_module(called_module=__name__, depth=16) == '_pytest.runner'

        assert calling_module(called_module=__name__, depth=0) == 'ae.console_app'
        assert calling_module(called_module=__name__, depth=-1) == 'ae.console_app'
        assert calling_module(called_module=__name__, depth=-2) == 'ae.console_app'

        assert calling_module(called_module=None, depth=-1) == 'ae.console_app'
        assert calling_module(called_module=None, depth=None) is None

    def test_fix_encoding_umlaut(self):
        assert fix_encoding('äöü') == '\\xe4\\xf6\\xfc'
        assert fix_encoding('äöü', encoding=None) == '\\xe4\\xf6\\xfc'
        assert fix_encoding('äöü', encoding='utf-8') == 'äöü'
        assert fix_encoding('äöü', encoding='utf-16') == 'äöü'
        assert fix_encoding('äöü', encoding='cp1252') == 'äöü'
        assert fix_encoding('äöü', encoding='utf-8', try_counter=0) == 'äöü'
        assert fix_encoding('äöü', encoding='utf-8', try_counter=1) == 'äöü'
        assert fix_encoding('äöü', encoding='utf-8', try_counter=3) == 'äöü'
        assert fix_encoding('äöü', encoding='utf-8', try_counter=4) == 'äöü'
        assert fix_encoding('äöü', encoding='utf-8', try_counter=5) is None

    def test_fix_encoding_error(self, capsys, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_fix_encoding_error', debug_level_def=DEBUG_LEVEL_VERBOSE)
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_VERBOSE  # needed for to init logging env
        assert fix_encoding('äöü', encoding='utf-8') == 'äöü'
        out, err = capsys.readouterr()
        # STRANGE: capsys/capfd don't show uprint output - out=='' although it is shown in the pytest log/console
        # possible fix in pytest 3.7.4 (https://github.com/pytest-dev/pytest/issues/3819) - current pytest is 3.6.2
        # STILL RETURNING EMPTY STRING after updating pytest to 5.0.1
        # .. got pip to work behind NTLM proxy by running Admin CMD and setting (but used NP_PROXY instead of NO_PROXY):
        # .. set NP_PROXY="acumen\aecker:xxxx@proxy.acumen.es:8080"
        # So on 18-Jul I did an update of all my pip packages with:
        # .. pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1  | xargs -n1 pip install -U
        # .. BUT still got the following errors:
        ''' - requests 2.19.1 has requirement idna<2.8,>=2.5, but you'll have idna 2.8 which is incompatible.
            - Successfully installed kivy.deps.gstreamer
            Exception:
            Traceback (most recent call last):
              File "c:\python35\lib\shutil.py", line 391, in _rmtree_unsafe
                os.rmdir(path)
            OSError: [WinError 145] The directory is not empty: 'C:\\Users\\AECKER~1.ACU\\AppData\\Local\\Temp\\
            pip-install-1etj4rnz\\kivy.deps.gstreamer\\
            kivy_deps.gstreamer-0.1.17.data\\data\\share\\gstreamer\\share\\locale\\eo\\lc_messages'
            
            During handling of the above exception, another exception occurred:
            ...
        After that I first tried to update pip with the command in the line above which worked without any error
        Could not update kivy-examples
        '''
        print("OUT/ERR", out, err)      # TODO: out is always an empty string
        assert out.startswith('ae.console_app.fix_encoding()') or out == ''

    def test_uprint(self, capsys):
        uprint()
        out, err = capsys.readouterr()
        assert (out == '\n' or out == '') and err == ''

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict_basic_from_ini')
        (_ca_instance or cae).debug_level = DEBUG_LEVEL_TIMESTAMPED
        (_ca_instance or cae).multi_threading = True
        uprint(invalid_kwarg='ika')
        out, err = capsys.readouterr()
        assert ('ika' in out or out == '') and err == ''

        us = chr(40960) + chr(1972)
        uprint(us, encode_errors_def='strict')
        out, err = capsys.readouterr()
        assert (us in out or out == '') and err == ''


class TestPythonLogging:
    def test_logging_config_dict_basic_from_ini(self, config_fna_vna_vva):
        file_name, var_name, var_val = config_fna_vna_vva(var_name='py_logging_config_dict',
                                                          var_value=dict(version=1,
                                                                         disable_existing_loggers=False))

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict_basic_from_ini', additional_cfg_files=[file_name])

        cfg_val = cae.get_config(var_name)
        assert cfg_val == var_val

        assert cae.logging_conf_dict == var_val

        logging.shutdown()

    def test_logging_config_dict_console_from_init(self):
        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.StreamHandler',
                                              'level': logging.INFO}))
        print(str(var_val))

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict_console',
                         logging_config=dict(py_logging_config_dict=var_val))

        assert cae.logging_conf_dict == var_val
        logging.shutdown()

    def test_logging_config_dict_complex(self, caplog):
        log_file = 'test_rot_file.log'
        entry_prefix = "TEST LOG ENTRY "

        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.handlers.RotatingFileHandler',
                                              'level': logging.INFO,
                                              'filename': log_file,
                                              'maxBytes': 33,
                                              'backupCount': 63}),
                       loggers={'root': dict(handlers=['console']),
                                'ae': dict(handlers=['console']),
                                'ae.console_app': dict(handlers=['console'])}
                       )
        print(str(var_val))

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict_file',
                         logging_config=dict(py_logging_config_dict=var_val))

        assert cae.logging_conf_dict == var_val

        root_logger = logging.getLogger()
        ae_logger = logging.getLogger('ae')
        ae_cae_logger = logging.getLogger('ae.console_app')

        # ConsoleAppEnv uprint
        log_text = entry_prefix + "0 uprint"
        cae.uprint(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 uprint root"
        cae.uprint(log_text, logger=root_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 uprint ae"
        cae.uprint(log_text, logger=ae_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 uprint ae_cae"
        cae.uprint(log_text, logger=ae_cae_logger)
        assert caplog.text.endswith(log_text + "\n")

        # logging
        logging.info(entry_prefix + "1 info")       # will NOT be added to log
        assert caplog.text.endswith(log_text + "\n")

        logging.debug(entry_prefix + "2 debug")     # NOT logged
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "3 warning"
        logging.warning(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error logging"
        logging.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        # loggers
        log_text = entry_prefix + "4 error root"
        root_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error ae"
        ae_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error ae_cae"
        ae_cae_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        # ConsoleAppEnv dprint
        sys.argv = ['test']     # sys.argv has to be reset for to allow get_option('debugLevel') calls, done by dprint()
        log_text = entry_prefix + "5 dprint"
        cae.dprint(log_text, minimum_debug_level=DEBUG_LEVEL_DISABLED)
        assert caplog.text.endswith(log_text + "\n")

        # final logging checks
        logging.shutdown()
        file_contents = list()
        import glob
        for log_file in glob.glob(log_file + '*'):
            with open(log_file) as fd:
                fc = fd.read()
            file_contents.append(fc)
            os.remove(log_file)     # remove log files from last test run
        assert len(file_contents) == 17
        for fc in file_contents:
            assert fc.startswith('####  ') or fc.startswith('_jb_pytest_runner ') or fc.startswith(entry_prefix) \
                or fc.startswith('  **  Additional instance') or fc == ''


class TestInternalLogFileRotation:
    """
    this test has to run first because only the first ConsoleApp instance will be able to create a log file; to
    workaround the module variable ae.console_app._ca_instance need to be reset to None before the next ConsoleApp init
    """
    def test_log_file_rotation(self, sys_argv_restore):
        log_file = 'test_internal_log_file_rot.log'
        reset_main_cae()        # ensure internal logging get enabled - even if we already created other cae instances
        cae = ConsoleApp('0.0', 'test_log_file_rotation',
                         logging_config=dict(file_name_def=log_file, file_size_max=.001))
        # no longer needed since added sys_argv_restore:
        # .. old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = []
        file_name_chk = cae.get_option('logFile')   # get_option() has to be called at least once for to create log file
        assert file_name_chk == log_file
        for i in range(MAX_NUM_LOG_FILES):
            for j in range(16):     # full loop is creating 1 kb of log entries (16 * 64 bytes)
                cae.uprint("TestLogEntry{: >26}{: >26}".format(i, j))
        cae._close_log_file()
        assert os.path.exists(log_file)
        # clean up
        os.remove(log_file)
        for i in range(MAX_NUM_LOG_FILES):
            fn, ext = os.path.splitext(log_file)
            rot_log_file = fn + "-{:0>{index_width}}".format(i+1, index_width=len(str(MAX_NUM_LOG_FILES))) + ext
            assert os.path.exists(rot_log_file)
            os.remove(rot_log_file)
        # no longer needed since added sys_argv_restore: sys.argv = old_args


class TestConsoleAppBasics:
    def test_app_name(self):
        cae = ConsoleApp('0.0', 'test_app_name')
        assert cae.app_name().startswith('test')

    def test_add_option(self):
        cae = ConsoleApp('0.0', 'test_add_option')
        cae.add_option('test_opt', 'test_opt_description', 'test_opt_value', short_opt='')

    def test_set_option(self):
        cae = ConsoleApp('0.0', 'test_set_option')
        cae.add_option('test_opt', 'test_opt_description', 'test_init_value')
        cae.set_option('test_opt', 'test_val', save_to_config=False)

    def test_add_parameter(self):
        cae = ConsoleApp('0.0', 'test_add_parameter')
        cae.add_parameter('test_arg')

    def test_get_parameter(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_add_parameter')
        cae.add_parameter('test_arg')
        arg_val = 'test_arg_val'
        sys.argv = ['test_app', arg_val]
        assert cae.get_parameter('test_arg') == arg_val

    def test_show_help(self):
        cae = ConsoleApp('0.0', 'test_add_parameter')
        cae.show_help()

    def test_sys_env_id(self, capsys):
        sei = 'TST'
        cae = ConsoleApp('0.0', 'test_add_parameter', sys_env_id=sei)
        assert cae.sys_env_id == sei
        cae.uprint(sei)     # increase coverage
        out, err = capsys.readouterr()
        assert sei in out or out == ''       # TODO: out is empty string

    def test_shutdown(self):
        import gc
        gc.disable()

        cae = ConsoleApp('0.0', 'test_app_name')  # pytest freezes in debug run with kwarg: , multi_threading=True)
        cae.shutdown(-69)

        # noinspection PyShadowingNames
        _ca_instance = cae
        del cae
        del _ca_instance        # TODO: this line should invoke _ca_instance.__del__() and .shutdown(0), BUT DOESN'T
        gc.collect()


class TestConfigOptions:
    def test_set_config_basics(self, sys_argv_restore, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(file_name='test.ini')

        cae = ConsoleApp('0.0', 'test_set_config_basics')
        cae.add_option(var_name, 'test_config_basics', 'init_test_val', short_opt='')
        opt_test_val = 'opt_test_val'
        sys.argv = ['test', '-t=' + opt_test_val]
        assert cae.get_option(var_name) == opt_test_val

        val = 'test_value'
        assert not cae.set_config(var_name, val)
        assert cae.get_config(var_name) == val

        val = ('test_val1', 'test_val2')
        assert not cae.set_config(var_name, val)
        assert cae.get_config(var_name) == repr(val)

        val = datetime.datetime.now()
        assert not cae.set_config(var_name, val)
        assert cae.get_config(var_name) == val.strftime(DATE_TIME_ISO)

        val = datetime.date.today()
        assert not cae.set_config(var_name, val)
        assert cae.get_config(var_name) == val.strftime(DATE_ISO)

    def test_set_config_without_ini(self, sys_argv_restore):
        var_name = 'test_config_var'
        cae = ConsoleApp('0.0', 'test_set_config_without_ini')
        cae.add_option(var_name, 'test_set_config_without_ini', 'init_test_val', short_opt='t')
        opt_test_val = 'opt_test_val'
        sys.argv = ['test', '-t=' + opt_test_val]
        assert cae.get_option(var_name) == opt_test_val

        val = 'test_value'
        assert cae.set_config(var_name, val)        # will be set, but returning error because test.ini does not exist
        assert cae.get_config(var_name) == val

        val = ('test_val1', 'test_val2')
        assert cae.set_config(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_config(var_name) == repr(val)

        val = datetime.datetime.now()
        assert cae.set_config(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_config(var_name) == val.strftime(DATE_TIME_ISO)

        val = datetime.date.today()
        assert cae.set_config(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_config(var_name) == val.strftime(DATE_ISO)

    def test_set_config_error(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('0.0', 'test_set_config_with_reload', additional_cfg_files=[file_name])
        val = 'test_value'

        assert cae.set_config(var_name, val, cfg_fnam=os.path.join(os.getcwd(), 'not_existing.ini'))
        with open(file_name, 'w'):      # open to lock file - so next set_config will fail
            assert cae.set_config(var_name, val)

        # new instance with not-existing additional config file
        file_name = 'invalid.ini'
        cae = ConsoleApp('0.0', 'test_set_config_with_reload', additional_cfg_files=[file_name])
        assert not [f for f in cae._config_files if f.endswith(file_name)]

    def test_set_config_with_reload(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('0.0', 'test_set_config_with_reload', additional_cfg_files=[file_name])
        val = 'test_value'
        assert not cae.set_config(var_name, val, cfg_fnam=file_name)

        cfg_val = cae.get_config(var_name)
        assert cfg_val == val

        cae.config_load()
        cfg_val = cae.get_config(var_name)
        assert cfg_val == val

    def test_multiple_option_single_char(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_multiple_option')
        sys.argv = ['test', "-Z=a", "-Z=1"]
        cae.add_option('testMultipleOptionSC', 'test multiple option', [], 'Z', multiple=True)
        assert cae.get_option('testMultipleOptionSC') == ['a', '1']

    def test_multiple_option_multi_char(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_multiple_option_multi_char')
        sys.argv = ['test', "-Z=abc", "-Z=123"]
        cae.add_option('testMultipleOptionMC', 'test multiple option', [], short_opt='Z', multiple=True)
        assert cae.get_option('testMultipleOptionMC') == ['abc', '123']

    def test_multiple_option_multi_values_fail(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_multiple_option_multi_val')
        sys.argv = ['test', "-Z", "abc", "123"]
        cae.add_option('testMultipleOptionMV', 'test multiple option', [], short_opt='Z', multiple=True)
        with pytest.raises(SystemExit):
            cae.get_option('testMultipleOptionMV')

    def test_multiple_option_single_char_with_choices(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_multiple_option_with_choices')
        sys.argv = ['test', "-Z=a", "-Z=1"]
        cae.add_option('testAppOptChoicesSCWC', 'test multiple choices', [], 'Z', choices=['a', '1'], multiple=True)
        assert cae.get_option('testAppOptChoicesSCWC') == ['a', '1']

    def test_multiple_option_single_char_fail_with_invalid_choices(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_multiple_option_with_choices')
        sys.argv = ['test', "-Z=x", "-Z=9"]
        cae.add_option('testAppOptChoices', 'test multiple choices', [], 'Z', choices=['a', '1'], multiple=True)
        with pytest.raises(ArgumentError):
            cae.get_option('testAppOptChoices')     # == ['x', '9'] but choices is ['a', '1']

    def test_config_default_bool(self):
        cae = ConsoleApp('0.0', 'test_config_defaults')
        cfg_val = cae.get_config('not_existing_config_var', default_value=False)
        assert cfg_val is False
        cfg_val = cae.get_config('not_existing_config_var2', value_type=bool)
        assert cfg_val is False

    def test_long_option_str_value(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_long_option_str_value')
        opt_val = 'testString'
        sys.argv = ['test', '--testStringOption=' + opt_val]
        cae.add_option('testStringOption', 'test long option', '', 'Z')
        assert cae.get_option('testStringOption') == opt_val

    def test_short_option_str_value(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_str_value')
        opt_val = 'testString'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testStringOption', 'test short option', '', 'Z')
        assert cae.get_option('testStringOption') == opt_val

    def test_short_option_str_eval(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_str_eval')
        opt_val = 'testString'
        sys.argv = ['test', '-Z=""""' + opt_val + '""""']
        cae.add_option('testString2Option', 'test str eval short option', '', 'Z')
        assert cae.get_option('testString2Option') == opt_val

    def test_short_option_bool_str(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        opt_val = 'False'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool str option', True, 'Z')
        assert cae.get_option('testBoolOption') is False

    def test_short_option_bool_number(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        opt_val = '0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool number option', True, 'Z')
        assert cae.get_option('testBoolOption') is False

    def test_short_option_bool_number_true(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        opt_val = '1'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool number option', False, 'Z')
        assert cae.get_option('testBoolOption') is True

    def test_short_option_bool_eval(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        opt_val = '"""0 == 1"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool eval option', True, 'Z')
        assert cae.get_option('testBoolOption') is False

    def test_short_option_bool_eval_true(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        opt_val = '"""9 == 9"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool eval option', False, 'Z')
        assert cae.get_option('testBoolOption') is True

    def test_short_option_date_str(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_date_str')
        opt_val = '2016-12-24'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testDateOption', 'test date str option', datetime.date.today(), 'Z')
        assert cae.get_option('testDateOption') == datetime.date(year=2016, month=12, day=24)

    def test_short_option_datetime_str(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_datetime_str')
        opt_val = '2016-12-24 7:8:0.0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testDatetimeOption', 'test datetime str option', datetime.datetime.now(), 'Z')
        assert cae.get_option('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)

    def test_short_option_date_eval(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_date_eval')
        sys.argv = ['test', '-Z="""datetime.date(year=2016, month=12, day=24)"""']
        cae.add_option('testDateOption', 'test date eval test option', datetime.date.today(), 'Z')
        assert cae.get_option('testDateOption') == datetime.date(year=2016, month=12, day=24)

    def test_short_option_datetime_eval(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_datetime_eval')
        sys.argv = ['test', '-Z="""datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)"""']
        cae.add_option('testDatetimeOption', 'test datetime eval test option', datetime.datetime.now(), 'Z')
        assert cae.get_option('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)

    def test_short_option_list_str(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_list_str')
        opt_val = [1, 2, 3]
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testListStrOption', 'test list str option', [], 'Z')
        assert cae.get_option('testListStrOption') == opt_val

    def test_short_option_list_eval(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_list_eval')
        sys.argv = ['test', '-Z="""[1, 2, 3]"""']
        cae.add_option('testListEvalOption', 'test list eval option', [], 'Z')
        assert cae.get_option('testListEvalOption') == [1, 2, 3]

    def test_short_option_dict_str(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_dict_str')
        opt_val = {'a': 1, 'b': 2, 'c': 3}
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testDictStrOption', 'test list str option', {}, 'Z')
        assert cae.get_option('testDictStrOption') == opt_val

    def test_short_option_dict_eval(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_dict_eval')
        sys.argv = ['test', "-Z='''{'a': 1, 'b': 2, 'c': 3}'''"]
        cae.add_option('testDictEvalOption', 'test dict eval option', {}, 'Z')
        assert cae.get_option('testDictEvalOption') == {'a': 1, 'b': 2, 'c': 3}

    def test_short_option_tuple_str(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_tuple_str')
        opt_val = ('a', 'b', 'c')
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testTupleStrOption', 'test tuple str option', (), 'Z')
        assert cae.get_option('testTupleStrOption') == opt_val

    def test_short_option_tuple_eval(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_option_tuple_eval')
        sys.argv = ['test', "-Z='''('a', 'b', 'c')'''"]
        cae.add_option('testDictEvalOption', 'test tuple eval option', (), 'Z')
        assert cae.get_option('testDictEvalOption') == ('a', 'b', 'c')

    def test_config_str_eval_single_quote(self, config_fna_vna_vva):
        opt_val = 'testString'
        file_name, var_name, _ = config_fna_vna_vva(var_value="''''" + opt_val + "''''")
        cae = ConsoleApp('0.0', 'test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == opt_val

    def test_config_str_eval_double_quote(self, config_fna_vna_vva):
        opt_val = 'testString'
        file_name, var_name, _ = config_fna_vna_vva(var_value='""""' + opt_val + '""""')
        cae = ConsoleApp('0.0', 'test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == opt_val

    def test_config_bool_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='True')
        cae = ConsoleApp('0.0', 'test_config_bool_str', additional_cfg_files=[file_name])
        assert cae.get_config(var_name, value_type=bool) is True

    def test_config_bool_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""1 == 0"""')
        cae = ConsoleApp('0.0', 'test_config_bool_eval', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) is False

    def test_config_bool_eval_true(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""6 == 6"""')
        cae = ConsoleApp('0.0', 'test_config_bool_eval', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) is True

    def test_config_date_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='2012-12-24')
        cae = ConsoleApp('0.0', 'test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_config(var_name, value_type=datetime.date) == datetime.date(year=2012, month=12, day=24)

    def test_config_date_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""datetime.date(year=2012, month=12, day=24)"""')
        cae = ConsoleApp('0.0', 'test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == datetime.date(year=2012, month=12, day=24)

    def test_config_datetime_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='2012-12-24 7:8:0.0')
        cae = ConsoleApp('0.0', 'test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_config(var_name, value_type=datetime.datetime) \
            == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)

    def test_config_datetime_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(
            var_value='"""datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)"""')
        cae = ConsoleApp('0.0', 'test_config_datetime_eval', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)

    def test_config_list_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='[1, 2, 3]')
        cae = ConsoleApp('0.0', 'test_config_list_str', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == [1, 2, 3]

    def test_config_list_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""[1, 2, 3]"""')
        cae = ConsoleApp('0.0', 'test_config_list_eval', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == [1, 2, 3]

    def test_config_dict_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value="{'a': 1, 'b': 2, 'c': 3}")
        cae = ConsoleApp('0.0', 'test_config_dict_str', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == {'a': 1, 'b': 2, 'c': 3}

    def test_config_dict_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""{"a": 1, "b": 2, "c": 3}"""')
        cae = ConsoleApp('0.0', 'test_config_dict_eval', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == {'a': 1, 'b': 2, 'c': 3}

    def test_config_tuple_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value="('a', 'b', 'c')")
        cae = ConsoleApp('0.0', 'test_config_tuple_str', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == ('a', 'b', 'c')

    def test_config_tuple_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""("a", "b", "c")"""')
        cae = ConsoleApp('0.0', 'test_config_tuple_eval', additional_cfg_files=[file_name])
        assert cae.get_config(var_name) == ('a', 'b', 'c')

    def test_debug_level_short_option_value(self, sys_argv_restore):
        cae = ConsoleApp('0.1', 'test_option_value')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_TIMESTAMPED)]
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_long_option_value(self, sys_argv_restore):
        cae = ConsoleApp('0.1', 'test_option_value')
        sys.argv = ['test', '--debugLevel=' + str(DEBUG_LEVEL_TIMESTAMPED)]
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_short_option_eval_single_quoted(self, sys_argv_restore):
        cae = ConsoleApp('0.1', 'test_option_eval')
        sys.argv = ["test", "-D='''int('" + str(DEBUG_LEVEL_TIMESTAMPED) + "')'''"]
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_short_option_eval_double_quoted(self):
        cae = ConsoleApp('0.1', 'test_option_eval')
        sys.argv = ['test', '-D="""int("' + str(DEBUG_LEVEL_TIMESTAMPED) + '")"""']
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_add_option_default(self, sys_argv_restore):
        cae = ConsoleApp('0.1', 'test_add_option_default', debug_level_def=DEBUG_LEVEL_TIMESTAMPED)
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_config_default(self, sys_argv_restore, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debugLevel', var_value=str(DEBUG_LEVEL_TIMESTAMPED))
        cae = ConsoleApp('0.2', 'test_config_default', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_option(var_name) == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_config_eval_single_quote(self, sys_argv_restore, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debugLevel',
                                                    var_value="'''int('" + str(DEBUG_LEVEL_TIMESTAMPED) + "')'''")
        cae = ConsoleApp('0.3', 'test_config_eval', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_option(var_name) == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_config_eval_double_quote(self, sys_argv_restore, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debugLevel',
                                                    var_value='"""int("' + str(DEBUG_LEVEL_TIMESTAMPED) + '")"""')
        cae = ConsoleApp('0.3', 'test_config_eval', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_option(var_name) == DEBUG_LEVEL_TIMESTAMPED


class TestIllegalXmlChars:
    def test_xml_char1(self):
        illegal_char = chr(1)       # '&#1;'
        xml = "test xml string with " + illegal_char + " character"
        test_xml = ILLEGAL_XML_SUB.sub('_', xml)
        assert test_xml == xml.replace(illegal_char, '_')


class TestFullStackTrace:
    def test_full_stack_trace(self):
        try:
            raise ValueError
        except ValueError as ex:
            # print(full_stack_trace(ex))
            assert full_stack_trace(ex)


class TestProgress:
    def test_init_start_msg(self):
        msg = 'msg_text'
        cae = ConsoleApp('0.0', 'test_progress_init')
        progress = Progress(cae, total_count=1, start_msg=msg, nothing_to_do_msg=msg)
        progress.finished(error_msg='t_err_msg')

    def test_init_nothing_to_do(self):
        msg = 'msg_text'
        cae = ConsoleApp('0.0', 'test_progress_init')
        progress = Progress(cae, nothing_to_do_msg=msg)
        progress.next(error_msg='test_error_msg')


class TestNamedLocks:
    def test_sequential(self):
        nl = NamedLocks()
        assert len(nl.active_lock_counters) == 0
        nl2 = NamedLocks()
        assert len(nl2.active_lock_counters) == 0

        assert nl.acquire('test', timeout=0.01)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1
        assert len(nl2.active_lock_counters) == 1 and nl2.active_lock_counters['test'] == 1

        nl.release('test')
        assert len(nl.active_lock_counters) == 0
        assert len(nl2.active_lock_counters) == 0

        assert nl2.acquire('test', timeout=.01)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1
        assert len(nl2.active_lock_counters) == 1 and nl2.active_lock_counters['test'] == 1

        nl2.release('test')
        assert len(nl.active_lock_counters) == 0
        assert len(nl2.active_lock_counters) == 0

    def test_locking_with_timeout(self):
        nl = NamedLocks(reentrant_locks=False)
        assert nl.acquire('test', timeout=0.01)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2 = NamedLocks(reentrant_locks=False)
        assert not nl2.acquire('test', timeout=.01)
        assert len(nl2.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl.release('test')
        assert len(nl2.active_lock_counters) == 0
        assert nl2.acquire('test', timeout=.01)
        assert len(nl2.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2.release('test')
        assert len(nl2.active_lock_counters) == 0

    def test_reentrant_locking_with_timeout(self):
        nl = NamedLocks()
        assert nl.acquire('test', timeout=0.01)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2 = NamedLocks()
        assert nl2.acquire('test', timeout=.01)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 2

        nl.release('test')
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2.release('test')
        assert len(nl2.active_lock_counters) == 0

        assert nl2.acquire('test', timeout=.01)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2.release('test')
        assert len(nl.active_lock_counters) == 0

    def test_non_blocking_args(self):
        nl = NamedLocks(reentrant_locks=False)
        assert nl.acquire('test')
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2 = NamedLocks(reentrant_locks=False)
        assert nl2.acquire('otherTest')
        assert len(nl.active_lock_counters) == 2 and nl.active_lock_counters['test'] == 1 \
            and nl.active_lock_counters['otherTest'] == 1

        nl2.release('otherTest')
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        assert not nl2.acquire('test', blocking=False)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        assert not nl2.acquire('test', False)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        assert not nl2.acquire('test', timeout=.01)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl.release('test')
        assert len(nl2.active_lock_counters) == 0

        assert nl2.acquire('test', blocking=False)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2.release('test')
        assert len(nl2.active_lock_counters) == 0

    def test_reentrant_non_blocking_args(self):
        nl = NamedLocks()
        assert nl.acquire('test')
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2 = NamedLocks()
        assert nl2.acquire('otherTest')
        assert len(nl.active_lock_counters) == 2 and nl.active_lock_counters['test'] == 1 \
            and nl.active_lock_counters['otherTest'] == 1
        nl2.release('otherTest')

        assert nl2.acquire('test', blocking=False)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 2

        assert nl2.acquire('test', False)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 3

        assert nl2.acquire('test', timeout=.01)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 4

        nl.release('test')
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 3

        nl.release('test')
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 2

        nl.release('test')
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl.release('test')
        assert len(nl2.active_lock_counters) == 0

        assert nl2.acquire('test', blocking=False)
        assert len(nl.active_lock_counters) == 1 and nl.active_lock_counters['test'] == 1

        nl2.release('test')
        assert len(nl2.active_lock_counters) == 0

    def test_with_context_with(self):
        with NamedLocks('test'):
            pass

    def test_error_context(self):
        with NamedLocks('test2') as nl:
            nl.release('test2')

        with NamedLocks('test3') as nl:
            assert 'test3' in nl.active_locks
            assert nl.active_locks.pop('test3')


class TestConfigMainFileModified:
    def test_not_modified(self, config_fna_vna_vva):
        config_fna_vna_vva(
            file_name=os.path.join(os.getcwd(), os.path.splitext(os.path.basename(sys.argv[0]))[0] + INI_EXT))
        cae = ConsoleApp('0.0', 'test_config_modified_after_startup')
        assert not cae.config_main_file_modified()

    def test_modified(self, config_fna_vna_vva):
        file_name, var_name, old_var_val = config_fna_vna_vva(
            file_name=os.path.join(os.getcwd(), os.path.splitext(os.path.basename(sys.argv[0]))[0] + INI_EXT))
        cae = ConsoleApp('0.0', 'test_set_config_with_reload')
        time.sleep(.300)    # needed because Python is too quick sometimes
        new_var_val = 'NEW_test_value'
        assert not cae.set_config(var_name, new_var_val)
        assert cae.config_main_file_modified()

        # cfg_val has still old value (OtherTestValue) because parser instance got not reloaded
        cfg_val = cae.get_config(var_name)
        assert cfg_val == old_var_val
        assert cfg_val != new_var_val
        assert cae.config_main_file_modified()

        cae.config_load()
        cfg_val = cae.get_config(var_name)
        assert cfg_val == new_var_val

        assert not cae.config_main_file_modified()


class TestSetting:
    def test_init(self):
        s = Setting()
        assert s.value is None

        s = Setting(value='test_val')
        assert isinstance(s.value, str)
        assert s.value == 'test_val'

    def test_bool_values(self):
        bs = 'True'
        s = Setting(value=bs, value_type=bool)
        assert isinstance(s.value, bool)
        assert s.value is True

        bn = 1
        s = Setting(value=bn, value_type=bool)
        assert isinstance(s.value, bool)
        assert s.value is True

    def test_byte_values(self):
        bs = b'TEST'
        s = Setting(value=bs)
        assert isinstance(s.value, bytes)
        assert s.value == bs

        s = Setting(value=bs, value_type=str)
        assert isinstance(s.value, str)
        assert s.value == 'TEST'

    def test_date_values(self):
        ds = '2020-12-24'
        s = Setting(value=ds, value_type=datetime.date)
        assert isinstance(s.value, datetime.date)
        assert s.value == datetime.datetime.strptime(ds, DATE_ISO).date()

        dts = datetime.datetime.now().strftime(DATE_TIME_ISO)
        s = Setting(value=dts, value_type=datetime.datetime)
        assert isinstance(s.value, datetime.datetime)
        assert s.value == datetime.datetime.strptime(dts, DATE_TIME_ISO)


class TestDuplicateSysOut:
    def test_init(self):
        lfn = 'log_file.log'
        lfo = open(lfn, 'w')
        dso = _DuplicateSysOut(lfo)
        assert dso.log_file == lfo
        assert dso.sys_out is sys.stdout

        dso = _DuplicateSysOut(lfo, sys_out=sys.stdout)
        assert dso.log_file == lfo
        assert dso.sys_out is sys.stdout

        dso = _DuplicateSysOut(lfo, sys_out=sys.stderr)
        assert dso.log_file == lfo
        assert dso.sys_out is sys.stderr

        lfo.close()
        assert os.path.exists(lfn)
        os.remove(lfn)

    def test_flush_method_exists(self):
        lfn = 'log_file.log'
        lfo = open(lfn, 'w')
        dso = _DuplicateSysOut(lfo)
        assert hasattr(dso, 'flush')
        assert callable(dso.flush)

        lfo.close()
        assert os.path.exists(lfn)
        os.remove(lfn)

    def test_write(self):
        lfn = 'log_file.log'
        lfo = open(lfn, 'w')
        dso = _DuplicateSysOut(lfo)
        msg = 'test_message'
        dso.write(msg)
        lfo.close()
        with open(lfn) as f:
            assert f.read() == msg

        lfn = 'log_file.log'
        lfo = open(lfn, 'w', encoding='utf-8')
        dso = _DuplicateSysOut(lfo)
        msg = chr(40960) + chr(1972)
        dso.write(msg)
        lfo.close()
        with open(lfn, encoding='utf-8') as f:
            assert f.read() == msg

        lfn = 'log_file.log'
        lfo = open(lfn, 'w')
        dso = _DuplicateSysOut(lfo)
        msg = chr(40960) + chr(1972)
        dso.write(msg)
        lfo.close()
        with open(lfn) as f:
            assert f.read() == '\\ua000\\u07b4'

        lfn = 'log_file.log'
        lfo = open(lfn, 'w', encoding='ascii')
        dso = _DuplicateSysOut(lfo)
        msg = chr(40960) + chr(1972)
        dso.write(msg)
        lfo.close()
        with open(lfn, encoding='ascii') as f:
            assert f.read() == '\\ua000\\u07b4'

        assert os.path.exists(lfn)
        os.remove(lfn)
