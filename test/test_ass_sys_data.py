# tests of AssSysData methods - some of them also done by the config settings tests (see test_config.py/conf_data)
import datetime
# import pytest

from sxmlif import ResFetch, convert2date
from shif import elem_value
from ass_sys_data import correct_email, correct_phone, AssSysData, EXT_REFS_SEP, CLIENT_REC_TYPE_ID_OWNERS


class TestContactValidation:
    def test_correct_email(self):
        # edge cases: empty string or None as email
        r = list()
        assert correct_email('', False, r) == ('', False)
        assert r == []
        r = list()
        assert correct_email(None, False, r) == (None, False)
        assert r == []
        # special characters !#$%&'*+-/=?^_`{|}~; are allowed in local part
        r = list()
        assert correct_email('john_smith@example.com', False, r) == ('john_smith@example.com', False)
        assert r == []
        r = list()
        assert correct_email('john?smith@example.com', False, r) == ('john?smith@example.com', False)
        assert r == []

        # dot is not the first or last character unless quoted, and does not appear consecutively unless quoted
        r = list()
        assert correct_email(".john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0:."]
        r = list()
        assert correct_email("john.smith.@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10:."]
        r = list()
        assert correct_email("john..smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["5:."]
        r = list()
        assert correct_email('"john..smith"@example.com', False, r) == ('"john..smith"@example.com', False)
        assert r == []
        r = list()
        assert correct_email("john.smith@example..com", False, r) == ("john.smith@example.com", True)
        assert r == ["19:."]

        # space and "(),:;<>@[\] characters are allowed with restrictions (they are only allowed inside a quoted string,
        # as described in the paragraph below, and in addition, a backslash or double-quote must be preceded
        # by a backslash);
        r = list()
        assert correct_email(" john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0: "]
        r = list()
        assert correct_email("john .smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["4: "]
        r = list()
        assert correct_email("john.smith @example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10: "]
        r = list()
        assert correct_email("john.smith@ example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["11: "]
        r = list()
        assert correct_email("john.smith@ex ample.com", False, r) == ("john.smith@example.com", True)
        assert r == ["13: "]
        r = list()
        assert correct_email("john.smith@example .com", False, r) == ("john.smith@example.com", True)
        assert r == ["18: "]
        r = list()
        assert correct_email("john.smith@example. com", False, r) == ("john.smith@example.com", True)
        assert r == ["19: "]
        r = list()
        assert correct_email("john.smith@example.com  ", False, r) == ("john.smith@example.com", True)
        assert r == ["22: ", "23: "]
        r = list()
        assert correct_email('john(smith@example.com', False, r) == ('johnsmith@example.com', True)
        assert r == ["4:("]
        r = list()
        assert correct_email('"john(smith"@example.com', False, r) == ('"john(smith"@example.com', False)
        assert r == []

        # comments at begin or end of local and domain part
        r = list()
        assert correct_email("john.smith(comment)@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10:(comment)"]
        r = list()
        assert correct_email("(comment)john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0:(comment)"]
        r = list()
        assert correct_email("john.smith@example.com(comment)", False, r) == ("john.smith@example.com", True)
        assert r == ["22:(comment)"]
        r = list()
        assert correct_email("john.smith@(comment)example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["11:(comment)"]
        r = list()
        assert correct_email(".john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0:."]
        r = list()
        assert correct_email("john.smith.@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10:."]
        r = list()
        assert correct_email("john.smith@.example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["11:."]
        r = list()
        assert correct_email("john.smith@example.com.", False, r) == ("john.smith@example.com", True)
        assert r == ["22:."]

        # international characters above U+007F
        r = list()
        assert correct_email('Heinz.Hübner@example.com', False, r) == ('Heinz.Hübner@example.com', False)
        assert r == []

        # quoted may exist as a dot separated entity within the local-part, or it may exist when the outermost
        # .. quotes are the outermost characters of the local-part
        r = list()
        assert correct_email('abc."def".xyz@example.com', False, r) == ('abc."def".xyz@example.com', False)
        assert r == []
        assert correct_email('"abc"@example.com', False, r) == ('"abc"@example.com', False)
        assert r == []
        assert correct_email('abc"def"xyz@example.com', False, r) == ('abcdefxyz@example.com', True)
        assert r == ['3:"', '7:"']

        # tests from https://en.wikipedia.org/wiki/Email_address
        r = list()
        assert correct_email('ex-indeed@strange-example.com', False, r) == ('ex-indeed@strange-example.com', False)
        assert r == []
        r = list()
        assert correct_email("#!$%&'*+-/=?^_`{}|~@example.org", False, r) == ("#!$%&'*+-/=?^_`{}|~@example.org", False)
        assert r == []
        r = list()
        assert correct_email('"()<>[]:,;@\\\\"!#$%&\'-/=?^_`{}| ~.a"@e.org', False, r) \
            == ('"()<>[]:,;@\\\\"!#$%&\'-/=?^_`{}| ~.a"@e.org', False)
        assert r == []

        r = list()
        assert correct_email("A@e@x@ample.com", False, r) == ("A@example.com", True)
        assert r == ["3:@", "5:@"]
        r = list()
        assert correct_email('this\ is\"not\\allowed@example.com', False, r) == ('thisisnotallowed@example.com', True)
        assert r == ["4:\\", "5: ", '8:"', '12:\\']

    def test_correct_phone(self):
        r = list()
        assert correct_phone('+4455667788', False, r) == ('004455667788', True)
        assert r == ["0:+"]

        r = list()
        assert correct_phone(' +4455667788', False, r) == ('004455667788', True)
        assert r == ["0: ", "1:+"]

        r = list()
        assert correct_phone('+004455667788', False, r) == ('004455667788', True)
        assert r == ["0:+"]

        r = list()
        assert correct_phone(' 44 5566/7788', False, r) == ('4455667788', True)
        assert r == ["0: ", "3: ", "8:/"]


class TestAssSysDataAvailRoomsSep14:
    def test_avail_rooms_for_all_hotels_and_cats(self, config_data):
        assert config_data.sh_avail_rooms(day=datetime.date(2017, 9, 14)) == 164  # 165 before Feb2018

    def test_avail_rooms_for_bhc_and_all_cats(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], day=datetime.date(2017, 9, 14)) == 21

    def test_avail_rooms_for_pbc_and_all_cats(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['4'], day=datetime.date(2017, 9, 14)) == 53

    def test_avail_rooms_for_bhc_pbc_and_all_cats(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1', '4'], day=datetime.date(2017, 9, 14)) == 74

    def test_avail_studios_for_all_hotels(self, config_data):
        assert config_data.sh_avail_rooms(room_cat_prefix="S", day=datetime.date(2017, 9, 14)) == 17

    def test_avail_studios_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="S", day=datetime.date(2017, 9, 14)) == 8

    def test_avail_1bed_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="1", day=datetime.date(2017, 9, 14)) == 5

    def test_avail_1bed_junior_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="1J", day=datetime.date(2017, 9, 14)) == 4

    def test_avail_2bed_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="2", day=datetime.date(2017, 9, 14)) == 7

    def test_avail_3bed_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="3", day=datetime.date(2017, 9, 14)) == 1
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="3BPS", day=datetime.date(2017, 9, 14)) == 1


