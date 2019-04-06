import datetime
# import pytest

from sxmlif import SihotXmlParser, ResResponse, SihotXmlBuilder


class TestAvailCats:
    def test_avail_stds_bhc_occ_discrepancy(self, avail_cats):
        beg = datetime.date(2017, 9, 23)
        end = datetime.date(2017, 10, 7)
        ret = avail_cats.avail_rooms(hotel_id='1', room_cat='STDS', from_date=beg, to_date=end)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDS' in ret

        assert ret['STDS']['2017-09-23']['AVAIL'] == 1
        assert ret['STDS']['2017-09-24']['AVAIL'] == 1
        # WRONG DATA FROM SIHOT (getting 0 instead of 1): assert ret['STDS']['2017-09-25']['AVAIL'] == 1
        # WRONG DATA FROM SIHOT (getting 2 instead of 3): assert ret['STDS']['2017-09-26']['AVAIL'] == 3
        # WRONG DATA FROM SIHOT (getting 0 instead of 1): assert ret['STDS']['2017-09-27']['AVAIL'] == 1
        # WRONG DATA FROM SIHOT (getting 0 instead of 1): assert ret['STDS']['2017-09-28']['AVAIL'] == 1
        # WRONG DATA FROM SIHOT (getting -1 instead of 0): assert ret['STDS']['2017-09-29']['AVAIL'] == 0
        # WRONG DATA FROM SIHOT (getting -1 instead of 0): assert ret['STDS']['2017-09-30']['AVAIL'] == 0
        # WRONG DATA FROM SIHOT (getting -1 instead of 0): assert ret['STDS']['2017-10-01']['AVAIL'] == 0
        assert ret['STDS']['2017-10-02']['AVAIL'] == 0
        assert ret['STDS']['2017-10-03']['AVAIL'] == 2
        assert ret['STDS']['2017-10-04']['AVAIL'] == 3
        assert ret['STDS']['2017-10-05']['AVAIL'] == 2
        assert ret['STDS']['2017-10-06']['AVAIL'] == 2
        assert ret['STDS']['2017-10-07']['AVAIL'] == 0

    def test_avail_studio_bhc_in_sep(self, avail_cats):
        beg = datetime.date(2017, 9, 17)
        end = datetime.date(2017, 9, 29)
        ret = avail_cats.avail_rooms(hotel_id='1', from_date=beg, to_date=end)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDO' in ret
        assert 'STDP' in ret
        assert 'STDS' in ret

        assert ret['STDO']['2017-09-17']['AVAIL'] == 6
        assert ret['STDO']['2017-09-18']['AVAIL'] == 2
        assert ret['STDO']['2017-09-19']['AVAIL'] == 7
        assert ret['STDO']['2017-09-20']['AVAIL'] == 5
        assert ret['STDO']['2017-09-21']['AVAIL'] == 2
        assert ret['STDO']['2017-09-22']['AVAIL'] == 6
        assert ret['STDO']['2017-09-23']['AVAIL'] == 5
        assert ret['STDO']['2017-09-24']['AVAIL'] == 7
        assert ret['STDO']['2017-09-25']['AVAIL'] == 6
        assert ret['STDO']['2017-09-26']['AVAIL'] == 6
        assert ret['STDO']['2017-09-27']['AVAIL'] == 5
        assert ret['STDO']['2017-09-28']['AVAIL'] == 7
        assert ret['STDO']['2017-09-29']['AVAIL'] == 13

        assert ret['STDP']['2017-09-17']['AVAIL'] == 1
        assert ret['STDP']['2017-09-18']['AVAIL'] == 1
        assert ret['STDP']['2017-09-19']['AVAIL'] == 0
        assert ret['STDP']['2017-09-20']['AVAIL'] == 1
        assert ret['STDP']['2017-09-21']['AVAIL'] == 1
        assert ret['STDP']['2017-09-22']['AVAIL'] == 1
        assert ret['STDP']['2017-09-23']['AVAIL'] == 1
        assert ret['STDP']['2017-09-24']['AVAIL'] == 0
        assert ret['STDP']['2017-09-25']['AVAIL'] == 1
        assert ret['STDP']['2017-09-26']['AVAIL'] == 2
        assert ret['STDP']['2017-09-27']['AVAIL'] == 1
        assert ret['STDP']['2017-09-28']['AVAIL'] == 4
        assert ret['STDP']['2017-09-29']['AVAIL'] == 1

        assert ret['STDS']['2017-09-17']['AVAIL'] == 0
        assert ret['STDS']['2017-09-18']['AVAIL'] == 0
        assert ret['STDS']['2017-09-19']['AVAIL'] == 0
        assert ret['STDS']['2017-09-20']['AVAIL'] == 0
        assert ret['STDS']['2017-09-21']['AVAIL'] == 0
        assert ret['STDS']['2017-09-22']['AVAIL'] == 1
        assert ret['STDS']['2017-09-23']['AVAIL'] == 1
        assert ret['STDS']['2017-09-24']['AVAIL'] == 1
        # WRONG DATA FROM SIHOT (getting 0 instead of 1): assert ret['STDS']['2017-09-25']['AVAIL'] == 1
        # WRONG DATA FROM SIHOT (getting 2 instead of 3): assert ret['STDS']['2017-09-26']['AVAIL'] == 3
        # WRONG DATA FROM SIHOT (getting 0 instead of 1): assert ret['STDS']['2017-09-27']['AVAIL'] == 1
        # WRONG DATA FROM SIHOT (getting 0 instead of 1): assert ret['STDS']['2017-09-28']['AVAIL'] == 1
        # WRONG DATA FROM SIHOT (getting -1 instead of 0): assert ret['STDS']['2017-09-29']['AVAIL'] == 0

    def test_avail_studio_pbc_in_sep(self, avail_cats):
        beg = datetime.date(2017, 9, 17)
        end = datetime.date(2017, 9, 29)
        ret = avail_cats.avail_rooms(hotel_id='4', from_date=beg, to_date=end)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDP' in ret
        assert 'STDS' in ret
        assert 'STDH' in ret
        assert 'STDB' in ret

        assert ret['STDP']['2017-09-17']['AVAIL'] == 0
        assert ret['STDP']['2017-09-18']['AVAIL'] == 0
        assert ret['STDP']['2017-09-19']['AVAIL'] == 6
        assert ret['STDP']['2017-09-20']['AVAIL'] == 4
        assert ret['STDP']['2017-09-21']['AVAIL'] == 2
        assert ret['STDP']['2017-09-22']['AVAIL'] == 3
        assert ret['STDP']['2017-09-23']['AVAIL'] == 2
        assert ret['STDP']['2017-09-24']['AVAIL'] == 5
        assert ret['STDP']['2017-09-25']['AVAIL'] == 5
        assert ret['STDP']['2017-09-26']['AVAIL'] == 8
        assert ret['STDP']['2017-09-27']['AVAIL'] == 5
        assert ret['STDP']['2017-09-28']['AVAIL'] == 3
        assert ret['STDP']['2017-09-29']['AVAIL'] == 1

        assert ret['STDS']['2017-09-17']['AVAIL'] == 3
        assert ret['STDS']['2017-09-18']['AVAIL'] == 0
        assert ret['STDS']['2017-09-19']['AVAIL'] == 1
        assert ret['STDS']['2017-09-20']['AVAIL'] == 1
        assert ret['STDS']['2017-09-21']['AVAIL'] == 2
        assert ret['STDS']['2017-09-22']['AVAIL'] == 1
        assert ret['STDS']['2017-09-23']['AVAIL'] == 1
        assert ret['STDS']['2017-09-24']['AVAIL'] == 6
        assert ret['STDS']['2017-09-25']['AVAIL'] == 10
        assert ret['STDS']['2017-09-26']['AVAIL'] == 10
        assert ret['STDS']['2017-09-27']['AVAIL'] == 6
        assert ret['STDS']['2017-09-28']['AVAIL'] == 1
        assert ret['STDS']['2017-09-29']['AVAIL'] == 0

        assert ret['STDH']['2017-09-17']['AVAIL'] == 0
        assert ret['STDH']['2017-09-18']['AVAIL'] == 0
        assert ret['STDH']['2017-09-19']['AVAIL'] == 0
        assert ret['STDH']['2017-09-20']['AVAIL'] == 0
        assert ret['STDH']['2017-09-21']['AVAIL'] == 0
        assert ret['STDH']['2017-09-22']['AVAIL'] == 0
        assert ret['STDH']['2017-09-23']['AVAIL'] == 0
        assert ret['STDH']['2017-09-24']['AVAIL'] == 0
        assert ret['STDH']['2017-09-25']['AVAIL'] == 1
        assert ret['STDH']['2017-09-26']['AVAIL'] == 0
        assert ret['STDH']['2017-09-27']['AVAIL'] == 0
        assert ret['STDH']['2017-09-28']['AVAIL'] == 1
        assert ret['STDH']['2017-09-29']['AVAIL'] == 0

        assert ret['STDB']['2017-09-17']['AVAIL'] == 1
        assert ret['STDB']['2017-09-18']['AVAIL'] == 0
        assert ret['STDB']['2017-09-19']['AVAIL'] == 0
        assert ret['STDB']['2017-09-20']['AVAIL'] == 1
        assert ret['STDB']['2017-09-21']['AVAIL'] == 1
        assert ret['STDB']['2017-09-22']['AVAIL'] == 1
        assert ret['STDB']['2017-09-23']['AVAIL'] == 0
        assert ret['STDB']['2017-09-24']['AVAIL'] == 1
        assert ret['STDB']['2017-09-25']['AVAIL'] == 1
        assert ret['STDB']['2017-09-26']['AVAIL'] == 3
        assert ret['STDB']['2017-09-27']['AVAIL'] == 2
        assert ret['STDB']['2017-09-28']['AVAIL'] == 4
        assert ret['STDB']['2017-09-29']['AVAIL'] == 3

    def test_avail_rooms_with_studio_cat_1oct(self, avail_cats):
        day = datetime.date(2017, 10, 1)

        ret = avail_cats.avail_rooms(hotel_id='1', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDO' in ret
        assert ret['STDO']['2017-10-01']['TOTAL'] == 42
        assert ret['STDO']['2017-10-01']['AVAIL'] == 7

        ret = avail_cats.avail_rooms(hotel_id='1', room_cat='STDP', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDP' in ret
        assert ret['STDP']['2017-10-01']['TOTAL'] == 33
        assert ret['STDP']['2017-10-01']['AVAIL'] == 2

        ret = avail_cats.avail_rooms(hotel_id='1', room_cat='STDS', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDS' in ret
        assert ret['STDS']['2017-10-01']['TOTAL'] == 19
        # results in -1 because OCC is wrongly returned by Sihot interface as 100% (but Sihot.exe is showing 94.74%:
        # assert ret['STDS']['2017-10-01']['AVAIL'] == 0

        ret = avail_cats.avail_rooms(hotel_id='2', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDO' in ret
        assert ret['STDO']['2017-10-01']['TOTAL'] == 1
        assert ret['STDO']['2017-10-01']['AVAIL'] == 0

        ret = avail_cats.avail_rooms(hotel_id='3', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDO' in ret
        assert ret['STDO']['2017-10-01']['TOTAL'] == 35
        assert ret['STDO']['2017-10-01']['AVAIL'] == 18

        ret = avail_cats.avail_rooms(hotel_id='3', room_cat='STDP', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDP' in ret
        assert ret['STDP']['2017-10-01']['TOTAL'] == 24
        assert ret['STDP']['2017-10-01']['AVAIL'] == 6

        ret = avail_cats.avail_rooms(hotel_id='3', room_cat='STDS', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDS' in ret
        assert ret['STDS']['2017-10-01']['TOTAL'] == 19
        assert ret['STDS']['2017-10-01']['AVAIL'] == 3

        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDP', from_date=day, to_date=day)  # no STDO in PBC
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDP' in ret
        assert ret['STDP']['2017-10-01']['TOTAL'] == 22
        assert ret['STDP']['2017-10-01']['AVAIL'] == 1

        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDS', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDS' in ret
        assert ret['STDS']['2017-10-01']['TOTAL'] == 36
        assert ret['STDS']['2017-10-01']['AVAIL'] == 0

        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDH', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDH' in ret
        assert ret['STDH']['2017-10-01']['TOTAL'] == 22
        assert ret['STDH']['2017-10-01']['AVAIL'] == 0

        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDB', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDB' in ret
        assert ret['STDB']['2017-10-01']['TOTAL'] == 29
        assert ret['STDB']['2017-10-01']['AVAIL'] == 1

        ret = avail_cats.avail_rooms(hotel_id='999', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        # hotel 999 has 0 TOTAL rooms and does not return any CAT availability values
        # assert len(ret)
        # assert 'STDO' in ret

    def test_avail_rooms_with_studio_cat_14sep(self, avail_cats):
        day = datetime.date(2017, 9, 14)

        ret = avail_cats.avail_rooms(hotel_id='1', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDO' in ret
        assert ret['STDO']['2017-09-14']['TOTAL'] == 42
        assert ret['STDO']['2017-09-14']['AVAIL'] == 4

        ret = avail_cats.avail_rooms(hotel_id='1', room_cat='STDP', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDP' in ret
        assert ret['STDP']['2017-09-14']['TOTAL'] == 33
        assert ret['STDP']['2017-09-14']['AVAIL'] == 2

        ret = avail_cats.avail_rooms(hotel_id='1', room_cat='STDS', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDS' in ret
        assert ret['STDS']['2017-09-14']['TOTAL'] == 19
        assert ret['STDS']['2017-09-14']['AVAIL'] == 2

        ret = avail_cats.avail_rooms(hotel_id='2', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDO' in ret
        assert ret['STDO']['2017-09-14']['TOTAL'] == 1
        assert ret['STDO']['2017-09-14']['AVAIL'] == 1

        ret = avail_cats.avail_rooms(hotel_id='3', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDO' in ret
        assert ret['STDO']['2017-09-14']['TOTAL'] == 35
        assert ret['STDO']['2017-09-14']['AVAIL'] == -7

        ret = avail_cats.avail_rooms(hotel_id='3', room_cat='STDP', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDP' in ret
        assert ret['STDP']['2017-09-14']['TOTAL'] == 24
        assert ret['STDP']['2017-09-14']['AVAIL'] == 24

        ret = avail_cats.avail_rooms(hotel_id='3', room_cat='STDS', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDS' in ret
        assert ret['STDS']['2017-09-14']['TOTAL'] == 19
        assert ret['STDS']['2017-09-14']['AVAIL'] == 4

        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDP', from_date=day, to_date=day)  # no STDO in PBC
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDP' in ret
        assert ret['STDP']['2017-09-14']['TOTAL'] == 22
        assert ret['STDP']['2017-09-14']['AVAIL'] == 3

        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDS', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDS' in ret
        assert ret['STDS']['2017-09-14']['TOTAL'] == 36
        assert ret['STDS']['2017-09-14']['AVAIL'] == 0

        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDH', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDH' in ret
        assert ret['STDH']['2017-09-14']['TOTAL'] == 22
        assert ret['STDH']['2017-09-14']['AVAIL'] == 0

        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDB', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDB' in ret
        assert ret['STDB']['2017-09-14']['TOTAL'] == 29
        assert ret['STDB']['2017-09-14']['AVAIL'] == 0

        ret = avail_cats.avail_rooms(hotel_id='999', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        # hotel 999 has 0 TOTAL rooms and does not return any CAT availability values
        # assert len(ret)
        # assert 'STDO' in ret

    def test_all_hotel_all_cats(self, avail_cats):
        ret = avail_cats.avail_rooms()      # all hotels is not supported, Sihot defaults to hotel id '1' if not given
        assert isinstance(ret, dict)
        assert len(ret)
        ret1 = avail_cats.avail_rooms(hotel_id='1')
        assert ret == ret1

    def test_error_with_invalid_cat(self, avail_cats):
        ret = avail_cats.avail_rooms(room_cat='XxYy')    # resulting in empty list without any error (RC==0)
        assert isinstance(ret, dict)
        assert len(ret) == 0
        assert avail_cats.response.rc == '0'

    def test_error_with_invalid_hotel(self, avail_cats):
        ret = avail_cats.avail_rooms(hotel_id='963', room_cat='STDO')
        assert isinstance(ret, str)
        assert avail_cats.response.rc != '0'
        assert 'unknown system id' in ret
        assert 'unknown system id' in avail_cats.response.msg


class TestSihotXmlParser:
    XML_EXAMPLE = '''<?xml version="1.0" encoding="iso-8859-1"?>
    <SIHOT-Document>
        <SIHOT-Version>
            <Version>9.0.0.0000</Version>
            <EXE>D:\sihot\sinetres.exe</EXE>
        </SIHOT-Version>
        <OC>A-SIMPLE_TEST_OC</OC>
        <ID>1</ID>
        <TN>123</TN>
        <RC>0</RC>
    </SIHOT-Document>'''

    def test_attributes(self, console_app_env):
        xml_parser = SihotXmlParser(console_app_env)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.oc == 'A-SIMPLE_TEST_OC'
        assert xml_parser.tn == '123'
        assert xml_parser.id == '1'
        assert xml_parser.rc == '0'
        assert xml_parser.msg == ''
        assert xml_parser.ver == ''
        assert xml_parser.error_level == '0'
        assert xml_parser.error_text == ''


class TestResResponse:
    SXML_RESPONSE_EXAMPLE = '''<?xml version="1.0" encoding="iso-8859-1"?>
    <SIHOT-Document>
        <SIHOT-Version>
            <Version>9.0.0.0000</Version>
            <EXE>D:\SIHOT\SINETRES.EXE</EXE>
        </SIHOT-Version>
        <OC>FAKE_UNKNOWN_OC_MSG</OC>
        <TN>135</TN>
        <ID>99</ID>
        <RC>1</RC>
        <MSG>Unknown operation code!</MSG>
        <MATCHCODE>E987654</MATCHCODE>
    </SIHOT-Document>'''

    def test_attributes(self, console_app_env):
        xml_parser = ResResponse(console_app_env)
        xml_parser.parse_xml(self.SXML_RESPONSE_EXAMPLE)
        assert xml_parser.oc == 'FAKE_UNKNOWN_OC_MSG'
        assert xml_parser.tn == '135'
        assert xml_parser.id == '99'
        assert xml_parser.rc == '1'
        assert xml_parser.msg == 'Unknown operation code!'
        assert xml_parser.ver == ''
        assert xml_parser.error_level == '0'
        assert xml_parser.error_text == ''
        assert xml_parser.matchcode == 'E987654'


class TestSihotXmlBuilder:
    def test_create_xml(self, console_app_env):
        xml_builder = SihotXmlBuilder(console_app_env)
        xml_builder.beg_xml('TEST_OC')
        xml_builder.add_tag('EMPTY')
        xml_builder.add_tag('DEEP', xml_builder.new_tag('DEEPER', 'value'))
        test_date = xml_builder.convert_value_to_xml_string(datetime.datetime.now())
        xml_builder.add_tag('DATE', test_date)
        xml_builder.end_xml()
        console_app_env.dprint('####  New XML created: ', xml_builder.xml)
        assert xml_builder.xml == '<?xml version="1.0" encoding="utf8"?>\n<SIHOT-Document>\n' + \
            '<OC>TEST_OC</OC><TN>2</TN><EMPTY></EMPTY><DEEP><DEEPER>value</DEEPER></DEEP>' + \
            '<DATE>' + test_date + '</DATE>\n</SIHOT-Document>'

    def test_create_xml_kernel(self, console_app_env):
        xml_builder = SihotXmlBuilder(console_app_env, use_kernel=True)
        xml_builder.beg_xml('TEST_OC')
        xml_builder.add_tag('EMPTY')
        xml_builder.add_tag('DEEP', xml_builder.new_tag('DEEPER', 'value'))
        test_date = xml_builder.convert_value_to_xml_string(datetime.datetime.now())
        xml_builder.add_tag('DATE', test_date)
        xml_builder.end_xml()
        console_app_env.dprint('####  New XML created: ', xml_builder.xml)
        assert xml_builder.xml == '<?xml version="1.0" encoding="utf8"?>\n<SIHOT-Document>\n<SIHOT-XML-REQUEST>' + \
            '\n<REQUEST-TYPE>TEST_OC</REQUEST-TYPE><EMPTY></EMPTY><DEEP><DEEPER>value</DEEPER></DEEP>' + \
            '<DATE>' + test_date + '</DATE>\n</SIHOT-XML-REQUEST>\n</SIHOT-Document>'
