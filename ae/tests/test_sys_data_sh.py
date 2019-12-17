from ae.sys_data_sh import *


class TestResToSihot:

    def test_basic_build_and_send(self, cons_app):
        res_to = ResToSihot(cons_app)
        fld_vals = dict(AcuId='E578973',
                        ResHotelId='1', ResGdsNo='TEST-123456789',
                        ResArrival=datetime.date(year=2019, month=12, day=24),
                        ResDeparture=datetime.date(year=2019, month=12, day=30),
                        ResAdults=1, ResChildren=1, ResRoomCat='1JNS', ResMktSegment='TO',
                        )
        err_msg = res_to.send_res_to_sihot(rec=Record(fields=fld_vals), ensure_client_mode=ECM_DO_NOT_SEND_CLIENT)
        assert not err_msg
        assert not res_to.get_warnings()

    def test_rate_amount_update(self, cons_app):
        res_to = ResToSihot(cons_app)
        fld_vals = dict(ResHotelId='1', ResGdsNo='TEST-123456789',
                        ResArrival=datetime.date(year=2019, month=12, day=24),
                        ResDeparture=datetime.date(year=2019, month=12, day=30),
                        ResAdults=1, ResChildren=1, ResRoomCat='1JNS', ResMktSegment='TO',
                        ResRateBoard='RO',
                        ResRates0RateDay=datetime.date(year=2019, month=12, day=24), ResRates0RateAmount='120.60',
                        ResRates1RateDay=datetime.date(year=2019, month=12, day=25), ResRates1RateAmount='150.60',
                        ResRates2RateDay=datetime.date(year=2019, month=12, day=28), ResRates2RateAmount='180.60',
                        AcuId='E578973',
                        )
        err_msg = res_to.send_res_to_sihot(rec=Record(fields=fld_vals), ensure_client_mode=ECM_DO_NOT_SEND_CLIENT)
        assert not err_msg
        assert not res_to.get_warnings()


class TestFldMapXmlParser:
    ELEM_MAP = (
        ('SYS_FNA', 'fnA'),
        ('SYS_FNB/', ),
        ('SYS_FNB' + ELEM_PATH_SEP + 'SF-A', ('fnB', 0, 'sfnA')),
        ('SYS_FNB' + ELEM_PATH_SEP + 'SF-B', ('fnB', 0, 'sfnB')),
        ('/SYS_FNB', ),
    )

    XML = "<root>" \
          "<SYS_FNA>fnAV</SYS_FNA>" \
          "<UNKNOWN/>" \
          "<SYS_FNB><SF-A>sfnAV0</SF-A></SYS_FNB>" \
          "<SYS_FNB><SF-A>sfnAV1</SF-A><SF-B>sfnBV1</SF-B></SYS_FNB>" \
          "<SYS_FNB><invali>xx</invali><SF-B>sfnBV2</SF-B></SYS_FNB>" \
          "</root>"

    def test_parse(self, cons_app):
        mp = FldMapXmlParser(cons_app, self.ELEM_MAP)
        assert len(mp.rec) == 2
        assert mp.elem_fld_map['SYS_FNA'].val() == ''

        mp.rec.field_items = True
        assert mp.rec['fnA'].root_idx() == ('fnA', )
        assert mp.rec['fnA'].root_idx(system=SDI_SH) == ('SYS_FNA', )
        assert mp.rec['fnA'].root_idx(system=SDI_SH, direction=FAD_FROM) == ('SYS_FNA', )
        assert mp.rec['fnB0sfnA'].root_idx() == ('fnB', 0, 'sfnA')
        assert mp.rec['fnB0sfnA'].root_idx(system=SDI_SH) == ('fnB', 0, 'SYS_FNB.SF-A')
        assert mp.rec['fnB0sfnA'].root_idx(system=SDI_SH, direction=FAD_FROM) == ('fnB', 0, 'SYS_FNB.SF-A')
        assert mp.rec[('fnB', 0, 'sfnB')].root_idx() == ('fnB', 0, 'sfnB')
        assert mp.rec[('fnB', 0, 'sfnB')].root_idx(system=SDI_SH) == ('fnB', 0, 'SYS_FNB.SF-B')
        assert mp.rec[('fnB', 0, 'sfnB')].root_idx(system=SDI_SH, direction=FAD_FROM) == ('fnB', 0, 'SYS_FNB.SF-B')
        mp.rec.field_items = False

        mp.parse_xml(self.XML)
        assert mp.rec.val('fnA') == 'fnAV'
        assert mp.rec.val('fnB', 0, 'sfnA', system=SDI_SH) == 'sfnAV0'
        assert mp.rec.val('fnB', 0, 'sfnB') == ''       # not None because created as template field
        assert mp.rec.val('fnB', 1, 'sfnA') == 'sfnAV1'
        assert mp.rec.val('fnB', 1, 'sfnB') == 'sfnBV1'
        assert mp.rec.val('fnB', 2, 'sfnA') == ''
        assert mp.rec.val('fnB', 2, 'sfnB') == 'sfnBV2'


