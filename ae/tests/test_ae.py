import pytest
import sys
from ae import (calling_module, force_encoding, full_stack_trace, round_traditional, sys_env_dict, sys_env_text,
                to_ascii,
                ILLEGAL_XML_SUB)


class TestHelpers:
    def test_calling_module(self):
        assert calling_module() == 'test_ae'
        assert calling_module('') == 'test_ae'
        assert calling_module('xxx_test') == 'test_ae'
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

        assert calling_module(called_module=__name__, depth=0) == 'ae'
        assert calling_module(called_module=__name__, depth=-1) == 'ae'
        assert calling_module(called_module=__name__, depth=-2) == 'ae'

        assert calling_module(called_module=None, depth=-1) == 'ae'
        assert calling_module(called_module=None, depth=None) is None

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
            assert force_encoding(s, encoding=None) == '\\xe4\\xf6\\xfc'

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


class TestIllegalXmlChars:
    def test_xml_char1(self):
        illegal_char = chr(1)       # '&#1;'
        xml = "test xml string with " + illegal_char + " character"
        test_xml = ILLEGAL_XML_SUB.sub('_', xml)
        assert test_xml == xml.replace(illegal_char, '_')
