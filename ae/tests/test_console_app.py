# import pytest
import sys
import os
import datetime
import time
import logging
from argparse import ArgumentError

import pytest

from sys_data_ids import DEBUG_LEVEL_TIMESTAMPED, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE
from ae.console_app import (ConsoleApp, fix_encoding, round_traditional, reset_main_cae, sys_env_dict, to_ascii,
                            Progress, NamedLocks, full_stack_trace,
                            ILLEGAL_XML_SUB, MAX_NUM_LOG_FILES, INI_EXT, calling_module, DATE_TIME_ISO, DATE_ISO)


class TestHelpers:
    def test_round_traditional(self):
        assert round_traditional(1.01) == 1
        assert round_traditional(10.1, -1) == 10
        assert round_traditional(1.123, 1) == 1.1
        assert round_traditional(0.5) == 1
        assert round_traditional(0.5001, 1) == 0.5

        assert round_traditional(0.075, 2) == 0.08
        assert round(0.075, 2) == 0.07

    def test_fix_encoding_umlaut(self, capsys, sys_argv_restore):
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
        # STRANGE: capsys/capfd don't show uprint output - although it is shown in the pytest log/console
        assert out.startswith('ae.console_app.fix_encoding()') or out == ''

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
        assert calling_module()
        assert calling_module(called_module=__name__)
        assert calling_module('')
        assert calling_module('xxx_test')


class TestPythonLogging:
    def test_logging_config_dict_basic_from_ini(self):
        file_name = os.path.join(os.getcwd(), 'test_conf.ini')
        var_name = 'py_logging_config_dict'
        var_val = dict(version=1, disable_existing_loggers=False)
        with open(file_name, 'w') as f:
            f.write('[Settings]\n' + var_name + ' = ' + str(var_val))

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict_basic_from_ini', additional_cfg_files=[file_name])

        cfg_val = cae.get_config(var_name)
        assert cfg_val == var_val

        assert cae.logging_conf_dict == var_val

        os.remove(file_name)
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

    def test_shutdown(self):
        cae = ConsoleApp('0.0', 'test_app_name', multi_threading=True)
        cae.shutdown(-69)


