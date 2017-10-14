import datetime
# import pytest

from sxmlif import SihotXmlParser, Response, GuestFromSihot, ResFromSihot, SihotXmlBuilder, \
    USE_KERNEL_FOR_CLIENTS_DEF, MAP_CLIENT_DEF


class TestAvailCats:
    def test_all_hotel_all_cats(self, avail_cats):
        ret = avail_cats.avail_rooms() # hotel_id='2')
        assert isinstance(ret, dict)
        assert len(ret)

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

    def test_avail_rooms_with_studio_cat(self, avail_cats):
        day = datetime.date(2017, 10, 7)
        ret = avail_cats.avail_rooms(hotel_id='2', room_cat='STDO', from_date=day, to_date=day)
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDO' in ret
        ret = avail_cats.avail_rooms(hotel_id='4', room_cat='STDP', from_date=day, to_date=day)  # no STDO in PBC
        assert isinstance(ret, dict)
        assert len(ret)
        assert 'STDP' in ret


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


class TestResponse:
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
        xml_parser = Response(console_app_env)
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

    def test_col_map(self, console_app_env):
        xml_parser = GuestFromSihot(console_app_env)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.elem_col_map['MATCHCODE']['elemVal'] == 'test2'
        assert xml_parser.acu_col_values['CD_CODE'] == 'test2'
        assert xml_parser.elem_col_map['CITY']['elemVal'] == 'city'
        assert xml_parser.acu_col_values['CD_CITY'] == 'city'

        # cae.dprint("--COUNTRY-colValToAcu/acu_col_values: ",
        # xml_guest.elem_col_map['COUNTRY']['colValToAcu'],
        # xml_guest.acu_col_values[xml_guest.elem_col_map['COUNTRY']['colName']])

    def test_client_to_acu(self, console_app_env):
        xml_parser = GuestFromSihot(console_app_env)
        xml_parser.parse_xml(self.XML_EXAMPLE)

        from AcuServer import client_to_acu

        error_msg, pk = client_to_acu(xml_parser.acu_col_values, console_app_env)
        assert not error_msg
        assert pk == 'test2'


class TestResFromSihot:
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
        <MATCHCODE/>
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

    def test_col_map(self, console_app_env):
        xml_parser = ResFromSihot(console_app_env)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.res_list[0]['MATCHCODE']['elemVal'] == 'test2'
        assert xml_parser.res_list[0]['MATCHCODE']['elemListVal'] == ['', 'GUBSE', 'test2']
        assert xml_parser.res_list[0]['GDSNO']['elemVal'] == '1234567890ABC'


class TestSihotXmlBuilder:
    def test_create_xml(self, console_app_env):
        xml_builder = SihotXmlBuilder(console_app_env,
                                      use_kernel_interface=USE_KERNEL_FOR_CLIENTS_DEF, col_map=MAP_CLIENT_DEF)
        xml_builder.beg_xml('TEST_OC')
        xml_builder.add_tag('EMPTY')
        xml_builder.add_tag('DEEP', xml_builder.new_tag('DEEPER', 'value'))
        test_date = xml_builder.convert_value_to_xml_string(datetime.datetime.now())
        xml_builder.add_tag('DATE', test_date)
        xml_builder.end_xml()
        console_app_env.dprint('####  New XML created: ', xml_builder.xml)
        if xml_builder.use_kernel_interface:
            assert xml_builder.xml == '<?xml version="1.0" encoding="utf8"?>\n<SIHOT-Document>\n<SIHOT-XML-REQUEST>' + \
                '\n<REQUEST-TYPE>TEST_OC</REQUEST-TYPE><EMPTY></EMPTY><DEEP><DEEPER>value</DEEPER></DEEP>' + \
                '<DATE>' + test_date + '</DATE>\n</SIHOT-XML-REQUEST>\n</SIHOT-Document>'
        else:
            assert xml_builder.xml == '<?xml version="1.0" encoding="utf8"?>\n<SIHOT-Document>\n' + \
                '<OC>TEST_OC</OC><TN>2</TN><EMPTY></EMPTY><DEEP><DEEPER>value</DEEPER></DEEP>' + \
                '<DATE>' + test_date + '</DATE>\n</SIHOT-Document>'


