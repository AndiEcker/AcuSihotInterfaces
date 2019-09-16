# TODO: remove " or out == ''" as soon as capsys bug is fixed
from typing import cast

import pytest

import sys
import os
import datetime
import glob
import time
import logging
import threading

from argparse import ArgumentError

from ae.core import (
    DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_TIMESTAMPED, DATE_TIME_ISO, DATE_ISO, INI_EXT, MAX_NUM_LOG_FILES, _app_instances)
from ae.console_app import ConsoleApp


main_cae_instance = None


class TestAeLogging:
    def test_log_file_rotation(self, sys_argv_restore):
        """ this test has to run first because only the 1st ConsoleApp instance can create an ae log file
        """
        global main_cae_instance
        log_file = 'test_ae_log.log'
        cae = ConsoleApp('test_log_file_rotation',
                         multi_threading=True,
                         logging_params=dict(file_name_def=log_file, file_size_max=.001))
        main_cae_instance = cae     # keep reference to prevent garbage collection
        # no longer needed since added sys_argv_restore:
        # .. old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = []
        file_name_chk = cae.get_opt('logFile')   # get_opt() has to be called at least once for to create log file
        assert file_name_chk == log_file
        for idx in range(MAX_NUM_LOG_FILES + 9):
            for line_no in range(16):     # full loop is creating 1 kb of log entries (16 * 64 bytes)
                cae.po("TestLogEntry{: >26}{: >26}".format(idx, line_no))
        cae._close_log_file()
        assert os.path.exists(log_file)
        # clean up
        os.remove(log_file)
        for idx in range(MAX_NUM_LOG_FILES + 9):
            fn, ext = os.path.splitext(log_file)
            rot_log_file = fn + "-{:0>{index_width}}".format(idx, index_width=len(str(MAX_NUM_LOG_FILES))) + ext
            if os.path.exists(rot_log_file):
                os.remove(rot_log_file)

    def test_open_log_file_with_suppressed_stdout(self, sys_argv_restore):
        """ another test that need to work with the first instance
        """
        cae = main_cae_instance
        try:
            cae.suppress_stdout = True
            sys.argv = []
            cae._parsed_args = False
            cae._close_log_file(full_reset=True)
            _ = cae.get_opt('debugLevel')   # get_opt() has to be called at least once for to create log file
            cae._close_log_file()
            assert os.path.exists(cae._log_file_name)
        finally:
            if os.path.exists(cae._log_file_name):
                os.remove(cae._log_file_name)

    def test_invalid_log_file_name(self):
        log_file = ':/:invalid:/:'
        cae = ConsoleApp('test_invalid_log_file_name', logging_params=dict(file_name_def=log_file))
        cae.activate_ae_logging()     # only for coverage of exception

    def test_log_file_flush(self, sys_argv_restore):
        log_file = 'test_ae_log_flush.log'
        cae = ConsoleApp('test_log_file_flush', logging_params=dict(file_name_def=log_file))
        sys.argv = []
        file_name_chk = cae.get_opt('logFile')   # get_opt() has to be called at least once for to create log file
        assert file_name_chk == log_file

    def test_exception_log_file_flush(self):
        cae = ConsoleApp('test_exception_log_file_flush')
        # cause/provoke _append_eof_and_flush_file() exceptions for coverage by passing any other non-stream object
        cae._append_eof_and_flush_file(cast('TextIO', None), 'invalid stream')


