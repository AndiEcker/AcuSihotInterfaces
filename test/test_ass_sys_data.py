# tests of AssSysData methods - some of them also done by the config settings tests (see test_config.py/asd)
import datetime
# import pytest

# from sys_data_ids import CLIENT_REC_TYPE_ID_OWNERS
from ae_sys_data import Record, FAD_ONTO

from sfif import MAP_RES_OBJECT, MAP_CLIENT_OBJECTS
from shif import res_search, client_data, ResFetch
from ass_sys_data import AssSysData
from sys_data_ids import SDI_ASS, SDI_SF


def test_tmp(console_app_env, ass_sys_data):
    asd = ass_sys_data
    assert not asd.clients
    asd.as_clients_pull(filter_records=lambda r: r.val('AssId') > 69,
                        field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'])
    assert asd.clients
    cnt = len(asd.clients)
    acc = asd.clients.copy(deepness=-1)

    asd.as_clients_push(filter_records=lambda r: r.val('AssId') > 69,
                        field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'],
                        match_fields=['AssId'])
    recs, dif = asd.as_clients_compare(filter_records=lambda r: r.val('AssId') > 69,
                                       field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'])
    assert len(recs) == cnt == len(asd.clients)
    assert not dif
    assert acc == asd.clients == recs

    print()


class TestSysDataActions:
    def test_clients_pull_count(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        asd.as_clients_pull(filter_records=lambda r: r.val('AssId') > 69)
        assert asd.clients
        cnt = len(asd.clients)
        asd.as_clients_pull(filter_records=lambda r: r.val('AssId') > 69)
        assert len(asd.clients) == cnt * 2

        asd.clients.clear()
        assert not asd.clients
        asd.as_clients_pull(field_names=['AssId', 'AcuId', 'ShId', 'Name'],
                            filter_records=lambda r: r.val('AssId') > 69)
        assert cnt == len(asd.clients)
        asd.as_clients_pull(match_fields=['AssId'],
                            filter_records=lambda r: r.val('AssId') > 69)
        assert cnt == len(asd.clients)

    def test_field_col_names(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        asd.as_clients_pull(col_names=['cl_pk', 'cl_ac_id', 'cl_sh_id', 'cl_phone', 'cl_email'],
                            filter_records=lambda r: r.val('AssId') > 69)
        assert asd.clients
        cnt = len(asd.clients)
        for rec in asd.clients:
            assert not rec.val('Name')

        asd.clients.clear()
        assert not asd.clients
        asd.as_clients_pull(field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'],
                            filter_records=lambda r: r.val('AssId') > 69)
        assert cnt == len(asd.clients)
        for rec in asd.clients:
            assert not rec.val('Name')

    def test_compare_match_fields_default(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        asd.as_clients_pull(col_names=['cl_pk', 'cl_ac_id', 'cl_sh_id', 'cl_phone', 'cl_email'],
                            filter_records=lambda r: r.val('AssId') > 69)
        assert asd.clients
        cnt = len(asd.clients)

        recs, dif = asd.as_clients_compare(field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'],
                                           match_fields=['AssId'],
                                           filter_records=lambda r: r.val('AssId') > 69)
        assert len(recs) == cnt == len(asd.clients)
        assert not dif

        recs, dif = asd.as_clients_compare(field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'],
                                           filter_records=lambda r: r.val('AssId') > 69)
        assert len(recs) == cnt == len(asd.clients)
        assert not dif


class TestAssSysDataSh:
    def test_sh_res_change_to_ass_4_33220(self, console_app_env):
        # use TO reservation with GDS 899993 from 26-Dec-17 to 3-Jan-18
        ho_id = '4'
        res_id = '33220'
        sub_id = '1'
        obj_id = '60544'

        res_data = ResFetch(console_app_env).fetch_by_res_id(ho_id=ho_id, res_id=res_id, sub_id=sub_id)
        assert isinstance(res_data, Record)
        assert ho_id == res_data.val('ResHotelId')
        assert res_id == res_data.val('ResId')
        assert sub_id == res_data.val('ResSubId')
        assert obj_id == res_data.val('ResObjId')
        arr_date = res_data.val('ResArrival')
        dep_date = res_data.val('ResDeparture')

        rgr_rec = Record(system=SDI_ASS, direction=FAD_ONTO)
        asd = AssSysData(console_app_env)
        asd.sh_res_change_to_ass(res_data, ass_res_rec=rgr_rec)
        assert ho_id == rgr_rec['rgr_ho_fk']
        assert res_id == rgr_rec['rgr_res_id']
        assert sub_id == rgr_rec['rgr_sub_id']
        assert obj_id == rgr_rec['rgr_obj_id']
        assert arr_date == rgr_rec['rgr_arrival']
        assert dep_date == rgr_rec['rgr_departure']

        rgr_dict = dict()       # sh_res_change_to_ass allows also dict
        asd = AssSysData(console_app_env)
        asd.sh_res_change_to_ass(res_data, ass_res_rec=rgr_dict)
        assert ho_id == rgr_dict['rgr_ho_fk']
        assert res_id == rgr_dict['rgr_res_id']
        assert sub_id == rgr_dict['rgr_sub_id']
        assert obj_id == rgr_dict['rgr_obj_id']
        assert arr_date == rgr_dict['rgr_arrival']
        assert dep_date == rgr_dict['rgr_departure']

        cols = ['rgr_ho_fk', 'rgr_res_id', 'rgr_sub_id', 'rgr_obj_id', 'rgr_arrival', 'rgr_departure']

        rgr_list = asd.rgr_fetch_list(cols, dict(rgr_obj_id=obj_id))
        assert isinstance(rgr_list, list)
        rgr_dict = dict(zip(cols, rgr_list[0]))
        assert ho_id == rgr_dict['rgr_ho_fk']
        assert res_id == rgr_dict['rgr_res_id']
        assert sub_id == rgr_dict['rgr_sub_id']
        assert obj_id == rgr_dict['rgr_obj_id']
        assert arr_date.toordinal() == rgr_dict['rgr_arrival'].toordinal()
        assert dep_date.toordinal() == rgr_dict['rgr_departure'].toordinal()
        assert arr_date == rgr_dict['rgr_arrival']
        assert dep_date == rgr_dict['rgr_departure']

        rgr_list = asd.rgr_fetch_list(cols, dict(rgr_ho_fk=ho_id, rgr_res_id=res_id, rgr_sub_id=sub_id))
        assert isinstance(rgr_list, list)
        rgr_dict = dict(zip(cols, rgr_list[0]))
        assert ho_id == rgr_dict['rgr_ho_fk']
        assert res_id == rgr_dict['rgr_res_id']
        assert sub_id == rgr_dict['rgr_sub_id']
        assert obj_id == rgr_dict['rgr_obj_id']
        assert arr_date.toordinal() == rgr_dict['rgr_arrival'].toordinal()
        assert dep_date.toordinal() == rgr_dict['rgr_departure'].toordinal()
        assert arr_date == rgr_dict['rgr_arrival']
        assert dep_date == rgr_dict['rgr_departure']

    @staticmethod
    def _compare_converted_field_dicts(dict_with_compare_keys, dict_with_compare_values):
        def _normalize_val(key, val):
            val = val.capitalize() if 'Name' in key else val.lower() if 'Email' in key else None if val == '' else val
            if isinstance(val, str) and len(val) > 40:
                val = val[:40].strip()
            return val
        diffs = [(sk, _normalize_val(sk, sv), _normalize_val(sk, dict_with_compare_values.get(sk)))
                 for sk, sv in dict_with_compare_keys.items()
                 if sk not in ('PersonAccountId', 'CurrencyIsoCode', 'Language__pc',
                               'SihotGuestObjId__pc', 'PersonHomePhone', 'PersonMailingCountry')
                 and _normalize_val(sk, sv) != _normalize_val(sk, dict_with_compare_values.get(sk))]
        return diffs

    def test_sending_resv_of_today(self, salesforce_connection, console_app_env):
        # whole week running 15 minutes on TEST system !!!!!
        sfc = salesforce_connection
        beg = datetime.date.today()
        end = beg + datetime.timedelta(days=1)
        ret = res_search(console_app_env, beg, date_till=end)
        assert isinstance(ret, list)
        res_count = len(ret)
        assert res_count
        asd = AssSysData(console_app_env)
        errors = list()
        for idx, res in enumerate(ret):
            print("++++  Test reservation {}/{} creation; res={}".format(idx, res_count, res))
            res_fields = Record(system=SDI_ASS, direction=FAD_ONTO)
            send_err = asd.sh_res_change_to_ass(res, ass_res_rec=res_fields)
            print('res_fields:', res_fields)
            if send_err:
                errors.append((idx, "sh_res_change_to_ass error " + send_err, res))
                continue

            cl_fields = client_data(console_app_env, res.val('ShId'))
            print('cl_fields', cl_fields)
            if not isinstance(cl_fields, dict):
                errors.append((idx, "client_data error - no dict=" + str(cl_fields), res))
                continue

            sf_data = Record(system=SDI_SF, direction=FAD_ONTO)\
                .add_system_fields(MAP_CLIENT_OBJECTS['Account'] + MAP_RES_OBJECT)
            send_err = asd.sf_ass_res_upsert(None, cl_fields, res_fields, sf_sent=sf_data)
            print('sf_data:', sf_data)
            if send_err:
                errors.append((idx, "sf_ass_res_upsert error " + send_err, res))
                continue

            sf_sent = sf_data.to_dict()
            sf_recd = sfc.res_data(sf_sent['ReservationOpportunityId'])
            if sfc.error_msg:
                errors.append((idx, "sfc.res_data() error " + sfc.error_msg, res))
                continue
            diff = self._compare_converted_field_dicts(sf_sent, sf_recd)
            if diff:
                errors.append((idx, "compare found differences: " + str(diff), res))
                continue
        assert not errors, "{} tests had {} fails; collected errors".format(len(ret), len(errors)) \
                           + str(["\n" + str(e) for e in errors])

    def test_sh_room_change_to_ass_4_33220(self, console_app_env):
        # use TO reservation with GDS 899993 from 26-Dec-17 to 3-Jan-18
        ho_id = '4'
        res_id = '33220'
        sub_id = '1'
        obj_id = '60544'
        room_id = '0999'
        asd = AssSysData(console_app_env)

        dt_in = datetime.datetime.now().replace(microsecond=0)
        asd.sh_room_change_to_ass('CI', ho_id=ho_id, res_id=res_id, sub_id=sub_id, room_id=room_id, action_time=dt_in)

        cols = ['rgr_ho_fk', 'rgr_res_id', 'rgr_sub_id', 'rgr_obj_id', 'rgr_room_id', 'rgr_time_in', 'rgr_time_out']

        rgr_list = asd.rgr_fetch_list(cols, dict(rgr_obj_id=obj_id))
        assert isinstance(rgr_list, list)
        rgr_dict = dict(zip(cols, rgr_list[0]))
        assert ho_id == rgr_dict['rgr_ho_fk']
        assert res_id == rgr_dict['rgr_res_id']
        assert sub_id == rgr_dict['rgr_sub_id']
        assert obj_id == rgr_dict['rgr_obj_id']
        assert room_id == rgr_dict['rgr_room_id']
        assert dt_in == rgr_dict['rgr_time_in']
        assert rgr_dict['rgr_time_out'] is None

        dt_out = datetime.datetime.now().replace(microsecond=0)
        asd.sh_room_change_to_ass('CO', ho_id=ho_id, res_id=res_id, sub_id=sub_id, room_id=room_id, action_time=dt_out)
        rgr_list = asd.rgr_fetch_list(cols, dict(rgr_obj_id=obj_id))
        assert isinstance(rgr_list, list)
        rgr_dict = dict(zip(cols, rgr_list[0]))
        assert ho_id == rgr_dict['rgr_ho_fk']
        assert res_id == rgr_dict['rgr_res_id']
        assert sub_id == rgr_dict['rgr_sub_id']
        assert obj_id == rgr_dict['rgr_obj_id']
        assert room_id == rgr_dict['rgr_room_id']
        assert dt_in == rgr_dict['rgr_time_in']
        assert dt_out == rgr_dict['rgr_time_out']


class TestAssSysDataAvailRoomsSep14:
    def test_avail_rooms_for_all_hotels_and_cats(self, ass_sys_data):    # SLOW (22 s)
        assert ass_sys_data.sh_avail_rooms(day=datetime.date(2017, 9, 14)) == 164  # 165 before Feb2018

    def test_avail_rooms_for_bhc_and_all_cats(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], day=datetime.date(2017, 9, 14)) == 21

    def test_avail_rooms_for_pbc_and_all_cats(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['4'], day=datetime.date(2017, 9, 14)) == 53

    def test_avail_rooms_for_bhc_pbc_and_all_cats(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1', '4'], day=datetime.date(2017, 9, 14)) == 74

    def test_avail_studios_for_all_hotels(self, ass_sys_data):   # SLOW (22 s)
        assert ass_sys_data.sh_avail_rooms(room_cat_prefix="S", day=datetime.date(2017, 9, 14)) == 17

    def test_avail_studios_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="S", day=datetime.date(2017, 9, 14)) == 8

    def test_avail_1bed_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="1", day=datetime.date(2017, 9, 14)) == 5

    def test_avail_1bed_junior_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="1J", day=datetime.date(2017, 9, 14)) == 4

    def test_avail_2bed_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="2", day=datetime.date(2017, 9, 14)) == 7

    def test_avail_3bed_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="3", day=datetime.date(2017, 9, 14)) == 1
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="3BPS", day=datetime.date(2017, 9, 14)) == 1