class TestConfigOptions:
    def test_set_config_basics(self, sys_argv_restore):
        file_name = os.path.join(os.getcwd(), 'test.ini')
        var_name = 'test_config_var'
        with open(file_name, 'w') as f:
            f.write('[Settings]\n' + var_name + ' = InitialTestValue')
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

        os.remove(file_name)

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

    def test_set_config_error(self):
        file_name = os.path.join(os.getcwd(), 'test_config.ini')
        var_name = 'test_config_var'
        cae = ConsoleApp('0.0', 'test_set_config_with_reload', additional_cfg_files=[file_name])
        val = 'test_value'
        assert cae.set_config(var_name, val)

    def test_set_config_with_reload(self):
        file_name = os.path.join(os.getcwd(), 'test_config.ini')
        var_name = 'test_config_var'
        with open(file_name, 'w') as f:
            f.write('[Settings]\n' + var_name + ' = OtherTestValue')
        cae = ConsoleApp('0.0', 'test_set_config_with_reload', additional_cfg_files=[file_name])
        val = 'test_value'
        assert not cae.set_config(var_name, val)

        cfg_val = cae.get_config(var_name)
        assert cfg_val != val

        cae.config_load()
        cfg_val = cae.get_config(var_name)
        assert cfg_val == val

        os.remove(file_name)

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

    def test_config_str_eval_single_quote(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        opt_val = 'testString'
        with open(file_name, 'w') as f:
            f.write("[Settings]\ntestStringConfig = ''''" + opt_val + "''''")
        cae = ConsoleApp('0.0', 'test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testStringConfig') == opt_val
        os.remove(file_name)

    def test_config_str_eval_double_quote(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        opt_val = 'testString'
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestStringConfig2 = """"' + opt_val + '""""')
        cae = ConsoleApp('0.0', 'test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testStringConfig2') == opt_val
        os.remove(file_name)

    def test_config_bool_str(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestBool = True')
        cae = ConsoleApp('0.0', 'test_config_bool_str', additional_cfg_files=[file_name])
        assert cae.get_config('testBool', value_type=bool) is True
        os.remove(file_name)

    def test_config_bool_eval(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestBool = """1 == 0"""')
        cae = ConsoleApp('0.0', 'test_config_bool_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testBool') is False
        os.remove(file_name)

    def test_config_bool_eval_true(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestBool = """6 == 6"""')
        cae = ConsoleApp('0.0', 'test_config_bool_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testBool') is True
        os.remove(file_name)

    def test_config_date_str(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestDate = 2012-12-24')
        cae = ConsoleApp('0.0', 'test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_config('testDate', value_type=datetime.date) == datetime.date(year=2012, month=12, day=24)
        os.remove(file_name)

    def test_config_date_eval(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestDate = """datetime.date(year=2012, month=12, day=24)"""')
        cae = ConsoleApp('0.0', 'test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_config('testDate') == datetime.date(year=2012, month=12, day=24)
        os.remove(file_name)

    def test_config_datetime_str(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestDatetime = 2012-12-24 7:8:0.0')
        cae = ConsoleApp('0.0', 'test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_config('testDatetime', value_type=datetime.datetime) \
            == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)
        os.remove(file_name)

    def test_config_datetime_eval(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestDatetime = """datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)"""')
        cae = ConsoleApp('0.0', 'test_config_datetime_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testDatetime') == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)
        os.remove(file_name)

    def test_config_list_str(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestListStr = [1, 2, 3]')
        cae = ConsoleApp('0.0', 'test_config_list_str', additional_cfg_files=[file_name])
        assert cae.get_config('testListStr') == [1, 2, 3]
        os.remove(file_name)

    def test_config_list_eval(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestListEval = """[1, 2, 3]"""')
        cae = ConsoleApp('0.0', 'test_config_list_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testListEval') == [1, 2, 3]
        os.remove(file_name)

    def test_config_dict_str(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write("[Settings]\ntestDictStr = {'a': 1, 'b': 2, 'c': 3}")
        cae = ConsoleApp('0.0', 'test_config_dict_str', additional_cfg_files=[file_name])
        assert cae.get_config('testDictStr') == {'a': 1, 'b': 2, 'c': 3}
        os.remove(file_name)

    def test_config_dict_eval(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestDictEval = """{"a": 1, "b": 2, "c": 3}"""')
        cae = ConsoleApp('0.0', 'test_config_dict_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testDictEval') == {'a': 1, 'b': 2, 'c': 3}
        os.remove(file_name)

    def test_config_tuple_str(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write("[Settings]\ntestTupleStr = ('a', 'b', 'c')")
        cae = ConsoleApp('0.0', 'test_config_tuple_str', additional_cfg_files=[file_name])
        assert cae.get_config('testTupleStr') == ('a', 'b', 'c')
        os.remove(file_name)

    def test_config_tuple_eval(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestTupleEval = """("a", "b", "c")"""')
        cae = ConsoleApp('0.0', 'test_config_tuple_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testTupleEval') == ('a', 'b', 'c')
        os.remove(file_name)

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

    def test_debug_level_config_default(self, sys_argv_restore):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ndebugLevel = ' + str(DEBUG_LEVEL_TIMESTAMPED))
        cae = ConsoleApp('0.2', 'test_config_default', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        os.remove(file_name)

    def test_debug_level_config_eval_single_quote(self, sys_argv_restore):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write("[Settings]\ndebugLevel = '''int('" + str(DEBUG_LEVEL_TIMESTAMPED) + "')'''")
        cae = ConsoleApp('0.3', 'test_config_eval', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        os.remove(file_name)

    def test_debug_level_config_eval_double_quote(self, sys_argv_restore):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ndebugLevel = """int("' + str(DEBUG_LEVEL_TIMESTAMPED) + '")"""')
        cae = ConsoleApp('0.3', 'test_config_eval', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        os.remove(file_name)


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
    def test_not_modified(self):
        cwd = os.getcwd()
        exe_name = sys.argv[0]
        file_name = os.path.join(cwd, os.path.splitext(os.path.basename(exe_name))[0] + INI_EXT)
        var_name = 'test_config_var'
        old_var_val = 'OtherTestValue'
        with open(file_name, 'w') as f:
            f.write('[Settings]\n' + var_name + ' = ' + old_var_val)
        cae = ConsoleApp('0.0', 'test_config_modified_after_startup')
        assert not cae.config_main_file_modified()

        os.remove(file_name)

    def test_modified(self):
        cwd = os.getcwd()
        exe_name = sys.argv[0]
        file_name = os.path.join(cwd, os.path.splitext(os.path.basename(exe_name))[0] + INI_EXT)
        var_name = 'test_config_var'
        old_var_val = 'OtherTestValue'
        with open(file_name, 'w') as f:
            f.write('[Settings]\n' + var_name + ' = ' + old_var_val)
        cae = ConsoleApp('0.0', 'test_set_config_with_reload')
        time.sleep(.300)    # needed because Python is too quick sometimes
        new_var_val = 'test_value'
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

        os.remove(file_name)