class TestGuestData:
    def test_guest_data_2443(self, cons_app):
        data = client_data(cons_app, 2443)
        assert data
        assert data['OBJID'] == '2443'
        assert data['MATCHCODE'] == 'G425796'

    def test_guest_data_260362(self, cons_app):
        data = client_data(cons_app, 260362)
        assert data
        assert data['OBJID'] == '260362'
        assert data['MATCHCODE'] == 'G635189'
        assert data['MATCH-SM'] == '00Qw000001BBl13EAD'


class TestElemHelpers:
    def test_elem_path_join(self):
        assert elem_path_join(list()) == ""
        assert elem_path_join(['path', 'to', 'elem']) == "path" + ELEM_PATH_SEP + "to" + ELEM_PATH_SEP + "elem"

    def test_hotel_and_res_id(self):
        assert hotel_and_res_id(Record(fields={'ResHotelId': '4'})) == (None, None)
        assert hotel_and_res_id(Record(fields={'ResId': '5'})) == (None, None)
        assert hotel_and_res_id(Record(fields={'ResHotelId': '4', 'ResId': '5'})) == ('4', '5@4')
        assert hotel_and_res_id(Record(fields={'ResHotelId': '4', 'ResId': '5', 'ResSubId': 'X'})) == ('4', '5/X@4')

    def test_pax_count(self):
        assert pax_count(Record()) == 0
        assert pax_count(Record(fields={'ResAdults': '1'})) == 1
        assert pax_count(Record(fields={'ResChildren': '1'})) == 1
        assert pax_count(Record(fields={'ResAdults': '1', 'ResChildren': '1'})) == 2
        assert pax_count(Record(fields={'ResAdults': 1, 'ResChildren': ''})) == 1
        assert pax_count(Record(fields={'ResAdults': 1, 'ResChildren': 1})) == 2
        assert pax_count(Record(fields={'ResAdults': '1', 'ResChildren': 1})) == 2

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
    def test_obj_id_to_res_no(self, cons_app):
        assert ('4', '33220', '1', '899993') == obj_id_to_res_no(cons_app, '60544')

    def test_gds_no_to_obj_id(self, cons_app):
        assert '60544' == gds_no_to_obj_id(cons_app, '4', '899993')

    def test_res_no_to_obj_id(self, cons_app):
        assert '60544' == res_no_to_obj_id(cons_app, '4', '33220', '1')

    def test_gds_no_to_obj_ids(self, cons_app):
        ids = gds_no_to_ids(cons_app, '4', '899993')
        assert '60544' == ids['ResObjId']
        assert '33220' == ids['ResId']
        assert '1' == ids['ResSubId']
        assert 'ResSfId' in ids
        assert ids['ResSfId'] == ''

    def test_res_no_to_obj_ids(self, cons_app):
        ids = res_no_to_ids(cons_app, '4', '33220', '1')
        assert '60544' == ids['ResObjId']
        assert '899993' == ids['ResGdsNo']
        assert 'ResSfId' in ids
        assert ids['ResSfId'] == ''


