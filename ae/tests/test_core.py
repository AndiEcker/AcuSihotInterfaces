""" test doc string for AppBase.app_title tests
"""
import pytest
from ae.tests.conftest import delete_files

import logging
import os
import sys

from typing import cast

from ae.core import (
    MAX_NUM_LOG_FILES, DATE_ISO,
    activate_multi_threading, _deactivate_multi_threading, main_app_instance,
    correct_email, correct_phone, exec_with_return, force_encoding, full_stack_trace, hide_dup_line_prefix, module_name,
    po, round_traditional, stack_frames, stack_var, sys_env_dict, sys_env_text, to_ascii, try_call, try_eval, try_exec,
    AppPrintingReplicator, AppBase)

import datetime as test_dt

__version__ = '3.6.9dev-test'   # used for automatic app version find tests


module_var = 'module_var_val'   # used for stack_var()/try_exec() tests


class TestCoreHelpers:
    def test_exec_with_return(self):
        assert exec_with_return('a = 1 + 2; a') == 3
        assert exec_with_return('a = 1 + 2; a + 3') == 6

        assert exec_with_return('a = b + 6; a', glo_vars=dict(b=3)) == 9
        assert exec_with_return('a = b + 6; a', loc_vars=dict(b=3)) == 9
        assert exec_with_return('a = b + 6; a', glo_vars=dict(b=69), loc_vars=dict(b=3)) == 9

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

    def test_force_encoding_umlaut(self):
        s = 'äöü'
        assert force_encoding(s) == '\\xe4\\xf6\\xfc'

        assert force_encoding(s, encoding='utf-8') == s
        assert force_encoding(s, encoding='utf-16') == s
        assert force_encoding(s, encoding='cp1252') == s

        assert force_encoding(s, encoding='utf-8', errors='strict') == s
        assert force_encoding(s, encoding='utf-8', errors='replace') == s
        assert force_encoding(s, encoding='utf-8', errors='backslashreplace') == s
        assert force_encoding(s, encoding='utf-8', errors='xmlcharrefreplace') == s
        assert force_encoding(s, encoding='utf-8', errors='ignore') == s
        assert force_encoding(s, encoding='utf-8', errors='') == s

        with pytest.raises(TypeError):
            assert force_encoding(s, encoding=cast(str, None)) == '\\xe4\\xf6\\xfc'

    def test_full_stack_trace(self):
        try:
            raise ValueError
        except ValueError as ex:
            # print(full_stack_trace(ex))
            assert full_stack_trace(ex)

    def test_hide_dup_line_prefix(self):
        l1 = "<t_s_t>"
        l2 = l1
        assert hide_dup_line_prefix(l1, l2) == " " * len(l2)
        l2 = l1 + l1
        assert hide_dup_line_prefix(l1, l2) == " " * len(l1) + l1
        assert hide_dup_line_prefix(l2, l1) == " " * len(l1)
        l2 = l1[:3] + l1
        assert hide_dup_line_prefix(l1, l2) == " " * 3 + l1

    def test_module_name(self):
        assert module_name(cast(str, None)) == 'ae.core'
        assert module_name(__name__) == 'ae.core'
        assert module_name(__name__, depth=0) == 'ae.core'
        assert module_name(__name__, depth=-1) == 'ae.core'
        assert module_name(__name__, depth=-2) == 'ae.core'
        assert module_name('') == 'ae.core'
        assert module_name('xxx_test') == 'ae.core'

        assert module_name() == 'test_core'
        assert module_name(depth=-1) == 'test_core'
        assert module_name('ae.core') == 'test_core'
        assert module_name(depth=2) == 'test_core'
        assert module_name(depth=3) == 'test_core'

        assert module_name('ae.core', 'test_core') == '_pytest.python'
        assert module_name('ae.core', __name__) == '_pytest.python'
        assert module_name(__name__, depth=3) == '_pytest.python'
        assert module_name(depth=4) == '_pytest.python'

        assert module_name('ae.core', __name__, '_pytest.python') == 'pluggy.callers'
        assert module_name('ae.core', __name__, '_pytest.python', depth=4) == 'pluggy.callers'
        assert module_name(depth=5) == 'pluggy.callers'

        assert module_name('ae.core', __name__, '_pytest.python', 'pluggy.callers') == 'pluggy.manager'
        assert module_name(depth=6) == 'pluggy.manager'
        assert module_name(depth=7) == 'pluggy.manager'

        assert module_name(
            'ae.core', __name__, '_pytest.python', 'pluggy.callers', 'pluggy.manager') == 'pluggy.hooks'
        assert module_name(depth=8) == 'pluggy.hooks'

        assert module_name(depth=9) == '_pytest.python'

        assert module_name(depth=10) == '_pytest.runner'

        assert module_name(depth=11) == 'pluggy.callers'

        assert module_name(depth=12) == 'pluggy.manager'
        assert module_name(depth=13) == 'pluggy.manager'

        assert module_name(depth=14) == 'pluggy.hooks'

        assert module_name(depth=15) == '_pytest.runner'
        assert module_name(depth=16) == '_pytest.runner'
        assert module_name(depth=17) == '_pytest.runner'
        assert module_name(depth=18) == '_pytest.runner'

        assert module_name(depth=36) == 'pluggy.hooks'

        assert module_name(depth=37) == '_pytest.config'

        assert module_name(depth=38) == '__main__'

        assert module_name(depth=cast(int, None)) is None
        assert module_name(depth=39) in (None, '_pydev_imps._pydev_execfile')   # PyCharm: differs in (run, debug) mode
        assert module_name(depth=54) is None
        assert module_name(depth=69) is None
        assert module_name(depth=369) is None

    def test_print_out(self, capsys, restore_app_env):
        po()
        out, err = capsys.readouterr()
        assert out == '\n' and err == ''

        po(invalid_kwarg='ika')
        out, err = capsys.readouterr()
        assert 'ika' in out and err == ''

        us = chr(40960) + chr(1972) + chr(2013) + 'äöü'
        po(us, encode_errors_def='strict')
        out, err = capsys.readouterr()
        assert us in out and err == ''

        po(us, file=sys.stdout)
        po(us, file=sys.stderr)
        fna = 'print_out.txt'
        fhd = open(fna, 'w', encoding='ascii', errors='strict')
        po(us, file=fhd)
        fhd.close()
        assert delete_files(fna) == 1
        po(bytes(chr(0xef) + chr(0xbb) + chr(0xbf), encoding='utf-8'))
        out, err = capsys.readouterr()
        assert us in out
        assert us in err

        # print invalid/surrogate code point/char for to force UnicodeEncodeError exception in po() (testing coverage)
        us = chr(0xD801)
        po(us, encode_errors_def='strict')
        out, err = capsys.readouterr()
        assert force_encoding(us) in out and err == ''

    def test_round_traditional(self):
        assert round_traditional(1.01) == 1
        assert round_traditional(10.1, -1) == 10
        assert round_traditional(1.123, 1) == 1.1
        assert round_traditional(0.5) == 1
        assert round_traditional(0.5001, 1) == 0.5

        assert round_traditional(0.075, 2) == 0.08
        assert round(0.075, 2) == 0.07

    def test_stack_frames(self):
        for frame in stack_frames():
            assert frame
            assert getattr(frame, 'f_globals')
            assert getattr(frame, 'f_locals')

    def test_stack_var(self):
        def _inner_func():
            _inner_var = 'inner_var_val'
            assert stack_var('_inner_var', depth=0, locals_only=True) == 'inner_var_val'
            assert stack_var('_inner_var', depth=2, locals_only=True) == 'inner_var_val'
            assert stack_var('_inner_var', 'ae.core', depth=2, locals_only=True) == 'inner_var_val'
            assert stack_var('_inner_var') is None
            assert stack_var('_inner_var', 'test_core', locals_only=True) is None
            assert stack_var('_inner_var', 'ae.core', 'test_core', locals_only=True) is None
            assert stack_var('_inner_var', depth=0) is None
            assert stack_var('_inner_var', depth=3, locals_only=True) is None

            assert stack_var('_outer_var', 'ae.core', locals_only=True) == 'outer_var_val'
            assert stack_var('_outer_var', locals_only=True) == 'outer_var_val'
            assert stack_var('_outer_var', depth=0, locals_only=True) == 'outer_var_val'
            assert stack_var('_outer_var', depth=3, locals_only=True) == 'outer_var_val'
            assert stack_var('_outer_var') is None
            assert stack_var('_outer_var', 'test_core', locals_only=True) is None
            assert stack_var('_outer_var', 'ae.core', 'test_core', locals_only=True) is None
            assert stack_var('_outer_var', depth=0) is None
            assert stack_var('_outer_var', depth=4, locals_only=True) is None

            assert stack_var('module_var') == 'module_var_val'
            assert stack_var('module_var', depth=3) == 'module_var_val'
            assert stack_var('module_var', locals_only=True) is None
            assert stack_var('module_var', 'test_core') is None
            assert stack_var('module_var', 'ae.core', 'test_core') is None
            assert stack_var('module_var', depth=4) is None

        _outer_var = 'outer_var_val'
        _inner_func()

        assert _outer_var
        assert stack_var('_outer_var', 'ae.core', locals_only=True) == 'outer_var_val'
        assert stack_var('_outer_var', locals_only=True) == 'outer_var_val'
        assert stack_var('_outer_var', depth=0, locals_only=True) == 'outer_var_val'
        assert stack_var('_outer_var', depth=2, locals_only=True) == 'outer_var_val'
        assert stack_var('_outer_var') is None
        assert stack_var('_outer_var', depth=0) is None
        assert stack_var('_outer_var', 'test_core', locals_only=True) is None
        assert stack_var('_outer_var', 'ae.core', 'test_core', locals_only=True) is None
        assert stack_var('_outer_var', depth=3, locals_only=True) is None

        assert module_var
        assert stack_var('module_var') == 'module_var_val'
        assert stack_var('module_var', depth=2) == 'module_var_val'
        assert stack_var('module_var', locals_only=True) is None
        assert stack_var('module_var', 'test_core') is None
        assert stack_var('module_var', 'ae.core', 'test_core') is None
        assert stack_var('module_var', depth=3) is None

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

    def test_try_call(self):
        assert try_call(str, 123) == "123"
        assert try_call(bytes, '123', encoding='ascii') == b"123"
        assert try_call(int, '123') == 123

        call_arg = "no-number"
        with pytest.raises(ValueError):
            assert try_call(int, call_arg)
        assert try_call(int, call_arg, ignored_exceptions=(ValueError, )) is None

    def test_try_eval(self):
        assert try_eval("str(123)") == "123"
        assert try_eval("str(bytes(b'123'), encoding='ascii')") == "123"
        assert try_eval("int('123')") == 123

        eval_str = "int('no-number')"
        with pytest.raises(ValueError):
            assert try_eval(eval_str)
        assert try_eval(eval_str, ignored_exceptions=(ValueError, )) is None
        with pytest.raises(TypeError):      # list with ignored exceptions is not accepted
            assert try_eval(eval_str, ignored_exceptions=cast(tuple, [ValueError, ])) is None

        assert try_eval('b + 6', glo_vars=dict(b=3)) == 9
        assert try_eval('b + 6', loc_vars=dict(b=3)) == 9
        assert try_eval('b + 6', glo_vars=dict(b=33), loc_vars=dict(b=3)) == 9

    def test_try_exec(self):
        assert try_exec('a = 1 + 2; a') == 3
        assert try_exec('a = 1 + 2; a + 3') == 6
        assert try_exec('a = b + 6; a', glo_vars=dict(b=3)) == 9
        assert try_exec('a = b + 6; a', loc_vars=dict(b=3)) == 9
        assert try_exec('a = b + 6; a', glo_vars=dict(b=69), loc_vars=dict(b=3)) == 9

        code_block = "a=1+2; module_var"
        with pytest.raises(NameError):
            assert try_exec(code_block) == module_var
        assert try_exec(code_block, glo_vars=globals()) == module_var

        # check ae.core datetime/DATE_ISO context (globals)
        dt_val = test_dt.datetime.now()
        dt_str = test_dt.datetime.strftime(dt_val, DATE_ISO)
        assert try_exec("dt = _; datetime.datetime.strftime(dt, DATE_ISO)", loc_vars={'_': dt_val}) == dt_str