class TestAssSysDataAvailRoomsSep15:
    def test_avail_rooms_for_all_hotels_and_cats(self, ass_sys_data):    # SLOW (22 s)
        assert ass_sys_data.sh_avail_rooms(day=datetime.date(2017, 9, 15)) == 98  # 99 before Feb2018

    def test_avail_rooms_for_bhc_and_all_cats(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], day=datetime.date(2017, 9, 15)) == 21

    def test_avail_rooms_for_pbc_and_all_cats(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['4'], day=datetime.date(2017, 9, 15)) == 34

    def test_avail_rooms_for_bhc_pbc_and_all_cats(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1', '4'], day=datetime.date(2017, 9, 15)) == 55

    def test_avail_studios_for_all_hotels(self, ass_sys_data):   # SLOW (24 s)
        assert ass_sys_data.sh_avail_rooms(room_cat_prefix="S", day=datetime.date(2017, 9, 15)) == 23

    def test_avail_studios_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="S", day=datetime.date(2017, 9, 15)) == 11

    def test_avail_1bed_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="1", day=datetime.date(2017, 9, 15)) == 3

    def test_avail_1bed_junior_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="1J", day=datetime.date(2017, 9, 15)) == 2

    def test_avail_2bed_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="2", day=datetime.date(2017, 9, 15)) == 6

    def test_avail_3bed_for_bhc(self, ass_sys_data):
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="3", day=datetime.date(2017, 9, 15)) == 1
        assert ass_sys_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="3BPS", day=datetime.date(2017, 9, 15)) == 1


