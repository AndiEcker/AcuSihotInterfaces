import datetime
import pprint
import re

from ae_db import OraDB, PostgresDB
from ae_console_app import uprint, DATE_ISO, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE
from ae_notification import add_notification_options, init_notification
from acif import add_ac_options
from sxmlif import AvailCatInfo, GuestSearch, ClientToSihot, ResSearch, ResFetch
from sfif import add_sf_options, prepare_connection, ensure_long_id, obj_from_id, DEF_CLIENT_OBJ, DETERMINE_CLIENT_OBJ
from shif import (add_sh_options, print_sh_options, elem_value, pax_count, gds_number,
                  gds_no_to_ids, res_no_to_ids, obj_id_to_res_no, ResBulkFetcher, SH_DATE_FORMAT)


# special client record type ids
CLIENT_REC_TYPE_ID_OWNERS = '012w0000000MSyZAAW'  # 15 digit ID == 012w0000000MSyZ

# external references separator
EXT_REFS_SEP = ','

# external reference type=id separator and types (also used as Sihot Matchcode/GDS prefix)
EXT_REF_TYPE_ID_SEP = '='
EXT_REF_TYPE_RCI = 'RCI'
EXT_REF_TYPE_RCIP = 'RCIP'

# SQL column expression merging wrongly classified Acumen external ref types holding RCI member IDs
AC_SQL_EXT_REF_TYPE = "CASE WHEN CR_TYPE in ('" + EXT_REF_TYPE_RCIP + "', 'SPX')" \
    " then '" + EXT_REF_TYPE_RCI + "' else CR_TYPE end"


mail_re = re.compile('[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+\.[a-zA-Z]{2,4}$')

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

# tuple indexes for Reservation Inventory data (ass_cache.res_inventories/AssSysData.res_inv_data)
_RI_PK = 0
_WKREF = 1
_HOTEL_ID = 2
_YEAR = 3
_ROREF = 4
_SWAPPED = 5
_GRANTED = 6
_POINTS = 7
_COMMENT = 8


# default search fields for external systems (SF e.g. used by AssSysData.sf_client_field_data())
SF_DEF_SEARCH_FIELD = 'SfId'
SF_DEF_RES_SEARCH_FIELD = 'ReservationOpportunityId'
SH_DEF_SEARCH_FIELD = 'ShId'


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

    ret_dict['assSysData'] = conf_data = AssSysData(cae, err_logger=err_logger, warn_logger=warn_logger,
                                                    used_systems_msg_prefix=used_systems_msg_prefix)
    sys_ids = list()
    if conf_data.ass_db:
        uprint('AssCache database name and user:', cae.get_option('assDSN'), cae.get_option('assUser'))
        sys_ids.append(cae.get_option('assDSN'))
    if conf_data.acu_db:
        uprint('Acumen database TNS and user:', cae.get_option('acuDSN'), cae.get_option('acuUser'))
        sys_ids.append(cae.get_option('acuDSN'))
    if conf_data.sf_conn:
        uprint("Salesforce " + ("sandbox" if conf_data.sf_sandbox else "production") + " user/client-id:",
               cae.get_option('sfUser'), cae.get_option('sfClientId', default_value=cae.app_name()))
        sys_ids.append("SBox" if conf_data.sf_sandbox else "Prod")
    if conf_data.sh_conn:
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


