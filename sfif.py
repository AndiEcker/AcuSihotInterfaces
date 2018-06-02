# salesforce high level interface
import string
import pprint
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceExpiredSession
from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE

# default client salesforce object
DEF_CLIENT_OBJ = 'Lead'

# flag to determine client object from SF ID
DETERMINE_CLIENT_OBJ = '#Unknown#'


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

# used salesforce record types for newly created Lead/Contact/Account objects
RECORD_TYPES = dict(Lead='SIHOT_Leads', Contact='Rentals', Account='PersonAccount')

# SF ID prefixes for to determine SF object
# TODO: get from Account/Contact/Lead.metadata()['objectDescribe']['keyPrefix']
ID_PREFIX_OBJECTS = {'001': 'Account', '003': 'Contact', '00Q': 'Lead'}


def obj_from_id(sf_id):
    return ID_PREFIX_OBJECTS.get(sf_id[:3], DEF_CLIENT_OBJ)


def ensure_long_id(sf_id):
    """
    ensure that the passed sf_id will be returned as a 18 character Salesforce ID (if passed in as 15 character SF ID).

    :param sf_id:   any valid (15 or 18 character long) SF ID.
    :return:        18 character SF ID if passed in as 15 or 18 character ID - other SF ID lengths/values returns None.
    """
    if not sf_id or len(sf_id) != 15:
        return None
    elif len(sf_id) == 18:
        return sf_id

    char_map = string.ascii_uppercase + "012345"
    extend = ""
    for chunk in range(3):
        bin_str = ""
        for pos in range(5):
            bin_str = ("1" if sf_id[chunk * 5 + pos] in string.ascii_uppercase else "0") + bin_str
        extend += char_map[int(bin_str, 2)]

    return sf_id + extend


def add_sf_options(cae):
    cae.add_option('sfUser', "Salesforce account user name", '', 'y')
    cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
    cae.add_option('sfToken', "Salesforce account token string", '', 'o')
    cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
    cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')


def prepare_connection(cae, verbose=True):
    global _debug_level
    _debug_level = cae.get_option('debugLevel')

    sf_user = cae.get_option('sfUser')
    if not sf_user:         # check if app is specifying Salesforce credentials, e.g. SihotResSync/SihotResImport do not
        uprint("sfif.prepare_connection(): skipped because of unspecified credentials")
        return None, None
    sf_pw = cae.get_option('sfPassword')
    sf_token = cae.get_option('sfToken')
    sf_sandbox = cae.get_option('sfIsSandbox', default_value='test' in sf_user.lower() or 'sandbox' in sf_user.lower())
    sf_client = cae.get_option('sfClientId')

    if verbose:
        uprint("Salesforce " + ("sandbox" if sf_sandbox else "production") + " user/client-id:", sf_user, sf_client)

    sf_conn = SfInterface(sf_user, sf_pw, sf_token, sf_sandbox, sf_client)

    return sf_conn, sf_sandbox


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
        if not self._ensure_lazy_connect():
            return None
        client_obj = getattr(self._conn, sf_obj, None)
        if not client_obj:
            self.error_msg = "SfInterface.sf_obj({}) called with invalid salesforce object type".format(sf_obj)
        return client_obj

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

    def client_ext_refs(self, sf_client_id, er_id=None, er_type=None, sf_obj=DETERMINE_CLIENT_OBJ):
        """
        Return external references of client specified by sf_client_id (and optionally sf_obj).

        :param sf_client_id:    Salesforce Id of client record (Lead, Contact, Account, PersonAccount, ...).
        :param er_id:           External reference (No or Id).
        :param er_type:         Type of external reference (e.g. EXT_REF_TYPE_RCI), pass None/nothing for all types.
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
            soql += " AND Reference_No_or_ID__c = '{}'".format(er_id)
        if er_type:
            soql += " AND Name = '{}'".format(er_type)
        res = self.soql_query_all(soql)
        if not self.error_msg and res['totalSize'] > 0:
            for c in res['records']:  # list of External_References__r OrderedDicts
                ext_refs.append(c['Id'] if er_id else (c['Name'], c['Reference_No_or_ID__c']))
        return ext_refs

    def ext_ref_upsert(self, sf_client_id, er_id, er_type, sf_obj=DETERMINE_CLIENT_OBJ):
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
