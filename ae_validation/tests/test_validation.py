import pytest
import os
import sys

from ae.console_app import ConsoleApp
from ae_validation.validation import (
    validate_flag_info, add_validation_options, init_validation, clients_to_validate,
    EmailValidator, PhoneValidator,
    EMAIL_DO_NOT_VALIDATE, EMAIL_NOT_VALIDATED, EMAIL_INVALIDATED, EMAIL_VALID, EMAIL_INVALID, EMAIL_ALL,
    PHONE_ALL, ADDR_ALL, )


@pytest.fixture
def console_app_env():
    return ConsoleApp('Console App Environment for EmailValidator and PhoneValidator')


class TestCloudContactValidation:
    def test_validate_flag_info(self):
        assert 'undeclared' in validate_flag_info(None)
        assert validate_flag_info(EMAIL_DO_NOT_VALIDATE)
        assert validate_flag_info(EMAIL_NOT_VALIDATED)
        assert validate_flag_info(EMAIL_INVALIDATED)
        assert validate_flag_info(EMAIL_INVALID)
        assert validate_flag_info(EMAIL_VALID)
        assert validate_flag_info(EMAIL_ALL)

    def test_add_validation_options(self, sys_argv_restore):
        cae = ConsoleApp('test_add_validation_options')
        assert 'filterSfClients' not in cae.cfg_options
        add_validation_options(cae)
        assert 'filterSfClients' in cae.cfg_options
        sys.argv = []
        assert cae.get_opt('filterSfClients') == ""

    def test_init_validation_all(self, sys_argv_restore):
        fn = 'test_valid.ini'
        with open(fn, 'w') as fp:
            fp.write('[aeOptions]\n')
        cae = ConsoleApp('test_init_validation', additional_cfg_files=[fn])
        add_validation_options(cae, email_def=EMAIL_ALL, phone_def=PHONE_ALL, addr_def=ADDR_ALL)
        sys.argv = []
        cae.get_opt('debugLevel')     # for to parse args before cae.set_opt() calls (resetting config option)

        assert cae.set_var('emailValidatorPauseSeconds', 1.0) == ''
        assert cae.set_var('emailValidatorMaxRetries', 1) == ''
        assert cae.set_var('phoneValidatorPauseSeconds', 1.0) == ''
        assert cae.set_var('phoneValidatorMaxRetries', 1) == ''
        assert cae.set_var('phoneValidatorAlternativeCountry', 'USA') == ''
        assert cae.set_var('addressValidatorPauseSeconds', 1.0) == ''
        assert cae.set_var('addressValidatorMaxRetries', 1) == ''
        assert cae.set_var('addressValidatorSearchUrl', 'https:/test.tst/search') == ''
        assert cae.set_var('addressValidatorFetchUrl', 'https:/test.tst/fetch') == ''
        assert cae.set_opt('filterSfClients', 'SOQL TEST WHERE CLAUSE') == ''
        assert cae.set_opt('filterSfRecTypes', 'SF TEST RECORD TYPES') == ''
        cae.load_cfg_files()
        ret_tuple = init_validation(cae)
        assert len(ret_tuple) == 13
        os.remove(fn)

    def test_init_validation_error(self, sys_argv_restore):
        fn = 'test_valid_err.ini'
        with open(fn, 'w') as fp:
            fp.write('[aeOptions]\n')
        cae = ConsoleApp('test_init_validation', additional_cfg_files=[fn])
        add_validation_options(cae, email_def=EMAIL_ALL, phone_def=PHONE_ALL, addr_def=ADDR_ALL)
        sys.argv = []

        assert cae.set_var('addressValidatorApiKey', '') == ''
        cae.load_cfg_files()
        with pytest.raises(AssertionError):
            init_validation(cae)

        assert cae.set_var('phoneValidatorApiKey', '') == ''
        cae.load_cfg_files()
        with pytest.raises(AssertionError):
            init_validation(cae)

        assert cae.set_var('emailValidatorApiKey', '') == ''
        cae.load_cfg_files()
        with pytest.raises(AssertionError):
            init_validation(cae)

        os.remove(fn)


class TestClientDbValidation:
    class ConnMockEmptyOrError:
        error_msg = "ConnMockEmptyOrError"

        def soql_query_all(self, _query):
            pass

    class ConnMockClients:
        error_msg = ""

        @staticmethod
        def soql_query_all(_query):
            records = [dict(attributes='ignored', Id='003000111222333444'),
                       dict(attributes='ignored', Id='003111222333444555'),
                       dict(attributes='ignored', Id='003222333444555666'),
                       ]
            return dict(totalSize=3, records=records)

    def test_clients_to_validate_empty_or_error(self):
        assert clients_to_validate(self.ConnMockEmptyOrError()) == list()

    def test_clients_to_validate(self):
        records = clients_to_validate(self.ConnMockClients())
        assert len(records) == 3
        assert 'Id' in records[0]
        assert records[0]['Id'] == '003000111222333444'


class TestEmailValidator:
    """ validation service is only checking the host """

    def test_invalid_email_host_with_underscore(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_var('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_var('emailValidatorApiKey'))
        err_msg = ev.validate('Andreas.Ecker@wrong_host_name.tld')
        print("Validator error", err_msg)
        assert err_msg

    def test_invalid_email_wrong_name(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_var('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_var('emailValidatorApiKey'))
        err_msg = ev.validate('AndrödelDödel@gmail.com')
        print("Validator error", err_msg)
        assert err_msg

    def test_invalid_email_wrong_name_with_spaces(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_var('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_var('emailValidatorApiKey'))
        err_msg = ev.validate('Andreas Ecker@test.com')
        print("Validator error", err_msg)
        assert err_msg

    def test_valid_email_of_signallia(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_var('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_var('emailValidatorApiKey'))
        err_msg = ev.validate('Andreas.Ecker@signallia.com')
        print("Validator error", err_msg)
        assert not err_msg

    def test_valid_email_of_google(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_var('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_var('emailValidatorApiKey'))
        err_msg = ev.validate('aecker2@gmail.com')
        print("Validator error", err_msg)
        assert not err_msg


class TestPhoneValidator:
    def test_invalid_phone(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        err_msg = ev.validate('1234567')
        print("Validator error", err_msg)
        assert err_msg

    def test_invalid_phone_with_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        err_msg = ev.validate('1234567', country_code='DE')
        print("Validator error", err_msg)
        assert err_msg

    def test_valid_phone_without_country_with_00_prefix(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('0049 7345 506122', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_00_prefix_and_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('0049 7345 506122', country_code='DE', ret_val_dict=ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_without_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+497345506122', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_with_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+497345506122', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_and_spaces_without_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+49 7345 506122', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_and_spaces_with_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+49 7345 506122', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_and_spaces_with_wrong_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+49 7345 506122', country_code='xyz', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg)
        assert err_msg

    def test_valid_nat_phone_with_valid_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('07345506122', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_nat_phone_with_valid_country_and_spaces(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('07345 506122', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_swe_phone_with_wrong_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('0046705856794', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg)
        assert err_msg

    def test_valid_swe_phone_with_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('0046705856794', country_code='SE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '0046705856794'

    def test_valid_swe_phone_with_no_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_var('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_var('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+46705856794', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '0046705856794'