class TestAppPrintingReplicator:
    def test_init(self):
        dso = AppPrintingReplicator()
        assert dso.sys_out_obj is sys.stdout

        dso = AppPrintingReplicator(sys_out_obj=sys.stdout)
        assert dso.sys_out_obj is sys.stdout

        dso = AppPrintingReplicator(sys_out_obj=sys.stderr)
        assert dso.sys_out_obj is sys.stderr

    def test_flush_method_exists(self):
        dso = AppPrintingReplicator()
        assert hasattr(dso, 'flush')
        assert callable(dso.flush)

    def test_write(self):
        lfn = 'ca_dup_sys_write_test.txt'
        try:
            lfo = open(lfn, 'w')
            dso = AppPrintingReplicator(lfo)
            msg = 'test_ascii_message'
            dso.write(msg)
            lfo.close()
            with open(lfn) as f:
                assert f.read() == msg

            lfo = open(lfn, 'w', encoding='utf-8')
            dso = AppPrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            with open(lfn, encoding='utf-8') as f:
                assert f.read() == msg

            lfo = open(lfn, 'w', encoding='ascii')
            dso = AppPrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            with open(lfn, encoding='ascii') as f:
                assert f.read() == '\\ua000\\u07b4'

            lfo = open(lfn, 'w')
            dso = AppPrintingReplicator(lfo)
            msg = chr(40960) + chr(1972)            # == '\ua000\u07b4'
            dso.write(msg)
            lfo.close()
            with open(lfn) as f:
                if f.encoding == 'ascii':
                    assert f.read() == '\\ua000\\u07b4'
                else:
                    assert f.read() == msg      # msg == '\ua000\u07b4'

        finally:
            assert delete_files(lfn) == 1


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
        assert correct_email('this is "not" \\allowed@example.com', removed=r) == ('thisisnotallowed@example.com', True)
        assert r == ['4: ', '7: ', '8:"', '12:"', '13: ', '14:\\']

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