class TestGuestSearch:
    def test_get_guest_with_test_client(self, guest_search, create_test_guest):
        ret = guest_search.get_guest(create_test_guest.objid)
        assert guest_search.response.objid == create_test_guest.objid     # OBJID passed only to response (ret is empty)
        # also MATCHCODE element is in response (and empty in ret): assert ret['MATCHCODE']==create_test_guest.matchcode
        assert guest_search.response.matchcode == create_test_guest.matchcode
        assert guest_search.response.objid == create_test_guest.objid
        assert ret['NAME-1'] == create_test_guest.surname
        assert ret['NAME-2'] == create_test_guest.forename
        assert ret['T-GUEST'] == create_test_guest.guest_type

    def test_get_guest_with_10_ext_refs(self, guest_search):
        objid = guest_search.get_objid_by_matchcode('E396693')
        assert objid
        ret = guest_search.get_guest(objid)
        assert ret['MATCH-ADM'] == '4806-00208'
        assert 'RCI' in ret['TYPE']
        assert 'RCIP' in ret['TYPE']
        assert 'RCI=1442-11521' in ret['COMMENT']
        assert '5445-12771' in ret['ID']
        assert '5-207931' in ret['ID']
        # Sihot is only storing the last ID with the same TYPE - resulting in RCI=5445-12771,RCIP=5-207931?!?!?
        # .. so this one fails: assert '1442-11521' in ret['ID']

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


