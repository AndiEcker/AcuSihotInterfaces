# from ae_sys_data import Record
from sfif import *


class TestConverter:
    def test_date_converters(self):
        d = datetime.date(2018, 1, 2)
        s_ugly = "2018-1-2"
        s_nice = "2018-01-02"
        s_0_hours = s_nice + SF_DATE_ZERO_HOURS
        s_any_hours = s_ugly + " 12:13:14"
        s_T_sep = s_ugly + "T12:13:14"
        micro_sec = ".12345"

        assert convert_date_from_sf(s_ugly) - SF_TIME_DIFF_FROM == d
        assert convert_date_from_sf(s_nice) - SF_TIME_DIFF_FROM == d
        assert convert_date_from_sf(s_0_hours) - SF_TIME_DIFF_FROM == d
        assert convert_date_from_sf(s_any_hours) - SF_TIME_DIFF_FROM == d
        assert convert_date_from_sf(s_T_sep) - SF_TIME_DIFF_FROM == d
        assert convert_date_from_sf(s_0_hours + micro_sec) - SF_TIME_DIFF_FROM == d
        assert convert_date_from_sf(s_any_hours + micro_sec) - SF_TIME_DIFF_FROM == d
        assert convert_date_from_sf(s_T_sep + micro_sec) - SF_TIME_DIFF_FROM == d

        assert convert_date_onto_sf(d) == s_0_hours

    def test_date_time_converters(self):
        d = datetime.datetime(2018, 1, 2, 13, 12, 11)
        s_ugly = "2018-1-2 13:12:11"
        s_nice = "2018-01-02 13:12:11"
        s_T_sep = "2018-01-02T13:12:11"
        micro_sec = ".12345"

        assert convert_date_time_from_sf(s_ugly) - SF_TIME_DIFF_FROM == d
        assert convert_date_time_from_sf(s_nice) - SF_TIME_DIFF_FROM == d
        assert convert_date_time_from_sf(s_T_sep) - SF_TIME_DIFF_FROM == d
        assert convert_date_time_from_sf(s_nice + micro_sec) - SF_TIME_DIFF_FROM == d
        assert convert_date_time_from_sf(s_T_sep + micro_sec) - SF_TIME_DIFF_FROM == d

        assert convert_date_time_onto_sf(d) == s_nice

    def test_field_converters(self):
        assert not [cnv for cnv in field_from_converters.values() if not callable(cnv)]
        assert not [cnv for cnv in field_onto_converters.values() if not callable(cnv)]


class TestSfId:
    objs = (('001234567890123', 'Account'), ('003456789012345', 'Contact'), ('00Q456789012345', 'Lead'))

    def test_obj_from_id(self):
        for sf_id, obj in self.objs:
            assert obj_from_id(sf_id) == obj

    def test_ensure_long_id(self):
        for sf_id, obj in self.objs:
            assert ensure_long_id(sf_id)
            assert len(ensure_long_id(sf_id)) == 18


class TestPrepareConnection:
    def test_prepare_connection_manual(self, console_app_env):
        sf_conn = prepare_connection(console_app_env)
        assert sf_conn
        assert sf_conn.is_sandbox

    def test_prepare_connection_conftest(self, salesforce_connection):
        assert salesforce_connection
        assert salesforce_connection.is_sandbox


''' find_client is no longer supported by our SF

class TestSfFindClient:
    def test_not_existing_client(self, salesforce_connection):
        sfi = salesforce_connection
        sf_id, sf_obj = sfi.find_client(email="tst@tst.tst", phone="0034567890123",
                                        first_name="Testy", last_name="T_es_ter")
        assert not sf_id
        assert sf_obj == 'Account'

    def test_identify_by_email(self, salesforce_connection):
        sfi = salesforce_connection
        # used for to wipe duplicates of previous failed test runs: 4sfi.client_delete('0012600000niFt6AAE', 'Account')

        fn = "Testy"
        ln = "Tester"
        em = "TestyTester@testr.com"
        so = 'Account'
        sf_id, err, msg = sfi.sf_client_upsert(rec=dict(FirstName=fn, LastName=ln, PersonEmail=em), sf_obj=so)
        print("test_identify_by_email() sf_id={}/err={}/msg={}:".format(sf_id, err, msg))
        assert len(sf_id) == 18
        assert err == ""

        sf_found_id, sf_obj = sfi.find_client(email=em, first_name=fn, last_name=ln)
        print('Encapsulated APEX REST call result', sf_found_id, sf_obj)

        # delete the test client before checking to prevent leftovers for the next test runs
        err_msg, log_msg = sfi.client_delete(sf_id, so)
        print("Error/Log messages:", err_msg, '/', log_msg)
        assert not err_msg

        assert len(sf_found_id) == 18
        assert sf_found_id == sf_id
        assert sf_obj == so
'''


