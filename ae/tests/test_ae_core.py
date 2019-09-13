import pytest

import glob
import logging
import os
import sys

from typing import cast

from ae.core import (
    MAX_NUM_LOG_FILES, calling_module, correct_email, correct_phone, force_encoding,
    full_stack_trace, round_traditional, sys_env_dict, sys_env_text, to_ascii, AppBase)


main_app_instance = None


class TestInternalLogging:
    def test_log_file_rotation(self, sys_argv_restore):
        """ this test has to run first because only the 1st AppBase instance can create an internal log file
        """
        global main_app_instance
        log_file = 'test_internal_base_log.log'
        app = AppBase('0.0', 'test_base_log_file_rotation', multi_threading=True)
        app.logging_init(logging_config=dict(file_name_def=log_file, file_size_max=.001))
        main_app_instance = app     # keep reference to prevent garbage collection
        # no longer needed since added sys_argv_restore:
        # .. old_args = sys.argv     # temporary remove pytest command line arguments (test_file.py)
        sys.argv = []
        for idx in range(MAX_NUM_LOG_FILES + 9):
            for line_no in range(16):     # full loop is creating 1 kb of log entries (16 * 64 bytes)
                app.uprint("TestBaseLogEntry{: >26}{: >26}".format(idx, line_no))
        app._close_log_file()
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
        app = main_app_instance
        app.suppress_stdout = True
        sys.argv = []
        app._parsed_args = False
        app._close_log_file(full_reset=True)
        #_ = app.get_option('debugLevel')   # get_option() has to be called at least once for to create log file
        app.activate_internal_logging(app._log_file_name)
        app._close_log_file()
        os.remove(app._log_file_name)

    def test_invalid_log_file_name(self, sys_argv_restore):
        log_file = ':/:invalid:/:'
        app = AppBase('0.0', 'test_invalid_log_file_name')
        app.activate_internal_logging(log_file)     # only for coverage of exception

    def test_log_file_flush(self, sys_argv_restore):
        log_file = 'test_internal_base_log_flush.log'
        app = AppBase('0.0', 'test_base_log_file_flush')
        app.logging_init(logging_config=dict(file_name_def=log_file))
        app.activate_internal_logging(log_file)
        sys.argv = []
        assert os.path.exists(log_file)

    def test_exception_log_file_flush(self):
        app = AppBase('0.0', 'test_exception_base_log_file_flush')
        # cause/provoke _append_eof_and_flush_file() exceptions for coverage by passing any other non-file object
        app._append_eof_and_flush_file(cast('TextIO', None), 'invalid stream file object')


