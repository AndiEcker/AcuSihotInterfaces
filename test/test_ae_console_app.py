# import pytest

from ae_console_app import ILLEGAL_XML_SUB, full_stack_trace


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
