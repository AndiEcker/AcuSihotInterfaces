from ae_unicode.unicode import illegal_xml_sub


class TestIllegalXmlChars:
    def test_xml_char1(self):
        illegal_char = chr(1)       # '&#1;'
        xml = "test xml string with " + illegal_char + " character"
        test_xml = illegal_xml_sub().sub('_', xml)
        assert test_xml == xml.replace(illegal_char, '_')