class TestPythonLogging:
    """ test python logging module support
    """
    def test_logging_config_dict_console_from_init(self):
        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.StreamHandler',
                                              'level': logging.INFO}))
        print(str(var_val))

        app = AppBase('0.0', 'test_python_base_logging_config_dict_console')
        app.logging_init(logging_config=dict(py_logging_config_dict=var_val))

        assert app.logging_conf_dict == var_val
        logging.shutdown()

    def test_logging_config_dict_complex(self, caplog):
        log_file = 'test_base_rot_file.log'
        entry_prefix = "TEST LOG ENTRY "

        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.handlers.RotatingFileHandler',
                                              'level': logging.INFO,
                                              'filename': log_file,
                                              'maxBytes': 33,
                                              'backupCount': 63}),
                       loggers={'root': dict(handlers=['console']),
                                'ae.core': dict(handlers=['console']),
                                'ae.console_app': dict(handlers=['console'])}
                       )
        print(str(var_val))

        app = AppBase('0.0', 'test_python_base_logging_config_dict_file')
        app.logging_init(logging_config=dict(py_logging_config_dict=var_val))

        assert app.logging_conf_dict == var_val

        root_logger = logging.getLogger()
        ae_core_logger = logging.getLogger('ae.core')
        ae_app_logger = logging.getLogger('ae.console_app')

        # AppBaseEnv uprint
        log_text = entry_prefix + "0 uprint"
        app.uprint(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 uprint root"
        app.uprint(log_text, logger=root_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 uprint ae"
        app.uprint(log_text, logger=ae_core_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 uprint ae_app"
        app.uprint(log_text, logger=ae_app_logger)
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
        ae_core_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error ae_app"
        ae_app_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        # AppBaseEnv uprint
        sys.argv = ['test']     # sys.argv has to be reset for to allow get_option('debugLevel') calls, done by dprint()
        log_text = entry_prefix + "5 dprint"
        app.uprint(log_text)
        assert caplog.text.endswith(log_text + "\n")

        # final checks of log file contents
        app._close_log_file()       # does also logging.shutdown()
        file_contents = list()
        for lf in glob.glob(log_file + '*'):
            with open(lf) as fd:
                fc = fd.read()
            file_contents.append(fc)
            os.remove(lf)     # remove log files from last test run
        assert len(file_contents) >= 5
        for fc in file_contents:
            if fc.startswith(" <"):
                fc = fc[fc.index("> ") + 2:]    # remove thread id prefix
            if fc.startswith("{TST}"):
                fc = fc[6:]                     # remove sys_env_id prefix
            assert fc.startswith('####  ') or fc.startswith('_jb_pytest_runner ') or fc.startswith(entry_prefix) \
                or fc.lower().startswith('test  v 0.0') or fc.startswith('  **  Additional instance') or fc == ''


class TestCoreHelpers:
    def test_calling_module(self):
        assert calling_module() == 'test_ae_core'
        assert calling_module('') == 'test_ae_core'
        assert calling_module(cast(str, None)) == 'test_ae_core'
        assert calling_module('xxx_test') == 'test_ae_core'
        assert calling_module('test_ae_core') == '_pytest.python'
        assert calling_module(__name__) == '_pytest.python'
        assert calling_module(__name__, depth=2) == '_pytest.python'
        assert calling_module(__name__, '_pytest.python') == 'pluggy.callers'
        assert calling_module(__name__, depth=3) == 'pluggy.callers'
        assert calling_module(__name__, '_pytest.python', 'pluggy.callers') == 'pluggy.manager'
        assert calling_module(__name__, depth=4) == 'pluggy.manager'
        assert calling_module(__name__, depth=5) == 'pluggy.manager'
        assert calling_module(__name__, '_pytest.python', 'pluggy.callers', 'pluggy.manager') == 'pluggy.hooks'
        assert calling_module(__name__, depth=6) == 'pluggy.hooks'
        assert calling_module(__name__, depth=7) == '_pytest.python'
        assert calling_module(__name__, depth=8) == '_pytest.runner'
        assert calling_module(__name__, depth=9) == 'pluggy.callers'
        assert calling_module(__name__, depth=10) == 'pluggy.manager'
        assert calling_module(__name__, depth=11) == 'pluggy.manager'
        assert calling_module(__name__, depth=12) == 'pluggy.hooks'
        assert calling_module(__name__, depth=13) == '_pytest.runner'
        assert calling_module(__name__, depth=14) == '_pytest.runner'
        assert calling_module(__name__, depth=15) == '_pytest.runner'
        assert calling_module(__name__, depth=16) == '_pytest.runner'

        assert calling_module(__name__, depth=0) == 'ae.core'
        assert calling_module(__name__, depth=-1) == 'ae.core'
        assert calling_module(__name__, depth=-2) == 'ae.core'

        assert calling_module(depth=-1) == 'test_ae_core'
        assert calling_module(depth=cast(int, None)) is None

    def test_force_encoding_umlaut(self):
        s = 'äöü'
        assert force_encoding(s) == '\\xe4\\xf6\\xfc'

        assert force_encoding(s, encoding='utf-8') == s
        assert force_encoding(s, encoding='utf-16') == s
        assert force_encoding(s, encoding='cp1252') == s

        assert force_encoding(s, encoding='utf-8', errors='strict') == s
        assert force_encoding(s, encoding='utf-8', errors='replace') == s
        assert force_encoding(s, encoding='utf-8', errors='ignore') == s
        assert force_encoding(s, encoding='utf-8', errors='') == s

        with pytest.raises(TypeError):
            assert force_encoding(s, encoding=cast(str, None)) == '\\xe4\\xf6\\xfc'

    def test_force_encoding_bytes(self):
        s = 'äöü'

        assert s.encode('ascii', errors='replace') == b'???'
        ba = s.encode('ascii', errors='backslashreplace')   # == b'\\xe4\\xf6\\xfc'
        assert force_encoding(ba, encoding='ascii') == str(ba, encoding='ascii')
        assert force_encoding(ba) == str(ba, encoding='ascii')

        bw = s.encode('cp1252')                             # == b'\xe4\xf6\xfc'
        assert force_encoding(bw, encoding='cp1252') == s
        with pytest.raises(UnicodeDecodeError):
            force_encoding(bw)

    def test_full_stack_trace(self):
        try:
            raise ValueError
        except ValueError as ex:
            # print(full_stack_trace(ex))
            assert full_stack_trace(ex)

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

    def test_sys_env_text(self):
        assert isinstance(sys_env_text(), str)
        assert 'python_ver' in sys_env_text()

    def test_to_ascii(self):
        assert to_ascii('äöü') == 'aou'


class TestOfflineContactValidation:
    def test_correct_email(self):
        # edge cases: empty string or None as email
        assert correct_email('') == ('', False)
        assert correct_email(None) == ('', False)
        r = list()
        assert correct_email('', removed=r) == ('', False)
        assert r == []
        r = list()
        assert correct_email(None, removed=r) == ('', False)
        assert r == []

        # special characters !#$%&'*+-/=?^_`{|}~; are allowed in local part
        r = list()
        assert correct_email('john_smith@example.com', removed=r) == ('john_smith@example.com', False)
        assert r == []
        r = list()
        assert correct_email('john?smith@example.com', removed=r) == ('john?smith@example.com', False)
        assert r == []

        # dot is not the first or last character unless quoted, and does not appear consecutively unless quoted
        r = list()
        assert correct_email(".john.smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["0:."]
        r = list()
        assert correct_email("john.smith.@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["10:."]
        r = list()
        assert correct_email("john..smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["5:."]
        r = list()
        assert correct_email('"john..smith"@example.com', removed=r) == ('"john..smith"@example.com', False)
        assert r == []
        r = list()
        assert correct_email("john.smith@example..com", removed=r) == ("john.smith@example.com", True)
        assert r == ["19:."]

        # space and "(),:;<>@[\] characters are allowed with restrictions (they are only allowed inside a quoted string,
        # as described in the paragraph below, and in addition, a backslash or double-quote must be preceded
        # by a backslash);
        r = list()
        assert correct_email(" john.smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["0: "]
        r = list()
        assert correct_email("john .smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["4: "]
        r = list()
        assert correct_email("john.smith @example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["10: "]
        r = list()
        assert correct_email("john.smith@ example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["11: "]
        r = list()
        assert correct_email("john.smith@ex ample.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["13: "]
        r = list()
        assert correct_email("john.smith@example .com", removed=r) == ("john.smith@example.com", True)
        assert r == ["18: "]
        r = list()
        assert correct_email("john.smith@example. com", removed=r) == ("john.smith@example.com", True)
        assert r == ["19: "]
        r = list()
        assert correct_email("john.smith@example.com  ", removed=r) == ("john.smith@example.com", True)
        assert r == ["22: ", "23: "]
        r = list()
        assert correct_email('john(smith@example.com', removed=r) == ('johnsmith@example.com', True)
        assert r == ["4:("]
        r = list()
        assert correct_email('"john(smith"@example.com', removed=r) == ('"john(smith"@example.com', False)
        assert r == []

        # comments at begin or end of local and domain part
        r = list()
        assert correct_email("john.smith(comment)@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["10:(comment)"]
        r = list()
        assert correct_email("(comment)john.smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["0:(comment)"]
        r = list()
        assert correct_email("john.smith@example.com(comment)", removed=r) == ("john.smith@example.com", True)
        assert r == ["22:(comment)"]
        r = list()
        assert correct_email("john.smith@(comment)example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["11:(comment)"]
        r = list()
        assert correct_email(".john.smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["0:."]
        r = list()
        assert correct_email("john.smith.@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["10:."]
        r = list()
        assert correct_email("john.smith@.example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["11:."]
        r = list()
        assert correct_email("john.smith@example.com.", removed=r) == ("john.smith@example.com", True)
        assert r == ["22:."]

        # international characters above U+007F
        r = list()
        assert correct_email('Heinz.Hübner@example.com', removed=r) == ('Heinz.Hübner@example.com', False)
        assert r == []

        # quoted may exist as a dot separated entity within the local-part, or it may exist when the outermost
        # .. quotes are the outermost characters of the local-part
        r = list()
        assert correct_email('abc."def".xyz@example.com', removed=r) == ('abc."def".xyz@example.com', False)
        assert r == []
        assert correct_email('"abc"@example.com', removed=r) == ('"abc"@example.com', False)
        assert r == []
        assert correct_email('abc"def"xyz@example.com', removed=r) == ('abcdefxyz@example.com', True)
        assert r == ['3:"', '7:"']

        # tests from https://en.wikipedia.org/wiki/Email_address
        r = list()
        assert correct_email('ex-indeed@strange-example.com', removed=r) == ('ex-indeed@strange-example.com', False)
        assert r == []
        r = list()
        assert correct_email("#!$%&'*+-/=?^_`{}|~@example.org", removed=r) == ("#!$%&'*+-/=?^_`{}|~@example.org", False)
        assert r == []
        r = list()
        assert correct_email('"()<>[]:,;@\\\\"!#$%&\'-/=?^_`{}| ~.a"@e.org', removed=r) \
            == ('"()<>[]:,;@\\\\"!#$%&\'-/=?^_`{}| ~.a"@e.org', False)
        assert r == []

        r = list()
        assert correct_email("A@e@x@ample.com", removed=r) == ("A@example.com", True)
        assert r == ["3:@", "5:@"]
        r = list()
        assert correct_email('this\ is\"not\\allowed@example.com', removed=r) == ('thisisnotallowed@example.com', True)
        assert r == ["4:\\", "5: ", '8:"', '12:\\']

    def test_correct_phone(self):
        assert correct_phone(None) == ('', False)
        assert correct_phone('') == ('', False)

        r = list()
        assert correct_phone('+4455667788', removed=r) == ('004455667788', True)
        assert r == ["0:+"]

        r = list()
        assert correct_phone(' +4455667788', removed=r) == ('004455667788', True)
        assert r == ["0: ", "1:+"]

        r = list()
        assert correct_phone('+004455667788', removed=r) == ('004455667788', True)
        assert r == ["0:+"]

        r = list()
        assert correct_phone(' 44 5566/7788', removed=r) == ('4455667788', True)
        assert r == ["0: ", "3: ", "8:/"]

        r = list()
        assert correct_phone(' 44 5566/7788-123', removed=r) == ('4455667788123', True)
        assert r == ["0: ", "3: ", "8:/", "13:-"]

        r = list()
        assert correct_phone(' 44 5566/7788-123', removed=r, keep_1st_hyphen=True) == ('4455667788-123', True)
        assert r == ["0: ", "3: ", "8:/"]
