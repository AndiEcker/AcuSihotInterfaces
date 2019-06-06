"""
    helper methods for to validate data values.

    providing/encapsulating services for to validate and correct email addresses, telephone numbers and int. addresses
"""
import json
import time

import requests

from ae.console_app import uprint


def correct_email(email, changed=False, removed=None):
    """ check and correct email address from a user input (removing all comments)

    Special conversions that are not returned as changed/corrected are: the domain part of an email will be corrected
    to lowercase characters, additionally emails with all letters in uppercase will be converted into lowercase.

    Regular expressions are not working for all edge cases (see the answer to this SO question:
    https://stackoverflow.com/questions/201323/using-a-regular-expression-to-validate-an-email-address) because RFC822
    is very complex (even the reg expression recommended by RFC 5322 is not complete; there is also a
    more readable form given in the informational RFC 3696). Additionally a regular expression
    does not allow corrections. Therefore this function is using a procedural approach (using recommendations from
    RFC 822 and https://en.wikipedia.org/wiki/Email_address).

    :param email:       email address
    :param changed:     (optional) flag if email address got changed (before calling this function) - will be returned
                        unchanged if email did not get corrected.
    :param removed:     (optional) list declared by caller for to pass back all the removed characters including
                        the index in the format "<index>:<removed_character(s)>".
    :return:            tuple of (possibly corrected email address, flag if email got changed/corrected)
    """
    if email is None:
        return "", False

    if removed is None:
        removed = list()

    in_local_part = True
    in_quoted_part = False
    in_comment = False
    all_upper_case = True
    local_part = ""
    domain_part = ""
    domain_beg_idx = -1
    domain_end_idx = len(email) - 1
    comment = ''
    last_ch = ''
    ch_before_comment = ''
    for idx, ch in enumerate(email):
        if ch.islower():
            all_upper_case = False
        next_ch = email[idx + 1] if idx + 1 < domain_end_idx else ''
        if in_comment:
            comment += ch
            if ch == ')':
                in_comment = False
                removed.append(comment)
                last_ch = ch_before_comment
            continue
        elif ch == '(' and not in_quoted_part \
                and (idx == 0 or email[idx:].find(')@') >= 0 if in_local_part
                     else idx == domain_beg_idx or email[idx:].find(')') == domain_end_idx - idx):
            comment = str(idx) + ':('
            ch_before_comment = last_ch
            in_comment = True
            changed = True
            continue
        elif ch == '"' \
                and (not in_local_part
                     or last_ch != '.' and idx and not in_quoted_part
                     or next_ch not in ('.', '@') and last_ch != '\\' and in_quoted_part):
            removed.append(str(idx) + ':' + ch)
            changed = True
            continue
        elif ch == '@' and in_local_part and not in_quoted_part:
            in_local_part = False
            domain_beg_idx = idx + 1
        elif ch.isalnum():
            pass    # uppercase and lowercase Latin letters A to Z and a to z
        elif ord(ch) > 127 and in_local_part:
            pass    # international characters above U+007F
        elif ch == '.' and in_local_part and not in_quoted_part and last_ch != '.' and idx and next_ch != '@':
            pass    # if not the first or last unless quoted, and does not appear consecutively unless quoted
        elif ch in ('-', '.') and not in_local_part and (last_ch != '.' or ch == '-') \
                and idx not in (domain_beg_idx, domain_end_idx):
            pass    # if not duplicated dot and not the first or last character in domain part
        elif (ch in ' (),:;<>@[]' or ch in '\\"' and last_ch == '\\' or ch == '\\' and next_ch == '\\') \
                and in_quoted_part:
            pass    # in quoted part and in addition, a backslash or double-quote must be preceded by a backslash
        elif ch == '"' and in_local_part:
            in_quoted_part = not in_quoted_part
        elif (ch in "!#$%&'*+-/=?^_`{|}~" or ch == '.'
              and (last_ch and last_ch != '.' and next_ch != '@' or in_quoted_part)) \
                and in_local_part:
            pass    # special characters (in local part only and not at beg/end and no dup dot outside of quoted part)
        else:
            removed.append(str(idx) + ':' + ch)
            changed = True
            continue

        if in_local_part:
            local_part += ch
        else:
            domain_part += ch.lower()
        last_ch = ch

    if all_upper_case:
        local_part = local_part.lower()

    return local_part + domain_part, changed


