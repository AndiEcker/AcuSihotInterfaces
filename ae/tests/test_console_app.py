# TODO: remove " or out == ''" as soon as capsys bug is fixed
import pytest

import sys
import os
import datetime
import glob
import time
import logging
import threading

from argparse import ArgumentError


from ae import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_TIMESTAMPED, DATE_TIME_ISO, DATE_ISO
from ae.console_app import (
    uprint, app_instances, main_app_instance, ConsoleApp, _DuplicateSysOut, MAX_NUM_LOG_FILES, INI_EXT)


@pytest.fixture
def config_fna_vna_vva(request):
    def _setup_and_teardown(file_name='test_config.cfg', var_name='test_config_var', var_value='test_value'):
        if os.path.sep not in file_name:
            file_name = os.path.join(os.getcwd(), file_name)
        with open(file_name, 'w') as f:
            f.write("[Settings]\n{} = {}".format(var_name, var_value))

        def _tear_down():       # using yield instead of finalizer does not execute the teardown part
            os.remove(file_name)
        request.addfinalizer(_tear_down)

        return file_name, var_name, var_value

    return _setup_and_teardown


main_cae_instance = None


class TestInternalLogging:
    def test_log_file_rotation(self, sys_argv_restore):
        """ this test has to run first because only the 1st ConsoleApp instance can create an internal log file
        """
        global main_cae_instance
        log_file = 'test_internal_log.log'
        cae = ConsoleApp('0.0', 'test_log_file_rotation',
                         multi_threading=True,
                         logging_config=dict(file_name_def=log_file, file_size_max=.001))
        main_cae_instance = cae     # keep reference to prevent garbage collection
        # no longer needed since added sys_argv_restore:
        # .. old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = []
        file_name_chk = cae.get_option('logFile')   # get_option() has to be called at least once for to create log file
        assert file_name_chk == log_file
        for idx in range(MAX_NUM_LOG_FILES + 9):
            for line_no in range(16):     # full loop is creating 1 kb of log entries (16 * 64 bytes)
                cae.uprint("TestLogEntry{: >26}{: >26}".format(idx, line_no))
        cae._close_log_file()
        assert os.path.exists(log_file)
        # clean up
        os.remove(log_file)
        for idx in range(MAX_NUM_LOG_FILES + 9):
            fn, ext = os.path.splitext(log_file)
            rot_log_file = fn + "-{:0>{index_width}}".format(idx, index_width=len(str(MAX_NUM_LOG_FILES))) + ext
            if os.path.exists(rot_log_file):
                os.remove(rot_log_file)

    def test_open_log_file_with_suppressed_stdout(self):
        """ another test that need to work with the first instance
        """
        cae = main_cae_instance
        cae.suppress_stdout = True
        sys.argv = []
        cae._parsed_args = False
        cae._close_log_file(full_reset=True)
        _ = cae.get_option('debugLevel')   # get_option() has to be called at least once for to create log file
        cae._close_log_file()
        os.remove(cae._log_file_name)

    def test_invalid_log_file_name(self, sys_argv_restore):
        log_file = ':/:invalid:/:'
        cae = ConsoleApp('0.0', 'test_invalid_log_file_name')
        cae.activate_internal_logging(log_file)     # only for coverage of exception

    def test_log_file_flush(self, sys_argv_restore):
        log_file = 'test_internal_log_flush.log'
        cae = ConsoleApp('0.0', 'test_log_file_flush', logging_config=dict(file_name_def=log_file))
        sys.argv = []
        file_name_chk = cae.get_option('logFile')   # get_option() has to be called at least once for to create log file
        assert file_name_chk == log_file
        # cause/provoke _append_eof_and_flush_file() exceptions for coverage by passing any other non-file object
        cae._append_eof_and_flush_file(cae, 'invalid stream file object')


class TestPythonLogging:
    """ test python logging module support
    """
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
            if fc.startswith(' <'):
                fc = fc[fc.index('> ') + 2:]
            assert fc.startswith('####  ') or fc.startswith('_jb_pytest_runner ') or fc.startswith(entry_prefix) \
                or fc.startswith('TesT  V 0.0') or fc.startswith('  **  Additional instance') or fc == ''


