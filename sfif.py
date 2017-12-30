# salesforce high level interface
from copy import deepcopy
import pprint
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceExpiredSession
from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE

# argument values for validate_flag_info() and SfInterface.contacts_to_validate()
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

# contact record types and ids
CONTACT_REC_TYPE_ID_OWNERS = '012w0000000MSyZAAW'  # 15 digit ID == 012w0000000MSyZ
CONTACT_REC_TYPE_RENTALS = 'Rentals'

# console app debug level (initialized with prepare_connection
_debug_level = DEBUG_LEVEL_VERBOSE


def prepare_connection(cae, print_on_console=True):
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
    sf_conn = SfInterface(sf_user, sf_pw, sf_token, sf_sandbox, sf_client)
    if print_on_console or _debug_level >= DEBUG_LEVEL_VERBOSE:
        uprint("Salesforce " + ("sandbox" if sf_sandbox else "production") + " user/client-id:", sf_user, sf_client)

    return sf_conn, sf_sandbox


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

    def _soql_query_all(self, soql_query):
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
                    self.error_msg = "SfInterface._soql_query_all({}) reconnect exception: {}".format(soql_query, sf_ex)
        except Exception as sf_ex:
            self.error_msg = "SfInterface._soql_query_all({}) query exception: {}".format(soql_query, sf_ex)
        if response and not response['done']:
            self.error_msg = "SfInterface._soql_query_all(): Salesforce is responding that query {} is NOT done." \
                .format(soql_query)
        return response

    def sf_types(self):
        if self._ensure_lazy_connect():
            return self._conn
        return None

    def contacts_with_rci_id(self, ext_refs_sep):
        contact_tuples = list()
        res = self._soql_query_all("SELECT Id, CD_CODE__c, RCI_Reference__c, Sihot_Guest_Object_Id__c, RecordType.Id,"
                                   " (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"
                                   " FROM Contact")
        if not self.error_msg and res['totalSize'] > 0:
            for c in res['records']:  # list of Contact OrderedDicts
                ext_refs = [c['RCI_Reference__c']] if c['RCI_Reference__c'] else list()
                if c['External_References__r']:
                    ext_refs.extend([_['Reference_No_or_ID__c'] for _ in c['External_References__r']['records']])
                if ext_refs:
                    contact_tuples.append((c['CD_CODE__c'], c['Id'], c['Sihot_Guest_Object_Id__c'],
                                          ext_refs_sep.join(ext_refs),
                                          1 if c['RecordType']['Id'] == CONTACT_REC_TYPE_ID_OWNERS else 0))
        return contact_tuples

    REF_TYPE_ALL = 'all'
    REF_TYPE_MAIN = 'main'
    REF_TYPE_EXT = 'external'

    def contact_by_rci_id(self, imp_rci_ref, sf_contact_id=None, dup_contacts=None, which_ref=REF_TYPE_ALL):
        if not dup_contacts:
            dup_contacts = list()
        if which_ref in (self.REF_TYPE_MAIN, self.REF_TYPE_ALL):
            soql_query = "SELECT Id FROM Contact WHERE RCI_Reference__c = '{}'".format(imp_rci_ref)
            col_name = 'Id'
        else:   # which_ref == REF_TYPE_EXT
            soql_query = "SELECT Contact__c FROM External_Ref__c WHERE Reference_No_or_ID__c = '{}'".format(imp_rci_ref)
            col_name = 'Contact__c'
        res = self._soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            if not sf_contact_id:
                sf_contact_id = res['records'][0][col_name]
            if res['totalSize'] > 1:
                new_contacts = [_[col_name] for _ in res['records']]
                dup_contacts = list(set([_ for _ in new_contacts + dup_contacts if _ != sf_contact_id]))

        if which_ref == self.REF_TYPE_ALL:
            sf_contact_id, dup_contacts = self.contact_by_rci_id(imp_rci_ref, sf_contact_id, dup_contacts,
                                                                 self.REF_TYPE_EXT)
        return sf_contact_id, dup_contacts

    def contact_id_by_email(self, email):
        soql_query = "SELECT Id FROM Contact WHERE Email = '{}'".format(email)
        res = self._soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            return res['records'][0]['Id']
        return None

    def contact_sh_id(self, sf_contact_id):
        sh_id = None
        res = self._soql_query_all("SELECT Sihot_Guest_Object_Id__c FROM Contact WHERE Id = '{}'".format(sf_contact_id))
        if not self.error_msg and res['totalSize'] > 0:
            sh_id = res['records'][0]['Sihot_Guest_Object_Id__c']
        return sh_id

    def contact_data_by_id(self, sf_contact_id, field_names):
        sf_dict = dict()
        res = self._soql_query_all("SELECT {} FROM Contact WHERE Id = '{}'"
                                   .format(", ".join(field_names), sf_contact_id))
        if not self.error_msg and res['totalSize'] > 0:
            sf_dict = res['records'][0]
        return sf_dict

    def contacts_to_validate(self, rec_type_dev_names=None, additional_filter='',
                             email_validation=EMAIL_NOT_VALIDATED,
                             phone_validation=PHONE_DO_NOT_VALIDATE, addr_validation=ADDR_DO_NOT_VALIDATE):
        assert not rec_type_dev_names or rec_type_dev_names.startswith("'") and rec_type_dev_names.endswith("'") \
            and rec_type_dev_names.count(",") == rec_type_dev_names.replace(" ", "").count("','")
        assert (email_validation != EMAIL_DO_NOT_VALIDATE or phone_validation != PHONE_DO_NOT_VALIDATE) \
            and addr_validation == ADDR_DO_NOT_VALIDATE     # address validation currently not fully implemented
        q = ("SELECT Id, Country__c"
             + (", Email, CD_email_valid__c" if email_validation != EMAIL_DO_NOT_VALIDATE else "")
             + (", HomePhone, CD_Htel_valid__c, MobilePhone, CD_mtel_valid__c, Work_Phone__c, CD_wtel_valid__c"
                if phone_validation != PHONE_DO_NOT_VALIDATE else "")
             + " FROM Contact WHERE"
             + (" (" + additional_filter + ") and " if additional_filter else "")
             + (" RecordType.DeveloperName in (" + rec_type_dev_names + ") and " if rec_type_dev_names else "")
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
        res = self._soql_query_all(q)
        if self.error_msg or res['totalSize'] <= 0:
            contact_dicts = list()
        else:
            contact_dicts = [{k: v for k, v in rec.items() if k != 'attributes'} for rec in res['records']]
            assert len(contact_dicts) == res['totalSize']
        return contact_dicts

    def contact_upsert(self, fields_dict):
        if not self._ensure_lazy_connect():
            return self.error_msg, ""

        sf_id = err = msg = ""
        if 'Id' in fields_dict:     # update?
            fd = deepcopy(fields_dict)     # copy to local dict fd for to prevent changing the passed-in dict field_dict
            sf_id = fd['Id']
            fd.pop('Id')
            try:
                sf_ret = self._conn.Contact.update(sf_id, fd)
                msg = "{} updated with {}, status={}".format(sf_id, pprint.pformat(fd, indent=9), sf_ret)
            except Exception as ex:
                err = "Contact update raised exception {}. sent={}".format(ex, pprint.pformat(fd, indent=9))
        else:
            try:
                sf_ret = self._conn.Contact.create(fields_dict)
                msg = "Contact created with {}, status={}".format(pprint.pformat(fields_dict, indent=9), sf_ret)
                if sf_ret['success']:
                    sf_id = sf_ret['id']
            except Exception as ex:
                err = "Contact creation raised exception {}. sent={}".format(ex, pprint.pformat(fields_dict, indent=9))

        if err:
            self.error_msg = err

        return sf_id, err, msg

    def contact_delete(self, sf_id):
        if not self._ensure_lazy_connect():
            return self.error_msg, ""

        msg = ""
        try:
            sf_ret = self._conn.Contact.delete(sf_id)
            msg = "Contact {} deleted, status={}".format(sf_id, pprint.pformat(sf_ret, indent=9))
        except Exception as ex:
            self.error_msg = "Contact {} deletion raised exception {}".format(sf_id, ex)

        return self.error_msg, msg

    def record_type_id(self, dev_name, obj_type='Contact'):
        rec_type_id = None
        res = self._soql_query_all("Select Id From RecordType Where SobjectType = '{}' and DeveloperName = '{}'"
                                   .format(obj_type, dev_name))
        if not self.error_msg and res['totalSize'] > 0:
            rec_type_id = res['records'][0]['Id']
        return rec_type_id

    def find_client(self, email="", phone="", first_name="", last_name=""):
        if not self._ensure_lazy_connect():
            return dict(id='', type='')

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
        result = self._conn.apexecute('SIHOT', method='POST', data=service_args)

        return result
