# salesforce high level interface
import string
import datetime
import pprint
from traceback import format_exc
from typing import Tuple, Dict, Any

from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceExpiredSession

from ae.core import DATE_ISO, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, parse_date, po
from ae.sys_data import Record, FAD_ONTO, ACTION_UPDATE, ACTION_INSERT

from sys_data_ids import EXT_REF_TYPE_RCI, EXT_REFS_SEP, EXT_REF_TYPE_ID_SEP

SDI_SF = 'Sf'                               # Salesforce Interfaces


SDF_SF_SANDBOX = 'sfIsSandbox'

# default client salesforce object (was 'Lead' changed to Person-'Account' within sys_data_generic branch)
DEF_CLIENT_OBJ = 'Account'


# client data maps for Lead, Contact and Account
SF_CLIENT_MAPS = \
    {'Account': (
        # ('AssCache_Id__pc', 'AssId'),
        ('AcumenClientRef__pc', 'AcuId'),
        ('Id', 'SfId'),                      # was Id but test_sys_data_sf.py needs lower case id, CHANGED BACK TO 'Id'
        ('SihotGuestObjId__pc', 'ShId'),
        ('LastName', 'Surname'),
        ('FirstName', 'Forename'),
        ('PersonEmail', 'Email'),
        ('PersonHomePhone', 'Phone'),
        ('RCI_Reference__pc', 'RciId'),     # TODO: add RCI_Reference__pc to SF.SihotRestInterface.doHttpPost()
        # ('KM_DOB__pc', 'DOB', None, None,
        #  lambda f, v: convert_date_from_sf(v), lambda f, v: convert_date_onto_sf(v)),
        ('PersonMailingStreet', 'Street'),
        ('PersonMailingCity', 'City'),
        # ('PersonMailingState', 'State'),
        ('PersonMailingPostalCode', 'Postal'),
        ('PersonMailingCountry', 'Country'),
        ('Language__pc', 'Language'),
        ('Nationality__pc', 'Nationality'),
        ('CurrencyIsoCode', 'Currency'),
        # ('Marketing_Source__pc', 'MarketSource'),
        # ('Previous_Arrival_Info__pc', 'ArrivalInfo')
     ),
     'Contact': (
         ('AssCache_Id__c', 'AssId'),
         ('AcumenClientRef__c', 'AcuId'),
         ('Id', 'SfId'),  # was Id but test_sys_data_sf.py needs lower case id, CHANGED BACK TO 'Id'
         ('Sihot_Guest_Object_Id__c', 'ShId'),
         ('LastName', 'Surname'),
         ('FirstName', 'Forename'),
         ('RCI_Reference__c', 'RciId'),
         ('DOB1__c', 'DOB', None, None,
          lambda f, v: convert_date_from_sf(v), lambda f, v: convert_date_onto_sf(v)),
         ('MailingStreet', 'Street'),
         ('MailingCity', 'City'),
         ('Country__c', 'Country'),
         ('Language__c', 'Language'),
         # ('Marketing_Source__c', 'MarketSource'),
         # ('Previous_Arrival_Info__c', 'ArrivalInfo')
     ),
     'Lead': (
         ('AssCache_Id__c', 'AssId'),
         ('Acumen_Client_Reference__c', 'AcuId'),
         ('Id', 'SfId'),  # was Id but test_sys_data_sf.py needs lower case id, CHANGED BACK TO 'Id'
         ('LastName', 'Surname'),
         ('FirstName', 'Forename'),
         ('DOB1__c', 'DOB', None, None,
          lambda f, v: convert_date_from_sf(v), lambda f, v: convert_date_onto_sf(v)),
         ('Nationality__c', 'Language'),
         # ('Market_Source__c', 'MarketSource'),
         # ('Previous_Arrivals__c', 'ArrivalInfo')
     )
     }  # type: Dict[str, Tuple[Tuple[Any, ...], ...]]

# Reservation Object fields
SF_RES_MAP = (
    ('HotelId__c', 'ResHotelId'),
    ('Number__c', 'ResId'),
    ('SubNumber__c', 'ResSubId'),
    ('GdsNo__c', 'ResGdsNo'),
    ('ReservationOpportunityId', 'ResSfId'),
    ('SihotResvObjectId__c', 'ResObjId'),
    ('Arrival__c', 'ResArrival', None, None,
     lambda f, v: convert_date_from_sf(v), lambda f, v: convert_date_onto_sf(v)),
    ('Departure__c', 'ResDeparture', None, None,
     lambda f, v: convert_date_from_sf(v), lambda f, v: convert_date_onto_sf(v)),
    ('RoomNo__c', 'ResRoomNo'),
    ('RoomCat__c', 'ResRoomCat'),
    ('Status__c', 'ResStatus'),
    ('MktGroup__c', 'ResMktGroup'),
    ('MktSegment__c', 'ResMktSegment'),
    ('Adults__c', 'ResAdults', None, None,
     lambda f, v: int(v)),
    ('Children__c', 'ResChildren', None, None,
     lambda f, v: int(v)),
    ('Note__c', 'ResNote'),
    # ('', ('ResPersons', 0, 'PersAcuId')),
    # ('', ('ResPersons', 0, 'PersDOB')),
    # ('', ('ResPersons', 0, 'PersForename')),
    # ('', ('ResPersons', 0, 'PersShId')),
    # ('', ('ResPersons', 0, 'PersSurname')),
    # ('', ('ResPersons', 0, 'RoomNo')),
    # ('', ('ResPersons', 0, 'TypeOfPerson')),
)  # type: Tuple[Tuple[Any, ...], ...]

