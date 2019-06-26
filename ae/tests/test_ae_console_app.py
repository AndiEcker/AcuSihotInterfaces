# import pytest
import sys
import os
import datetime
import time
import logging
from argparse import ArgumentError

import pytest

from sys_data_ids import DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_TIMESTAMPED
from ae.console_app import ConsoleApp, NamedLocks, full_stack_trace, ILLEGAL_XML_SUB, MAX_NUM_LOG_FILES, INI_EXT


class TestLogFile:
    """
    this test has to run first because only the first ConsoleApp instance will be able to create a log file; to
    workaround the module variable ae.console_app._ca_instance need to be reset to None before the next ConsoleApp init
    """
    def test_log_file_rotation(self, sys_argv_restore):
        log_file = 'test_log_file_rot.log'
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


class TestPythonLogging:
    def test_logging_config_dict_basic(self):
        file_name = os.path.join(os.getcwd(), 'test_conf.ini')
        var_name = 'test_logging_config_var'
        var_val = dict(version=1)
        with open(file_name, 'w') as f:
            f.write('[Settings]\n' + var_name + ' = ' + str(var_val))

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict', additional_cfg_files=[file_name],
                         logging_config=dict(config_var_name=var_name))

        cfg_val = cae.get_config(var_name)
        assert cfg_val == var_val

        os.remove(file_name)

    def test_logging_config_dict_console(self):
        file_name = os.path.join(os.getcwd(), 'test_conf.ini')
        var_name = 'test_logging_config_var'
        var_val = dict(version=1,
                       handlers=dict(console={'class': 'logging.StreamHandler',
                                              'level': logging.INFO}))
        print(str(var_val))
        with open(file_name, 'w') as f:
            f.write('[Settings]\n' + var_name + ' = ' + str(var_val))

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict_console', additional_cfg_files=[file_name],
                         logging_config=dict(config_var_name=var_name))

        cfg_val = cae.get_config(var_name)
        assert cfg_val == var_val

        os.remove(file_name)

    def test_logging_config_dict_file(self):
        file_name = os.path.join(os.getcwd(), 'test_conf.ini')
        var_name = 'test_logging_config_var'
        log_file = 'test_rot_file.log'
        var_val = dict(version=1,
                       handlers=dict(console={'class': 'logging.handlers.RotatingFileHandler',
                                              'level': logging.INFO,
                                              'filename': log_file,
                                              'maxBytes': 33,
                                              'backupCount': 3}))
        print(str(var_val))
        with open(file_name, 'w') as f:
            f.write('[Settings]\n' + var_name + ' = ' + str(var_val))

        cae = ConsoleApp('0.0', 'test_python_logging_config_dict_file', additional_cfg_files=[file_name],
                         logging_config=dict(config_var_name=var_name))

        cfg_val = cae.get_config(var_name)
        assert cfg_val == var_val

        cae.uprint('TEST LOG ENTRY 0 uprint')
        logging.info('TEST LOG ENTRY 1 info')
        logging.debug('TEST LOG ENTRY 2 debug')
        logging.warning('TEST LOG ENTRY 3 warning')
        logging.error('TEST LOG ENTRY 4 error')

        # sys.argv has to be reset for to allow get_option('debugLevel') calls
        sys.argv = ['test']
        cae.dprint('TEST LOG ENTRY 5 dprint', minimum_debug_level=DEBUG_LEVEL_ENABLED)

        os.remove(file_name)


class TestConfigOptions:
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