class TestPythonLogging:
    """ test python logging module support
    """
    def test_logging_params_dict_basic_from_ini(self, config_fna_vna_vva):
        file_name, var_name, var_val = config_fna_vna_vva(var_name='py_logging_params',
                                                          var_value=dict(version=1,
                                                                         disable_existing_loggers=False))

        cae = ConsoleApp('test_python_logging_params_dict_basic_from_ini', additional_cfg_files=[file_name])

        cfg_val = cae.get_var(var_name)
        assert cfg_val == var_val

        assert cae.py_log_params == var_val

        logging.shutdown()

    def test_logging_params_dict_console_from_init(self):
        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.StreamHandler',
                                              'level': logging.INFO}))
        print(str(var_val))

        cae = ConsoleApp('test_python_logging_params_dict_console',
                         logging_params=dict(py_logging_params=var_val))

        assert cae.py_log_params == var_val
        logging.shutdown()

    def test_logging_params_dict_complex(self, caplog, sys_argv_restore):
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

        cae = ConsoleApp('test_python_logging_params_dict_file',
                         logging_params=dict(py_logging_params=var_val))

        assert cae.py_log_params == var_val

        root_logger = logging.getLogger()
        ae_logger = logging.getLogger('ae')
        ae_cae_logger = logging.getLogger('ae.console_app')

        # ConsoleApp print_out
        log_text = entry_prefix + "0 print_out"
        cae.po(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out root"
        cae.po(log_text, logger=root_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out ae"
        cae.po(log_text, logger=ae_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out ae_cae"
        cae.po(log_text, logger=ae_cae_logger)
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

        # ConsoleAppEnv dpo
        sys.argv = ['tl_cdc']   # sys.argv has to be reset for to allow get_opt('debugLevel') calls, done by dpo()
        log_text = entry_prefix + "5 dpo"
        cae.dpo(log_text, minimum_debug_level=DEBUG_LEVEL_DISABLED)
        assert caplog.text.endswith(log_text + "\n")

        # final checks of log file contents
        cae._close_log_file()       # does also logging.shutdown()
        file_contents = list()
        for lf in glob.glob(log_file + '*'):
            with open(lf) as fd:
                fc = fd.read()
            file_contents.append(fc)
            os.remove(lf)     # remove log files from last test run
        assert len(file_contents) >= 15     # in (15, 17) # +2 '  **  Additional instance' entries, but meanwhile 21
        for fc in file_contents:
            if fc.startswith(" <"):
                fc = fc[fc.index("> ") + 2:]  # remove thread id prefix
            if fc.startswith("{TST}"):
                fc = fc[6:]  # remove sys_env_id prefix
            assert fc.startswith('####  ') or fc.startswith('_jb_pytest_runner ') or fc.startswith(entry_prefix) \
                or fc.lower().startswith('test  v 0.0') or fc.startswith('  **  Additional instance') or fc == ''


class TestConsoleAppBasics:
    def test_app_name(self, sys_argv_restore):
        name = 'tan_cae_name'
        sys.argv = [name]
        cae = ConsoleApp()
        assert cae.app_name == name

    def test_add_opt(self):
        cae = ConsoleApp('test_add_opt')
        cae.add_opt('test_opt', 'test_opt_description', 'test_opt_value', short_opt='')

    def test_set_opt(self):
        cae = ConsoleApp('test_set_opt')
        cae.add_opt('test_opt', 'test_opt_description', 'test_init_value')
        cae.set_opt('test_opt', 'test_val', save_to_config=False)

    def test_add_argument(self):
        cae = ConsoleApp('test_add_argument')
        cae.add_argument('test_arg')

    def test_get_argument(self, sys_argv_restore):
        cae = ConsoleApp('test_get_argument')
        cae.add_argument('test_arg')
        arg_val = 'test_arg_val'
        sys.argv = ['test_app', arg_val]
        assert cae.get_argument('test_arg') == arg_val

    def test_show_help(self):
        cae = ConsoleApp('test_show_help')
        cae.show_help()

    def test_sys_env_id(self, capsys):
        sei = 'TST'
        cae = ConsoleApp('test_sys_env_id', sys_env_id=sei)
        assert cae.sys_env_id == sei
        cae.po(sei)     # increase coverage
        out, err = capsys.readouterr()
        assert sei in out or out == ''

        # special case for error code path coverage
        _app_instances[''] = ConsoleApp('test_sys_env_id_COPY')
        cae.sys_env_id = ''
        assert cae.get_opt('debugLevel') == DEBUG_LEVEL_DISABLED

    def test_shutdown_basics(self):
        def thr():
            while running:
                pass

        cae = ConsoleApp('shutdown_basics')
        cae.shutdown(exit_code=None)

        cae.multi_threading = True
        cae.shutdown(exit_code=None, timeout=0.6)       # tests freezing in debug run without timeout/thread-join

        running = True
        threading.Thread(target=thr).start()
        cae.shutdown(exit_code=None, timeout=0.6)
        running = False

    def test_shutdown_coverage(self):
        cae = ConsoleApp('shutdown_coverage')
        cae.shutdown(exit_code=None, timeout=0.9)

        cae._log_file_index = 1
        cae.shutdown(exit_code=None, timeout=0.1)

        cae._nul_std_out = open(os.devnull, 'w')
        cae.shutdown(exit_code=None, timeout=0.1)


class TestConfigOptions:
    def test_set_var_basics(self, sys_argv_restore, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(file_name='test.ini')

        opt_test_val = 'opt_test_val'
        sys.argv = ['test', '-t=' + opt_test_val]

        cae = ConsoleApp('test_set_var_basics')
        cae.add_opt(var_name, 'test_config_basics', 'init_test_val', short_opt='')
        assert cae.get_opt(var_name) == opt_test_val

        val = 'test_value'
        assert not cae.set_var(var_name, val)
        assert cae.get_var(var_name) == val

        val = ('test_val1', 'test_val2')
        assert not cae.set_var(var_name, val)
        assert cae.get_var(var_name) == repr(val)

        val = datetime.datetime.now()
        assert not cae.set_var(var_name, val)
        assert cae.get_var(var_name) == val.strftime(DATE_TIME_ISO)

        val = datetime.date.today()
        assert not cae.set_var(var_name, val)
        assert cae.get_var(var_name) == val.strftime(DATE_ISO)

    def test_set_var_without_ini(self, sys_argv_restore):
        var_name = 'test_config_var'
        cae = ConsoleApp('test_set_var_without_ini')
        cae.add_opt(var_name, 'test_set_var_without_ini', 'init_test_val', short_opt='t')
        opt_test_val = 'opt_test_val'
        sys.argv = ['test', '-t=' + opt_test_val]
        assert cae.get_opt(var_name) == opt_test_val

        val = 'test_value'
        assert cae.set_var(var_name, val)        # will be set, but returning error because test.ini does not exist
        assert cae.get_var(var_name) == val

        val = ('test_val1', 'test_val2')
        assert cae.set_var(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_var(var_name) == repr(val)

        val = datetime.datetime.now()
        assert cae.set_var(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_var(var_name) == val.strftime(DATE_TIME_ISO)

        val = datetime.date.today()
        assert cae.set_var(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_var(var_name) == val.strftime(DATE_ISO)

    def test_set_var_file_error(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_var_file_error', additional_cfg_files=[file_name])
        val = 'test_value'

        assert cae.set_var(var_name, val, cfg_fnam=os.path.join(os.getcwd(), 'not_existing.ini'))
        with open(file_name, 'w'):      # open to lock file - so next set_var() will fail
            assert cae.set_var(var_name, val, cfg_fnam=file_name)

        # new instance with not-existing additional config file
        file_name = 'invalid.ini'
        cae = ConsoleApp('test_set_var_with_reload', additional_cfg_files=[file_name])
        assert not [f for f in cae._cfg_files if f.endswith(file_name)]

    def test_set_var_with_reload(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_var_with_reload', additional_cfg_files=[file_name])
        val = 'test_value'
        assert not cae.set_var(var_name, val, cfg_fnam=file_name)

        cfg_val = cae.get_var(var_name)
        assert cfg_val == val

        cae.load_cfg_files()
        cfg_val = cae.get_var(var_name)
        assert cfg_val == val

    def test_multiple_option_single_char(self, sys_argv_restore):
        cae = ConsoleApp('test_multiple_option')
        sys.argv = ['test', "-Z=a", "-Z=1"]
        cae.add_opt('testMultipleOptionSC', 'test multiple option', [], 'Z', multiple=True)
        assert cae.get_opt('testMultipleOptionSC') == ['a', '1']

    def test_multiple_option_multi_char(self, sys_argv_restore):
        cae = ConsoleApp('test_multiple_option_multi_char')
        sys.argv = ['test', "-Z=abc", "-Z=123"]
        cae.add_opt('testMultipleOptionMC', 'test multiple option', [], short_opt='Z', multiple=True)
        assert cae.get_opt('testMultipleOptionMC') == ['abc', '123']

    def test_multiple_option_multi_values_fail(self, sys_argv_restore):
        cae = ConsoleApp('test_multiple_option_multi_val')
        sys.argv = ['test', "-Z", "abc", "123"]
        cae.add_opt('testMultipleOptionMV', 'test multiple option', [], short_opt='Z', multiple=True)
        with pytest.raises(SystemExit):
            cae.get_opt('testMultipleOptionMV')

    def test_multiple_option_single_char_with_choices(self, sys_argv_restore):
        cae = ConsoleApp('test_multiple_option_with_choices')
        sys.argv = ['test', "-Z=a", "-Z=1"]
        cae.add_opt('testAppOptChoicesSCWC', 'test multiple choices', [], 'Z', choices=['a', '1'], multiple=True)
        assert cae.get_opt('testAppOptChoicesSCWC') == ['a', '1']

    def test_multiple_option_stripped_value_with_choices(self, sys_argv_restore):
        cae = ConsoleApp('test_multiple_option_stripped_with_choices', cfg_opt_val_stripper=lambda v: v[-1])
        sys.argv = ['test', "-Z=x6", "-Z=yyy9"]
        cae.add_opt('testAppOptChoicesSVWC', 'test multiple choices', [], 'Z', choices=['6', '9'], multiple=True)
        assert cae.get_opt('testAppOptChoicesSVWC') == ['x6', 'yyy9']

    def test_multiple_option_single_char_fail_with_invalid_choices(self, sys_argv_restore):
        cae = ConsoleApp('test_multiple_option_fail_with_choices')
        sys.argv = ['test', "-Z=x", "-Z=9"]
        cae.add_opt('testAppOptChoices', 'test multiple choices', [], 'Z', choices=['a', '1'], multiple=True)
        with pytest.raises(ArgumentError):
            cae.get_opt('testAppOptChoices')     # == ['x', '9'] but choices is ['a', '1']

    def test_config_default_bool(self):
        cae = ConsoleApp('test_config_defaults')
        cfg_val = cae.get_var('not_existing_config_var', default_value=False)
        assert cfg_val is False
        cfg_val = cae.get_var('not_existing_config_var2', value_type=bool)
        assert cfg_val is False

    def test_long_option_str_value(self, sys_argv_restore):
        cae = ConsoleApp('test_long_option_str_value')
        opt_val = 'testString'
        sys.argv = ['test', '--testStringOption=' + opt_val]
        cae.add_opt('testStringOption', 'test long option', '', 'Z')
        assert cae.get_opt('testStringOption') == opt_val

    def test_short_option_str_value(self, sys_argv_restore):
        cae = ConsoleApp('test_option_str_value')
        opt_val = 'testString'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testStringOption', 'test short option', '', 'Z')
        assert cae.get_opt('testStringOption') == opt_val

    def test_short_option_str_eval(self, sys_argv_restore):
        cae = ConsoleApp('test_option_str_eval')
        opt_val = 'testString'
        sys.argv = ['test', '-Z=""""' + opt_val + '""""']
        cae.add_opt('testString2Option', 'test str eval short option', '', 'Z')
        assert cae.get_opt('testString2Option') == opt_val

    def test_short_option_bool_str(self, sys_argv_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = 'False'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool str option', True, 'Z')
        assert cae.get_opt('testBoolOption') is False

    def test_short_option_bool_number(self, sys_argv_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool number option', True, 'Z')
        assert cae.get_opt('testBoolOption') is False

    def test_short_option_bool_number_true(self, sys_argv_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '1'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool number option', False, 'Z')
        assert cae.get_opt('testBoolOption') is True

    def test_short_option_bool_eval(self, sys_argv_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '"""0 == 1"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool eval option', True, 'Z')
        assert cae.get_opt('testBoolOption') is False

    def test_short_option_bool_eval_true(self, sys_argv_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '"""9 == 9"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool eval option', False, 'Z')
        assert cae.get_opt('testBoolOption') is True

    def test_short_option_date_str(self, sys_argv_restore):
        cae = ConsoleApp('test_option_date_str')
        opt_val = '2016-12-24'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testDateOption', 'test date str option', datetime.date.today(), 'Z')
        assert cae.get_opt('testDateOption') == datetime.date(year=2016, month=12, day=24)

    def test_short_option_datetime_str(self, sys_argv_restore):
        cae = ConsoleApp('test_option_datetime_str')
        opt_val = '2016-12-24 7:8:0.0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testDatetimeOption', 'test datetime str option', datetime.datetime.now(), 'Z')
        assert cae.get_opt('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)

    def test_short_option_date_eval(self, sys_argv_restore):
        cae = ConsoleApp('test_option_date_eval')
        sys.argv = ['test', '-Z="""datetime.date(year=2016, month=12, day=24)"""']
        cae.add_opt('testDateOption', 'test date eval test option', datetime.date.today(), 'Z')
        assert cae.get_opt('testDateOption') == datetime.date(year=2016, month=12, day=24)

    def test_short_option_datetime_eval(self, sys_argv_restore):
        cae = ConsoleApp('test_option_datetime_eval')
        sys.argv = ['test', '-Z="""datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)"""']
        cae.add_opt('testDatetimeOption', 'test datetime eval test option', datetime.datetime.now(), 'Z')
        assert cae.get_opt('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)

    def test_short_option_list_str(self, sys_argv_restore):
        cae = ConsoleApp('test_option_list_str')
        opt_val = [1, 2, 3]
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_opt('testListStrOption', 'test list str option', [], 'Z')
        assert cae.get_opt('testListStrOption') == opt_val

    def test_short_option_list_eval(self, sys_argv_restore):
        cae = ConsoleApp('test_option_list_eval')
        sys.argv = ['test', '-Z="""[1, 2, 3]"""']
        cae.add_opt('testListEvalOption', 'test list eval option', [], 'Z')
        assert cae.get_opt('testListEvalOption') == [1, 2, 3]

    def test_short_option_dict_str(self, sys_argv_restore):
        cae = ConsoleApp('test_option_dict_str')
        opt_val = {'a': 1, 'b': 2, 'c': 3}
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_opt('testDictStrOption', 'test list str option', {}, 'Z')
        assert cae.get_opt('testDictStrOption') == opt_val

    def test_short_option_dict_eval(self, sys_argv_restore):
        cae = ConsoleApp('test_option_dict_eval')
        sys.argv = ['test', "-Z='''{'a': 1, 'b': 2, 'c': 3}'''"]
        cae.add_opt('testDictEvalOption', 'test dict eval option', {}, 'Z')
        assert cae.get_opt('testDictEvalOption') == {'a': 1, 'b': 2, 'c': 3}

    def test_short_option_tuple_str(self, sys_argv_restore):
        cae = ConsoleApp('test_option_tuple_str')
        opt_val = ('a', 'b', 'c')
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_opt('testTupleStrOption', 'test tuple str option', (), 'Z')
        assert cae.get_opt('testTupleStrOption') == opt_val

    def test_short_option_tuple_eval(self, sys_argv_restore):
        cae = ConsoleApp('test_option_tuple_eval')
        sys.argv = ['test', "-Z='''('a', 'b', 'c')'''"]
        cae.add_opt('testDictEvalOption', 'test tuple eval option', (), 'Z')
        assert cae.get_opt('testDictEvalOption') == ('a', 'b', 'c')

    def test_config_str_eval_single_quote(self, config_fna_vna_vva):
        opt_val = 'testString'
        file_name, var_name, _ = config_fna_vna_vva(var_value="''''" + opt_val + "''''")
        cae = ConsoleApp('test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == opt_val

    def test_config_str_eval_double_quote(self, config_fna_vna_vva):
        opt_val = 'testString'
        file_name, var_name, _ = config_fna_vna_vva(var_value='""""' + opt_val + '""""')
        cae = ConsoleApp('test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == opt_val

    def test_config_bool_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='True')
        cae = ConsoleApp('test_config_bool_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name, value_type=bool) is True

    def test_config_bool_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""1 == 0"""')
        cae = ConsoleApp('test_config_bool_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) is False

    def test_config_bool_eval_true(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""6 == 6"""')
        cae = ConsoleApp('test_config_bool_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) is True

    def test_config_date_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='2012-12-24')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name, value_type=datetime.date) == datetime.date(year=2012, month=12, day=24)

    def test_config_date_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""datetime.date(year=2012, month=12, day=24)"""')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == datetime.date(year=2012, month=12, day=24)

    def test_config_datetime_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='2012-12-24 7:8:0.0')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name, value_type=datetime.datetime) \
            == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)

    def test_config_datetime_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(
            var_value='"""datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)"""')
        cae = ConsoleApp('test_config_datetime_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)

    def test_config_list_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='[1, 2, 3]')
        cae = ConsoleApp('test_config_list_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == [1, 2, 3]

    def test_config_list_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""[1, 2, 3]"""')
        cae = ConsoleApp('test_config_list_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == [1, 2, 3]

    def test_config_dict_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value="{'a': 1, 'b': 2, 'c': 3}")
        cae = ConsoleApp('test_config_dict_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == {'a': 1, 'b': 2, 'c': 3}

    def test_config_dict_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""{"a": 1, "b": 2, "c": 3}"""')
        cae = ConsoleApp('test_config_dict_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == {'a': 1, 'b': 2, 'c': 3}

    def test_config_tuple_str(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value="('a', 'b', 'c')")
        cae = ConsoleApp('test_config_tuple_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == ('a', 'b', 'c')

    def test_config_tuple_eval(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""("a", "b", "c")"""')
        cae = ConsoleApp('test_config_tuple_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == ('a', 'b', 'c')

    def test_debug_level_short_option_value(self, sys_argv_restore):
        cae = ConsoleApp('test_option_value')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_TIMESTAMPED)]
        assert cae.get_opt('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_long_option_value(self, sys_argv_restore):
        cae = ConsoleApp('test_long_option_value')
        sys.argv = ['test', '--debugLevel=' + str(DEBUG_LEVEL_TIMESTAMPED)]
        assert cae.get_opt('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_short_option_eval_single_quoted(self, sys_argv_restore):
        cae = ConsoleApp('test_quoted_option_eval')
        sys.argv = ["test", "-D='''int('" + str(DEBUG_LEVEL_TIMESTAMPED) + "')'''"]
        assert cae.get_opt('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_short_option_eval_double_quoted(self, sys_argv_restore):
        cae = ConsoleApp('test_double_quoted_option_eval')
        sys.argv = ['test', '-D="""int("' + str(DEBUG_LEVEL_TIMESTAMPED) + '")"""']
        assert cae.get_opt('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_add_opt_default(self, sys_argv_restore):
        cae = ConsoleApp('test_add_opt_default', debug_level=DEBUG_LEVEL_TIMESTAMPED)
        sys.argv = list()
        assert cae.get_opt('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_config_default(self, sys_argv_restore, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debugLevel', var_value=str(DEBUG_LEVEL_TIMESTAMPED))
        cae = ConsoleApp('test_config_default', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_opt(var_name) == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_config_eval_single_quote(self, sys_argv_restore, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debugLevel',
                                                    var_value="'''int('" + str(DEBUG_LEVEL_TIMESTAMPED) + "')'''")
        cae = ConsoleApp('test_config_eval', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_opt(var_name) == DEBUG_LEVEL_TIMESTAMPED

    def test_debug_level_config_eval_double_quote(self, sys_argv_restore, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debugLevel',
                                                    var_value='"""int("' + str(DEBUG_LEVEL_TIMESTAMPED) + '")"""')
        cae = ConsoleApp('test_config_double_eval', additional_cfg_files=[file_name])
        sys.argv = list()
        assert cae.get_opt(var_name) == DEBUG_LEVEL_TIMESTAMPED

    def test_sys_env_id_with_debug(self, sys_argv_restore):
        cae = ConsoleApp('test_sys_env_id_with_debug', sys_env_id='OTHER')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_TIMESTAMPED)]
        assert cae.get_opt('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_config_main_file_not_modified(self, config_fna_vna_vva):
        config_fna_vna_vva(
            file_name=os.path.join(os.getcwd(), os.path.splitext(os.path.basename(sys.argv[0]))[0] + INI_EXT))
        cae = ConsoleApp('test_config_modified_after_startup')
        assert not cae.is_main_cfg_file_modified()

    def test_is_main_cfg_file_modified(self, config_fna_vna_vva):
        file_name, var_name, old_var_val = config_fna_vna_vva(
            file_name=os.path.join(os.getcwd(), os.path.splitext(os.path.basename(sys.argv[0]))[0] + INI_EXT))
        cae = ConsoleApp('test_set_var_with_reload')
        time.sleep(.300)    # needed because Python is too quick sometimes
        new_var_val = 'NEW_test_value'
        assert not cae.set_var(var_name, new_var_val)
        assert cae.is_main_cfg_file_modified()

        # cfg_val has still old value (OtherTestValue) because parser instance got not reloaded
        cfg_val = cae.get_var(var_name)
        assert cfg_val == old_var_val
        assert cfg_val != new_var_val
        assert cae.is_main_cfg_file_modified()

        cae.load_cfg_files()
        cfg_val = cae.get_var(var_name)
        assert cfg_val == new_var_val

        assert not cae.is_main_cfg_file_modified()
