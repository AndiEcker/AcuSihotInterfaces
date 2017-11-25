# import pytest
import sys
import os
import datetime

from ae_console_app import ConsoleApp, DEBUG_LEVEL_TIMESTAMPED, ILLEGAL_XML_SUB, full_stack_trace, uprint


class TestLogFile:
    def test_log_file_rotation(self):
        log_file = '../log/test_log_file_rot.log'
        cae = ConsoleApp('0.0', 'test_log_file_rotation', log_file_def=log_file, log_max_size=.001)
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = []
        assert cae.get_option('logFile')    # get_option() has to be called at least once for to create log file
        for i in range(12):
            for j in range(16):     # full loop is creating 1 kb of log entries (16 * 64 bytes)
                uprint("TestLogEntry{: >26}{: >26}".format(i, j))
        # clean up
        cae._close_log_file()
        os.remove(log_file)
        for i in range(9):
            fn, ext = os.path.splitext(log_file)
            rot_log_file = fn + "-" + str(i + 1) + ext
            assert os.path.exists(rot_log_file)
            os.remove(rot_log_file)
        sys.argv = old_args


class TestConfigOptions:
    def test_config_default_bool(self):
        cae = ConsoleApp('0.0', 'test_config_defaults')
        cfg_val = cae.get_config('not_existing_config_var', default_value=False)
        assert cfg_val is False
        cfg_val = cae.get_config('not_existing_config_var2', value_type=bool)
        assert cfg_val is False

    def test_long_option_str_value(self):
        cae = ConsoleApp('0.0', 'test_long_option_str_value')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = 'testString'
        sys.argv = ['test', '--testStringOption=' + opt_val]
        cae.add_option('testStringOption', 'test long option', '', 'Z')
        assert cae.get_option('testStringOption') == opt_val
        sys.argv = old_args

    def test_short_option_str_value(self):
        cae = ConsoleApp('0.0', 'test_option_str_value')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = 'testString'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testStringOption', 'test short option', '', 'Z')
        assert cae.get_option('testStringOption') == opt_val
        sys.argv = old_args

    def test_short_option_str_eval(self):
        cae = ConsoleApp('0.0', 'test_option_str_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = 'testString'
        sys.argv = ['test', '-Z=""""' + opt_val + '""""']
        cae.add_option('testString2Option', 'test str eval short option', '', 'Z')
        assert cae.get_option('testString2Option') == opt_val
        sys.argv = old_args

    def test_short_option_bool_str(self):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = 'False'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool str option', True, 'Z')
        assert cae.get_option('testBoolOption') is False
        sys.argv = old_args

    def test_short_option_bool_number(self):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = '0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool number option', True, 'Z')
        assert cae.get_option('testBoolOption') is False
        sys.argv = old_args

    def test_short_option_bool_number_true(self):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = '1'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool number option', False, 'Z')
        assert cae.get_option('testBoolOption') is True
        sys.argv = old_args

    def test_short_option_bool_eval(self):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = '"""0 == 1"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool eval option', True, 'Z')
        assert cae.get_option('testBoolOption') is False
        sys.argv = old_args

    def test_short_option_bool_eval_true(self):
        cae = ConsoleApp('0.0', 'test_option_bool_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = '"""9 == 9"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool eval option', False, 'Z')
        assert cae.get_option('testBoolOption') is True
        sys.argv = old_args

    def test_short_option_date_str(self):
        cae = ConsoleApp('0.0', 'test_option_date_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = '2016-12-24'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testDateOption', 'test date str option', datetime.date.today(), 'Z')
        assert cae.get_option('testDateOption') == datetime.date(year=2016, month=12, day=24)
        sys.argv = old_args

    def test_short_option_datetime_str(self):
        cae = ConsoleApp('0.0', 'test_option_datetime_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = '2016-12-24 7:8:0.0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testDatetimeOption', 'test datetime str option', datetime.datetime.now(), 'Z')
        assert cae.get_option('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)
        sys.argv = old_args

    def test_short_option_date_eval(self):
        cae = ConsoleApp('0.0', 'test_option_date_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ['test', '-Z="""datetime.date(year=2016, month=12, day=24)"""']
        cae.add_option('testDateOption', 'test date eval test option', datetime.date.today(), 'Z')
        assert cae.get_option('testDateOption') == datetime.date(year=2016, month=12, day=24)
        sys.argv = old_args

    def test_short_option_datetime_eval(self):
        cae = ConsoleApp('0.0', 'test_option_datetime_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ['test', '-Z="""datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)"""']
        cae.add_option('testDatetimeOption', 'test datetime eval test option', datetime.datetime.now(), 'Z')
        assert cae.get_option('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)
        sys.argv = old_args

    def test_short_option_list_str(self):
        cae = ConsoleApp('0.0', 'test_option_list_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = [1, 2, 3]
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testListStrOption', 'test list str option', [], 'Z')
        assert cae.get_option('testListStrOption') == opt_val
        sys.argv = old_args

    def test_short_option_list_eval(self):
        cae = ConsoleApp('0.0', 'test_option_list_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ['test', '-Z="""[1, 2, 3]"""']
        cae.add_option('testListEvalOption', 'test list eval option', [], 'Z')
        assert cae.get_option('testListEvalOption') == [1, 2, 3]
        sys.argv = old_args

    def test_short_option_dict_str(self):
        cae = ConsoleApp('0.0', 'test_option_dict_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = {'a': 1, 'b': 2, 'c': 3}
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testDictStrOption', 'test list str option', {}, 'Z')
        assert cae.get_option('testDictStrOption') == opt_val
        sys.argv = old_args

    def test_short_option_dict_eval(self):
        cae = ConsoleApp('0.0', 'test_option_dict_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ['test', "-Z='''{'a': 1, 'b': 2, 'c': 3}'''"]
        cae.add_option('testDictEvalOption', 'test dict eval option', {}, 'Z')
        assert cae.get_option('testDictEvalOption') == {'a': 1, 'b': 2, 'c': 3}
        sys.argv = old_args

    def test_short_option_tuple_str(self):
        cae = ConsoleApp('0.0', 'test_option_tuple_str')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = ('a', 'b', 'c')
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testTupleStrOption', 'test tuple str option', (), 'Z')
        assert cae.get_option('testTupleStrOption') == opt_val
        sys.argv = old_args

    def test_short_option_tuple_eval(self):
        cae = ConsoleApp('0.0', 'test_option_tuple_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ['test', "-Z='''('a', 'b', 'c')'''"]
        cae.add_option('testDictEvalOption', 'test tuple eval option', (), 'Z')
        assert cae.get_option('testDictEvalOption') == ('a', 'b', 'c')
        sys.argv = old_args

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

    def test_debug_level_short_option_value(self):
        cae = ConsoleApp('0.1', 'test_option_value')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_TIMESTAMPED)]
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        sys.argv = old_args

    def test_debug_level_long_option_value(self):
        cae = ConsoleApp('0.1', 'test_option_value')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ['test', '--debugLevel=' + str(DEBUG_LEVEL_TIMESTAMPED)]
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        sys.argv = old_args

    def test_debug_level_short_option_eval_single_quoted(self):
        cae = ConsoleApp('0.1', 'test_option_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ["test", "-D='''int('" + str(DEBUG_LEVEL_TIMESTAMPED) + "')'''"]
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        sys.argv = old_args

    def test_debug_level_short_option_eval_double_quoted(self):
        cae = ConsoleApp('0.1', 'test_option_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = ['test', '-D="""int("' + str(DEBUG_LEVEL_TIMESTAMPED) + '")"""']
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        sys.argv = old_args

    def test_debug_level_add_option_default(self):
        cae = ConsoleApp('0.1', 'test_add_option_default', debug_level_def=DEBUG_LEVEL_TIMESTAMPED)
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        sys.argv = old_args

    def test_debug_level_config_default(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ndebugLevel = ' + str(DEBUG_LEVEL_TIMESTAMPED))
        cae = ConsoleApp('0.2', 'test_config_default', additional_cfg_files=[file_name])
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        sys.argv = old_args
        os.remove(file_name)

    def test_debug_level_config_eval_single_quote(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write("[Settings]\ndebugLevel = '''int('" + str(DEBUG_LEVEL_TIMESTAMPED) + "')'''")
        cae = ConsoleApp('0.3', 'test_config_eval', additional_cfg_files=[file_name])
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        sys.argv = old_args
        os.remove(file_name)

    def test_debug_level_config_eval_double_quote(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        with open(file_name, 'w') as f:
            f.write('[Settings]\ndebugLevel = """int("' + str(DEBUG_LEVEL_TIMESTAMPED) + '")"""')
        cae = ConsoleApp('0.3', 'test_config_eval', additional_cfg_files=[file_name])
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = list()
        assert cae.get_option('debugLevel') == DEBUG_LEVEL_TIMESTAMPED
        sys.argv = old_args
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
            print(full_stack_trace(ex))
            assert full_stack_trace(ex)