# Allocation Object fields
SF_ROOM_MAP = (
    ('CheckIn__c', 'ResCheckIn', None, None,
     lambda f, v: convert_date_time_from_sf(v), lambda f, v: convert_date_time_onto_sf(v)),
    ('CheckOut__c', 'ResCheckOut'),
)  # type: Tuple[Tuple[Any, ...], ...]

# from Sf rec map (used e.g. by SihotServer)
''' - NOT NEEDED BECAUSE SAME FIELD NAMES (see SihotServer.py/sh_res_action())
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
    ('ResPersons0Surname', ('ResPersons', 0, 'PersSurname')),
)
'''

# sf address field type/length - taken from https://developer.salesforce.com/forums/?id=906F00000008ih6IAA
"""
    Address.Street      (TextArea, 255)
    Address.City        (String,    40)
    Address.State       (String,    80)
    Address.PostalCode  (String,    20)
    Address.Country     (String,    80)
"""

# SF ID prefixes for to determine SF object (s.a. Sf object describe 'keyPrefix')
ID_PREFIX_OBJECTS = {'001': 'Account', '003': 'Contact', '00Q': 'Lead', '006': 'Opportunity'}


# default search fields for external systems (used by sys_data_sf.cl_field_data())
SF_DEF_SEARCH_FIELD = 'SfId'


ppf = pprint.PrettyPrinter(indent=12, width=96, depth=9).pformat


def add_sf_options(cae):
    cae.add_opt('sfUser', "Salesforce account user name", '', 'y')
    cae.add_opt('sfPassword', "Salesforce account user password", '', 'a')
    cae.add_opt('sfToken', "Salesforce account token string", '', 'o')
    cae.add_opt(SDF_SF_SANDBOX, "Use Salesforce sandbox (instead of production)", True, 's')


# date/datetime formats used for calling interface and SOQL queries (SOQL queries are using different format!!!)
SF_DATE_FORMAT = DATE_ISO
SF_DATE_TIME_FORMAT_FROM = '%Y-%m-%dT%H:%M:%S.%f%z'
SF_DATE_TIME_FORMAT_ONTO = '%Y-%m-%d %H:%M:%S'
''' TODO: remove on code-clean-up
# no longer needed since changed company+user time zone to GMT+0: SF_TIME_DIFF_FROM = datetime.timedelta(hours=1)
# no longer needed since using Date.valueOf() in SF: SF_DATE_ZERO_HOURS = " 00:00:00"
'''


def convert_date_from_sf(str_val):
    return parse_date(str_val, SF_DATE_FORMAT, ret_date=True)


def convert_date_onto_sf(date):
    return date.strftime(SF_DATE_FORMAT)    # no longer needed since using Date.valueOf() in SF: + SF_DATE_ZERO_HOURS


def convert_date_time_from_sf(str_val):
    return parse_date(str_val, SF_DATE_TIME_FORMAT_FROM, replace=dict(microsecond=0, tzinfo=None))


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


def soql_value_literal(val):
    if isinstance(val, datetime.date):
        val = val.strftime(SF_DATE_FORMAT)
    elif isinstance(val, datetime.datetime):
        val = convert_date_time_onto_sf(val)
    elif isinstance(val, int):
        val = str(val)
    else:
        val = "'" + str(val) + "'"
    return val


def obj_from_id(sf_id):
    return ID_PREFIX_OBJECTS.get(sf_id[:3], DEF_CLIENT_OBJ)


def ensure_long_id(sf_id):
    """
    ensure that the passed sf_id will be returned as a 18 character Salesforce ID (if passed in as 15 character SF ID).

    :param sf_id:   any valid (15 or 18 character long) SF ID.
    :return:        18 character SF ID if passed in as 15 or 18 character ID - other SF ID lengths/values returns None.
    """
    if not sf_id:
        return None
    elif len(sf_id) == 18:
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


def sf_field_name(sf_fld, sf_obj):
    field_map = SF_CLIENT_MAPS.get(sf_obj, tuple())
    for sys_name, fld_name in field_map:
        if sys_name == sf_fld:
            field_name = fld_name
            break
    else:
        field_name = sf_fld
    return field_name


def sf_fld_sys_name(field_name, sf_obj):
    field_map = SF_CLIENT_MAPS.get(sf_obj, tuple())
    for sys_name, fld_name, *_ in field_map:
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
            field_dict[sf_field_name(sf_fld, sf_obj)] = val
    return field_dict


def field_list_to_sf(field_names, sf_obj):
    sf_list = list()
    for field_name in field_names:
        sf_list.append(sf_fld_sys_name(field_name, sf_obj))
    return sf_list


