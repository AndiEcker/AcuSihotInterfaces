"""
    providing/encapsulating services for to validate email addresses, telephone numbers and int. addresses
"""
import time
import requests
import json

from ae_console_app import uprint

# contact record types and ids
CONTACT_REC_TYPE_ID_OWNERS = '012w0000000MSyZAAW'  # 15 digit ID == 012w0000000MSyZ
CONTACT_REC_TYPE_RENTALS = 'Rentals'


# argument values for validate_flag_info() and sfif.py/SfInterface.contacts_to_validate()
EMAIL_DO_NOT_VALIDATE = ""
EMAIL_NOT_VALIDATED = "NULL"
EMAIL_INVALIDATED = "'0'"
EMAIL_VALID = "'1'"
EMAIL_INVALID = EMAIL_NOT_VALIDATED + ',' + EMAIL_INVALIDATED
EMAIL_ALL = EMAIL_NOT_VALIDATED + ',' + EMAIL_INVALIDATED + ',' + EMAIL_VALID

PHONE_DO_NOT_VALIDATE = ""
PHONE_NOT_VALIDATED = "NULL"
PHONE_INVALIDATED = "'0'"
PHONE_VALID = "'1'"
PHONE_INVALID = PHONE_NOT_VALIDATED + ',' + PHONE_INVALIDATED
PHONE_ALL = PHONE_NOT_VALIDATED + ',' + PHONE_INVALIDATED + ',' + PHONE_VALID

ADDR_DO_NOT_VALIDATE = ""
ADDR_NOT_VALIDATED = "NULL"
ADDR_INVALIDATED = "'0'"
ADDR_VALID = "'1'"
ADDR_INVALID = ADDR_NOT_VALIDATED + ',' + ADDR_INVALIDATED
ADDR_ALL = ADDR_NOT_VALIDATED + ',' + ADDR_INVALIDATED + ',' + ADDR_VALID


def validate_flag_info(validate_flag):
    if validate_flag in (EMAIL_DO_NOT_VALIDATE, PHONE_DO_NOT_VALIDATE, ADDR_DO_NOT_VALIDATE):
        info = "Do Not Validate"
    elif validate_flag in (EMAIL_NOT_VALIDATED, PHONE_NOT_VALIDATED, ADDR_NOT_VALIDATED):
        info = "Not Validated Only"
    elif validate_flag in (EMAIL_INVALIDATED, PHONE_INVALIDATED, ADDR_INVALIDATED):
        info = "Invalidated Only"
    elif validate_flag in (EMAIL_INVALID, PHONE_INVALID, ADDR_INVALID):
        info = "Invalidated And Not Validated"
    elif validate_flag in (EMAIL_VALID, PHONE_VALID, ADDR_VALID):
        info = "Re-validate Valid"
    elif validate_flag in (EMAIL_ALL, PHONE_ALL, ADDR_ALL):
        info = "All"
    else:
        info = validate_flag + " (undeclared)"

    return info


def add_validation_options(cae, email_def=EMAIL_DO_NOT_VALIDATE, phone_def=PHONE_DO_NOT_VALIDATE,
                           addr_def=ADDR_DO_NOT_VALIDATE):
    cae.add_option('filterSfClients', "Additional WHERE filter clause for Salesforce SOQL client fetch query", "", 'W')
    cae.add_option('filterSfRecTypes', "Salesforce client record type(s) to be processed",
                   [CONTACT_REC_TYPE_RENTALS], 'R')

    cae.add_option('emailsToValidate', "Emails to be validated", email_def, 'E',
                   choices=(EMAIL_DO_NOT_VALIDATE, EMAIL_NOT_VALIDATED, EMAIL_INVALIDATED, EMAIL_INVALID, EMAIL_VALID,
                            EMAIL_ALL))
    cae.add_option('phonesToValidate', "Phones to be validated", phone_def, 'P',
                   choices=(PHONE_DO_NOT_VALIDATE, PHONE_NOT_VALIDATED, PHONE_INVALIDATED, PHONE_INVALID, PHONE_VALID,
                            PHONE_ALL))
    cae.add_option('addressesToValidate', "Post addresses to be validated", addr_def, 'A',
                   choices=(ADDR_DO_NOT_VALIDATE, ADDR_NOT_VALIDATED, ADDR_INVALIDATED, ADDR_INVALID, ADDR_VALID,
                            ADDR_ALL))


