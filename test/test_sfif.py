from sys_data_ids import EXT_REFS_SEP, CLIENT_REC_TYPE_ID_OWNERS
from sfif import *


class TestConverter:
    def test_date_converters(self):
        d = datetime.datetime(2018, 1, 2, 13, 12, 11)
        s_ugly = "2018-1-2 13:12:11"
        s_nice = "2018-01-02 13:12:11"

        assert convert_date_from_sf(s_ugly) == d
        assert convert_date_from_sf(s_nice) == d
        assert convert_date_onto_sf(d) == s_nice

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


class TestReservation:
    sf_id_of_rci_id = dict()

    @staticmethod
    def _compare_converted_field_dicts(dict_with_compare_keys, dict_with_compare_values):
        diffs = [(sk, sv, dict_with_compare_values.get(sk)) for sk, sv in dict_with_compare_keys.items()
                 if (sv.capitalize() if 'Name' in sk else
                     sv.lower() if 'Email' in sk else
                     sv) != dict_with_compare_values.get(sk)]
        return diffs

    def test_sf_apexecute_core_res_upsert(self, salesforce_connection):
        sfc = salesforce_connection
        assert not sfc.error_msg
        sf_sent = dict(FirstName='First-Test-Name', LastName='Last-Test-Name', Language__pc='EN',
                       PersonEmail='TestName@test.tst', CD_CODE__pc='T987654',
                       Arrival__c=datetime.date(year=2018, month=3, day=1),
                       Departure__c=datetime.date(year=2018, month=3, day=8),
                       HotelId__c='4', Number__c='12345', SubNumber__c='1', Status__c='1',
                       Adults__c=2, Children__c=1, Note__c="core test no checks",
                       )
        ret = sfc.res_upsert(sf_sent)   # returning (PersonAccountId, ReservationOpportunityId, ErrorMessage)
        print(ret)
        assert not sfc.error_msg
        assert len(ret) == 3
        assert ret[0].startswith('001')
        assert ret[1].startswith('006')
        assert not ret[2]
        sf_recd = sfc.sf_res_data(ret[1])
        assert not self._compare_converted_field_dicts(sf_sent, sf_recd)

    def test_sf_res_upsert_basic_not_existing_any(self, salesforce_connection):
        sfc = salesforce_connection
        assert not sfc.error_msg
        cl_fields = {'NAME-1': 'LNam', 'NAME-2': 'FNam',
                     'OBJID': '123456789', 'MATCHCODE': 'E012345',
                     'T-LANGUAGE': 'EN', 'T-COUNTRY-CODE': 'GB',
                     'EMAIL-1': 't@ts.tst', 'PHONE-1': '0049765432100',
                     }
        arr_date = datetime.date.today() + datetime.timedelta(days=18)
        dep_date = arr_date + datetime.timedelta(days=7)
        res_fields = dict(rgr_ho_fk='999', rgr_res_id='999999', rgr_sub_id='9',
                          rgr_arrival=arr_date, rgr_departure=dep_date)
        sf_sent = dict()
        assert not sfc.sf_res_upsert(None, cl_fields, res_fields, sync_cache=False, sf_data=sf_sent)
        assert not sfc.error_msg
        sf_recd = sfc.sf_res_data(sf_sent['ReservationOpportunityId'])
        assert not self._compare_converted_field_dicts(sf_sent, sf_recd)

    def test_sf_res_upsert_basic_not_existing_bhc(self, salesforce_connection):
        sfc = salesforce_connection
        assert not sfc.error_msg
        cl_fields = {'NAME-1': 'LstNam', 'NAME-2': 'FstNam',
                     'OBJID': '11123456789', 'MATCHCODE': 'T111111',
                     'T-LANGUAGE': 'EN', 'T-COUNTRY-CODE': 'GB',
                     'EMAIL-1': 't111@ts111.tst', 'PHONE-1': '00491111111',
                     }
        arr_date = datetime.date.today() + datetime.timedelta(days=15)
        dep_date = arr_date + datetime.timedelta(days=7)
        res_fields = dict(rgr_ho_fk='1', rgr_res_id='1111111', rgr_sub_id='1',
                          rgr_arrival=arr_date, rgr_departure=dep_date)
        sf_sent = dict()
        assert not sfc.sf_res_upsert(None, cl_fields, res_fields, sync_cache=False, sf_data=sf_sent)
        assert not sfc.error_msg

        sf_recd = sfc.sf_res_data(sf_sent['ReservationOpportunityId'])
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(sf_sent, sf_recd)

    def test_sf_res_upsert_basic_not_existing_bhh(self, salesforce_connection):
        sfc = salesforce_connection
        cl_fields = {'NAME-1': 'LstNam2', 'NAME-2': 'FstNam2',
                     'OBJID': '22223456789', 'MATCHCODE': 'T222222',
                     'T-LANGUAGE': 'DE', 'T-COUNTRY-CODE': 'DE',
                     'EMAIL-1': 't222@ts222.tst', 'PHONE-1': '00492222222',
                     }
        arr_date = datetime.date.today() + datetime.timedelta(days=12)
        dep_date = arr_date + datetime.timedelta(days=7)
        res_fields = dict(rgr_ho_fk='2', rgr_res_id='222222', rgr_sub_id='2',
                          rgr_arrival=arr_date, rgr_departure=dep_date)
        sf_sent = dict()
        assert not sfc.sf_res_upsert(None, cl_fields, res_fields, sync_cache=False, sf_data=sf_sent)
        assert not sfc.error_msg

        sf_recd = sfc.sf_res_data(sf_sent['ReservationOpportunityId'])
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(sf_sent, sf_recd)

    def test_sf_res_upsert_basic_not_existing_hmc(self, salesforce_connection):
        sfc = salesforce_connection
        cl_fields = {'NAME-1': 'Lst3Nam', 'NAME-2': 'Fst3Nam',
                     'OBJID': '33323456789', 'MATCHCODE': 'T333333',
                     'T-LANGUAGE': 'ES', 'T-COUNTRY-CODE': 'ES',
                     'EMAIL-1': 't333@ts333.tst', 'PHONE-1': '00493333333',
                     }
        arr_date = datetime.date.today() + datetime.timedelta(days=3)
        dep_date = arr_date + datetime.timedelta(days=7)
        res_fields = dict(rgr_ho_fk='3', rgr_res_id='3333333', rgr_sub_id='3',
                          rgr_arrival=arr_date, rgr_departure=dep_date)
        sf_sent = dict()
        assert not sfc.sf_res_upsert(None, cl_fields, res_fields, sync_cache=False, sf_data=sf_sent)
        assert not sfc.error_msg

        sf_recd = sfc.sf_res_data(sf_sent['ReservationOpportunityId'])
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(sf_sent, sf_recd)

    def test_sf_res_upsert_basic_not_existing_pbc(self, salesforce_connection):
        sfc = salesforce_connection
        cl_fields = {'NAME-1': 'Lst4Nam', 'NAME-2': 'Fst4Nam',
                     'OBJID': '44423456789', 'MATCHCODE': 'T444444',
                     'T-LANGUAGE': 'FR', 'T-COUNTRY-CODE': 'FR',
                     'EMAIL-1': 't444@ts444.tst', 'PHONE-1': '004744444444',
                     }
        arr_date = datetime.date.today() + datetime.timedelta(days=4)
        dep_date = arr_date + datetime.timedelta(days=7)
        res_fields = dict(rgr_ho_fk='4', rgr_res_id='4444444', rgr_sub_id='4',
                          rgr_room_id='0842', rgr_arrival=arr_date, rgr_departure=dep_date)
        sf_sent = dict()
        assert not sfc.sf_res_upsert(None, cl_fields, res_fields, sync_cache=False, sf_data=sf_sent)
        assert not sfc.error_msg

        sf_recd = sfc.sf_res_data(sf_sent['ReservationOpportunityId'])
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(sf_sent, sf_recd)

    def test_sf_res_upsert_with_unicode_strings(self, salesforce_connection):
        # because HTTP is not supporting UNICODE we actually have to encode them as latin1/iso-8859-1 before sending
        # .. and decode back to unicode on receive, s.a. PEP333/3 at https://www.python.org/dev/peps/pep-3333/
        sfc = salesforce_connection
        cl_fields = {'NAME-1': 'Lästñame', 'NAME-2': 'FírstNümé',
                     'OBJID': '55423456789', 'MATCHCODE': 'T555555',
                     'T-LANGUAGE': 'ES', 'T-COUNTRY-CODE': 'FR',
                     'EMAIL-1': 't555@ts555.tst', 'PHONE-1': '004955555555',
                     }
        arr_date = datetime.date.today() + datetime.timedelta(days=4)
        dep_date = arr_date + datetime.timedelta(days=7)
        res_fields = dict(rgr_ho_fk='1', rgr_res_id='555555', rgr_sub_id='5',
                          rgr_room_id='A105', rgr_arrival=arr_date, rgr_departure=dep_date)
        sf_sent = dict()
        assert not sfc.sf_res_upsert(None, cl_fields, res_fields, sync_cache=False, sf_data=sf_sent)
        assert not sfc.error_msg

        sf_recd = sfc.sf_res_data(sf_sent['ReservationOpportunityId'])
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(sf_sent, sf_recd)

    def test_sf_res_upsert_basic_existing(self, salesforce_connection):
        sfc = salesforce_connection
        # dict(Name='FNam LNam', FirstName='FNam', LastName='LNam', Email='t@ts.tst', Phone='0049765432100')
        cl_fields = {'NAME-1': 'LNam', 'NAME-2': 'FNam',
                     'OBJID': '123456789', 'MATCHCODE': 'E012345',
                     'T-LANGUAGE': 'EN', 'T-COUNTRY-CODE': 'GB',
                     'EMAIL-1': 't@ts.tst', 'PHONE-1': '0049765432100',
                     }
        arr_date = datetime.date(2017, 12, 26)
        dep_date = datetime.date(2018, 1, 3)
        res_fields = dict(rgr_ho_fk='4', rgr_res_id='33220', rgr_sub_id='1',
                          rgr_gds_no='899993', rgr_obj_id='60544',
                          rgr_arrival=arr_date, rgr_departure=dep_date,
                          rgr_room_id='3322', rgr_room_cat_id='STDO', rgr_status='1',
                          rgr_mkt_group='SP', rgr_mkt_segment='TO',
                          rgr_adults=2, rgr_children=0,
                          rgr_comment="This is a test comment",
                          rgc_list=[dict(rgc_room_id='3322'), ],
                          )
        sf_sent = dict()
        assert not sfc.sf_res_upsert(None, cl_fields, res_fields, sf_data=sf_sent)
        assert not sfc.error_msg

        sf_recd = sfc.sf_res_data(sf_sent['ReservationOpportunityId'])
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(sf_sent, sf_recd)

    def test_sf_apexecute_core_room_change(self, salesforce_connection, test_date=None):
        sfc = salesforce_connection
        now = datetime.datetime.now().replace(microsecond=0)
        dt = test_date or now
        found_test_data = False
        for step in range(3):   # do 3 tests for each res: check-in, check-out and reset check-in/-out
            rgr_list = sfc.rgr_fetch_list(['rgr_sf_id', 'rgr_time_in', 'rgr_time_out', 'rgr_room_id'], dict(dt=dt),
                                          ":dt between rgr_arrival AND rgr_departure")
            assert not sfc.error_msg
            assert isinstance(rgr_list, list)
            if not rgr_list:
                break
            for res in rgr_list:
                if res[0]:  # rgr_sf_id
                    found_test_data = True
                    time_in = time_out = None
                    if not res[1]:  # rgr_time_in
                        time_in = dt
                    elif not res[2]:    # rgr_time_out
                        time_out = dt
                    ret = sfc.sf_conn.room_change(res[0], time_in, time_out, res[3])  # returning ErrorMessage
                    assert not ret
                    rd = sfc.sf_room_data(res[0])
                    assert not sfc.error_msg
                    assert not self._compare_converted_field_dicts(dict(CheckIn__c=time_in, CheckOut__c=time_out), rd)
        if not found_test_data:
            print("test_sf_apexecute_core_room_change() WARNING: no test data found at day {}!".format(dt))
            assert dt > datetime.datetime(year=2018, month=1, day=1)   # found reservations of last week
            self.test_sf_apexecute_core_room_change(sfc, test_date=dt - datetime.timedelta(weeks=1))

    def test_sf_room_change(self, salesforce_connection):
        sfc = salesforce_connection
        now = datetime.datetime.now().replace(microsecond=0)
        dt = now - datetime.timedelta(days=3)
        found_test_data = False
        rgr_list = sfc.rgr_fetch_list(['rgr_sf_id', 'rgr_time_in', 'rgr_time_out'], dict(dt=dt),
                                      ":dt between rgr_arrival AND rgr_departure")
        assert not sfc.error_msg
        assert isinstance(rgr_list, list)
        for res in rgr_list:
            if res[0]:  # rgr_sf_id
                ci = co = None
                sd = dict()
                if not res[1]:  # rgr_time_in
                    ci = dt
                    sd = dict(CheckIn__c=dt)
                elif not res[2]:    # rgr_time_out
                    co = dt
                    sd = dict(CheckOut__c=dt)
                if sd:
                    found_test_data = True
                    ret = sfc.sf_room_change(res[0], ci, co, None)  # returning ErrorMessage
                    assert not sfc.error_msg
                    assert not ret
                    rd = sfc.sf_room_data(res[0])
                    assert not sfc.error_msg
                    assert not self._compare_converted_field_dicts(sd, rd)
        if not found_test_data:
            print("test_sf_room_change() WARNING: no test data found at day {}!".format(dt))
            assert dt > datetime.datetime(year=2018, month=1, day=1)   # found reservations of last week
            self.test_sf_apexecute_core_room_change(sfc, test_date=dt - datetime.timedelta(weeks=1))

    def __not_finished__test_all_clients(self, salesforce_connection):
        sfc = salesforce_connection
        assert sfc.error_msg == ""
        clients = sfc.sf_clients_with_rci_id(EXT_REFS_SEP, owner_rec_types=[CLIENT_REC_TYPE_ID_OWNERS])
        print("Found clients:", clients)
        print("Error message:", sfc.error_msge)
        assert salesforce_connection.error_msg == ""
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
            sf_id, duplicates = sfc.sf_client_by_rci_id(rci_id)
            # print(rci_id, sf_id, duplicates)
            assert sf_id == self.sf_id_of_rci_id[rci_id]
            assert isinstance(duplicates, list)