class TestReservation:
    sf_id_of_rci_id = dict()

    @staticmethod
    def _compare_converted_field_dicts(dict_with_compare_keys, dict_with_compare_values):
        diffs = [(sk, sv, dict_with_compare_values.get(sk)) for sk, sv in dict_with_compare_keys.items()
                 if sk not in ('PersonAccountId', 'CurrencyIsoCode', 'Language__pc',
                               'SihotGuestObjId__pc', 'PersonHomePhone')
                 and (sv.capitalize() if 'Name' in sk else
                      sv.lower() if 'Email' in sk else
                      None if sv == '' else
                      sv) != dict_with_compare_values.get(sk)]
        return diffs

    def test_sf_apexecute_core_res_upsert(self, salesforce_connection):
        sfc = salesforce_connection
        assert not sfc.error_msg
        rec = sfc.cl_res_rec_onto\
            .copy(deepness=-1)\
            .update(FirstName='First-Test-Name', LastName='Last-Test-Name', Language__pc='EN',
                    PersonEmail='TestName@test.tst',       # unknown: CD_CODE__pc='T987654',
                    Arrival__c=datetime.date(year=2018, month=3, day=1),
                    Departure__c=datetime.date(year=2018, month=3, day=8),
                    HotelId__c='4', Number__c='12345', SubNumber__c='1', Status__c='1',
                    Adults__c=2, Children__c=1, Note__c="core test no checks",
                    )
        sf_id, res_sf_id, err_msg = sfc.res_upsert(rec)   # (PersonAccountId, ReservationOpportunityId, ErrorMessage)
        print(sf_id, res_sf_id, err_msg)
        assert sf_id.startswith('001')
        assert res_sf_id.startswith('006')
        assert not err_msg
        assert not sfc.error_msg
        sf_recd = sfc.sf_res_data(res_sf_id)
        assert not self._compare_converted_field_dicts(rec.to_dict(system=SDI_SF, direction=FAD_ONTO), sf_recd)

    def test_res_upsert_basic_not_existing_any(self, salesforce_connection):
        sfc = salesforce_connection
        assert not sfc.error_msg

        arr_date = datetime.date.today() + datetime.timedelta(days=18)
        dep_date = arr_date + datetime.timedelta(days=7)
        rec = sfc.cl_res_rec_onto\
            .copy(deepness=-1)\
            .update({'Surname': 'LNam', 'Forename': 'FNam',
                     'SfId': '123456789', 'AcId': 'E012345',
                     'Language': 'EN', 'Country': 'GB',
                     'Email': 't@ts.tst', 'Phone': '0049765432100',
                     'ResHotelId': '999', 'ResId': '999999', 'ResSubId': '9',
                     'ResArrival': arr_date, 'ResDeparture': dep_date,
                     'ResAdults': 1, 'ResChildren': 0,
                     })
        sf_id, res_sf_id, err_msg = sfc.res_upsert(rec)
        assert not err_msg
        assert sf_id
        assert res_sf_id
        assert not sfc.error_msg

        sf_recd = sfc.sf_res_data(res_sf_id)
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(rec.to_dict(system=SDI_SF, direction=FAD_ONTO), sf_recd)

    def test_res_upsert_basic_not_existing_bhc(self, salesforce_connection):
        sfc = salesforce_connection
        assert not sfc.error_msg

        arr_date = datetime.date.today() + datetime.timedelta(days=15)
        dep_date = arr_date + datetime.timedelta(days=7)
        rec = sfc.cl_res_rec_onto\
            .copy(deepness=-1)\
            .update({'Surname': 'LstNam', 'Forename': 'FstNam',
                     'SfId': '11123456789', 'AcId': 'T111111',
                     'Language': 'EN', 'Country': 'GB',
                     'Email': 't111@ts111.tst', 'Phone': '00491111111',
                     'ResHotelId': '1', 'ResId': '1111111', 'ResSubId': '1',
                     'ResArrival': arr_date, 'ResDeparture': dep_date,
                     'ResAdults': 1, 'ResChildren': 0,
                     })
        sf_id, res_sf_id, err_msg = sfc.res_upsert(rec)
        assert not err_msg
        assert sf_id
        assert res_sf_id

        sf_recd = sfc.sf_res_data(res_sf_id)
        assert not self._compare_converted_field_dicts(rec.to_dict(system=SDI_SF, direction=FAD_ONTO), sf_recd)

    def test_res_upsert_with_unicode_strings(self, salesforce_connection):
        # because HTTP is not supporting UNICODE we actually have to encode them as latin1/iso-8859-1 before sending
        # .. and decode back to unicode on receive, s.a. PEP333/3 at https://www.python.org/dev/peps/pep-3333/
        sfc = salesforce_connection

        arr_date = datetime.date.today() + datetime.timedelta(days=4)
        dep_date = arr_date + datetime.timedelta(days=7)
        rec = sfc.cl_res_rec_onto\
            .copy(deepness=-1)\
            .update({'Surname': 'Lästñame', 'Forename': 'FírstNümé',
                     'SfId': '55423456789', 'AcId': 'T555555',
                     'Language': 'ES', 'Country': 'FR',
                     'Email': 't555@ts555.tst', 'Phone': '004955555555',
                     'ResHotelId': '1', 'ResId': '555555', 'ResSubId': '5',
                     'ResArrival': arr_date, 'ResDeparture': dep_date,
                     'ResAdults': 1, 'ResChildren': 0,
                     })
        sf_id, res_sf_id, err_msg = sfc.res_upsert(rec)
        assert not err_msg
        assert sf_id
        assert res_sf_id

        sf_recd = sfc.sf_res_data(res_sf_id)
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(rec.to_dict(system=SDI_SF, direction=FAD_ONTO), sf_recd)

    def test_room_change(self, salesforce_connection):
        sfc = salesforce_connection

        arr_date = (datetime.datetime.now() + datetime.timedelta(days=9)).replace(microsecond=0, tzinfo=None)
        dep_date = (arr_date + datetime.timedelta(days=7)).replace(microsecond=0, tzinfo=None)
        rec = sfc.cl_res_rec_onto\
            .copy(deepness=-1)\
            .update({'Surname': 'Surname_RC_test', 'Forename': 'Forename_RC_test',
                     'ResHotelId': '999', 'ResId': '999999', 'ResSubId': '9', 'ResStatus': '1',
                     'ResArrival': arr_date, 'ResDeparture': dep_date,
                     'ResAdults': 1, 'ResChildren': 0,
                     })
        cl_sf_id, res_sf_id, err_msg = sfc.res_upsert(rec)
        assert not err_msg
        assert cl_sf_id
        assert res_sf_id

        err_msg = sfc.room_change(res_sf_id, arr_date, None, '9999')
        assert not err_msg
        _dict = sfc.sf_room_data(res_sf_id)
        assert _dict['CheckIn__c'] == arr_date
        assert _dict['CheckOut__c'] is None

        err_msg = sfc.room_change(res_sf_id, None, dep_date, '9999')
        assert not err_msg
        _dict = sfc.sf_room_data(res_sf_id)
        assert _dict['CheckIn__c'] is None
        assert _dict['CheckOut__c'] == dep_date

        err_msg = sfc.room_change(res_sf_id, arr_date, dep_date, '9999')
        assert not err_msg
        _dict = sfc.sf_room_data(res_sf_id)
        assert _dict['CheckIn__c'] == arr_date
        assert _dict['CheckOut__c'] == dep_date
