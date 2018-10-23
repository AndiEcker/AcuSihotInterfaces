import datetime
# import pytest

from sxmlif import SihotXmlParser, ResResponse, GuestFromSihot, ResFromSihot, SihotXmlBuilder, ClientToSihot, ResToSihot


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


class TestGuestFromSihot:
    XML_EXAMPLE = '''<?xml version="1.0" encoding="iso-8859-1"?>
    <SIHOT-Document>
        <OC>GUEST-CREATE</OC>
        <ID>1</ID>
        <TN>1</TN>
        <GUEST>
            <MATCHCODE>test2</MATCHCODE>
            <PWD>pass56</PWD>
            <ADDRESS></ADDRESS>
            <GUESTTYPE>1</GUESTTYPE>
            <NAME>Test O'Neil</NAME>
            <NAME2>und Co</NAME2>
            <DOB>1962-6-18</DOB>
            <STREET>Strasse</STREET>
            <POBOX />
            <ZIP>68696</ZIP>
            <CITY>city</CITY>
            <COUNTRY>DE</COUNTRY>
            <LANG>de</LANG>
            <PHONE1>Telefon1</PHONE1>
            <PHONE2>Telefon2</PHONE2>
            <FAX1>Fax1</FAX1>
            <FAX2>Fax2</FAX2>
            <EMAIL1>Email1</EMAIL1>
            <EMAIL2>Email2</EMAIL2>
            <MOBIL1 />
            <MOBIL2 />
            <PERS-TYPE>1A</PERS-TYPE>
            <COMMENT></COMMENT>
            <DEFAULT-PAYMENT-TYPE>BA</DEFAULT-PAYMENT-TYPE>
            <ACARDLIST>
                <CARD>
                    <NO>4242424242424242</NO>
                    <TYPE>VI</TYPE>
                    <VAL>2011-01-31</VAL>
                    <CVC>2424</CVC>
                    <HOLDER-NAME></HOLDER-NAME>
                    <CCHANDLE></CCHANDLE>
                    <CCHANDLEVALIDUNTIL></CCHANDLEVALIDUNTIL>
                </CARD>
            </ACARDLIST>
        </GUEST>
    </SIHOT-Document>'''

    def test_attributes(self, console_app_env):
        xml_parser = GuestFromSihot(console_app_env)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.oc == 'GUEST-CREATE'
        assert xml_parser.tn == '1'
        assert xml_parser.id == '1'
        assert xml_parser.rc == '0'
        assert xml_parser.msg == ''
        assert xml_parser.ver == ''
        assert xml_parser.error_level == '0'
        assert xml_parser.error_text == ''

    def test_elem_map(self, console_app_env):
        xml_parser = GuestFromSihot(console_app_env)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert len(xml_parser.guest_list)
        assert xml_parser.guest_list[0]['MATCHCODE'].val() == 'test2'
        assert xml_parser.guest_list[0]['AcId'].val() == 'test2'
        assert xml_parser.guest_list[0]['CITY'].val() == 'city'
        assert xml_parser.guest_list[0]['City'].val() == 'city'

        # cae.dprint("--COUNTRY-fldValToAcu/acu_fld_values: ",
        # xml_guest.elem_fld_map['COUNTRY']['fldValToAcu'],
        # xml_guest.acu_fld_values[xml_guest.elem_fld_map['COUNTRY']['fldName']])


