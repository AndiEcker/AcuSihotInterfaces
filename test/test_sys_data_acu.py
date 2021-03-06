import pytest

from ae.sys_data import FAD_FROM
from ae.sys_data_sh import ClientFromSihot, ResFromSihot
from sys_data_acu import AcuClientToSihot, AcuResToSihot, AcumenClient, SDI_ACU


@pytest.fixture()
def acu_client(cons_app):
    return AcuClientToSihot(cons_app)


@pytest.fixture()
def acu_res(cons_app):
    return AcuResToSihot(cons_app)


class TestClientFromAcuToSihot:
    def test_couple_with_different_surname(self, acu_client):
        error_msg = acu_client.fetch_from_acu_by_cd('E007434')  # Christopher J. Smith & Irene Fitzgerald
        assert not error_msg
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'E007434'
        assert rec.val('CD_CODE2') == 'E007434P2'
        assert str(rec.val('SIHOT_SALUTATION1')) == '1'
        assert str(rec.val('SIHOT_SALUTATION2')) == '2'
        assert str(rec.val('SIHOT_GUESTTYPE1')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE2')) == '0'
        assert rec.val('SIHOT_COUNTRY') == 'GB'
        assert rec.val('SIHOT_LANG') == 'EN'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_couple_with_same_surname(self, acu_client):
        error_msg = acu_client.fetch_from_acu_by_cd('D496085')  # Nicholas & Anne Smith
        assert not error_msg
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'D496085'
        assert rec.val('CD_CODE2') == 'D496085P2'
        assert str(rec.val('SIHOT_SALUTATION1')) == ''
        assert str(rec.val('SIHOT_SALUTATION2')) == ''
        assert str(rec.val('SIHOT_GUESTTYPE1')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE2')) == '0'
        assert rec.val('SIHOT_COUNTRY') == 'ES'
        assert rec.val('SIHOT_LANG') == 'ES'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_female_client(self, acu_client):
        error_msg = acu_client.fetch_from_acu_by_cd('E119378')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'E119378'
        assert rec.val('CD_CODE2') == ''
        assert str(rec.val('SIHOT_SALUTATION1')) == '2'
        assert str(rec.val('SIHOT_SALUTATION2')) == ''
        assert str(rec.val('SIHOT_GUESTTYPE1')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE2')) == ''
        assert rec.val('SIHOT_COUNTRY') == 'GB'
        assert rec.val('SIHOT_LANG') == 'EN'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_couple_rci_number_without_res(self, acu_client):
        error_msg = acu_client.fetch_from_acu_by_cd('E128745')  # test Pax2 deletion/change-of-pax1 - has no LOG entry
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'E128745'
        assert rec.val('CD_CODE2') == 'E128745P2'
        assert str(rec.val('SIHOT_SALUTATION1')) == '1'
        assert str(rec.val('SIHOT_SALUTATION2')) == '2'
        assert str(rec.val('SIHOT_GUESTTYPE1')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE2')) == '0'
        assert rec.val('SIHOT_COUNTRY') == 'GB'
        assert rec.val('SIHOT_LANG') == 'EN'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_couple_with_rci_without_res(self, acu_client):
        error_msg = acu_client.fetch_from_acu_by_cd('E128746')       # has no log entry
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'E128746'
        assert rec.val('CD_CODE2') == 'E128746P2'
        assert str(rec.val('SIHOT_SALUTATION1')) == '1'
        assert str(rec.val('SIHOT_SALUTATION2')) == '2'
        assert str(rec.val('SIHOT_GUESTTYPE1')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE2')) == '0'
        assert rec.val('SIHOT_COUNTRY') == 'GB'
        assert rec.val('SIHOT_LANG') == 'EN'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_pax1_with_doctor_title(self, acu_client):  # G558956/G561518 - same family with future res
        error_msg = acu_client.fetch_from_acu_by_cd(acu_id='G561518')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'G561518'
        assert rec.val('CD_CODE2') == 'G561518P2'
        assert str(rec.val('SIHOT_SALUTATION1')) == ''
        assert str(rec.val('SIHOT_SALUTATION2')) == '1'
        assert str(rec.val('SIHOT_TITLE1')) == '1'
        assert str(rec.val('SIHOT_TITLE2')) == ''
        assert str(rec.val('SIHOT_GUESTTYPE1')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE2')) == '0'
        assert rec.val('SIHOT_COUNTRY') == 'AT'
        assert rec.val('SIHOT_LANG') == 'DE'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_both_pax_with_doctor_title(self, acu_client):  # G558956/G561518 - same family with future res
        error_msg = acu_client.fetch_from_acu_by_cd(acu_id='G558956')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'G558956'
        assert rec.val('CD_CODE2') == 'G558956P2'
        assert str(rec.val('SIHOT_SALUTATION1')) == ''
        assert str(rec.val('SIHOT_SALUTATION2')) == ''
        assert str(rec.val('SIHOT_TITLE1')) == '1'
        assert str(rec.val('SIHOT_TITLE2')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE1')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE2')) == '0'
        assert rec.val('SIHOT_COUNTRY') == 'AT'
        assert rec.val('SIHOT_LANG') == 'DE'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_both_pax_are_doctors_and_have_salutation(self, acu_client):  # Y203585/HUN - Name decoded wrongly with ISO
        error_msg = acu_client.fetch_from_acu_by_cd('Y203585')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'Y203585'
        assert rec.val('CD_CODE2') == 'Y203585P2'
        assert str(rec.val('SIHOT_SALUTATION1')) == '1'
        assert str(rec.val('SIHOT_SALUTATION2')) == '1'
        assert str(rec.val('SIHOT_TITLE1')) == '1'
        assert str(rec.val('SIHOT_TITLE2')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE1')) == '1'
        assert str(rec.val('SIHOT_GUESTTYPE2')) == '0'
        assert rec.val('SIHOT_COUNTRY') == 'HU'
        assert rec.val('SIHOT_LANG') == ''
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_client_with_10_ext_refs(self, acu_client):  # E396693 - fetch from unsynced
        error_msg = acu_client.fetch_from_acu_by_cd('E396693')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'E396693'
        # RCI=1442-11521,RCI=1442-55556,RCI=2429-09033,RCI=2429-09777,RCI=2429-12042,RCI=2429-13656,
        # .. RCI=2429-55556,RCI=2972-00047,RCI=5445-12771,RCIP=5-207931
        assert 'RCI=1442-11521' in rec.val('EXT_REFS')
        assert 'RCI=2972-00047' in rec.val('EXT_REFS')
        assert 'RCI=5-207931' in rec.val('EXT_REFS')
        assert len(rec.val('EXT_REFS').split(',')) >= 12
        # already done by fetch: rec.pull(SDI_ACU)
        assert len(rec.val('ExtRefs')) >= 12
        assert any(_ for _ in rec.val('ExtRefs') if _['Type'] == 'RCI' and _['Id'] == '1442-11521')
        assert any(_ for _ in rec.val('ExtRefs') if _['Type'] == 'RCI' and _['Id'] == '2972-00047')
        assert any(_ for _ in rec.val('ExtRefs') if _['Type'] == 'RCI' and _['Id'] == '5-207931')
        error_msg = acu_client.send_client_to_sihot(rec)
        # Sihot is only storing the last ID with the same TYPE - resulting in RCI=5445-12771,RCIP=5-207931?!?!?
        assert not error_msg

    def test_client_with_objid_but_deleted_in_sihot(self, acu_client):  # E610488, ObjId=294
        error_msg = acu_client.fetch_from_acu_by_cd('E610488')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec.val('CD_CODE') == 'E610488'
        assert rec.val('CD_CODE2') == ''
        # overwrite objid with not existing one
        rec['CD_SIHOT_OBJID'] = int(rec.val('CD_SIHOT_OBJID')) + 1 if rec.val('CD_SIHOT_OBJID') else 99999
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg or error_msg.endswith('No guest found.')

    #################################################################
    #  SENDING TO SIHOT PMS

    def test_guest_booking_in_the_past(self, acu_res):
        # 2 guest requests (1 PBC, 1 BHC) on behave of owner E113650
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E421535'")
        assert not error_msg
        assert len(acu_res.recs) in (0, 1)
        error_msg = acu_res.send_res_recs_to_sihot(break_on_error=False)
        assert not error_msg

    def test_tc_booking_with_kids_in_the_future(self, acu_res):
        # 1 request in PBC on behave of thomas cook
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'N616715'")
        assert not error_msg
        assert len(acu_res.recs) in (0, 1)
        error_msg = acu_res.send_res_recs_to_sihot(break_on_error=False)
        assert not error_msg

    def test_remove_past_no_room_and_future_cxl(self, acu_res):
        # 23 PBC requests (2 future) - 21 req synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'F385312'")
        assert not error_msg
        assert 0 <= len(acu_res.recs) <= 23
        error_msg = acu_res.send_res_recs_to_sihot(break_on_error=False)
        assert not error_msg

    def test_remove_res_occ_and_cancelled(self, acu_res):
        # 20 PBC requests, 2 excluded because BK resOcc or cancelled/past/no-room
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'Z007184'")
        assert not error_msg
        assert 0 <= len(acu_res.recs) <= 20
        error_msg = acu_res.send_res_recs_to_sihot(break_on_error=False)
        assert not error_msg

    def test_exclude_cancelled_with_break_and_rec_commit(self, acu_res):
        # 21 PBC requests
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E499163'")
        assert not error_msg
        assert 0 <= len(acu_res.recs) <= 21
        error_msg = acu_res.send_res_recs_to_sihot()
        acu_res.ora_db.commit()
        assert not error_msg


class TestAcuServerParts:
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

    def test_send_client_to_acu(self, cons_app):
        xml_parser = ClientFromSihot(cons_app)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        acu_cl = AcumenClient(cons_app)
        error_msg, pk = acu_cl.save_client(xml_parser.rec)
        assert not error_msg
        assert pk == 'test2'


class TestClientFromSihot:
    XML_EXAMPLE = '''<?xml version="1.0" encoding="iso-8859-1"?>
    <SIHOT-Document>
        <OC>GUEST-CREATE</OC>
        <ID>1</ID>
        <TN>1</TN>
        <GUEST-PROFILE>
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
        </GUEST-PROFILE>
    </SIHOT-Document>'''

    def test_attributes(self, cons_app):
        xml_parser = ClientFromSihot(cons_app)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.oc == 'GUEST-CREATE'
        assert xml_parser.tn == '1'
        assert xml_parser.id == '1'
        assert xml_parser.rc == '0'
        assert xml_parser.msg == ''
        assert xml_parser.ver == ''
        assert xml_parser.error_level == '0'
        assert xml_parser.error_text == ''

    def test_elem_map(self, cons_app):
        xml_parser = ClientFromSihot(cons_app)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        rec = xml_parser.client_list[0]
        assert rec['AcuId'] == 'test2'
        assert rec['MATCHCODE'] == 'test2'
        assert rec['City'] == 'city'
        assert rec['CITY'] == 'city'

        # cae.dpo("--COUNTRY-fldValToAcu/acu_fld_vals: ",
        # xml_guest.elem_fld_map['COUNTRY']['fldValToAcu'],
        # xml_guest.acu_fld_vals[xml_guest.elem_fld_map['COUNTRY']['fldName']])


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

    def test_attributes(self, cons_app):
        xml_parser = ResFromSihot(cons_app)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.oc == 'RES-SEARCH'
        assert xml_parser.tn == '0'
        assert xml_parser.id == '1'
        assert xml_parser.rc == '0'
        assert xml_parser.msg == ''
        assert xml_parser.ver == ''
        assert xml_parser.error_level == '0'
        assert xml_parser.error_text == ''

    def test_fld_map(self, cons_app):
        xml_parser = ResFromSihot(cons_app)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.res_list.val(0, 'AcuId') == 'test2'
        assert xml_parser.res_list.val(0, 'RESERVATION.MATCHCODE') == 'test2'
        assert xml_parser.res_list.val(0, 'ResGdsNo') == '1234567890ABC'
        assert xml_parser.res_list.val(0, 'GDSNO') == '1234567890ABC'


class TestClientToSihot:
    def test_pax1_with_doctor_title(self, acu_client):  # G558956/G561518 - same family with future res
        error_msg = acu_client.fetch_from_acu_by_cd(acu_id='G561518')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec['AcuId'] == 'G561518'
        assert rec.val('AcuId_P') == 'G561518P2'
        assert str(rec['Salutation']) == ''
        assert str(rec['SIHOT_SALUTATION2']) == '1'
        assert str(rec['Title']) == '1'
        assert str(rec['SIHOT_TITLE2']) == ''
        assert str(rec['GuestType']) == '1'
        assert str(rec['SIHOT_GUESTTYPE2']) == '0'
        assert rec['Country'] == 'AT'
        assert rec['Language'] == 'DE'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_both_pax_with_doctor_title(self, acu_client):  # G558956/G561518 - same family with future res
        error_msg = acu_client.fetch_from_acu_by_cd(acu_id='G558956')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec['AcuId'] == 'G558956'
        assert rec['AcuId_P'] == 'G558956P2'
        assert str(rec['Salutation']) == ''
        assert str(rec['SIHOT_SALUTATION2']) == ''
        assert str(rec['Title']) == '1'
        assert str(rec['SIHOT_TITLE2']) == '1'
        assert str(rec['GuestType']) == '1'
        assert str(rec['SIHOT_GUESTTYPE2']) == '0'
        assert rec['Country'] == 'AT'
        assert rec['Language'] == 'DE'
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_both_pax_are_doctors_and_have_salutation(self, acu_client):  # Y203585/HUN - Name decoded wrongly with ISO
        error_msg = acu_client.fetch_from_acu_by_cd('Y203585')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec['AcuId'] == 'Y203585'
        assert rec.val('AcuId_P') == 'Y203585P2'
        assert str(rec['Salutation']) == '1'
        assert str(rec['SIHOT_SALUTATION2']) == '1'
        assert str(rec['Title']) == '1'
        assert str(rec['SIHOT_TITLE2']) == '1'
        assert str(rec['GuestType']) == '1'
        assert str(rec['SIHOT_GUESTTYPE2']) == '0'
        assert rec['Country'] == 'HU'
        assert rec['Language'] == ''
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg

    def test_client_with_10_ext_refs(self, acu_client):  # E396693 - fetch from unsynced
        error_msg = acu_client.fetch_from_acu_by_cd('E396693')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec['AcuId'] == 'E396693'
        # RCI=1442-11521,RCI=1442-55556,RCI=2429-09033,RCI=2429-09777,RCI=2429-12042,RCI=2429-13656,
        # .. RCI=2429-55556,RCI=2972-00047,RCI=5445-12771,RCIP=5-207931
        ext_refs = rec.val('ExtRefs', system=SDI_ACU, direction=FAD_FROM)
        assert 'RCI=1442-11521' in ext_refs
        assert 'RCI=2972-00047' in ext_refs
        assert 'RCI=5-207931' in ext_refs
        assert len(ext_refs.split(',')) >= 12
        # already done by fetch: rec.pull(SDI_ACU)
        assert any(_ for _ in rec.val('ExtRefs') if _['Type'] == 'RCI' and _['Id'] == '1442-11521')
        assert any(_ for _ in rec.val('ExtRefs') if _['Type'] == 'RCI' and _['Id'] == '2972-00047')
        assert any(_ for _ in rec.val('ExtRefs') if _['Type'] == 'RCI' and _['Id'] == '5-207931')
        error_msg = acu_client.send_client_to_sihot(rec)
        # Sihot is only storing the last ID with the same TYPE - resulting in RCI=5445-12771,RCIP=5-207931?!?!?
        assert not error_msg

    def test_client_with_objid_but_deleted_in_sihot(self, acu_client):  # E610488, ObjId=294
        error_msg = acu_client.fetch_from_acu_by_cd('E610488')
        assert not error_msg
        assert len(acu_client.recs) == 1
        rec = acu_client.recs[0]
        assert rec['AcuId'] == 'E610488'
        assert rec.val('AcuId_P') == ''
        # overwrite objid with not existing one
        rec['ShId'] = int(rec['ShId']) + 1 if rec['ShId'] else 99999
        error_msg = acu_client.send_client_to_sihot(rec)
        assert not error_msg or error_msg.endswith('No guest found.')


class TestResToSihot:

    def test_client_with_sp_usage(self, acu_res):
        # Silverpoint Usage 2016 - 884 request on 29-09-16 but not synced because of resOcc/RO_SIHOT_RATE filter
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E578973'")
        assert not error_msg
        assert len(acu_res.recs) == 0

    def test_client_with_reforma_res(self, acu_res):
        # --E420545: 371 / 27 = Reforma Reforma(~330 Arr < 5.7.16 - checked on 23.7.) - Not synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E420545'")
        assert not error_msg
        assert len(acu_res.recs) == 0

    def test_fx_vuelo_res(self, acu_res):
        # --E599377: 130 / 0 - later 4 FX Vuelo(~180 Arr:6.5. - 23.6.16) - Not synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E599377'")
        assert not error_msg
        assert len(acu_res.recs) == 0

    def test_disney_res(self, acu_res):
        # --E558549: 167 / 83 - later 437 = Inventory Disney(8 Arr:12.8. - 30.12.16) - not synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E558549'")
        assert not error_msg
        assert len(acu_res.recs) == 0

    def test_pax1_with_doctor_title(self, acu_res):
        # G558956/G561518 - same family with future res - 13 res in HMC - not synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'G558956'")
        assert not error_msg
        assert len(acu_res.recs) == 0

    #################################################################
    #  SENDING TO SIHOT PMS

    def test_guest_booking_in_the_past(self, acu_res):
        # 2 guest requests (1 PBC, 1 BHC) on behave of owner E113650
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E421535'")
        assert not error_msg
        assert len(acu_res.recs) in (0, 1)
        error_msg = acu_res.send_res_recs_to_sihot(break_on_error=False)
        assert not error_msg

    def test_tc_booking_with_kids_in_the_future(self, acu_res):
        # 1 request in PBC on behave of thomas cook
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'N616715'")
        assert not error_msg
        assert len(acu_res.recs) in (0, 1)
        error_msg = acu_res.send_res_recs_to_sihot(break_on_error=False)
        assert not error_msg

    def test_remove_past_no_room_and_future_cxl(self, acu_res):
        # 23 PBC requests (2 future) - 21 req synced
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'F385312'")
        assert not error_msg
        assert 0 <= len(acu_res.recs) <= 23
        error_msg = acu_res.send_res_recs_to_sihot(break_on_error=False)
        assert not error_msg

    def test_remove_res_occ_and_cancelled(self, acu_res):
        # 20 PBC requests, 2 excluded because BK resOcc or cancelled/past/no-room
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'Z007184'")
        assert not error_msg
        assert 0 <= len(acu_res.recs) <= 20
        error_msg = acu_res.send_res_recs_to_sihot(break_on_error=False)
        assert not error_msg

    def test_exclude_cancelled_with_break_and_rec_commit(self, acu_res):
        # 21 PBC requests
        error_msg = acu_res.fetch_from_acu_by_aru(where_group_order="CD_CODE = 'E499163'")
        assert not error_msg
        assert 0 <= len(acu_res.recs) <= 21
        error_msg = acu_res.send_res_recs_to_sihot()
        assert not error_msg