# Acumen, Salesforce and Sihot field name re-mappings
#   AssSysDataClientsIdx    AssSysData.clients columns/fields index (like fetched with view v_clients_refs_owns)
FIELD_NAMES = dict(AssId=dict(Desc="AssCache client PKey", AssSysDataClientsIdx=_ASS_ID,
                              AssDb='cl_pk',
                              Lead='AssCache_Id__c', Contact='AssCache_Id__c', Account='AssCache_Id__c',
                              Sihot=''),
                   AcId=dict(Desc="Acumen client reference", AssSysDataClientsIdx=_AC_ID,
                             AssDb='cl_ac_id', AcDb='CD_CODE', Lead='Acumen_Client_Reference__c', Contact='CD_CODE__c',
                             Account='CD_CODE__pc', Sihot='MATCHCODE'),
                   SfId=dict(Desc="Salesforce client Id", AssSysDataClientsIdx=_SF_ID,
                             AssDb='cl_sf_id', AcDb='CD_SF_ID1',
                             Lead='id', Contact='id', Account='id',     # was Id but test_sfif.py needs lower case id
                             Sihot='MATCH-SM'),
                   ShId=dict(Desc="Sihot guest ID", AssSysDataClientsIdx=_SH_ID,
                             AssDb='cl_sh_id', AcDb='CD_SIHOT_OBJID', Lead='Sihot_Guest_Object_Id__c',
                             Contact='Sihot_Guest_Object_Id__c', Account='Sihot_Guest_Object_Id__c', Sihot='OBJID'),
                   Name=dict(Desc="Client name", AssSysDataClientsIdx=_NAME,
                             AssDb='cl_name', Sihot=dict(getter=lambda shd: shd['NAME-2'] + ' ' + shd['NAME-1'])),
                   Email=dict(Desc="Client email", AssSysDataClientsIdx=_EMAIL,
                              AssDb='cl_email', AcDb='CD_EMAIL', Account='PersonEmail',
                              Sihot=dict(in_list=['EMAIL-1', 'EMAIL-2'])),
                   Phone=dict(Desc="Client phone", AssSysDataClientsIdx=_PHONE,
                              AssDb='cl_phone', AcDb='CD_HTEL1', Account='PersonHomePhone',
                              Sihot=dict(in_list=['PHONE-1', 'PHONE-2', 'MOBIL-1', 'MOBIL-2'])),
                   ExtRefs=dict(Desc="Client external references", AssSysDataClientsIdx=_EXT_REFS),
                   Products=dict(Desc="Products owned by client", AssSysDataClientsIdx=_PRODUCTS),
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


def field_desc(code_field_name):
    if code_field_name in FIELD_NAMES:
        return FIELD_NAMES.get(code_field_name).get('Desc', "")


def field_clients_idx(code_field_name):
    if code_field_name in FIELD_NAMES:
        return FIELD_NAMES.get(code_field_name).get('AssSysDataClientsIdx', -1)


def ass_fld_name(code_field_name):
    ass_field_name = code_field_name
    field_map = FIELD_NAMES.get(code_field_name)
    if field_map:
        ass_field_name = field_map.get('AssDb', code_field_name)
    return ass_field_name


def ac_fld_name(code_field_name):
    ac_field_name = ""
    field_map = FIELD_NAMES.get(code_field_name)
    if field_map:
        ac_field_name = field_map.get('AcDb', code_field_name)
    return ac_field_name


def sf_fld_name(code_field_name, sf_obj):
    sf_field_name = code_field_name
    field_map = FIELD_NAMES.get(code_field_name)
    if field_map:
        sf_field_name = field_map.get(sf_obj, code_field_name)
    return sf_field_name


def sh_fld_name(code_field_name):
    sh_field_name = ""
    field_map = FIELD_NAMES.get(code_field_name)
    if field_map:
        sh_field_name = field_map.get('Sihot', code_field_name)
    return sh_field_name


def sh_fld_value(sh_dict, code_field_name):
    ret = ""
    fld = sh_fld_name(code_field_name)
    if not isinstance(fld, dict):
        ret = sh_dict[fld]      # normal field mapping
    elif 'getter' in fld:
        ret = fld.get('getter')(sh_dict)
    elif 'in_list' in fld:
        ret = list((sh_dict[_] for _ in fld.get('in_list') if sh_dict[_]))

    if code_field_name == 'Email':
        if isinstance(ret, list):
            for idx, email in enumerate(ret):
                ret[idx], _ = correct_email(email)
        else:
            ret, _ = correct_email(ret)
    elif code_field_name == 'Phone':
        if isinstance(ret, list):
            for idx, phone in enumerate(ret):
                ret[idx], _ = correct_phone(phone)
        else:
            ret, _ = correct_phone(ret)

    return ret


def field_list_to_sf(code_list, sf_obj):
    sf_list = list()
    for code_field_name in code_list:
        sf_list.append(sf_fld_name(code_field_name, sf_obj))
    return sf_list


def field_dict_to_sf(code_dict, sf_obj):
    sf_dict = dict()
    for code_field_name, val in code_dict.items():
        sf_key = sf_fld_name(code_field_name, sf_obj)
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


def fields_with(field_def_key_name, exclude_fields=None):
    if exclude_fields is None:
        exclude_fields = list()
    return list(k for k, v in FIELD_NAMES.items() if field_def_key_name in v and k not in exclude_fields)


def client_fields(exclude_fields=None):
    return fields_with('AssSysDataClientsIdx', exclude_fields=exclude_fields)


def res_fields(exclude_fields=None):
    return fields_with('AssSysDataResIdx', exclude_fields=exclude_fields)


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
        return None, False

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


def _dummy_stub(msg, *args, **kwargs):
    uprint("******  Fallback call of ass_sys_data._dummy_stub() with:\n        msg='{}', args={}, kwargs={}"
           .format(msg, args, kwargs))


USED_SYS_ASS_ID = 'Ass'
USED_SYS_ACU_ID = 'Acu'
USED_SYS_SF_ID = 'Sf'
USED_SYS_SHWEB_ID = 'Shweb'
USED_SYS_SHKERNEL_ID = 'Shkernel'
USED_SYS_ERR_MARKER = "**!"


class AssSysData:   # Acumen, Salesforce, Sihot and config system data provider
    def __init__(self, cae, ass_user=None, ass_password=None, acu_user=None, acu_password=None,
                 err_logger=None, warn_logger=None, ctx_no_file='', used_systems_msg_prefix=""):
        self.cae = cae
        self._err = err_logger or _dummy_stub
        self._warn = warn_logger or _dummy_stub
        self._ctx_no_file = ctx_no_file
        
        self.error_message = ""
        self.debug_level = cae.get_option('debugLevel')
        self.used_systems = list()

        self.ass_db = None
        self.ass_user = ass_user or cae.get_option('assUser')
        self.ass_password = ass_password or cae.get_option('assPassword')
        self.ass_dsn = cae.get_option('assDSN')
        if self.ass_user and self.ass_password and self.ass_dsn:
            self.used_systems.append(USED_SYS_ASS_ID)
            self.connect_ass_db()
            if not self.ass_db:
                self.used_systems[-1] += USED_SYS_ERR_MARKER

        self.acu_db = None
        self.acu_user = acu_user or cae.get_option('acuUser')
        self.acu_password = acu_password or cae.get_option('acuPassword')
        self.acu_dsn = cae.get_option('acuDSN')
        if self.acu_user and self.acu_password and self.acu_dsn:
            self.used_systems.append(USED_SYS_ACU_ID)
            self.connect_acu_db()
            if not self.acu_db:
                self.used_systems[-1] += USED_SYS_ERR_MARKER

        # if user credentials are specified then prepare Salesforce connection (non-permanent)
        self.sf_conn, self.sf_sandbox = None, True
        if cae.get_option('sfUser') and cae.get_option('sfPassword') and cae.get_option('sfToken'):
            self.used_systems.append(USED_SYS_SF_ID)
            self.sf_conn, self.sf_sandbox = prepare_connection(cae, verbose=False)
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

        # Sihot does also not provide permanent connection; at least prepare GuestSearch instance
        if cae.get_option('shServerIP') and cae.get_option('shServerPort'):
            self.used_systems.append(USED_SYS_SHWEB_ID)
        if cae.get_option('shServerIP') and cae.get_option('shServerKernelPort'):
            self.used_systems.append(USED_SYS_SHKERNEL_ID)
        self.sh_conn = True
        self._guest_search = GuestSearch(cae)

        # load configuration settings (either from INI file or from Acumen)
        self.hotel_ids = cae.get_config('hotelIds')
        if self.hotel_ids:      # fetch config data from INI/CFG
            self.resort_cats = cae.get_config('resortCats')
            self.ap_cats = cae.get_config('apCats')
            self.ro_agencies = cae.get_config('roAgencies')
            self.room_change_max_days_diff = cae.get_config('roomChangeMaxDaysDiff', default_value=3)
        else:               # fetch config data from Acumen
            db = self.acu_db
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
                                                            ["F_CONST_VALUE_NUM('k.SihotRoomChangeMaxDaysDiff')"],
                                                            '')[0][0]

            db.close()

        self.client_refs_add_exclude = cae.get_config('ClientRefsAddExclude', default_value='').split(',')

        # load invalid email fragments (ClientHasNoEmail and OTA pseudo email fragments)
        self.invalid_email_fragments = cae.get_config('invalidEmailFragments', default_value=list())
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("Text fragments for to detect ignorable/invalid email addresses:", self.invalid_email_fragments)

        # --- self.clients contains client data from AssCache database like external references/Ids, owner status ...
        self.clients = list()
        self.clients_changed = list()      # list indexes of changed records within self.clients

        # --- res_inv_data is caching banking/swap/grant info
        self.res_inv_data = list()

        # summary display of used systems
        if used_systems_msg_prefix or self.debug_level >= DEBUG_LEVEL_ENABLED:
            uprint((used_systems_msg_prefix or "Used systems") + ":", self.used_systems)

    def __del__(self):
        self.close_dbs()

    def is_test_system(self):
        return (self.ass_db and 'sihot3v' in self.cae.get_option('assDSN', default_value='')
                or self.acu_db and '.TEST' in self.cae.get_option('acuDSN', default_value='')
                or self.sf_conn and self.sf_sandbox
                or self.sh_conn and 'sihot3v' in self.cae.get_option('shServerIP', default_value='')
                )

    def close_dbs(self, commit=True):
        # ensure to close of DB connections (execution of auto-commits)
        err_msg = ""
        if getattr(self, 'acu_db', None):
            err_msg += self.acu_db.close(commit=commit)
            self.acu_db = None
        if getattr(self, 'ass_db', None):
            err_msg += self.ass_db.close(commit=commit)
            self.ass_db = None      # postgres connection keeps open w/o, explicit dereference always good style:)
        return err_msg

    def connect_acu_db(self, force_reconnect=False):
        if not self.acu_db or force_reconnect:
            self.acu_db = OraDB(usr=self.acu_user, pwd=self.acu_password, dsn=self.acu_dsn,
                                app_name=self.cae.app_name(), debug_level=self.debug_level)
            self.error_message = self.acu_db.connect()
            if self.error_message:
                self._err(self.error_message, self._ctx_no_file + 'ConnAcuDb')
                self.acu_db = None
        return self.acu_db

    def connect_ass_db(self, force_reconnect=False):
        if not self.ass_db or force_reconnect:
            self.ass_db = PostgresDB(usr=self.ass_user, pwd=self.ass_password, dsn=self.ass_dsn,
                                     app_name=self.cae.app_name(), debug_level=self.debug_level)
            self.error_message = self.ass_db.connect()
            if self.error_message:
                self._err(self.error_message, self._ctx_no_file + 'ConnAssDb')
                self.ass_db = None
        return self.ass_db

    def load_view(self, db_opt, view, cols=None, where="", bind_vars=None):
        if db_opt:      # use existing db connection if passed by caller
            db = db_opt
            self.error_message = ""
        else:
            db = self.acu_db
        if not self.error_message:
            self.error_message = db.select(view, cols, where, bind_vars)
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
            if mail_re.match(email_addr):
                for frag in self.invalid_email_fragments:
                    if frag in email_addr:
                        break  # email is invalid/filtered-out
                else:
                    return True
        return False

    # ############################  client data helpers  #########################################################

    def cl_fetch_all(self, where_group_order=""):
        if "ORDER BY " not in where_group_order.upper():
            where_group_order += ("" if where_group_order else "1=1") + " ORDER BY cl_pk"
        if self.ass_db.select('v_clients_refs_owns', where_group_order=where_group_order):
            return self.ass_db.last_err_msg

        self.clients = self.ass_db.fetch_all()
        return self.ass_db.last_err_msg

    def cl_save(self, client_data, save_fields=None, match_fields=None, ext_refs=None, ass_idx=None,
                commit=False, locked_cols=None):
        """
        save/upsert client data into AssCache database.

        :param client_data:     dict of client data (using generic field names).
        :param save_fields:     list of generic field names to be saved in AssCache db (def=all fields in client_data).
        :param match_fields:    list of generic field names for rec match/lookup (def=non-empty AssId/AcId/SfId/ShId).
        :param ext_refs:        list of external reference tuples (type, id) to save.
        :param ass_idx:         self.clients list index of client record. If None/default then determine for to update
                                the self.clients cache list.
        :param commit:          boolean flag if AssCache data changes should be committed (def=False).
        :param locked_cols:     list of generic field names where the cl_ column value will be preserved if not empty.
        :return:                PKey of upserted AssCache client record or None on error (see self.error_message).
        """
        # normalize field values
        for k, v in client_data.items():
            if k == 'SfId' and v:
                client_data[k] = ensure_long_id(v)
            elif k == 'Email' and v:
                if self.email_is_valid(v):
                    client_data[k], _ = correct_email(v)
                else:
                    client_data[k] = ""
            elif k == 'Phone' and v:
                client_data[k], _ = correct_phone(v)
        # process and check parameters
        if not save_fields:
            save_fields = client_data.keys()
        col_values = {ass_fld_name(k): v for k, v in client_data.items() if k in save_fields}
        if not match_fields:
            # default to non-empty, external system references (k.endswith('Id') and len(k) <= 5 and k != 'RciId')
            match_fields = [k for k, v in client_data.items() if k in ('AssId', 'AcId', 'SfId', 'ShId') and v]
        chk_values = {ass_fld_name(k): v for k, v in client_data.items() if k in match_fields}
        if not col_values or not chk_values:
            self.error_message = "AssSysData.cl_save({}, {}, {}) called without data or non-empty foreign system id"\
                .format(client_data, save_fields, match_fields)
            return None
        # if locked_cols is None:
        #    locked_cols = save_fields.copy()        # uncomment for all fields being locked by default

        if self.ass_db.upsert('clients', col_values, chk_values=chk_values, returning_column='cl_pk', commit=commit,
                              locked_cols=locked_cols):
            self.error_message = "cl_save({}, {}, {}) clients upsert error: "\
                                     .format(client_data, save_fields, match_fields) + self.ass_db.last_err_msg
            return None

        cl_pk = self.ass_db.fetch_value()

        for er in ext_refs or list():
            col_values = dict(er_cl_fk=cl_pk, er_type=er[0], er_id=er[1])
            if self.ass_db.upsert('external_refs', col_values, chk_values=col_values, commit=commit):
                break
        if self.ass_db.last_err_msg:
            self.error_message = "cl_save({}, {}, {}) external_refs upsert error: "\
                                     .format(client_data, save_fields, match_fields) + self.ass_db.last_err_msg
            return None

        if ass_idx is None:
            ass_idx = self.cl_idx_by_ass_id(cl_pk)
            if ass_idx is None:
                erj = EXT_REFS_SEP.join([t + EXT_REF_TYPE_ID_SEP + i for t, i in ext_refs or list()])
                self.clients.append((cl_pk, client_data.get('AcId'), client_data.get('SfId'), client_data.get('ShId'),
                                     client_data.get('Name'), client_data.get('Email'), client_data.get('Phone'), erj,
                                     0))
        else:
            self.clients[ass_idx][_ASS_ID] = cl_pk

        return cl_pk

    def cl_flush(self):
        for idx in self.clients_changed:
            co = self.clients[idx]
            client_data = dict(AcId=co[_AC_ID], SfId=co[_SF_ID], ShId=co[_SH_ID], Name=co[_NAME], Email=co[_EMAIL],
                               Phone=co[_PHONE])
            cl_pk = self.cl_save(client_data, ext_refs=co[_EXT_REFS].split(EXT_REFS_SEP), ass_idx=idx, commit=True)
            if cl_pk is None:
                return self.error_message

        return self.ass_db.commit()

    def cl_verify_ext_refs(self):
        resort_codes = self.cae.get_config('ClientRefsResortCodes', default_value='').split(',')
        found_ids = dict()
        for c_rec in self.clients:
            if c_rec[_EXT_REFS]:
                for rci_id in c_rec[_EXT_REFS].split(EXT_REFS_SEP):
                    if rci_id not in found_ids:
                        found_ids[rci_id] = [c_rec]
                    elif [_ for _ in found_ids[rci_id] if _[_AC_ID] != c_rec[_AC_ID]]:
                        found_ids[rci_id].append(c_rec)
                    if c_rec[_AC_ID]:
                        if rci_id in self.client_refs_add_exclude and c_rec[_AC_ID] not in resort_codes:
                            self._warn("Resort RCI ID {} found in client {}".format(rci_id, c_rec[_AC_ID]),
                                       self._ctx_no_file + 'CheckClientsDataResortId')
                        elif c_rec[_AC_ID] in resort_codes and rci_id not in self.client_refs_add_exclude:
                            self._warn("Resort {} is missing RCI ID {}".format(c_rec[_AC_ID], rci_id),
                                       self._ctx_no_file + 'CheckClientsDataResortId')
        # prepare found duplicate ids, prevent duplicate printouts and re-order for to separate RCI refs from others
        dup_ids = list()
        for ref, recs in found_ids.items():
            if len(recs) > 1:
                dup_ids.append("Duplicate external {} ref {} found in clients: {}"
                               .format(ref.split(EXT_REF_TYPE_ID_SEP)[0] if EXT_REF_TYPE_ID_SEP in ref
                                       else EXT_REF_TYPE_RCI,
                                       repr(ref), ';'.join([_[_AC_ID] for _ in recs])))
        for dup in sorted(dup_ids):
            self._warn(dup, self._ctx_no_file + 'CheckClientsDataExtRefDuplicates')

    def cl_ass_id_by_idx(self, index):
        return self.clients[index][_ASS_ID]

    def cl_ass_id_by_ac_id(self, ac_id):
        """
        :param ac_id:   Acumen client reference/ID.
        :return:        AssCache client primary key.
        """
        cl_pk = None
        for cl_rec in self.clients:
            if cl_rec[_AC_ID] == ac_id:
                cl_pk = cl_rec[_ASS_ID]
                break
        if not cl_pk:
            if self.ass_db.select('clients', ['cl_pk'], "cl_ac_id = :ac_id", dict(ac_id=ac_id)):
                self.error_message = "cl_ass_id_by_ac_id(): Acumen client ID {} not found in AssCache (err={})"\
                    .format(ac_id, self.ass_db.last_err_msg)
            else:
                cl_pk = self.ass_db.fetch_value()
        return cl_pk

    def cl_ass_id_by_sh_id(self, sh_id):
        """
        :param sh_id:   Sihot guest object ID.
        :return:        AssCache client primary key.
        """
        cl_pk = None
        for cl_rec in self.clients:
            if cl_rec[_SH_ID] == sh_id:
                cl_pk = cl_rec[_ASS_ID]
                break
        if not cl_pk:
            if self.ass_db.select('clients', ['cl_pk'], "cl_sh_id = :sh_id", dict(sh_id=sh_id)):
                self.error_message = "cl_ass_id_by_sh_id(): Sihot guest object ID {} not found in AssCache (err={})" \
                    .format(sh_id, self.ass_db.last_err_msg)
            else:
                cl_pk = self.ass_db.fetch_value()
        return cl_pk

    def cl_sf_id_by_ass_id(self, ass_id):
        """
        :param ass_id:  AssCache client Id/PKey.
        :return:        Salesforce Contact/Account Id.
        """
        sf_id = None
        for cl_rec in self.clients:
            if cl_rec[_ASS_ID] == ass_id:
                sf_id = cl_rec[_SF_ID]
                break
        if not sf_id:
            if self.ass_db.select('clients', ['cl_sf_id'], "cl_pk = :ass_id", dict(ass_id=ass_id)):
                self.error_message = "cl_sf_id_by_ass_id(): AssCache client ID {} not found (err={})" \
                    .format(ass_id, self.ass_db.last_err_msg)
            else:
                sf_id = self.ass_db.fetch_value()
        return sf_id

    def cl_ensure_id(self, sh_id=None, ac_id=None, name=None, email=None, phone=None):
        """
        determine client id in ass_cache database, from either sh_id or ac_id, create the client record if not exists.
        :param sh_id:       Sihot guest object ID (mandatory if ac_id is not specified).
        :param ac_id:       Acumen client reference/Sihot matchcode (mandatory if sh_id is not specified).
        :param name:        Firstname + space + Surname for client (only needed if client gets created).
        :param email:       Email address of client (only needed if client gets created).
        :param phone:       Phone number of client (only needed if client gets created).
        :return:            primary key (ass_id/cl_pk) of this client (if exists) or None if error.
        """
        if self.debug_level >= DEBUG_LEVEL_VERBOSE and not sh_id and not ac_id:
            self._err("cl_ensure_id(... {}, {}, {}) Missing client references".format(name, email, phone))
        cl_pk = None
        if sh_id and ac_id:
            for cl_rec in self.clients:
                if cl_rec[_SH_ID] == sh_id and cl_rec[_AC_ID] == ac_id:
                    cl_pk = cl_rec[_ASS_ID]
                    break
            if not cl_pk:
                if self.ass_db.select('clients', ['cl_pk'], "cl_sh_id = :sh_id and cl_ac_id = :ac_id",
                                      dict(sh_id=sh_id, ac_id=ac_id)):
                    self.error_message = "cl_ensure_id(): Sihot client {}/{} not found in AssCache (err={})" \
                        .format(sh_id, ac_id, self.ass_db.last_err_msg)
                else:
                    cl_pk = self.ass_db.fetch_value()

        if not cl_pk and sh_id:
            cl_pk = self.cl_ass_id_by_sh_id(sh_id)

        if not cl_pk and ac_id:
            cl_pk = self.cl_ass_id_by_ac_id(ac_id)

        if not cl_pk:   # create client record?
            cl_data = dict()
            if ac_id:
                cl_data['AcId'] = ac_id
            if sh_id:
                cl_data['ShId'] = sh_id
            if name:
                cl_data['Name'] = name
            if email:
                cl_data['Email'] = email
            if phone:
                cl_data['Phone'] = phone
            cl_pk = self.cl_save(cl_data, locked_cols=['AcId', 'ShId', 'Name', 'Email', 'Phone'])

        return cl_pk

    def cl_ac_id_by_idx(self, index):
        return self.clients[index][_AC_ID]

    def cl_sh_id_by_idx(self, index):
        return self.clients[index][_SH_ID]

    def cl_ext_refs_by_idx(self, index):
        return self.clients[index][_EXT_REFS].split(EXT_REFS_SEP)

    def cl_idx_by_ass_id(self, ass_id):
        for list_idx, c_rec in enumerate(self.clients):
            if c_rec[_ASS_ID] == ass_id:
                return list_idx
        return None

    def cl_idx_by_rci_id(self, imp_rci_ref, fields_dict, file_name, line_num):
        """ determine list index in cached clients """
        # check first if client exists
        for list_idx, c_rec in enumerate(self.clients):
            ext_refs = c_rec[_EXT_REFS]
            if ext_refs and imp_rci_ref in ext_refs.split(EXT_REFS_SEP):
                break
        else:
            sf_id, dup_clients = self.sf_conn.sf_client_by_rci_id(imp_rci_ref)
            if self.sf_conn.error_msg:
                self._err("cl_idx_by_rci_id() Salesforce connect/fetch error " + self.sf_conn.error_msg,
                          file_name, line_num, importance=3)
            if len(dup_clients) > 0:
                self._err("Found duplicate Salesforce client(s) with main or external RCI ID {}. Used client {}, dup={}"
                          .format(imp_rci_ref, sf_id, dup_clients), file_name, line_num)
            if sf_id:
                ass_id = self.sf_conn.cl_ass_id_by_idx(sf_id)
                if self.sf_conn.error_msg:
                    self._err("cl_idx_by_rci_id() AssCache id fetch error " + self.sf_conn.error_msg,
                              file_name, line_num, importance=3)
                ac_id = self.sf_conn.cl_ac_id_by_idx(sf_id)
                if self.sf_conn.error_msg:
                    self._err("cl_idx_by_rci_id() Acumen id fetch error " + self.sf_conn.error_msg,
                              file_name, line_num, importance=3)
                sh_id = self.sf_conn.cl_sh_id_by_idx(sf_id)
                if self.sf_conn.error_msg:
                    self._err("cl_idx_by_rci_id() Sihot id fetch error " + self.sf_conn.error_msg,
                              file_name, line_num, importance=3)
            else:
                ass_id = None
                ac_id = None
                sf_fields = fields_dict.copy()
                sf_fields['RciId'] = imp_rci_ref    # also create in Sf an entry in the External_Ref custom object
                sf_id, err, msg = self.sf_client_upsert(sf_fields)
                if err:
                    self._err("cl_idx_by_rci_id() Salesforce upsert error " + self.sf_conn.error_msg,
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
        c_rec = self.clients[c_idx]
        if not c_rec[_SH_ID] or c_rec[_SH_ID] != sh_id:
            if c_rec[_SH_ID]:
                self._warn("Sihot guest object id changed from {} to {} for Salesforce client {}"
                           .format(c_rec[_SH_ID], sh_id, c_rec[_SF_ID]), self._ctx_no_file + 'CompShId', importance=1)
            self.clients[c_idx] = (c_rec[_ASS_ID], c_rec[_AC_ID], c_rec[_SF_ID], sh_id,
                                   c_rec[_NAME], c_rec[_EMAIL], c_rec[_PHONE], c_rec[_EXT_REFS], c_rec[_PRODUCTS])
            self.clients_changed.append(c_idx)

    def cl_sent_to_sihot(self):
        return [i for i, _ in enumerate(self.clients) if _[_SH_ID]]

    def cl_list_by_ac_id(self, ac_id):
        return [_ for _ in self.clients if _[_AC_ID] == ac_id]

    # =================  res_inv_data  =========================================================================

    def ri_fetch_all(self):
        self._warn("Fetching reservation inventory from AssCache (needs some minutes)",
                   self._ctx_no_file + 'FetchResInv', importance=4)
        self.res_inv_data = self.load_view(self.ass_db, 'res_inventories')
        if not self.res_inv_data:
            return self.error_message

        return ""

    def ri_allocated_room(self, room_no, arr_date):
        year, week = self.rci_arr_to_year_week(arr_date)
        for r_rec in self.res_inv_data:
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
        :param col_values:      dict of res_groups updated columns.
        :param chk_values:      dict of res_groups search/WHERE column values.
        :return:                True if all ids could be set to non-empty value, else False.
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
                if isinstance(ids, dict):   # silently ignoring ResFetch error
                    col_values['rgr_obj_id'] = ids['ResObjId']
            elif ((chk_values.get('rgr_ho_fk') or col_values.get('rgr_ho_fk'))
                  and (chk_values.get('rgr_gds_no') or col_values.get('rgr_gds_no'))):
                ids = gds_no_to_ids(self.cae,
                                    chk_values.get('rgr_ho_fk') or col_values['rgr_ho_fk'],
                                    chk_values.get('rgr_gds_no') or col_values['rgr_gds_no'])
                if isinstance(ids, dict):   # silently ignoring ResFetch error
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
                if res_no_ids:
                    if res_no_ids[:2] != (col_values['rgr_ho_fk'], col_values['rgr_res_id'], ):
                        self._warn("Automatic/hidden update of reservation number from {}/{}@{} to {}/{}@{}"
                                   .format(col_values.get('rgr_ho_fk'), col_values.get('rgr_res_id'),
                                           col_values.get('rgr_sub_id'), *res_no_ids),
                                   self._ctx_no_file + "rgr_complete_ids()")
                    col_values['rgr_ho_fk'], col_values['rgr_res_id'], col_values['rgr_sub_id'] = res_no_ids
            elif col_values.get('rgr_ho_fk') and col_values.get('rgr_res_id'):
                col_values['rgr_sub_id'] = '0'
            ret = bool(col_values.get('rgr_ho_fk') and col_values.get('rgr_res_id') and col_values.get('rgr_sub_id'))

        return ret

    def rgr_fetch_list(self, col_names, chk_values=None, where_group_order=""):
        if chk_values and not where_group_order:
            where_group_order = " AND ".join([k + " = :" + k for k in chk_values.keys()])
        if self.ass_db.select('res_groups', col_names, where_group_order, bind_vars=chk_values):
            self.error_message = self.ass_db.last_err_msg
        ret = self.ass_db.fetch_all()
        if self.ass_db.last_err_msg:
            self.error_message += self.ass_db.last_err_msg
        return ret

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
        ''' prevent to wipe id value -- NOT NEEDED
        if prevent_id_wipe:
            for k in ('rgr_obj_id', 'rgr_ho_fk', 'rgr_res_id', 'rgr_sub_id', 'rgr_gds_no', 'rgr_sf_id', ):
                if k in col_values and col_values.get(k) in (None, ''):
                    col_values.pop(k)   # remove pk column with empty value
        '''
        ret = None
        if not chk_values:
            self.error_message = "rgr_upsert({}, {}): Missing reservation IDs (ObjId, Hotel/ResId or GdsNo)" \
                .format(col_values, chk_values)
        elif not multiple_row_update and not self.rgr_complete_ids(col_values, chk_values):
            self.error_message = "rgr_upsert({}, {}): Incomplete-able reservation IDs".format(col_values, chk_values)
        else:
            self.error_message = self.ass_db.upsert('res_groups', col_values, chk_values,
                                                    returning_column=returning_column, commit=commit,
                                                    multiple_row_update=multiple_row_update)
            if self.error_message:
                if commit:
                    self.error_message += "\n" + self.ass_db.rollback()
            elif not multiple_row_update and self.ass_db.curs.rowcount != 1:
                self.error_message = "rgr_upsert({}, {}): Invalid affected row count; expected 1 but got {}" \
                    .format(col_values, chk_values, self.ass_db.curs.rowcount)
            elif returning_column:
                ret = self.ass_db.fetch_value()
            else:
                ret = chk_values

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
            self.error_message = self.ass_db.upsert('res_group_clients', col_values, chk_values, commit=commit,
                                                    multiple_row_update=multiple_row_update)
            if not self.error_message and not multiple_row_update and self.ass_db.curs.rowcount != 1:
                self.error_message = "rgc_upsert({}, {}): Invalid affected row count; expected 1 but got {}"\
                    .format(col_values, chk_values, self.ass_db.curs.rowcount)
        else:
            self.error_message = "rgc_upsert({}): Missing res-client id (rgr_pk,room_seq,pers_seq)".format(col_values)

        return self.error_message

    # =================  RCI data conversion  ==================================================

    def rci_to_sihot_hotel_id(self, rc_resort_id):
        return self.cae.get_config(rc_resort_id, 'RcResortIds', default_value=-369)     # pass default for int type ret

    def rci_first_week_of_year(self, year):
        rci_wk_01 = self.cae.get_config(str(year), 'RcWeeks')
        if rci_wk_01:
            ret = datetime.datetime.strptime(rci_wk_01, '%Y-%m-%d')
        else:
            self._warn("AssSysData.rci_first_week_of_year({}): missing RcWeeks config".format(year), notify=True)
            ret = datetime.datetime(year=year, month=1, day=1)
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
        """ determine seg=RE RG RI RL  and  grp=RCI External, RCI Guest, RCI Internal, RCI External """
        if self.clients[c_idx][_PRODUCTS] and not is_guest:
            key = 'Internal'
        else:  # not an owner/internal, so will be either Guest or External
            # changed by Esther/Nitesh - now Guest is External: key = 'Guest' if is_guest else 'External'
            key = 'External'
        seg, desc, grp = self.cae.get_config(key, 'RcMktSegments').split(',')
        if file_name[:3].upper() == 'RL_':
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                self._warn("Reclassified booking from " + seg + "/" + grp + " into RL/RCI External",
                           file_name, line_num, importance=1)
            # seg, grp = 'RL', 'RCI External'
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

    def sf_client_upsert(self, fields_dict, sf_obj=None):
        # check if Id passed in (then this method can determine the sf_obj and will do an update not an insert)
        sf_id, update_client = (fields_dict.pop(SF_DEF_SEARCH_FIELD), True) if SF_DEF_SEARCH_FIELD in fields_dict \
            else ('', False)

        if sf_obj is None:
            if not sf_id:
                self.error_message = "sf_client_upsert({}, {}): client object cannot be determined without Id"\
                    .format(fields_dict, sf_obj)
                return None, self.error_message, ""
            sf_obj = obj_from_id(sf_id)

        client_obj = self.sf_conn.sf_obj(sf_obj)
        if not client_obj:
            self.error_message += "\n      +sf_client_upsert({}, {}): empty client object".format(fields_dict, sf_obj)
            return None, self.error_message, ""

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
                    sf_id = sf_ret[sf_fld_name(SF_DEF_SEARCH_FIELD, sf_obj)]
            except Exception as ex:
                err = "{} create() exception {}. sent={}".format(sf_obj, ex, pprint.pformat(sf_dict, indent=9))

        if not err and sf_id and 'RciId' in fields_dict:
            _, err, msg = self.sf_conn.ext_ref_upsert(sf_id, fields_dict['RciId'], EXT_REF_TYPE_RCI, sf_obj=sf_obj)

        if err:
            self.error_message = err

        return sf_id, err, msg

    def sf_clients_with_rci_id(self, ext_refs_sep, owner_rec_types=None, sf_obj=DEF_CLIENT_OBJ):
        if not owner_rec_types:
            owner_rec_types = list()
        code_fields = ['SfId', 'AcId', 'RciId', 'ShId', 'RecordType.Id',
                       "(SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"]
        sf_fields = field_list_to_sf(code_fields, sf_obj)
        res = self.sf_conn.soql_query_all("SELECT {} FROM {}".format(", ".join(sf_fields), sf_obj))
        client_tuples = list()
        if self.sf_conn.error_msg:
            self.error_message = "sf_clients_with_rci_id(): " + self.sf_conn.error_msg
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
        res = self.sf_conn.soql_query_all(soql_query)
        if self.sf_conn.error_msg:
            self.error_message = "sf_client_by_rci_id({}): ".format(rci_ref) + self.sf_conn.error_msg
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
                             search_field=SF_DEF_SEARCH_FIELD, sf_obj=DETERMINE_CLIENT_OBJ,
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
        if sf_obj == DETERMINE_CLIENT_OBJ:
            if search_field not in (SF_DEF_SEARCH_FIELD, 'External_Id__c', 'Contact_Ref__c', 'Id_before_convert__c',
                                    'CSID__c'):
                self._err("sf_client_field_data({}, {}, {}, {}): client object cannot be determined without Id"
                          .format(fetch_fields, search_value, search_field, sf_obj))
                return None
            sf_obj = obj_from_id(search_value)
            if not sf_obj:
                self._err("sf_client_field_data(): {} field value {} is not a valid Lead/Contact/Account SF ID"
                          .format(search_field, search_value))
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
        res = self.sf_conn.soql_query_all(soql_query)
        if self.sf_conn.error_msg:
            self.error_message = "sf_client_field_data(): " + self.sf_conn.error_msg
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

    def sf_client_ass_id(self, sf_client_id, sf_obj=DETERMINE_CLIENT_OBJ):
        return self.sf_client_field_data('AssId', sf_client_id, sf_obj=sf_obj)

    def sf_client_ac_id(self, sf_client_id, sf_obj=DETERMINE_CLIENT_OBJ):
        return self.sf_client_field_data('AcId', sf_client_id, sf_obj=sf_obj)

    def sf_client_sh_id(self, sf_client_id, sf_obj=DETERMINE_CLIENT_OBJ):
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
                   Account.AcumenClientRef__pc, Account.SihotGuestObjId__pc, 
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
        res = self.sf_conn.soql_query_all(soql_query)
        if self.sf_conn.error_msg:
            self.error_message = "sf_res_data(): " + self.sf_conn.error_msg
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
                    v = datetime.datetime.strptime(v, '%Y-%m-%d').date()
                ret_val[k] = v

        return ret_val

    def sf_res_upsert(self, rgr_sf_id, sh_cl_data, ass_res_data, sync_cache=True, sf_data=None):
        """
        convert ass_cache db columns to SF fields, and then push to Salesforce server via APEX method call

        :param rgr_sf_id:       Reservation Opportunity Id (SF ID with 18 characters). Pass None for to create new-one.
        :param sh_cl_data:      dict with Sihot guest data (fetched with GuestSearch.get_guest()/shif.guest_data()).
        :param ass_res_data:    reservation fields.
        :param sync_cache:      True for to update ass_cache/res_groups/rgr_last_sync+rgr_sf_id (opt, def=True).
        :param sf_data:         Salesforce field data of Account/Reservation object (OUT, opt). The Reservation Opp. Id
                                gets returned as sf_data['ReservationOpportunityId'].
        :return:                error message if error occurred, else empty string.
        """
        sf_args = dict() if sf_data is None else sf_data        # sf_data or dict()  would fail if sf_data is empty dict
        sf_args.update(ReservationOpportunityId=rgr_sf_id)
        ass_id = ass_res_data.get('rgr_order_cl_fk')
        if ass_id:
            sf_cl_id = self.cl_sf_id_by_ass_id(ass_id)
            if sf_cl_id:
                sf_args['PersonAccountId'] = sf_cl_id

        for sfn, shn in (('LastName', 'NAME-1'), ('FirstName', 'NAME-2'),
                         ('PersonEmail', 'EMAIL-1'), ('PersonHomePhone', 'PHONE-1'),
                         ('SihotGuestObjId__pc', 'OBJID'), ('AcumenClientRef__pc', 'MATCHCODE'),
                         ('Language__pc', 'T-LANGUAGE'), ('PersonMailingCountry', 'T-COUNTRY-CODE'),
                         ('Nationality__pc', 'T-NATION'),
                         ('PersonMailingStreet', 'STREET'), ('PersonMailingPostalCode', 'ZIP'),
                         ('PersonMailingCity', 'CITY'), ('CurrencyIsoCode', 'T-STANDARD-CURRENCY'),
                         ):
            elem_val = sh_cl_data.get(shn)
            if elem_val:
                if isinstance(elem_val, list):
                    self._warn("asd.sf_res_upsert({}, {}, {}); using first value '{}' for {} from list value {}"
                               .format(rgr_sf_id, sh_cl_data, ass_res_data, elem_val[0], sfn, elem_val))
                    elem_val = elem_val[0]
                sf_args[sfn] = elem_val

        sf_args['HotelId__c'] = ho_id = ass_res_data['rgr_ho_fk']
        sf_args['Number__c'] = res_id = ass_res_data['rgr_res_id']
        sf_args['SubNumber__c'] = sub_id = ass_res_data['rgr_sub_id']
        for sfn, asn in (('GdsNo__c', 'rgr_gds_no'),
                         ('SihotResvObjectId__c', 'rgr_obj_id'),
                         ('Arrival__c', 'rgr_arrival'),
                         ('Departure__c', 'rgr_departure'),
                         ('RoomNo__c', 'rgr_room_id'),
                         ('RoomCat__c', 'rgr_room_cat_id'),
                         ('Status__c', 'rgr_status'),
                         ('MktGroup__c', 'rgr_mkt_group'),
                         ('MktSegment__c', 'rgr_mkt_segment'),
                         ('Adults__c', 'rgr_adults'),
                         ('Children__c', 'rgr_children'),
                         ('Note__c', 'rgr_comment'),
                         ):
            if ass_res_data.get(asn):
                sf_args[sfn] = ass_res_data[asn]

        if not sf_args.get('RoomNo__c') \
                and ass_res_data.get('rgc_list') and ass_res_data['rgc_list'][0].get('rgc_room_id'):
            sf_args['RoomNo__c'] = ass_res_data['rgc_list'][0]['rgc_room_id']

        sf_cl_id, sf_opp_id, err_msg = self.sf_conn.res_upsert(sf_args)
        if 'ENTITY_IS_DELETED' in err_msg and rgr_sf_id:    # retry without rgr_sf_id if ResOpp got deleted within SF
            sf_args['ReservationOpportunityId'] = ''
            sf_cl_id, sf_opp_id, err_msg = self.sf_conn.res_upsert(sf_args)
            self._warn("asd.sf_res_upsert({}, {}, {}) cached ResOpp value reset to {}; SF client={}; err='{}'"
                       .format(rgr_sf_id, sh_cl_data, ass_res_data, sf_opp_id, sf_cl_id, err_msg))
            rgr_sf_id = ''

        if sf_args.get('PersonAccountId') and sf_args['PersonAccountId'] != sf_cl_id \
                and self.debug_level >= DEBUG_LEVEL_VERBOSE:
            self._err("sf_res_upsert({}, {}, {}) PersonAccount discrepancy {} != {}"
                      .format(rgr_sf_id, sh_cl_data, ass_res_data, sf_args.get('PersonAccountId'), sf_cl_id))

        if sync_cache:
            if sf_cl_id and ass_id:
                col_values = dict(AssId=ass_id, SfId=sf_cl_id)
                self.cl_save(col_values, match_fields=['AssId'])    # on error populating/overwriting self.error_message
                if self.error_message:
                    err_msg += self.error_message
                    self.error_message = ""

            col_values = dict() if err_msg else dict(rgr_last_sync=datetime.datetime.now())
            if not rgr_sf_id and sf_opp_id:     # save just (re-)created ID of Reservation Opportunity in AssCache
                col_values['rgr_sf_id'] = sf_opp_id
            elif self.debug_level >= DEBUG_LEVEL_VERBOSE and sf_opp_id and rgr_sf_id and sf_opp_id != rgr_sf_id:
                self._err("sf_res_upsert({}, {}, {}) Reservation Opportunity ID discrepancy {} != {}"
                          .format(rgr_sf_id, sh_cl_data, ass_res_data, sf_opp_id, rgr_sf_id))

            if col_values:
                self.rgr_upsert(col_values, dict(rgr_ho_fk=ho_id, rgr_res_id=res_id, rgr_sub_id=sub_id))
                if self.error_message:
                    err_msg += self.error_message
                    self.error_message = ""

        if err_msg:
            self.error_message += err_msg
        return self.error_message

    def sf_room_change(self, rgr_sf_id, check_in, check_out, next_room_id):
        """
        check room change and if ok then pass to Salesforce Allocation custom object.
        :param rgr_sf_id:       SF Reservation Opportunity object Id.
        :param check_in:        check-in timestamp.
        :param check_out:       check-out timestamp.
        :param next_room_id:    newest apartment/room number.
        :return:                empty string if ok, else error message.
        """
        self._warn("sf_room_change({}, {}, {}, {}) called".format(rgr_sf_id, check_in, check_out, next_room_id),
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        self.error_message = self.sf_conn.room_change(rgr_sf_id, check_in, check_out, next_room_id)
        return self.error_message

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
        res = self.sf_conn.soql_query_all(soql_query)
        if self.sf_conn.error_msg:
            self.error_message = "sf_room_data(): " + self.sf_conn.error_msg
        elif res['totalSize'] > 0:
            ret_all = res['records'][0]
            ret = dict(ReservationId=ret_all['Id'])
            ret.update(ret_all['Allocations__r']['records'][0])
            ret['AllocationId'] = ret.pop('Id')
            del ret['attributes']
            for k, v in ret.items():
                if k in ('CheckIn__c', 'CheckOut__c') and v:
                    v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%f%z').replace(microsecond=0)
                ret_val[k] = v

        return ret_val

    # #######################  SH helpers  ######################################################################

    def sh_apt_wk_yr(self, shd, arri=0):
        arr = datetime.datetime.strptime(elem_value(shd, 'ARR'), SH_DATE_FORMAT)
        year, wk = self.rci_arr_to_year_week(arr)
        apt = elem_value(shd, 'RN', arri=arri)
        apt_wk = "{}-{:0>2}".format(apt, wk)
        return apt_wk, year

    def sh_client_upsert(self, fields_dict):
        guest = ClientToSihot(self.cae)
        col_values = dict()
        for fld, val in fields_dict.items():
            col_name = ac_fld_name(fld)
            if col_name and col_name in guest.acu_fld_names:
                col_values[col_name] = val
        return guest.send_client_to_sihot(col_values)

    def sh_guest_ids(self, match_field, match_val):
        ret = None
        if match_field == 'AcId':
            ret = self._guest_search.get_objids_by_matchcode(match_val)
        elif match_field == 'Name':
            ret = self._guest_search.get_objids_by_guest_name(match_val)
        elif match_field == 'Email':
            ret = self._guest_search.get_objids_by_email(match_val)
        return ret

    def sh_avail_rooms(self, hotel_ids=None, room_cat_prefix='', day=None):
        """ accumulating the number of available rooms in all the hotels specified by the hotel_ids list with the room
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
            all_rows = res_search.search(hotel_id=hotel_id, from_date=day - res_len_max_timedelta, to_date=day)
            if all_rows and isinstance(all_rows, list):
                for row_dict in all_rows:
                    res_type = row_dict['RT']['elemVal']
                    room_cat = row_dict['CAT']['elemVal']
                    checked_in = datetime.datetime.strptime(row_dict['ARR']['elemVal'], DATE_ISO).date()
                    checked_out = datetime.datetime.strptime(row_dict['DEP']['elemVal'], DATE_ISO).date()
                    skip_reasons = []
                    if res_type == 'S':
                        skip_reasons.append("cancelled")
                    if res_type == 'E':
                        skip_reasons.append("erroneous")
                    if not room_cat.startswith(room_cat_prefix):
                        skip_reasons.append("room cat " + room_cat)
                    if not (checked_in <= day < checked_out):
                        skip_reasons.append("out of date range " + str(checked_in) + "..." + str(checked_out))
                    if not skip_reasons:
                        count += 1
                    elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
                        self._warn("AssSysData.sh_count_res(): skipped {} res: {}".format(str(skip_reasons), row_dict))
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

    def sh_res_change_to_ass(self, shd, last_change=None, rgr_dict=None):
        """
        extract reservation data from sihot ResResponse dict and save it into the ass_cache database.

        :param shd:         Sihot ResChange dict.
        :param last_change: if not None then set rgr_last_change column value to this passed timestamp.
        :param rgr_dict:    return reservation data and person/rooming-list (in rgr_dict['rgc_list']) (opt).
        :return:            ""/empty-string if ok and committed, else error message (and rolled-back).
        """
        if rgr_dict is None:
            rgr_dict = dict()
        # determine ordering client; RESCHANNELLIST element is situated within RESERVATION xml block
        ord_cl_pk = None
        sh_id = elem_value(shd, ['RESCHANNELLIST', 'RESCHANNEL', 'OBJID'])
        ac_id = elem_value(shd, ['RESCHANNELLIST', 'RESCHANNEL', 'MATCHCODE'])
        if sh_id or ac_id:
            self._warn("sh_res_change_to_ass(): create new client record for orderer {}/{}".format(sh_id, ac_id),
                       minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            ord_cl_pk = self.cl_ensure_id(sh_id=sh_id, ac_id=ac_id)
            if ord_cl_pk is None:
                self._warn("sh_res_change_to_ass(): creation of new orderer {}/{} failed with (ignored) err={}"
                           .format(sh_id, ac_id, self.error_message))
                self.error_message = ""

        ri_pk = None
        apt_wk, year = self.sh_apt_wk_yr(shd)
        if self.ass_db.select('res_inventories', ['ri_pk'], "ri_pr_fk = :aw and ri_usage_year = :yr",
                              dict(aw=apt_wk, yr=year)):
            self._warn("sh_res_change_to_ass(): res inv {}~{} not found; (ignored) err={}"
                       .format(apt_wk, year, self.error_message))
            self.error_message = ""
        else:
            ri_pk = self.ass_db.fetch_value()

        error_msg = ""
        ho_id = elem_value(shd, 'RES-HOTEL')    # SS/RES-SEARCH using RES-HOTEL instead of ID xml element
        res_id = elem_value(shd, 'RES-NR')
        sub_id = elem_value(shd, 'SUB-NR')
        err_pre = "sh_res_change_to_ass() for res-no {}/{}@{}: ".format(res_id, sub_id, ho_id)
        chk_values = dict(rgr_ho_fk=ho_id)
        if ho_id and res_id and sub_id:
            chk_values.update(rgr_res_id=res_id, rgr_sub_id=sub_id)
        else:
            gds_no = gds_number(shd)
            if gds_no:
                chk_values.update(rgr_gds_no=gds_no)
            else:
                error_msg = err_pre + "Incomplete reservation id ({}/{}@{})".format(res_id, sub_id, ho_id)

        if not error_msg:
            upd_values = chk_values.copy()
            upd_values\
                .update(rgr_order_cl_fk=ord_cl_pk,
                        rgr_used_ri_fk=ri_pk,
                        # xml path prefix for all elements within RESERVATION block is different for responses of
                        # .. RES-SEARCH (['SIHOT-Document', 'ARESLIST']) and of SS (['SIHOT-Document'])
                        rgr_obj_id=elem_value(shd, ['RESERVATION', 'OBJID']),
                        # finally not added next/commented line because IDs should only come from ID generating system
                        # rgr_sf_id=elem_value(rg, ['RESERVATION', ''NN2']),
                        rgr_status=elem_value(shd, ['RESERVATION', 'RT']),
                        rgr_adults=elem_value(shd, ['RESERVATION', 'NOPAX']),
                        rgr_children=elem_value(shd, ['RESERVATION', 'NOCHILDS']),
                        rgr_arrival=datetime.datetime.strptime(elem_value(shd, ['RESERVATION', 'ARR']),
                                                               SH_DATE_FORMAT).date(),
                        rgr_departure=datetime.datetime.strptime(elem_value(shd, ['RESERVATION', 'DEP']),
                                                                 SH_DATE_FORMAT).date(),
                        rgr_mkt_segment=elem_value(shd, ['RESERVATION', 'MARKETCODE']),
                        rgr_mkt_group=elem_value(shd, ['RESERVATION', 'CHANNEL']),
                        rgr_room_id=elem_value(shd, ['PERSON', 'RN']),
                        rgr_room_cat_id=elem_value(shd, ['RESERVATION', 'CAT']),
                        rgr_room_rate=elem_value(shd, ['RESERVATION', 'RATE-SEGMENT']),
                        rgr_payment_inst=elem_value(shd, ['RESERVATION', 'PAYMENT-INST']),
                        rgr_ext_book_id=elem_value(shd, ['RESERVATION', 'VOUCHERNUMBER']),
                        rgr_ext_book_day=elem_value(shd, ['RESERVATION', 'SALES-DATE']),
                        rgr_comment=elem_value(shd, ['RESERVATION', 'COMMENT']),
                        rgr_long_comment=elem_value(shd, ['RESERVATION', 'TEC-COMMENT']),
                        )
            if last_change:
                upd_values.update(rgr_last_change=datetime.datetime.now())
            if self.ass_db.upsert('res_groups', upd_values, chk_values=chk_values, returning_column='rgr_pk'):
                error_msg = self.ass_db.last_err_msg
            else:
                rgr_dict.update(upd_values)
        if not error_msg:
            rgr_pk = rgr_dict['rgr_pk'] = self.ass_db.fetch_value()

            rgr_dict['rgc_list'] = list()
            for arri in range(pax_count(shd)):
                occ_cl_pk = None
                sh_id = elem_value(shd, ['PERSON', 'GUEST-ID'], arri=arri)
                ac_id = elem_value(shd, ['PERSON', 'MATCHCODE'], arri=arri)
                if sh_id is None and ac_id is None:
                    self._warn(err_pre + "ignoring unspecified person {}".format(arri + 1),
                               minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                    continue
                sn = elem_value(shd, ['PERSON', 'NAME'], arri=arri)
                fn = elem_value(shd, ['PERSON', 'NAME2'], arri=arri)
                if sh_id or ac_id:
                    self._warn(err_pre + "ensure client {} {} for occupant {}/{}".format(fn, sn, sh_id, ac_id),
                               minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                    occ_cl_pk = self.cl_ensure_id(sh_id=sh_id, ac_id=ac_id,
                                                  name=fn + " " + sn if fn and sn else sn or fn)
                    if occ_cl_pk is None:
                        self._warn(err_pre + "create client record for occupant {} {} {}/{} failed; ignored err={}"
                                   .format(fn, sn, sh_id, ac_id, self.error_message),
                                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                        self.error_message = ""
                room_seq = elem_value(shd, ['PERSON', 'ROOM-SEQ'], arri=arri)
                pers_seq = elem_value(shd, ['PERSON', 'ROOM-PERS-SEQ'], arri=arri)
                if room_seq is None:
                    self._warn(err_pre + "ignoring unspecified room/person seq {}".format(arri + 1),
                               minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                    continue
                chk_values = dict(rgc_rgr_fk=rgr_pk, rgc_room_seq=int(room_seq), rgc_pers_seq=int(pers_seq))
                upd_values = chk_values.copy()
                upd_values\
                    .update(rgc_surname=sn,
                            rgc_firstname=fn,
                            rgc_auto_generated=elem_value(shd, ['PERSON', 'AUTO-GENERATED'], arri=arri),
                            rgc_occup_cl_fk=occ_cl_pk,
                            # Sihot offers also PICKUP-TYPE-ARRIVAL(1=car, 2=van), we now use PICKUP-TIME-ARRIVAL
                            # .. instead of ARR-TIME for the flight arr/dep (pg converts str into time object/value)
                            rgc_flight_arr_comment=elem_value(shd, ['PERSON', 'PICKUP-COMMENT-ARRIVAL']),
                            rgc_flight_arr_time=elem_value(shd, ['PERSON', 'PICKUP-TIME-ARRIVAL']),
                            rgc_flight_dep_comment=elem_value(shd, ['PERSON', 'PICKUP-COMMENT-DEPARTURE']),
                            rgc_flight_dep_time=elem_value(shd, ['PERSON', 'PICKUP-TIME-DEPARTURE']),
                            # occupation data
                            rgc_pers_type=elem_value(shd, ['PERSON', 'PERS-TYPE'], arri=arri),
                            rgc_sh_pack=elem_value(shd, ['PERSON', 'R'], arri=arri),
                            rgc_room_id=elem_value(shd, ['PERSON', 'RN'], arri=arri),
                            )
                pers_dob = elem_value(shd, ['PERSON', 'DOB'], arri=arri)
                if pers_dob:
                    upd_values.update(rgc_dob=datetime.datetime.strptime(pers_dob, SH_DATE_FORMAT))
                if self.ass_db.upsert('res_group_clients', upd_values, chk_values=chk_values):
                    error_msg = self.ass_db.last_err_msg
                    break
                rgr_dict['rgc_list'].append(upd_values)

        if error_msg:
            self.error_message = error_msg
            self.ass_db.rollback()
        else:
            self.ass_db.commit()

        return error_msg

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
            self.error_message = "sh_room_change_to_ass({}, {}, {}, {}, {}, {}): Invalid operation code"\
                .format(oc, ho_id, res_id, sub_id, room_id, action_time)

        rgr_sf_id = None
        if not self.error_message:
            rgr_sf_id = self.rgr_upsert(upd_col_values,
                                        chk_values=dict(rgr_ho_fk=ho_id, rgr_res_id=res_id, rgr_sub_id=sub_id),
                                        commit=True, returning_column='rgr_sf_id')

        return rgr_sf_id
