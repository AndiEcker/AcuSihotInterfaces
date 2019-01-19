# tests of AssSysData methods - some of them also done by the config settings tests (see test_config.py/asd)
import datetime
# import pytest

# from sys_data_ids import CLIENT_REC_TYPE_ID_OWNERS
from ae_sys_data import Record, FAD_ONTO, Records

from sfif import SF_RES_MAP, SF_CLIENT_MAPS
from shif import res_search, client_data, ResFetch, SH_CLIENT_MAP
from ass_sys_data import AssSysData, ASS_CLIENT_MAP
from sys_data_ids import SDI_ASS, SDI_SF


cl_test_rec = Record(fields=dict(AssId=None, AcuId='T000369', SfId=None, ShId=None, RciId="1234-6789012",
                                 Surname="Tester-Surname", Forename="Tester-Forename",
                                 Name="Tester-Forename Tester-Surname",
                                 Salutation=None, Title=None,
                                 Email="tester-surname@tester-host.com", Phone="001234567890123",
                                 DOB=datetime.date(year=1962, month=6, day=15),
                                 Street="Tester-street 36", City="Tester City", Postal="123456", POBox=None, State=None,
                                 Country="GB", Language="EN", Nationality="DE", Currency="EUR",
                                 ExtRefs=Records((Record(fields=dict(Type="RCI", Id="1234-6789012")),
                                                  Record(fields=dict(Type="ABC", Id="abc-def/ghi")),
                                                  Record(fields=dict(Type="RCI", Id="1234-6789345")),
                                                  Record(fields=dict(Type="xyz", Id="1a 234-xzy")),
                                                  )),
                                 GuestType='1', ProductTypes=None))
res_test_arr = datetime.date(year=datetime.date.today().year + 1, month=12, day=9)
res_test_rec = Record(fields=dict(AssId=None, AcuId='T963369', SfId=None, ShId=None,
                                  Surname="Tester-Res-Surname", Forename="Tester-Res-Forename",
                                  Name="Tester-Res-Forename Tester-Res-Surname",
                                  Email="tester-res-surname@tester-res-host.com", Phone="00321098765432",
                                  GuestType='1',
                                  RinId=None,
                                  ResAssId=None,
                                  ResHotelId='4', ResId=None, ResSubId=None, ResObjId=None, ResGdsNo='TEST-9876543333',
                                  ResArrival=res_test_arr, ResDeparture=res_test_arr + datetime.timedelta(days=9),
                                  ResRoomNo=None, ResRoomCat='STDO', ResPriceCat=None,
                                  ResStatus='1',
                                  ResMktGroup='TO', ResMktSegment='TO',
                                  ResSource=None, ResGroupNo=None, ResMktGroupNN=None,
                                  ResAdults=1, ResChildren=1,
                                  ResBoard=None,
                                  ResNote="test_ass_sys_data res_test_rec ResNote",
                                  ResCheckIn=None, ResCheckOut=None,
                                  ResVoucherNo=None,
                                  ResBooked=None, ResLongNote="test_ass_sys_data res_test_rec ResLongNote",
                                  ResRateSegment=None, ResAccount=None,
                                  ResPersons=Records((Record(fields=dict(AssId=None, RoomSeq=None, PersSeq=None,
                                                                         SurName="Tester-Res-Surname", Forename="",
                                                                         DOB=datetime.date(year=1962, month=6, day=3),
                                                                         GuestType='1A')),
                                                      Record(fields=dict(AssId=None, RoomSeq=None, PersSeq=None,
                                                                         SurName="", Forename="John-Boy",
                                                                         DOB=datetime.date(year=2019, month=1, day=3),
                                                                         GuestType='2A')),
                                                      )),
                                  ResAction=None,
                                  ))