def correct_phone(phone, changed=False, removed=None, keep_1st_hyphen=False):
    """ check and correct phone number from a user input (removing all invalid characters including spaces)

    :param phone:           phone number
    :param changed:         (optional) flag if phone got changed (before calling this function) - will be returned
                            unchanged if phone did not get corrected.
    :param removed:         (optional) list declared by caller for to pass back all the removed characters including
                            the index in the format "<index>:<removed_character(s)>".
    :param keep_1st_hyphen  (optional, def=False) pass True for to keep at least the first occurring hyphen character.
    :return:                tuple of (possibly corrected phone number, flag if phone got changed/corrected)
    """

    if phone is None:
        return "", False

    if removed is None:
        removed = list()

    corr_phone = ''
    got_hyphen = False
    for idx, ch in enumerate(phone):
        if ch.isdigit():
            corr_phone += ch
        elif keep_1st_hyphen and ch == '-' and not got_hyphen:
            got_hyphen = True
            corr_phone += ch
        else:
            if ch == '+' and not corr_phone and not phone[idx + 1:].startswith('00'):
                corr_phone = '00'
            removed.append(str(idx) + ':' + ch)
            changed = True

    return corr_phone, changed


# argument values for validate_flag_info() and sfif.py/SfInterface.clients_to_validate()
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
    cae.add_option('filterSfRecTypes', "Salesforce client record type(s) to be processed", list(), 'R')

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
            uprint("****  SfClientValidator email validation configuration error: api key is missing")
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
            uprint("****  SfClientValidator phone validation configuration error: api key is missing")
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
            uprint("****  SfClientValidator address validation configuration error: api key is missing")
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


def clients_to_validate(conn, filter_sf_clients='', filter_sf_rec_types=None,
                        email_validation=EMAIL_NOT_VALIDATED, phone_validation=PHONE_DO_NOT_VALIDATE,
                        addr_validation=ADDR_DO_NOT_VALIDATE):
    """
    query from Salesforce the clients that need to be validated

    :param conn:                    Salesforce connection (SfInterface instance - see sfif.py).
    :param filter_sf_clients:       extra salesforce SOQL where clause string for to filter clients.
    :param filter_sf_rec_types:     list of sf record type dev-names to be filtered (empty list will return all).
    :param email_validation:        email validation flag (see EMAIL_*).
    :param phone_validation:        phone validation flag (see PHONE_*).
    :param addr_validation:         address validation flag (see ADDR_*).
    :return:    list of client field dictionaries for to be processed/validated.
    """
    # assert not filter_sf_rec_types or isinstance(filter_sf_rec_types, collections.Iterable)
    if addr_validation != ADDR_DO_NOT_VALIDATE:
        uprint("****  SfInterface.clients_to_validate() error: address validation search is not implemented!")
    rec_type_filter_expr = "'" + "','".join(filter_sf_rec_types) + "'"
    q = ("SELECT Id, Country__c"
         + (", Email, CD_email_valid__c" if email_validation != EMAIL_DO_NOT_VALIDATE else "")
         + (", HomePhone, CD_Htel_valid__c, MobilePhone, CD_mtel_valid__c, Work_Phone__c, CD_wtel_valid__c"
            if phone_validation != PHONE_DO_NOT_VALIDATE else "")
         + " FROM Contact WHERE"
         + (" (" + filter_sf_clients + ") and " if filter_sf_clients else "")
         + (" RecordType.DeveloperName in (" + rec_type_filter_expr + ") and " if filter_sf_rec_types else "")
         + "("
         + ("(Email != Null and CD_email_valid__c in ({email_validation}))" if email_validation else "")
         + (" or " if email_validation != EMAIL_DO_NOT_VALIDATE and phone_validation != PHONE_DO_NOT_VALIDATE
            else "")
         + ("(HomePhone != NULL and CD_Htel_valid__c in ({phone_validation}))"
            + " or (MobilePhone != NULL and CD_mtel_valid__c in ({phone_validation}))"
            + " or (Work_Phone__c != NULL and CD_wtel_valid__c in ({phone_validation}))"
            if phone_validation != PHONE_DO_NOT_VALIDATE
            else "")
         + ") ORDER BY Country__c").format(email_validation=email_validation, phone_validation=phone_validation)
    res = conn.soql_query_all(q)
    if conn.error_msg or res['totalSize'] <= 0:
        client_dicts = list()
    else:
        client_dicts = [{k: v for k, v in rec.items() if k != 'attributes'} for rec in res['records']]
        assert len(client_dicts) == res['totalSize']
    return client_dicts


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