class TestAssSysDataAvailRoomsSep15:
    def test_avail_rooms_for_all_hotels_and_cats(self, config_data):
        assert config_data.sh_avail_rooms(day=datetime.date(2017, 9, 15)) == 98  # 99 before Feb2018

    def test_avail_rooms_for_bhc_and_all_cats(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], day=datetime.date(2017, 9, 15)) == 21

    def test_avail_rooms_for_pbc_and_all_cats(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['4'], day=datetime.date(2017, 9, 15)) == 34

    def test_avail_rooms_for_bhc_pbc_and_all_cats(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1', '4'], day=datetime.date(2017, 9, 15)) == 55

    def test_avail_studios_for_all_hotels(self, config_data):
        assert config_data.sh_avail_rooms(room_cat_prefix="S", day=datetime.date(2017, 9, 15)) == 23

    def test_avail_studios_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="S", day=datetime.date(2017, 9, 15)) == 11

    def test_avail_1bed_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="1", day=datetime.date(2017, 9, 15)) == 3

    def test_avail_1bed_junior_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="1J", day=datetime.date(2017, 9, 15)) == 2

    def test_avail_2bed_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="2", day=datetime.date(2017, 9, 15)) == 6

    def test_avail_3bed_for_bhc(self, config_data):
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="3", day=datetime.date(2017, 9, 15)) == 1
        assert config_data.sh_avail_rooms(hotel_ids=['1'], room_cat_prefix="3BPS", day=datetime.date(2017, 9, 15)) == 1