class TestClientFromAcuToSihot:
    def test_couple_with_different_surname(self, acu_guest):
        error_msg = acu_guest.fetch_from_acu_by_cd('E007434')  # Christopher J. Smith & Irene Fitzgerald
        assert error_msg == ''
        if not error_msg:
            row = acu_guest.cols
            assert row['CD_CODE'] == 'E007434'
            assert row['CD_CODE2'] == 'E007434P2'
            assert str(row['SIHOT_SALUTATION1']) == '1'
            assert str(row['SIHOT_SALUTATION2']) == '2'
            assert str(row['SIHOT_GUESTTYPE1']) == '1'
            assert str(row['SIHOT_GUESTTYPE2']) == '0'
            assert row['SIHOT_COUNTRY'] == 'GB'
            assert row['SIHOT_LANG'] == 'EN'
            error_msg = acu_guest.send_client_to_sihot(row, commit=True)
            assert not error_msg

    def test_couple_with_same_surname(self, acu_guest):
        error_msg = acu_guest.fetch_from_acu_by_cd('D496085')  # Nicholas & Anne Smith
        assert not error_msg
        if not error_msg:
            row = acu_guest.cols
            assert row['CD_CODE'] == 'D496085'
            assert row['CD_CODE2'] == 'D496085P2'
            assert str(row['SIHOT_SALUTATION1']) == 'None'
            assert str(row['SIHOT_SALUTATION2']) == 'None'
            assert str(row['SIHOT_GUESTTYPE1']) == '1'
            assert str(row['SIHOT_GUESTTYPE2']) == '0'
            assert row['SIHOT_COUNTRY'] == 'ES'
            assert row['SIHOT_LANG'] == 'ES'
            error_msg = acu_guest.send_client_to_sihot(row, commit=True)
            assert not error_msg

    def test_female_client(self, acu_guest):
        error_msg = acu_guest.fetch_from_acu_by_acu('E119378')       # Marlene Guy - has no T_LOG entries
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count <= 1

        error_msg = acu_guest.fetch_from_acu_by_cd('E119378')
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count == 1
            row = acu_guest.cols
            assert row['CD_CODE'] == 'E119378'
            assert row['CD_CODE2'] is None
            assert str(row['SIHOT_SALUTATION1']) == '2'
            assert str(row['SIHOT_SALUTATION2']) == 'None'
            assert str(row['SIHOT_GUESTTYPE1']) == '1'
            assert str(row['SIHOT_GUESTTYPE2']) == 'None'
            assert row['SIHOT_COUNTRY'] == 'GB'
            assert row['SIHOT_LANG'] == 'EN'
            error_msg = acu_guest.send_client_to_sihot(row, commit=True)
            assert not error_msg

    def test_couple_rci_number_without_res(self, acu_guest):
        error_msg = acu_guest.fetch_from_acu_by_cd('E128745')  # test Pax2 deletion/change-of-pax1 - has no LOG entry
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count == 1
            row = acu_guest.cols
            assert row['CD_CODE'] == 'E128745'
            assert row['CD_CODE2'] == 'E128745P2'
            assert str(row['SIHOT_SALUTATION1']) == '1'
            assert str(row['SIHOT_SALUTATION2']) == '2'
            assert str(row['SIHOT_GUESTTYPE1']) == '1'
            assert str(row['SIHOT_GUESTTYPE2']) == '0'
            assert row['SIHOT_COUNTRY'] == 'GB'
            assert row['SIHOT_LANG'] == 'EN'
            error_msg = acu_guest.send_client_to_sihot(row, commit=True)
            assert not error_msg

    def test_couple_with_rci_without_res(self, acu_guest):
        error_msg = acu_guest.fetch_from_acu_by_cd('E128746')       # has no log entry
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count == 1
            row = acu_guest.cols
            assert row['CD_CODE'] == 'E128746'
            assert row['CD_CODE2'] == 'E128746P2'
            assert str(row['SIHOT_SALUTATION1']) == '1'
            assert str(row['SIHOT_SALUTATION2']) == '2'
            assert str(row['SIHOT_GUESTTYPE1']) == '1'
            assert str(row['SIHOT_GUESTTYPE2']) == '0'
            assert row['SIHOT_COUNTRY'] == 'GB'
            assert row['SIHOT_LANG'] == 'EN'
            error_msg = acu_guest.send_client_to_sihot(row, commit=True)
            assert not error_msg

    def test_pax1_with_doctor_title(self, acu_guest):  # G558956/G561518 - same family with future res
        error_msg = acu_guest.fetch_from_acu_by_acu(acu_id='G561518')
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count <= 1
            if acu_guest.row_count:
                row = acu_guest.cols
                assert row['CD_CODE'] == 'G561518'
                assert row['CD_CODE2'] == 'G561518P2'
                assert str(row['SIHOT_SALUTATION1']) == 'None'
                assert str(row['SIHOT_SALUTATION2']) == '1'
                assert str(row['SIHOT_TITLE1']) == '1'
                assert str(row['SIHOT_TITLE2']) == 'None'
                assert str(row['SIHOT_GUESTTYPE1']) == '1'
                assert str(row['SIHOT_GUESTTYPE2']) == '0'
                assert row['SIHOT_COUNTRY'] == 'AT'
                assert row['SIHOT_LANG'] == 'DE'
                error_msg = acu_guest.send_client_to_sihot(row, commit=True)
                assert not error_msg

    def test_both_pax_with_doctor_title(self, acu_guest):  # G558956/G561518 - same family with future res
        error_msg = acu_guest.fetch_from_acu_by_acu(acu_id='G558956')
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count <= 1
            if acu_guest.row_count:
                row = acu_guest.cols
                assert row['CD_CODE'] == 'G558956'
                assert row['CD_CODE2'] == 'G558956P2'
                assert str(row['SIHOT_SALUTATION1']) == 'None'
                assert str(row['SIHOT_SALUTATION2']) == 'None'
                assert str(row['SIHOT_TITLE1']) == '1'
                assert str(row['SIHOT_TITLE2']) == '1'
                assert str(row['SIHOT_GUESTTYPE1']) == '1'
                assert str(row['SIHOT_GUESTTYPE2']) == '0'
                assert row['SIHOT_COUNTRY'] == 'AT'
                assert row['SIHOT_LANG'] == 'DE'
                error_msg = acu_guest.send_client_to_sihot(row, commit=True)
                assert not error_msg

    def test_both_pax_are_doctors_and_have_salutation(self, acu_guest):  # Y203585/HUN - Name decoded wrongly with ISO
        error_msg = acu_guest.fetch_from_acu_by_cd('Y203585')
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count == 1
            row = acu_guest.cols
            assert row['CD_CODE'] == 'Y203585'
            assert row['CD_CODE2'] == 'Y203585P2'
            assert str(row['SIHOT_SALUTATION1']) == '1'
            assert str(row['SIHOT_SALUTATION2']) == '1'
            assert str(row['SIHOT_TITLE1']) == '1'
            assert str(row['SIHOT_TITLE2']) == '1'
            assert str(row['SIHOT_GUESTTYPE1']) == '1'
            assert str(row['SIHOT_GUESTTYPE2']) == '0'
            assert row['SIHOT_COUNTRY'] == 'HU'
            assert row['SIHOT_LANG'] is None
            error_msg = acu_guest.send_client_to_sihot(row, commit=True)
            assert not error_msg

    def test_client_with_10_ext_refs(self, acu_guest):  # E396693 - fetch from unsynced
        error_msg = acu_guest.fetch_from_acu_by_acu('E396693')
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count <= 1
            if acu_guest.row_count:
                row = acu_guest.cols
                assert row['CD_CODE'] == 'E396693'
                # RCI=1442-11521,RCI=1442-55556,RCI=2429-09033,RCI=2429-09777,RCI=2429-12042,RCI=2429-13656,
                # .. RCI=2429-55556,RCI=2972-00047,RCI=5445-12771,RCIP=5-207931
                assert 'RCI=1442-11521' in row['EXT_REFS']
                assert 'RCI=2972-00047' in row['EXT_REFS']
                assert 'RCIP=5-207931' in row['EXT_REFS']
                assert len(row['EXT_REFS'].split(',')) == 10
                error_msg = acu_guest.send_client_to_sihot(row, commit=True)
                # Sihot is only storing the last ID with the same TYPE - resulting in RCI=5445-12771,RCIP=5-207931?!?!?
                assert not error_msg

    def test_client_with_objid_but_deleted_in_sihot(self, acu_guest):  # E610488, ObjId=294
        error_msg = acu_guest.fetch_from_acu_by_cd('E610488')
        assert not error_msg
        if not error_msg:
            assert acu_guest.row_count == 1
            row = acu_guest.cols
            assert row['CD_CODE'] == 'E610488'
            assert row['CD_CODE2'] is None
            # overwrite objid with not existing one
            acu_guest.cols['CD_SIHOT_OBJID'] = int(row['CD_SIHOT_OBJID']) + 1 if row['CD_SIHOT_OBJID'] else 99999
            error_msg = acu_guest.send_client_to_sihot(row, commit=True)
            assert not error_msg or error_msg.endswith('No guest found.')


