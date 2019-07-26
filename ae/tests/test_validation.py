import pytest
import os
import sys

from ae.console_app import ConsoleApp
from ae.validation import (
    correct_email, correct_phone, validate_flag_info, add_validation_options, init_validation, clients_to_validate,
    EmailValidator, PhoneValidator,
    EMAIL_DO_NOT_VALIDATE, EMAIL_NOT_VALIDATED, EMAIL_INVALIDATED, EMAIL_VALID, EMAIL_INVALID, EMAIL_ALL,
    PHONE_ALL, ADDR_ALL, )


@pytest.fixture
def console_app_env():
    return ConsoleApp('0.0', 'Console App Environment for EmailValidator and PhoneValidator')


class TestOfflineContactValidation:
    def test_correct_email(self):
        # edge cases: empty string or None as email
        assert correct_email('') == ('', False)
        assert correct_email(None) == ('', False)
        r = list()
        assert correct_email('', removed=r) == ('', False)
        assert r == []
        r = list()
        assert correct_email(None, removed=r) == ('', False)
        assert r == []

        # special characters !#$%&'*+-/=?^_`{|}~; are allowed in local part
        r = list()
        assert correct_email('john_smith@example.com', removed=r) == ('john_smith@example.com', False)
        assert r == []
        r = list()
        assert correct_email('john?smith@example.com', removed=r) == ('john?smith@example.com', False)
        assert r == []

        # dot is not the first or last character unless quoted, and does not appear consecutively unless quoted
        r = list()
        assert correct_email(".john.smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["0:."]
        r = list()
        assert correct_email("john.smith.@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["10:."]
        r = list()
        assert correct_email("john..smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["5:."]
        r = list()
        assert correct_email('"john..smith"@example.com', removed=r) == ('"john..smith"@example.com', False)
        assert r == []
        r = list()
        assert correct_email("john.smith@example..com", removed=r) == ("john.smith@example.com", True)
        assert r == ["19:."]

        # space and "(),:;<>@[\] characters are allowed with restrictions (they are only allowed inside a quoted string,
        # as described in the paragraph below, and in addition, a backslash or double-quote must be preceded
        # by a backslash);
        r = list()
        assert correct_email(" john.smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["0: "]
        r = list()
        assert correct_email("john .smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["4: "]
        r = list()
        assert correct_email("john.smith @example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["10: "]
        r = list()
        assert correct_email("john.smith@ example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["11: "]
        r = list()
        assert correct_email("john.smith@ex ample.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["13: "]
        r = list()
        assert correct_email("john.smith@example .com", removed=r) == ("john.smith@example.com", True)
        assert r == ["18: "]
        r = list()
        assert correct_email("john.smith@example. com", removed=r) == ("john.smith@example.com", True)
        assert r == ["19: "]
        r = list()
        assert correct_email("john.smith@example.com  ", removed=r) == ("john.smith@example.com", True)
        assert r == ["22: ", "23: "]
        r = list()
        assert correct_email('john(smith@example.com', removed=r) == ('johnsmith@example.com', True)
        assert r == ["4:("]
        r = list()
        assert correct_email('"john(smith"@example.com', removed=r) == ('"john(smith"@example.com', False)
        assert r == []

        # comments at begin or end of local and domain part
        r = list()
        assert correct_email("john.smith(comment)@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["10:(comment)"]
        r = list()
        assert correct_email("(comment)john.smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["0:(comment)"]
        r = list()
        assert correct_email("john.smith@example.com(comment)", removed=r) == ("john.smith@example.com", True)
        assert r == ["22:(comment)"]
        r = list()
        assert correct_email("john.smith@(comment)example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["11:(comment)"]
        r = list()
        assert correct_email(".john.smith@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["0:."]
        r = list()
        assert correct_email("john.smith.@example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["10:."]
        r = list()
        assert correct_email("john.smith@.example.com", removed=r) == ("john.smith@example.com", True)
        assert r == ["11:."]
        r = list()
        assert correct_email("john.smith@example.com.", removed=r) == ("john.smith@example.com", True)
        assert r == ["22:."]

        # international characters above U+007F
        r = list()
        assert correct_email('Heinz.Hübner@example.com', removed=r) == ('Heinz.Hübner@example.com', False)
        assert r == []

        # quoted may exist as a dot separated entity within the local-part, or it may exist when the outermost
        # .. quotes are the outermost characters of the local-part
        r = list()
        assert correct_email('abc."def".xyz@example.com', removed=r) == ('abc."def".xyz@example.com', False)
        assert r == []
        assert correct_email('"abc"@example.com', removed=r) == ('"abc"@example.com', False)
        assert r == []
        assert correct_email('abc"def"xyz@example.com', removed=r) == ('abcdefxyz@example.com', True)
        assert r == ['3:"', '7:"']

        # tests from https://en.wikipedia.org/wiki/Email_address
        r = list()
        assert correct_email('ex-indeed@strange-example.com', removed=r) == ('ex-indeed@strange-example.com', False)
        assert r == []
        r = list()
        assert correct_email("#!$%&'*+-/=?^_`{}|~@example.org", removed=r) == ("#!$%&'*+-/=?^_`{}|~@example.org", False)
        assert r == []
        r = list()
        assert correct_email('"()<>[]:,;@\\\\"!#$%&\'-/=?^_`{}| ~.a"@e.org', removed=r) \
            == ('"()<>[]:,;@\\\\"!#$%&\'-/=?^_`{}| ~.a"@e.org', False)
        assert r == []

        r = list()
        assert correct_email("A@e@x@ample.com", removed=r) == ("A@example.com", True)
        assert r == ["3:@", "5:@"]
        r = list()
        assert correct_email('this\ is\"not\\allowed@example.com', removed=r) == ('thisisnotallowed@example.com', True)
        assert r == ["4:\\", "5: ", '8:"', '12:\\']

    def test_correct_phone(self):
        assert correct_phone(None) == ('', False)
        assert correct_phone('') == ('', False)

        r = list()
        assert correct_phone('+4455667788', removed=r) == ('004455667788', True)
        assert r == ["0:+"]

        r = list()
        assert correct_phone(' +4455667788', removed=r) == ('004455667788', True)
        assert r == ["0: ", "1:+"]

        r = list()
        assert correct_phone('+004455667788', removed=r) == ('004455667788', True)
        assert r == ["0:+"]

        r = list()
        assert correct_phone(' 44 5566/7788', removed=r) == ('4455667788', True)
        assert r == ["0: ", "3: ", "8:/"]

        r = list()
        assert correct_phone(' 44 5566/7788-123', removed=r) == ('4455667788123', True)
        assert r == ["0: ", "3: ", "8:/", "13:-"]

        r = list()
        assert correct_phone(' 44 5566/7788-123', removed=r, keep_1st_hyphen=True) == ('4455667788-123', True)
        assert r == ["0: ", "3: ", "8:/"]


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
        cae = ConsoleApp('0.0', 'test_add_validation_options')
        assert 'filterSfClients' not in cae.config_options
        add_validation_options(cae)
        assert 'filterSfClients' in cae.config_options
        sys.argv = []
        assert cae.get_option('filterSfClients') == ""

    def test_init_validation_all(self, sys_argv_restore):
        fn = 'test_valid.ini'
        with open(fn, 'w') as fp:
            fp.write('[Settings]\n')
        cae = ConsoleApp('0.0', 'test_init_validation', additional_cfg_files=[fn])
        add_validation_options(cae, email_def=EMAIL_ALL, phone_def=PHONE_ALL, addr_def=ADDR_ALL)
        sys.argv = []
        cae.get_option('debugLevel')     # for to parse args before cae.set_option() calls (resetting option)

        assert cae.set_config('emailValidatorPauseSeconds', 1.0) == ''
        assert cae.set_config('emailValidatorMaxRetries', 1) == ''
        assert cae.set_config('phoneValidatorPauseSeconds', 1.0) == ''
        assert cae.set_config('phoneValidatorMaxRetries', 1) == ''
        assert cae.set_config('phoneValidatorAlternativeCountry', 'USA') == ''
        assert cae.set_config('addressValidatorPauseSeconds', 1.0) == ''
        assert cae.set_config('addressValidatorMaxRetries', 1) == ''
        assert cae.set_config('addressValidatorSearchUrl', 'https:/test.tst/search') == ''
        assert cae.set_config('addressValidatorFetchUrl', 'https:/test.tst/fetch') == ''
        assert cae.set_option('filterSfClients', 'SOQL TEST WHERE CLAUSE') == ''
        assert cae.set_option('filterSfRecTypes', 'SF TEST RECORD TYPES') == ''
        cae.config_load()
        ret_tuple = init_validation(cae)
        assert len(ret_tuple) == 13
        os.remove(fn)

    def test_init_validation_error(self, sys_argv_restore):
        fn = 'test_valid_err.ini'
        with open(fn, 'w') as fp:
            fp.write('[Settings]\n')
        cae = ConsoleApp('0.0', 'test_init_validation', additional_cfg_files=[fn])
        add_validation_options(cae, email_def=EMAIL_ALL, phone_def=PHONE_ALL, addr_def=ADDR_ALL)
        sys.argv = []

        assert cae.set_config('addressValidatorApiKey', '') == ''
        cae.config_load()
        with pytest.raises(AssertionError):
            init_validation(cae)

        assert cae.set_config('phoneValidatorApiKey', '') == ''
        cae.config_load()
        with pytest.raises(AssertionError):
            init_validation(cae)

        assert cae.set_config('emailValidatorApiKey', '') == ''
        cae.config_load()
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
        ev = EmailValidator(base_url=console_app_env.get_config('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_config('emailValidatorApiKey'))
        err_msg = ev.validate('Andreas.Ecker@wrong_host_name.tld')
        print("Validator error", err_msg)
        assert err_msg

    def test_invalid_email_wrong_name(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_config('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_config('emailValidatorApiKey'))
        err_msg = ev.validate('AndrödelDödel@gmail.com')
        print("Validator error", err_msg)
        assert err_msg

    def test_invalid_email_wrong_name_with_spaces(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_config('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_config('emailValidatorApiKey'))
        err_msg = ev.validate('Andreas Ecker@test.com')
        print("Validator error", err_msg)
        assert err_msg

    def test_valid_email_of_signallia(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_config('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_config('emailValidatorApiKey'))
        err_msg = ev.validate('Andreas.Ecker@signallia.com')
        print("Validator error", err_msg)
        assert not err_msg

    def test_valid_email_of_google(self, console_app_env):
        ev = EmailValidator(base_url=console_app_env.get_config('emailValidatorBaseUrl'),
                            api_key=console_app_env.get_config('emailValidatorApiKey'))
        err_msg = ev.validate('aecker2@gmail.com')
        print("Validator error", err_msg)
        assert not err_msg


class TestPhoneValidator:
    def test_invalid_phone(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        err_msg = ev.validate('1234567')
        print("Validator error", err_msg)
        assert err_msg

    def test_invalid_phone_with_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        err_msg = ev.validate('1234567', country_code='DE')
        print("Validator error", err_msg)
        assert err_msg

    def test_valid_phone_without_country_with_00_prefix(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('0049 7345 506122', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_00_prefix_and_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('0049 7345 506122', country_code='DE', ret_val_dict=ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_without_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+497345506122', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_with_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+497345506122', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_and_spaces_without_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+49 7345 506122', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_and_spaces_with_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+49 7345 506122', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_phone_with_int_prefix_and_spaces_with_wrong_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+49 7345 506122', country_code='xyz', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg)
        assert err_msg

    def test_valid_nat_phone_with_valid_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('07345506122', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_nat_phone_with_valid_country_and_spaces(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('07345 506122', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '00497345506122'

    def test_valid_swe_phone_with_wrong_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('0046705856794', country_code='DE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg)
        assert err_msg

    def test_valid_swe_phone_with_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('0046705856794', country_code='SE', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '0046705856794'

    def test_valid_swe_phone_with_no_country(self, console_app_env):
        ev = PhoneValidator(base_url=console_app_env.get_config('phoneValidatorBaseUrl'),
                            api_key=console_app_env.get_config('phoneValidatorApiKey'))
        ret = dict()
        err_msg = ev.validate('+46705856794', ret_val_dict=ret)
        print("Validator response", ret)
        print("Validator error", err_msg or 'OK - No Error')
        assert not err_msg
        assert ret['formatinternational'] == '0046705856794'
