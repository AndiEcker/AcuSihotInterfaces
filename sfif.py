# salesforce high level interface
import string
import pprint
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceExpiredSession
from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE

# default client salesforce object
DEF_CLIENT_OBJ = 'Lead'

# default search field (used by SfInterface.client_field_data())
DEF_SEARCH_FIELD = 'Id'

# flag to determine client object from SF ID
DETERMINE_CLIENT_OBJ = '#Unknown#'

# special client record type ids
CLIENT_REC_TYPE_ID_OWNERS = '012w0000000MSyZAAW'  # 15 digit ID == 012w0000000MSyZ

# external reference type=id separator and types (also used as Sihot Matchcode/GDS prefix)
EXT_REF_TYPE_ID_SEP = '='
EXT_REF_TYPE_RCI = 'RCI'
EXT_REF_TYPE_RCIP = 'RCIP'


# console app debug level (initialized by prepare_connection())
_debug_level = DEBUG_LEVEL_VERBOSE

# sf address field type/length - copied from https://developer.salesforce.com/forums/?id=906F00000008ih6IAA
"""
    Address.Street      (TextArea, 255)
    Address.City        (String,    40)
    Address.State       (String,    80)
    Address.PostalCode  (String,    20)
    Address.Country     (String,    80)
"""
# salesforce object field name re-mappings
FIELD_NAMES = dict(RecordType=dict(Lead='RecordType.DeveloperName', Contact='RecordType.DeveloperName',
                                   Account='RecordType.DeveloperName'),
                   Email=dict(Account='PersonEmail'),
                   Phone=dict(),
                   FirstName=dict(),
                   LastName=dict(),
                   Name=dict(),
                   Birthdate=dict(Lead='DOB1__c', Contact='DOB1__c', Account='KM_DOB__pc'),
                   Street=dict(Contact='MailingStreet', Account='PersonMailingStreet'),
                   City=dict(Contact='MailingCity', Account='PersonMailingCity'),
                   State=dict(Account='PersonMailingState'),
                   Postal=dict(Account='PersonMailingPostalCode'),
                   Country=dict(Contact='Country__c', Account='PersonMailingCountry'),
                   Language=dict(Lead='Nationality__c', Contact='Language__c', Account='Language__pc'),
                   MarketSource=dict(Lead='Market_Source__c', Contact='Marketing_Source__c',
                                     Account='Marketing_Source__pc'),
                   ArrivalInfo=dict(Lead='Previous_Arrivals__c', Contact='Previous_Arrival_Info__c',
                                    Account='Previous_Arrival_Info__pc'),
                   AssId=dict(Lead='AssCache_Id__c', Contact='AssCache_Id__c', Account='AssCache_Id__c'),
                   AcId=dict(Lead='Acumen_Client_Reference__c', Contact='CD_CODE__c', Account='CD_CODE__pc'),
                   SfId=dict(Lead='Id', Contact='Id', Account='Id'),
                   ShId=dict(Lead='Sihot_Guest_Object_Id__c', Contact='Sihot_Guest_Object_Id__c',
                             Account='Sihot_Guest_Object_Id__c'),
                   RciId=dict(Contact='RCI_Reference__c', Account='RCI_Reference__pc'),
                   )

# used salesforce record types for newly created Lead/Contact/Account objects
RECORD_TYPES = dict(Lead='SIHOT_Leads', Contact='Rentals', Account='PersonAccount')

# SF ID prefixes for to determine SF object
ID_PREFIX_OBJECTS = {'001': 'Account', '003': 'Contact', '00Q': 'Lead'}


def obj_from_id(sf_id):
    return ID_PREFIX_OBJECTS.get(sf_id[:3], DEF_CLIENT_OBJ)


def ensure_long_id(sf_id):
    """
    ensure that the passed sf_id will be returned as a 18 character Salesforce ID (if passed in as 15 character SF ID).

    :param sf_id:   any valid (15 or 18 character long) SF ID.
    :return:        18 character SF ID if passed in as 15 or 18 character ID - any other SF ID length returns None.
    """
    if len(sf_id) == 18:
        return sf_id
    elif len(sf_id) != 15:
        return None

    char_map = string.ascii_uppercase + "012345"
    extend = ""
    for chunk in range(3):
        bin_str = ""
        for pos in range(5):
            bin_str = ("1" if sf_id[chunk * 5 + pos] in string.ascii_uppercase else "0") + bin_str
        extend += char_map[int(bin_str, 2)]

    return sf_id + extend