class TestAssSysDataCountRes:
    def test_count_res_sep14_for_any_and_all_cats(self, ass_sys_data):   # SLOW (22 s)
        assert ass_sys_data.sh_count_res(hotel_ids=['999'], day=datetime.date(2017, 9, 14)) == 20

    def test_count_res_sep14_for_any_and_stdo_cats(self, ass_sys_data):  # SLOW (21 s)
        asd = ass_sys_data
        assert asd.sh_count_res(hotel_ids=['999'], room_cat_prefix="STDO", day=datetime.date(2017, 9, 14)) == 16

    def test_count_res_sep14_for_any_and_1jnr_cats(self, ass_sys_data):  # SLOW (22 s)
        assert ass_sys_data.sh_count_res(hotel_ids=['999'], room_cat_prefix="1JNR", day=datetime.date(2017, 9, 14)) == 4

    # too slow - needs minimum 6 minutes
    # def test_count_res_sep14_all_hotels_and_cats(self, ass_sys_data):
    #     assert ass_sys_data.sh_count_res(day=datetime.date(2017, 9, 14)) == 906

    # too slow - needs minimum 1:30 minutes (sometimes up to 9 minutes)
    # def test_count_res_sep14_for_bhc_and_all_cats(self, ass_sys_data):
    #    assert ass_sys_data.sh_count_res(hotel_ids=['1'], day=datetime.date(2017, 9, 14)) == 207  # 273 before Feb2018


