import datetime
import pprint
import re
from traceback import format_exc
from typing import Dict, Any, Union, Tuple  # , Tuple

from sys_data_ids import (SDI_ASS, SDI_ACU, SDI_SF, SDI_SH,
                          EXT_REFS_SEP, EXT_REF_TYPE_ID_SEP, EXT_REF_TYPE_RCI,
                          DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, SDF_SF_SANDBOX,
                          ALL_AVAILABLE_RECORD_TYPES, ALL_AVAILABLE_SYSTEMS)
from ae_sys_data import correct_email, correct_phone, Records, Record, FAD_FROM, FAD_ONTO, UsedSystems, \
    string_to_records
from ae_db import OraDB, PostgresDB
from ae_console_app import uprint, DATE_ISO
from ae_notification import add_notification_options, init_notification
from acif import add_ac_options, ACU_CLIENT_MAP, onto_field_indexes, from_field_indexes, AcumenClient
from sfif import (add_sf_options, ensure_long_id, SfInterface, SF_RES_MAP, SF_CLIENT_MAPS,
                  sf_fld_sys_name, SF_DEF_SEARCH_FIELD, soql_value_literal)
from sxmlif import AvailCatInfo
from shif import (add_sh_options, print_sh_options, gds_no_to_ids, res_no_to_ids, obj_id_to_res_no,
                  ClientSearch, ResSearch, ResFetch, ResBulkFetcher, ShInterface, SH_CLIENT_MAP, ClientToSihot,
                  SH_RES_MAP, ResToSihot, ClientFetch)


'''
# tuple indexes for Clients data list (ass_cache.clients/AssSysData.clients)
_ASS_ID = 0
_AC_ID = 1
_SF_ID = 2
_SH_ID = 3
_NAME = 4
_EMAIL = 5
_PHONE = 6
_EXT_REFS = 7
_PRODUCTS = 8
'''

# ass_cache client rec map (columns ordered like in the view v_clients_refs_owns)
ASS_CLIENT_MAP = (
    ('cl_pk', 'AssId'),
    ('cl_ac_id', 'AcuId'),
    ('cl_sf_id', 'SfId'),
    ('cl_sh_id', 'ShId'),
    ('cl_email', 'Email'),
    ('cl_phone', 'Phone'),
    ('cl_surname', 'Surname'),
    ('cl_firstname', 'Forename'),
    ('ext_refs', 'ExtRefs', None,
     None,
     lambda f, v: f.string_to_records(v, ('Type', 'Id'), rec_sep=EXT_REFS_SEP, fld_sep=EXT_REF_TYPE_ID_SEP)),
    ('owns', 'ProductTypes'),
)  # type: Tuple[Tuple[Any, ...], ...]


# ass_cache res_groups/res_group_clients rec map
ASS_RES_MAP = (
    ('rgr_pk', 'ResAssId'),
    ('rgr_order_cl_fk', 'AssId'),
    ('rgr_used_ri_fk', 'RinId'),
    ('rgr_ho_fk', 'ResHotelId'),
    ('rgr_res_id', 'ResId'),
    ('rgr_sub_id', 'ResSubId'),
    ('rgr_gds_no', 'ResGdsNo'),
    ('rgr_sf_id', 'ResSfId'),
    ('rgr_obj_id', 'ResObjId'),
    ('rgr_status', 'ResStatus'),
    ('rgr_source', 'ResSource'),
    ('rgr_arrival', 'ResArrival'),
    ('rgr_departure', 'ResDeparture'),
    ('rgr_room_id', 'ResRoomNo'),
    ('rgr_room_cat_id', 'ResRoomCat'),
    ('rgr_mkt_group', 'ResMktGroup'),
    ('rgr_mkt_segment', 'ResMktSegment'),
    ('rgr_group_no', 'ResGroupNo'),
    ('rgr_sh_pack', 'ResBoard'),
    ('rgr_adults', 'ResAdults'),
    ('rgr_children', 'ResChildren'),
    ('rgr_comment', 'ResNote'),
    ('rgr_time_in', 'ResCheckIn'),
    ('rgr_time_out', 'ResCheckOut'),
    ('rgr_ext_book_id', 'ResVoucherNo'),
    ('rgr_ext_book_day', 'ResBooked'),
    ('rgr_long_comment', 'ResLongNote'),
    ('rgr_room_rate', 'ResRateSegment'),
    ('rgr_payment_inst', 'ResAccount'),
    # ('rgc_rgr_fk', 'ResAssId'),
    ('rgc_occup_cl_fk', ('ResPersons', 0, 'PersAssId')),
    ('rgc_room_seq', ('ResPersons', 0, 'RoomSeq')),
    ('rgc_pers_seq', ('ResPersons', 0, 'RoomPersSeq')),
    ('rgc_surname', ('ResPersons', 0, 'PersSurname')),
    ('rgc_firstname', ('ResPersons', 0, 'PersForename')),
    ('rgc_email', ('ResPersons', 0, 'PersEmail')),
    ('rgc_phone', ('ResPersons', 0, 'PersPhone')),
    ('rgc_language', ('ResPersons', 0, 'PersLanguage')),
    ('rgc_country', ('ResPersons', 0, 'PersCountry')),
    ('rgc_dob', ('ResPersons', 0, 'PersDOB')),
    ('rgc_auto_generated', ('ResPersons', 0, 'AutoGen')),
    ('rgc_flight_arr_comment', ('ResPersons', 0, 'FlightArrComment')),
    ('rgc_flight_arr_time', ('ResPersons', 0, 'FlightETA')),
    ('rgc_flight_dep_comment', ('ResPersons', 0, 'FlightDepComment')),
    ('rgc_flight_dep_time', ('ResPersons', 0, 'FlightETD')),
    ('rgc_pers_type', ('ResPersons', 0, 'TypeOfPerson')),
    ('rgc_sh_pack', ('ResPersons', 0, 'Board')),
    ('rgc_room_id', ('ResPersons', 0, 'RoomNo')),
)  # type: Tuple[Tuple[Any, ...], ...]


# Reservation Inventory data (ass_cache.res_inventories/AssSysData.reservation_inventories)
ASS_RIN_MAP = (
    ('ri_pk', 'RinId'),
    ('ri_pr_fk', 'RinProdId'),
    ('ri_ho_fk', 'RinHotelId'),
    ('ri_usage_year', 'RinUsageYear'),
    ('ri_inv_type', 'RinType'),
    ('ri_swapped_product_id', 'RinSwappedProdId'),
    ('ri_granted_to', 'RinGrantedTo'),
    ('ri_used_points', 'RinUsedPoints'),
    ('ri_usage_comment', 'RinUsageComment'),
)


ppf = pprint.PrettyPrinter(indent=9, width=96, depth=9).pformat


def add_ass_options(cae, client_port=None, add_kernel_port=False, break_on_error=False, bulk_fetcher=None):
    cae.add_option('assUser', "AssCache/Postgres user account name", '', 'U')
    cae.add_option('assPassword', "AssCache/Postgres user account password", '', 'P')
    cae.add_option('assDSN', "AssCache/Postgres database (and host) name (dbName[@host])", 'ass_cache', 'N')
    add_ac_options(cae)
    add_sf_options(cae)
    ass_options = dict()
    if bulk_fetcher == 'Res':
        ass_options['resBulkFetcher'] = ResBulkFetcher(cae)
        ass_options['resBulkFetcher'].add_options()
    else:
        add_sh_options(cae, client_port=client_port, add_kernel_port=add_kernel_port)
    if break_on_error:
        cae.add_option('breakOnError', "Abort processing if error occurs (0=No, 1=Yes)", 0, 'b', choices=(0, 1))
        ass_options['breakOnError'] = None
    add_notification_options(cae, add_warnings=True)

    return ass_options


def init_ass_data(cae, ass_options, err_logger=None, warn_logger=None, used_systems_msg_prefix=""):
    """ initialize system data/environment/configuration and print to stdout

    :param cae:                     application environment including command line options and config settings.
    :param ass_options:             ass options dict (returned by add_ass_options()).
    :param err_logger:              error logger method
    :param warn_logger:             warning logger method
    :param used_systems_msg_prefix  message prefix for display of used systems.
    :return:                        dict with initialized parts (e.g. AssSysData).
    """
    ret_dict = dict()

    ret_dict['assSysData'] = asd = AssSysData(cae, err_logger=err_logger, warn_logger=warn_logger,
                                              sys_msg_prefix=used_systems_msg_prefix)
    sys_ids = list()
    if asd.connection(SDI_ASS, raise_if_error=False):
        uprint('AssCache database name and user:', cae.get_option('assDSN'), cae.get_option('assUser'))
        sys_ids.append(cae.get_option('assDSN'))
    if asd.connection(SDI_ACU, raise_if_error=False):
        uprint('Acumen database TNS and user:', cae.get_option('acuDSN'), cae.get_option('acuUser'))
        sys_ids.append(cae.get_option('acuDSN'))
    if asd.connection(SDI_SF, raise_if_error=False):
        sf_sandbox = SDF_SF_SANDBOX + '=True' in asd.used_systems[SDI_SF].features
        uprint("Salesforce " + ("sandbox" if sf_sandbox else "production") + " user/client-id:",
               cae.get_option('sfUser'))
        sys_ids.append("SBox" if sf_sandbox else "Prod")
    if asd.connection(SDI_SH, raise_if_error=False):
        print_sh_options(cae)
        sys_ids.append(cae.get_option('shServerIP'))
    ret_dict['sysIds'] = sys_ids

    ret_dict['notification'], ret_dict['warningEmailAddresses'] = init_notification(cae, '/'.join(sys_ids))

    if 'resBulkFetcher' in ass_options:
        ass_options['resBulkFetcher'].load_options()
        ass_options['resBulkFetcher'].print_options()

    if 'breakOnError' in ass_options:
        break_on_error = cae.get_option('breakOnError')
        uprint('Break on error:', 'Yes' if break_on_error else 'No')
        ret_dict['breakOnError'] = break_on_error

    return ret_dict


'''
# Acumen, Salesforce and Sihot field name re-mappings
#   AssSysDataClientsIdx    AssSysData.clients columns/fields index (like fetched with view v_clients_refs_owns)
FIELD_NAMES = dict(AssId=dict(AssSysDataClientsIdx=_ASS_ID,
                              AssDb='cl_pk',
                              Lead='AssCache_Id__c', Contact='AssCache_Id__c', Account='AssCache_Id__pc',
                              Sihot=''),
                   AcuId=dict(AssSysDataClientsIdx=_AC_ID,
                             AssDb='cl_ac_id', AcDb='CD_CODE', Lead='Acumen_Client_Reference__c', Contact='CD_CODE__c',
                             Account='CD_CODE__pc', Sihot='MATCHCODE'),
                   SfId=dict(AssSysDataClientsIdx=_SF_ID,
                             AssDb='cl_sf_id', AcDb='CD_SF_ID1',
                             Lead='id', Contact='id', Account='id',     # was Id but test_sfif.py needs lower case id
                             Sihot='MATCH-SM'),
                   ShId=dict(AssSysDataClientsIdx=_SH_ID,
                             AssDb='cl_sh_id', AcDb='CD_SIHOT_OBJID', Lead='Sihot_Guest_Object_Id__c',
                             Contact='Sihot_Guest_Object_Id__c', Account='SihotGuestObjId__pc', Sihot='OBJID'),
                   Name=dict(AssSysDataClientsIdx=_NAME,
                             AssDb='cl_name', Sihot=dict(getter=lambda shd: shd['NAME-2'] + ' ' + shd['NAME-1'])),
                   Email=dict(AssSysDataClientsIdx=_EMAIL,
                              AssDb='cl_email', AcDb='CD_EMAIL', Account='PersonEmail',
                              Sihot=dict(in_list=['EMAIL-1', 'EMAIL-2'])),
                   Phone=dict(AssSysDataClientsIdx=_PHONE,
                              AssDb='cl_phone', AcDb='CD_HTEL1', Account='PersonHomePhone',
                              Sihot=dict(in_list=['PHONE-1', 'PHONE-2', 'MOBIL-1', 'MOBIL-2'])),
                   ExtRefs=dict(AssSysDataClientsIdx=_EXT_REFS),
                   Products=dict(AssSysDataClientsIdx=_PRODUCTS),
                   RciId=dict(Contact='RCI_Reference__c', Account='RCI_Reference__pc', Sihot='MATCH-ADM'),
                   FirstName=dict(),
                   LastName=dict(),
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
                   RecordType=dict(Lead='RecordType.DeveloperName', Contact='RecordType.DeveloperName',
                                   Account='RecordType.DeveloperName'),
                   )

'''


def _dummy_stub(msg, *args, **kwargs):
    uprint("******  Fallback call of ass_sys_data._dummy_stub() with:\n        msg='{}', args={}, kwargs={}"
           .format(msg, args, kwargs))


'''
USED_SYS_ASS_ID = 'Ass'
USED_SYS_ACU_ID = 'Acu'
USED_SYS_SF_ID = 'Sf'
USED_SYS_SHWEB_ID = 'Shweb'
USED_SYS_SHKERNEL_ID = 'Shkernel'
USED_SYS_ERR_MARKER = "**!"
'''


def list_idx_by_match_fields(searched_list, match_fields, match_values):
    for list_idx, rec in enumerate(searched_list):
        for idx, fn in enumerate(match_fields):
            if rec.val(fn) != match_values[idx]:
                break
        else:
            return list_idx


