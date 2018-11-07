# salesforce high level interface
import string
import datetime
import pprint
from traceback import format_exc

from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceExpiredSession
from ae_console_app import uprint, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE

# default client salesforce object
DEF_CLIENT_OBJ = 'Lead'

# flag to determine client object from SF ID
DETERMINE_CLIENT_OBJ = '#Unknown#'


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


ppf = pprint.PrettyPrinter(indent=12, width=96, depth=9).pformat


SF_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def convert_date_from_sf(str_val):
    return datetime.datetime.strptime(str_val, SF_DATE_FORMAT)


def convert_date_onto_sf(date):
    return date.strftime(SF_DATE_FORMAT)


def convert_date_field_from_sf(_, str_val):
    return convert_date_from_sf(str_val)


def convert_date_field_onto_sf(_, date):
    return convert_date_onto_sf(date)


field_from_converters = dict(ResArrival=convert_date_field_from_sf, ResDeparture=convert_date_field_from_sf,
                             ResAdults=lambda f, v: int(v), ResChildren=lambda f, v: int(v))

field_onto_converters = dict(ResArrival=convert_date_field_onto_sf, ResDeparture=convert_date_field_onto_sf,
                             ResAdults=lambda f, v: str(v), ResChildren=lambda f, v: str(v))


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
    debug_level = cae.get_option('debugLevel')
    sf_user = cae.get_option('sfUser')
    if not sf_user:         # check if app is specifying Salesforce credentials, e.g. SihotResSync/SihotResImport do not
        uprint("sfif.prepare_connection(): skipped because of unspecified credentials")
        return None, None
    sf_pw = cae.get_option('sfPassword')
    sf_token = cae.get_option('sfToken')
    sf_sandbox = cae.get_option('sfIsSandbox', default_value='test' in sf_user.lower() or 'sdbx' in sf_user.lower())
    sf_client = cae.get_option('sfClientId', default_value=cae.app_name())

    if verbose:
        uprint("Salesforce " + ("sandbox" if sf_sandbox else "production") + " user/client-id:", sf_user, sf_client)

    sf_conn = SfInterface(sf_user, sf_pw, sf_token, sf_sandbox, sf_client, debug_level)

    return sf_conn, sf_sandbox


