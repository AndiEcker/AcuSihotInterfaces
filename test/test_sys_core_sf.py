from ae.sys_core import UsedSystems
from sys_core_sf import *


class TestReservation:
    sf_id_of_rci_id = dict()

    @staticmethod
    def _compare_converted_field_dicts(dict_with_compare_keys, dict_with_compare_values):
        def _normalize_val(sv, sk):
            return (sv.capitalize() if isinstance(sv, str) and 'name' in sk.lower() else
                    sv.lower() if isinstance(sv, str) and 'Email' in sk else
                    sv[:2] if isinstance(sv, str) and sk == 'Language__pc' else
                    # no longer needed since using Date.valueOf() in SF:
                    # .. sv[:-9] if isinstance(sv, str) and sv.endswith(SF_DATE_ZERO_HOURS) else
                    None if isinstance(sv, str) and sv == '' else
                    sv)
        diffs = [(sk, sv, _normalize_val(dict_with_compare_values.get(sk), sk))
                 for sk, sv in dict_with_compare_keys.items()
                 if sk not in ('xxPersonAccountId', 'xxCurrencyIsoCode', 'xxLanguage__pc',
                               'xxSihotGuestObjId__pc', 'xxPersonHomePhone')
                 and _normalize_val(sv, sk) != _normalize_val(dict_with_compare_values.get(sk), sk)]
        return diffs

    def test_sf_apexecute_core_res_upsert(self, salesforce_connection):
        sfc = salesforce_connection
        rec = sfc.cl_res_rec_onto.copy(deepness=-1)
        rec.update(FirstName='First-Test-Name', LastName='Last-Test-Name', Language__pc='EN',
                   PersonEmail='TestName@test.tst', AcumenClientRefpc='T987654',
                   Arrival__c='2018-03-01',  # no longer needed since using Date.valueOf() in SF: + SF_DATE_ZERO_HOURS
                   Departure__c='2018-03-08',  # no longer needed since using Date.valueOf(): + SF_DATE_ZERO_HOURS
                   HotelId__c='4', Number__c='12345', SubNumber__c='1', Status__c='1',
                   Adults__c=2, Children__c=1, Note__c="core test no checks",
                   )
        # returns (PersonAccountId, ReservationOpportunityId, ErrorMessage)
        sf_id, res_sf_id, err_msg = sfc.res_upsert(rec, push_onto=False)
        print(sf_id, res_sf_id, err_msg)
        assert sf_id.startswith('001')
        assert res_sf_id.startswith('006')
        assert not err_msg
        assert not sfc.error_msg
        sf_recd = sfc.res_dict(res_sf_id)
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(rec.to_dict(system=SDI_SF, direction=FAD_ONTO, push_onto=False),
                                                       sf_recd)

    def test_res_upsert_basic_not_existing_bhc(self, salesforce_connection):
        sfc = salesforce_connection

        arr_date = datetime.date.today() + datetime.timedelta(days=15)
        dep_date = arr_date + datetime.timedelta(days=7)
        rec = sfc.cl_res_rec_onto.copy(deepness=-1)
        rec.update({'Surname': 'LstNam111', 'Forename': 'FstNam111',
                    'ShId': '11123456711', 'AcuId': 'TST1111',
                    'Language': 'EN', 'Country': 'GB',
                    'Email': 't11111@ts11111.tst', 'Phone': '0049111111111',
                    'ResHotelId': '1', 'ResId': '111111', 'ResSubId': '11',
                    'ResArrival': arr_date, 'ResDeparture': dep_date,
                    'ResAdults': 1, 'ResChildren': 0,
                    })
        sf_id, res_sf_id, err_msg = sfc.res_upsert(rec)
        print(sf_id, res_sf_id, err_msg)
        assert not err_msg
        assert sf_id
        assert res_sf_id

        sf_recd = sfc.res_dict(res_sf_id)
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(rec.to_dict(system=SDI_SF, direction=FAD_ONTO), sf_recd)

    def test_res_upsert_basic_not_existing_any(self, salesforce_connection):
        sfc = salesforce_connection

        arr_date = datetime.date.today() + datetime.timedelta(days=18)
        dep_date = arr_date + datetime.timedelta(days=7)
        rec = sfc.cl_res_rec_onto.copy(deepness=-1)
        rec.update({'Surname': 'LNam222', 'Forename': 'FNam222',
                    'ShId': '2222222', 'AcuId': 'TST2222',
                    'Language': 'EN', 'Country': 'GB',
                    'Email': 't222@ts2222.tst', 'Phone': '00492222222',
                    'ResHotelId': '999', 'ResId': '22222', 'ResSubId': '2',
                    'ResArrival': arr_date, 'ResDeparture': dep_date,
                    'ResAdults': 2, 'ResChildren': 0,
                    })
        sf_id, res_sf_id, err_msg = sfc.res_upsert(rec)
        print(sf_id, res_sf_id, err_msg)
        assert not err_msg
        assert sf_id
        assert res_sf_id
        assert not sfc.error_msg

        sf_recd = sfc.res_dict(res_sf_id)
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(rec.to_dict(system=SDI_SF, direction=FAD_ONTO), sf_recd)

    def test_res_upsert_with_unicode_strings(self, salesforce_connection):
        # because HTTP is not supporting UNICODE we actually have to encode them as latin1/iso-8859-1 before sending
        # .. and decode back to unicode on receive, s.a. PEP333/3 at https://www.python.org/dev/peps/pep-3333/
        sfc = salesforce_connection

        arr_date = datetime.date.today() + datetime.timedelta(days=4)
        dep_date = arr_date + datetime.timedelta(days=7)
        rec = sfc.cl_res_rec_onto.copy(deepness=-1)
        rec.update({'Surname': 'Lästñame', 'Forename': 'FírstNümé',
                    'ShId': '55423456755', 'AcuId': 'TST5555',
                    'Language': 'FR', 'Country': 'FR',
                    'Email': 't5555@ts5555.tst', 'Phone': '0049555555555',
                    'ResHotelId': '1', 'ResId': '55555', 'ResSubId': '5',
                    'ResArrival': arr_date, 'ResDeparture': dep_date,
                    'ResAdults': 1, 'ResChildren': 0,
                    })
        sf_id, res_sf_id, err_msg = sfc.res_upsert(rec)
        print(sf_id, res_sf_id, err_msg)
        assert not err_msg
        assert sf_id
        assert res_sf_id

        sf_recd = sfc.res_dict(res_sf_id)
        assert not sfc.error_msg
        assert not self._compare_converted_field_dicts(rec.to_dict(system=SDI_SF, direction=FAD_ONTO), sf_recd)

    def test_room_change(self, salesforce_connection):
        sfc = salesforce_connection

        arr_date = (datetime.datetime.now() + datetime.timedelta(days=9)).replace(microsecond=0, tzinfo=None)
        dep_date = (arr_date + datetime.timedelta(days=7)).replace(microsecond=0, tzinfo=None)
        rec = sfc.cl_res_rec_onto.copy(deepness=-1)
        rec.update({'Surname': 'Surname_RC_test', 'Forename': 'Forename_RC_test',
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
        room_dict = sfc.room_data(res_sf_id)
        assert convert_date_time_from_sf(room_dict['CheckIn__c']) == arr_date
        assert room_dict['CheckOut__c'] is None

        err_msg = sfc.room_change(res_sf_id, None, dep_date, '9999')
        assert not err_msg
        room_dict = sfc.room_data(res_sf_id)
        assert room_dict['CheckIn__c'] is None
        assert convert_date_time_from_sf(room_dict['CheckOut__c']) == dep_date

        err_msg = sfc.room_change(res_sf_id, arr_date, dep_date, '9999')
        assert not err_msg
        room_dict = sfc.room_data(res_sf_id)
        assert convert_date_time_from_sf(room_dict['CheckIn__c']) == arr_date
        assert convert_date_time_from_sf(room_dict['CheckOut__c']) == dep_date


class TestConverter:
    def test_date_converters(self):
        d = datetime.date(2018, 1, 2)
        s_ugly = "2018-1-2"
        s_nice = "2018-01-02"
        # s_0_hours = s_nice  # no longer needed since using Date.valueOf() in SF: + SF_DATE_ZERO_HOURS
        s_any_hours = s_ugly + " 12:13:14"
        s_T_sep = s_ugly + "T12:13:14"
        micro_sec = ".12345"

        # no longer needed since changed company+user time zone to GMT+0: - SF_TIME_DIFF_FROM == d
        assert convert_date_from_sf(s_ugly) == d
        assert convert_date_from_sf(s_nice) == d
        ''' assert convert_date_from_sf(s_0_hours) == d '''
        assert convert_date_from_sf(s_any_hours) == d
        assert convert_date_from_sf(s_T_sep) == d
        ''' assert convert_date_from_sf(s_0_hours + micro_sec) == d '''
        assert convert_date_from_sf(s_any_hours + micro_sec) == d
        assert convert_date_from_sf(s_T_sep + micro_sec) == d

        assert convert_date_onto_sf(d) == s_nice

        assert convert_date_field_from_sf(None, s_ugly) == d
        assert convert_date_field_onto_sf(None, d) == s_nice

    def test_date_time_converters(self):
        d = datetime.datetime(2018, 1, 2, 13, 12, 11)
        s_ugly = "2018-1-2 13:12:11"
        s_nice = "2018-01-02 13:12:11"
        s_T_sep = "2018-01-02T13:12:11"
        micro_sec = ".12345"

        # no longer needed since changed company+user time zone to GMT+0: - SF_TIME_DIFF_FROM == d
        assert convert_date_time_from_sf(s_ugly) == d
        assert convert_date_time_from_sf(s_nice) == d
        assert convert_date_time_from_sf(s_T_sep) == d
        assert convert_date_time_from_sf(s_nice + micro_sec) == d
        assert convert_date_time_from_sf(s_T_sep + micro_sec) == d

        assert convert_date_time_onto_sf(d) == s_nice

        assert convert_date_time_field_from_sf(None, s_ugly) == d
        assert convert_date_time_field_onto_sf(None, d) == s_nice

    def test_field_converters(self):
        assert not [cnv for cnv in field_from_converters.values() if not callable(cnv)]
        assert not [cnv for cnv in field_onto_converters.values() if not callable(cnv)]

    def test_sf_field_name(self):
        assert sf_field_name('FirstName', 'Account') == 'Forename'
        assert sf_field_name('UnKnown', 'Account') == 'UnKnown'

    def test_field_dict_from_sf(self):
        sd = dict(FirstName='Forename', LastName='Surname')
        xfd = {_: _ for _ in sd.values()}

        fd = field_dict_from_sf(sd, 'Lead')
        assert fd == xfd

        fd = field_dict_from_sf(sd, 'Contact')
        assert fd == xfd

        fd = field_dict_from_sf(sd, 'Account')
        assert fd == xfd

    def test_field_list_to_sf(self):
        fns = ['Forename', 'Surname']
        xsf = ['FirstName', 'LastName']

        assert field_list_to_sf(fns, 'Lead') == xsf
        assert field_list_to_sf(fns, 'Contact') == xsf
        assert field_list_to_sf(fns, 'Account') == xsf


class TestSfId:
    phones = (('001234567890123', 'Account'), ('003456789012345', 'Contact'), ('00Q456789012345', 'Lead'))

    def test_obj_from_id(self):
        for sf_id, obj in self.phones:
            assert obj_from_id(sf_id) == obj

    def test_ensure_long_id(self):
        for sf_id, obj in self.phones:
            print(sf_id, obj)
            assert ensure_long_id(sf_id)
            assert ensure_long_id(sf_id) == sf_id + ('EAA' if obj == 'Lead' else 'AAA')
            assert len(ensure_long_id(sf_id)) == 18
            assert ensure_long_id(sf_id + 'AAA') == sf_id + 'AAA'

        assert ensure_long_id(None) is None


class TestConnection:
    def test_connection_manual(self, cons_app):
        us = UsedSystems(cons_app, SDI_SF)
        assert not us.connect()
        assert SDI_SF in us
        sf_conn = us[SDI_SF].connection
        assert sf_conn
        assert sf_conn.is_sandbox

    def test_connection_missing_cred(self, cons_app):
        us = UsedSystems(cons_app, SDI_SF)
        ck = us.available_systems[SDI_SF]['credential_keys']
        ck += ('MissingCredKey', )
        assert not us.connect()
        assert SDI_SF not in us

    def test_connection_conftest(self, salesforce_connection):
        assert salesforce_connection
        assert salesforce_connection.is_sandbox

    def test_connect(self, cons_app):
        us = UsedSystems(cons_app, SDI_SF)
        assert not us.connect()
        sf_conn = us[SDI_SF].connection
        res = sf_conn.soql_query_all("SELECT Id from Lead WHERE Name = '__test__connect__'")
        assert not sf_conn.error_msg
        assert res['totalSize'] == 0

    def test_connect_fail(self, cons_app):
        us = UsedSystems(cons_app, SDI_SF)
        assert not us.connect()
        sf_conn = us[SDI_SF].connection
        assert sf_conn
        assert not sf_conn.error_msg
        res = sf_conn.soql_query_all("SELECT Id from Lead WHERE Name = '__test__connect__'")
        assert sf_conn.error_msg
        assert 'INVALID_LOGIN' in sf_conn.error_msg
        assert res is None


class TestSimpleSalesforceObject:
    def test_lead_obj(self, salesforce_connection):
        obj = salesforce_connection.ssf_object('Lead')
        assert not salesforce_connection.error_msg
        assert obj

    def test_contact_obj(self, salesforce_connection):
        obj = salesforce_connection.ssf_object('Contact')
        assert not salesforce_connection.error_msg
        assert obj

    def test_account_obj(self, salesforce_connection):
        obj = salesforce_connection.ssf_object('Account')
        assert not salesforce_connection.error_msg
        assert obj

    def test_opportunity_obj(self, salesforce_connection):
        obj = salesforce_connection.ssf_object('Opportunity')
        assert not salesforce_connection.error_msg
        assert obj

    def test_ext_refs_obj(self, salesforce_connection):
        obj = salesforce_connection.ssf_object('External Reference')
        assert not salesforce_connection.error_msg
        assert obj


class TestRecordTypeId:
    def test_lead_obj(self, salesforce_connection):
        obj = salesforce_connection.record_type_id('Lead')
        assert not salesforce_connection.error_msg
        assert obj

    def test_contact_obj(self, salesforce_connection):
        obj = salesforce_connection.record_type_id('Contact')
        assert not salesforce_connection.error_msg
        assert obj

    def test_account_obj(self, salesforce_connection):
        obj = salesforce_connection.record_type_id('Account')
        assert not salesforce_connection.error_msg
        assert obj

    def test_opportunity_obj(self, salesforce_connection):
        obj = salesforce_connection.record_type_id('Opportunity')
        assert not salesforce_connection.error_msg
        assert obj


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
        # used to wipe duplicates of previous failed test runs: 4sfi.cl_delete('0012600000niFt6AAE', 'Account')

        fn = "Testy"
        ln = "Tester"
        em = "TestyTester@testr.com"
        so = 'Account'
        sf_id, err, msg = sfi.cl_upsert(rec=dict(FirstName=fn, LastName=ln, PersonEmail=em), sf_obj=so)
        print("test_identify_by_email() sf_id={}/err={}/msg={}:".format(sf_id, err, msg))
        assert len(sf_id) == 18
        assert err == ""

        sf_found_id, sf_obj = sfi.find_client(email=em, first_name=fn, last_name=ln)
        print('Encapsulated APEX REST call result', sf_found_id, sf_obj)

        # delete the test client before checking to prevent leftovers for the next test runs
        err_msg, log_msg = sfi.cl_delete(sf_id, so)
        print("Error/Log messages:", err_msg, '/', log_msg)
        assert not err_msg

        assert len(sf_found_id) == 18
        assert sf_found_id == sf_id
        assert sf_obj == so
'''


class TestClient:
    def test_cl_upsert_lead(self, salesforce_connection):
        sfc = salesforce_connection

        rec = Record(fields=dict(Forename='testy', Surname='Tst Lead'), system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ('LastName', 'Surname')))
        sf_id, err, msg = sfc.cl_upsert(rec, sf_obj='Lead')
        assert not err
        assert sf_id
        assert msg

        assert sfc.cl_field_data('Forename', sf_id) == 'Testy'  # SF is capitalizing names
        assert sfc.cl_field_data('Surname', sf_id) == 'Tst Lead'

        err, msg = sfc.cl_delete(sf_id)
        assert not err
        assert msg

    def test_cl_upsert_contact(self, salesforce_connection):
        sfc = salesforce_connection

        rec = Record(fields=dict(Forename='testy', Surname='Tst Contact'),
                     system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ('LastName', 'Surname')))
        sf_id, err, msg = sfc.cl_upsert(rec, sf_obj='Contact')
        assert not err
        assert sf_id
        assert msg

        assert sfc.cl_field_data('Forename', sf_id) == 'Testy'  # SF is capitalizing names
        assert sfc.cl_field_data('Surname', sf_id) == 'Tst Contact'

        err, msg = sfc.cl_delete(sf_id)
        assert not err
        assert msg

    def test_cl_upsert_account(self, salesforce_connection):
        sfc = salesforce_connection

        rec = Record(fields=dict(Forename='testy', Surname='Tst Account'),
                     system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ('LastName', 'Surname')))
        sf_id, err, msg = sfc.cl_upsert(rec, sf_obj='Account')
        assert not err
        assert sf_id
        assert msg

        assert sfc.cl_field_data('Forename', sf_id) == 'Testy'  # SF is capitalizing names
        assert sfc.cl_field_data('Surname', sf_id) == 'Tst Account'

        rec = Record(fields=dict(SfId=sf_id, Forename='Chg_FNam'), system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ))
        sf_upd_id, err, msg = sfc.cl_upsert(rec)
        assert not err
        assert sf_upd_id == sf_id
        assert msg
        assert sfc.cl_field_data('Forename', sf_id) == 'Chg_fnam'    # SF name capitalization

        err, msg = sfc.cl_delete(sf_id)
        assert not err
        assert msg

    def test_cl_upsert_errors(self, salesforce_connection):
        sfc = salesforce_connection

        rec = Record()
        sf_id, err, msg = sfc.cl_upsert(rec)
        assert not sf_id
        assert err

        rec.add_fields(dict(SfId='001456789012345678'))
        sf_id, err, msg = sfc.cl_upsert(rec)
        assert not sf_id
        assert err
        sf_id, err, msg = sfc.cl_upsert(rec, sf_obj='InExistent')
        assert not sf_id
        assert err

    def test_ext_refs(self, salesforce_connection):
        sfc = salesforce_connection

        rec = Record(fields=dict(Forename='testy', Surname='Test Ext Ref'),
                     system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ('LastName', 'Surname')))
        sf_id, err, msg = sfc.cl_upsert(rec, sf_obj='Account')
        assert not err
        assert sf_id

        sf_er_id1, err, msg = sfc.cl_ext_ref_upsert(sf_id, 'TST-TYPE', 'TST-ID-123')
        assert not err
        assert sf_er_id1
        assert msg
        sf_er_id2, err, msg = sfc.cl_ext_ref_upsert(sf_id, 'TST-TYPE', 'TST-ID-456')
        assert not err
        assert sf_er_id2
        assert msg
        sf_er_id3, err, msg = sfc.cl_ext_ref_upsert(sf_id, 'OTHER-TYPE', 'TST-ID-123')
        assert not err
        assert sf_er_id3
        assert msg

        ext_refs = sfc.cl_ext_refs(sf_id, return_obj_id=True)
        assert not sfc.error_msg
        assert ext_refs
        assert len(ext_refs) == 3
        assert ('TST-TYPE', sf_er_id1) in ext_refs
        assert ('TST-TYPE', sf_er_id2) in ext_refs
        assert ('OTHER-TYPE', sf_er_id3) in ext_refs

        ext_refs = sfc.cl_ext_refs(sf_id)
        assert not sfc.error_msg
        assert ext_refs
        assert len(ext_refs) == 3
        assert ('TST-TYPE', 'TST-ID-123') in ext_refs
        assert ('TST-TYPE', 'TST-ID-456') in ext_refs
        assert ('OTHER-TYPE', 'TST-ID-123') in ext_refs

        ext_refs = sfc.cl_ext_refs(sf_id, er_type='TST-TYPE')
        assert not sfc.error_msg
        assert ext_refs
        assert len(ext_refs) == 2
        assert 'TST-ID-123' in ext_refs
        assert 'TST-ID-456' in ext_refs

        ext_refs = sfc.cl_ext_refs(sf_id, er_type='OTHER-TYPE')
        assert not sfc.error_msg
        assert ext_refs
        assert len(ext_refs) == 1
        assert ext_refs[0] == 'TST-ID-123'

        ext_refs = sfc.cl_ext_refs(sf_id, er_id='TST-ID-123')
        assert not sfc.error_msg
        assert ext_refs
        assert len(ext_refs) == 2
        assert isinstance(ext_refs[0], (tuple, list))
        assert ext_refs[0][0] in ('TST-TYPE', 'OTHER-TYPE')
        assert ext_refs[1][0] in ('TST-TYPE', 'OTHER-TYPE')
        assert ext_refs[0][0] != ext_refs[1][0]
        assert ext_refs[0][1] == ext_refs[1][1] == 'TST-ID-123'

        # update
        upd_rec = Record(fields={'Type': 'TST-TYPE', 'Id': 'TST-ID-789'})
        sf_er_id3b, err, msg = sfc.cl_ext_ref_upsert(sf_id, 'OTHER-TYPE', 'TST-ID-123', upd_rec=upd_rec)
        assert not err
        assert sf_er_id3b

        ext_refs = sfc.cl_ext_refs(sf_id, er_type='TST-TYPE')
        assert not sfc.error_msg
        assert ext_refs
        assert len(ext_refs) == 3
        assert 'TST-ID-123' in ext_refs
        assert 'TST-ID-456' in ext_refs
        assert 'TST-ID-789' in ext_refs

        # clean-up
        err, msg = sfc.cl_delete(sf_id)
        assert not err
        assert msg

        ext_refs = sfc.cl_ext_refs(sf_id)
        assert not sfc.error_msg
        assert not ext_refs
        assert len(ext_refs) == 0

    def test_cl_field_data(self, salesforce_connection):
        sfc = salesforce_connection

        rec = Record(fields=dict(   # AssId='123123', NOT IMPLEMENTED IN SF
                                 AcuId='T000123', ShId='999123', Email='cl@fld.data',
                                 Forename='testy', Surname='Test Field Data Fetch'),
                     system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields(SF_CLIENT_MAPS['Account'])
        rec.pop('SfId')     # remove SfId (Id SF field) to prevent SF create Account error
        sf_id, err, msg = sfc.cl_upsert(rec, sf_obj='Account')
        assert not err
        assert sf_id

        # AssId NOT IMPLEMENTED IN SF: assert sfc.cl_ass_id(sf_id) == '123123'
        assert sfc.cl_ac_id(sf_id) == 'T000123'
        assert sfc.cl_sh_id(sf_id) == '999123'
        assert sfc.cl_id_by_email('cl@fld.data', sf_obj='Account')

        err, msg = sfc.cl_delete(sf_id)
        assert not err
        assert msg

    def test_cl_by_rci_id(self, salesforce_connection):
        sfc = salesforce_connection

        # first clean up SF with all clients with this test RCI Id - from last tests
        sf_found_id, dup_cl = sfc.cl_by_rci_id('5-987654321')
        print(sf_found_id, dup_cl)
        for sf_id in ([sf_found_id] if sf_found_id else []) + dup_cl:
            err, msg = sfc.cl_delete(sf_id)
            assert not err
            assert msg

        rec = Record(fields=dict(Forename='testy', Surname='Test Main RCI Ref', RciId='5-987654321'),
                     system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ('LastName', 'Surname'), ('RCI_Reference__pc', 'RciId')))
        sf_id_main, err, msg = sfc.cl_upsert(rec, sf_obj='Account')
        assert not err
        assert sf_id_main

        rec = Record(fields=dict(Forename='testy', Surname='Test RCI Ref'), system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ('LastName', 'Surname')))
        sf_id, err, msg = sfc.cl_upsert(rec, sf_obj='Account')
        assert not err
        assert sf_id
        sf_er_id, err, msg = sfc.cl_ext_ref_upsert(sf_id, 'TST-RCI', '5-987654321')
        assert not err
        assert sf_er_id
        assert msg

        sf_found_id, dup_cl = sfc.cl_by_rci_id('5-987654321')
        print(sf_found_id, dup_cl)
        assert not sfc.error_msg
        assert sf_found_id
        assert sf_found_id == sf_id_main
        assert len(dup_cl) == 1
        assert [sf_id] == dup_cl

        err, msg = sfc.cl_delete(sf_id)
        assert not err
        err, msg = sfc.cl_delete(sf_id_main)
        assert not err

    def test_clients_with_rci_id(self, salesforce_connection):
        sfc = salesforce_connection

        rec = Record(fields=dict(Forename='testy', Surname='Test Cl main with RCI Ref', RciId='X-678901234'),
                     system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ('LastName', 'Surname'), ('RCI_Reference__pc', 'RciId')))
        sf_id_main, err, msg = sfc.cl_upsert(rec, sf_obj='Account')
        assert not err
        assert sf_id_main

        rec = Record(fields=dict(Forename='testy', Surname='Test Cl with RCI Ref'), system=SDI_SF, direction=FAD_ONTO)
        rec.add_system_fields((('FirstName', 'Forename'), ('LastName', 'Surname')))
        sf_id, err, msg = sfc.cl_upsert(rec, sf_obj='Account')
        assert not err
        sf_er_id, err, msg = sfc.cl_ext_ref_upsert(sf_id, 'RCI', 'Y-987654321')
        assert not err

        clients = sfc.clients_with_rci_id()
        assert not sfc.error_msg
        assert len(clients) >= 2
        sf_ids = list()
        rci_ids = list()
        for cl in clients:
            sf_ids.append(cl[2])
            rci_ids.extend([_ for _ in cl[4].split(EXT_REFS_SEP)])
        assert sf_id_main in sf_ids
        assert sf_id in sf_ids
        assert 'X-678901234' in rci_ids
        assert 'Y-987654321' in rci_ids

        err, msg = sfc.cl_delete(sf_id)
        assert not err
        err, msg = sfc.cl_delete(sf_id_main)
        assert not err