def init_validation(cae):
    uprint("####  Initializing validation options and configuration settings")
    prefix = "      "
    email_validator = phone_validator = addr_validator = None

    email_validation = cae.get_option('emailsToValidate')
    if email_validation != EMAIL_DO_NOT_VALIDATE:
        uprint(prefix + "Email validation:", validate_flag_info(email_validation))
        api_key = cae.get_config('emailValidatorApiKey')
        if not api_key:
            uprint("****  SfContactValidator email validation configuration error: api key is missing")
            cae.shutdown(12003)
        args = dict()
        pause_seconds = cae.get_config('emailValidatorPauseSeconds')
        if pause_seconds:
            args['pause_seconds'] = pause_seconds
        max_retries = cae.get_config('emailValidatorMaxRetries')
        if max_retries:
            args['max_retries'] = max_retries
        email_validator = EmailValidator(cae.get_config('emailValidatorBaseUrl'), api_key, **args)

    phone_validation = cae.get_option('phonesToValidate')
    if phone_validation != PHONE_DO_NOT_VALIDATE:
        uprint(prefix + "Phone validation:", validate_flag_info(phone_validation))
        api_key = cae.get_config('phoneValidatorApiKey')
        if not api_key:
            uprint("****  SfContactValidator phone validation configuration error: api key is missing")
            cae.shutdown(12006)
        args = dict()
        pause_seconds = cae.get_config('phoneValidatorPauseSeconds')
        if pause_seconds:
            args['pause_seconds'] = pause_seconds
        max_retries = cae.get_config('phoneValidatorMaxRetries')
        if max_retries:
            args['max_retries'] = max_retries
        alternative_country = cae.get_config('phoneValidatorAlternativeCountry')
        if alternative_country:
            args['alternative_country'] = alternative_country
        phone_validator = PhoneValidator(cae.get_config('phoneValidatorBaseUrl'), api_key, **args)

    addr_validation = cae.get_option('addressesToValidate')
    if addr_validation != ADDR_DO_NOT_VALIDATE:
        uprint(prefix + "Address validation:", validate_flag_info(addr_validation))
        api_key = cae.get_config('addressValidatorApiKey')
        if not api_key:
            uprint("****  SfContactValidator address validation configuration error: api key is missing")
            cae.shutdown(12009)
        args = dict()
        pause_seconds = cae.get_config('addressValidatorPauseSeconds')
        if pause_seconds:
            args['pause_seconds'] = pause_seconds
        max_retries = cae.get_config('addressValidatorMaxRetries')
        if max_retries:
            args['max_retries'] = max_retries
        search_url = cae.get_config('addressValidatorSearchUrl')
        if search_url:
            args['auto_complete_search_url'] = search_url
        fetch_url = cae.get_config('addressValidatorFetchUrl')
        if fetch_url:
            args['auto_complete_fetch_url'] = fetch_url
        addr_validator = AddressValidator(cae.get_config('addressValidatorBaseUrl'), api_key, **args)

    # determine filter options
    filter_sf_clients = cae.get_option('filterSfClients')
    if filter_sf_clients:
        uprint(prefix + "Filter clients matching SOQL where clause:", filter_sf_clients)
    filter_sf_rec_types = cae.get_option('filterSfRecTypes')
    if filter_sf_rec_types:
        uprint(prefix + "Filter clients with record types:", filter_sf_rec_types)

    # determine config settings for extra filters and other preferences
    filter_email = cae.get_config('filterEmail', default_value='')
    if filter_email:
        uprint(prefix + "Filter email addresses that are:", filter_email)
    default_email_address = cae.get_config('defaultEmailAddress', default_value='')
    if default_email_address:
        uprint(prefix + "Default email address:", default_email_address)
    invalid_email_fragments = cae.get_config('invalidEmailFragments', default_value=list())
    if invalid_email_fragments:
        uprint(prefix + "Invalid email fragments:", invalid_email_fragments)

    ignore_case_fields = cae.get_config('ignoreCaseFields', default_value=list())
    if ignore_case_fields:
        uprint(prefix + "Case ignored in Salesforce fields:", ignore_case_fields)
    changeable_fields = cae.get_config('changeableFields', default_value=list())
    if changeable_fields:
        uprint(prefix + "Salesforce fields that can be updated/changed:", changeable_fields)

    return email_validation, email_validator, phone_validation, phone_validator, addr_validation, addr_validator, \
        filter_sf_clients, filter_sf_rec_types, filter_email, \
        default_email_address, invalid_email_fragments, ignore_case_fields, changeable_fields


