"""
    providing/encapsulating services for to validate email addresses, telephone numbers and int. addresses
"""
import time
import requests
import json


class EmailValidator:
    """
        Alternative and free email validation (MX-record, DNS and extended regular expression match) with free
        pip python module: https://github.com/syrusakbary/validate_email/blob/master/validate_email.py
    """
    def __init__(self, base_url, api_key, pause_seconds=9.0, max_retries=3):
        assert base_url
        self._base_url = base_url
        assert api_key
        self._api_key = api_key
        assert pause_seconds >= 0.0
        self._pause_seconds = pause_seconds
        assert max_retries > 0
        self._max_retries = max_retries

    def validate(self, email):
        pause_seconds = self._pause_seconds
        try:
            for tries in range(1, self._max_retries + 1):
                if tries > 1 and pause_seconds:
                    time.sleep(pause_seconds)
                # POST==GET: res = requests.post(self._base_url, data=dict(EmailAddress=email, APIKey=self._api_key))
                res = requests.get(self._base_url, params=dict(EmailAddress=email, APIKey=self._api_key))
                if res.status_code != requests.codes.ok:    # ==200
                    if tries == self._max_retries:
                        return "EmailValidator.validate(): http error status code {}".format(res.status_code)
                    continue

                ret = json.loads(res.text)
                # doc on all status codes available at: https://www.email-validator.net/email-verification-results.html
                # .. e.g. 114=grey listing, 118=api rate limit (Daniels code documents 5 min. pause/wait in this case)
                status = ret['status']
                if status in (200, 207, 215):
                    break
                if tries == self._max_retries:
                    return "EmailValidator.validate(): maximum/{} retries reached. ret={}".format(tries, ret)
                if status in (114, 118):
                    pause_seconds += 3.0 * (tries ** 2.0)
        except requests.exceptions.RequestException as ex:
            return "EmailValidator.validate(): requests exception {} raised".format(ex)
        except Exception as ex:
            return "EmailValidator.validate(): generic exception {} raised".format(ex)

        return ""


class PhoneValidator:
    def __init__(self, base_url, api_key, pause_seconds=9.0, max_retries=3):
        assert base_url
        self._base_url = base_url
        assert api_key
        self._api_key = api_key
        assert pause_seconds >= 0.0
        self._pause_seconds = pause_seconds
        assert max_retries > 0
        self._max_retries = max_retries

    def validate(self, phone, country_code='', ret_val_dict=None):
        pause_seconds = self._pause_seconds
        try:
            for tries in range(1, self._max_retries + 1):
                if tries > 1 and pause_seconds:
                    time.sleep(pause_seconds)
                res = requests.get(self._base_url, params=dict(PhoneNumber=phone, CountryCode=country_code,
                                                               APIKey=self._api_key))
                if res.status_code != requests.codes.ok:    # ==200
                    if tries == self._max_retries:
                        return "PhoneValidator.validate(): http error status code {}".format(res.status_code)
                    continue

                ret = json.loads(res.text)
                status = ret['status']
                # other status: VALID_UNCONFIRMED, INVALID, DELAYED, RATE_LIMIT_EXCEEDED, API_KEY_INVALID_OR_DEPLETED
                if status in ('VALID_CONFIRMED', 'VALID_UNCONFIRMED'):
                    if ret_val_dict is not None:
                        # pass back other fields like line-type, location, reformatted phone number, ...
                        # .. see also https://www.phone-validator.net/phone-number-online-validation-api.html
                        if 'formatinternational' in ret:
                            if ret['formatinternational'].startswith('+'):
                                ret['formatinternational'] = '00' + ret['formatinternational'][1:]
                            ret['formatinternational'] = ret['formatinternational'].replace(' ', '')
                        ret_val_dict.update(ret)
                    break
                if tries == self._max_retries:
                    return "PhoneValidator.validate(): maximum/{} retries reached. ret={}".format(tries, ret)
                pause_seconds += 3.0 * (tries ** 2.0)
        except requests.exceptions.RequestException as ex:
            return "PhoneValidator.validate(): requests exception {} raised".format(ex)
        except Exception as ex:
            return "PhoneValidator.validate(): generic exception {} raised".format(ex)

        return ""


class AddressValidator:
    def __init__(self, base_url, api_key, pause_seconds=9.0, max_retries=3,
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
        assert self._auto_complete_search_url and self._auto_complete_fetch_url
        address = address.replace('\n', ',').replace('\r', ',')
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
                    return "AddressValidator.validate(): maximum/{} retries reached. ret={}".format(tries, ret)
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
                        return "AddressValidator.validate(): maximum/{} retries reached. ret={}".format(tries, ret)
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
                    return "AddressValidator.validate(): maximum/{} retries reached. ret={}".format(tries, ret)
                pause_seconds += 3.0 * (tries ** 2.0)

        except requests.exceptions.RequestException as ex:
            return "AddressValidator.validate(): requests exception {} raised".format(ex)
        except Exception as ex:
            return "AddressValidator.validate(): generic exception {} raised".format(ex)

        return ""