def test_tmp(console_app_env, ass_sys_data):
    asd = ass_sys_data
    rec = res_test_rec.copy(deepness=-1)

    asd.reservations.append(rec)

    # first need to be pushed/created within Sihot, because AssCache.res_groups needs non-empty the ResObjId/rgr_obj_id
    asd.sh_reservation_push()
    assert not asd.error_message
    print(rec.val('ResObjId'))
    assert rec.val('ResObjId')
    assert rec.val('ResObjId') == asd.reservations[0].val('ResObjId')
    # .. so now we can test the push to AssCache
    asd.ass_reservations_push()
    assert not asd.error_message
    print(rec.val('ResAssId'))
    assert rec.val('ResAssId')
    assert rec.val('ResAssId') == asd.reservations[0].val('ResAssId')

    # added field_names arg for to only compare AssCache.clients fields
    recs, dif = asd.ass_reservations_compare(chk_values=dict(rgr_pk=rec.val('ResAssId')))
    assert not asd.error_message
    print(recs)
    assert len(recs) == 1 == len(asd.clients)
    print(dif)
    assert not dif
    # will always be False because asd.reservations has more fields than in AssCache:
    # assert repr(recs) == repr(asd.clients)
    print(repr(recs))
    print(repr(asd.clients))

    print()