class EmailValidator:
    """
        Alternative and free email validation (MX-record, DNS and extended regular expression match) with free
        pip python module: https://github.com/syrusakbary/validate_email/blob/master/validate_email.py
    """
    def __init__(self, base_url, api_key, pause_seconds=18.0, max_retries=2):
        assert base_url
        self._base_url = base_url
        assert api_key
        self._api_key = api_key
        assert pause_seconds >= 0.0
        self._pause_seconds = pause_seconds
        assert max_retries > 0
        self._max_retries = max_retries
        # save costs on re-validating duplicates
        self._already_validated = dict()
        # response status codes - see also https://www.email-validator.net/email-verification-results.html
        self._retry_status = list((114, 118, 215, 313, 314,))       # retry the validation
        self._valid_status = list((200, 207, 215,))                 # valid emails

    def validate(self, email):
        """ validate email address

        :param email:           email address to validate.
        :return:                "" if valid else error message.
        """
        if email in self._already_validated:    # save validator API costs if already validated
            last_err = self._already_validated[email]
            if last_err:
                last_err += " (already validated)"
            return last_err

        err_msg = ""
        pause_seconds = self._pause_seconds
        try:
            for tries in range(1, self._max_retries + 1):
                if tries > 1 and pause_seconds:
                    time.sleep(pause_seconds)
                    pause_seconds += 3.0 * (tries ** 2.0)   # increment for next try/loop
                # POST==GET: res = requests.post(self._base_url, data=dict(EmailAddress=email, APIKey=self._api_key))
                res = requests.get(self._base_url, params=dict(EmailAddress=email, APIKey=self._api_key))
                if res.status_code != requests.codes.ok:    # ==200
                    if tries == self._max_retries:
                        err_msg = "EmailValidator.validate(): http error status code {}".format(res.status_code)
                        break
                    continue        # retry validation

                ret = json.loads(res.text)
                # doc on all status codes available at: https://www.email-validator.net/email-verification-results.html
                # .. e.g. 114=grey listing, 118=api rate limit (Daniels code documents 5 min. pause/wait in this case)
                status = ret['status']
                if tries == self._max_retries and status not in self._valid_status:
                    err_msg = "maximum retries ({}) reached. ret={}".format(tries, ret)
                    break
                if status in self._valid_status and status not in self._retry_status:
                    break           # VALID

        except requests.exceptions.RequestException as ex:
            err_msg = "EmailValidator.validate(): requests exception {} raised".format(ex)
        except Exception as ex:
            err_msg = "EmailValidator.validate(): generic exception {} raised".format(ex)

        self._already_validated[email] = err_msg

        return err_msg


