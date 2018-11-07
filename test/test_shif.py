from ae_sys_data import Record, Field
from shif import *  # guest_data, elem_path_join, elem_value, ...


class TestGuestData:
    def test_guest_data_2443(self, console_app_env):
        data = guest_data(console_app_env, 2443)
        assert data
        assert data['OBJID'] == '2443'
        assert data['MATCHCODE'] == 'G425796'

    def test_guest_data_260362(self, console_app_env):
        data = guest_data(console_app_env, 260362)
        assert data
        assert data['OBJID'] == '260362'
        assert data['MATCHCODE'] == 'G635189'
        assert data['MATCH-SM'] == '00Qw000001BBl13EAD'


class TestElemHelpers:
    def test_elem_path_join(self):
        assert elem_path_join(list()) == ""
        assert elem_path_join(['path', 'to', 'elem']) == "path" + ELEM_PATH_SEP + "to" + ELEM_PATH_SEP + "elem"

    def test_hotel_and_res_id(self):
        hof = Field().set_name('RES-HOTEL', system=SDI_SH).set_val('4', system=SDI_SH)
        rnf = Field().set_name('RES-NR', system=SDI_SH).set_val('5')
        rsf = Field().set_name('SUB-NR', system=SDI_SH).set_val('X')
        assert hotel_and_res_id(Record({'ResHotelId': hof})) == (None, None)
        assert hotel_and_res_id(Record({'ResNo': rnf})) == (None, None)
        assert hotel_and_res_id(Record({'ResHotelId': hof, 'ResNo': rnf})) == ('4', '5@4')
        assert hotel_and_res_id(Record({'ResHotelId': hof, 'ResNo': rnf, 'ResSubNo': rsf})) == ('4', '5/X@4')

    def test_pax_count(self):
        pxc = Field().set_name('NOPAX', system=SDI_SH).set_val('1')
        chc = Field().set_name('NOCHILDS', system=SDI_SH).set_val('1')
        pxn = Field().set_name('NOPAX', system=SDI_SH).set_val(1)
        chn = Field().set_name('NOCHILDS', system=SDI_SH).set_val(1)
        che = Field().set_name('NOCHILDS', system=SDI_SH).set_val('')
        assert pax_count(Record()) == 0
        assert pax_count(Record(fields={'ResAdults': pxc})) == 1
        assert pax_count(Record(fields={'ResChildren': chc})) == 1
        assert pax_count(Record(fields={'ResAdults': pxc, 'ResChildren': chc})) == 2
        assert pax_count(Record(fields={'ResAdults': pxn, 'ResChildren': che})) == 2
        assert pax_count(Record(fields={'ResAdults': pxn, 'ResChildren': chn})) == 2
        assert pax_count(Record(fields={'ResAdults': pxc, 'ResChildren': chn})) == 2

    def test_gds_no(self):
        assert gds_number(Record()) is None
        assert gds_number(Record({'ResGdsNo': Field().set_name('GDSNO', system=SDI_SH).set_val('123abc')})) == '123abc'

    def test_date_range_chunks(self):
        d1 = datetime.date(2018, 6, 1)
        d2 = datetime.date(2018, 7, 1)
        for beg, end in date_range_chunks(d1, d2, 1):
            assert beg
            assert end
            assert isinstance(beg, datetime.date)
            assert isinstance(end, datetime.date)

        d3 = d1 + datetime.timedelta(days=1)
        i = date_range_chunks(d1, d3, 1)
        beg, end = next(i)
        assert beg == d1
        assert end == d1
        beg, end = next(i)
        assert beg == d3
        assert end == d3

        d3 = d1 + datetime.timedelta(days=2)
        i = date_range_chunks(d1, d3, 2)
        beg, end = next(i)
        print(beg, end)
        assert beg == d1
        assert end == d1 + datetime.timedelta(days=1)
        beg, end = next(i)
        print(beg, end)
        assert beg == d3
        assert end == d3

        d3 = d1 + datetime.timedelta(days=3)
        i = date_range_chunks(d1, d3, 2)
        beg, end = next(i)
        print(beg, end)
        assert beg == d1
        assert end == d1 + datetime.timedelta(days=1)
        beg, end = next(i)
        print(beg, end)
        assert beg == d3 - datetime.timedelta(days=1)
        assert end == d3


class TestIdConverters:
    # test res of Z007184 from 26.12.17 until 3.1.2018
    def test_obj_id_to_res_no(self, console_app_env):
        assert ('4', '33220', '1') == obj_id_to_res_no(console_app_env, '60544')

    def test_gds_no_to_obj_id(self, console_app_env):
        assert '60544' == gds_no_to_obj_id(console_app_env, '4', '899993')

    def test_res_no_to_obj_id(self, console_app_env):
        assert '60544' == res_no_to_obj_id(console_app_env, '4', '33220', '1')

    def test_gds_no_to_obj_ids(self, console_app_env):
        ids = gds_no_to_ids(console_app_env, '4', '899993')
        assert '60544' == ids['ResObjId']
        assert '33220' == ids['ResNo']
        assert '1' == ids['ResSubNo']
        assert 'ResSfId' in ids
        assert ids['ResSfId'] is None

    def test_res_no_to_obj_ids(self, console_app_env):
        ids = res_no_to_ids(console_app_env, '4', '33220', '1')
        assert '60544' == ids['ResObjId']
        assert '899993' == ids['ResGdsNo']
        assert 'ResSfId' in ids
        assert ids['ResSfId'] is None


