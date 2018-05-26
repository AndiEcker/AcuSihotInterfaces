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