class TestResSender:
    def test_create_all_fields(self, cons_app):
        ho_id = '3'
        gdsno = 'TEST-1234567890'
        today = datetime.date.today()
        wk1 = datetime.timedelta(days=7)
        cat = 'STDS'

        rs = ResSender(cons_app)
        row = dict(ResHotelId=ho_id, ResStatus='1', ResAction=ACTION_INSERT,
                   ResGdsNo=gdsno, ResVoucherNo='Voucher1234567890',
                   ResBooked=today, ResArrival=today + wk1, ResDeparture=today + wk1 + wk1,
                   ResRoomCat=cat, ResPriceCat=cat, ResRoomNo='3220',
                   ShId='27', AcuId='TCRENT',
                   ResNote='test short note', ResLongNote='test large TEC note',
                   ResBoard='RO',    # room only (no board/meal-plan)
                   ResMktSegment='TC', ResRateSegment='TC',
                   ResAccount='1',
                   ResSource='A', ResMktGroup='RS',
                   ResFlightArrComment='Flight1234',
                   ResAllotmentNo=123456,
                   ResAdults=2, ResChildren=2,
                   ResPersons0PersSurname='Tester', ResPersons0PersForename='TestX',
                   ResPersons0PersDOB=today - 1000 * wk1,
                   ResPersons1PersSurname='Tester', ResPersons1PersForename='TestY',
                   ResPersons2PersSurname='Tester', ResPersons2PersForename='Chilly', ResPersons2TypeOfPerson='2B',
                   ResPersons3PersSurname='', ResPersons3PersForename='', ResPersons3PersDOB=today - 100 * wk1,
                   )
        rec = Record(fields=row)
        err, msg = rs.send_rec(rec)
        if "setDataRoom not available!" in err:     # no error only on first run after TEST replication
            row.pop('ResRoomNo')           # .. so on n. run simply remove room number and then retry
            rs.wipe_gds_errors()            # .. and also remove send locking by wiping GDS errors for this GDS
            err, msg = rs.send_rec(Record(fields=row))

        assert not err
        assert ho_id == rs.response.id
        assert gdsno == rs.response.gdsno
        h, r, s, g = rs.get_res_no()
        assert ho_id == h
        assert r
        assert s
        assert '1' == s
        assert gdsno == g

    def test_create_minimum_fields_with_mc(self, cons_app):
        ho_id = '1'
        gdsno = 'TEST-1234567890'
        today = datetime.datetime.today()
        wk1 = datetime.timedelta(days=7)
        arr = today + wk1
        dep = arr + wk1
        cat = 'STDO'
        mkt_seg = 'TC'

        rs = ResSender(cons_app)
        row = dict(ResHotelId=ho_id, ResArrival=arr, ResDeparture=dep, ResRoomCat=cat, ResMktSegment=mkt_seg,
                   AcuId='TCRENT', ResGdsNo=gdsno)
        rec = Record(fields=row, system=SDI_SH, direction=FAD_ONTO).add_system_fields(rs.elem_map)
        err, msg = rs.send_rec(rec)

        assert not err
        assert ho_id == rs.response.id
        assert gdsno == rs.response.gdsno
        h, r, s, g = rs.get_res_no()
        assert ho_id == h
        assert r
        assert s
        assert '1' == s
        assert gdsno == g

    def test_create_minimum_fields_with_objid(self, cons_app):
        ho_id = '1'
        gdsno = 'TEST-1234567890'
        today = datetime.datetime.today()
        wk1 = datetime.timedelta(days=7)
        arr = today + wk1
        dep = arr + wk1
        cat = 'STDO'
        mkt_seg = 'TC'

        rs = ResSender(cons_app)
        row = dict(ResHotelId=ho_id, ResArrival=arr, ResDeparture=dep, ResRoomCat=cat, ResMktSegment=mkt_seg,
                   ShId='27', ResGdsNo=gdsno)
        err, msg = rs.send_rec(Record(fields=row))

        assert not err
        assert ho_id == rs.response.id
        assert gdsno == rs.response.gdsno
        h, r, s, g = rs.get_res_no()
        assert ho_id == h
        assert r
        assert s
        assert '1' == s
        assert gdsno == g


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
        assert xml_parser.client_list.val(0, 'AcuId') == 'test2'
        assert xml_parser.client_list.val(0, 'MATCHCODE') == 'test2'
        assert xml_parser.client_list.val(0, 'City') == 'city'
        assert xml_parser.client_list.val(0, 'CITY') == 'city'


