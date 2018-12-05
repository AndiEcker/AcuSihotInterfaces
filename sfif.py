# salesforce high level interface
import string
import datetime
import pprint
from traceback import format_exc

from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceExpiredSession

from ae_sys_data import Record, FAD_ONTO
from sys_data_ids import EXT_REF_TYPE_RCI, SDI_SF
from ae_console_app import uprint, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE

# default client salesforce object (was 'Lead' changed to Person-'Account' within sys_data_generic branch)
DEF_CLIENT_OBJ = 'Account'


# client data maps for Lead, Contact and Account
MAP_CLIENT_OBJECTS = \
    {'Account': (
        # ('AssCache_Id__pc', 'AssId'),
        # ('CD_CODE__pc', 'AcId'),
        ('PersonAccountId', 'SfId'),                      # was Id but test_sfif.py needs lower case id
        ('SihotGuestObjId__pc', 'ShId'),
        ('LastName', 'Surname'),
        ('FirstName', 'Forename'),
        ('PersonEmail', 'Email'),
        ('PersonHomePhone', 'Phone'),
        # ('RCI_Reference__pc', 'RciId'),
        # ('KM_DOB__pc', 'DOB'),
        ('PersonMailingStreet', 'Street'),
        ('PersonMailingCity', 'City'),
        # ('PersonMailingState', 'State'),
        # ('PersonMailingPostalCode', 'Postal'),
        ('PersonMailingCountry', 'Country'),
        ('Language__pc', 'Language'),
        ('Nationality__pc', 'Nationality'),
        ('CurrencyIsoCode', 'Currency'),
        # ('Marketing_Source__pc', 'MarketSource'),
        # ('Previous_Arrival_Info__pc', 'ArrivalInfo')
     ),
     'Contact': (
         ('AssCache_Id__c', 'AssId'),
         ('CD_CODE__c', 'AcId'),
         ('id', 'SfId'),  # was Id but test_sfif.py needs lower case id
         ('Sihot_Guest_Object_Id__c', 'ShId'),
         ('RCI_Reference__c', 'RciId'),
         ('DOB1__c', 'DOB'),
         ('MailingStreet', 'Street'),
         ('MailingCity', 'City'),
         ('Country__c', 'Country'),
         ('Language__c', 'Language'),
         # ('Marketing_Source__c', 'MarketSource'),
         # ('Previous_Arrival_Info__c', 'ArrivalInfo')
     ),
     'Lead': (
         ('AssCache_Id__c', 'AssId'),
         ('Acumen_Client_Reference__c', 'AcId'),
         ('id', 'SfId'),  # was Id but test_sfif.py needs lower case id
         ('Sihot_Guest_Object_Id__c', 'ShId'),
         ('DOB1__c', 'DOB'),
         ('Nationality__c', 'Language'),
         # ('Market_Source__c', 'MarketSource'),
         # ('Previous_Arrivals__c', 'ArrivalInfo')
     )
     }

# Reservation Object fields
MAP_RES_OBJECT = (
    ('HotelId__c', 'ResHotelId'),
    ('Number__c', 'ResId'),
    ('SubNumber__c', 'ResSubId'),
    ('GdsNo__c', 'ResGdsNo'),
    ('ReservationOpportunityId', 'ResSfId'),
    ('SihotResvObjectId__c', 'ResObjId'),
    ('Arrival__c', 'ResArrival'),
    ('Departure__c', 'ResDeparture'),
    ('RoomNo__c', 'ResRoomNo'),
    ('RoomCat__c', 'ResRoomCat'),
    ('Status__c', 'ResStatus'),
    ('MktGroup__c', 'ResMktGroup'),
    ('MktSegment__c', 'ResMktSegment'),
    ('Adults__c', 'ResAdults'),
    ('Children__c', 'ResChildren'),
    ('Note__c', 'ResNote'),
    # ('', ('ResPersons', 0, 'AcId')),
    # ('', ('ResPersons', 0, 'DOB')),
    # ('', ('ResPersons', 0, 'Forename')),
    # ('', ('ResPersons', 0, 'GuestType')),
    # ('', ('ResPersons', 0, 'ShId')),
    # ('', ('ResPersons', 0, 'Surname')),
)