class TestAssSysDataCountRes:
    def test_count_res_sep14_for_any_and_all_cats(self, config_data):
        assert config_data.sh_count_res(hotel_ids=['999'], day=datetime.date(2017, 9, 14)) == 20

    def test_count_res_sep14_for_any_and_stdo_cats(self, config_data):
        assert config_data.sh_count_res(hotel_ids=['999'], room_cat_prefix="STDO", day=datetime.date(2017, 9, 14)) == 16

    def test_count_res_sep14_for_any_and_1jnr_cats(self, config_data):
        assert config_data.sh_count_res(hotel_ids=['999'], room_cat_prefix="1JNR", day=datetime.date(2017, 9, 14)) == 4

    # too slow - needs around 6 minutes
    # def test_count_res_sep14_all_hotels_and_cats(self, config_data):
    #     assert config_data.sh_count_res(day=datetime.date(2017, 9, 14)) == 906

    # quite slow - needs 1:30 minutes
    def test_count_res_sep14_for_bhc_and_all_cats(self, config_data):
        assert config_data.sh_count_res(hotel_ids=['1'], day=datetime.date(2017, 9, 14)) == 207  # 273 before Feb2018


class TestAssSysDataAptWkYr:
    def test_apt_wk_yr(self, console_app_env, config_data):
        console_app_env._options['2018'] = '2018-01-05'     # create fake config entries (defined in SihotResImport.ini)
        console_app_env._options['2019'] = '2019-01-04'
        assert config_data.sh_apt_wk_yr(dict(ARR=dict(elemVal='2018-06-01')), console_app_env) == ('None-22', 2018)
        assert config_data.sh_apt_wk_yr(dict(ARR=dict(elemVal='2018-06-01'),
                                             RN=dict(elemVal='A')), console_app_env) == ('A-22', 2018)


class TestAssSysDataHotelData:
    def test_cat_by_size(self, config_data):
        assert config_data.cat_by_size(None, None) is None
        assert config_data.cat_by_size('', '') is None
        assert config_data.cat_by_size('BHC', '') is None
        assert config_data.cat_by_size('', '1 BED', allow_any=False) is None
        assert config_data.cat_by_size('BHC', 'xxx') is None
        assert config_data.cat_by_size('', '1 BED') == '1JNR'
        assert config_data.cat_by_size('BHC', '1 BED') == '1JNR'
        assert config_data.cat_by_size('1', '1 BED') == '1JNR'
        assert config_data.cat_by_size('ANY', '') is None
        assert config_data.cat_by_size('ANY', '', allow_any=False) is None
        assert config_data.cat_by_size('ANY', '1 BED') == '1JNR'
        assert config_data.cat_by_size('999', '1 BED') == '1JNR'
        assert config_data.cat_by_size('ANY', '1 BED', allow_any=False) == '1JNR'
        assert config_data.cat_by_size('999', '1 BED', allow_any=False) == '1JNR'
        assert config_data.cat_by_size('xxx', '1 BED') == '1JNR'
        assert config_data.cat_by_size('xxx', '1 BED', allow_any=False) is None

    def test_cat_by_room(self, config_data):
        assert config_data.cat_by_room(None) is None
        assert config_data.cat_by_room('') is None
        assert config_data.cat_by_room('131') == '1JNP'
        assert config_data.cat_by_room('0131') == '1JNP'

    def test_ho_id_list(self, config_data):
        assert len(config_data.ho_id_list())
        assert '1' in config_data.ho_id_list()
        assert '999' in config_data.ho_id_list()
        assert '1' in config_data.ho_id_list(acu_rs_codes=['BHC'])
        assert '999' in config_data.ho_id_list(acu_rs_codes=['ANY'])
        assert '1' not in config_data.ho_id_list(acu_rs_codes=['ANY'])
        assert '999' not in config_data.ho_id_list(acu_rs_codes=[])
        assert '999' not in config_data.ho_id_list(acu_rs_codes=['BHC'])
        assert '999' not in config_data.ho_id_list(acu_rs_codes=['xxx'])