class TestHelpers:
    def test_uprint(self, capsys):
        uprint()
        out, err = capsys.readouterr()
        assert (out == '\n' or out == '') and err == ''

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict_basic_from_ini', multi_threading=True)
        (main_app_instance() or cae).debug_level = DEBUG_LEVEL_TIMESTAMPED
        (main_app_instance() or cae).multi_threading = True
        uprint(invalid_kwarg='ika')
        out, err = capsys.readouterr()
        assert ('ika' in out or out == '') and err == ''

        us = chr(40960) + chr(1972) + chr(2013) + 'äöü'
        uprint(us, encode_errors_def='strict')
        out, err = capsys.readouterr()
        assert (us in out or out == '') and err == ''

        uprint(us, cae_instance=cae)
        uprint(us, file=sys.stdout)
        uprint(us, file=sys.stderr)
        fna = 'uprint.txt'
        fhd = open(fna, 'w', encoding='ascii', errors='strict')
        uprint(us, file=fhd)
        fhd.close()
        os.remove(fna)
        uprint(bytes(chr(0xef) + chr(0xbb) + chr(0xbf), encoding='utf-8'))
        out, err = capsys.readouterr()
        print(out)
        assert us in out or out == ''
        assert us in err

        # print invalid/surrogate code point/char for to force UnicodeEncodeError exception in uprint (testing coverage)
        us = chr(0xD801)
        uprint(us, encode_errors_def='strict')

        # multi_threading has to be reset for to prevent debug test run freeze (added multi_threading for coverage)
        cae.multi_threading = False


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
        cae = ConsoleApp('0.0', 'test_get_parameter')
        cae.add_parameter('test_arg')
        arg_val = 'test_arg_val'
        sys.argv = ['test_app', arg_val]
        assert cae.get_parameter('test_arg') == arg_val

    def test_show_help(self):
        cae = ConsoleApp('0.0', 'test_show_help')
        cae.show_help()

    def test_sys_env_id(self, capsys):
        sei = 'TST'
        cae = ConsoleApp('0.0', 'test_sys_env_id', sys_env_id=sei)
        assert cae.sys_env_id == sei
        cae.uprint(sei)     # increase coverage
        out, err = capsys.readouterr()
        assert sei in out or out == ''

        # special case for error code path coverage
        app_instances[''] = ConsoleApp('0.0', 'test_sys_env_id_COPY')
        cae.sys_env_id = ''
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_DISABLED

    def test_shutdown_basics(self):
        def thr():
            while running:
                pass

        cae = ConsoleApp('0.0', 'shutdown_basics')
        cae.shutdown(exit_code=None)

        cae.multi_threading = True
        cae.shutdown(exit_code=None, timeout=0.6)       # tests freezing in debug run without timeout/thread-join

        running = True
        threading.Thread(target=thr).start()
        cae.shutdown(exit_code=None, timeout=0.6)
        running = False

    def test_shutdown_coverage(self):
        cae = ConsoleApp('0.0', 'shutdown_coverage')
        cae.shutdown(exit_code=None, timeout=0.9)

        cae._log_file_index = 1
        cae.shutdown(exit_code=None, timeout=0.1)

        cae._nul_std_out = open(os.devnull, 'w')
        cae.shutdown(exit_code=None, timeout=0.1)


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

    def test_set_config_file_error(self, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('0.0', 'test_set_config_file_error', additional_cfg_files=[file_name])
        val = 'test_value'

        assert cae.set_config(var_name, val, cfg_fnam=os.path.join(os.getcwd(), 'not_existing.ini'))
        with open(file_name, 'w'):      # open to lock file - so next set_config will fail
            assert cae.set_config(var_name, val, cfg_fnam=file_name)

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

    def test_multiple_option_stripped_value_with_choices(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_multiple_option_stripped_with_choices', option_value_stripper=lambda v: v[-1])
        sys.argv = ['test', "-Z=x6", "-Z=yyy9"]
        cae.add_option('testAppOptChoicesSVWC', 'test multiple choices', [], 'Z', choices=['6', '9'], multiple=True)
        assert cae.get_option('testAppOptChoicesSVWC') == ['x6', 'yyy9']

    def test_multiple_option_single_char_fail_with_invalid_choices(self, sys_argv_restore):
        cae = ConsoleApp('0.0', 'test_multiple_option_fail_with_choices')
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

    def test_sys_env_id_with_debug(self, sys_argv_restore):
        cae = ConsoleApp('0.1', 'test_sys_env_id_with_debug', sys_env_id='OTHER')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_TIMESTAMPED)]
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED

    def test_config_main_file_not_modified(self, config_fna_vna_vva):
        config_fna_vna_vva(
            file_name=os.path.join(os.getcwd(), os.path.splitext(os.path.basename(sys.argv[0]))[0] + INI_EXT))
        cae = ConsoleApp('0.0', 'test_config_modified_after_startup')
        assert not cae.config_main_file_modified()

    def test_config_main_file_modified(self, config_fna_vna_vva):
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


class TestDuplicateSysOut:
    def test_init(self):
        lfn = 'log_file.log'
        lfo = open(lfn, 'w')
        dso = _DuplicateSysOut(lfo)
        assert dso.log_file_obj == lfo
        assert dso.sys_out_obj is sys.stdout

        dso = _DuplicateSysOut(lfo, sys_out_obj=sys.stdout)
        assert dso.log_file_obj == lfo
        assert dso.sys_out_obj is sys.stdout

        dso = _DuplicateSysOut(lfo, sys_out_obj=sys.stderr)
        assert dso.log_file_obj == lfo
        assert dso.sys_out_obj is sys.stderr

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