class AssSysData:   # Acumen, Salesforce, Sihot and config system data provider
    def __init__(self, cae, err_logger=None, warn_logger=None, ctx_no_file='', sys_msg_prefix="",
                 **sys_credentials):
        """
        initialize and possibly connect all available systems.

        :param cae:             app environment - mainly used for command line args and config file settings.
        :param err_logger:      method for to display or log error notifications.
        :param warn_logger:     method for to log warnings.
        :param ctx_no_file:     str prefix for to mark contexts with no file involved.
        :param sys_msg_prefix:  prefix str for to display the finally fully-configured/used systems.
        :param sys_credentials: credentials of all configured systems: ass_user, ass_password, acu_user, acu_password.
        """
        self.cae = cae
        self._err = err_logger or _dummy_stub
        self._warn = warn_logger or _dummy_stub
        self._ctx_no_file = ctx_no_file
        
        self.debug_level = cae.get_option('debugLevel')

        self.used_systems = UsedSystems(cae, SDI_ASS, SDI_ACU, SDI_SF, SDI_SH, **sys_credentials)
        self._crs = {SDI_ASS: PostgresDB, SDI_ACU: OraDB, SDI_SF: SfInterface, SDI_SH: ShInterface}
        self.error_message = self.used_systems.connect(self._crs, app_name=cae.app_name(), debug_level=self.debug_level)
        if self.error_message:
            self._err(self.error_message, self._ctx_no_file + 'ConnFailed')

        '''
        # if user credentials are specified then prepare Salesforce connection (non-permanent)
        self.sf_conn, self.sf_sandbox = None, True
        if cae.get_option('sfUser') and cae.get_option('sfPassword') and cae.get_option('sfToken'):
            self.used_systems.append(USED_SYS_SF_ID)
            self.sf_conn = prepare_connection(cae, verbose=False)
            if not self.sf_conn:
                self.error_message = "AssSysData: SF connection failed - please check account data and credentials"
                self._err(self.error_message, self._ctx_no_file + 'InitSfConn')
                self.used_systems[-1] += USED_SYS_ERR_MARKER
                return
            elif self.sf_conn.error_msg:
                self.error_message = self.sf_conn.error_msg
                self._err(self.error_message, self._ctx_no_file + 'InitSfErr')
                self.used_systems[-1] += USED_SYS_ERR_MARKER
                return
            self.sf_sandbox = self.sf_conn.is_sandbox

        # Sihot does also not provide permanent connection; at least prepare ClientSearch instance
        sh_features = dict()
        if cae.get_option('shServerIP') and cae.get_option(SDF_SH_WEB_PORT):
            sh_features[]
            self.used_systems.append(USED_SYS_SHWEB_ID)
        if cae.get_option('shServerIP') and cae.get_option(SDF_SH_KERNEL_PORT):
            self.used_systems.append(USED_SYS_SHKERNEL_ID)
        self.sh_conn = True
        self._guest_search = ClientSearch(cae)
        '''
        # load configuration settings (either from INI file or from Acumen)
        self.hotel_ids = cae.get_config('hotelIds')
        if self.hotel_ids:      # fetch config data from INI/CFG
            self.resort_cats = cae.get_config('resortCats')
            self.ap_cats = cae.get_config('apCats')
            self.ro_agencies = cae.get_config('roAgencies')
            self.room_change_max_days_diff = cae.get_config('roomChangeMaxDaysDiff', default_value=3)
        else:                   # fetch config data from Acumen
            db = self.connection(SDI_ACU, raise_if_error=False)
            if not db:      # logon/connect error
                self.error_message = "AssSysData: Missing credentials for to open Acumen database"
                self._err(self.error_message, self._ctx_no_file + 'InitAcuDb')
                return

            self.hotel_ids = self.load_view(db, 'T_LU', ['to_char(LU_NUMBER)', 'LU_ID'],
                                            "LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1")

            any_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_ANY'")
            bhc_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_BHC'")
            pbc_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_PBC'")
            bhh_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_BHH'")
            hmc_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_HMC'")
            # self.hotel_cats = {'999': any_cats, '1': bhc_cats, '4': pbc_cats, '2': bhh_cats, '3': hmc_cats}
            self.resort_cats = {'ANY': any_cats, 'BHC': bhc_cats, 'PBC': pbc_cats, 'BHH': bhh_cats, 'HMC': hmc_cats}

            self.ap_cats = self.load_view(db, 'T_AP, T_AT, T_LU', ['AP_CODE', 'AP_SIHOT_CAT'],
                                          "AP_ATREF = AT_CODE and AT_RSREF = LU_ID"
                                          " and LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1")

            self.ro_agencies = self.load_view(db, 'T_RO',
                                              ['RO_CODE', 'RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC',
                                               'RO_SIHOT_RATE', 'RO_RES_GROUP', 'RO_SIHOT_RES_GROUP'],
                                              "RO_SIHOT_AGENCY_OBJID is not NULL")

            self.room_change_max_days_diff = self.load_view(db, 'dual',
                                                            ["F_CONST_VALUE_NUM('k.SihotRoomChangeMaxDaysDiff')"])[0][0]

            db.close()

        self.client_refs_add_exclude = cae.get_config('ClientRefsAddExclude', default_value='').split(',')

        # load invalid email fragments (ClientHasNoEmail and OTA pseudo email fragments)
        self.invalid_email_fragments = cae.get_config('invalidEmailFragments', default_value=list())
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("Text fragments for to detect ignorable/invalid email addresses:", self.invalid_email_fragments)

        self.sf_id_reset_fragments = cae.get_config('SfIdResetResendFragments') or list()
        if self.sf_id_reset_fragments and self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint('Error fragments to re-sync res change with reset ResSfId:', self.sf_id_reset_fragments)

        self.mail_re = re.compile(r'[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,4}$')

        # --- contains pulled client data
        self.clients = Records()
        self.clients_changed = list()      # list indexes of changed records within self.clients

        # --- contains pulled reservation data
        self.reservations = Records()

        # --- caching banking/swap/grant info
        self.reservation_inventories = Records()

        # summary display of used systems
        if sys_msg_prefix or self.debug_level >= DEBUG_LEVEL_ENABLED:
            uprint((sys_msg_prefix or "Used systems") + ":", self.used_systems)

    def __del__(self):
        self.close_dbs()

    def is_test_system(self, raise_if_error=False):
        err_msg = self.error_message
        ass_db = self.connection(SDI_ASS, raise_if_error=raise_if_error)
        acu_db = self.connection(SDI_ACU, raise_if_error=raise_if_error)
        sf_conn = self.connection(SDI_SF, raise_if_error=raise_if_error)
        sh_conn = self.connection(SDI_SH, raise_if_error=raise_if_error)
        self.error_message = err_msg    # restore old error message (most likely empty string)

        return (ass_db and 'sihot3v' in self.cae.get_option('assDSN', default_value='')
                or acu_db and '.TEST' in self.cae.get_option('acuDSN', default_value='')
                or sf_conn and SDF_SF_SANDBOX + '=True' in self.used_systems[SDI_SF].features
                or sh_conn and 'sihot3v' in self.cae.get_option('shServerIP', default_value='')
                )

    def close_dbs(self):
        # ensure to close of DB connections (execution of auto-commits)
        return self.used_systems.disconnect()

    def connection(self, sys_id, raise_if_error=True):
        msg = "AssSysData.connection({}): ".format(sys_id)
        if not sys_id:
            msg += "empty system id"
        elif sys_id not in ALL_AVAILABLE_SYSTEMS:
            msg += "invalid system id"
        elif sys_id not in self.used_systems:
            msg += "unknown/unused system id"
        elif not self.used_systems[sys_id].connection:
            msg += "system is not connected/initialized"
        else:
            return self.used_systems[sys_id].connection

        if raise_if_error:
            self.error_message = msg
            raise ConnectionError(msg)

    def reconnect(self, sys_id):
        if sys_id in self.used_systems:
            self.used_systems[sys_id].connect(self._crs[sys_id],
                                              app_name=self.cae.app_name(),
                                              debug_level=self.debug_level,
                                              force_reconnect=True)

    def load_view(self, db_opt, view, cols=None, where="", bind_vars=None):
        if db_opt:      # use existing db connection if passed by caller
            db = db_opt
            self.error_message = ""
        else:
            db = self.connection(SDI_ACU, raise_if_error=False)
        if not self.error_message:
            self.error_message = db.select(view, cols, where_group_order=where, bind_vars=bind_vars)
        if self.error_message:
            self._err(self.error_message, self._ctx_no_file + 'LoadView')
            ret = None
        else:
            ret = db.fetch_all()
        if db and not db_opt:  # close temporary db connection if not passed by caller
            db.close()
        return ret

    # ############################  hotel/resort data helpers  ##################################################

    def cat_by_size(self, rs_or_ho_id, ap_size, ap_feats=None, allow_any=True):
        found = None
        variations = None       # removing PyCharm warning
        if ap_feats:  # optional list of apartment feature ids (AFT_CODEs)
            variations = 2 ** len(ap_feats)  # all possible ordered variations of apt features
            ap_feats = [str(ft) for ft in sorted(ap_feats)]
        if rs_or_ho_id in self.resort_cats:
            rs_list = [rs_or_ho_id]
        else:
            rs_list = [_[1] for _ in self.hotel_ids if _[0] == rs_or_ho_id]
        for resort in rs_list + (['ANY'] if rs_or_ho_id not in ('ANY', '999') and allow_any else list()):
            view = self.resort_cats[resort]
            if not view:
                continue
            key = ap_size
            if ap_feats:
                key += '_' + '_'.join(ap_feats)
            found = next((cols[1] for cols in view if cols[0] == key), None)

            if not found and ap_feats:
                for deg in range(variations - 1):
                    key = ap_size \
                          + ('' if variations - deg - 2 == 0 else '_') \
                          + '_'.join([ft for no, ft in enumerate(ap_feats) if 2 ** no & variations - deg - 2])
                    found = next((cols[1] for cols in view if cols[0] == key), None)
                    if found:
                        break

            if found:
                break

        return found

    def cat_by_room(self, room_no):
        if room_no:
            room_no = room_no.lstrip('0')  # remove leading zero from 3-digit PBC Sihot room number (if given)
        return next((cols[1] for cols in self.ap_cats if cols[0] == room_no), None)

    def ho_id_resort(self, ho_id):
        ac_res_id = None
        for sh_id, ac_id in self.hotel_ids:
            if sh_id == ho_id:
                ac_res_id = ac_id
                break
        return ac_res_id

    def ho_id_list(self, acu_rs_codes=None):
        if acu_rs_codes is None:
            hotel_id_list = [cols[0] for cols in self.hotel_ids]
        else:
            hotel_id_list = [cols[0] for cols in self.hotel_ids if cols[1] in acu_rs_codes]
        return hotel_id_list

    def email_is_valid(self, email_addr):
        if email_addr:
            email_addr = email_addr.lower()
            if self.mail_re.match(email_addr):
                for frag in self.invalid_email_fragments:
                    if frag in email_addr:
                        break  # email is invalid/filtered-out
                else:
                    return True
        return False

    # ############################  client data helpers  #########################################################

    def cl_fetch_list(self, col_names=(), chk_values=None, where_group_order="", bind_values=None):
        if "ORDER BY " not in where_group_order.upper():
            where_group_order += ("" if where_group_order else "1=1") + " ORDER BY cl_pk"

        ass_db = self.connection(SDI_ASS)
        if ass_db.select('v_clients_refs_owns', col_names, chk_values=chk_values,
                         where_group_order=where_group_order, bind_vars=bind_values):
            self.error_message = ass_db.last_err_msg
            rows = tuple()
        else:
            rows = ass_db.fetch_all()
            if ass_db.last_err_msg:
                self.error_message += ass_db.last_err_msg
        return rows

    def cl_save(self, client_data, field_names=None, match_fields=None, ass_idx=None,
                commit=False, locked_cols=None):
        """
        save/upsert client data into AssCache database.

        :param client_data:     Record or dict of client data (using generic field names).
        :param field_names:     list of generic field names to be saved in AssCache db (def=all fields in client_data).
        :param match_fields:    list of generic field names for rec match/lookup (def=non-empty AssId/AcuId/SfId/ShId).
        :param ass_idx:         self.clients list index of client record. If None/default then determine for to update
                                the self.clients cache list.
        :param commit:          boolean flag if AssCache data changes should be committed (def=False).
        :param locked_cols:     list of generic field names where the cl_ column value will be preserved if not empty.
        :return:                PKey/cl_pk of upserted AssCache client record or None on error (see self.error_message).
        """

        # normalize field values
        if not isinstance(client_data, Record):
            client_data = Record(fields=client_data, system=SDI_ASS, direction=FAD_ONTO)
            client_data.add_system_fields(ASS_CLIENT_MAP)
        for k, f in client_data.items():
            if k == 'SfId' and f.val():
                client_data[k] = ensure_long_id(f.val())
            elif 'Email' in k and f.val():
                if self.email_is_valid(f.val()):
                    client_data[k], _ = correct_email(f.val())
                else:
                    client_data[k] = ""
            elif 'Phone' in k and f.val():
                client_data[k], _ = correct_phone(f.val())

        # process and check parameters
        if not field_names:
            field_names = [k for k in client_data.keys() if k not in ('AssId', 'ExtRefs', 'ProductTypes')]
        col_values = {f.name(system=SDI_ASS): f.val() for k, f in client_data.items()
                      if k in field_names and k not in ('AssId', 'ExtRefs', 'ProductTypes')}
        '''
        # cl_name got DEPRECATED in sys_data_generic branch and replaced by cl_firstname, cl_surname
        # if 'Surname' in field_names or 'Forename' in field_names:
        #    col_values['cl_name'] = client_data.val('Forename') + FORE_SURNAME_SEP + client_data.val('Surname')
        '''
        if not match_fields:
            # default to non-empty, external system references (k.endswith('Id') and len(k) <= 5 and k != 'RciId')
            match_fields = [k for k, f in client_data.items() if k in ('AssId', 'AcuId', 'SfId', 'ShId') and f.val()]
        chk_values = {f.name(system=SDI_ASS): f.val() for k, f in client_data.items() if k in match_fields}

        msg_tpl = "AssSysData.cl_save() error={}; {}, {}, {}".format("{}", ppf(client_data), field_names, match_fields)
        if not col_values or not chk_values or not match_fields:
            self.error_message = msg_tpl.format("called without data or with a non-empty system id")
            return None
        '''
        # if locked_cols is None:
        #    locked_cols = field_names.copy()        # uncomment for all fields being locked by default
        '''

        ass_db = self.connection(SDI_ASS)
        if ass_db.upsert('clients', col_values, chk_values=chk_values, returning_column='cl_pk', commit=commit,
                         locked_cols=locked_cols):
            self.error_message = msg_tpl.format(ass_db.last_err_msg)
            return None

        cl_pk = ass_db.fetch_value()

        ers_table = 'external_refs'
        ers_key = dict(er_cl_fk=cl_pk)
        with ass_db.thread_lock_init(ers_table, ers_key):
            ext_refs = client_data.val('ExtRefs', system='', direction='')
            if isinstance(ext_refs, str):
                ext_refs = string_to_records(ext_refs, ('Type', 'Id'), rec_sep=EXT_REFS_SEP,
                                             fld_sep=EXT_REF_TYPE_ID_SEP)
            if ext_refs and not ass_db.delete(ers_table, chk_values=ers_key, commit=commit):
                for erd in ext_refs:
                    if erd['Type'] and erd['Id']:   # ignore/skip empty template record
                        col_values = dict(er_cl_fk=cl_pk, er_type=erd['Type'], er_id=erd['Id'])
                        if ass_db.insert(ers_table, col_values, commit=commit):
                            break
        if ass_db.last_err_msg:
            self.error_message = msg_tpl.format(ass_db.last_err_msg)
            return None

        if 'AssId' in client_data and not client_data.val('AssId'):
            client_data.set_val(cl_pk, 'AssId')
        if ass_idx is None:
            ass_idx = self.cl_idx_by_ass_id(cl_pk)
        if ass_idx is None:
            ass_idx = self.cl_idx_by_match_fields(match_fields, client_data.match_key(match_fields))
        if ass_idx is None:
            rec = client_data.copy().set_env(system=SDI_ASS, direction=FAD_ONTO)
            # rec.set_val(EXT_REFS_SEP.join([t + EXT_REF_TYPE_ID_SEP + i for t, i in ext_refs]), 'ExtRefs')
            rec.set_val(cl_pk, 'AssId')
            self.clients.append(rec)
        else:
            self.clients[ass_idx].set_val(cl_pk, 'AssId')

        return cl_pk

    def cl_flush(self):
        ass_db = self.connection(SDI_ASS)
        for idx in self.clients_changed:
            rec = self.clients[idx]
            cl_pk = self.cl_save(rec, ass_idx=idx, commit=True)
            if cl_pk is None or self.error_message:                 # ROLLBACK on empty pkey or error
                return "cl_flush(): err?={} -> roll_back-err?={}".format(self.error_message, ass_db.rollback())

        return ass_db.commit()

    @staticmethod
    def cl_compare_ext_refs(this_rec, that_rec):
        dif = list()
        this_has = this_rec.val('ExtRefs')
        that_has = that_rec.val('ExtRefs')
        if this_has and that_has:
            this_val = set(this_has.split(EXT_REFS_SEP) if isinstance(this_has, str)
                           else [r.val('Type') + EXT_REF_TYPE_ID_SEP + r.val('Id')
                                 for r in this_has if r.val('Type') and r.val('Id')])
            that_val = set(that_has.split(EXT_REFS_SEP) if isinstance(that_has, str)
                           else [r.val('Type') + EXT_REF_TYPE_ID_SEP + r.val('Id')
                                 for r in that_has if r.val('Type') and r.val('Id')])
            set_dif = this_val - that_val
            if set_dif:
                dif.append("External references {} in {} not found in {}".format(set_dif, this_rec, that_rec))
            set_dif = that_val - this_val
            if set_dif:
                dif.append("External references {} not in {} found in {}".format(set_dif, this_rec, that_rec))
        elif this_has != that_has:
            dif.append("External reference field does not exist in {}".format(this_rec if that_has else that_rec))
        return dif

    ''' migrate check of ClientRefsAddExclude against ClientRefsResortCodes to config_test 
        .. and check of duplicates too
    
        resort_codes = self.cae.get_config('ClientRefsResortCodes', default_value='').split(',')
        found_ids = dict()
        for rec in self.clients:
            if rec.val('ExtRefs'):
                for er_id in rec.val('ExtRefs').split(EXT_REFS_SEP):
                    if er_id not in found_ids:
                        found_ids[er_id] = [rec]
                    elif [_ for _ in found_ids[er_id] if _.val('AcuId') != rec.val('AcuId')]:
                        found_ids[er_id].append(rec)
                    if rec.val('AcuId'):
                        if er_id in self.client_refs_add_exclude and rec.val('AcuId') not in resort_codes:
                            self._warn("Resort RCI ID {} found in client {}".format(er_id, rec.val('AcuId')),
                                       self._ctx_no_file + 'CheckClientsDataResortId')
                        elif rec.val('AcuId') in resort_codes and er_id not in self.client_refs_add_exclude:
                            self._warn("Resort {} is missing RCI ID {}".format(rec.val('AcuId'), er_id),
                                       self._ctx_no_file + 'CheckClientsDataResortId')
        # prepare found duplicate ids, prevent duplicate printouts and re-order for to separate RCI refs from others
        dup_ids = list()
        for ref, recs in found_ids.items():
            if len(recs) > 1:
                dup_ids.append("Duplicate external {} ref {!r} found in clients: {}"
                               .format(ref.split(EXT_REF_TYPE_ID_SEP)[0] if EXT_REF_TYPE_ID_SEP in ref
                                       else EXT_REF_TYPE_RCI,
                                       ref, 
                                       ';'.join([_.val('AcuId') for _ in recs])))
        for dup in sorted(dup_ids):
            self._warn(dup, self._ctx_no_file + 'CheckClientsDataExtRefDuplicates')
    '''

    def cl_ac_id_by_ass_id(self, ass_id):
        """
        :param ass_id:  AssCache client pkey/ID.
        :return:        Acumen client reference.
        """
        acu_id = None
        for rec in self.clients:
            if rec.val('AssId') == ass_id:
                acu_id = rec.val('AcuId')
                break
        if not acu_id:
            ass_db = self.connection(SDI_ASS)
            if ass_db.select('clients', ['cl_ac_id'], chk_values=dict(cl_pk=ass_id)):
                self.error_message = "cl_ac_id_by_ass_id(): AssCache client PKey {} not found (err={})" \
                    .format(ass_id, ass_db.last_err_msg)
            else:
                acu_id = ass_db.fetch_value()
        return acu_id

    def cl_ass_id_by_idx(self, index):
        return self.clients[index].val('AssId')

    def cl_ass_id_by_ac_id(self, ac_id):
        """
        :param ac_id:   Acumen client reference/ID.
        :return:        AssCache client primary key.
        """
        cl_pk = None
        for rec in self.clients:
            if rec.val('AcuId') == ac_id:
                cl_pk = rec.val('AssId')
                break
        if not cl_pk:
            ass_db = self.connection(SDI_ASS)
            if ass_db.select('clients', ['cl_pk'], chk_values=dict(cl_ac_id=ac_id)):
                self.error_message = "cl_ass_id_by_ac_id(): Acumen client ID {} not found in AssCache (err={})"\
                    .format(ac_id, ass_db.last_err_msg)
            else:
                cl_pk = ass_db.fetch_value()
        return cl_pk

    def cl_ass_id_by_sh_id(self, sh_id):
        """
        :param sh_id:   Sihot guest object ID.
        :return:        AssCache client primary key.
        """
        cl_pk = None
        for rec in self.clients:
            if rec.val('ShId') == sh_id:
                cl_pk = rec.val('AssId')
                break
        if not cl_pk:
            ass_db = self.connection(SDI_ASS)
            if ass_db.select('clients', ['cl_pk'], chk_values=dict(cl_sh_id=sh_id)):
                self.error_message = "cl_ass_id_by_sh_id(): Sihot guest object ID {} not found in AssCache (err={})" \
                    .format(sh_id, ass_db.last_err_msg)
            else:
                cl_pk = ass_db.fetch_value()
        return cl_pk

    def cl_sf_id_by_ass_id(self, ass_id):
        """
        :param ass_id:  AssCache client Id/PKey.
        :return:        Salesforce Contact/Account Id.
        """
        sf_id = None
        for rec in self.clients:
            if rec.val('AssId') == ass_id:
                sf_id = rec.val('SfId')
                break
        if not sf_id:
            ass_db = self.connection(SDI_ASS)
            if ass_db.select('clients', ['cl_sf_id'], chk_values=dict(cl_pk=ass_id)):
                self.error_message = "cl_sf_id_by_ass_id(): AssCache client ID {} not found (err={})" \
                    .format(ass_id, ass_db.last_err_msg)
            else:
                sf_id = ass_db.fetch_value()
        return sf_id

    def cl_sh_id_by_ass_id(self, ass_id):
        """
        :param ass_id:  AssCache client pkey/ID.
        :return:        Sihot client/guest object id.
        """
        sh_id = None
        for rec in self.clients:
            if rec.val('AssId') == ass_id:
                sh_id = rec.val('ShId')
                break
        if not sh_id:
            ass_db = self.connection(SDI_ASS)
            if ass_db.select('clients', ['cl_sh_id'], chk_values=dict(cl_pk=ass_id)):
                self.error_message = "cl_sh_id_by_ass_id(): AssCache client PKey {} not found (err={})" \
                    .format(ass_id, ass_db.last_err_msg)
            else:
                sh_id = ass_db.fetch_value()
        return sh_id

    def cl_ensure_id(self, sh_id=None, ac_id=None, surname=None, forename=None, email=None, phone=None):
        """
        determine client id in ass_cache database, from either sh_id or ac_id, create the client record if not exists.
        :param sh_id:       Sihot guest object ID (mandatory if ac_id is not specified).
        :param ac_id:       Acumen client reference/Sihot matchcode (mandatory if sh_id is not specified).
        :param surname:     Surname for client (only needed if client gets created).
        :param forename:    Firstname for client (only needed if client gets created).
        :param email:       Email address of client (only needed if client gets created).
        :param phone:       Phone number of client (only needed if client gets created).
        :return:            primary key (ass_id/cl_pk) of this client (if exists) or None if error.
        """
        if not sh_id and not ac_id:
            self._err("cl_ensure_id() missing Acu-/Sh-client references; name={} {}; email={}, phone={}"
                      .format(surname, forename, email, phone))
            return None
        cl_pk = None
        if sh_id and ac_id:
            for rec in self.clients:
                if rec.val('ShId') == sh_id and rec.val('AcuId') == ac_id:
                    cl_pk = rec.val('AssId')
                    break
            if not cl_pk:
                ass_db = self.connection(SDI_ASS)
                if ass_db.select('clients', ['cl_pk'], chk_values=dict(cl_sh_id=sh_id, cl_ac_id=ac_id)):
                    self.error_message = "cl_ensure_id(): Sihot client {}/{} not found in AssCache (err={})" \
                        .format(sh_id, ac_id, ass_db.last_err_msg)
                    return None
                else:
                    cl_pk = ass_db.fetch_value()

        if not cl_pk and sh_id:
            cl_pk = self.cl_ass_id_by_sh_id(sh_id)

        if not cl_pk and ac_id:
            cl_pk = self.cl_ass_id_by_ac_id(ac_id)

        if not cl_pk:   # create client record?
            cl_data = dict()        # type: Union[Record, Dict[Union[str, Any], Any]]
            if ac_id:
                cl_data['AcuId'] = ac_id
            if sh_id:
                cl_data['ShId'] = sh_id
            if surname:
                cl_data['Surname'] = surname
            if forename:
                cl_data['Forename'] = forename
            if email:
                cl_data['Email'] = email
            if phone:
                cl_data['Phone'] = phone
            cl_pk = self.cl_save(cl_data, locked_cols=['AcuId', 'ShId', 'Surname', 'Forename', 'Email', 'Phone'])
            if self.error_message:
                self._err("cl_ensure_id(): error '{}' after cl_save({})".format(self.error_message, cl_data))

        return cl_pk

    def cl_ac_id_by_idx(self, index):
        return self.clients[index].val('AcuId')

    def cl_sh_id_by_idx(self, index):
        return self.clients[index].val('ShId')

    def cl_ext_refs_by_idx(self, index):
        return self.clients[index].val('ExtRefs').split(EXT_REFS_SEP)

    def cl_idx_by_ass_id(self, ass_id):
        for list_idx, rec in enumerate(self.clients):
            if rec.val('AssId') == ass_id:
                return list_idx

    def cl_idx_by_match_fields(self, match_fields, match_values):
        return list_idx_by_match_fields(self.clients, match_fields, match_values)

    def cl_idx_by_rci_id(self, imp_rci_ref, fields_dict, file_name, line_num):
        """ determine list index in cached clients """
        # check first if client exists
        for list_idx, rec in enumerate(self.clients):
            ext_refs = rec.val('ExtRefs')
            # if ext_refs and EXT_REF_TYPE_ID_SEP + imp_rci_ref in ext_refs.split(EXT_REFS_SEP):
            if ext_refs and imp_rci_ref in ext_refs.split(EXT_REFS_SEP):
                break
        else:
            sf_conn = self.connection(SDI_SF)
            sf_id, dup_clients = sf_conn.cl_by_rci_id(imp_rci_ref)
            if sf_conn.error_msg:
                self._err("cl_idx_by_rci_id() Salesforce connect/fetch error " + sf_conn.error_msg,
                          file_name, line_num, importance=3)
            if len(dup_clients) > 0:
                self._err("Found duplicate Salesforce client(s) with main or external RCI ID {}. Used client {}, dup={}"
                          .format(imp_rci_ref, sf_id, dup_clients), file_name, line_num)
            if sf_id:
                ass_id = sf_conn.cl_ass_id_by_idx(sf_id)
                if sf_conn.error_msg:
                    self._err("cl_idx_by_rci_id() AssCache id fetch error " + sf_conn.error_msg,
                              file_name, line_num, importance=3)
                ac_id = sf_conn.cl_ac_id_by_idx(sf_id)
                if sf_conn.error_msg:
                    self._err("cl_idx_by_rci_id() Acumen id fetch error " + sf_conn.error_msg,
                              file_name, line_num, importance=3)
                sh_id = sf_conn.cl_sh_id_by_idx(sf_id)
                if sf_conn.error_msg:
                    self._err("cl_idx_by_rci_id() Sihot id fetch error " + sf_conn.error_msg,
                              file_name, line_num, importance=3)
            else:
                ass_id = None
                ac_id = None
                rec = Record(fields=fields_dict)
                rec.set_val(imp_rci_ref, 'RciId')   # also create in Sf an entry in the External_Ref custom object
                sf_id, err, msg = sf_conn.cl_upsert(rec)
                if err:
                    self._err("cl_idx_by_rci_id() Salesforce upsert error " + sf_conn.error_msg,
                              file_name, line_num, importance=3)
                elif msg and self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    self._warn("cl_idx_by_rci_id() client upsert message: " + msg, file_name, line_num, importance=1)
                sh_id = None
            self.clients.append((ass_id, ac_id, sf_id, sh_id, fields_dict.get('name'), fields_dict.get('email'),
                                 fields_dict.get('phone'), imp_rci_ref, 0))
            list_idx = len(self.clients) - 1
            self.clients_changed.append(list_idx)
        return list_idx

    def cl_complete_with_sh_id(self, c_idx, sh_id):
        """ complete clients with imported data and sihot objid """
        rec = self.clients[c_idx]
        if not rec.val('ShId') or rec.val('ShId') != sh_id:
            if rec.val('ShId'):
                self._warn("Sihot guest object id changed from {} to {} for Salesforce client {}"
                           .format(rec.val('ShId'), sh_id, rec.val('SfId')), self._ctx_no_file + 'CompShId',
                           importance=1)
            rec.set_val(sh_id, 'ShId')
            self.clients[c_idx] = rec
            self.clients_changed.append(c_idx)

    def cl_sent_to_sihot(self):
        return [i for i, _ in enumerate(self.clients) if _.val('ShId')]

    def cl_list_by_ac_id(self, ac_id):
        return [_ for _ in self.clients if _.val('AcuId') == ac_id]

    # =================  reservation_inventories  =====================================================================

    def ri_fetch_all(self):
        self._warn("Fetching reservation inventory from AssCache (needs some minutes)",
                   self._ctx_no_file + 'FetchResInv', importance=4)
        self.reservation_inventories = self.load_view(self.connection(SDI_ASS), 'res_inventories')
        if not self.reservation_inventories:
            return self.error_message

        return ""

    def ri_allocated_room(self, room_no, arr_date):
        # _RI_PK = 0, _HOTEL_ID = 2, _POINTS = 7, _COMMENT = 8
        _WKREF = 1
        _YEAR = 3
        _ROREF = 4
        _SWAPPED = 5
        _GRANTED = 6
        year, week = self.rci_arr_to_year_week(arr_date)
        for r_rec in self.reservation_inventories:
            if r_rec[_WKREF] == room_no.lstrip('0') + '-' + ('0' + str(week))[:2] and r_rec[_YEAR] == year:
                if r_rec[_GRANTED] == 'HR' or not r_rec[_SWAPPED] \
                        or r_rec[_ROREF] in ('RW', 'RX', 'rW'):
                    return room_no
        return ''

    # =================  reservation bookings  ===================================================================

    @staticmethod
    def rgr_min_chk_values(col_values):
        if col_values.get('rgr_ho_fk') and col_values.get('rgr_res_id') and col_values.get('rgr_sub_id'):
            where_vars = dict(rgr_ho_fk=col_values['rgr_ho_fk'], rgr_res_id=col_values['rgr_res_id'],
                              rgr_sub_id=col_values['rgr_sub_id'])
        elif col_values.get('rgr_obj_id'):
            where_vars = dict(rgr_obj_id=col_values['rgr_obj_id'])
        elif col_values.get('rgr_gds_no'):
            where_vars = dict(rgr_gds_no=col_values['rgr_gds_no'])
        elif col_values.get('rgr_sf_id'):
            where_vars = dict(rgr_sf_id=col_values['rgr_sf_id'])
        elif col_values.get('rgr_ho_fk') and col_values.get('rgr_res_id'):
            where_vars = dict(rgr_ho_fk=col_values['rgr_ho_fk'], rgr_res_id=col_values['rgr_res_id'], rgr_sub_id='-1')
        else:   # if not obj_id and not (ho_id and res_id) and not gds_no:
            where_vars = dict()
        return where_vars

    def rgr_complete_ids(self, col_values, chk_values):
        """
        complete id values (mainly objId or reservation number) within col_values from Sihot server data.
        :param col_values:      dict of res_groups columns to be extended/updated.
        :param chk_values:      dict of res_groups search/WHERE column values.
        :return:                True if all required ids (rgr_obj_id, rgr_ho_fk, rgr_res_id and rgr_sub_id) could be
                                set to non-empty value, else False.
        """
        ret = True

        if not col_values.get('rgr_obj_id') and not chk_values.get('rgr_obj_id'):
            # rgr_obj_id missing in col_values and no need to set: col_values['rgr_obj_id'] = chk_values['rgr_obj_id']
            ids = dict()
            if ((chk_values.get('rgr_ho_fk') or col_values.get('rgr_ho_fk'))
                    and (chk_values.get('rgr_res_id') or col_values.get('rgr_res_id'))
                    and (chk_values.get('rgr_sub_id') or col_values.get('rgr_sub_id'))):
                ids = res_no_to_ids(self.cae,
                                    chk_values.get('rgr_ho_fk') or col_values['rgr_ho_fk'],
                                    chk_values.get('rgr_res_id') or col_values['rgr_res_id'],
                                    chk_values.get('rgr_sub_id') or col_values['rgr_sub_id'])
                if isinstance(ids, dict) and ids.get('ResObjId'):   # silently ignoring ResFetch/resNotFound error
                    col_values['rgr_obj_id'] = ids['ResObjId']
            elif ((chk_values.get('rgr_ho_fk') or col_values.get('rgr_ho_fk'))
                  and (chk_values.get('rgr_gds_no') or col_values.get('rgr_gds_no'))):
                ids = gds_no_to_ids(self.cae,
                                    chk_values.get('rgr_ho_fk') or col_values['rgr_ho_fk'],
                                    chk_values.get('rgr_gds_no') or col_values['rgr_gds_no'])
                if isinstance(ids, dict) and ids.get('ResObjId'):   # silently ignoring ResFetch/resNotFound error
                    col_values['rgr_obj_id'] = ids['ResObjId']
            ret = bool(col_values.get('rgr_obj_id'))
            if ret and isinstance(ids, dict):
                # if Sihot Reservation Object ID was completed by fetching from Sihot, we'll have anyway all IDs,
                # .. so then check if first init of empty cache value is also needed for the other fetched IDs
                if ids.get('ResGdsNo'):
                    if col_values.get('rgr_gds_no') and col_values['rgr_gds_no'] != ids['ResGdsNo']:
                        self._warn("Automatic/hidden update of rgr_gds_no from {} to {}"
                                   .format(col_values.get('rgr_gds_no'), ids['ResGdsNo']),
                                   self._ctx_no_file + "rgr_complete_ids()")
                    col_values['rgr_gds_no'] = ids['ResGdsNo']
                if ids.get('ResSfId'):
                    if col_values.get('rgr_sf_id') and col_values['rgr_sf_id'] != ids['ResSfId']:
                        self._warn("Automatic/hidden update of rgr_sf_id from {} to {}"
                                   .format(col_values.get('rgr_sf_id'), ids['ResSfId']),
                                   self._ctx_no_file + "rgr_complete_ids()")
                    col_values['rgr_sf_id'] = ids['ResSfId']

        if not (col_values.get('rgr_ho_fk') and col_values.get('rgr_res_id') and col_values.get('rgr_sub_id')) \
                and not (chk_values.get('rgr_ho_fk') and chk_values.get('rgr_res_id') and chk_values.get('rgr_sub_id')):
            if chk_values.get('rgr_obj_id') or col_values.get('rgr_obj_id'):
                res_no_ids = obj_id_to_res_no(self.cae, chk_values.get('rgr_obj_id') or col_values['rgr_obj_id'])
                if res_no_ids[0] is not None:
                    if res_no_ids[:2] != (col_values.get('rgr_ho_fk'), col_values.get('rgr_res_id'), ):
                        self._warn("Automatic/hidden update of reservation number from {}/{}@{} to {}/{}@{}"
                                   .format(col_values.get('rgr_ho_fk'), col_values.get('rgr_res_id'),
                                           col_values.get('rgr_sub_id'), *res_no_ids),
                                   self._ctx_no_file + "rgr_complete_ids()")
                    col_values['rgr_ho_fk'], col_values['rgr_res_id'], col_values['rgr_sub_id'] = res_no_ids
            elif col_values.get('rgr_ho_fk') and col_values.get('rgr_res_id'):
                col_values['rgr_sub_id'] = '0'
            ret = bool(col_values.get('rgr_ho_fk') and col_values.get('rgr_res_id') and col_values.get('rgr_sub_id'))

        return ret

    def rgr_fetch_list(self, col_names, chk_values=None, where_group_order="", bind_values=None):
        ass_db = self.connection(SDI_ASS)
        if ass_db.select('res_groups', col_names, chk_values=chk_values, where_group_order=where_group_order,
                         bind_vars=bind_values):
            self.error_message = ass_db.last_err_msg
            rows = tuple()
        else:
            rows = ass_db.fetch_all()
            if ass_db.last_err_msg:
                self.error_message += ass_db.last_err_msg
        return rows

    def rgr_upsert(self, col_values, chk_values=None, commit=False, multiple_row_update=False, returning_column=''):
        """
        upsert into ass_cache.res_groups

        :param col_values:          dict of column values to be inserted/updated.
        :param chk_values:          dict of column values for to identify the record to update (insert if not exists).
                                    (opt, def=IDs from col_values items: obj_id, ho_id+res_id+sub_id, gds_no or sf_id).
        :param commit:              pass True to commit on success or rollback on error (opt, def=False).
        :param multiple_row_update: allow update of multiple records with the same chk_values (opt, def=False).
        :param returning_column:    name of the returning column or empty (opt, def='').
        :return:                    returning_column value (if specified) OR chk_values OR None if self.error message.
        """
        if chk_values is None:
            chk_values = self.rgr_min_chk_values(col_values)
        msg = " in rgr_upsert(col_values=\n{}\nchk_values=\n{})".format(ppf(col_values), ppf(chk_values))
        ''' prevent to wipe id value -- NOT NEEDED
        if prevent_id_wipe:
            for k in ('rgr_obj_id', 'rgr_ho_fk', 'rgr_res_id', 'rgr_sub_id', 'rgr_gds_no', 'rgr_sf_id', ):
                if k in col_values and col_values.get(k) in (None, ''):
                    col_values.pop(k)   # remove pk column with empty value
        '''
        ret = None
        if not chk_values:
            self.error_message = "Missing reservation IDs (ObjId, Hotel/ResId or GdsNo)" + msg
        elif not multiple_row_update and not self.rgr_complete_ids(col_values, chk_values):
            self.error_message = "Incomplete-able res IDs" + msg
        else:
            ass_db = self.connection(SDI_ASS)
            self.error_message = ass_db.upsert('res_groups', col_values, chk_values,
                                               returning_column=returning_column, commit=commit,
                                               multiple_row_update=multiple_row_update)
            if self.error_message:
                if commit:
                    self.error_message += "\n" + ass_db.rollback()
            elif not multiple_row_update and ass_db.curs.rowcount != 1:
                self.error_message = "Invalid row count; expected 1 but got {}".format(ass_db.curs.rowcount) + msg
            elif returning_column:
                ret = ass_db.fetch_value()
            else:
                ret = chk_values

        return ret

    def rgc_fetch_list(self, col_names, chk_values=None, where_group_order="", bind_values=None):
        ass_db = self.connection(SDI_ASS)
        if ass_db.select('res_group_clients', col_names, chk_values=chk_values, where_group_order=where_group_order,
                         bind_vars=bind_values):
            self.error_message = ass_db.last_err_msg
        ret = ass_db.fetch_all()
        if ass_db.last_err_msg:
            self.error_message += ass_db.last_err_msg
        return ret

    def rgc_upsert(self, col_values, chk_values=None, commit=False, multiple_row_update=False):
        """
        upsert into ass_cache.res_group_clients

        :param col_values:          dict of column values to be inserted/updated.
        :param chk_values:          dict of column values for to identify the record to update (insert if not exists).
                                    Allowed keys: rgc_rgr_fk, rgc_room_seq, rgc_pers_seq.
        :param commit:              True to commit (opt, def=False).
        :param multiple_row_update: allow update of multiple records with the same chk_values (opt, def=False).
        :return:                    error message on error else empty string.
        """
        if chk_values is None:
            chk_values = {k: v for k, v in col_values.items() if k in ('rgc_rgr_fk', 'rgc_room_seq', 'rgc_pers_seq')}
        if chk_values:
            ass_db = self.connection(SDI_ASS)
            self.error_message = ass_db.upsert('res_group_clients', col_values, chk_values, commit=commit,
                                               multiple_row_update=multiple_row_update)
            if not self.error_message and not multiple_row_update and ass_db.curs.rowcount != 1:
                self.error_message = "rgc_upsert(): expected 1 but got {} affected row count; col=\n{}; chk=\n{}" \
                    .format(ass_db.curs.rowcount, ppf(col_values), ppf(chk_values))
        else:
            self.error_message = "ASD.rgc_upsert(): missing occupant id\ncol_values=\n{}".format(ppf(col_values))

        return self.error_message

    def res_idx_by_match_fields(self, match_fields, match_values):
        return list_idx_by_match_fields(self.reservations, match_fields, match_values)

    def res_save(self, res_rec, field_names=(), match_fields=(), ass_idx=None, commit=False, last_change=None,
                 ass_res_rec=None):
        """
        extract reservation data from sihot ResResponse Record and save it into the ass_cache database.

        :param res_rec:         Reservation data Record.
        :param field_names:     list of field names to be saved in AssCache db (def=all fields in res_data).
        :param match_fields:    list of field names for rec lookup (def=non-empty ResHotelId/ResId/ResSubId/ResGdsNo).
        :param ass_idx:         Records index of self.reservations record. If None/default then determine for to update
                                the self.reservations cache list.
        :param commit:          boolean flag if AssCache data changes should be committed (def=False).
        :param last_change:     if not None then set rgr_last_change column value to this passed timestamp.
        :param ass_res_rec:     pass in empty Record/dict for to return reservation data, including the
                                person/rooming-list (in the Records value of ass_res_rec['ResPersons'])
        :return:                primary key of saved reservation (rgr_pk) or None on error (see self.error_message).
        """
        if not field_names:
            field_names = res_rec.leaf_names()  # [k for k in res_rec.keys()]
        if not match_fields:
            # default to non-empty, system references
            match_fields = [k for k, f in res_rec.items()
                            if k in ('ResHotelId', 'ResId', 'ResSubId', 'ResGdsNo') and f.val()]
        chk_values = {f.name(system=SDI_ASS): f.val(system=SDI_ASS) for k, f in res_rec.items() if k in match_fields}
        if not field_names or not chk_values or not match_fields:
            self.error_message = "ASD.res_save({}, {}, {}) called without data or with a non-empty system id"\
                .format(ppf(res_rec), field_names, match_fields)
            return None

        if ass_res_rec is None:
            ass_res_rec = Record(system=SDI_ASS, direction=FAD_ONTO)
        is_rec = isinstance(ass_res_rec, Record)
        if is_rec:
            ass_res_rec.add_system_fields(ASS_CLIENT_MAP + ASS_RES_MAP)

        # determine ordering client; RESCHANNELLIST element is situated within RESERVATION xml block
        ord_cl_pk = None
        sh_id = res_rec.val('ShId')         # was RESCHANNELLIST.RESCHANNEL.OBJID
        ac_id = res_rec.val('AcuId')        # was RESCHANNELLIST.RESCHANNEL.MATCHCODE
        if sh_id or ac_id:
            self._warn("res_save(): create new client record for orderer {}/{}".format(sh_id, ac_id),
                       minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            ord_cl_pk = self.cl_ensure_id(sh_id=sh_id, ac_id=ac_id)
            if ord_cl_pk is None:
                self._warn("res_save(): creation of new orderer {}/{} failed with (ignored) err={}"
                           .format(sh_id, ac_id, self.error_message))
                self.error_message = ""

        ass_db = self.connection(SDI_ASS)
        ri_pk = None
        apt_wk, year = self.sh_apt_wk_yr(res_rec)
        if ass_db.select('res_inventories', ['ri_pk'], chk_values=dict(ri_pr_fk=apt_wk, ri_usage_year=year)):
            self._warn("res_save(): res inv {}~{} not found; (ignored) err={}"
                       .format(apt_wk, year, self.error_message))
            self.error_message = ""
        else:
            ri_pk = ass_db.fetch_value()
            if ass_db.last_err_msg:
                self._warn("res_save(): res inv {}~{} error={}".format(apt_wk, year, ass_db.last_err_msg))

        ho_id = res_rec.val('ResHotelId')
        chk_values = dict(rgr_ho_fk=ho_id)
        res_id = res_rec.val('ResId')
        sub_id = res_rec.val('ResSubId')
        gds_no = res_rec.val('ResGdsNo')
        err_pre = "res_save() for res-no {}/{}@{} and GDS-No. {}: ".format(res_id, sub_id, ho_id, gds_no)
        if ho_id and res_id and sub_id:
            chk_values.update(rgr_res_id=res_id, rgr_sub_id=sub_id)
        elif gds_no:
            chk_values.update(rgr_gds_no=gds_no)
        else:                                               # RETURN
            self.error_message = err_pre + "Incomplete reservation id"
            return None

        sh_ass_rec = Record(system=SDI_ASS, direction=FAD_ONTO)
        sh_ass_rec.merge_leafs(res_rec, system=SDI_SH, direction=FAD_FROM)
        sh_ass_rec.add_system_fields(ASS_CLIENT_MAP + ASS_RES_MAP, extend=False)
        sh_ass_rec.pull(SDI_SH)
        sh_ass_rec.set_val(ord_cl_pk, 'AssId')
        sh_ass_rec.set_val(ri_pk, 'RinId')
        for pers_idx, occ_rec in enumerate(sh_ass_rec.value('ResPersons', flex_sys_dir=True)):
            if not sh_ass_rec.val('ResRoomNo') and occ_rec.val('RoomNo'):
                sh_ass_rec.set_val(occ_rec.val('RoomNo'), 'ResRoomNo')

            sh_id = occ_rec.val('PersShId')
            ac_id = occ_rec.val('PersAcuId')
            if sh_id or ac_id:
                sn = occ_rec.val('PersSurname')
                fn = occ_rec.val('PersForename')
                self._warn(err_pre + "ensure client {} {} for occupant {}/{}".format(fn, sn, sh_id, ac_id),
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                occ_cl_pk = self.cl_ensure_id(sh_id=sh_id, ac_id=ac_id, surname=sn, forename=fn)
                if occ_cl_pk is None:
                    self._warn(err_pre + "create client record for occupant {} {} {}/{} failed; ignored err={}"
                               .format(fn, sn, sh_id, ac_id, self.error_message),
                               minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                    self.error_message = ""
                else:
                    occ_rec.set_val(occ_cl_pk, 'PersAssId', root_rec=sh_ass_rec, root_idx=('ResPersons', pers_idx))

        sh_ass_rec.push(SDI_ASS)

        with ass_db.thread_lock_init('res_groups', chk_values):
            def _filter_rgr_cols(f):
                fld_name = f.name()
                sys_name = f.name(system=SDI_ASS, direction=FAD_ONTO)
                return not sys_name.startswith('rgr_') or fld_name not in field_names

            def _filter_rgc_cols(f):
                fld_name = f.name()
                sys_name = f.name(system=SDI_ASS, direction=FAD_ONTO)
                return not sys_name.startswith('rgc_') or fld_name not in field_names

            upd_values = sh_ass_rec.to_dict(filter_fields=_filter_rgr_cols, system=SDI_ASS, direction=FAD_ONTO)
            if last_change:
                upd_values.update(rgr_last_change=datetime.datetime.now())

            rgr_pk = self.rgr_upsert(upd_values, chk_values=chk_values, commit=commit, returning_column='rgr_pk')
            if not self.error_message:
                ass_res_rec.update(upd_values)
                ass_res_rec['ResAssId'] = rgr_pk
                next_rs = next_ps = '0'
                for pers_idx, occ_rec in enumerate(sh_ass_rec.value('ResPersons', flex_sys_dir=True)):
                    '''
                    # sometimes Sihot SS is sending back ROOM-SEQ value as "1" - therefore now hard-coded to "0"
                    # .. room_seq, pers_seq = occ_rec.val('RoomSeq') or next_rs, occ_rec.val('RoomPersSeq') or next_ps
                    # LATER in Mar-2019 migrated the bug fix underneath to FldMapXmlParser.end()
                    # .. room_seq, pers_seq = "0", occ_rec.val('RoomPersSeq') or next_ps
                    '''
                    room_seq, pers_seq = occ_rec.val('RoomSeq') or next_rs, occ_rec.val('RoomPersSeq') or next_ps
                    chk_values = dict(rgc_rgr_fk=rgr_pk, rgc_room_seq=int(room_seq), rgc_pers_seq=int(pers_seq))
                    occ_rec.update(chk_values)
                    upd_values = occ_rec.to_dict(filter_fields=_filter_rgc_cols, system=SDI_ASS, direction=FAD_ONTO)
                    if self.rgc_upsert(upd_values, chk_values=chk_values, commit=commit):
                        break
                    if is_rec:
                        ass_res_rec.set_val(upd_values, 'ResPersons', pers_idx)
                    else:
                        if 'ResPersons' not in ass_res_rec:
                            ass_res_rec['ResPersons'] = list()
                        ass_res_rec['ResPersons'].append(upd_values)
                    next_rs, next_ps = room_seq, str(int(pers_seq) + 1) if room_seq == next_rs else '0'

            if self.error_message:
                ass_db.rollback()
                return None
            ass_db.commit()

        if 'ResAssId' in res_rec and not res_rec.val('ResAssId'):
            res_rec.set_val(rgr_pk, 'ResAssId')
        if ass_idx is None:
            ass_idx = self.res_idx_by_match_fields(match_fields, res_rec.match_key(match_fields))
        if ass_idx is None:
            rec = res_rec.copy().set_env(system=SDI_ASS, direction=FAD_ONTO)
            rec.set_val(rgr_pk, 'ResAssId')
            self.reservations.append(rec)
        else:
            self.reservations[ass_idx].set_val(rgr_pk, 'ResAssId')

        return rgr_pk

    # =================  RCI data conversion  ==================================================

    def rci_to_sihot_hotel_id(self, rc_resort_id):
        return self.cae.get_config(rc_resort_id, 'RcResortIds', default_value=-369)     # pass default for int type ret

    def rci_first_week_of_year(self, year):
        rci_wk_01 = self.cae.get_config(str(year), 'RcWeeks')
        if rci_wk_01:
            ret = datetime.datetime.strptime(rci_wk_01, '%Y-%m-%d').date()
        else:
            self._warn("AssSysData.rci_first_week_of_year({}): missing RcWeeks config".format(year), notify=True)
            ret = datetime.date(year=year, month=1, day=1)
            # if ret.weekday() != 4:    # is the 1st of January a Friday? if not then add some/0..6 days
            ret += datetime.timedelta(days=(11 - ret.weekday()) % 7)
        return ret

    def rci_arr_to_year_week(self, arr_date):
        year = arr_date.year
        week_1_begin = self.rci_first_week_of_year(year)
        next_year_week_1_begin = self.rci_first_week_of_year(year + 1)
        if arr_date < week_1_begin:
            year -= 1
            week_1_begin = self.rci_first_week_of_year(year)
        elif arr_date > next_year_week_1_begin:
            year += 1
            week_1_begin = next_year_week_1_begin
        diff = arr_date - week_1_begin
        return year, 1 + int(diff.days / 7)

    def rci_ro_group(self, c_idx, is_guest, file_name, line_num):
        """ determine seg=RE RG RI RL, group=RE RI  and  desc=RCI Internal, RCI External
            (removed RG and RO == RCI Owner/External Guest) """
        if self.clients[c_idx].val('ProductTypes') and not is_guest:
            key = 'Internal'
        else:  # not an owner/internal, so will be either Guest or External
            # changed by Esther/Nitesh - now Guest and RL are External: key = 'Guest' if is_guest else 'External'
            key = 'External'
        seg, desc, grp = self.cae.get_config(key, 'RcMktSegments').split(',')
        if file_name[:3].upper() == 'RL_':
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                self._warn("Reclassified booking from " + seg + "/" + grp + " into RL/RCI External",
                           file_name, line_num, importance=1)
            seg, desc, grp = self.cae.get_config('Leads', 'RcMktSegments').split(',')
        return seg, grp

    # ##########################  market segment helpers  #####################################################

    def ro_agency_objid(self, ro_code):
        return next((cols[1] for cols in self.ro_agencies if cols[0] == ro_code), None)

    def ro_agency_matchcode(self, ro_code):
        return next((cols[2] for cols in self.ro_agencies if cols[0] == ro_code), None)

    def ro_sihot_mkt_seg(self, ro_code):
        sihot_mkt_seg = next((cols[3] for cols in self.ro_agencies if cols[0] == ro_code), None)
        return sihot_mkt_seg or ro_code

    def ro_res_group(self, ro_code):
        return next((cols[4] for cols in self.ro_agencies if cols[0] == ro_code), None)

    # #######################  SF helpers  ######################################################################

    def sf_ass_res_upsert(self, sf_res_id, sh_cl_data, ass_res_data, sync_cache=True, sf_sent=None):
        """
        convert ass_cache db columns to SF fields, and then push to Salesforce server via APEX method call

        :param sf_res_id:       Reservation Opportunity Id (SF ID with 18 characters). Pass None for to create new-one.
        :param sh_cl_data:      Record with Sihot guest data of the reservation orderer (fetched with
                                ClientSearch.fetch_client()/shif.client_data()).
        :param ass_res_data:    Record with reservation fields (from ass_cache.res_groups).
        :param sync_cache:      True for to update ass_cache/res_groups/rgr_last_sync+rgr_sf_id (opt, def=True).
        :param sf_sent:         (OUT, opt) Record(system=SDI_SF, direction=FAD_ONTO) of sent Account+Reservation object
                                fields; e.g. the Reservation Opportunity Id gets returned as sf_data['ResSfId'].
        :return:                error message if error occurred, else empty string.
        """
        msg_sfx = " in ASD.sf_ass_res_upsert({}) sh=\n{} ass=\n{}".format(sf_res_id, ppf(sh_cl_data), ppf(ass_res_data))

        sf_rec = Record(system=SDI_SF, direction=FAD_ONTO).add_system_fields(SF_CLIENT_MAPS['Account'] + SF_RES_MAP) \
            if sf_sent is None else sf_sent
        sf_rec['ResSfId'] = sf_res_id
        ass_id = ass_res_data.val('AssId')
        if ass_id:
            sf_cl_id = self.cl_sf_id_by_ass_id(ass_id)
            if sf_cl_id:
                sf_rec['SfId'] = sf_cl_id

        sf_rec.merge_leafs(ass_res_data)
        sf_rec.merge_leafs(sh_cl_data)

        if not sf_rec.val('ResRoomNo') and ass_res_data.val('ResPersons', 0, 'RoomNo'):
            sf_rec['ResRoomNo'] = ass_res_data.val('ResPersons', 0, 'RoomNo')

        self._warn("Sending reservation to Salesforce; sf_rec=\n{}".format(ppf(sf_rec)),
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        sf_conn = self.connection(SDI_SF)
        sf_cl_id, sf_opp_id, err_msg = sf_conn.res_upsert(sf_rec)
        if err_msg and sf_res_id and [frag for frag in self.sf_id_reset_fragments if frag in err_msg]:
            ori_err = err_msg
            if "Required fields are missing: [LastName]" in err_msg:
                # retry with dummy Surname if Sihot client has no surname
                sf_rec['Surname'] = "+++EmptySihotClientSurname+++"
                sf_cl_id, sf_opp_id, err_msg = sf_conn.res_upsert(sf_rec)
                self._warn("Sent empty Sihot surname as {} to SF client={}; ori-/err='{}'/'{}'"
                           .format(sf_rec['Surname'], sf_cl_id, ori_err, err_msg) + msg_sfx,
                           notify=True)
            else:
                # retry without sf_res_id if ResOpp got deleted within SF
                sf_rec['ResSfId'] = ''
                sf_cl_id, sf_opp_id, err_msg = sf_conn.res_upsert(sf_rec)
                self._warn("Cached ResSfId {} reset to {}; SF client={}; ori-/err='{}'/'{}'"
                           .format(sf_res_id, sf_opp_id, sf_cl_id, ori_err, err_msg) + msg_sfx,
                           notify=True)
                sf_res_id = ''

        if not err_msg and (not sf_cl_id or not sf_opp_id):
            self._err("Empty Id from SF: PersonAccount.Id={}; ResSfId={}".format(sf_cl_id, sf_opp_id) + msg_sfx)
        if not err_msg and sf_rec.val('SfId') and sf_rec.val('SfId') != sf_cl_id \
                and self.debug_level >= DEBUG_LEVEL_VERBOSE:
            self._err("PersonAccountId/id/SfId discrepancy {} != {}".format(sf_rec.val('SfId'), sf_cl_id) + msg_sfx)
        if not err_msg and sf_rec.val('ResSfId') and sf_rec.val('ResSfId') != sf_opp_id \
                and self.debug_level >= DEBUG_LEVEL_VERBOSE:
            self._err("Res. Opportunity Id discrepancy {} != {}".format(sf_rec.val('ResSfId'), sf_opp_id) + msg_sfx)

        if sync_cache:
            if sf_cl_id and ass_id:
                col_values = dict(AssId=ass_id, SfId=sf_cl_id)      # type: Union[Record, Dict[Union[str, Any], Any]]
                self.cl_save(col_values, match_fields=['AssId'])    # on error populating/overwriting self.error_message
                if self.error_message:
                    err_msg += self.error_message
                    self.error_message = ""

            col_values = dict() if err_msg else dict(rgr_last_sync=datetime.datetime.now())
            if not sf_res_id and sf_opp_id:     # save just (re-)created ID of Reservation Opportunity in AssCache
                col_values['rgr_sf_id'] = sf_opp_id
            elif self.debug_level >= DEBUG_LEVEL_VERBOSE and sf_opp_id and sf_res_id and sf_opp_id != sf_res_id:
                self._err("Reservation Opportunity ID discrepancy {} != {}".format(sf_opp_id, sf_res_id) + msg_sfx)

            if col_values:
                self.rgr_upsert(col_values,
                                chk_values=dict(rgr_ho_fk=sf_rec.val('ResHotelId'), rgr_res_id=sf_rec.val('ResId'),
                                                rgr_sub_id=sf_rec.val('ResSubId')),
                                commit=True)
                if self.error_message:
                    err_msg += self.error_message
                    self.error_message = ""

        if err_msg:
            self.error_message += err_msg
        return self.error_message

    def sf_ass_room_change(self, rgr_sf_id, check_in, check_out, next_room_id):
        """
        check room change and if ok then pass to Salesforce Allocation custom object.
        :param rgr_sf_id:       SF Reservation Opportunity object Id.
        :param check_in:        check-in timestamp.
        :param check_out:       check-out timestamp.
        :param next_room_id:    newest apartment/room number.
        :return:                empty string if ok, else error message.
        """
        msg = "ASD.sf_ass_room_change({}, {}, {}, {}) ".format(rgr_sf_id, check_in, check_out, next_room_id)
        self._warn(msg + "called", minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        err_msg = self.connection(SDI_SF).room_change(rgr_sf_id, check_in, check_out, next_room_id)
        if err_msg and [frag for frag in self.sf_id_reset_fragments if frag in err_msg]:
            # reset last-res-change-datetime to now for to re-sync reservation (to get new ResSfId) and then try again
            self.rgr_upsert(dict(rgr_last_change=datetime.datetime.now(), rgr_sf_id=None), dict(rgr_sf_id=rgr_sf_id),
                            multiple_row_update=True, commit=True)
            self._warn("ResSfId {} reset; ori-/err='{}'/'{}' in "
                       .format(rgr_sf_id, err_msg, self.error_message) + msg, notify=True)
            self.error_message = ""
            return ""

        if err_msg:
            self.error_message += err_msg
        return self.error_message

    # #######################  SH helpers  ######################################################################

    def sh_apt_wk_yr(self, rec):
        arr = rec.val('ResArrival')
        year, wk = self.rci_arr_to_year_week(arr)
        apt = rec.val('ResRoomNo')
        apt_wk = "{}-{:0>2}".format(apt, wk)
        return apt_wk, year

    def sh_guest_ids(self, match_field, match_val):
        ret = None
        client_search = ClientSearch(self.cae)
        if match_field == 'AcuId':
            ret = client_search.search_clients(matchcode=match_val)
        elif match_field == 'Surname':
            ret = client_search.search_clients(name=match_val)
        elif match_field == 'Email':
            ret = client_search.search_clients(email=match_val)
        return ret

    def sh_avail_rooms(self, hotel_ids=None, room_cat_prefix='', day=None):
        """
        accumulating the number of available rooms in all the hotels specified by the hotel_ids list with the room
        category matching the first characters of the specified room_cat_prefix string and for a certain day.

        All parameters are web-service-query-param-ready (means they could be passed as str).

        :param hotel_ids:       Optional list of hotel IDs (leave empty for to get the rooms in all hotels accumulated).
        :param room_cat_prefix: Optional room category prefix string (leave empty for all room categories or pass e.g.
                                'S' for a accumulation of all the Studios or '1J' for all 1 bedroom junior rooms).
        :param day:             Optional day (leave empty for to get the available rooms for today's date).
        :return:                Number of available rooms (negative on overbooking).
        """
        if not hotel_ids:
            # hotel_ids = ['1', '2', '3', '4', '999']
            hotel_ids = self.ho_id_list()  # determine list of IDs of all active/valid Sihot-hotels
        elif isinstance(hotel_ids, str):
            hotel_ids = hotel_ids.split(',')
        if not day:
            day = datetime.date.today()
        elif isinstance(day, str):
            day = datetime.datetime.strptime(day, DATE_ISO).date()

        day_str = datetime.date.strftime(day, DATE_ISO)
        cat_info = AvailCatInfo(self.cae)
        rooms = 0
        for hotel_id in hotel_ids:
            if hotel_id == '999':  # unfortunately currently there is no avail data for this pseudo hotel
                rooms -= self.sh_count_res(hotel_ids=['999'], room_cat_prefix=room_cat_prefix, day=day)
            else:
                ret = cat_info.avail_rooms(hotel_id=hotel_id, from_date=day, to_date=day)
                if not isinstance(ret, dict):
                    self._err("sh_avail_rooms(): call to avail_rooms({}, {}, {}) failed with error {}"
                              .format(hotel_id, day, day, ret), self._ctx_no_file + "ShAvailRooms")
                    continue
                for cat_id, cat_data in ret.items():
                    if cat_id.startswith(room_cat_prefix):  # True for all room cats if room_cat_prefix is empty string
                        rooms += ret[cat_id][day_str]['AVAIL']
        return rooms

    def sh_count_res(self, hotel_ids=None, room_cat_prefix='', day=None, res_max_days=27):
        """ counting uncancelled reservations in all the hotels specified by the hotel_ids list with the room
        category matching the first characters of the specified room_cat_prefix string and for a certain day.

        All parameters are web-service-query-param-ready (means they could be passed as str).

        :param hotel_ids:       Optional list of hotel IDs (leave empty for to get the rooms in all hotels accumulated).
        :param room_cat_prefix: Optional room category prefix string (leave empty for all room categories or pass e.g.
                                'S' for a accumulation of all the Studios or '1J' for all 1 bedroom junior rooms).
        :param day:             Optional day (leave empty for to get the available rooms for today's date).
        :param res_max_days:    Optional maximum length of reservation (def=27 days).
        :return:                Number of valid reservations of the specified hotel(s) and room category prefix and
                                with arrivals within the date range day-res_max_days...day.
        """
        if not hotel_ids:
            hotel_ids = self.ho_id_list()  # determine list of IDs of all active/valid Sihot-hotels
        elif isinstance(hotel_ids, str):
            hotel_ids = hotel_ids.split(',')
        if not day:
            day = datetime.date.today()
        elif isinstance(day, str):
            day = datetime.datetime.strptime(day, DATE_ISO).date()
        if isinstance(res_max_days, str):
            res_max_days = int(res_max_days)

        res_len_max_timedelta = datetime.timedelta(days=res_max_days)
        count = 0
        res_search = ResSearch(self.cae)
        for hotel_id in hotel_ids:
            all_recs = res_search.search_res(hotel_id=hotel_id, from_date=day - res_len_max_timedelta, to_date=day)
            if all_recs and isinstance(all_recs, list):
                for rec in all_recs:
                    res_type = rec.val('ResStatus')
                    room_cat = rec.val('ResRoomCat')
                    checked_in = rec.val('ResArrival')
                    checked_out = rec.val('ResDeparture')
                    skip_reasons = []
                    if res_type == 'S':
                        skip_reasons.append("cancelled")
                    if res_type == 'E':
                        skip_reasons.append("erroneous")
                    if not room_cat.startswith(room_cat_prefix):
                        skip_reasons.append("room cat " + room_cat)
                    if not (checked_in.toordinal() <= day.toordinal() < checked_out.toordinal()):
                        skip_reasons.append("out of date range " + str(checked_in) + "..." + str(checked_out))
                    if not skip_reasons:
                        count += 1
                    elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
                        self._warn("AssSysData.sh_count_res(): skipped {} res: {}".format(skip_reasons, rec))
        return count

    def sh_res_data(self, hotel_id='1', gds_no='', res_id='', sub_id=''):
        """

        :param hotel_id:    Sihot hotel id for which the reservation was made.
        :param gds_no:      GDS number of the reservation to fetch (optional, use res_id/sub_id instead).
        :param res_id:      Reservation number (optional, used gds_no instead).
        :param sub_id:      Reservation sub-ordinal number (optional, used gds_no instead).
        :return:            dict of reservation data or str with error message.
        """
        res_fetch = ResFetch(self.cae)
        if gds_no:
            ret = res_fetch.fetch_by_gds_no(ho_id=hotel_id, gds_no=gds_no)
        else:
            ret = res_fetch.fetch_by_res_id(ho_id=hotel_id, res_id=res_id, sub_id=sub_id)
        return ret

    def sh_room_change_to_ass(self, oc, ho_id, res_id, sub_id, room_id, action_time):
        """ move/check in/out guest from/into room_no

        :param oc:              operation code: either 'CI', 'CO', 'CI-RM', 'CO-RM' or 'RC-RM'.
        :param ho_id:           Sihot hotel id (e.g. '1'==BHC).
        :param res_id:          Sihot reservation main id.
        :param sub_id:          Sihot reservation sub id.
        :param room_id:         id (number) of the affected Sihot room.
        :param action_time:     Date and time of check-in/-out.
        :return:                rgr_sf_id or None if error (error message available in self.error_message).
        """
        upd_col_values = dict(rgr_room_id=room_id, rgr_room_last_change=action_time)
        if oc[:2] == 'CI':
            upd_col_values.update(rgr_time_in=action_time, rgr_time_out=None)
        elif oc[:2] == 'CO':
            upd_col_values.update(rgr_time_out=action_time)
        elif oc != 'RC-RM':
            self.error_message = "ASD.sh_room_change_to_ass({}, {}, {}, {}, {}, {}): Invalid operation code"\
                .format(oc, ho_id, res_id, sub_id, room_id, action_time)

        rgr_sf_id = None
        if not self.error_message:
            rgr_sf_id = self.rgr_upsert(upd_col_values,
                                        chk_values=dict(rgr_ho_fk=ho_id, rgr_res_id=res_id, rgr_sub_id=sub_id),
                                        commit=True, returning_column='rgr_sf_id')

        return rgr_sf_id

    # #######################  push/pull/compare action helpers  #######################################################

    def system_records_action(self, system, rec_type, action, **kwargs):
        msg = "ASD.system_records_action({}, {}, {}, {}): ".format(system, rec_type, action, kwargs)
        type_name = ALL_AVAILABLE_RECORD_TYPES.get(rec_type)
        if not type_name:
            self._err(msg + "Unknown record type {}".format(rec_type))
        else:
            method_name = system.lower() + '_' + type_name.lower() + '_' + action.lower()
            method = getattr(self, method_name, None)
            if method:
                self._warn(msg + "Processing {} action against {}/{} system for record type {}/{}"
                           .format(action, ALL_AVAILABLE_SYSTEMS.get(system), system, type_name, rec_type),
                           action.lower() + system + type_name, importance=4)
                try:
                    method(**kwargs)
                except Exception as ex:
                    self._err(msg + "Executing method {} failed with exception {}\n{}"
                              .format(method_name, ex, format_exc(ex)))
            else:
                self._err(msg + "{} action method {} is not implemented for system {} and record type {}"
                          .format(action, method_name, system, rec_type))

    def _acu_clients_pull(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                          field_names=(), exclude_fields=(), filter_records=None):
        """ pulls clients data from the Acumen system """
        '''
        AC_CLIENT_MAP1 = (
            # ('', 'AssId'),
            ('CODE', 'AcuId'),
            ('SF_ID', 'SfId'),
            ('SH_ID', 'ShId'),
            ('SURNAME', 'Surname'),
            ('FORENAME', 'Forename'),
            ('EMAIL', 'Email'),
            ('PHONE', 'Phone'),
            ('EXT_REFS', 'ExtRefs'),
            ('OWNS', 'ProductTypes'),
        )

        # column expression SQL for to fetch client data from Acumen - now migrated into V_CLIENTS_REFS_OWNS
        AC_SQL_AC_ID1 = "CD_CODE"
        AC_SQL_AC_ID2 = "CD_CODE || '" + AC_ID_2ND_COUPLE_SUFFIX + "'"
        AC_SQL_SF_ID1 = "nvl(CD_SF_ID1, (select max(MS_SF_ID) from T_ML, T_MS" \
                        " where ML_CODE = MS_MLREF and MS_SF_ID is not NULL and ML_CDREF = CD_CODE))"
        AC_SQL_SF_ID2 = "CD_SF_ID2"
        AC_SQL_SH_ID1 = "to_char(CD_SIHOT_OBJID)"
        AC_SQL_SH_ID2 = "to_char(CD_SIHOT_OBJID2)"
        AC_SQL_NAME1 = "CD_FNAM1 || ' ' || CD_SNAM1"
        AC_SQL_NAME2 = "CD_FNAM2 || ' ' || CD_SNAM2"
        AC_SQL_EMAIL1 = "F_EMAIL_CLEANED(CD_EMAIL)"
        AC_SQL_EMAIL2 = "F_EMAIL_CLEANED(CD_EMAIL, 1)"
        AC_SQL_PHONE1 = "nvl(CD_HTEL1, nvl(CD_MOBILE1, CD_WTEL1 || CD_WEXT1))"
        AC_SQL_MAIN_RCI = "CD_RCI_REF"
        '''

        self._warn("Fetching client data from Acumen", 'pullAcuClientData', importance=4)

        rec_tpl = Record(system=SDI_ACU, direction=FAD_FROM)
        rec_tpl.add_system_fields(ACU_CLIENT_MAP, sys_fld_indexes=from_field_indexes)
        if field_names or exclude_fields:
            col_names += rec_tpl.leaf_names(system=SDI_ACU, direction=FAD_FROM,
                                            field_names=field_names, exclude_fields=exclude_fields)
        if not col_names:
            col_names = rec_tpl.leaf_names(system=SDI_ACU, direction=FAD_FROM)

        '''
        acu_db = self.connection(SDI_ACU)
        recs = Records()
        if acu_db.select('V_CLIENTS_REFS_OWNS', cols=col_names, chk_values=chk_values,
                         where_group_order=where_group_order, bind_vars=bind_values):
            self.error_message = acu_db.last_err_msg
        else:
            rows = acu_db.fetch_all()
            if acu_db.last_err_msg:
                self.error_message = acu_db.last_err_msg
            else:
                for idx, col_values in enumerate(rows):
                    rec = rec_tpl.copy(deepness=-1)
                    for col_idx, val in enumerate(col_values):
                        rec.set_val(val, col_names[col_idx], system=SDI_ACU, direction=FAD_FROM)
                    rec.pull(from_system=SDI_ASS)
                    if not callable(filter_records) or not filter_records(rec):
                        recs.append(rec)
        '''
        acu_cl = AcumenClient(self.cae, ora_db=self.connection(SDI_ACU, raise_if_error=False))
        self.error_message = acu_cl.fetch_all_valid_from_acu(col_names=col_names, chk_values=chk_values,
                                                             where_group_order=where_group_order,
                                                             bind_values=bind_values, filter_records=filter_records)
        if self.error_message:
            self._err("_acu_clients_pull() error {}".format(self.error_message))
            recs = Records()
        else:
            recs = acu_cl.recs

        return recs

    def acu_clients_pull(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                         field_names=(), exclude_fields=(), filter_records=None, match_fields=()):
        recs = self._acu_clients_pull(col_names=col_names, chk_values=chk_values, where_group_order=where_group_order,
                                      bind_values=bind_values, field_names=field_names, exclude_fields=exclude_fields,
                                      filter_records=filter_records)
        if recs:
            self.clients.merge_records(recs, match_fields=match_fields)

    def acu_clients_compare(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                            field_names=(), exclude_fields=(), filter_records=None,
                            match_fields=()):
        self._warn("Comparing pulled client data against Acumen", 'compareAcuClientData', importance=4)

        if not match_fields:
            match_fields = ['AcuId']

        pulled = self._acu_clients_pull(col_names=col_names, chk_values=chk_values, where_group_order=where_group_order,
                                        bind_values=bind_values, field_names=field_names, exclude_fields=exclude_fields,
                                        filter_records=filter_records)
        if self.error_message:
            dif = ["acu_clients_compare() error {}".format(self.error_message)]
        else:
            # adding 'ExtRefs' to excluded_fields because Oracle's f_stragg() does not have fixed ordering
            dif = self.clients.compare_records(pulled, match_fields=match_fields,
                                               field_names=field_names, exclude_fields=exclude_fields + ('ExtRefs', ),
                                               record_comparator=self.cl_compare_ext_refs)
            for msg in dif:
                self._warn(msg)

        return pulled, dif

    def acu_clients_push(self, field_names=(), exclude_fields=('ProductTypes', ), filter_records=None, match_fields=()):
        self._warn("Pushing client data onto Acumen", 'pushAcuClientData', importance=4)

        ignored_errors = 0
        recs = self.clients
        recs.set_env(system=SDI_ACU, direction=FAD_ONTO)
        acu_cl = AcumenClient(self.cae, ora_db=self.connection(SDI_ACU, raise_if_error=False))
        for rec in recs:
            rec.add_system_fields(ACU_CLIENT_MAP, sys_fld_indexes=onto_field_indexes)
            rec.push(SDI_ACU)
            if not callable(filter_records) or not filter_records(rec):
                # leaf_names() has to be called after add_system_fields()
                field_names = rec.leaf_names(system=SDI_ACU, direction=FAD_ONTO,
                                             field_names=field_names, exclude_fields=exclude_fields,
                                             col_names=rec.sys_name_field_map.keys(), name_type='f')
                err_msg, pkey = acu_cl.save_client(rec, field_names=field_names, match_fields=match_fields, commit=True)
                if err_msg or self.error_message:
                    self.error_message += err_msg
                    msg = "acu_clients_push() error: '{}'".format(self.error_message)
                    if self.cae.get_option('breakOnError'):
                        self._err(msg)
                        break
                    ignored_errors += 1
                    self._warn("Ignoring/Skipping " + msg)
        if ignored_errors:
            self._err("Finished Acumen client push with {} skipped/ignored errors".format(ignored_errors))

    def _ass_clients_pull(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                          field_names=(), exclude_fields=(), filter_records=None):
        self._warn("Fetching client data from AssCache", 'pullAssClientData', importance=4)

        rec_tpl = Record(system=SDI_ASS, direction=FAD_FROM).add_system_fields(ASS_CLIENT_MAP)
        if field_names or exclude_fields:
            col_names += rec_tpl.leaf_names(system=SDI_ASS, direction=FAD_FROM,
                                            field_names=field_names, exclude_fields=exclude_fields)
        if not col_names:
            col_names = rec_tpl.leaf_names(system=SDI_ASS, direction=FAD_FROM)
        # field_names = rec_tpl.leaf_names(sys_names=col_names)

        recs = Records()
        rows = self.cl_fetch_list(col_names=col_names, chk_values=chk_values, where_group_order=where_group_order,
                                  bind_values=bind_values)
        if self.error_message:
            self._err("_ass_clients_pull() error {}".format(self.error_message))
        else:
            for col_values in rows:
                rec = rec_tpl.copy(deepness=-1)
                for col_idx, val in enumerate(col_values):
                    rec.set_val(val, col_names[col_idx], system=SDI_ASS, direction=FAD_FROM)
                rec.pull(from_system=SDI_ASS)
                if not callable(filter_records) or not filter_records(rec):
                    recs.append(rec)
        return recs

    def ass_clients_pull(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                         field_names=(), exclude_fields=(), filter_records=None, match_fields=()):
        recs = self._ass_clients_pull(col_names=col_names, chk_values=chk_values, where_group_order=where_group_order,
                                      bind_values=bind_values, field_names=field_names, exclude_fields=exclude_fields,
                                      filter_records=filter_records)
        if recs:
            self.clients.merge_records(recs, match_fields=match_fields)

    def ass_clients_push(self, field_names=(), exclude_fields=(), filter_records=None, match_fields=()):
        self._warn("Pushing client data onto AssCache", 'pushAssClientData', importance=4)

        ignored_errors = 0
        recs = self.clients
        recs.set_env(system=SDI_ASS, direction=FAD_ONTO)
        for rec in recs:
            rec.add_system_fields(ASS_CLIENT_MAP)
            rec.push(SDI_ASS)
            if not callable(filter_records) or not filter_records(rec):
                # leaf_names() has to be called after add_system_fields()
                field_names = rec.leaf_names(system=SDI_ASS, direction=FAD_ONTO,
                                             field_names=field_names, exclude_fields=exclude_fields,
                                             col_names=rec.sys_name_field_map.keys(), name_type='f')
                if not self.cl_save(rec, field_names=field_names, match_fields=match_fields, commit=True) \
                        or self.error_message:
                    msg = "ass_clients_push() error: '{}'".format(self.error_message)
                    if self.cae.get_option('breakOnError'):
                        self._err(msg)
                        break
                    ignored_errors += 1
                    self._warn("Ignoring/Skipping " + msg)
        if ignored_errors:
            self._err("Finished AssCache client push with {} skipped/ignored errors".format(ignored_errors))

    def ass_clients_compare(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                            field_names=(), exclude_fields=(), filter_records=None, match_fields=()):
        self._warn("Comparing pulled client data against AssCache", 'compareAssClientData', importance=4)

        if not match_fields:
            match_fields = ['AssId']

        pulled = self._ass_clients_pull(col_names=col_names, chk_values=chk_values, where_group_order=where_group_order,
                                        bind_values=bind_values, field_names=field_names, filter_records=filter_records)
        if self.error_message:
            dif = ["ass_clients_compare() error {}".format(self.error_message)]
        else:
            dif = self.clients.compare_records(pulled, match_fields=match_fields,
                                               field_names=field_names, exclude_fields=exclude_fields,  # +('ExtRefs',),
                                               record_comparator=self.cl_compare_ext_refs)
            for msg in dif:
                self._warn(msg)

        return pulled, dif

    def _ass_reservations_pull(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                               field_names=(), exclude_fields=(), filter_records=None):
        self._warn("Fetching reservation data from AssCache", 'pullAssResData', importance=4)

        rec_tpl = Record(system=SDI_ASS, direction=FAD_FROM).add_system_fields(ASS_CLIENT_MAP + ASS_RES_MAP)
        if field_names or exclude_fields:
            col_names += rec_tpl.leaf_names(system=SDI_ASS, direction=FAD_FROM,
                                            field_names=field_names, exclude_fields=exclude_fields)
        if not col_names:
            col_names = rec_tpl.leaf_names(system=SDI_ASS, direction=FAD_FROM)
        # field_names = rec_tpl.leaf_names(sys_names=col_names)

        rgr_cols = [cn for cn in col_names if cn.startswith('rgr_')]
        rgc_cols = [cn for cn in col_names if cn.startswith('rgc_')]
        if rgc_cols and 'rgr_pk' not in rgr_cols:
            rgr_cols.append('rgr_pk')

        rows = self.rgr_fetch_list(col_names=rgr_cols, chk_values=chk_values, where_group_order=where_group_order,
                                   bind_values=bind_values)
        recs = Records()
        for rgr_values in rows:
            rec = rec_tpl.copy(deepness=-1)
            for col_idx, val in enumerate(rgr_values):
                col_name = rgr_cols[col_idx]
                rec.set_val(val, col_name, system=SDI_ASS, direction=FAD_FROM)
                if col_name == 'rgr_order_cl_fk' and val:
                    cl_col_names = [cn for cn in col_names if cn.startswith('cl_')]
                    order_data = self.cl_fetch_list(col_names=cl_col_names, chk_values=dict(cl_pk=val))
                    if len(order_data) != 1:
                        self._warn("_ass_reservation_pull() didn't find orderer {} in res {}".format(val, rgr_values))
                    else:
                        for cl_col_idx, cl_value in enumerate(order_data[0]):
                            rec.set_val(cl_value, cl_col_names[cl_col_idx], system=SDI_ASS, direction=FAD_FROM)
            if rgc_cols:
                rgr_pk = rgr_values[rgr_cols.index('rgr_pk')]
                rgc_rows = self.rgc_fetch_list(col_names=rgc_cols, chk_values=dict(rgc_rgr_fk=rgr_pk),
                                               where_group_order="ORDER BY rgc_room_seq, rgc_pers_seq")
                for row_idx, rgc_values in enumerate(rgc_rows):
                    for col_idx, val in enumerate(rgc_values):
                        col_name = rgc_cols[col_idx]
                        idx_pre = ('ResPersons', row_idx, )
                        rec.set_val(val, *idx_pre, col_name, system=SDI_ASS, direction=FAD_FROM)
                        if val and col_name == 'rgc_occup_cl_fk':
                            if 'PersAcuId' in rec.value(*idx_pre):
                                acu_id = self.cl_ac_id_by_ass_id(val)
                                if acu_id:
                                    rec.set_val(acu_id, *idx_pre, 'PersAcuId', system=SDI_ASS, direction=FAD_FROM)
                            sf_id = self.cl_sf_id_by_ass_id(val)
                            if sf_id:
                                rec.set_val(sf_id, *idx_pre, 'PersSfId', system=SDI_ASS, direction=FAD_FROM)
                            sh_id = self.cl_sh_id_by_ass_id(val)
                            if sh_id:
                                rec.set_val(sh_id, *idx_pre, 'PersShId', system=SDI_ASS, direction=FAD_FROM)

            rec.pull(from_system=SDI_ASS)
            if not callable(filter_records) or not filter_records(rec):
                recs.append(rec)

        if self.error_message:
            self._err("_ass_reservations_pull() error {}".format(self.error_message))
        return recs

    def ass_reservations_pull(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                              field_names=(), exclude_fields=(), filter_records=None, match_fields=()):
        recs = self._ass_reservations_pull(col_names=col_names, chk_values=chk_values,
                                           where_group_order=where_group_order, bind_values=bind_values,
                                           field_names=field_names, exclude_fields=exclude_fields,
                                           filter_records=filter_records)
        if recs:
            self.reservations.merge_records(recs, match_fields=match_fields)

    def ass_reservations_push(self, field_names=(), exclude_fields=(), filter_records=None, match_fields=()):
        self._warn("Pushing reservation data onto AssCache", 'pushAssResData', importance=4)

        ignored_errors = 0
        recs = self.reservations
        recs.set_env(system=SDI_ASS, direction=FAD_ONTO)
        for rec in recs:
            rec.add_system_fields(ASS_CLIENT_MAP + ASS_RES_MAP)
            rec.push(SDI_ASS)
            if not callable(filter_records) or not filter_records(rec):
                # leaf_names() has to be called after add_system_fields()
                field_names = rec.leaf_names(system=SDI_ASS, direction=FAD_ONTO,
                                             field_names=field_names, exclude_fields=exclude_fields,
                                             col_names=rec.sys_name_field_map.keys(), name_type='f')
                if not self.res_save(rec, field_names=field_names, match_fields=match_fields, commit=True):
                    msg = "ass_reservations_push() error: '{}'".format(self.error_message)
                    if self.cae.get_option('breakOnError'):
                        self._err(msg)
                        break
                    ignored_errors += 1
                    self._warn("Ignoring/Skipping " + msg)
        if ignored_errors:
            self._err("Finished AssCache reservation push with {} skipped/ignored errors".format(ignored_errors))

    def ass_reservations_compare(self, col_names=(), chk_values=None, where_group_order='', bind_values=None,
                                 field_names=(), exclude_fields=(), filter_records=None, match_fields=()):
        self._warn("Comparing pulled reservation data against AssCache", 'compareAssResData', importance=4)

        if not match_fields:
            match_fields = ['ResHotelId', 'ResId', 'ResSubId']

        pulled = self._ass_reservations_pull(col_names=col_names, chk_values=chk_values,
                                             where_group_order=where_group_order, bind_values=bind_values,
                                             field_names=field_names, filter_records=filter_records)
        if self.error_message:
            dif = ["ass_reservations_compare() error {}".format(self.error_message)]
        else:
            dif = self.reservations.compare_records(pulled, match_fields=match_fields,
                                                    field_names=field_names, exclude_fields=exclude_fields)
            for msg in dif:
                self._warn(msg)

        return pulled, dif

    def _sf_clients_pull(self, col_names=(), chk_values=None, where_group_order='',
                         field_names=(), exclude_fields=(), filter_records=None):
        def _prepare(obj, c_names, f_names, x_names):
            c_names = list(c_names)     # copy passed list/tuple for to not change col_names
            tpl = Record(system=SDI_SF, direction=FAD_FROM).add_system_fields(SF_CLIENT_MAPS[obj])
            if f_names or x_names:
                c_names += tpl.leaf_names(system=SDI_SF, direction=FAD_FROM,
                                          field_names=f_names, exclude_fields=x_names)
            if not c_names:
                c_names = tpl.leaf_names(system=SDI_SF, direction=FAD_FROM)
            return tpl, c_names

        def _fetch(obj, c_names, c_values, where_sql, add_ers):
            if c_values:
                whx = " AND ".join([k + " = " + soql_value_literal(v) for k, v in c_values.items()])
                where_sql = "(" + where_sql + ")" + " AND " + whx if where_sql else whx
            if where_sql:
                where_sql = "WHERE " + where_sql
            if add_ers and obj != 'Lead':
                # ExtRefs got already removed with leaf_indexes(), so no need to do: c_names.pop('ExtRefs')
                # c_names.append("(SELECT Name, Reference_No_or_ID__c FROM {})"
                #                .format('External_References__pr' if obj == 'Account' else 'External_References__r'))
                c_names.append("(SELECT Name, Reference_No_or_ID__c FROM External_References__r)")
            return sf_conn.soql_query_all("SELECT {} FROM {} {}".format(", ".join(c_names), obj, where_sql))

        def _retrieve(obj, tpl, result, add_ers):
            # rel_name = 'External_References__pr' if obj == 'Account' else 'External_References__r'
            rel_name = 'External_References__r'
            for sf_cols in result['records']:  # list of client OrderedDicts
                rec = tpl.copy(deepness=-1)
                for col_name in sf_cols.keys():
                    if col_name in rec:
                        rec.set_val(sf_cols[col_name], col_name, system=SDI_SF, direction=FAD_FROM)
                if add_ers:
                    ers = Records()
                    if obj != 'Lead':
                        if sf_cols[rel_name]:
                            ers.extend([Record(fields=dict(Type=_['Name'].split(EXT_REF_TYPE_ID_SEP)[0],
                                                           Id=_['Reference_No_or_ID__c']))
                                        for _ in sf_cols[rel_name]['records']])
                        rci_id = sf_cols.get(sf_fld_sys_name('RciId', obj))
                        if rci_id and not [er_rec for er_rec in ers
                                           if er_rec['Type'].startswith(EXT_REF_TYPE_RCI) and er_rec['Id'] == rci_id]:
                            ers.append(Record(fields=dict(Type=EXT_REF_TYPE_RCI, Id=rci_id)))
                    rec.set_val(ers, 'ExtRefs', system=SDI_SF, direction=FAD_FROM)  # ADD field for other systems
                rec.pull(from_system=SDI_SF)
                if not callable(filter_records) or not filter_records(rec):
                    recs.append(rec)

        self._warn("Fetching client data from Salesforce", 'pullSfClientData', importance=4)

        sf_obj = 'Account'
        sf_conn = self.connection(SDI_SF)
        has_ers = 'ExtRefs' not in exclude_fields and ('ExtRefs' in field_names if field_names else False)

        recs = Records()
        rec_tpl, cols = _prepare(sf_obj, col_names, field_names, exclude_fields)
        response = _fetch(sf_obj, cols, chk_values, where_group_order, has_ers)
        if sf_conn.error_msg:
            self.error_message = "sf_clients_pull() Account fetch error: {}".format(sf_conn.error_msg)
        elif response['totalSize'] > 0:
            _retrieve(sf_obj, rec_tpl, response, has_ers)

            sf_obj = 'Lead'
            rec_tpl, cols = _prepare(sf_obj, col_names, field_names, exclude_fields)
            if 'AcumenClientRef__pc' in chk_values:     # TODO: remove if Lead is no longer needed
                chk_values = chk_values.copy()
                chk_values['Acumen_Client_Reference__c'] = chk_values.pop('AcumenClientRef__pc')
            response = _fetch(sf_obj, cols, chk_values,
                              "IsConverted = false" + (" and (" + where_group_order + ")" if where_group_order else ""),
                              has_ers)
            if sf_conn.error_msg:
                self.error_message = "sf_clients_pull() Lead append error: {}".format(sf_conn.error_msg)
            elif response['totalSize'] > 0:
                _retrieve(sf_obj, rec_tpl, response, has_ers)

        if self.error_message:
            self._err("_sf_clients_pull() error {}".format(self.error_message))
        return recs

    def sf_clients_pull(self, col_names=(), chk_values=None, where_group_order='',
                        field_names=(), exclude_fields=(), filter_records=None, match_fields=(), **kwargs):
        if kwargs:      # bind_values is not supported by SF PULL
            self.error_message = "The action argument(s) {} are not supported by SF client PULL action".format(kwargs)
            self._err(self.error_message)
            return

        recs = self._sf_clients_pull(col_names=col_names, chk_values=chk_values,
                                     where_group_order=where_group_order,
                                     field_names=field_names, exclude_fields=exclude_fields,
                                     filter_records=filter_records)
        if recs:
            self.reservations.merge_records(recs, match_fields=match_fields)

    def sf_clients_push(self, field_names=(), exclude_fields=(), filter_records=None, match_fields=()):
        assert not match_fields or (match_fields[0] == SF_DEF_SEARCH_FIELD and len(match_fields) == 1), \
            "sf_clients_push() only supports the match field {}, but got {}".format(SF_DEF_SEARCH_FIELD, match_fields)

        self._warn("Pushing client data onto Salesforce", 'pushSfClientData', importance=4)

        ignored_errors = 0
        sf_conn = self.connection(SDI_SF)
        recs = self.clients
        recs.set_env(system=SDI_SF, direction=FAD_ONTO)
        for rec in recs:
            rec.add_system_fields(SF_CLIENT_MAPS['Account'])
            rec.push(SDI_SF)
            if not callable(filter_records) or not filter_records(rec):
                # leaf_names() has to be called after add_system_fields()
                field_names = rec.leaf_names(system=SDI_SF, direction=FAD_ONTO,
                                             field_names=field_names, exclude_fields=exclude_fields,
                                             col_names=rec.sys_name_field_map.keys(), name_type='f')
                sf_id, err, msg = sf_conn.cl_upsert(rec, filter_fields=lambda f: f.name() not in field_names,
                                                    sf_obj='Account')
                if err:
                    err = "sf_clients_push() error: '{}'".format(err)
                    if self.cae.get_option('breakOnError'):
                        self.error_message = err
                        self._err(err)
                        break
                    ignored_errors += 1
                    self._warn("Ignoring/skipping " + err, importance=3)
                elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    self._warn("sf_clients_push(): client {} upserted; msg='{}'; rec={}".format(sf_id, msg, rec))
        if ignored_errors:
            self._err("Finished SF client push with {} skipped/ignored errors".format(ignored_errors))

    def sf_clients_compare(self, col_names=(), chk_values=None, where_group_order='',
                           field_names=(), exclude_fields=(), filter_records=None, match_fields=(), **kwargs):
        if kwargs:      # bind_values is not supported by SF PULL
            self.error_message = "The action argument(s) {} are not supported by SF client COMPARE".format(kwargs)
            self._err(self.error_message)
            return

        self._warn("Comparing pulled client data against Salesforce", 'compareSfClientData', importance=4)

        if not match_fields:
            match_fields = [SF_DEF_SEARCH_FIELD]

        pulled = self._sf_clients_pull(col_names=col_names, chk_values=chk_values, where_group_order=where_group_order,
                                       field_names=field_names, filter_records=filter_records)
        if self.error_message:
            dif = ["sf_clients_compare() error {}".format(self.error_message)]
        else:
            dif = self.clients.compare_records(pulled, match_fields=match_fields,
                                               field_names=field_names,  exclude_fields=exclude_fields,
                                               record_comparator=self.cl_compare_ext_refs)
            for msg in dif:
                self._warn(msg)

        return pulled, dif

    def _sf_reservations_pull(self, col_names=(), chk_values=None, where_group_order='',
                              field_names=(), exclude_fields=(), filter_records=None):
        self._warn("Fetching reservation data from Salesforce", 'pullSfResData', importance=4)

        rec_tpl = Record(system=SDI_SF, direction=FAD_FROM).add_system_fields(SF_RES_MAP)
        if field_names or exclude_fields:
            col_names += rec_tpl.leaf_names(system=SDI_SF, direction=FAD_FROM,
                                            field_names=field_names, exclude_fields=exclude_fields)
        if not col_names:
            col_names = rec_tpl.leaf_names(system=SDI_SF, direction=FAD_FROM)
        # field_names = rec_tpl.leaf_names(sys_names=col_names)

        sf_conn = self.connection(SDI_SF)
        recs = Records()
        rows = sf_conn.res_fetch_list(col_names=col_names, chk_values=chk_values, where_group_order=where_group_order)
        if not rows or sf_conn.error_msg:
            self._err("_sf_reservations_pull() error {}".format(sf_conn.error_msg), 'pullSfResDataPrepErr',
                      importance=3, exit_code=150)
        else:
            for res_dict in rows:
                rec = rec_tpl.copy(deepness=-1)
                for col, val in res_dict.items():
                    rec.set_val(val, col, system=SDI_SF, direction=FAD_FROM)
                rec.pull(from_system=SDI_SF)
                if not callable(filter_records) or not filter_records(rec):
                    recs.append(rec)
        return recs

    def sf_reservations_pull(self, col_names=(), chk_values=None, where_group_order='',
                             field_names=(), exclude_fields=(), filter_records=None, match_fields=(), **kwargs):
        if kwargs:      # bind_values is not supported by SF PULL
            self.error_message = "The action argument(s) {} are not supported by SF reservation PULL".format(kwargs)
            self._err(self.error_message)
        else:
            recs = self._sf_reservations_pull(col_names=col_names, chk_values=chk_values,
                                              where_group_order=where_group_order,
                                              field_names=field_names, exclude_fields=exclude_fields,
                                              filter_records=filter_records)
            if recs:
                self.reservations.merge_records(recs, match_fields=match_fields)

    def sf_reservations_compare(self, col_names=(), chk_values=None, where_group_order='',
                                field_names=(), exclude_fields=(), filter_records=None, match_fields=(), **kwargs):
        if kwargs:      # bind_values is not supported by SF PULL
            self.error_message = "The action argument(s) {} are not supported by SF reservation COMPARE".format(kwargs)
            self._err(self.error_message)
            return

        self._warn("Comparing pulled reservation data against Salesforce", 'compareSfResData', importance=4)

        if not match_fields:
            match_fields = ['ResHotelId', 'ResId', 'ResSubId']

        pulled = self._sf_reservations_pull(col_names=col_names, chk_values=chk_values,
                                            where_group_order=where_group_order, field_names=field_names,
                                            filter_records=filter_records)
        if self.error_message:
            dif = ["sf_reservations_compare() error {}".format(self.error_message)]
        else:
            dif = self.reservations.compare_records(pulled, match_fields=match_fields,
                                                    field_names=field_names, exclude_fields=exclude_fields)
            for msg in dif:
                self._warn(msg)

        return pulled, dif

    def sf_reservations_push(self, field_names=(), exclude_fields=(), filter_records=None, **kwargs):
        if kwargs:
            self.error_message = "The action argument(s) {} are not supported by SF reservation PUSH".format(kwargs)
            self._err(self.error_message)
            return

        self._warn("Pushing reservation data onto Salesforce", 'pushSfResData', importance=4)

        ignored_errors = 0
        sf_conn = self.connection(SDI_SF)
        recs = self.reservations
        recs.set_env(system=SDI_SF, direction=FAD_ONTO)
        for rec in recs:
            rec.add_system_fields(SF_CLIENT_MAPS['Account'] + SF_RES_MAP)
            rec.push(SDI_SF)
            if not callable(filter_records) or not filter_records(rec):
                # leaf_names() has to be called after add_system_fields()
                field_names = rec.leaf_names(system=SDI_SF, direction=FAD_ONTO,
                                             field_names=field_names, exclude_fields=exclude_fields,
                                             col_names=rec.sys_name_field_map.keys(), name_type='f')
                cl_id, res_id, err = sf_conn.res_upsert(rec, filter_fields=lambda f: f.name() not in field_names)
                if err:
                    err = "sf_reservations_push() error: '{}'".format(err)
                    if self.cae.get_option('breakOnError'):
                        self.error_message = err
                        self._err(err)
                        break
                    ignored_errors += 1
                    self._warn("Ignoring/skipping " + err, importance=3)
                elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    self._warn("sf_reservations_push(): reservation {} upserted; client={}; rec={}"
                               .format(res_id, cl_id, rec))
        if ignored_errors:
            self._err("Finished SF reservation push with {} skipped/ignored errors".format(ignored_errors))

    def _sh_clients_pull(self, chk_values=None, field_names=(), exclude_fields=(), filter_records=None):
        assert chk_values, "_sh_clients_pull() expects non-empty chk_values"

        self._warn("Fetching clients data from Sihot", 'pullShClientData', importance=4)

        recs = Records()
        if chk_values.get('obj_id'):
            rec = ClientFetch(self.cae).fetch_client(chk_values['obj_id'], field_names=field_names)
            recs_or_err = rec if isinstance(rec, str) else [rec]
        else:
            recs_or_err = ClientSearch(self.cae).search_clients(field_names=field_names, **chk_values)
        if isinstance(recs_or_err, str):
            self.error_message = recs_or_err
        else:
            for sh_rec in recs_or_err:
                rec = sh_rec.copy(deepness=-1,
                                  filter_fields=lambda f: field_names and f.name() not in field_names
                                  or f.name() in exclude_fields)
                rec.pull(SDI_SH)
                if not callable(filter_records) or not filter_records(rec):
                    recs.append(rec)

        if self.error_message:
            self._err("_sh_clients_pull() error {}".format(self.error_message))
        return recs

    def sh_clients_pull(self, chk_values=None, field_names=(), exclude_fields=(), filter_records=None,
                        match_fields=(), **kwargs):
        sh_conn = self.connection(SDI_SH)
        match_fields = [sh_conn.clients_match_field_init(match_fields)]
        if kwargs:      # col_names, where_group_order and bind_values are not supported by Sihot PULL
            self.error_message = "The action argument(s) {} are not supported by Sihot client PULL".format(kwargs)
            self._err(self.error_message)
        else:
            recs = self._sh_clients_pull(chk_values=chk_values, field_names=field_names, exclude_fields=exclude_fields,
                                         filter_records=filter_records)
            if recs:
                self.reservations.merge_records(recs, match_fields=match_fields)

    def sh_clients_push(self, field_names=(), exclude_fields=(), filter_records=None, **kwargs):
        if kwargs:      # most action arguments are not supported by Sihot PUSH
            self.error_message = "The action argument(s) {} are not supported by Sihot client PUSH".format(kwargs)
            self._err(self.error_message)
            return

        self._warn("Pushing client data onto Sihot", 'pushShClientData', importance=4)

        ignored_errors = 0
        recs = self.clients
        recs.set_env(system=SDI_SH, direction=FAD_ONTO)
        for rec in recs:
            rec.add_system_fields(SH_CLIENT_MAP)
            rec.push(SDI_SH)
            if not callable(filter_records) or not filter_records(rec):
                if field_names or exclude_fields:
                    rec = rec.copy(filter_fields=lambda f: field_names and f.name() not in field_names
                                   or f.name() in exclude_fields)
                err = ClientToSihot(self.cae).send_client_to_sihot(rec)
                if err:
                    err = "sh_clients_push() error: '{}'".format(err)
                    if self.cae.get_option('breakOnError'):
                        self.error_message = err
                        self._err(err)
                        break
                    ignored_errors += 1
                    self._warn("Ignoring/Skipping " + err, importance=3)
                elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    self._warn("sh_clients_push(): client upserted; rec={}".format(rec))
        if ignored_errors:
            self._err("Finished Sihot client push with {} skipped/ignored errors".format(ignored_errors))

    def sh_clients_compare(self, chk_values=None, field_names=(), exclude_fields=('ExtRefs', 'ProductTypes', ),
                           filter_records=None, match_fields=(), **kwargs):
        if kwargs:
            self.error_message = "The action argument(s) {} are not supported by Sihot client COMPARE".format(kwargs)
            self._err(self.error_message)
            return

        self._warn("Comparing pulled client data against Sihot", 'compareShClientData', importance=4)

        sh_conn = self.connection(SDI_SH)
        match_fields = [sh_conn.clients_match_field_init(match_fields)]

        pulled = self._sh_clients_pull(chk_values=chk_values, field_names=field_names, exclude_fields=exclude_fields,
                                       filter_records=filter_records)
        if self.error_message:
            dif = ["sh_clients_compare() error {}".format(self.error_message)]
        else:
            dif = self.clients.compare_records(pulled, match_fields=match_fields,
                                               field_names=field_names, exclude_fields=exclude_fields)
            for msg in dif:
                self._warn(msg)

        return pulled, dif

    def _sh_reservations_pull(self, chk_values=None, field_names=(), exclude_fields=(), filter_records=None):
        assert chk_values, "_sh_reservations_pull() expects non-empty chk_values"

        self._warn("Fetching reservations data from Sihot", 'pullShResData', importance=4)

        recs = Records()
        recs_or_err = ResSearch(self.cae).search_res(**chk_values)
        if isinstance(recs_or_err, str):
            self.error_message = recs_or_err
        else:
            for sh_rec in recs_or_err:
                rec = sh_rec.copy(deepness=-1,
                                  filter_fields=lambda f: field_names and f.name() not in field_names
                                  or f.name() in exclude_fields)
                rec.pull(SDI_SH)
                if not callable(filter_records) or not filter_records(rec):
                    recs.append(rec)

        if self.error_message:
            self._err("_sf_reservations_pull() error {}".format(self.error_message))
        return recs

    def sh_reservations_pull(self, chk_values=None, field_names=(), exclude_fields=(), filter_records=None,
                             match_fields=(), **kwargs):
        if not match_fields:
            match_fields = ['ResHotelId', 'ResId', 'ResSubId']

        if kwargs:      # col_names, where_group_order and bind_values are not supported by Sihot PULL
            self.error_message = "The action argument(s) {} are not supported by Sihot reservation PULL".format(kwargs)
            self._err(self.error_message)
        else:
            recs = self._sh_reservations_pull(chk_values=chk_values,
                                              field_names=field_names, exclude_fields=exclude_fields,
                                              filter_records=filter_records)
            if recs:
                self.reservations.merge_records(recs, match_fields=match_fields)

    def sh_reservations_compare(self, chk_values=None, field_names=(), exclude_fields=(), filter_records=None,
                                match_fields=(), **kwargs):
        if kwargs:
            self.error_message = "Action argument(s) {} are not supported by Sihot reservation COMPARE".format(kwargs)
            self._err(self.error_message)
            return

        self._warn("Comparing pulled reservation data against Sihot", 'compareShResData', importance=4)

        if not match_fields:
            match_fields = ['ResHotelId', 'ResId', 'ResSubId']

        pulled = self._sh_reservations_pull(chk_values=chk_values,
                                            field_names=field_names, exclude_fields=exclude_fields,
                                            filter_records=filter_records)
        if self.error_message:
            dif = ["sh_reservations_compare() error {}".format(self.error_message)]
        else:
            dif = self.reservations.compare_records(pulled, match_fields=match_fields,
                                                    field_names=field_names, exclude_fields=exclude_fields)
            for msg in dif:
                self._warn(msg)

        return pulled, dif

    def sh_reservation_push(self, field_names=(), exclude_fields=(), filter_records=None, **kwargs):
        if kwargs:      # most action arguments are not supported by Sihot PUSH
            self.error_message = "The action argument(s) {} are not supported by Sihot reservation PUSH".format(kwargs)
            self._err(self.error_message)
            return

        self._warn("Pushing reservation data onto Sihot", 'pushShResData', importance=4)

        err, ignored_errors = "", list()
        recs = self.reservations
        recs.set_env(system=SDI_SH, direction=FAD_ONTO)
        for rec in recs:
            rec.add_system_fields(SH_CLIENT_MAP + SH_RES_MAP)
            rec.push(SDI_SH)
            if not callable(filter_records) or not filter_records(rec):
                if field_names or exclude_fields:
                    rec = rec.copy(filter_fields=lambda f: field_names and f.name() not in field_names
                                   or f.name() in exclude_fields)
                rts = ResToSihot(self.cae)
                err = rts.send_res_to_sihot(rec)
                if err:
                    err = "sh_reservations_push() error: '{}'; WARNINGS='{}'".format(err, rts.get_warnings())
                    if self.cae.get_option('breakOnError'):
                        break
                    ignored_errors.append(err)
                    self._warn("Ignoring/Skipping " + err, importance=3)
                elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    self._warn("sh_reservations_push(): reservation upserted; rec={}".format(rec))

        if ignored_errors:
            err = "Sihot reservation push had {} ignored errors:\n{}".format(len(ignored_errors), ppf(ignored_errors))
        if err:
            self.error_message = err
            self._err(err)