class TestClientHelpers:
    def test_cl_fetch_all(self, config_data):
        assert config_data.cl_fetch_all() == ""
        assert len(config_data.clients) >= 0


class TestRciHelpers:
    def test_rci_arr_to_year_week(self, console_app_env, config_data):
        console_app_env._options['2018'] = '2018-01-05'     # create fake config entries (defined in SihotResImport.ini)
        console_app_env._options['2019'] = '2019-01-04'
        d1 = datetime.datetime(2018, 6, 1)
        assert config_data.rci_arr_to_year_week(d1) == (2018, 22)


class TestAssSysDataSf:
    sf_id_of_rci_id = dict()

    def test_sf_res_upsert_basic_existing(self, console_app_env):
        asd = AssSysData(console_app_env)
        # dict(Name='FNam LNam', FirstName='FNam', LastName='LNam', Email='t@ts.tst', Phone='0049765432100')
        cl_fields = {'NAME-1': dict(elemVal='LNam'), 'NAME-2': dict(elemVal='FNam'),
                     'EMAIL-1': dict(elemVal='t@ts.tst'), 'PHONE-1': dict(elemVal='0049765432100')}
        arr_date = datetime.date(2017, 12, 26)
        dep_date = datetime.date(2018, 1, 3)
        res_fields = dict(rgr_ho_fk='4', rgr_res_id='33220', rgr_sub_id='1',
                          rgr_arrival=arr_date, rgr_departure=dep_date)
        assert not asd.sf_res_upsert(None, cl_fields, res_fields)

    def test_sf_res_upsert_basic_not_existing(self, console_app_env):
        asd = AssSysData(console_app_env)
        # dict(Name='FNam LNam', FirstName='FNam', LastName='LNam', Email='t@ts.tst', Phone='0049765432100')
        cl_fields = {'NAME-1': dict(elemVal='LNam'), 'NAME-2': dict(elemVal='FNam'),
                     'EMAIL-1': dict(elemVal='t@ts.tst'), 'PHONE-1': dict(elemVal='0049765432100')}
        arr_date = datetime.date.today() + datetime.timedelta(days=12)
        dep_date = arr_date + datetime.timedelta(days=7)
        res_fields = dict(rgr_ho_fk='999', rgr_res_id='999999', rgr_sub_id='9',
                          rgr_arrival=arr_date, rgr_departure=dep_date)
        assert not asd.sf_res_upsert(None, cl_fields, res_fields, sync_cache=False)

    def __not_finished__test_all_clients(self, config_data):
        assert config_data.error_message == ""
        clients = config_data.sf_clients_with_rci_id(EXT_REFS_SEP, owner_rec_types=[CLIENT_REC_TYPE_ID_OWNERS])
        print("Found clients:", clients)
        print("Error message:", config_data.error_message)
        assert config_data.error_message == ""
        for c in clients:
            print(c)
            assert len(c) == 5  # tuple items: (CD_CODE, Sf_Id, Sihot_Guest_Object_Id, RCI refs, is_owner)
            assert len(c[1]) == 18
            assert isinstance(c[3], str)
            assert len(c[3]) > 0
            rci_ids = c[3].split(EXT_REFS_SEP)
            assert len(rci_ids) > 0
            for rci_id in rci_ids:
                assert rci_id not in self.sf_id_of_rci_id.items()
                self.sf_id_of_rci_id[rci_id] = c[1]

        # now check if the client can be found by the rci_id
        print(repr(self.sf_id_of_rci_id))
        for rci_id in self.sf_id_of_rci_id:
            sf_id, duplicates = config_data.sf_client_by_rci_id(rci_id)
            # print(rci_id, sf_id, duplicates)
            assert sf_id == self.sf_id_of_rci_id[rci_id]
            assert isinstance(duplicates, list)