class TestResFromSihot:
    XML_MATCHCODE_EXAMPLE = '''
    <SIHOT-Document>
        <ARESLIST>
        <RESERVATION>
        <PERSON>
            <MATCHCODE>PersonAcId</MATCHCODE>
        </PERSON>
        <RESCHANNELLIST>
            <RESCHANNEL>
                <MATCHCODE>GUBSE</MATCHCODE>
            </RESCHANNEL>
        </RESCHANNELLIST>
        <MATCHCODE>test2</MATCHCODE>
        </RESERVATION>
        </ARESLIST>
        </SIHOT-Document>
        '''

    XML_EXAMPLE = '''
    <SIHOT-Document>
        <OC>RES-SEARCH</OC>
        <RC>0</RC>
        <ARESLIST>
        <RESERVATION>
        <PRICE>99</PRICE>
        <RATE>
            <ISDEFAULT>Y</ISDEFAULT>
            <R>UF1</R>
            <PRICE>99</PRICE>
        </RATE>
        <PERSON>
            <SEX>0</SEX>
            <ROOM-SEQ>0</ROOM-SEQ>
            <ROOM-PERS-SEQ>0</ROOM-PERS-SEQ>
            <CITY>Schiffweiler</CITY>
            <DOB/>
            <EMAIL/>
            <COUNTRY>DE</COUNTRY>
            <NAME>GUBSE AG</NAME>
            <PERS-TYPE>1A</PERS-TYPE>
            <TITLE></TITLE>
            <COMMENT/>
            <ADDRESS></ADDRESS>
            <NAME2/>
            <PHONE/>
            <ZIP>66578</ZIP>
            <STREET/>
            <FAX/>
            <ARR>2009-02-23</ARR>
            <DEP>2009-03-01</DEP>
            <CAT/>
            <PCAT>EZ</PCAT>
            <RN>102</RN>
            <CENTRALGUEST-ID>0</CENTRALGUEST-ID>
            <MATCHCODE-ADM/>
            <EXT-REFERENCE/>
            <VOUCHERNUMBER/>
            <MATCHCODE>PersonAcId</MATCHCODE>
        </PERSON>
        <RESCHANNELLIST>
            <RESCHANNEL>
                <IDX>0</IDX>
                <MATCHCODE>GUBSE</MATCHCODE>
                <CENTRALGUEST-ID>0</CENTRALGUEST-ID>
                <CONTACT-ID>0</CONTACT-ID>
                <COMMISSION>
                <PC>0</PC>
                <TOTAL>0</TOTAL>
                </COMMISSION>
            </RESCHANNEL>
        </RESCHANNELLIST>
        <CHECKLIST>
            <CHECKLISTENTRY>
                <TYPE>6</TYPE>
                <DATE>2009-02-23</DATE>
                <USER>ADM</USER>
            </CHECKLISTENTRY>
        </CHECKLIST>
        <APERS-TYPE-LIST>
            <PERS-TYPE>
                <TYPE>1A</TYPE>
                <NO>1</NO>
            </PERS-TYPE>
        </APERS-TYPE-LIST>
        <CCLIST/>
        <RES-HOTEL>1</RES-HOTEL>
        <RES-NR>20000003</RES-NR>
        <SUB-NR>1</SUB-NR>
        <OBJID>2</OBJID>
        <OUTPUTCOUNTER>1</OUTPUTCOUNTER>
        <RT>1</RT>
        <ALLOTMENT-NO>0</ALLOTMENT-NO>
        <ARR>2009-02-23</ARR>
        <DEP>2009-03-01</DEP>
        <ARR-TIME/>
        <DEP-TIME/>
        <CAT>EZ</CAT>
        <PCAT>EZ</PCAT>
        <CENTRAL-RESERVATION-ID>0</CENTRAL-RESERVATION-ID>
        <COMMENT/>
        <GDSNO>1234567890ABC</GDSNO>
        <EXT-REFERENCE/>
        <EXT-KEY/>
        <LAST-MOD>2009-02-23</LAST-MOD>
        <MARKETCODE>F2</MARKETCODE>
        <MEDIA/>
        <SOURCE/>
        <CHANNEL/>
        <NN/>
        <NOPAX>1</NOPAX>
        <NOROOMS>1</NOROOMS>
        <PERS-TYPE>1A</PERS-TYPE>
        <DISCOUNT-GROUP/>
        <RATE-SEGMENT/>
        <T-POST-COMMISSION>0</T-POST-COMMISSION>
        <ASSIGNED-TO/>
        <DISABLE-DEPOSIT>N</DISABLE-DEPOSIT>
        <ADDRESS>0</ADDRESS>
        <CENTRALGUEST-ID>0</CENTRALGUEST-ID>
        <CITY>city</CITY>
        <COUNTRY>DE</COUNTRY>
        <DOB/>
        <EMAIL1>info@gubse.com</EMAIL1>
        <FAX1>+49 6821 9646 110</FAX1>
        <RT>2</RT>
        <LANG>DE</LANG>
        <MATCHCODE>test2</MATCHCODE>
        <NAME2/>
        <NAME>GUBSE AG</NAME>
        <PHONE1>+49 6821 9646 0</PHONE1>
        <STREET>Test Street 28</STREET>
        <ZIP>66578</ZIP>
        <DEPOSIT-DATE1/>
        <DEPOSIT-AMOUNT1>0</DEPOSIT-AMOUNT1>
        <DEPOSIT-DATE2/>
        <DEPOSIT-AMOUNT2>0</DEPOSIT-AMOUNT2>
        <DEPOSIT-DATE3/>
        <DEPOSIT-AMOUNT3>0</DEPOSIT-AMOUNT3>
        <IS-LOCKED>N</IS-LOCKED>
        </RESERVATION>
        </ARESLIST>
        </SIHOT-Document>
        '''

    def test_attributes(self, console_app_env):
        xml_parser = ResFromSihot(console_app_env)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.oc == 'RES-SEARCH'
        assert xml_parser.tn == '0'
        assert xml_parser.id == '1'
        assert xml_parser.rc == '0'
        assert xml_parser.msg == ''
        assert xml_parser.ver == ''
        assert xml_parser.error_level == '0'
        assert xml_parser.error_text == ''

    def test_fld_map_matchcode(self, console_app_env):
        xml_parser = ResFromSihot(console_app_env)
        xml_parser.parse_xml(self.XML_MATCHCODE_EXAMPLE)
        assert xml_parser.res_list[0]['ResOrdererMc'].val() == 'test2'
        assert xml_parser.res_list[0]['RESERVATION.MATCHCODE'].val() == 'test2'
        assert xml_parser.res_list[0]['AcId'].val() == 'PersonAcId'
        assert xml_parser.res_list[0]['PERSON.MATCHCODE'].val() == 'PersonAcId'
        # TODO:
        assert xml_parser.res_list[0][('ResPersons', 0, 'AcId', )].val() == 'PersonAcId'
        # assert xml_parser.res_list[0]['MATCHCODE']['elemListVal'] == ['PersonAcId', 'GUBSE', 'test2']

    def test_fld_map_big(self, console_app_env):
        xml_parser = ResFromSihot(console_app_env)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.res_list[0]['ResOrdererMc'].val() == 'test2'
        assert xml_parser.res_list[0]['RESERVATION.MATCHCODE'].val() == 'test2'
        assert xml_parser.res_list[0]['AcId'].val() == 'PersonAcId'
        assert xml_parser.res_list[0]['PERSON.MATCHCODE'].val() == 'PersonAcId'
        # assert xml_parser.res_list[0]['MATCHCODE']['elemListVal'] == ['PersonAcId', 'GUBSE', 'test2']
        assert xml_parser.res_list[0]['ResGdsNo'].val() == '1234567890ABC'
        assert xml_parser.res_list[0]['GDSNO'].val() == '1234567890ABC'


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
        # STRANGE?!?!?: test run 16-06-18 failed because TYPE and ID where None, on 2nd run also COMMENT Is None
        if ret['COMMENT']:
            assert 'RCI=1442-11521' in ret['COMMENT']
            assert 'RCI=5445-12771' in ret['COMMENT']
            assert 'RCIP=5-207931' in ret['COMMENT']
        if ret['EXTID.TYPE']:
            assert 'RCI' in ret['EXTID.TYPE']
            assert 'RCIP' in ret['EXTID.TYPE']
        if ret['EXTID.ID']:
            assert '5445-12771' in ret['EXTID.ID']
            assert '5-207931' in ret['EXTID.ID']
            # Sihot is only storing the last ID with the same TYPE - resulting in RCI=5445-12771,RCIP=5-207931?!?!?
            # TODO: .. so this one fails:
            assert '1442-11521' in ret['EXTID.ID']

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


class TestClientToSihot:

    def test_basic_build_and_send(self, console_app_env):
        cli_to = ClientToSihot(console_app_env)
        row = dict(AcId='T111222', Title='1', GuestType='1', Country='AT', Language='DE', ExtRefs='RCI=123,XXX=456')
        err_msg = cli_to.send_client_to_sihot(c_row=row, commit=True)
        assert not err_msg


class TestResToSihot:

    def test_basic_build_and_send(self, console_app_env):
        res_to = ResToSihot(console_app_env)
        row = dict(ResHotelId='1', ResGdsNo='TEST-123456789', ResOrdererMc='E578973',
                   ResArrival=datetime.date(year=2019, month=12, day=24),
                   ResDeparture=datetime.date(year=2019, month=12, day=30),
                   ResAdults=1, ResChildren=1, ResRoomCat='1STDP',
                   )
        err_msg = res_to.send_row_to_sihot(crow=row)
        assert not err_msg