# Allocation Object fields
MAP_ROOM_OBJECT = (
    ('CheckIn__c', 'ResCheckIn'),
    ('CheckOut__c', 'ResCheckOut'),
)

# from Sf rec map (used e.g. by SihotServer)
''' - NOT NEEDED BECAUSE SAME FIELD NAMES (see SihotServer.py/sh_res_upsert())
MAP_RES_FROM_SF = (
    ('ResHotelId', 'ResHotelId'),
    ('ResId', 'ResId'),
    ('ResSubId', 'ResSubId'),
    ('ResGdsNo', 'ResGdsNo'),
    ('ResArrival', 'ResArrival'),
    ('ResDeparture', 'ResDeparture'),
    ('ResRoomNo', 'ResRoomNo'),
    ('ResRoomCat', 'ResRoomCat'),
    ('ResPriceCat', 'ResPriceCat'),
    ('ResPersons0SurName', ('ResPersons', 0, 'SurName')),
)
'''

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
ID_PREFIX_OBJECTS = {'001': 'Account', '003': 'Contact', '00Q': 'Lead'}


# default search fields for external systems (used by sfif.sf_client_field_data())
SF_DEF_SEARCH_FIELD = 'SfId'


ppf = pprint.PrettyPrinter(indent=12, width=96, depth=9).pformat


def add_sf_options(cae):
    cae.add_option('sfUser', "Salesforce account user name", '', 'y')
    cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
    cae.add_option('sfToken', "Salesforce account token string", '', 'o')
    cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
    cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')


SF_DATE_FORMAT = '%Y-%m-%d'
SF_DATE_TIME_FORMAT_FROM = '%Y-%m-%dT%H:%M:%S.%f%z'
SF_DATE_TIME_FORMAT_ONTO = '%Y-%m-%d %H:%M:%S'
SF_TIME_DIFF_FROM = datetime.timedelta(hours=1)
SF_DATE_ZERO_HOURS = " 00:00:00"


def convert_date_from_sf(str_val):
    if str_val.find(' ') != -1:
        str_val = str_val.split(' ')[0]
    elif str_val.find('T') != -1:
        str_val = str_val.split('T')[0]
    return (datetime.datetime.strptime(str_val, SF_DATE_FORMAT) + SF_TIME_DIFF_FROM).date()


def convert_date_onto_sf(date):
    return date.strftime(SF_DATE_FORMAT) + SF_DATE_ZERO_HOURS


def convert_date_time_from_sf(str_val):
    mask = SF_DATE_TIME_FORMAT_FROM
    if str_val.find('+') == -1:
        mask = mask[:-2]        # no timezone specified in str_val, then remove %z from mask
    if str_val.find('.') == -1:
        mask = mask[:mask.find('.')]
    if str_val.find(' ') != -1:
        mask = mask.replace('T', ' ')
    elif str_val.find('T') == -1:
        mask = mask[:mask.find('T')]
    return datetime.datetime.strptime(str_val, mask).replace(microsecond=0, tzinfo=None) + SF_TIME_DIFF_FROM


def convert_date_time_onto_sf(date):
    return date.strftime(SF_DATE_TIME_FORMAT_ONTO)


def convert_date_field_from_sf(_, str_val):
    return convert_date_from_sf(str_val)


def convert_date_field_onto_sf(_, date):
    return convert_date_onto_sf(date)


def convert_date_time_field_from_sf(_, str_val):
    return convert_date_time_from_sf(str_val)


def convert_date_time_field_onto_sf(_, date):
    return convert_date_time_onto_sf(date)


field_from_converters = dict(ResArrival=convert_date_field_from_sf, ResDeparture=convert_date_field_from_sf,
                             ResCheckIn=convert_date_time_field_from_sf, ResCheckOut=convert_date_time_field_from_sf,
                             ResAdults=lambda f, v: int(v), ResChildren=lambda f, v: int(v),
                             )
field_onto_converters = dict(ResArrival=convert_date_field_onto_sf, ResDeparture=convert_date_field_onto_sf,
                             ResCheckIn=convert_date_time_field_onto_sf, ResCheckOut=convert_date_time_field_onto_sf,
                             ResAdults=lambda f, v: str(v), ResChildren=lambda f, v: str(v),
                             )


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

    return sf_conn


