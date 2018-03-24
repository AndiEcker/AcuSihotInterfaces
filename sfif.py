# salesforce high level interface
import pprint
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceExpiredSession
from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE

# default client salesforce object
SF_DEF_CLIENT_OBJ = 'Lead'

# special client record type ids
CLIENT_REC_TYPE_ID_OWNERS = '012w0000000MSyZAAW'  # 15 digit ID == 012w0000000MSyZ

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
                   Birthdate=dict(Lead='DOB1__c', Account='KM_DOB__pc'),
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
                   AcId=dict(Contact='CD_CODE__c', Account='CD_CODE__pc'),
                   ShId=dict(Contact='Sihot_Guest_Object_Id__c'),
                   RciId=dict(Contact='RCI_Reference__c', Account='RCI_Reference__pc'),
                   AssId=dict(Contact='AssCache_Contact_Id__c'),
                   )

# used salesforce record types for newly created Lead/Contact/Account objects
RECORD_TYPES = dict(Lead='SIHOT_Leads', Contact='Rentals', Account='PersonAccount')


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


def correct_phone(phone, changed=False, removed=None):
    """ check and correct phone number from a user input (removing all invalid characters including spaces)

    :param phone:       phone number
    :param changed:     (optional) flag if phone got changed (before calling this function) - will be returned
                        unchanged if phone did not get corrected.
    :param removed:     (optional) list declared by caller for to pass back all the removed characters including
                        the index in the format "<index>:<removed_character(s)>".
    :return:            tuple of (possibly corrected phone number, flag if phone got changed/corrected)
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
        elif ch == '-' and not got_hyphen:
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

    def client_data_by_id(self, sf_id, field_names, sf_obj=SF_DEF_CLIENT_OBJ):
        sf_fields = field_list_to_sf(field_names, sf_obj)
        res = self.soql_query_all("SELECT {} FROM {} WHERE Id = '{}'".format(", ".join(sf_fields), sf_obj, sf_id))
        sf_dict = dict()
        if not self.error_msg and res['totalSize'] > 0:
            sf_dict = res['records'][0]
        return sf_dict

    def client_upsert(self, fields_dict, sf_obj=SF_DEF_CLIENT_OBJ):
        if not self._ensure_lazy_connect():
            return None, self.error_msg, ""

        client_obj = self.sf_obj(sf_obj)
        if not client_obj:
            self.error_msg += " client_upsert() data={}".format(fields_dict)
            return None, self.error_msg, ""

        sf_dict = field_dict_to_sf(fields_dict, sf_obj)
        sf_id = err = msg = ""
        if 'Id' in sf_dict:     # update?
            sf_id = sf_dict.pop('Id')
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
                    sf_id = sf_ret['id']
            except Exception as ex:
                err = "{} create() exception {}. sent={}".format(sf_obj, ex, pprint.pformat(sf_dict, indent=9))

        if err:
            self.error_msg = err

        return sf_id, err, msg

    def client_delete(self, sf_id, sf_obj=SF_DEF_CLIENT_OBJ):
        if not self._ensure_lazy_connect():
            return self.error_msg, ""

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

    def clients_with_rci_id(self, ext_refs_sep, sf_obj=SF_DEF_CLIENT_OBJ):
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

    def client_by_rci_id(self, rci_ref, sf_id=None, dup_clients=None, which_ref=REF_TYPE_ALL, sf_obj=SF_DEF_CLIENT_OBJ):
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

    def client_id_by_email(self, email, sf_obj=SF_DEF_CLIENT_OBJ):
        soql_query = "SELECT Id FROM {} WHERE {} = '{}'".format(sf_obj, sf_name('Email', sf_obj), email)
        res = self.soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            return res['records'][0]['Id']
        return None

    def client_ass_id(self, sf_client_id, sf_obj=SF_DEF_CLIENT_OBJ):
        ass_id = None
        fld_name = sf_name('AssId', sf_obj)
        soql_query = "SELECT {} FROM {} WHERE Id = '{}'".format(fld_name, sf_obj, sf_client_id)
        res = self.soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            ass_id = res['records'][0][fld_name]
        return ass_id

    def client_ac_id(self, sf_client_id, sf_obj=SF_DEF_CLIENT_OBJ):
        ac_id = None
        fld_name = sf_name('AcId', sf_obj)
        soql_query = "SELECT {} FROM {} WHERE Id = '{}'".format(fld_name, sf_obj, sf_client_id)
        res = self.soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            ac_id = res['records'][0][fld_name]
        return ac_id

    def client_sh_id(self, sf_client_id, sf_obj=SF_DEF_CLIENT_OBJ):
        sh_id = None
        fld_name = sf_name('ShId', sf_obj)
        soql_query = "SELECT {} FROM {} WHERE Id = '{}'".format(fld_name, sf_obj, sf_client_id)
        res = self.soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            sh_id = res['records'][0][fld_name]
        return sh_id

    def client_ext_refs(self, sf_client_id, sf_obj=SF_DEF_CLIENT_OBJ):
        ext_refs = list()
        res = self.soql_query_all("SELECT Name, Reference_No_or_ID__c FROM External_References__r"
                                  " WHERE {}__c = '{}'".format(sf_obj, sf_client_id))
        if not self.error_msg and res['totalSize'] > 0:
            for c in res['records']:  # list of External_References__r OrderedDicts
                ext_refs.append((c['Name'], c['Reference_No_or_ID__c']))
        return ext_refs

    def record_type_id(self, sf_obj=SF_DEF_CLIENT_OBJ):
        rec_type_id = None
        res = self.soql_query_all("Select Id From RecordType Where SobjectType = '{}' and DeveloperName = '{}'"
                                  .format(sf_obj, RECORD_TYPES.get(sf_obj)))
        if not self.error_msg and res['totalSize'] > 0:
            rec_type_id = res['records'][0]['Id']
        return rec_type_id

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
            return '', SF_DEF_CLIENT_OBJ

        return result['id'], result['type']