class TestAeLogging:
    def test_log_file_rotation(self, restore_app_env):
        log_file = 'test_ae_base_log.log'
        try:
            app = AppBase('test_base_log_file_rotation')
            app.init_logging(file_name_def=log_file, file_size_max=.001)
            app.log_file_check()
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):     # full loop is creating 1 kb of log entries (16 * 64 bytes)
                    app.po("TestBaseLogEntry{: >26}{: >26}".format(idx, line_no))
            assert os.path.exists(log_file)
        finally:
            assert delete_files(log_file, keep_ext=True) >= MAX_NUM_LOG_FILES

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_log_file_rotation_multi_threading(self, restore_app_env):
        log_file = 'test_ae_multi_log.log'
        try:
            app = AppBase('test_base_log_file_rotation')
            activate_multi_threading()
            app.init_logging(file_name_def=log_file, file_size_max=.001)
            app.log_file_check()
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):     # full loop is creating 1 kb of log entries (16 * 64 bytes)
                    app.po("TestBaseLogEntry{: >26}{: >26}".format(idx, line_no))
            assert os.path.exists(log_file)
        finally:
            assert delete_files(log_file, keep_ext=True) >= MAX_NUM_LOG_FILES

    def test_open_log_file_with_suppressed_stdout(self, capsys, restore_app_env):
        log_file = 'test_ae_no_stdout.log'
        try:
            app = AppBase('test_open_log_file_with_suppressed_stdout', suppress_stdout=True)
            assert app.suppress_stdout is True
            app.init_logging(file_name_def=log_file)
            app.log_file_check()
            app.init_logging()      # close log file
            assert os.path.exists(log_file)
        finally:
            assert delete_files(log_file) == 1

    def test_invalid_log_file_name(self, restore_app_env):
        log_file = ':/:invalid:/:'
        app = AppBase('test_invalid_log_file_name')
        app.init_logging(file_name_def=log_file)
        with pytest.raises(FileNotFoundError):
            app.log_file_check()     # coverage of callee exception
        assert not os.path.exists(log_file)

    def test_log_file_flush(self, restore_app_env):
        log_file = 'test_ae_base_log_flush.log'
        try:
            app = AppBase('test_base_log_file_flush')
            app.init_logging(file_name_def=log_file)
            app.log_file_check()
            assert os.path.exists(log_file)
        finally:
            assert delete_files(log_file) == 1

    def test_exception_log_file_flush(self, restore_app_env):
        app = AppBase('test_exception_base_log_file_flush')
        # cause/provoke _append_eof_and_flush_file() exceptions for coverage by passing any other non-stream object
        app._append_eof_and_flush_file(cast('TextIO', None), 'invalid stream')

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestPythonLogging:
    """ test python logging module support
    """
    def test_logging_params_dict_console_from_init(self, restore_app_env):
        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.StreamHandler',
                                              'level': logging.INFO}))
        print(str(var_val))

        app = AppBase('test_python_base_logging_params_dict_console')
        app.init_logging(py_logging_params=var_val)

        assert app.py_log_params == var_val
        logging.shutdown()

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_logging_params_dict_complex(self, caplog, restore_app_env, tst_app_key):
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

        app = AppBase('test_python_base_logging_params_dict_file')
        app.init_logging(py_logging_params=var_val)

        assert app.py_log_params == var_val

        root_logger = logging.getLogger()
        ae_core_logger = logging.getLogger('ae.core')
        ae_app_logger = logging.getLogger('ae.console_app')

        # AppBase print_out()/po()
        log_text = entry_prefix + "0 print_out"
        app.po(log_text)
        assert caplog.text == ""

        log_text = entry_prefix + "0 print_out root"
        app.po(log_text, logger=root_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out ae"
        app.po(log_text, logger=ae_core_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out ae_app"
        app.po(log_text, logger=ae_app_logger)
        assert caplog.text.endswith(log_text + "\n")

        # logging
        logging.info(entry_prefix + "1 info")       # will NOT be added to log
        assert caplog.text.endswith(log_text + "\n")

        logging.debug(entry_prefix + "2 debug")     # NOT logged
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "3 warning"
        logging.warning(log_text)                   # NOT logged
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

        new_log_text = entry_prefix + "5 dpo"
        app.po(new_log_text)
        assert caplog.text.endswith(log_text + "\n")    # NO LOGGER OUTPUT without po logger arg - caplog unchanged
        app.po(new_log_text, logger=ae_app_logger)
        assert caplog.text.endswith(new_log_text + "\n")

        # final checks of log file contents
        logging.shutdown()
        file_contents = delete_files(log_file, ret_type='contents')
        assert len(file_contents) >= 5
        for fc in file_contents:
            if fc.startswith(" <"):
                fc = fc[fc.index("> ") + 2:]    # remove thread id prefix
            if fc.startswith("{TST}"):
                fc = fc[6:]                     # remove sys_env_id prefix
            assert fc.startswith(entry_prefix)
            assert "1 info" not in fc and "2 debug" not in fc and "3 warning" not in fc

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestAppBase:      # only some basic tests - test coverage is done by :class:`~console_app.ConsoleApp` tests
    def test_app_name(self, restore_app_env, sys_argv_app_key_restore):
        name = 'tan_app_name'
        sys.argv = [name, ]
        app = AppBase()
        assert app.app_name == name

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_app_attributes(self, restore_app_env):
        ver = '0.0'
        title = 'test_app_name'
        app = AppBase(title, app_version=ver)
        assert app.app_title == title
        assert app.app_version == ver
        assert app._app_path == os.path.dirname(sys.argv[0])

    def test_app_find_version(self, restore_app_env):
        app = AppBase()
        assert app.app_version == __version__

    def test_app_find_title(self, restore_app_env):
        app = AppBase()
        assert app.app_title == __doc__

    def test_print_out(self, capsys, restore_app_env):
        app = AppBase('test_python_logging_params_dict_basic_from_ini')
        activate_multi_threading()
        app.po()
        out, err = capsys.readouterr()
        assert out.endswith('\n') and err == ''

        app.po(invalid_kwarg='ika')
        out, err = capsys.readouterr()
        assert 'ika' in out and err == ''

        us = chr(40960) + chr(1972) + chr(2013) + 'äöü'
        app.po(us, encode_errors_def='strict')
        out, err = capsys.readouterr()
        assert us in out and err == ''

        app.po(us, app_instance=app)
        app.po(us, file=sys.stdout)
        app.po(us, file=sys.stderr)
        fna = 'print_out.txt'
        fhd = open(fna, 'w', encoding='ascii', errors='strict')
        app.po(us, file=fhd)
        fhd.close()
        assert delete_files(fna) == 1
        app.po(bytes(chr(0xef) + chr(0xbb) + chr(0xbf), encoding='utf-8'))
        out, err = capsys.readouterr()
        print(out)
        assert us in out
        assert us in err

        # print invalid/surrogate code point/char for to force UnicodeEncodeError exception in po() (testing coverage)
        us = chr(0xD801)
        app.po(us, encode_errors_def='strict')

        # multi_threading has to be reset for to prevent debug test run freeze (added multi_threading for coverage)
        _deactivate_multi_threading()

    def test_app_instances_reset2(self):
        assert main_app_instance() is None