def sf_name(code_field_name, sf_obj):
    sf_field_name = code_field_name
    field_map = FIELD_NAMES.get(code_field_name)
    if field_map:
        sf_field_name = field_map.get(sf_obj, code_field_name)
    return sf_field_name


def field_list_to_sf(code_list, sf_obj):
    sf_list = list()
    for code_field_name in code_list:
        sf_list.append(sf_name(code_field_name, sf_obj))
    return sf_list


def field_dict_to_sf(code_dict, sf_obj):
    sf_dict = dict()
    for code_field_name, val in code_dict.items():
        sf_key = sf_name(code_field_name, sf_obj)
        sf_dict[sf_key] = val
    return sf_dict


def code_name(sf_field_name, sf_obj):
    for code_field_name, field_map in FIELD_NAMES.items():
        if field_map.get(sf_obj) == sf_field_name:
            break
    else:
        code_field_name = sf_field_name
    return code_field_name


def field_list_from_sf(sf_list, sf_obj):
    code_list = list()
    for sf_field_name in sf_list:
        code_list.append(code_name(sf_field_name, sf_obj))
    return code_list


def field_dict_from_sf(sf_dict, sf_obj):
    code_dict = dict()
    for sf_field_name, val in sf_dict.items():
        if sf_field_name != 'attributes':
            code_dict[code_name(sf_field_name, sf_obj)] = val
    return code_dict


def add_sf_options(cae):
    cae.add_option('sfUser', "Salesforce account user name", '', 'y')
    cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
    cae.add_option('sfToken', "Salesforce account token string", '', 'o')
    cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
    cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')


def prepare_connection(cae):
    global _debug_level
    _debug_level = cae.get_option('debugLevel')

    sf_user = cae.get_option('sfUser', default_value=cae.get_config('sfUser'))
    if not sf_user:         # check if app is specifying Salesforce credentials, e.g. SihotResSync/SihotResImport do not
        uprint("sfif.prepare_connection(): skipped because of unspecified credentials")
        return None, None
    sf_pw = cae.get_option('sfPassword', default_value=cae.get_config('sfPassword'))
    sf_token = cae.get_option('sfToken', default_value=cae.get_config('sfToken'))
    sf_sandbox = cae.get_option('sfIsSandbox',
                                default_value=cae.get_config('sfIsSandbox',
                                                             default_value='test' in sf_user.lower()
                                                                           or 'sandbox' in sf_user.lower()))
    sf_client = cae.get_option('sfClientId', default_value=cae.get_config('sfClientId'))

    uprint("Salesforce " + ("sandbox" if sf_sandbox else "production") + " user/client-id:", sf_user, sf_client)

    sf_conn = SfInterface(sf_user, sf_pw, sf_token, sf_sandbox, sf_client)

    return sf_conn, sf_sandbox