class TestAssSysDataSh:
    def test_sh_res_change_to_ass_4_33220(self, console_app_env):
        # use TO reservation with GDS 899993 from 26-Dec-17 to 3-Jan-18
        ho_id = '4'
        res_id = '33220'
        sub_id = '1'
        obj_id = '60544'
        asd = AssSysData(console_app_env)

        res_data = ResFetch(console_app_env).fetch_by_res_id(ho_id=ho_id, res_id=res_id, sub_id=sub_id)
        assert isinstance(res_data, dict)
        assert ho_id == elem_value(res_data, 'RES-HOTEL')
        assert res_id == elem_value(res_data, 'RES-NR')
        assert sub_id == elem_value(res_data, 'SUB-NR')
        assert obj_id == elem_value(res_data, ['RESERVATION', 'OBJID'])
        arr_date = convert2date(elem_value(res_data, ['RESERVATION', 'ARR']))
        dep_date = convert2date(elem_value(res_data, ['RESERVATION', 'DEP']))

        rgr_dict = dict()
        asd.sh_res_change_to_ass(res_data, rgr_dict=rgr_dict)
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
        assert arr_date.date() == rgr_dict['rgr_arrival']
        assert dep_date.date() == rgr_dict['rgr_departure']

        rgr_list = asd.rgr_fetch_list(cols, dict(rgr_ho_fk=ho_id, rgr_res_id=res_id, rgr_sub_id=sub_id))
        assert isinstance(rgr_list, list)
        rgr_dict = dict(zip(cols, rgr_list[0]))
        assert ho_id == rgr_dict['rgr_ho_fk']
        assert res_id == rgr_dict['rgr_res_id']
        assert sub_id == rgr_dict['rgr_sub_id']
        assert obj_id == rgr_dict['rgr_obj_id']
        assert arr_date.date() == rgr_dict['rgr_arrival']
        assert dep_date.date() == rgr_dict['rgr_departure']

    def test_sh_room_change_to_ass_4_33220(self, console_app_env):
        # use TO reservation with GDS 899993 from 26-Dec-17 to 3-Jan-18
        ho_id = '4'
        res_id = '33220'
        sub_id = '1'
        obj_id = '60544'
        asd = AssSysData(console_app_env)

        dt_in = datetime.datetime.now()
        asd.sh_room_change_to_ass('CI', ho_id=ho_id, res_id=res_id, sub_id=sub_id, action_time=dt_in)

        cols = ['rgr_ho_fk', 'rgr_res_id', 'rgr_sub_id', 'rgr_obj_id', 'rgr_time_in', 'rgr_time_out']

        rgr_list = asd.rgr_fetch_list(cols, dict(rgr_obj_id=obj_id))
        assert isinstance(rgr_list, list)
        rgr_dict = dict(zip(cols, rgr_list[0]))
        assert ho_id == rgr_dict['rgr_ho_fk']
        assert res_id == rgr_dict['rgr_res_id']
        assert sub_id == rgr_dict['rgr_sub_id']
        assert obj_id == rgr_dict['rgr_obj_id']
        assert dt_in == rgr_dict['rgr_time_in']
        assert rgr_dict['rgr_time_out'] is None

        dt_out = datetime.datetime.now()
        asd.sh_room_change_to_ass('CO', ho_id=ho_id, res_id=res_id, sub_id=sub_id, action_time=dt_out)
        rgr_list = asd.rgr_fetch_list(cols, dict(rgr_obj_id=obj_id))
        assert isinstance(rgr_list, list)
        rgr_dict = dict(zip(cols, rgr_list[0]))
        assert ho_id == rgr_dict['rgr_ho_fk']
        assert res_id == rgr_dict['rgr_res_id']
        assert sub_id == rgr_dict['rgr_sub_id']
        assert obj_id == rgr_dict['rgr_obj_id']
        assert dt_in == rgr_dict['rgr_time_in']
        assert dt_out == rgr_dict['rgr_time_out']