class TestResFromAcuToSihot:

    def test_client_with_sp_usage(self, acu_res):
        # Silverpoint Usage 2016 - 884 request on 29-09-16 but not synced because of resOcc/RO_SIHOT_RATE filter
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E578973'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count == 0

    def test_client_with_reforma_res(self, acu_res):
        # --E420545: 371 / 27 = Reforma Reforma(~330 Arr < 5.7.16 - checked on 23.7.) - Not synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E420545'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count == 0

    def test_fx_vuelo_res(self, acu_res):
        # --E599377: 130 / 0 - later 4 FX Vuelo(~180 Arr:6.5. - 23.6.16) - Not synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E599377'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count == 0

    def test_disney_res(self, acu_res):
        # --E558549: 167 / 83 - later 437 = Inventory Disney(8 Arr:12.8. - 30.12.16) - not synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E558549'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count == 0

    def test_pax1_with_doctor_title(self, acu_res):
        # G558956/G561518 - same family with future res - 13 res in HMC - not synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'G558956'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count == 0

    """
    def _old_test_excluded_rental_ota_res_occ(self, acu_res):
        # 1 RR request in PBC arriving 13-10-16
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E610488'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count == 0
        error_msg = acu_res.fetch_from_acu_by_cd('E610488')
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count >= 1
    """

    #################################################################
    #  SENDING TO SIHOT PMS

    def test_guest_booking_in_the_past(self, acu_res):
        # 2 guest requests (1 PBC, 1 BHC) on behave of owner E113650
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E421535'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count in (0, 1)
            error_msg = acu_res.send_rows_to_sihot(break_on_error=False, commit_last_row=True)
            assert not error_msg

    def test_tc_booking_with_kids_in_the_future(self, acu_res):
        # 1 request in PBC on behave of thomas cook
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'N616715'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count in (0, 1)
            error_msg = acu_res.send_rows_to_sihot(break_on_error=False, commit_last_row=True)
            assert not error_msg

    def test_remove_past_no_room_and_future_cxl(self, acu_res):
        # 23 PBC requests (2 future) - 21 req synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'F385312'")
        assert not error_msg
        if not error_msg:
            assert 0 <= acu_res.row_count <= 23
            error_msg = acu_res.send_rows_to_sihot(break_on_error=False, commit_last_row=True)
            assert not error_msg

    def test_remove_res_occ_and_cancelled(self, acu_res):
        # 20 PBC requests, 2 excluded because BK resOcc or cancelled/past/no-room
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'Z007184'")
        assert not error_msg
        if not error_msg:
            assert 0 <= acu_res.row_count <= 20
            error_msg = acu_res.send_rows_to_sihot(break_on_error=False, commit_last_row=True)
            assert not error_msg

    def test_exclude_cancelled_with_break_and_row_commit(self, acu_res):
        # 21 PBC requests
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E499163'")
        assert not error_msg
        if not error_msg:
            assert 0 <= acu_res.row_count <= 21
            error_msg = acu_res.send_rows_to_sihot(break_on_error=True, commit_per_row=True)
            assert not error_msg

    """
    def _old_test_15_requests_by_cd(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'Z136231'")
        assert not error_msg
        if not error_msg:
            assert acu_res.row_count == 15
            error_msg = acu_res.send_rows_to_sihot(break_on_error=False, commit_last_row=True)
            assert not error_msg

    def _old_test_res_with_euro_char_fetched_by_cd(self, acu_res):
        # 20 PBC reservations and one with Euro-sign (in reservation comment of transfer on 10-10-2014)
        # .. and some with wrong/different arrival client id - e.g. E436263 is 1st RU within 3-4 wk requests/RH
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'E374408'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) in (0, 20)
            assert '€' in [r['SIHOT_NOTE'] for r in rows if r['RUL_PRIMARY'] == '864355'][0]
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg

    # FB examples with board: F468913, F614205, V576425, I615916
    def _old_test_fb_with_board1(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'F468913'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 1
            for row in rows:
                assert row['RUL_SIHOT_HOTEL'] in (1, 4)
                error_msg = acu_res.send_row_to_sihot(crow=row, commit=True)
                assert not error_msg

    def _old_test_fb_with_board2(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'F614205'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 1
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg

    def _old_test_fb_with_board3(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'V576425'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 2
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg
    """

    def test_fb_with_board4(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'I615916'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 2
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg

    # test ER/External Rental: G522633, E588450, E453121, Z124997
    def test_external_rental1(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'G522633'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 2
            for row in rows:
                assert row['RUL_SIHOT_HOTEL'] in (1, 4)
                error_msg = acu_res.send_row_to_sihot(crow=row, commit=True)
                assert 'has Check-Ins' in error_msg or 'This reservation has been settled already!' in error_msg

    def test_external_rental2(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'E588450'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 2
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg

    def test_external_rental3(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'E453121'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 2
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg

    """
    def test_external_rental4(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'Z124997'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) >= 15
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg

    def _old_test_any_resort1(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'C612158'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 1
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg

    def _old_test_any_resort2(self, acu_res):
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="CD_CODE = 'E543935'")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 4  # only one is for ANY and future - 3 others in past/2014
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg

    def _old_test_tc_booking_created_via_sync_and_then_deleted_via_res_import(self, acu_res):
        # RUL_CODE == 4785629
        error_msg = acu_res.fetch_all_valid_from_acu(where_group_order="RUL_PRIMARY = 1023128")
        assert not error_msg
        if not error_msg:
            rows = acu_res.rows
            assert len(rows) == 1
            error_msg = acu_res.send_rows_to_sihot()
            assert not error_msg
    """