class TestResSender:
    def test_create_all_fields(self, console_app_env):
        ho_id = '3'
        gdsno = 'TEST-1234567890'
        today = datetime.datetime.today()
        wk1 = datetime.timedelta(days=7)
        cat = 'STDS'

        rs = ResSender(console_app_env)
        crow = dict(ResHotelId=ho_id, ResStatus='1', ResAction=ACTION_INSERT,
                    ResGdsNo=gdsno, ResVoucherNo='Voucher1234567890',
                    ResBooked=today, ResArrival=today + wk1, ResDeparture=today + wk1 + wk1,
                    ResRoomCat=cat, ResPriceCat=cat, ResRoomNo='3220',
                    ShId='27', ResOrdererId='27', AcId='TCRENT', ResOrdererMc='TCRENT',
                    ResNote='test short note', ResLongNote='test large TEC note',
                    ResBoard='RO',    # room only (no board/meal-plan)
                    ResMktSegment='TC', SIHOT_MKT_SEG='TC', ResRateSegment='TC',
                    ResAccount=1,
                    ResSource='A', ResMktGroup='RS',
                    ResAdults=1, ResChildren=1,
                    ResAdult1Surname='Tester', ResAdult1Forename='TestY', ResAdult1DOB=today - 100 * wk1,
                    ResAdult2Surname='', ResAdult2Forename='',
                    ResChild1Surname='Tester', ResChild1Forename='Chilly', ResChild1DOB=today - 10 * wk1,
                    ResChild2Surname='', ResChild2Forename='',
                    ResFlightArrComment='Flight1234',
                    ResAllotmentNo=123456)
        err, msg = rs.send_row(crow)
        if "setDataRoom not available!" in err:     # no error only on first run after TEST replication
            crow.pop('ResRoomNo')              # .. so on n. run simply remove room number and then retry
            rs.wipe_gds_errors()         # .. and also remove send locking by wiping GDS errors for this GDS
            err, msg = rs.send_row(crow)

        assert not err
        assert ho_id == rs.response.id
        assert gdsno == rs.response.gdsno
        h, r, s = rs.get_res_no()
        assert ho_id == h
        assert r
        assert s
        assert '1' == s

    def test_create_minimum_fields_with_mc(self, console_app_env):
        ho_id = '1'
        gdsno = 'TEST-1234567890'
        today = datetime.datetime.today()
        wk1 = datetime.timedelta(days=7)
        arr = today + wk1
        dep = arr + wk1
        cat = 'STDO'
        mkt_seg = 'TC'

        rs = ResSender(console_app_env)
        crow = dict(ResHotelId=ho_id, ResArrival=arr, ResDeparture=dep, ResRoomCat=cat, ResMktSegment=mkt_seg,
                    ResOrdererMc='TCRENT', ResGdsNo=gdsno)
        err, msg = rs.send_row(crow)

        assert not err
        assert ho_id == rs.response.id
        assert gdsno == rs.response.gdsno
        h, r, s = rs.get_res_no()
        assert ho_id == h
        assert r
        assert s
        assert '1' == s

    def test_create_minimum_fields_with_objid(self, console_app_env):
        ho_id = '1'
        gdsno = 'TEST-1234567890'
        today = datetime.datetime.today()
        wk1 = datetime.timedelta(days=7)
        arr = today + wk1
        dep = arr + wk1
        cat = 'STDO'
        mkt_seg = 'TC'

        rs = ResSender(console_app_env)
        crow = dict(ResHotelId=ho_id, ResArrival=arr, ResDeparture=dep, ResRoomCat=cat, ResMktSegment=mkt_seg,
                    ResOrdererId='27', ResGdsNo=gdsno)
        err, msg = rs.send_row(crow)

        assert not err
        assert ho_id == rs.response.id
        assert gdsno == rs.response.gdsno
        h, r, s = rs.get_res_no()
        assert ho_id == h
        assert r
        assert s
        assert '1' == s


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
        assert xml_parser.elem_fld_map['MATCHCODE'].val() == 'test2'
        assert xml_parser.acu_fld_vals['AcId'] == 'test2'
        assert xml_parser.elem_fld_map['CITY'].val() == 'city'
        assert xml_parser.acu_fld_vals['City'] == 'city'

        # cae.dprint("--COUNTRY-fldValToAcu/acu_fld_vals: ",
        # xml_guest.elem_fld_map['COUNTRY']['fldValToAcu'],
        # xml_guest.acu_fld_vals[xml_guest.elem_fld_map['COUNTRY']['fldName']])


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


class TestClientToSihot:

    def test_basic_build_and_send(self, console_app_env):
        cli_to = ClientToSihot(console_app_env)
        fld_vals = dict(AcId='T111222', Title='1', GuestType='1', Country='AT', Language='DE',
                        ExtRefs='RCI=123,XXX=456')
        err_msg = cli_to.send_client_to_sihot(fld_vals=fld_vals)
        assert not err_msg
        assert cli_to.response.objid


class TestResToSihot:

    def test_basic_build_and_send(self, console_app_env):
        res_to = ResToSihot(console_app_env)
        fld_vals = dict(ResHotelId='1', ResGdsNo='TEST-123456789', ResOrdererMc='E578973',
                        ResArrival=datetime.date(year=2019, month=12, day=24),
                        ResDeparture=datetime.date(year=2019, month=12, day=30),
                        ResAdults=1, ResChildren=1, ResRoomCat='1STDP',
                        )
        err_msg = res_to.send_res_to_sihot(fld_vals=fld_vals, ensure_client_mode=ECM_DO_NOT_SEND_CLIENT)
        assert not err_msg