class TestSysDataActions:
    def test_acu_clients_compare(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        # needs 3 minutes because full T_CD fetch:
        # .. asd.acu_clients_pull(filter_records=lambda r: len(r.val('ExtRefs')) < 69)
        # Using WHERE filter needs 2 minutes, and with additional CD_CODE filter finally needs only 8 seconds
        asd.acu_clients_pull(where_group_order="substr(CODE, 1, 1) = 'F' and length(EXT_REFS) > 69")
        assert not asd.error_message
        assert asd.clients
        cnt = len(asd.clients)
        acc = asd.clients.copy(deepness=-1)
        assert repr(acc) == repr(asd.clients)

        recs, dif = asd.acu_clients_compare(where_group_order="substr(CODE, 1, 1) = 'F' and length(EXT_REFS) > 69")
        assert not asd.error_message
        assert len(recs) == cnt == len(asd.clients)
        assert not dif
        assert repr(acc) == repr(asd.clients)
        assert repr(acc) == repr(recs)

    def test_ass_clients_pull_count(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        asd.ass_clients_pull(filter_records=lambda r: r.val('AssId') > 69)
        assert not asd.error_message
        assert asd.clients
        cnt = len(asd.clients)
        asd.ass_clients_pull(filter_records=lambda r: r.val('AssId') > 69)
        assert not asd.error_message
        assert len(asd.clients) == cnt * 2

        asd.clients.clear()
        assert not asd.clients
        asd.ass_clients_pull(field_names=['AssId', 'AcuId', 'ShId', 'Name'],
                             filter_records=lambda r: r.val('AssId') > 69)
        assert not asd.error_message
        assert cnt == len(asd.clients)
        asd.ass_clients_pull(match_fields=['AssId'],
                             filter_records=lambda r: r.val('AssId') > 69)
        assert not asd.error_message
        assert cnt == len(asd.clients)

    def test_ass_clients_pull_field_col_names(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        asd.ass_clients_pull(col_names=['cl_pk', 'cl_ac_id', 'cl_sh_id', 'cl_phone', 'cl_email'],
                             filter_records=lambda r: r.val('AssId') > 69)
        assert not asd.error_message
        assert asd.clients
        cnt = len(asd.clients)
        for rec in asd.clients:
            assert not rec.val('Name')

        asd.clients.clear()
        assert not asd.clients
        asd.ass_clients_pull(field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'],
                             filter_records=lambda r: r.val('AssId') > 69)
        assert not asd.error_message
        assert cnt == len(asd.clients)
        for rec in asd.clients:
            assert not rec.val('Name')

    def test_ass_clients_push_count_equal(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        asd.ass_clients_pull(filter_records=lambda r: r.val('AssId') > 69,
                             field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'])
        assert not asd.error_message
        assert asd.clients
        cnt = len(asd.clients)
        acc = asd.clients.copy(deepness=-1)
        assert repr(acc) == repr(asd.clients)
        # TODO: investigate why failing without repr: assert acc == asd.clients

        asd.ass_clients_push(filter_records=lambda r: r.val('AssId') > 69,
                             field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'],
                             match_fields=['AssId'])
        assert not asd.error_message
        assert repr(acc) == repr(asd.clients)

        recs, dif = asd.ass_clients_compare(filter_records=lambda r: r.val('AssId') > 69,
                                            field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'])
        assert not asd.error_message
        assert len(recs) == cnt == len(asd.clients)
        assert not dif
        assert repr(acc) == repr(asd.clients)
        assert repr(acc) == repr(recs)

    def test_ass_clients_push_after_pull_from_acu(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        # needs 3 minutes because full T_CD fetch:
        # .. asd.acu_clients_pull(filter_records=lambda r: len(r.val('ExtRefs')) < 69)
        # Using WHERE filter needs 2 minutes, and with additional CD_CODE filter finally needs only 8 seconds
        asd.acu_clients_pull(where_group_order="substr(CODE, 1, 1) = 'F' and length(EXT_REFS) > 69")
        assert not asd.error_message
        assert asd.clients
        cnt = len(asd.clients)
        acc = asd.clients.copy(deepness=-1)
        assert repr(acc) == repr(asd.clients)

        recs, dif = asd.acu_clients_compare(where_group_order="substr(CODE, 1, 1) = 'F' and length(EXT_REFS) > 69")
        assert not asd.error_message
        assert len(recs) == cnt == len(asd.clients)
        assert not dif
        assert repr(acc) == repr(asd.clients)
        assert repr(acc) == repr(recs)

        # mark pulled test records for to be compared and deleted at the end
        for rec in asd.clients:
            rec.set_val(('TST_TMP_' + rec.val('Name'))[:39], 'Name')

        asd.ass_clients_push(match_fields=['AcuId'])
        assert not asd.error_message

        # using where_group_order="substr(cl_ac_id, 1, 1) = 'F' and (SELECT list_agg(er_type || '=' || er_i==TOO COMPLEX
        recs, dif = asd.ass_clients_compare(filter_records=lambda r: not r.val('Name')
                                            or not r.val('Name').startswith('TST_TMP_'),
                                            match_fields=['AcuId'])
        assert not asd.error_message
        assert len(recs) == cnt == len(asd.clients)

        # TEARDOWN not working because AssInterface user has no rights to delete clients
        '''
        ass_conn = asd.connection(SDI_ASS)
        ass_conn.execute_sql("DELETE FROM clients WHERE cl_name LIKE 'TST_TMP_%'")
        assert not ass_conn.last_err_msg
        assert ass_conn.get_row_count() == cnt
        '''

    def test_ass_clients_compare_match_fields_default(self, ass_sys_data):
        asd = ass_sys_data
        assert not asd.clients
        asd.ass_clients_pull(col_names=['cl_pk', 'cl_ac_id', 'cl_sh_id', 'cl_phone', 'cl_email'],
                             filter_records=lambda r: r.val('AssId') > 69)
        assert not asd.error_message
        assert asd.clients
        cnt = len(asd.clients)

        recs, dif = asd.ass_clients_compare(field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'],
                                            filter_records=lambda r: r.val('AssId') > 69,
                                            match_fields=['AssId'])
        assert not asd.error_message
        assert len(recs) == cnt == len(asd.clients)
        assert not dif

        recs, dif = asd.ass_clients_compare(field_names=['AssId', 'AcuId', 'ShId', 'Phone', 'Email'],
                                            filter_records=lambda r: r.val('AssId') > 69)
        assert not asd.error_message
        assert len(recs) == cnt == len(asd.clients)
        assert not dif

    def test_ass_clients_push_with_ext_refs(self, ass_sys_data):
        asd = ass_sys_data
        rec = cl_test_rec.copy(deepness=-1)

        asd.clients.append(rec)
        asd.ass_clients_push(match_fields=['AcuId'])
        assert not asd.error_message
        assert rec.val('AssId')
        assert rec.val('AssId') == asd.clients[0].val('AssId')

        # added field_names arg for to only compare AssCache.clients fields
        recs, dif = asd.ass_clients_compare(chk_values=dict(cl_pk=rec.val('AssId'), cl_ac_id='T000369'),
                                            match_fields=('AcuId',),
                                            field_names=[fn for sn, fn in ASS_CLIENT_MAP])
        assert not asd.error_message
        assert len(recs) == 1 == len(asd.clients)
        assert not dif
        # the following assert will always fail because asd.clients has much more fields than AssCache.clients:
        # assert repr(recs) == repr(asd.clients)

    def test_sf_clients_push_with_ext_refs(self, ass_sys_data):
        asd = ass_sys_data
        rec = cl_test_rec.copy(deepness=-1)

        asd.clients.append(rec)
        asd.sf_clients_push()  # no explicit match field available; Assertion error if passing match_fields=['AcuId'])
        assert not asd.error_message
        print(rec.val('SfId'))
        assert rec.val('SfId')
        assert rec.val('SfId') == asd.clients[0].val('SfId')

        # added field_names arg for to only compare AssCache.clients fields
        recs, dif = asd.sf_clients_compare(chk_values=dict(Id=rec.val('SfId'), AcumenClientRef__pc='T000369'),
                                           match_fields=('AcuId',),
                                           field_names=[fn for sn, fn, *_ in SF_CLIENT_MAPS['Account']] + ['ExtRefs'])
        asd.connection(SDI_SF).cl_delete(rec.val('SfId'))  # TODO: convert in proper test data teardown
        assert not asd.error_message
        print(recs)
        assert len(recs) == 1 == len(asd.clients)
        print(dif)
        assert not dif
        # will always be False because asd.clients has more fields than in SF.Accounts:
        # assert repr(recs) == repr(asd.clients)
        print(repr(recs))
        print(repr(asd.clients))

    def test_sh_clients_push_with_ext_refs(self, ass_sys_data):
        asd = ass_sys_data
        rec = cl_test_rec.copy(deepness=-1)

        asd.clients.append(rec)
        asd.sh_clients_push()  # no explicit match field available; Assertion error if passing match_fields=['AcuId'])
        assert not asd.error_message
        print(rec.val('ShId'))
        assert rec.val('ShId')
        assert rec.val('ShId') == asd.clients[0].val('ShId')

        # added field_names arg for to only compare AssCache.clients fields
        recs, dif = asd.sh_clients_compare(chk_values=dict(OBJID=rec.val('ShId'), MATCHCODE='T000369'),
                                           match_fields=('AcuId',),
                                           field_names=[fn for sn, fn, *_ in SH_CLIENT_MAP] + ['ExtRefs'])
        assert not asd.error_message
        print(recs)
        assert len(recs) == 1 == len(asd.clients)
        print(dif)
        assert not dif
        # will always be False because asd.clients has more fields than in Sihot:
        # assert repr(recs) == repr(asd.clients)
        print(repr(recs))
        print(repr(asd.clients))


class TestAssSysDataSh:
    def test_res_save_4_33220(self, console_app_env):
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
        asd.res_save(res_data, ass_res_rec=rgr_rec)
        assert ho_id == rgr_rec['rgr_ho_fk']
        assert res_id == rgr_rec['rgr_res_id']
        assert sub_id == rgr_rec['rgr_sub_id']
        assert obj_id == rgr_rec['rgr_obj_id']
        assert arr_date == rgr_rec['rgr_arrival']
        assert dep_date == rgr_rec['rgr_departure']

        rgr_dict = dict()       # res_save allows also dict
        asd = AssSysData(console_app_env)
        asd.res_save(res_data, ass_res_rec=rgr_dict)
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
            send_err = asd.res_save(res, ass_res_rec=res_fields)
            print('res_fields:', res_fields)
            if send_err:
                errors.append((idx, "res_save error " + send_err, res))
                continue

            cl_fields = client_data(console_app_env, res.val('ShId'))
            print('cl_fields', cl_fields)
            if not isinstance(cl_fields, dict):
                errors.append((idx, "client_data error - no dict=" + str(cl_fields), res))
                continue

            sf_data = Record(system=SDI_SF, direction=FAD_ONTO)\
                .add_system_fields(SF_CLIENT_MAPS['Account'] + SF_RES_MAP)
            send_err = asd.sf_ass_res_upsert(None, cl_fields, res_fields, sf_sent=sf_data)
            print('sf_data:', sf_data)
            if send_err:
                errors.append((idx, "sf_ass_res_upsert error " + send_err, res))
                continue

            sf_sent = sf_data.to_dict()
            sf_recd = sfc.res_dict(sf_sent['ReservationOpportunityId'])
            if sfc.error_msg:
                errors.append((idx, "sfc.res_dict() error " + sfc.error_msg, res))
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


class TestRciHelpers:
    def test_rci_arr_to_year_week(self, console_app_env, ass_sys_data):
        console_app_env._options['2018'] = '2018-01-05'     # create fake config entries (defined in SihotResImport.ini)
        console_app_env._options['2019'] = '2019-01-04'
        d1 = datetime.date(2018, 6, 1)
        assert ass_sys_data.rci_arr_to_year_week(d1) == (2018, 22)