'''
def rec_to_sf_obj_fld_dict(rec, sf_obj):
    sf_dict = dict()
    for idx in rec.leaf_indexes():
        sf_key = sf_fld_sys_name(idx_path_field_name(idx), sf_obj)
        sf_dict[sf_key] = rec.val(idx)
    return sf_dict
'''


def _format_exc(ex):    # wrapper because SimpleSalesforce is throwing exception in relation with formatting his objects
    try:
        exc_msg = format_exc(ex)
    except Exception as fex:
        exc_msg = str(ex) + '\n      ' + str(fex)
    return exc_msg


class SfInterface:
    def __init__(self, credentials, features=None, app_name='', debug_level=DEBUG_LEVEL_DISABLED):
        """
        create instance of generic database object (base class for real database like e.g. postgres or oracle).
        :param credentials: dict with account credentials ('CredItems' cfg), including User=user name, Password=user
                            password and DSN=database name and optionally host address (separated with a @ character).
        :param features:    optional list of features (currently only used for SDF_SF_SANDBOX/'sfIsSandbox').
        :param app_name:    application name (shown in the server DB session).
        :param debug_level: debug level.
        """
        # store user credentials for lazy Salesforce connect (only if needed) because of connection limits and timeouts
        self._conn = None
        self._user = credentials.get('User')
        self._pw = credentials.get('Password')
        self._tok = credentials.get('Token')
        self._sb = features and SDF_SF_SANDBOX + '=True' in features \
            or 'test' in self._user.lower() or 'dbx' in self._user.lower()
        self._client = app_name
        self._debug_level = debug_level

        self.error_msg = ""
        self.cl_res_rec_onto = Record(system=SDI_SF, direction=FAD_ONTO)
        self.cl_res_rec_onto.add_system_fields(SF_CLIENT_MAPS['Account'] + SF_RES_MAP)

    @property
    def is_sandbox(self):
        return self._sb

    def _connect(self):
        try:
            self._conn = Salesforce(username=self._user, password=self._pw, security_token=self._tok,
                                    sandbox=self._sb, client_id=self._client)
            if self._debug_level >= DEBUG_LEVEL_ENABLED:
                po("  ##  Connection to Salesforce established with session id {}".format(self._conn.session_id))
        except SalesforceAuthenticationFailed as sf_ex:
            self.error_msg = "SfInterface._connect(): Salesforce {} authentication failed with exception: {}" \
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
                self.error_msg = "Invalid Salesforce login - {}; last error={}".format(msg, self.error_msg)
            po(self.error_msg)
            return False
        self.error_msg = ""

        if not self._conn:
            self.error_msg = ""
            self._connect()
            if self.error_msg:
                if self._debug_level >= DEBUG_LEVEL_VERBOSE:
                    po("  **  _ensure_lazy_connect() err={}".format(self.error_msg))
                return None

        if self._conn:
            try:
                return self._conn.query_all(soql_query)
            except SalesforceExpiredSession:
                po("  ##  SfInterface._ensure_lazy_connect(): Trying re-connecting expired Salesforce session...")
                self._conn = None
                return self._ensure_lazy_connect(soql_query)

        if not self.error_msg:
            self.error_msg = "SfInterface._ensure_lazy_connect(): Reconnection to Salesforce failed"
            po(" ***  " + self.error_msg)

        return None

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
            self.error_msg += "SfInterface.apex_call({}, {}) exception='{}'\n{}"\
                .format(function_name, function_args, ex, _format_exc(ex))
            result = dict(sfif_apex_error=self.error_msg)

        return result

    def soql_query_all(self, soql_query):
        """
        Query Salesforce cloud objects/tables with SOQL.
        This method is tight coupled with the _ensure_lazy_connect() method above - using it for to execute the
        query and doing a connection expiration check at the same time.

        :param soql_query:      SOQL query as string.
        :return:                response dict from Salesforce or None on error.
        """
        response = None
        try:
            response = self._ensure_lazy_connect(soql_query)
        except Exception as sf_ex:
            self.error_msg += "SfInterface.soql_query_all({}) query exception: {}".format(soql_query, sf_ex)
        if response is None:
            self.error_msg += "SfInterface.soql_query_all({}) SimpleSalesforce.query_all() -> None".format(soql_query)
        elif isinstance(response, dict) and not response.get('done'):
            self.error_msg += "SfInterface.soql_query_all(): Salesforce is responding that query {} is NOT done." \
                .format(soql_query)

        if self._debug_level >= DEBUG_LEVEL_VERBOSE:
            po("soql_query_all({}) response={}".format(soql_query, response))

        return response

    def ssf_object(self, sf_obj):
        if not self._ensure_lazy_connect():
            return None
        client_obj = getattr(self._conn, sf_obj, None)
        if not client_obj:
            self.error_msg = "SfInterface.ssf_object({}) called with invalid salesforce object type".format(sf_obj)
        return client_obj

    def record_type_id(self, sf_obj, dev_name=None):
        if not dev_name:
            # salesforce record types for newly created Lead/Contact/Account/Opportunity objects
            # .. alternatively use 'Service_Center_Booking' for lead reservation opportunities
            dev_name = dict(Lead='SIHOT_Leads', Contact='Rentals', Account='PersonAccount',
                            Opportunity='Sihot_Generated').get(sf_obj)
        rec_type_id = None
        res = self.soql_query_all("Select Id From RecordType Where SobjectType = '{}' and DeveloperName = '{}'"
                                  .format(sf_obj, dev_name))
        if not self.error_msg and res['totalSize'] > 0:
            rec_type_id = res['records'][0]['Id']
        return rec_type_id

    ''' NO LONGER IMPLEMENTED WITHIN SF
    def find_client(self, email="", phone="", first_name="", last_name=""):
        service_args = dict(email=email, phone=phone, firstName=first_name, lastName=last_name)
        result = self.apex_call('clientsearch', function_args=service_args)

        if self._debug_level >= DEBUG_LEVEL_VERBOSE:
            po("find_client({}, {}, {}, {}) result={}".format(email, phone, first_name, last_name, ppf(result)))

        if self.error_msg or 'Id' not in result or 'type' not in result:
            return '', DEF_CLIENT_OBJ

        return result['Id'], result['type']
    '''

    def cl_delete(self, sf_id, sf_obj=None):
        if not self._ensure_lazy_connect():
            return self.error_msg, ""

        if sf_obj is None:
            sf_obj = obj_from_id(sf_id)

        client_obj = self.ssf_object(sf_obj)
        if not client_obj:
            self.error_msg += " cl_delete() id={}".format(sf_id)
            return self.error_msg, ""

        msg = ""
        try:
            sf_ret = client_obj.delete(sf_id)
            msg = "{} {} deleted, status=\n{}".format(sf_obj, sf_id, ppf(sf_ret))
        except Exception as ex:
            self.error_msg = "{} {} deletion raised exception {}".format(sf_obj, sf_id, ex)

        return self.error_msg, msg

    def cl_ext_refs(self, sf_client_id, er_type=None, er_id=None, return_obj_id=False, sf_obj=None):
        """
        Return external references of client specified by sf_client_id (and optionally sf_obj).

        :param sf_client_id:    Salesforce Id of client record (Lead, Contact, Account, PersonAccount, ...).
        :param er_type:         Type of external reference (e.g. EXT_REF_TYPE_RCI), pass None/nothing for all types.
        :param er_id:           External reference No or Id string, pass None for to get all external reference Ids.
        :param return_obj_id:   Pass True to get the SF Ids of the External_Ref object (Def=External Reference Ids).
        :param sf_obj:          Salesforce object of the client passed into sf_client_id (Lead, Contact, Account, ...).
        :return:                If er_type get passed in then: list of SF_IDs
                                Else: list of tuples of found external ref type and SF_IDs;
                                If return_obj_id==False then: SF_IDs will be the external reference Ids
                                Else: SF_IDs will be the Salesforce object Ids of external references object.
        """
        id_name = 'Id' if return_obj_id else 'Reference_No_or_ID__c'
        if sf_obj is None:
            sf_obj = obj_from_id(sf_client_id)

        ext_refs = list()
        soql = "SELECT Name, {} FROM External_Ref__c  WHERE {}__c = '{}'"\
            .format(id_name, sf_obj, sf_client_id)
        if er_type and er_id:
            soql += " AND Name = '{}{}{}'".format(er_type, EXT_REF_TYPE_ID_SEP, er_id)
        elif er_type:
            soql += " AND Name LIKE '{}{}%'".format(er_type, EXT_REF_TYPE_ID_SEP)
        elif er_id:
            soql += " AND Reference_No_or_ID__c = '{}'".format(er_id)
        res = self.soql_query_all(soql)
        if not self.error_msg and res['totalSize'] > 0:
            for c in res['records']:
                ext_refs.append(c[id_name] if er_type else (c['Name'].split(EXT_REF_TYPE_ID_SEP)[0], c[id_name]))
        return ext_refs

    def cl_ext_ref_upsert(self, sf_client_id, er_type, er_id, sf_obj=None, upd_rec=None):
        """
        insert or update external reference for a client.
        :param sf_client_id:    SF Id of Contact/Account for to upsert external reference.
        :param er_type:         External reference type to insert/update.
        :param er_id:           External reference Id to insert/update.
        :param sf_obj:          SF client object (Contact or Account). Def=determined from sf_client_id.
        :param upd_rec:         Record with one of the fields Type, Id, which is only used if external reference
                                specified by sf_client_id+er_type+er_id exists as the new er_type/er_id value.
        :return:
        """
        if not self._ensure_lazy_connect():
            return None, self.error_msg, ""

        if not sf_client_id or not er_type or not er_id:
            self.error_msg += " cl_ext_ref_upsert() expects non-empty client id and external reference type and id"
            return None, self.error_msg, ""

        er_obj = 'External_Ref__c'
        ext_ref_obj = self.ssf_object(er_obj)
        if not ext_ref_obj:
            self.error_msg += " cl_ext_ref_upsert() sf_id={}, er_id={}".format(sf_client_id, er_id)
            return None, self.error_msg, ""

        if sf_obj is None:
            sf_obj = obj_from_id(sf_client_id)
        sf_dict = dict(Reference_No_or_ID__c=er_id, Name=er_type + EXT_REF_TYPE_ID_SEP + er_id)
        sf_dict[sf_obj + '__c'] = sf_client_id
        sf_er_id = err = msg = ""
        er_list = self.cl_ext_refs(sf_client_id, er_type, er_id, return_obj_id=True, sf_obj=sf_obj)
        if er_list:     # update?
            if self._debug_level >= DEBUG_LEVEL_VERBOSE and len(er_list) > 1:
                po("cl_ext_ref_upsert({}): duplicate external refs found:\n{}".format(sf_client_id, ppf(er_list)))
            sf_er_id = er_list[0]
            if upd_rec:
                new_id = upd_rec.val('Id') or sf_dict['Name'].split(EXT_REF_TYPE_ID_SEP)[1]
                if upd_rec.val('Type'):
                    sf_dict['Name'] = upd_rec.val('Type') + EXT_REF_TYPE_ID_SEP + new_id
                sf_dict['Reference_No_or_ID__c'] = new_id
            try:
                sf_ret = ext_ref_obj.update(sf_er_id, sf_dict)
                msg = "{} {} updated with {} ret=\n{}".format(er_obj, sf_er_id, ppf(sf_dict), ppf(sf_ret))
            except Exception as ex:
                err = "{} update() raised exception {}. msg={}; sent={}".format(er_obj, ex, msg, ppf(sf_dict))
        else:
            try:
                sf_ret = ext_ref_obj.create(sf_dict)
                msg = "{} created with {}, ret=\n{}".format(er_obj, ppf(sf_dict), ppf(sf_ret))
                if sf_ret['success']:
                    sf_er_id = sf_ret.get('Id') or sf_ret.get('id')     # TODO: fix UGLY lowercase API field name
            except Exception as ex:
                err = "{} create() exception {}. msg={}; sent={}".format(er_obj, ex, msg, ppf(sf_dict))

        if err:
            if self._debug_level >= DEBUG_LEVEL_VERBOSE:
                po("  **  cl_ext_ref_upsert({}) err={}".format(sf_client_id, err))
            self.error_msg = err

        return sf_er_id, err, msg

    def cl_field_data(self, fetch_fields, search_value, search_val_deli="'", search_op='=',
                      search_field=SF_DEF_SEARCH_FIELD, sf_obj=None,
                      log_warnings=None):
        """
        fetch field data from SF object (identified by sf_obj) and client (identified by search_value/search_field).
        :param fetch_fields:    either pass single field name (str) or list of field names of value(s) to be returned.
        :param search_value:    value for to identify client record.
        :param search_val_deli: delimiter used for to enclose search value within SOQL query.
        :param search_op:       search operator (between search_field and search_value).
        :param search_field:    field name used for to identify client record (def=SF_DEF_SEARCH_FIELD=='SfId').
        :param sf_obj:          SF object to be searched (def=determined by the passed SF ID prefix).
        :param log_warnings:    pass list for to append warning log entries on re-search on old/redirected SF IDs.
        :return:                either single field value (if fetch_fields is str) or dict(fld=val) of field values.
        """
        msg = " in cl_field_data(); {}, {}, {}".format(fetch_fields, search_value, search_field)
        if sf_obj is None:
            if search_field not in (SF_DEF_SEARCH_FIELD, 'External_Id__c', 'Contact_Ref__c', 'Id_before_convert__c',
                                    'CSID__c'):
                self.error_msg = "client object cannot be determined without Id" + msg
                return None
            sf_obj = obj_from_id(search_value)
            if not sf_obj:
                self.error_msg = "search_value is not a valid Lead/Contact/Account SF ID" + msg
                return None

        ret_dict = isinstance(fetch_fields, list)
        if ret_dict:
            select_fields = ", ".join(field_list_to_sf(fetch_fields, sf_obj))
            fetch_field = None  # only needed for to remove PyCharm warning
            ret_val = dict()
        else:
            select_fields = fetch_field = sf_fld_sys_name(fetch_fields, sf_obj)
            ret_val = None
        soql_query = "SELECT {} FROM {} WHERE {} {} {}{}{}" \
            .format(select_fields, sf_obj,
                    sf_fld_sys_name(search_field, sf_obj), search_op, search_val_deli, search_value, search_val_deli)
        res = self.soql_query_all(soql_query)
        if self.error_msg:
            self.error_msg += msg
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
            log_warnings.append("{} ID {} not found in SF{}".format(sf_obj, search_value, msg))
            if sf_obj == 'Lead':
                # try to find this Lead Id in the Lead field External_Id__c
                ret_val = self.cl_field_data(fetch_fields, search_value, search_field='External_Id__c')
                if not ret_val:
                    ret_val = self.cl_field_data(fetch_fields, search_value, search_field='CSID__c')
                    if not ret_val:
                        log_warnings.append("{} ID {} not found in Lead fields External_Id__c/CSID__c{}"
                                            .format(sf_obj, search_value, msg))
            elif sf_obj == 'Contact':
                # try to find this Contact Id in the Contact fields Contact_Ref__c, Id_before_convert__c
                ret_val = self.cl_field_data(fetch_fields, search_value, search_field='Contact_Ref__c')
                if not ret_val:
                    ret_val = self.cl_field_data(fetch_fields, search_value, search_field='Id_before_convert__c')
                    if not ret_val:
                        log_warnings.append("{} ID {} not found in Contact fields Contact_Ref__c/Id_before_convert__c{}"
                                            .format(sf_obj, search_value, msg))

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
                chk_val = self.cl_field_data(fetch_fields, search_value, sf_obj='Account')
                if chk_val:
                    ret_val = chk_val
        """
        return ret_val

    def cl_ass_id(self, sf_client_id, sf_obj=None):
        return self.cl_field_data('AssId', sf_client_id, sf_obj=sf_obj)

    def cl_ac_id(self, sf_client_id, sf_obj=None):
        return self.cl_field_data('AcuId', sf_client_id, sf_obj=sf_obj)

    def cl_sh_id(self, sf_client_id, sf_obj=None):
        return self.cl_field_data('ShId', sf_client_id, sf_obj=sf_obj)

    def cl_id_by_email(self, email, sf_obj=DEF_CLIENT_OBJ):
        return self.cl_field_data('SfId', email, search_field='Email', sf_obj=sf_obj)

    def cl_upsert(self, rec, sf_obj=None, filter_fields=None):
        # check if Id passed in (then this method can determine the sf_obj and will do an update not an insert)
        sf_id, update_client = (rec.pop(SF_DEF_SEARCH_FIELD).val(), True) if rec.val(SF_DEF_SEARCH_FIELD) else \
            ('', False)
        msg = f" in sys_data_sf.cl_upsert() {ACTION_UPDATE if update_client else ACTION_INSERT} rec=\n{ppf(rec)}"

        if sf_obj is None:
            if not sf_id:
                self.error_msg = "missing client object or Id{}".format(msg)
                return None, self.error_msg, ""
            sf_obj = obj_from_id(sf_id)

        client_obj = self.ssf_object(sf_obj)
        if not client_obj:
            self.error_msg += "\n      +empty {} client object{}".format(sf_obj, msg)
            return None, self.error_msg, ""

        sf_dict = rec.to_dict(system=SDI_SF, direction=FAD_ONTO, filter_fields=filter_fields)
        err = msg = ""
        if update_client:
            try:
                sf_ret = client_obj.update(sf_id, sf_dict)
                msg = "{} {} updated with {}, ret=\n{}".format(sf_obj, sf_id, ppf(sf_dict), ppf(sf_ret))
            except Exception as ex:
                err = "{} update() raised exception {}. sent=\n{}".format(sf_obj, _format_exc(ex), ppf(sf_dict))
                sf_id = None
        else:
            try:
                sf_ret = client_obj.create(sf_dict)
                msg = "{} created with {}, ret=\n{}".format(sf_obj, ppf(sf_dict), ppf(sf_ret))
                if sf_ret['success']:
                    fld_name = sf_fld_sys_name(SF_DEF_SEARCH_FIELD, sf_obj)
                    sf_id = sf_ret.get(fld_name) or sf_ret.get(fld_name.lower())    # TODO: fix UGLY lowercase API name
            except Exception as ex:
                err = "{} create() exception {}. sent={}".format(sf_obj, _format_exc(ex), ppf(sf_dict))
                sf_id = None

        if not err and sf_id:
            if not rec.val(SF_DEF_SEARCH_FIELD):
                rec.set_val(sf_id, SF_DEF_SEARCH_FIELD)
            if rec.val('RciId'):
                _, err, er_msg = self.cl_ext_ref_upsert(sf_id, EXT_REF_TYPE_RCI, rec.val('RciId'), sf_obj=sf_obj)
                msg += ("\n      " if msg else "") + er_msg
            if not err and rec.val('ExtRefs'):
                for er_rec in rec.val('ExtRefs'):
                    _, err, er_msg = self.cl_ext_ref_upsert(sf_id, er_rec.val('Type'), er_rec.val('Id'), sf_obj=sf_obj)
                    if err:
                        break
                    msg += ("\n      " if msg else "") + er_msg

        if err:
            self.error_msg = err

        return sf_id, err, msg

    REF_TYPE_ALL = 'all'
    REF_TYPE_MAIN = 'main'
    REF_TYPE_EXT = 'external'

    def cl_by_rci_id(self, rci_ref, sf_id=None, dup_clients=None, which_ref=REF_TYPE_ALL, sf_obj=DEF_CLIENT_OBJ):
        if not dup_clients:
            dup_clients = list()
        if which_ref in (self.REF_TYPE_MAIN, self.REF_TYPE_ALL):
            fld_name = sf_fld_sys_name(SF_DEF_SEARCH_FIELD, sf_obj)
            soql_query = "SELECT {} FROM {} WHERE {} = '{}'".format(fld_name, sf_obj, sf_fld_sys_name('RciId', sf_obj),
                                                                    rci_ref)
        else:  # which_ref == REF_TYPE_EXT
            fld_name = '{}__c'.format(sf_obj)
            soql_query = "SELECT {} FROM External_Ref__c WHERE Reference_No_or_ID__c = '{}'".format(fld_name, rci_ref)
        res = self.soql_query_all(soql_query)
        if self.error_msg:
            self.error_msg = "cl_by_rci_id({}): ".format(rci_ref) + self.error_msg
        elif res['totalSize'] > 0:
            if fld_name not in res['records'][0]:
                fld_name = fld_name.lower()        # TODO: fix UGLY lowercase API field name
            if not sf_id:
                sf_id = res['records'][0].get(fld_name)
            if res['totalSize'] > 1:
                new_clients = [_[fld_name] for _ in res['records']]
                dup_clients = list(set([_ for _ in new_clients + dup_clients if _ and _ != sf_id]))

        if not self.error_msg and which_ref == self.REF_TYPE_ALL:
            sf_id, dup_clients = self.cl_by_rci_id(rci_ref, sf_id, dup_clients, self.REF_TYPE_EXT)

        return sf_id, dup_clients

    def clients_with_rci_id(self, ext_refs_sep=EXT_REFS_SEP, owner_rec_types=None, sf_obj=DEF_CLIENT_OBJ):
        if not owner_rec_types:
            owner_rec_types = list()
        soql_fields = ['SfId', 'AcuId', 'RciId', 'ShId', 'RecordType.Id',
                       "(SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE '{}%')"
                       .format(EXT_REF_TYPE_RCI)]
        sf_fields = field_list_to_sf(soql_fields, sf_obj)
        res = self.soql_query_all("SELECT {} FROM {}".format(", ".join(sf_fields), sf_obj))
        client_tuples = list()
        if self.error_msg:
            self.error_msg = "clients_with_rci_id(): " + self.error_msg
        elif res['totalSize'] > 0:
            for c in res['records']:  # filter out clients with RCI ref from SF-list of client OrderedDicts
                ext_refs = [c[sf_fld_sys_name('RciId', sf_obj)]] if c[sf_fld_sys_name('RciId', sf_obj)] else list()
                if c['External_References__r']:
                    ext_refs.extend([_['Reference_No_or_ID__c'] for _ in c['External_References__r']['records']])
                if ext_refs:
                    client_tuples.append((None,
                                          c[sf_fld_sys_name('AcuId', sf_obj)],
                                          c[sf_fld_sys_name(SF_DEF_SEARCH_FIELD, sf_obj)],
                                          c[sf_fld_sys_name('ShId', sf_obj)],
                                          ext_refs_sep.join(ext_refs),
                                          1 if c['RecordType']['Id'] in owner_rec_types else 0))
        return client_tuples

    def res_dict(self, res_opp_id):
        """
        fetch client+res data from SF Reservation Opportunity object (identified by res_opp_id)
        :param res_opp_id:  Reservation Opportunity Id value for to identify client reservation records.
        :return:            dict with sf_data.
        """
        res_list = self.res_fetch_list(chk_values=dict(ReservationOpportunityId=res_opp_id))
        if res_list:
            return res_list[0]

    def res_fetch_list(self, col_names=(), chk_values=None, where_group_order=""):
        msg = "res_fetch_list({}, {}, {}) ".format(col_names, chk_values, where_group_order)

        if not col_names:
            col_names = tuple([sn for sn, *_ in SF_CLIENT_MAPS['Account'] + SF_RES_MAP + SF_ROOM_MAP])

        cli_cols = ", ".join(["Account__r." + sn for sn, *_ in SF_CLIENT_MAPS['Account'] if sn in col_names])
        res_cols = ", ".join([sn for sn, *_ in SF_RES_MAP if sn != 'ReservationOpportunityId' and sn in col_names])
        alo_cols = ", ".join([sn for sn, *_ in SF_ROOM_MAP if sn in col_names])
        where = " AND ".join([('Opportunity__c' if k == 'ReservationOpportunityId' else k)
                              + " = " + soql_value_literal(v) for k, v in chk_values.items()])
        where += " AND " + "(" + where_group_order + ")" if where_group_order else ""

        soql_query = "SELECT Id, Opportunity__c" \
                     + (", " + cli_cols if cli_cols else "") \
                     + (", " + res_cols if res_cols else "") \
                     + (", " + "(SELECT Id" + ", " + alo_cols + " FROM Allocations__r)" if alo_cols else "") \
                     + " FROM Reservation__c" \
                     + (" WHERE " + where if where else "")

        res_list = list()
        res = self.soql_query_all(soql_query)
        if self.error_msg:
            self.error_msg = msg + "error: {}".format(self.error_msg)
        elif res['totalSize'] > 0:
            for sf_res_dict in res['records']:
                ret = dict()
                ret['ReservationId'] = sf_res_dict.pop('Id')
                ret['ReservationOpportunityId'] = sf_res_dict.pop('Opportunity__c')
                sf_res_dict.pop('attributes', None)

                if cli_cols and sf_res_dict.get('Account__r'):      # 'Account' does not exist if no Account associated
                    sf_res_dict['Account__r'].pop('attributes', None)
                    ret.update(sf_res_dict['Account__r'])
                    ret['PersonAccountId'] = ret.pop('Id', None)
                sf_res_dict.pop('Account__r', None)

                if alo_cols and sf_res_dict['Allocations__r'] and sf_res_dict['Allocations__r']['totalSize'] > 0:
                    ret.update(sf_res_dict['Allocations__r']['records'][0])
                    ret['AllocationId'] = ret.pop('Id')
                sf_res_dict.pop('Allocations__r', None)

                ret.update(sf_res_dict)
                res_list.append(ret)

        return res_list

    def res_upsert(self, cl_res_rec, filter_fields=None, push_onto=True, put_system_val=True):
        sf_args = cl_res_rec.to_dict(filter_fields=lambda f: (filter_fields(f) if filter_fields else False)
                                     # TODO: add RCI_Reference__pc to SihotRestInterface.doHttpPost(), then remove:
                                     or f.name() in ('RciId', ),
                                     push_onto=push_onto, put_system_val=put_system_val,
                                     system=SDI_SF, direction=FAD_ONTO)
        dbg = self._debug_level >= DEBUG_LEVEL_VERBOSE
        sf_id = sf_args.pop('Id', None)
        if sf_id:
            sf_args['PersonAccountId'] = sf_id
        sf_res_id = sf_args.get('ReservationOpportunityId')
        if not sf_res_id and sf_args.get('GdsNo__c', '').startswith('006'):
            sf_args['ReservationOpportunityId'] = sf_args['GdsNo__c']

        result = self.apex_call('reservation_upsert', function_args=sf_args)

        if dbg:
            po(f"... sys_data_sf.res_upsert() err?={self.error_msg}; sent=\n{ppf(sf_args)}, result=\n{ppf(result)}")

        if result.get('ErrorMessage'):
            msg = ppf(result) if dbg else result.get('ErrorMessage')
            self.error_msg += f"sys_data_sf.res_upsert() received err=\n{msg} from SF; rec=\n{ppf(cl_res_rec)}"
        if not self.error_msg:
            if not cl_res_rec.val('ResSfId') and result.get('ReservationOpportunityId'):
                cl_res_rec.set_val(result['ReservationOpportunityId'], 'ResSfId')
            elif cl_res_rec.val('ResSfId') != result.get('ReservationOpportunityId'):
                msg = "sys_data_sf.res_upsert() ResSfId discrepancy; sent={} received={}; cl_res_rec=\n{}"\
                       .format(cl_res_rec.val('ResSfId'), result.get('ReservationOpportunityId'), ppf(cl_res_rec))
                po(msg)
                if dbg:
                    self.error_msg += "\n      " + msg

        return result.get('PersonAccountId'), result.get('ReservationOpportunityId'), self.error_msg

    def room_change(self, res_sf_id, check_in, check_out, next_room_id):
        msg = "sys_data_sf.room_change({}, {}, {}, {})".format(res_sf_id, check_in, check_out, next_room_id)
        dbg = self._debug_level >= DEBUG_LEVEL_VERBOSE

        room_chg_data = dict(ReservationOpportunityId=res_sf_id, CheckIn__c=check_in, CheckOut__c=check_out,
                             RoomNo__c=next_room_id)
        result = self.apex_call('reservation_room_move', function_args=room_chg_data)

        if self.error_msg or result.get('ErrorMessage'):
            self.error_msg += "err=\n{} from SF in {}".format(ppf(result) if dbg else result.get('ErrorMessage'), msg)
        elif dbg:
            po(msg + " result=\n{}'".format(ppf(result)))

        return self.error_msg

    def room_data(self, res_opp_id):
        """
        fetch client+res+room data from SF Reservation Opportunity object (identified by res_opp_id)
        :param res_opp_id:  value for to identify client record.
        :return:            dict with sf_data.
        """
        sf_data = self.res_dict(res_opp_id)

        # TODO: implement generic sf_field_data() method for to be called by this method and cl_field_data()
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
            self.error_msg = "room_data({}): ".format(res_opp_id) + self.error_msg
        elif res['totalSize'] > 0:
            ret_all = res['records'][0]
            ret = dict(ReservationId=ret_all['Id'])
            ret.update(ret_all['Allocations__r']['records'][0])
            ret['AllocationId'] = ret.pop('Id')
            ret.pop('attributes', None)
            ret_val.update(ret)

        return ret_val

    def occupants_upsert(self, res_sf_id, ho_id, res_id, sub_id, send_occ,
                         sf_fields=('PersSurname', 'PersForename', 'PersDOB', 'TypeOfPerson')):
        msg = "sys_data_sf.occupants_upsert({}, {}, {}, {}, {})".format(res_sf_id, ho_id, res_id, sub_id, send_occ)
        dbg = self._debug_level >= DEBUG_LEVEL_VERBOSE

        sf_data = dict(ReservationOpportunityId=res_sf_id, HotelId__c=ho_id, Number__c=res_id, SubNumber__c=sub_id)
        for occ_idx, occ_rec in enumerate(send_occ):
            prefix = 'ResPersons' + str(occ_idx)
            for fld in sf_fields:
                sf_data[prefix + fld] = occ_rec.val(fld)

        result = self.apex_call('reservation_occupants_upsert', function_args=sf_data)
        if self.error_msg or result.get('ErrorMessage'):
            self.error_msg += "SF err=\n{} in {}".format(ppf(result) if dbg else result.get('ErrorMessage'), msg)
        elif dbg:
            po(msg + " send-data=\n{}; result=\n{}'".format(ppf(sf_data), ppf(result)))

        return self.error_msg