class PhoneValidator:
    def __init__(self, base_url, api_key, pause_seconds=18.0, max_retries=2, alternative_country=''):
        assert base_url
        self._base_url = base_url
        assert api_key
        self._api_key = api_key
        assert pause_seconds >= 0.0
        self._pause_seconds = pause_seconds
        assert max_retries > 0
        self._max_retries = max_retries
        self._alt_country = alternative_country
        # save costs on re-validating duplicates
        self._already_validated = dict()
        # response status codes - see also https://www.phone-validator.net/phone-number-online-validation-api.html
        self._retry_status = list(('VALID_UNCONFIRMED', 'DELAYED',))            # retry the validation
        self._valid_status = list(('VALID_UNCONFIRMED', 'VALID_CONFIRMED',))    # VALID

    def validate(self, phone, country_code='', ret_val_dict=None, try_alternative_country=True):
        """ validate phone number

        Phone validator does not accept leading 00 instead of leading + character, so this method is correcting
        them accordingly.

        :param phone:           phone number to be validated (without spaces and special characters apart from + and -).
        :param country_code:    ISO2 country code (optional).
        :param ret_val_dict:    dictionary for to pass back the response values from the API including the
                                validated phone number in international format (with leading 00).
        :param try_alternative_country  if True and self._alt_country is specified on class instantiation and if
                                the validation with the passed country_code was invalid then do another validation try
                                with the country code specified in self._alt_country.
        :return:                "" if valid else error message.
        """
        if phone.startswith('00'):  # convert phone number international format from 00 to + prefix
            phone = '+' + phone[2:]

        if phone in self._already_validated:    # save phone validator API costs if phone was already validated
            last_err, last_ret = self._already_validated[phone]
            if ret_val_dict is not None and last_ret:
                ret_val_dict.update(last_ret)
            if last_err:
                last_err += " (already validated)"
            return last_err

        err_msg = ""
        ret = dict()
        pause_seconds = self._pause_seconds
        try:
            for tries in range(1, self._max_retries + 1):
                if tries > 1 and pause_seconds:
                    time.sleep(pause_seconds)
                    pause_seconds += 3.0 * (tries ** 2.0)
                res = requests.get(self._base_url, params=dict(PhoneNumber=phone, CountryCode=country_code,
                                                               APIKey=self._api_key))
                if res.status_code != requests.codes.ok:    # ==200
                    if tries == self._max_retries:
                        err_msg = "PhoneValidator.validate(): http error status code {}".format(res.status_code)
                        ret = dict()
                        break
                    continue

                ret = json.loads(res.text)
                status = ret['status']
                # status: VALID_UNCONFIRMED, INVALID, DELAYED, RATE_LIMIT_EXCEEDED, API_KEY_INVALID_OR_DEPLETED
                if tries == self._max_retries and status not in self._valid_status:
                    err_msg = "maximum retries ({}) reached. country={} ret={}".format(tries, country_code, ret)
                    if try_alternative_country and self._alt_country and self._alt_country != country_code:
                        # start 2nd validation with alternative country code (for foreigners using a local prepaid SIM)
                        err = self.validate(phone, country_code=self._alt_country, ret_val_dict=ret_val_dict)
                        if not err:
                            return ""       # RETURN to not overwrite self._already_validated cache with old validation
                        err_msg += '\t\t' + err
                    break
                if status in self._valid_status and status not in self._retry_status:
                    break           # VALID

            # phone number is VALID_UNCONFIRMED (after self._max_retries retries) or VALID_CONFIRMED
            if ret_val_dict is not None and ret:
                if 'formatinternational' in ret:
                    if ret['formatinternational'].startswith('+'):  # convert int format from + to 00 prefix
                        if ret['formatinternational'].startswith('+00'):
                            ret['formatinternational'] = ret['formatinternational'][1:]
                        else:
                            ret['formatinternational'] = '00' + ret['formatinternational'][1:]
                    ret['formatinternational'] = ret['formatinternational'].replace(' ', '')    # validator puts spaces
                # pass back other fields like line-type, location, reformatted phone number, ...
                # .. see also https://www.phone-validator.net/phone-number-online-validation-api.html
                ret_val_dict.update(ret)

        except requests.exceptions.RequestException as ex:
            err_msg = "PhoneValidator.validate(): requests exception {} raised".format(ex)
        except Exception as ex:
            err_msg = "PhoneValidator.validate(): generic exception {} raised".format(ex)

        self._already_validated[phone] = (err_msg, ret)

        return err_msg


