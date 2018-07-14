# from sxmlif import ELEM_PATH_SEP
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

    def test_elem_value_simple(self):
        assert elem_value(dict(), 'missing') is None
        assert elem_value(dict(), 'missing', default_value=1) == 1
        assert elem_value(dict(elem_name=dict()), 'missing') is None
        assert elem_value(dict(elem_name=dict()), 'missing', default_value='xx') == 'xx'
        assert elem_value(dict(elem_name=dict(elemVal='ttt')), 'elem_name') == 'ttt'

    def test_elem_value_list(self):
        assert elem_value(dict(elem_name=dict(elemListVal=['vvv'])), 'elem_name') == 'vvv'
        assert elem_value(dict(elem_name=dict(elemListVal=['vvv'])), 'elem_name', arri=0) == 'vvv'
        assert elem_value(dict(elem_name=dict(elemListVal=['aaa', 'vvv'])), 'elem_name', arri=2) is None

    def test_elem_value_with_path(self):
        assert elem_value(dict(), elem_path_join(['missing', 'too'])) is None
        assert elem_value(dict(), elem_path_join(['missing', 'too']), default_value=1) == 1
        assert elem_value(dict(elem_name=dict()), elem_path_join(['missing', 'too'])) is None
        assert elem_value(dict(elem_name=dict()), elem_path_join(['missing', 'too']), default_value='xx') == 'xx'
        assert elem_value(dict(elem=dict(elemVal='ttt')), elem_path_join(['path', 'elem'])) is None
        assert elem_value(dict(elem=dict(elemPathValues={'path.elem': ['ttt']})), ['path', 'elem']) == 'ttt'
        assert elem_value(dict(elem=dict(elemPathValues={'path.elem': ['v']})), 'path' + ELEM_PATH_SEP + 'elem') == 'v'
        assert elem_value(dict(elem=dict(elemPathValues={'path.elem': ['vvv']})), 'path.elem', arri=0) == 'vvv'
        assert elem_value(dict(elem=dict(elemPathValues={'path.elem': ['aaa', 'vvv']})), 'path.elem') == 'aaa'
        assert elem_value(dict(elem=dict(elemPathValues={'path.elem': ['aaa', 'vvv']})), 'path.elem', arri=1) == 'vvv'
        assert elem_value(dict(elem=dict(elemPathValues={'path.elem': ['aaa', 'vvv']})), 'path.elem', arri=2) is None

    def test_hotel_and_res_id(self):
        assert hotel_and_res_id({'RES-HOTEL': dict(elemVal='4')}) == (None, None)
        assert hotel_and_res_id({'RES-NR': dict(elemVal='5')}) == (None, None)
        assert hotel_and_res_id({'RES-HOTEL': dict(elemVal='4'), 'RES-NR': dict(elemVal='5')}) == ('4', '5@4')
        assert hotel_and_res_id({'RES-HOTEL': dict(elemVal='4'), 'RES-NR': dict(elemVal='5'),
                                 'SUB-NR': dict(elemVal='X')}) == ('4', '5/X@4')

    def test_pax_count(self):
        assert pax_count(dict()) == 0
        assert pax_count(dict(NOPAX=dict(elemVal='1'))) == 1
        assert pax_count(dict(NOCHILDS=dict(elemVal='1'))) == 1
        assert pax_count(dict(NOPAX=dict(elemVal=2), NOCHILDS=dict(elemVal=''))) == 2
        assert pax_count(dict(NOPAX=dict(elemVal=2), NOCHILDS=dict(elemVal=1))) == 3
        assert pax_count(dict(NOPAX=dict(elemVal='2'), NOCHILDS=dict(elemVal='1'))) == 3

    def test_gds_no(self):
        assert gds_no(dict()) is None
        assert gds_no(dict(GDSNO=dict(elemVal='123abc'))) == '123abc'

    def test_date_range(self):
        ds = '2018-06-01'
        dd = datetime.date(2018, 6, 1)
        assert date_range(dict(ARR=dict(elemVal=ds), DEP=dict(elemVal=ds))) == (dd, dd)

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
    def test_gds_no_to_obj_id(self, console_app_env):
        # test res of Z007184 from 26.12.17 until 3.1.2018
        assert '60544' == gds_no_to_obj_id(console_app_env, '4', '899993')

    def test_obj_id_to_res_no(self, console_app_env):
        assert ('4', '33220', '1') == obj_id_to_res_no(console_app_env, '60544')

    def test_res_no_to_obj_id(self, console_app_env):
        assert '60544' == res_no_to_obj_id(console_app_env, '4', '33220', '1')


class TestResSender:
    def test_create_all_fields(self, console_app_env):
        ho_id = '3'
        gdsno = 'TEST-1234567890'
        today = datetime.datetime.today()
        wk1 = datetime.timedelta(days=7)
        cat = 'STDS'

        rs = ResSender(console_app_env)
        crow = dict(ResHotelId=ho_id, ResStatus='1', ResAction='INSERT',
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
                    ResFlightNo='Flight1234',
                    ResAllotmentNo=123456)
        err, msg = rs.send_row(crow)
        if "setDataRoom not available!" in err:     # no error only on first run after TEST replication
            crow.pop('ResRoomNo')              # .. so on n. run simply remove room number and then retry
            rs.res_sender.wipe_gds_errors()         # .. and also remove send locking by wiping GDS errors for this GDS
            err, msg = rs.send_row(crow)

        assert not err
        assert ho_id == rs.res_sender.response.id
        assert gdsno == rs.res_sender.response.gdsno
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
        assert ho_id == rs.res_sender.response.id
        assert gdsno == rs.res_sender.response.gdsno
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
        assert ho_id == rs.res_sender.response.id
        assert gdsno == rs.res_sender.response.gdsno
        h, r, s = rs.get_res_no()
        assert ho_id == h
        assert r
        assert s
        assert '1' == s