class TestAssSysDataAptWkYr:
    def test_apt_wk_yr(self, console_app_env, ass_sys_data):
        console_app_env._options['2018'] = '2018-01-05'     # create fake config entries (defined in SihotResImport.ini)
        console_app_env._options['2019'] = '2019-01-04'
        r = Record(fields=dict(ResArrival=datetime.date(2018, 6, 1)))
        assert ass_sys_data.sh_apt_wk_yr(r) == ('None-22', 2018)

        r = Record(fields=dict(ResArrival=datetime.date(2018, 6, 1), ResRoomNo='A'))
        assert ass_sys_data.sh_apt_wk_yr(r) == ('A-22', 2018)


class TestAssSysDataHotelData:
    def test_cat_by_size(self, ass_sys_data):
        assert ass_sys_data.cat_by_size(None, None) is None
        assert ass_sys_data.cat_by_size('', '') is None
        assert ass_sys_data.cat_by_size('BHC', '') is None
        assert ass_sys_data.cat_by_size('', '1 BED', allow_any=False) is None
        assert ass_sys_data.cat_by_size('BHC', 'xxx') is None
        assert ass_sys_data.cat_by_size('', '1 BED') == '1JNR'
        assert ass_sys_data.cat_by_size('BHC', '1 BED') == '1JNR'
        assert ass_sys_data.cat_by_size('1', '1 BED') == '1JNR'
        assert ass_sys_data.cat_by_size('ANY', '') is None
        assert ass_sys_data.cat_by_size('ANY', '', allow_any=False) is None
        assert ass_sys_data.cat_by_size('ANY', '1 BED') == '1JNR'
        assert ass_sys_data.cat_by_size('999', '1 BED') == '1JNR'
        assert ass_sys_data.cat_by_size('ANY', '1 BED', allow_any=False) == '1JNR'
        assert ass_sys_data.cat_by_size('999', '1 BED', allow_any=False) == '1JNR'
        assert ass_sys_data.cat_by_size('xxx', '1 BED') == '1JNR'
        assert ass_sys_data.cat_by_size('xxx', '1 BED', allow_any=False) is None

    def test_cat_by_room(self, ass_sys_data):
        assert ass_sys_data.cat_by_room(None) is None
        assert ass_sys_data.cat_by_room('') is None
        assert ass_sys_data.cat_by_room('131') == '1JNP'
        assert ass_sys_data.cat_by_room('0131') == '1JNP'

    def test_ho_id_list(self, ass_sys_data):
        assert len(ass_sys_data.ho_id_list())
        assert '1' in ass_sys_data.ho_id_list()
        assert '999' in ass_sys_data.ho_id_list()
        assert '1' in ass_sys_data.ho_id_list(acu_rs_codes=['BHC'])
        assert '999' in ass_sys_data.ho_id_list(acu_rs_codes=['ANY'])
        assert '1' not in ass_sys_data.ho_id_list(acu_rs_codes=['ANY'])
        assert '999' not in ass_sys_data.ho_id_list(acu_rs_codes=[])
        assert '999' not in ass_sys_data.ho_id_list(acu_rs_codes=['BHC'])
        assert '999' not in ass_sys_data.ho_id_list(acu_rs_codes=['xxx'])


class TestClientHelpers:
    def test_as_clients_pull(self, ass_sys_data):
        assert ass_sys_data.as_clients_pull() == ""
        assert len(ass_sys_data.clients) >= 0


class TestRciHelpers:
    def test_rci_arr_to_year_week(self, console_app_env, ass_sys_data):
        console_app_env._options['2018'] = '2018-01-05'     # create fake config entries (defined in SihotResImport.ini)
        console_app_env._options['2019'] = '2019-01-04'
        d1 = datetime.date(2018, 6, 1)
        assert ass_sys_data.rci_arr_to_year_week(d1) == (2018, 22)
