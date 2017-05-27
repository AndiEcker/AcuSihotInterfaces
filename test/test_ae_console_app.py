# import pytest

from ae_console_app import ILLEGAL_XML_SUB


class TestIllegalXmlChars:
    def test_xml_char1(self):
        illegal_char = chr(1)       # '&#1;'
        xml = "test xml string with " + illegal_char + " character"
        test_xml = ILLEGAL_XML_SUB.sub('_', xml)
        assert test_xml == xml.replace(illegal_char, '_')

