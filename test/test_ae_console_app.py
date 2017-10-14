# import pytest
import sys
import os
import datetime

from ae_console_app import ConsoleApp, DEBUG_LEVEL_TIMESTAMPED, ILLEGAL_XML_SUB, full_stack_trace


class TestOptions:
    def test_short_option_str_value(self):
        cae = ConsoleApp('0.0', 'test_option_str_value')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = 'testString'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testOption', 'test test option', '', 'Z')
        assert cae.get_option('testOption') == opt_val
        sys.argv = old_args

    def test_short_option_str_eval(self):
        cae = ConsoleApp('0.0', 'test_option_str_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = 'testString'
        sys.argv = ['test', '-Z=""""' + opt_val + '""""']
        cae.add_option('testOption', 'test str eval test option', '', 'Z')
        assert cae.get_option('testOption') == opt_val
        sys.argv = old_args

    def test_short_option_date_eval(self):
        cae = ConsoleApp('0.0', 'test_option_date_eval')
        old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        opt_val = '2016-12-24'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testOption', 'test date eval test option', datetime.date.today(), 'Z')
        assert cae.get_option('testOption') == datetime.date(year=2016, month=12, day=24)
        sys.argv = old_args

    def test_config_str_eval_single_quote(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        opt_val = 'testString'
        with open(file_name, 'w') as f:
            f.write("[Settings]\ntestOption = ''''" + opt_val + "''''")
        cae = ConsoleApp('0.0', 'test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testOption') == opt_val
        os.remove(file_name)

    def test_config_str_eval_double_quote(self):
        file_name = os.path.join(os.getcwd(), 'test_config.cfg')
        opt_val = 'testString'
        with open(file_name, 'w') as f:
            f.write('[Settings]\ntestOption = """"' + opt_val + '""""')
        cae = ConsoleApp('0.0', 'test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_config('testOption') == opt_val
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

    def test_full_stack_trace(self):
        try:
            raise ValueError
        except ValueError as ex:
            print(full_stack_trace(ex))
            assert full_stack_trace(ex)
