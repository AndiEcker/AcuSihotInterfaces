from ae_contact_validation import EmailValidator, PhoneValidator


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
        err_msg = ev.validate('Andreas.Ecker@test.com')
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