def code_name(sf_fld, sf_obj):
    field_map = MAP_CLIENT_OBJECTS.get(sf_obj, tuple())
    for sys_name, fld_name in field_map:
        if sys_name == sf_fld:
            field_name = fld_name
            break
    else:
        field_name = sf_fld
    return field_name


def sf_fld_name(field_name, sf_obj):
    field_map = MAP_CLIENT_OBJECTS.get(sf_obj, tuple())
    for sys_name, fld_name in field_map:
        if fld_name == field_name:
            fld_name = sys_name
            break
    else:
        fld_name = field_name
    return fld_name


def field_dict_from_sf(sf_dict, sf_obj):
    field_dict = dict()
    for sf_fld, val in sf_dict.items():
        if sf_fld != 'attributes':
            field_dict[code_name(sf_fld, sf_obj)] = val
    return field_dict


def field_list_to_sf(code_list, sf_obj):
    sf_list = list()
    for field_name in code_list:
        sf_list.append(sf_fld_name(field_name, sf_obj))
    return sf_list


def rec_to_sf_obj_fld_dict(rec, sf_obj):
    sf_dict = dict()
    for field_name, val in rec.items():
        sf_key = sf_fld_name(field_name, sf_obj)
        sf_dict[sf_key] = val
    return sf_dict


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
        self.cl_res_rec_onto = Record(system=SDI_SF, direction=FAD_ONTO)\
            .add_system_fields(MAP_CLIENT_OBJECTS['Account'] + MAP_RES_OBJECT)

    @property
    def is_sandbox(self):
        return self._sb

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

    def client_delete(self, sf_id, sf_obj=None):
        if not self._ensure_lazy_connect():
            return self.error_msg, ""

        if sf_obj is None:
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

    def client_ext_refs(self, sf_client_id, er_id=None, er_type=None, sf_obj=None):
        """
        Return external references of client specified by sf_client_id (and optionally sf_obj).

        :param sf_client_id:    Salesforce Id of client record (Lead, Contact, Account, PersonAccount, ...).
        :param er_id:           External reference (No or Id).
        :param er_type:         Type of external reference (e.g. EXT_REF_TYPE_RCI), pass None/nothing for all types.
        :param sf_obj:          Salesforce object of the client passed into sf_client_id (Lead, Contact, Account, ...).
        :return:                If er_id get passed in then: list of tuples of found external ref type and id of client.
                                Else: list of Salesforce Ids of external references (mostly only one).
        """
        if sf_obj is None:
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

    def ext_ref_upsert(self, sf_client_id, er_id, er_type, sf_obj=None):
        if not self._ensure_lazy_connect():
            return None, self.error_msg, ""

        er_obj = 'External_References'
        ext_ref_obj = self.sf_obj(er_obj)
        if not ext_ref_obj:
            self.error_msg += " ext_ref_upsert() sf_id={}, er_id={}".format(sf_client_id, er_id)
            return None, self.error_msg, ""

        if sf_obj is None:
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
        if not self._ensure_lazy_connect():
            return dict(sfif_apex_error=self.error_msg)

        if function_args:
            # don't change callers dict, remove underscore characters from arg names (APEX methods doesn't allow them)
            # .. and convert date/time types into SF apex format
            # STRANGE PYTHON: isinstance(datetime_value, date) == True - therefore 1st check for datetime.datetime
            function_args = {k.replace('_', ''):
                             convert_date_time_onto_sf(v) if isinstance(v, datetime.datetime) else
                             (convert_date_onto_sf(v) if isinstance(v, datetime.date) else v)
                             for (k, v) in function_args.items()}

        try:
            result = self._conn.apexecute(function_name, method='POST', data=function_args)
        except Exception as ex:
            err_msg = "sfif.apex_call({}, {}) exception='{}'\n{}".format(function_name, function_args, ex, format_exc())
            result = dict(sfif_apex_error=err_msg)
            self.error_msg = err_msg

        return result

    def find_client(self, email="", phone="", first_name="", last_name=""):
        service_args = dict(email=email, phone=phone, firstName=first_name, lastName=last_name)
        result = self.apex_call('clientsearch', function_args=service_args)

        if self._debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("find_client({}, {}, {}, {}) result={}".format(email, phone, first_name, last_name, ppf(result)))

        if self.error_msg or 'id' not in result or 'type' not in result:
            return '', DEF_CLIENT_OBJ

        return result['id'], result['type']

    def sf_client_upsert(self, rec, sf_obj=None):
        # check if Id passed in (then this method can determine the sf_obj and will do an update not an insert)
        sf_id, update_client = (rec.pop(SF_DEF_SEARCH_FIELD), True) if SF_DEF_SEARCH_FIELD in rec \
            else ('', False)

        if sf_obj is None:
            if not sf_id:
                self.error_msg = "sf_client_upsert({}, {}): client object cannot be determined without Id"\
                    .format(ppf(rec), sf_obj)
                return None, self.error_msg, ""
            sf_obj = obj_from_id(sf_id)

        client_obj = self.sf_obj(sf_obj)
        if not client_obj:
            self.error_msg += "\n      +sf_client_upsert({}, {}): no client object".format(ppf(rec), sf_obj)
            return None, self.error_msg, ""

        sf_dict = rec_to_sf_obj_fld_dict(rec, sf_obj)
        err = msg = ""
        if update_client:
            try:
                sf_ret = client_obj.update(sf_id, sf_dict)
                msg = "{} {} updated with {}, ret={}".format(sf_obj, sf_id, ppf(sf_dict), sf_ret)
            except Exception as ex:
                err = "{} update() raised exception {}. sent={}".format(sf_obj, ex, ppf(sf_dict))
        else:
            try:
                sf_ret = client_obj.create(sf_dict)
                msg = "{} created with {}, ret={}".format(sf_obj, ppf(sf_dict), sf_ret)
                if sf_ret['success']:
                    sf_id = sf_ret[sf_fld_name(SF_DEF_SEARCH_FIELD, sf_obj)]
            except Exception as ex:
                err = "{} create() exception {}. sent={}".format(sf_obj, ex, ppf(sf_dict))

        if not err and sf_id and 'RciId' in rec:
            _, err, msg = self.ext_ref_upsert(sf_id, rec['RciId'], EXT_REF_TYPE_RCI, sf_obj=sf_obj)

        if err:
            self.error_msg = err

        return sf_id, err, msg

    def sf_clients_with_rci_id(self, ext_refs_sep, owner_rec_types=None, sf_obj=DEF_CLIENT_OBJ):
        if not owner_rec_types:
            owner_rec_types = list()
        soql_fields = ['SfId', 'AcId', 'RciId', 'ShId', 'RecordType.Id',
                       "(SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"]
        sf_fields = field_list_to_sf(soql_fields, sf_obj)
        res = self.soql_query_all("SELECT {} FROM {}".format(", ".join(sf_fields), sf_obj))
        client_tuples = list()
        if self.error_msg:
            self.error_msg = "sf_clients_with_rci_id(): " + self.error_msg
        elif res['totalSize'] > 0:
            for c in res['records']:  # list of client OrderedDicts
                ext_refs = [c[sf_fld_name('RciId', sf_obj)]] if c[sf_fld_name('RciId', sf_obj)] else list()
                if c['External_References__r']:
                    ext_refs.extend([_['Reference_No_or_ID__c'] for _ in c['External_References__r']['records']])
                if ext_refs:
                    client_tuples.append((None, c[sf_fld_name('AcId', sf_obj)],
                                          c[sf_fld_name(SF_DEF_SEARCH_FIELD, sf_obj)], c[sf_fld_name('ShId', sf_obj)],
                                          ext_refs_sep.join(ext_refs),
                                          1 if c['RecordType']['Id'] in owner_rec_types else 0))
        return client_tuples

    REF_TYPE_ALL = 'all'
    REF_TYPE_MAIN = 'main'
    REF_TYPE_EXT = 'external'

    def sf_client_by_rci_id(self, rci_ref, sf_id=None, dup_clients=None, which_ref=REF_TYPE_ALL, sf_obj=DEF_CLIENT_OBJ):
        if not dup_clients:
            dup_clients = list()
        if which_ref in (self.REF_TYPE_MAIN, self.REF_TYPE_ALL):
            fld_name = sf_fld_name(SF_DEF_SEARCH_FIELD, sf_obj)
            soql_query = "SELECT {} FROM {} WHERE {} = '{}'".format(fld_name, sf_obj, sf_fld_name('RciId', sf_obj),
                                                                    rci_ref)
        else:  # which_ref == REF_TYPE_EXT
            fld_name = '{}__c'.format(sf_obj)
            soql_query = "SELECT {} FROM External_Ref__c WHERE Reference_No_or_ID__c = '{}'".format(fld_name, rci_ref)
        res = self.soql_query_all(soql_query)
        if self.error_msg:
            self.error_msg = "sf_client_by_rci_id({}): ".format(rci_ref) + self.error_msg
        elif res['totalSize'] > 0:
            if not sf_id:
                sf_id = res['records'][0][fld_name]
            if res['totalSize'] > 1:
                new_clients = [_[fld_name] for _ in res['records']]
                dup_clients = list(set([_ for _ in new_clients + dup_clients if _ != sf_id]))

        if which_ref == self.REF_TYPE_ALL:
            sf_id, dup_clients = self.sf_client_by_rci_id(rci_ref, sf_id, dup_clients, self.REF_TYPE_EXT)
        return sf_id, dup_clients

    def sf_client_field_data(self, fetch_fields, search_value, search_val_deli="'", search_op='=',
                             search_field=SF_DEF_SEARCH_FIELD, sf_obj=None,
                             log_warnings=None):
        """
        fetch field data from SF object (identified by sf_obj) and client (identified by search_value/search_field).
        :param fetch_fields:    either pass single field name (str) or list of field names of value(s) to be returned.
        :param search_value:    value for to identify client record.
        :param search_val_deli: delimiter used for to enclose search value within SOQL query.
        :param search_op:       search operator (between search_field and search_value).
        :param search_field:    field name used for to identify client record (def=SF_DEF_SEARCH_FIELD=='SfId').
        :param sf_obj:          SF object to be searched (def=determined by the passed ID prefix).
        :param log_warnings:    pass list for to append warning log entries on re-search on old/redirected SF IDs.
        :return:                either single field value (if fetch_fields is str) or dict(fld=val) of field values.
        """
        if sf_obj is None:
            if search_field not in (SF_DEF_SEARCH_FIELD, 'External_Id__c', 'Contact_Ref__c', 'Id_before_convert__c',
                                    'CSID__c'):
                self.error_msg = "sf_client_field_data({}, {}, {}, {}): client object cannot be determined without Id" \
                    .format(fetch_fields, search_value, search_field, sf_obj)
                return None
            sf_obj = obj_from_id(search_value)
            if not sf_obj:
                self.error_msg = "sf_client_field_data(): {} field value {} is not a valid Lead/Contact/Account SF ID" \
                    .format(search_field, search_value)
                return None

        ret_dict = isinstance(fetch_fields, list)
        if ret_dict:
            select_fields = ", ".join(field_list_to_sf(fetch_fields, sf_obj))
            fetch_field = None  # only needed for to remove PyCharm warning
            ret_val = dict()
        else:
            select_fields = fetch_field = sf_fld_name(fetch_fields, sf_obj)
            ret_val = None
        soql_query = "SELECT {} FROM {} WHERE {} {} {}{}{}" \
            .format(select_fields, sf_obj,
                    sf_fld_name(search_field, sf_obj), search_op, search_val_deli, search_value, search_val_deli)
        res = self.soql_query_all(soql_query)
        if self.error_msg:
            self.error_msg = "sf_client_field_data({}, {}, {}): ".format(fetch_fields, search_value, search_field) \
                             + self.error_msg
        elif res['totalSize'] > 0:
            ret_val = res['records'][0]
            if ret_dict:
                ret_val = field_dict_from_sf(ret_val, sf_obj)
            else:
                ret_val = ret_val[fetch_field]

        # if not found as object ID then re-search recursively old/redirected SF IDs in other indexed/external SF fields
        if not ret_val and search_field == SF_DEF_SEARCH_FIELD:
            if log_warnings is None:
                log_warnings = list()
            log_warnings.append("{} ID {} not found as direct/main ID in {}s".format(sf_obj, search_value, sf_obj))
            if sf_obj == 'Lead':
                # try to find this Lead Id in the Lead field External_Id__c
                ret_val = self.sf_client_field_data(fetch_fields, search_value, search_field='External_Id__c')
                if not ret_val:
                    ret_val = self.sf_client_field_data(fetch_fields, search_value, search_field='CSID__c')
                    if not ret_val:
                        log_warnings.append("{} ID {} not found in Lead fields External_Id__c/CSID__c"
                                            .format(sf_obj, search_value))
            elif sf_obj == 'Contact':
                # try to find this Contact Id in the Contact fields Contact_Ref__c, Id_before_convert__c
                ret_val = self.sf_client_field_data(fetch_fields, search_value, search_field='Contact_Ref__c')
                if not ret_val:
                    ret_val = self.sf_client_field_data(fetch_fields, search_value, search_field='Id_before_convert__c')
                    if not ret_val:
                        log_warnings.append("{} ID {} not found in Contact fields Contact_Ref__c/Id_before_convert__c"
                                            .format(sf_obj, search_value))

        """ FUTURE ENHANCEMENT 
            in case a Lead IsConverted to Contact/Account we need to get more up-to-date Contact/Account data.

            Select Id, ConvertedContactId, ConvertedAccountId, ConvertedDate, 
                   Phone, Lead.ConvertedContact.Phone, Lead.ConvertedAccount.Phone, 
                   Email, Lead.ConvertedContact.Email, Lead.ConvertedAccount.PersonEmail, 
                   Name, Lead.ConvertedContact.Name, Lead.ConvertedAccount.Name 
              from Lead
             where IsConverted = true

        # if found then check if there is a follow-up/converted/parent SF obj with maybe more actual data
        if ret_val:
            if sf_obj == 'Lead':
                chk_val = self.sf_client_field_data(fetch_fields, search_value, sf_obj='Account')
                if chk_val:
                    ret_val = chk_val
        """
        return ret_val

    def sf_client_ass_id(self, sf_client_id, sf_obj=None):
        return self.sf_client_field_data('AssId', sf_client_id, sf_obj=sf_obj)

    def sf_client_ac_id(self, sf_client_id, sf_obj=None):
        return self.sf_client_field_data('AcId', sf_client_id, sf_obj=sf_obj)

    def sf_client_sh_id(self, sf_client_id, sf_obj=None):
        return self.sf_client_field_data('ShId', sf_client_id, sf_obj=sf_obj)

    def sf_client_id_by_email(self, email, sf_obj=DEF_CLIENT_OBJ):
        return self.sf_client_field_data('SfId', email, search_field='Email', sf_obj=sf_obj)

    def sf_res_data(self, res_opp_id):
        """
        fetch client+res data from SF Reservation Opportunity object (identified by res_opp_id)
        :param res_opp_id:  value for to identify client record.
        :return:            dict with sf_data.
        """
        ret_val = dict(ReservationOpportunityId=res_opp_id)
        soql_query = '''
            SELECT Account.Id, Account.FirstName, Account.LastName, Account.PersonEmail, Account.PersonHomePhone,
                   Account.CD_CODE__pc, Account.SihotGuestObjId__pc, 
                   Account.Language__pc, 
                   Account.PersonMailingStreet, Account.PersonMailingPostalCode, Account.PersonMailingCity, 
                   Account.PersonMailingCountry, 
                   Account.CurrencyIsoCode, Account.Nationality__pc, 
                   (SELECT Id, HotelId__c, Number__c, SubNumber__c, GdsNo__c, Arrival__c, Departure__c, Status__c,  
                           RoomNo__c, MktSegment__c, MktGroup__c, RoomCat__c, Adults__c, Children__c, Note__c, 
                           SihotResvObjectId__c
                      FROM Reservations__r) 
              FROM Opportunity WHERE Id = '{}'
              '''.format(res_opp_id)
        res = self.soql_query_all(soql_query)
        if self.error_msg:
            self.error_msg = "sf_res_data({}): ".format(res_opp_id) + self.error_msg
        elif res['totalSize'] > 0:
            ret_all = res['records'][0]
            ret = dict()
            if ret_all['Account']:      # is None if no Account associated
                ret.update(ret_all['Account'])
                ret['PersonAccountId'] = ret.get('Id')
            if ret_all['Reservations__r'] and ret_all['Reservations__r']['totalSize'] > 0:
                ret.update(ret_all['Reservations__r']['records'][0])
                ret['ReservationId'] = ret.get('Id')
            del ret['attributes']
            for k, v in ret.items():
                if k in ('attributes', 'Id', ):
                    continue
                if k in ('Arrival__c', 'Departure__c', ) and v:
                    v = convert_date_from_sf(v)
                ret_val[k] = v

        return ret_val

    def res_upsert(self, cl_res_rec):
        sf_args = cl_res_rec.to_dict(system=SDI_SF, direction=FAD_ONTO)
        result = self.apex_call('reservation_upsert', function_args=sf_args)

        if self._debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("... sfif.res_upsert({}) result={} err='{}'".format(ppf(cl_res_rec), ppf(result), self.error_msg))

        if result.get('ErrorMessage'):
            msg = ppf(result) if self._debug_level >= DEBUG_LEVEL_ENABLED else result['ErrorMessage']
            self.error_msg += "sfif.res_upsert({}) received error '{}' from SF".format(ppf(cl_res_rec), msg)
        if not self.error_msg:
            if not cl_res_rec.val('ResSfId') and result.get('ReservationOpportunityId'):
                cl_res_rec['ResSfId'] = result['ReservationOpportunityId']
            elif cl_res_rec.val('ResSfId') != result.get('ReservationOpportunityId'):
                msg = "sfif.res_upsert({}) ResSfId discrepancy; sent={} received={}"\
                       .format(ppf(cl_res_rec),
                               cl_res_rec.val('ResSfId'), result.get('ReservationOpportunityId'))
                uprint(msg)
                if msg and self._debug_level >= DEBUG_LEVEL_ENABLED:
                    self.error_msg += "\n      " + msg

        return result.get('PersonAccountId'), result.get('ReservationOpportunityId'), self.error_msg

    def room_change(self, res_sf_id, check_in, check_out, next_room_id):
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

    def sf_room_data(self, res_opp_id):
        """
        fetch client+res+room data from SF Reservation Opportunity object (identified by res_opp_id)
        :param res_opp_id:  value for to identify client record.
        :return:            dict with sf_data.
        """
        sf_data = self.sf_res_data(res_opp_id)

        # TODO: implement generic sf_field_data() method for to be called by this method and sf_client_field_data()
        # UNTIL THEN HARDCODED SOQL QUERIES
        ''' 
        # select from Reservation object:
        SELECT Opportunity__r.Id, 
               Opportunity__r.Account.LastName, Opportunity__r.Account.PersonEmail, 
               Id, Arrival__c, HotelId__c, 
               (select Id, CheckIn__c, CheckOut__c from Allocations__r) 
          FROM Reservation__c WHERE Id = '...a8G0D0000004CH0UAM'

        # select via ResOpp - SF does not allow more than one level of child relation:
        SELECT Id, Account.Id, Account.PersonEmail, (select Id from Reservations__r) 
          FROM Opportunity WHERE Id = '0060O00000rTYe1QAG'
        SELECT Id, Account.Id, Account.PersonEmail, (select Id, HotelId__c, Arrival__c from Reservations__r)
          FROM Opportunity WHERE Id = '0060O00000rTYe1QAG'
        '''
        ret_val = dict(ReservationOpportunityId=res_opp_id)
        soql_query = '''
            SELECT Id, 
                   (select Id, CheckIn__c, CheckOut__c from Allocations__r) 
              FROM Reservation__c WHERE Id = '{}'
              '''.format(sf_data['ReservationId'])
        res = self.soql_query_all(soql_query)
        if self.error_msg:
            self.error_msg = "sf_room_data({}): ".format(res_opp_id) + self.error_msg
        elif res['totalSize'] > 0:
            ret_all = res['records'][0]
            ret = dict(ReservationId=ret_all['Id'])
            ret.update(ret_all['Allocations__r']['records'][0])
            ret['AllocationId'] = ret.pop('Id')
            del ret['attributes']
            for k, v in ret.items():
                if k in ('CheckIn__c', 'CheckOut__c') and v:
                    v = convert_date_time_from_sf(v)
                ret_val[k] = v

        return ret_val