class SfInterface:
    def __init__(self, username, password, token, sandbox, client_id, debug_level):
        # store user credentials for lazy Salesforce connect (only if needed) because of connection limits and timeouts
        self._conn = None
        self._user = username
        self._pw = password
        self._tok = token
        self._sb = sandbox
        self._client = client_id
        self._debug_level = debug_level

        self.error_msg = ""

    def _connect(self):
        try:
            self._conn = Salesforce(username=self._user, password=self._pw, security_token=self._tok,
                                    sandbox=self._sb, client_id=self._client)
            uprint("  ##  Connection to Salesforce established with session id {}".format(self._conn.session_id))
        except SalesforceAuthenticationFailed as sf_ex:
            self.error_msg = "SfInterface.__init__(): Salesforce {} authentication failed with exception: {}" \
                .format('Sandbox' if self._sb else 'Production', sf_ex)

    def _ensure_lazy_connect(self, soql_query="SELECT Id from Lead WHERE Name = '__test__'"):
        """
        ensure that the connection to Salesforce got at least once established and did not expired since then (2 hours).

        :param soql_query:  SOQL query for to check established connection if expired.
        :return:            False:  if connection never got established because of previous invalid login,
                            None:   if first try to connect to Salesforce failed,
                            else return the Salesforce response for the check query (soql_query) if connection was
                            already established or just got established the first time (by calling this method).
        """
        if 'INVALID_LOGIN' in self.error_msg:
            msg = "preventing lock of user account {}".format(self._user)
            if msg not in self.error_msg:
                self.error_msg = " ***  Invalid Salesforce login - {}; last error={}".format(msg, self.error_msg)
            uprint(self.error_msg)
            return False
        self.error_msg = ""

        if not self._conn:
            self.error_msg = ""
            self._connect()
            if self.error_msg:
                if self._debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint("  **  _ensure_lazy_connect() err={}".format(self.error_msg))
                return None

        if self._conn:
            try:
                return self._conn.query_all(soql_query)
            except SalesforceExpiredSession:
                uprint("  ##  SfInterface._ensure_lazy_connect(): Trying re-connecting expired Salesforce session...")
                self._conn = None
                return self._ensure_lazy_connect(soql_query)

        return None

    def soql_query_all(self, soql_query):
        """
        Query Salesforce cloud tables with SOQL.
        This method is tight coupled with the _ensure_lazy_connect() method above - using it for to execute the
        query and doing a connection expiration check at the same time.

        :param soql_query:      SOQL query as string.
        :return:                response from Salesforce.
        """
        response = None
        try:
            response = self._ensure_lazy_connect(soql_query)
        except Exception as sf_ex:
            self.error_msg = "SfInterface.soql_query_all({}) query exception: {}".format(soql_query, sf_ex)
        if isinstance(response, dict) and not response['done']:
            self.error_msg = "SfInterface.soql_query_all(): Salesforce is responding that query {} is NOT done." \
                .format(soql_query)

        if self._debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("soql_query_all({}) response={}".format(soql_query, response))

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
            msg = "{} {} deleted, status={}".format(sf_obj, sf_id, ppf(sf_ret))
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
            if self._debug_level >= DEBUG_LEVEL_VERBOSE and len(er_list) > 1:
                uprint(" ###  ext_ref_upsert({}): duplicate external refs found: {}".format(sf_client_id, ppf(er_list)))
            sf_er_id = er_list[0]
            try:
                sf_ret = ext_ref_obj.update(sf_er_id, sf_dict)
                msg = "{} {} updated with {} ret={}".format(er_obj, sf_er_id, ppf(sf_dict), sf_ret)
            except Exception as ex:
                err = "{} update() raised exception {}. sent={}".format(er_obj, ex, ppf(sf_dict))
        else:
            try:
                sf_ret = ext_ref_obj.create(sf_dict)
                msg = "{} created with {}, ret={}".format(er_obj, ppf(sf_dict), sf_ret)
                if sf_ret['success']:
                    sf_er_id = sf_ret['Id']
            except Exception as ex:
                err = "{} create() exception {}. sent={}".format(er_obj, ex, ppf(sf_dict))

        if err:
            if self._debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("  **  ext_ref_upsert({}) err={}".format(sf_client_id, err))
            self.error_msg = err

        return sf_er_id, err, msg

    def record_type_id(self, sf_obj):
        rec_type_id = None
        res = self.soql_query_all("Select Id From RecordType Where SobjectType = '{}' and DeveloperName = '{}'"
                                  .format(sf_obj, RECORD_TYPES.get(sf_obj)))
        if not self.error_msg and res['totalSize'] > 0:
            rec_type_id = res['records'][0]['Id']
        return rec_type_id

    def apex_call(self, function_name, function_args=None):
        if function_args:
            # don't change callers dict, remove underscore characters from arg names (APEX methods doesn't allow them)
            # .. and convert date/time types into SF apex format
            function_args = {k.replace('_', ''): convert_date_onto_sf(v)
                             if isinstance(v, datetime.date) or isinstance(v, datetime.datetime) else v
                             for (k, v) in function_args.items()}
            # TODO: refactor function_args data type conversion into FIELDS feature method fields_dict_to_sf()
            # NEVER IMPLEMENTED/TESTED ALTERNATIVE: change callers dict keys (removing underscores)
            # .. much simpler after FIELDS refactoring: function_args[k.replace('_', '')] = function_args.pop(k)
            # for k in list(function_args):
            #     new_k = k.replace('_', '')
            #     v = function_args.pop(k)
            #     if isinstance(v, datetime.date) or isinstance(v, datetime.datetime):
            #         v.strftime('%Y-%m-%d %H:%M:%S')
            #     function_args[new_k] = v
        try:
            result = self._conn.apexecute(function_name, method='POST', data=function_args)
        except Exception as ex:
            err_msg = "sfif.apex_call({}, {}) exception='{}'\n{}".format(function_name, function_args, ex, format_exc())
            result = dict(sfif_apex_error=err_msg)
            self.error_msg = err_msg

        # TODO: refactor result data type conversion into FIELDS feature methods sf_fld_value(), fields_dict_from_sf()
        return result

    def find_client(self, email="", phone="", first_name="", last_name=""):
        if not self._ensure_lazy_connect():
            return None, None

        service_args = dict(email=email, phone=phone, firstName=first_name, lastName=last_name)
        result = self.apex_call('clientsearch', function_args=service_args)

        if self._debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("find_client({}, {}, {}, {}) result={}".format(email, phone, first_name, last_name, ppf(result)))

        if self.error_msg or 'id' not in result or 'type' not in result:
            return '', DEF_CLIENT_OBJ

        return result['id'], result['type']

    def res_upsert(self, cl_res_data):
        if not self._ensure_lazy_connect():
            return None, None

        result = self.apex_call('reservation_upsert', function_args=cl_res_data)

        if self._debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("... sfif.res_upsert({}) result={} err='{}'".format(ppf(cl_res_data), ppf(result), self.error_msg))

        if result.get('ErrorMessage'):
            msg = ppf(result) if self._debug_level >= DEBUG_LEVEL_ENABLED else result['ErrorMessage']
            self.error_msg += "sfif.res_upsert({}) received error '{}' from SF".format(ppf(cl_res_data), msg)
        if not self.error_msg:
            if not cl_res_data.get('ReservationOpportunityId') and result.get('ReservationOpportunityId'):
                cl_res_data['ReservationOpportunityId'] = result['ReservationOpportunityId']
            elif cl_res_data['ReservationOpportunityId'] != result.get('ReservationOpportunityId'):
                msg = "sfif.res_upsert({}) ResSfId discrepancy; sent={} received={}"\
                       .format(ppf(cl_res_data),
                               cl_res_data['ReservationOpportunityId'], result.get('ReservationOpportunityId'))
                uprint(msg)
                if msg and self._debug_level >= DEBUG_LEVEL_ENABLED:
                    self.error_msg += "\n      " + msg

        return result.get('PersonAccountId'), result.get('ReservationOpportunityId'), self.error_msg

    def room_change(self, res_sf_id, check_in, check_out, next_room_id):
        if not self._ensure_lazy_connect():
            return None, None

        room_chg_data = dict(ReservationOpportunityId=res_sf_id, CheckIn__c=check_in, CheckOut__c=check_out,
                             RoomNo__c=next_room_id)
        result = self.apex_call('reservation_room_move', function_args=room_chg_data)

        if self._debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("... room_change({}, {}, {}, {}) args={} result={} err='{}'"
                   .format(res_sf_id, check_in, check_out, next_room_id, room_chg_data, ppf(result), self.error_msg))

        if result.get('ErrorMessage'):
            self.error_msg += "sfif.room_change({}, {}, {}, {}) received error '{}' from SF"\
                .format(res_sf_id, check_in, check_out, next_room_id,
                        ppf(result) if self._debug_level >= DEBUG_LEVEL_VERBOSE else result['ErrorMessage'])

        return self.error_msg