class TestResFromSihot:
    XML_MATCHCODE_EXAMPLE = '''
    <SIHOT-Document>
        <ARESLIST>
        <RESERVATION>
        <PERSON>
            <MATCHCODE>PersonAcuId</MATCHCODE>
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
            <MATCHCODE>PersonAcuId</MATCHCODE>
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

    def test_fld_map_matchcode(self, cons_app):
        xml_parser = ResFromSihot(cons_app)
        xml_parser.parse_xml(self.XML_MATCHCODE_EXAMPLE)
        assert xml_parser.res_list[0].val('AcuId') == 'test2'
        assert xml_parser.res_list[0].val('RESERVATION.MATCHCODE') == 'test2'
        assert xml_parser.res_list[0].val('ResPersons', 0, 'PersAcuId') == 'PersonAcuId'
        assert xml_parser.res_list.val(0, 'ResPersons', 0, 'PERSON.MATCHCODE') == 'PersonAcuId'

    def test_fld_map_big(self, cons_app):
        xml_parser = ResFromSihot(cons_app)
        xml_parser.parse_xml(self.XML_EXAMPLE)
        assert xml_parser.res_list.val(0, 'AcuId') == 'test2'
        assert xml_parser.res_list[0].val('AcuId') == 'test2'
        assert xml_parser.res_list.val(0, 'RESERVATION.MATCHCODE') == 'test2'
        assert xml_parser.res_list[0].val('RESERVATION.MATCHCODE') == 'test2'
        assert xml_parser.res_list.val(0, 'ResPersons', 0, 'PersAcuId') == 'PersonAcuId'
        assert xml_parser.res_list[0].val('ResPersons0PersAcuId') == 'PersonAcuId'
        assert xml_parser.res_list.val(0, 'ResPersons', 0, 'PERSON.MATCHCODE') == 'PersonAcuId'
        assert xml_parser.res_list.value(0, 'ResPersons', 0).val('PERSON.MATCHCODE') == 'PersonAcuId'
        assert xml_parser.res_list.val(0, 'ResGdsNo') == '1234567890ABC'
        assert xml_parser.res_list[0].val('ResGdsNo') == '1234567890ABC'
        assert xml_parser.res_list.val(0, 'GDSNO') == '1234567890ABC'
        assert xml_parser.res_list[0].val('GDSNO') == '1234567890ABC'


class TestClientToSihot:

    def test_basic_build_and_send(self, cons_app):
        cli_to = ClientToSihot(cons_app)
        fld_vals = dict(AcuId='T111222', Title='1', GuestType='1', Country='AT', Language='DE',
                        ExtRefs='RCI=123,XXX=456')
        rec = Record(fields=fld_vals)
        err_msg = cli_to.send_client_to_sihot(rec=rec)
        assert not err_msg
        assert cli_to.response.objid
        assert cli_to.response.objid == rec.val('ShId')


class TestClientFetchSearch:
    def test_fetch_client_with_test_client(self, cons_app, create_test_client):
        client_fetch = ClientFetch(cons_app)
        rec = client_fetch.fetch_client(create_test_client.objid)
        assert client_fetch.response.objid == create_test_client.objid   # OBJID passed only to response (ret is empty)
        # also MATCHCODE element is in response (empty in ret): assert ret['MATCHCODE']==create_test_client.matchcode
        assert client_fetch.response.matchcode == create_test_client.matchcode
        assert client_fetch.response.objid == create_test_client.objid
        assert isinstance(rec, Record)
        assert rec['Surname'] == create_test_client.surname
        assert rec['Forename'] == create_test_client.forename
        assert rec['GuestType'] == create_test_client.client_type

        assert rec.val('NAME-1') == create_test_client.surname
        assert rec['NAME-1'] == create_test_client.surname  # also rec['NAME-1'] does work (NO split into ('NAME-', 1))
        assert rec.val('NAME-2') == create_test_client.forename
        assert rec['NAME-2'] == create_test_client.forename
        assert rec['T-GUEST'] == create_test_client.client_type

    def test_client_with_10_ext_refs(self, client_search, cons_app):
        objid = client_search.client_id_by_matchcode('E396693')
        assert objid
        ret = ClientFetch(cons_app).fetch_client(objid)
        assert isinstance(ret, dict)
        assert ret['MATCH-ADM'] == '4806-00208'
        if ret['COMMENT']:
            assert 'RCI=1442-11521' in ret['COMMENT']
            assert 'RCI=5445-12771' in ret['COMMENT']
            assert 'RCI=5-207931' in ret['COMMENT']     # RCIP got remapped to RCI

    def test_get_objids_by_client_names(self, client_search):
        obj_ids = client_search.search_clients(surname='OTS Open Travel Services AG')
        obj_id = client_search.client_id_by_matchcode('OTS')
        assert obj_id in obj_ids
        obj_ids = client_search.search_clients(surname='Sumar Ferdir')
        obj_id = client_search.client_id_by_matchcode('SF')
        assert obj_id in obj_ids
        obj_ids = client_search.search_clients(surname='Thomas Cook AG')
        obj_id = client_search.client_id_by_matchcode('TCAG')
        assert obj_id in obj_ids
        obj_ids = client_search.search_clients(surname='Thomas Cook Northern Europe')
        obj_id = client_search.client_id_by_matchcode('TCRENT')
        assert obj_id in obj_ids

    def test_get_objids_by_email(self, client_search):
        obj_ids = client_search.search_clients(email='info@opentravelservice.com')
        obj_id = client_search.client_id_by_matchcode('OTS')
        assert obj_id in obj_ids
        obj_id = client_search.client_id_by_matchcode('SF')
        assert obj_id in obj_ids

    def test_client_id_by_matchcode(self, client_search):
        assert client_search.client_id_by_matchcode('OTS') == '69'
        assert client_search.client_id_by_matchcode('SF') == '100'
        assert client_search.client_id_by_matchcode('TCAG') == '20'
        assert client_search.client_id_by_matchcode('TCRENT') == '27'

    def test_client_id_by_matchcode2(self, client_search, create_test_client):
        ret = client_search.client_id_by_matchcode(create_test_client.matchcode)
        assert ret == create_test_client.objid

    def test_search_agencies(self, client_search):
        ags = client_search.search_clients(guest_type='7')     # 1=Guest, 7=Company (wrong documented in KERNEL PDF)
        assert [_ for _ in ags if _ == '69']
        assert [_ for _ in ags if _ == '100']
        assert [_ for _ in ags if _ == '20']
        assert [_ for _ in ags if _ == '27']

        ags = client_search.search_clients(guest_type='7', field_names=('AcuId', 'ShId'))
        assert [_ for _ in ags if _['AcuId'] == 'OTS' and _['ShId'] == '69']
        assert [_ for _ in ags if _['AcuId'] == 'SF' and _['ShId'] == '100']
        assert [_ for _ in ags if _['AcuId'] == 'TCAG' and _['ShId'] == '20']
        assert [_ for _ in ags if _['AcuId'] == 'TCRENT' and _['ShId'] == '27']
