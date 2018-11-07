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
        xml_builder = SihotXmlBuilder(console_app_env, use_kernel=False)
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


class TestGuestSearch:
    def test_get_guest_with_test_client(self, guest_search, create_test_guest):
        ret = guest_search.get_guest(create_test_guest.objid)
        assert guest_search.response.objid == create_test_guest.objid     # OBJID passed only to response (ret is empty)
        # also MATCHCODE element is in response (and empty in ret): assert ret['MATCHCODE']==create_test_guest.matchcode
        assert guest_search.response.matchcode == create_test_guest.matchcode
        assert guest_search.response.objid == create_test_guest.objid
        assert isinstance(ret, dict)
        assert ret['NAME-1'] == create_test_guest.surname
        assert ret['NAME-2'] == create_test_guest.forename
        assert ret['T-GUEST'] == create_test_guest.guest_type

    def test_get_guest_with_10_ext_refs(self, guest_search):
        objid = guest_search.get_objid_by_matchcode('E396693')
        assert objid
        ret = guest_search.get_guest(objid)
        assert isinstance(ret, dict)
        assert ret['MATCH-ADM'] == '4806-00208'
        if ret['COMMENT']:
            assert 'RCI=1442-11521' in ret['COMMENT']
            assert 'RCI=5445-12771' in ret['COMMENT']
            assert 'RCI=5-207931' in ret['COMMENT']     # RCIP got remapped to RCI

    def test_get_guest_nos_by_matchcode(self, guest_search):
        guest_nos = guest_search.get_guest_nos_by_matchcode('OTS')
        assert '31' in guest_nos
        guest_nos = guest_search.get_guest_nos_by_matchcode('SF')
        assert '62' in guest_nos
        guest_nos = guest_search.get_guest_nos_by_matchcode('TCAG')
        assert '12' in guest_nos
        guest_nos = guest_search.get_guest_nos_by_matchcode('TCRENT')
        assert '19' in guest_nos

    def test_get_objid_by_guest_no(self, guest_search):
        obj_id1 = guest_search.get_objid_by_guest_no(31)
        obj_id2 = guest_search.get_objid_by_matchcode('OTS')
        assert obj_id1 == obj_id2
        obj_id1 = guest_search.get_objid_by_guest_no(62)
        obj_id2 = guest_search.get_objid_by_matchcode('SF')
        assert obj_id1 == obj_id2
        obj_id1 = guest_search.get_objid_by_guest_no(12)
        obj_id2 = guest_search.get_objid_by_matchcode('TCAG')
        assert obj_id1 == obj_id2
        obj_id1 = guest_search.get_objid_by_guest_no('19')
        obj_id2 = guest_search.get_objid_by_matchcode('TCRENT')
        assert obj_id1 == obj_id2

    def test_get_objids_by_guest_names(self, guest_search):
        obj_ids = guest_search.get_objids_by_guest_names('OTS Open Travel Services AG', '')
        obj_id = guest_search.get_objid_by_matchcode('OTS')
        assert obj_id in obj_ids
        obj_ids = guest_search.get_objids_by_guest_names('Sumar Ferdir', '')
        obj_id = guest_search.get_objid_by_matchcode('SF')
        assert obj_id in obj_ids
        obj_ids = guest_search.get_objids_by_guest_names('Thomas Cook AG', '')
        obj_id = guest_search.get_objid_by_matchcode('TCAG')
        assert obj_id in obj_ids
        obj_ids = guest_search.get_objids_by_guest_names('Thomas Cook Northern Europe', '')
        obj_id = guest_search.get_objid_by_matchcode('TCRENT')
        assert obj_id in obj_ids

    def test_get_objids_by_email(self, guest_search):
        obj_ids = guest_search.get_objids_by_email('info@opentravelservice.com')
        obj_id = guest_search.get_objid_by_matchcode('OTS')
        assert obj_id in obj_ids
        obj_id = guest_search.get_objid_by_matchcode('SF')
        assert obj_id in obj_ids

    def test_get_objid_by_matchcode(self, guest_search):
        assert guest_search.get_objid_by_matchcode('OTS') == '69'
        assert guest_search.get_objid_by_matchcode('SF') == '100'
        assert guest_search.get_objid_by_matchcode('TCAG') == '20'
        assert guest_search.get_objid_by_matchcode('TCRENT') == '27'

    def test_get_objid_by_matchcode2(self, guest_search, create_test_guest):
        ret = guest_search.get_objid_by_matchcode(create_test_guest.matchcode)
        assert ret == create_test_guest.objid

    def test_search_agencies(self, guest_search):
        ags = guest_search.search_agencies()
        assert [_ for _ in ags if _['MATCHCODE'] == 'OTS' and _['OBJID'] == '69']
        assert [_ for _ in ags if _['MATCHCODE'] == 'SF' and _['OBJID'] == '100']
        assert [_ for _ in ags if _['MATCHCODE'] == 'TCAG' and _['OBJID'] == '20']
        assert [_ for _ in ags if _['MATCHCODE'] == 'TCRENT' and _['OBJID'] == '27']