def correct_email(email, changed=False, removed=None):
    """ check and correct email address from a user input (removing all comments)

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
        return None, False

    if removed is None:
        removed = list()

    in_local_part = True
    in_quoted_part = False
    in_comment = False
    local_part = ""
    domain_part = ""
    domain_beg_idx = -1
    domain_end_idx = len(email) - 1
    comment = ''
    last_ch = ''
    ch_before_comment = ''
    for idx, ch in enumerate(email):
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
            domain_part += ch
        last_ch = ch

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
        return None, False

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


class SfInterface:
    def __init__(self, username, password, token, sandbox, client_id='SignalliaSfInterface'):
        # store user credentials for lazy Salesforce connect (only if needed) because of connection limits and timeouts
        self._conn = None
        self._user = username
        self._pw = password
        self._tok = token
        self._sb = sandbox
        self._client = client_id

        self.error_msg = ""

    def _connect(self):
        try:
            self._conn = Salesforce(username=self._user, password=self._pw, security_token=self._tok,
                                    sandbox=self._sb, client_id=self._client)
        except SalesforceAuthenticationFailed as sf_ex:
            self.error_msg = "SfInterface.__init__(): Salesforce {} authentication failed with exception: {}" \
                .format('Sandbox' if self._sb else 'Production', sf_ex)

    def _ensure_lazy_connect(self):
        if 'INVALID_LOGIN' in self.error_msg:
            uprint(" ***  Invalid Salesforce login occurred - preventing lock of user account {}; last error={}"
                   .format(self._user, self.error_msg))
            return False
        self.error_msg = ""
        if not self._conn:
            self._connect()
            if self.error_msg:
                return False
        return True

    def soql_query_all(self, soql_query):
        if not self._ensure_lazy_connect():
            return None
        response = None
        try:
            response = self._conn.query_all(soql_query)
        except SalesforceExpiredSession:
            uprint("  **  Trying to re-connect expired Salesforce session...")
            self._conn = None
            if self._ensure_lazy_connect():
                try:
                    response = self._conn.query_all(soql_query)
                except Exception as sf_ex:
                    self.error_msg = "SfInterface.soql_query_all({}) reconnect exception: {}".format(soql_query, sf_ex)
        except Exception as sf_ex:
            self.error_msg = "SfInterface.soql_query_all({}) query exception: {}".format(soql_query, sf_ex)
        if response and not response['done']:
            self.error_msg = "SfInterface.soql_query_all(): Salesforce is responding that query {} is NOT done." \
                .format(soql_query)
        return response

    def sf_obj(self, sf_obj):
        client_obj = getattr(self._conn, sf_obj)
        if not client_obj:
            self.error_msg = "SfInterface.sf_obj({}) called with invalid salesforce object type".format(sf_obj)
        return client_obj

    def client_upsert(self, fields_dict, sf_obj=DETERMINE_CLIENT_OBJ):
        if not self._ensure_lazy_connect():
            return None, self.error_msg, ""

        # check if Id passed in (then this method can determine the sf_obj and will do an update not an insert)
        sf_id, update_client = (fields_dict.pop('Id'), True) if 'Id' in fields_dict else ('', False)

        if sf_obj == DETERMINE_CLIENT_OBJ:
            if not sf_id:
                self.error_msg = "SfInterface.client_upsert({}, {}): client object cannot be determined without Id"\
                    .format(fields_dict, sf_obj)
                return None, self.error_msg, ""
            sf_obj = obj_from_id(sf_id)

        client_obj = self.sf_obj(sf_obj)
        if not client_obj:
            self.error_msg += "+SfInterface.client_upsert({}, {}): empty client object".format(fields_dict, sf_obj)
            return None, self.error_msg, ""

        sf_dict = field_dict_to_sf(fields_dict, sf_obj)
        err = msg = ""
        if update_client:
            try:
                sf_ret = client_obj.update(sf_id, sf_dict)
                msg = "{} {} updated with {}, ret={}".format(sf_obj, sf_id, pprint.pformat(sf_dict, indent=9), sf_ret)
            except Exception as ex:
                err = "{} update() raised exception {}. sent={}".format(sf_obj, ex, pprint.pformat(sf_dict, indent=9))
        else:
            try:
                sf_ret = client_obj.create(sf_dict)
                msg = "{} created with {}, ret={}".format(sf_obj, pprint.pformat(sf_dict, indent=9), sf_ret)
                if sf_ret['success']:
                    sf_id = sf_ret['Id']    # ?!?!? was lower-case 'id' (changed 19-04-18)
            except Exception as ex:
                err = "{} create() exception {}. sent={}".format(sf_obj, ex, pprint.pformat(sf_dict, indent=9))

        if err:
            self.error_msg = err

        if sf_id and 'RciId' in fields_dict:
            ext_ref_id, err, msg = self.ext_ref_upsert(sf_id, fields_dict['RciId'], sf_obj=sf_obj)

        return sf_id, err, msg

    def client_delete(self, sf_id, sf_obj=DETERMINE_CLIENT_OBJ):
        if not self._ensure_lazy_connect():
            return self.error_msg, ""

        if sf_obj == DETERMINE_CLIENT_OBJ:
            sf_obj = obj_from_id(sf_id)

        client_obj = self.sf_obj(sf_obj)
        if not client_obj:
            self.error_msg += " client_delete() id={}".format(sf_id)
            return self.error_msg, ""

        msg = ""
        try:
            sf_ret = client_obj.delete(sf_id)
            msg = "{} {} deleted, status={}".format(sf_obj, sf_id, pprint.pformat(sf_ret, indent=9))
        except Exception as ex:
            self.error_msg = "{} {} deletion raised exception {}".format(sf_obj, sf_id, ex)

        return self.error_msg, msg

    def clients_with_rci_id(self, ext_refs_sep, sf_obj=DEF_CLIENT_OBJ):
        code_fields = ['Id', 'AcId', 'RciId', 'ShId', 'RecordType.Id',
                       "(SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"]
        sf_fields = field_list_to_sf(code_fields, sf_obj)
        res = self.soql_query_all("SELECT {} FROM {}".format(", ".join(sf_fields), sf_obj))
        client_tuples = list()
        if not self.error_msg and res['totalSize'] > 0:
            for c in res['records']:  # list of client OrderedDicts
                ext_refs = [c[sf_name('RciId', sf_obj)]] if c[sf_name('RciId', sf_obj)] else list()
                if c['External_References__r']:
                    ext_refs.extend([_['Reference_No_or_ID__c'] for _ in c['External_References__r']['records']])
                if ext_refs:
                    client_tuples.append((None, c[sf_name('AcId', sf_obj)], c['Id'], c[sf_name('ShId', sf_obj)],
                                          ext_refs_sep.join(ext_refs),
                                          1 if c['RecordType']['Id'] == CLIENT_REC_TYPE_ID_OWNERS else 0))
        return client_tuples

    REF_TYPE_ALL = 'all'
    REF_TYPE_MAIN = 'main'
    REF_TYPE_EXT = 'external'

    def client_by_rci_id(self, rci_ref, sf_id=None, dup_clients=None, which_ref=REF_TYPE_ALL, sf_obj=DEF_CLIENT_OBJ):
        if not dup_clients:
            dup_clients = list()
        if which_ref in (self.REF_TYPE_MAIN, self.REF_TYPE_ALL):
            soql_query = "SELECT Id FROM {} WHERE {} = '{}'".format(sf_obj, sf_name('RciId', sf_obj), rci_ref)
            fld_name = 'Id'
        else:   # which_ref == REF_TYPE_EXT
            fld_name = '{}__c'.format(sf_obj)
            soql_query = "SELECT {} FROM External_Ref__c WHERE Reference_No_or_ID__c = '{}'".format(fld_name, rci_ref)
        res = self.soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            if not sf_id:
                sf_id = res['records'][0][fld_name]
            if res['totalSize'] > 1:
                new_clients = [_[fld_name] for _ in res['records']]
                dup_clients = list(set([_ for _ in new_clients + dup_clients if _ != sf_id]))

        if which_ref == self.REF_TYPE_ALL:
            sf_id, dup_clients = self.client_by_rci_id(rci_ref, sf_id, dup_clients, self.REF_TYPE_EXT)
        return sf_id, dup_clients

    def client_field_data(self, fetch_fields, search_value, search_field=DEF_SEARCH_FIELD, sf_obj=DETERMINE_CLIENT_OBJ,
                          log_warnings=None):
        """
        fetch field data from SF object (identified by sf_obj) and client (identified by search_value/search_field).
        :param fetch_fields:    either pass single field name (str) or list of field names of value(s) to be returned.
        :param search_value:    value for to identify client record.
        :param search_field:    field name used for to identify client record (def='Id'/DEF_SEARCH_FIELD).
        :param sf_obj:          SF object to be searched (def=determined by the passed ID prefix).
        :param log_warnings:    pass list for to append warning log entries on re-search on old/redirected SF IDs.
        :return:                either single field value (if fetch_fields is str) or dict(fld=val) of field values.
        """
        if sf_obj == DETERMINE_CLIENT_OBJ:
            if search_field not in (DEF_SEARCH_FIELD, 'External_Id__c', 'Contact_Ref__c', 'Id_before_convert__c'):
                uprint("SfInterface.client_field_data({}, {}, {}, {}): client object cannot be determined without Id"
                       .format(fetch_fields, search_value, search_field, sf_obj))
                return None
            sf_obj = obj_from_id(search_value)
            if not sf_obj:
                uprint("SfInterface.client_field_data(): {} field value {} is not a valid Lead/Contact/Account SF ID"
                       .format(search_field, search_value))
                return None

        ret_dict = isinstance(fetch_fields, list)
        if ret_dict:
            select_fields = ", ".join(field_list_to_sf(fetch_fields, sf_obj))
            fetch_field = None      # only needed for to remove PyCharm warning
            ret_val = dict()
        else:
            select_fields = fetch_field = sf_name(fetch_fields, sf_obj)
            ret_val = None
        soql_query = "SELECT {} FROM {} WHERE {} = '{}'"\
            .format(select_fields, sf_obj, sf_name(search_field, sf_obj), search_value)
        res = self.soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            ret_val = res['records'][0]
            if ret_dict:
                ret_val = field_dict_from_sf(ret_val, sf_obj)
            else:
                ret_val = ret_val[fetch_field]

        # if not found as object ID then re-search recursively old/redirected SF IDs in other indexed/external SF fields
        if not ret_val and search_field == DEF_SEARCH_FIELD:
            if log_warnings is None:
                log_warnings = list()
            log_warnings.append("{} ID {} not found as direct/main ID in {}s".format(sf_obj, search_value, sf_obj))
            if sf_obj == 'Lead':
                # try to find this Lead Id in the Lead field External_Id__c
                ret_val = self.client_field_data(fetch_fields, search_value, search_field='External_Id__c')
                if not ret_val:
                    log_warnings.append("{} ID {} not found in Lead fields External_Id__c".format(sf_obj, search_value))
            elif sf_obj == 'Contact':
                # try to find this Contact Id in the Contact fields Contact_Ref__c, Id_before_convert__c
                ret_val = self.client_field_data(fetch_fields, search_value, search_field='Contact_Ref__c')
                if not ret_val:
                    ret_val = self.client_field_data(fetch_fields, search_value, search_field='Id_before_convert__c')
                    if not ret_val:
                        log_warnings.append("{} ID {} not found in Contact fields Contact_Ref__c/Id_before_convert__c"
                                            .format(sf_obj, search_value))

        return ret_val

    def client_ass_id(self, sf_client_id, sf_obj=DETERMINE_CLIENT_OBJ):
        return self.client_field_data('AssId', sf_client_id, sf_obj=sf_obj)

    def client_ac_id(self, sf_client_id, sf_obj=DETERMINE_CLIENT_OBJ):
        return self.client_field_data('AcId', sf_client_id, sf_obj=sf_obj)

    def client_sh_id(self, sf_client_id, sf_obj=DETERMINE_CLIENT_OBJ):
        return self.client_field_data('ShId', sf_client_id, sf_obj=sf_obj)

    def client_id_by_email(self, email, sf_obj=DEF_CLIENT_OBJ):
        return self.client_field_data('Id', email, search_field='Email', sf_obj=sf_obj)

    def client_ext_refs(self, sf_client_id, er_id=None, er_type=EXT_REF_TYPE_RCI, sf_obj=DETERMINE_CLIENT_OBJ):
        """
        Return external references of client specified by sf_client_id (and optionally sf_obj).

        :param sf_client_id:    Salesforce Id of client record (Lead, Contact, Account, PersonAccount, ...).
        :param er_id:           External reference (No or Id).
        :param er_type:         Type of external reference (e.g. EXT_REF_TYPE_RCI).
        :param sf_obj:          Salesforce object of the client passed into sf_client_id (Lead, Contact, Account, ...).
        :return:                If er_id get passed in then: list of tuples of found external ref type and id of client.
                                Else: list of Salesforce Ids of external references (mostly only one).
        """
        if sf_obj == DETERMINE_CLIENT_OBJ:
            sf_obj = obj_from_id(sf_client_id)

        ext_refs = list()
        soql = "SELECT Id, Name, Reference_No_or_ID__c FROM External_References__r  WHERE {}__c = '{}'"\
            .format(sf_obj, sf_client_id)
        if er_id:
            soql += " AND Reference_No_or_ID__c = '{}' AND Name = '{}'".format(er_id, er_type)
        res = self.soql_query_all(soql)
        if not self.error_msg and res['totalSize'] > 0:
            for c in res['records']:  # list of External_References__r OrderedDicts
                ext_refs.append(c['Id'] if er_id else (c['Name'], c['Reference_No_or_ID__c']))
        return ext_refs

    def ext_ref_upsert(self, sf_client_id, er_id, er_type=EXT_REF_TYPE_RCI, sf_obj=DETERMINE_CLIENT_OBJ):
        if not self._ensure_lazy_connect():
            return None, self.error_msg, ""

        er_obj = 'External_References'
        ext_ref_obj = self.sf_obj(er_obj)
        if not ext_ref_obj:
            self.error_msg += " ext_ref_upsert() sf_id={}, er_id={}".format(sf_client_id, er_id)
            return None, self.error_msg, ""

        if sf_obj == DETERMINE_CLIENT_OBJ:
            sf_obj = obj_from_id(sf_client_id)
        sf_dict = dict(Reference_No_or_ID__c=er_id, Name=er_type)
        sf_dict[sf_obj + '__c'] = sf_client_id
        sf_er_id = err = msg = ""
        er_list = self.client_ext_refs(sf_client_id, er_id, er_type, sf_obj=sf_obj)
        if er_list:     # update?
            if _debug_level >= DEBUG_LEVEL_VERBOSE and len(er_list) > 1:
                uprint(" ###  ext_ref_upsert(): {} duplicate external refs found: {}".format(sf_client_id, er_list))
            sf_er_id = er_list[0]
            try:
                sf_ret = ext_ref_obj.update(sf_er_id, sf_dict)
                msg = "{} {} updated with {} ret={}".format(er_obj, sf_er_id, pprint.pformat(sf_dict, indent=9), sf_ret)
            except Exception as ex:
                err = "{} update() raised exception {}. sent={}".format(er_obj, ex, pprint.pformat(sf_dict, indent=9))
        else:
            try:
                sf_ret = ext_ref_obj.create(sf_dict)
                msg = "{} created with {}, ret={}".format(er_obj, pprint.pformat(sf_dict, indent=9), sf_ret)
                if sf_ret['success']:
                    sf_er_id = sf_ret['Id']
            except Exception as ex:
                err = "{} create() exception {}. sent={}".format(er_obj, ex, pprint.pformat(sf_dict, indent=9))

        if err:
            self.error_msg = err

        return sf_er_id, err, msg

    def find_client(self, email="", phone="", first_name="", last_name=""):
        if not self._ensure_lazy_connect():
            return None, None

        changed = False
        removed = list()
        email, changed = correct_email(email, changed=changed, removed=removed)
        if changed and _debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("SfInterface.find_client(): email address changed to {}. Removed chars: {}".format(email, removed))

        changed = False
        removed = list()
        phone, changed = correct_phone(phone, changed=changed, removed=removed)
        if changed and _debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("SfInterface.find_client(): phone number corrected to {}. Removed chars: {}".format(phone, removed))

        service_args = dict(email=email, phone=phone, firstName=first_name, lastName=last_name)
        result = self._conn.apexecute('clientsearch', method='POST', data=service_args)

        if 'id' not in result or 'type' not in result:
            return '', DEF_CLIENT_OBJ

        return result['id'], result['type']

    def record_type_id(self, sf_obj):
        rec_type_id = None
        res = self.soql_query_all("Select Id From RecordType Where SobjectType = '{}' and DeveloperName = '{}'"
                                  .format(sf_obj, RECORD_TYPES.get(sf_obj)))
        if not self.error_msg and res['totalSize'] > 0:
            rec_type_id = res['records'][0]['Id']
        return rec_type_id
