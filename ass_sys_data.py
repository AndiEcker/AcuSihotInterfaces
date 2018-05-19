import datetime
import pprint
import re

from ae_db import OraDB, PostgresDB
from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE
from sxmlif import GuestSearch, ClientToSihot
from sfif import prepare_connection, ensure_long_id, obj_from_id, DEF_CLIENT_OBJ, DETERMINE_CLIENT_OBJ

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
SH_DEF_SEARCH_FIELD = 'ShId'


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
                             AssDb='cl_sf_id', AcDb='CD_SF_ID1', Lead='Id', Contact='Id', Account='Id',
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
                              AssDb='cl_phone', AcDb='CD_HTEL1',
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


def client_fields(exclude_fields=None):
    if exclude_fields is None:
        exclude_fields = list()
    return list(k for k, v in FIELD_NAMES.items() if 'AssSysDataClientsIdx' in v and k not in exclude_fields)


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


def _dummy_stub(msg, ctx_file, *args, **kwargs):
    uprint("******  Fallback call of ass_sys_data._dummy_stub() with:\n        msg={}, ctx/file={}; args/kwargs:"
           .format(msg, ctx_file), args, kwargs)


class AssSysData:   # Acumen, Salesforce, Sihot and config system data provider
    def __init__(self, cae, ass_user=None, ass_password=None, acu_user=None, acu_password=None,
                 err_logger=_dummy_stub, warn_logger=_dummy_stub, ctx_no_file=''):
        self.cae = cae
        self._err = err_logger
        self._warn = warn_logger
        self._ctx_no_file = ctx_no_file
        
        self.error_message = ""
        self.debug_level = cae.get_option('debugLevel')

        self.ass_db = None  # lazy connection
        self.ass_user = ass_user or cae.get_option('pgUser')
        self.ass_password = ass_password or cae.get_option('pgPassword')
        self.ass_dsn = cae.get_option('pgDSN')
        if self.ass_user and self.ass_password and self.ass_dsn:
            self.connect_ass_db()

        self.acu_db = None  # lazy connection
        self.acu_user = acu_user or cae.get_option('acuUser')
        self.acu_password = acu_password or cae.get_option('acuPassword')
        self.acu_dsn = cae.get_option('acuDSN')
        if self.acu_user and self.acu_password and self.acu_dsn:
            self.connect_acu_db()

        # if user credentials are specified then open/check Salesforce connection
        self.sf_conn, self.sf_sandbox = None, False
        if cae.get_option('sfUser') and cae.get_option('sfPassword') and cae.get_option('sfToken'):
            self.sf_conn, self.sf_sandbox = prepare_connection(cae)
            if not self.sf_conn:
                self.error_message = "AssSysData: SF connection failed - please check account data and credentials"
                self._err(self.error_message, self._ctx_no_file + 'InitSfConn')
                return
            elif self.sf_conn.error_msg:
                self.error_message = self.sf_conn.error_msg
                self._err(self.error_message, self._ctx_no_file + 'InitSfErr')
                return

        # Sihot does not provide permanent connection; at least prepare GuestSearch instance
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
            uprint("Invalid Email Fragments:", self.invalid_email_fragments)

        # --- self.clients contains client data from AssCache database like external references/Ids, owner status ...
        self.clients = list()
        self.clients_changed = list()      # list indexes of changed records within self.clients

        # --- res_inv_data is caching banking/swap/grant info
        self.res_inv_data = list()

    def connect_acu_db(self, force_reconnect=False):
        if not self.acu_db or force_reconnect:
            self.acu_db = OraDB(usr=self.acu_user, pwd=self.acu_password, dsn=self.acu_dsn,
                                debug_level=self.debug_level)
            self.error_message = self.acu_db.connect()
            if self.error_message:
                self._err(self.error_message, self._ctx_no_file + 'ConnAcuDb')
                self.acu_db = None
        return self.acu_db

    def connect_ass_db(self, force_reconnect=False):
        if not self.ass_db or force_reconnect:
            self.ass_db = PostgresDB(usr=self.ass_user, pwd=self.ass_password, dsn=self.ass_dsn,
                                     debug_level=self.debug_level)
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
            cl_pk = self.cl_save(client_data, ext_refs=co[_EXT_REFS].split(EXT_REFS_SEP), ass_idx=idx)
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
        ''' alternatively:
        if ass_db.select('clients', ['cl_pk'], "cl_ac_id = :ac_id", dict(ac_id=ac_id)):
            break
        cl_pk = ass_db.fetch_value()
        '''
        cl_pk = None
        for cl_rec in self.clients:
            if cl_rec[_AC_ID] == ac_id:
                cl_pk = cl_rec[_ASS_ID]
                break
        else:
            self.error_message = "cl_ass_id_by_ac_id(): Acumen client ID {} not found in AssCache".format(ac_id)
        return cl_pk

    def cl_ass_id_by_sh_id(self, sh_id):
        """
        :param sh_id:   Sihot guest object ID.
        :return:        AssCache client primary key.
        """
        ''' alternatively:
        if ass_db.select('clients', ['cl_pk'], "cl_sh_id = :sh_id", dict(sh_id=sh_id)):
            break
        cl_pk = ass_db.fetch_value()
        '''
        cl_pk = None
        for cl_rec in self.clients:
            if cl_rec[_SH_ID] == sh_id:
                cl_pk = cl_rec[_ASS_ID]
                break
        else:
            self.error_message = "cl_ass_id_by_sh_id(): Sihot guest object ID {} not found in AssCache".format(sh_id)
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

    def rgr_upsert(self, upd_col_values, ho_id, gds_no=None, res_id=None, sub_id=None, commit=False):
        if not gds_no and not (res_id and sub_id):
            return "rgr_upsert({}, {}): Missing reservation id (gds|res-id)".format(ho_id, upd_col_values)
        where_vars = dict(rgr_ho_fk=ho_id)
        if gds_no:
            where_vars.update(rgr_gds_no=gds_no)
        else:
            where_vars.update(rgr_res_id=res_id, rgr_sub_id=sub_id)
        self.error_message = self.ass_db.upsert('res_groups', upd_col_values, where_vars, 'rgr_pk', commit=commit)
        if not self.error_message and self.ass_db.curs.rowcount != 1:
            self.error_message = "rgr_upsert({}, {}, {}): Invalid affected row count; expected 1 but got {}"\
                .format(upd_col_values, ho_id, where_vars, self.ass_db.curs.rowcount)

        return self.error_message

    def rgc_upsert(self, upd_col_values, rgr_pk, room_seq, pers_seq, commit=False):
        where_vars = dict(rgc_rgr_fk=rgr_pk, rgc_room_seq=room_seq, rgc_pers_seq=pers_seq)
        upd_col_values.update(where_vars)
        self.error_message = self.ass_db.upsert('res_group_clients', upd_col_values, where_vars, commit=commit)
        if not self.error_message and self.ass_db.curs.rowcount != 1:
            self.error_message = "rgc_upsert({}, {}): Invalid affected row count; expected 1 but got {}"\
                .format(upd_col_values, rgr_pk, self.ass_db.curs.rowcount)

        return self.error_message

    # =================  RCI data conversion  ==================================================

    def rci_to_sihot_hotel_id(self, rc_resort_id):
        return self.cae.get_config(rc_resort_id, 'RcResortIds', default_value=-369)     # pass default for int type ret

    def rci_arr_to_year_week(self, arr_date):
        year = arr_date.year
        week_1_begin = datetime.datetime.strptime(self.cae.get_config(str(year), 'RcWeeks'), '%Y-%m-%d')
        next_year_week_1_begin = datetime.datetime.strptime(self.cae.get_config(str(year + 1), 'RcWeeks'), '%Y-%m-%d')
        if arr_date < week_1_begin:
            year -= 1
            week_1_begin = datetime.datetime.strptime(self.cae.get_config(str(year), 'RcWeeks'), '%Y-%m-%d')
        elif arr_date > next_year_week_1_begin:
            year += 1
            week_1_begin = next_year_week_1_begin
        diff = arr_date - week_1_begin
        return year, 1 + int(diff.days / 7)

    def rci_ro_group(self, c_idx, is_guest, file_name, line_num):
        """ determine seg=RE RG RI RL  and  grp=RCI External, RCI Guest, RCI Internal, RCI External """
        if self.clients[c_idx][_PRODUCTS]:
            key = 'Internal'
        else:  # not an owner/internal, so will be either Guest or External
            key = 'Guest' if is_guest else 'External'
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
                uprint("sf_client_field_data({}, {}, {}, {}): client object cannot be determined without Id"
                       .format(fetch_fields, search_value, search_field, sf_obj))
                return None
            sf_obj = obj_from_id(search_value)
            if not sf_obj:
                uprint("sf_client_field_data(): {} field value {} is not a valid Lead/Contact/Account SF ID"
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

    def sh_client_upsert(self, fields_dict):
        guest = ClientToSihot(self.cae, connect_to_acu=False)
        col_values = dict()
        for fld, val in fields_dict.items():
            col_name = ac_fld_name(fld)
            if col_name and col_name in guest.acu_col_names:
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
