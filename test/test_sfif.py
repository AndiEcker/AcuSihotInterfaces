from ass_sys_data import AssSysData


class TestSfFindClient:
    def test_not_existing_client(self, salesforce_connection):
        sfi = salesforce_connection
        sf_id, sf_obj = sfi.find_client(email="tst@tst.tst", phone="0034922777888",
                                        first_name="Testy", last_name="Tester")
        print('Encapsulated APEX REST call result', sf_id, sf_obj)
        assert not sf_id     # ... is None or ... == ''
        # before refactoring of SF Apex class: assert not obj or obj == 'None'   # '' or 'None'
        assert sf_obj == 'Lead'

    def test_identify_by_email(self, salesforce_connection, console_app_env):
        sfi = salesforce_connection
        # used for to wipe duplicates of previous failed test runs: 4sfi.client_delete('0012600000niFt6AAE', 'Account')

        asd = AssSysData(console_app_env)
        fn = "Testy"
        ln = "Tester"
        em = "testyTester@test.com"
        so = 'Account'
        sf_id, err, msg = asd.sf_client_upsert(fields_dict=dict(FirstName=fn, LastName=ln, Email=em), sf_obj=so)
        print("test_identify_by_email() sf_id={}/err={}/msg={}:".format(sf_id, err, msg))
        assert len(sf_id) == 18
        assert err == ""

        sf_found_id, sf_obj = sfi.find_client(email=em, first_name=fn, last_name=ln)
        print('Encapsulated APEX REST call result', sf_found_id, sf_obj)

        # before checking we need first to delete the test client
        err_msg, log_msg = sfi.client_delete(sf_id, so)
        print("Error/Log messages:", err_msg, '/', log_msg)
        assert not err_msg

        assert len(sf_found_id) == 18
        assert sf_found_id == sf_id
        assert sf_obj == so