class AddressValidator:
    def __init__(self, base_url, api_key, pause_seconds=18.0, max_retries=1,
                 auto_complete_search_url='', auto_complete_fetch_url=''):
        assert base_url
        self._base_url = base_url
        assert api_key
        self._api_key = api_key
        assert pause_seconds >= 0.0
        self._pause_seconds = pause_seconds
        assert max_retries > 0
        self._max_retries = max_retries
        # optional for to use auto_complete() method
        self._auto_complete_search_url = auto_complete_search_url
        self._auto_complete_fetch_url = auto_complete_fetch_url

    def auto_complete(self, address, country_code='', ret_val_dict=None):
        """ autocomplete/reformat post address
        :param address:         post address lines separated by comma, CrLf, CR or LF.
        :param country_code:    optional country code (in ISO2).
        :param ret_val_dict:    dictionary for to pass back the response values from the API.
        :return:                "" if valid else error message.
        """
        assert self._auto_complete_search_url and self._auto_complete_fetch_url
        address = address.replace('\r\n', ',').replace('\n', ',').replace('\r', ',')
        pause_seconds = self._pause_seconds
        try:
            result_ids = list()
            for tries in range(1, self._max_retries + 1):
                if tries > 1 and pause_seconds:
                    time.sleep(pause_seconds)
                res = requests.get(self._auto_complete_search_url, params=dict(Query=address, Country=country_code,
                                                                               APIKey=self._api_key))
                if res.status_code != requests.codes.ok:    # ==200
                    if tries == self._max_retries:
                        return "AddressValidator.auto_complete(): http search error code {}".format(res.status_code)
                    continue

                ret = json.loads(res.text)
                results = ret['results']
                if results:
                    result_ids = [_['id'] for _ in results]
                    break
                if tries == self._max_retries:
                    return "maximum retries ({}) reached. country={} ret={}".format(tries, country_code, ret)
                pause_seconds += 3.0 * (tries ** 2.0)

            for addr_id in result_ids:
                for tries in range(1, self._max_retries + 1):
                    if tries > 1 and pause_seconds:
                        time.sleep(pause_seconds)
                    res = requests.get(self._auto_complete_fetch_url, params=dict(id=addr_id, APIKey=self._api_key))
                    if res.status_code != requests.codes.ok:  # ==200
                        if tries == self._max_retries:
                            return "AddressValidator.auto_complete(): http fetch error code {}".format(res.status_code)
                        continue

                    ret = json.loads(res.text)
                    results = ret['result']
                    if results:
                        if ret_val_dict is not None:
                            # pass back fetched fields like formatted-address, country, state, city, street, ...
                            # .. see also https://www.address-validator.net/address-online-verification-api.html
                            ret_val_dict.update(results)
                        break
                    if tries == self._max_retries:
                        return "AddressValidator.auto_complete(): maximum/{} retries reached. ret={}".format(tries, ret)
                    pause_seconds += 3.0 * (tries ** 2.0)

        except requests.exceptions.RequestException as ex:
            return "AddressValidator.auto_complete(): requests exception {} raised".format(ex)
        except Exception as ex:
            return "AddressValidator.auto_complete(): generic exception {} raised".format(ex)

        return ""

    def validate(self, street, city, country_code='', postal='', state='', apt_suite='', ret_val_dict=None):
        pause_seconds = self._pause_seconds
        try:
            for tries in range(1, self._max_retries + 1):
                if tries > 1 and pause_seconds:
                    time.sleep(pause_seconds)
                res = requests.get(self._base_url, params=dict(StreetAddress=street, City=city,
                                                               CountryCode=country_code, PostalCode=postal, State=state,
                                                               AdditionalAddressInfo=apt_suite,
                                                               APIKey=self._api_key))
                if res.status_code != requests.codes.ok:    # ==200
                    if tries == self._max_retries:
                        return "AddressValidator.validate(): http error status code {}".format(res.status_code)
                    continue

                ret = json.loads(res.text)
                status = ret['status']
                if status in ('VALID',):
                    if ret_val_dict is not None:
                        # pass back other fields like formatted-address, street, city, street-number, postal-code, ...
                        # .. see also https://www.address-validator.net/address-online-verification-api.html
                        ret_val_dict.update(ret)
                    break
                # other status: SUSPECT, INVALID, DELAYED, RATE_LIMIT_EXCEEDED, API_KEY_INVALID_OR_DEPLETED, RESTRICTED,
                # .. INTERNAL_ERROR
                if tries == self._max_retries:
                    return "reached maximum retries ({}). country={} ret={}".format(tries, country_code, ret)
                pause_seconds += 3.0 * (tries ** 2.0)

        except requests.exceptions.RequestException as ex:
            return "AddressValidator.validate(): requests exception {} raised".format(ex)
        except Exception as ex:
            return "AddressValidator.validate(): generic exception {} raised".format(ex)

        return ""
