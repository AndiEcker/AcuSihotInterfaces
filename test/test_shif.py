# from sxmlif import ELEM_PATH_SEP
from shif import *  # avail_rooms, count_res, guest_data, elem_path_join, elem_value


class TestAvailRoomsSep14:
    def test_avail_rooms_for_all_hotels_and_cats(self, console_app_env):
        assert avail_rooms(console_app_env, day=datetime.date(2017, 9, 14)) == 164  # 165 before Feb2018

    def test_avail_rooms_for_bhc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], day=datetime.date(2017, 9, 14)) == 21

    def test_avail_rooms_for_pbc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['4'], day=datetime.date(2017, 9, 14)) == 53

    def test_avail_rooms_for_bhc_pbc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1', '4'], day=datetime.date(2017, 9, 14)) == 74

    def test_avail_studios_for_all_hotels(self, console_app_env):
        assert avail_rooms(console_app_env, room_cat_prefix="S", day=datetime.date(2017, 9, 14)) == 17

    def test_avail_studios_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="S", day=datetime.date(2017, 9, 14)) == 8

    def test_avail_1bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="1", day=datetime.date(2017, 9, 14)) == 5

    def test_avail_1bed_junior_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="1J", day=datetime.date(2017, 9, 14)) == 4

    def test_avail_2bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="2", day=datetime.date(2017, 9, 14)) == 7

    def test_avail_3bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="3", day=datetime.date(2017, 9, 14)) == 1
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="3BPS", day=datetime.date(2017, 9, 14)) == 1


class TestAvailRoomsSep15:
    def test_avail_rooms_for_all_hotels_and_cats(self, console_app_env):
        assert avail_rooms(console_app_env, day=datetime.date(2017, 9, 15)) == 98  # 99 before Feb2018

    def test_avail_rooms_for_bhc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], day=datetime.date(2017, 9, 15)) == 21

    def test_avail_rooms_for_pbc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['4'], day=datetime.date(2017, 9, 15)) == 34

    def test_avail_rooms_for_bhc_pbc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1', '4'], day=datetime.date(2017, 9, 15)) == 55

    def test_avail_studios_for_all_hotels(self, console_app_env):
        assert avail_rooms(console_app_env, room_cat_prefix="S", day=datetime.date(2017, 9, 15)) == 23

    def test_avail_studios_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="S", day=datetime.date(2017, 9, 15)) == 11

    def test_avail_1bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="1", day=datetime.date(2017, 9, 15)) == 3

    def test_avail_1bed_junior_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="1J", day=datetime.date(2017, 9, 15)) == 2

    def test_avail_2bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="2", day=datetime.date(2017, 9, 15)) == 6

    def test_avail_3bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="3", day=datetime.date(2017, 9, 15)) == 1
        assert avail_rooms(console_app_env, hotel_ids=['1'], room_cat_prefix="3BPS", day=datetime.date(2017, 9, 15)) == 1


class TestCountRes:
    def test_count_res_sep14_for_any_and_all_cats(self, console_app_env):
        assert count_res(console_app_env, hotel_ids=['999'], day=datetime.date(2017, 9, 14)) == 20

    def test_count_res_sep14_for_any_and_stdo_cats(self, console_app_env):
        assert count_res(console_app_env, hotel_ids=['999'], room_cat_prefix="STDO", day=datetime.date(2017, 9, 14)) == 16

    def test_count_res_sep14_for_any_and_1jnr_cats(self, console_app_env):
        assert count_res(console_app_env, hotel_ids=['999'], room_cat_prefix="1JNR", day=datetime.date(2017, 9, 14)) == 4

    # too slow - needs around 6 minutes
    # def test_count_res_sep14_all_hotels_and_cats(self, console_app_env):
    #     assert count_res(console_app_env, day=datetime.date(2017, 9, 14)) == 906

    # quite slow - needs 1:30 minutes
    def test_count_res_sep14_for_bhc_and_all_cats(self, console_app_env):
        assert count_res(console_app_env, hotel_ids=['1'], day=datetime.date(2017, 9, 14)) == 207  # 273 before Feb2018


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

    def test_apt_wk_yr(self, console_app_env):
        console_app_env._options['2018'] = '2018-01-05'     # create fake config entries (defined in SihotResImport.ini)
        console_app_env._options['2019'] = '2019-01-04'
        assert apt_wk_yr(dict(ARR=dict(elemVal='2018-06-01')), console_app_env) == (None, 22, 2018)
        assert apt_wk_yr(dict(ARR=dict(elemVal='2018-06-01'), RN=dict(elemVal='A')), console_app_env) == ('A', 22, 2018)

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
