import os
import datetime

from ae_lockfile import LockFile
from ae_db import OraDB
from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE

from sfif import prepare_connection

# init constants and load constant config settings
EXT_REFS_SEP = ','
RCI_MATCH_AND_BOOK_CODE_PREFIX = 'rci'

# tuple indexes for AssSysData.contacts list
_ACU_ID = 0
_SF_ID = 1
_SH_ID = 2
_EXT_REFS = 3
_IS_OWNER = 4

# tuple indexes for Reservation Inventory data (AssSysData.res_inv_data
_WKREF = 0
_YEAR = 1
_ROREF = 2
_SWAPPED = 3
_GRANTED = 4


def _dummy_stub(*args, **kwargs):
    uprint("******  Unexpected call of acu_sf_sh_sys_data._dummy_stub()", args, kwargs)


class AssSysData:   # Acumen, Salesforce, Sihot and config system data provider
    def __init__(self, cae, acu_user=None, acu_password=None,
                 err_logger=_dummy_stub, warn_logger=_dummy_stub, ctx_no_file=''):
        self.cae = cae
        self._err = err_logger
        self._warn = warn_logger
        self._ctx_no_file = ctx_no_file
        
        self.acu_user = acu_user or cae.get_option('acuUser')
        self.acu_password = acu_password or cae.get_option('acuPassword')
        self.acu_dsn = cae.get_option('acuDSN')

        self.debug_level = cae.get_option('debugLevel')

        self.error_message = ''

        self.hotel_ids = cae.get_config('hotelIds')
        if self.hotel_ids:      # fetch config data from INI/CFG
            self.resort_cats = cae.get_config('resortCats')
            self.ap_cats = cae.get_config('apCats')
            self.ro_agencies = cae.get_config('roAgencies')
            self.room_change_max_days_diff = cae.get_config('roomChangeMaxDaysDiff', default_value=3)
        else:               # fetch config data from Acumen
            db = self.connect_db()
            if not db:      # logon/connect error
                return

            self.hotel_ids = self.load_view(db, 'T_LU', ['LU_NUMBER', 'LU_ID'],
                                            "LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1")

            any_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_ANY'")
            bhc_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_BHC'")
            pbc_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_PBC'")
            bhh_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_BHH'")
            hmc_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_HMC'")
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

        # open and check Salesforce connection
        self.sales_force, _ = prepare_connection(cae)
        if not self.sales_force:
            self.error_message = "Salesforce connection failed - please check your account data and credentials"
            cae.dprint(self.error_message)
            return
        elif self.sales_force.error_msg:
            self.error_message = self.sales_force.error_msg
            cae.dprint(self.error_message)
            return

        self.client_refs_add_exclude = cae.get_config('ClientRefsAddExclude', default_value='').split(EXT_REFS_SEP)

        # --- contacts is caching contact data like external references/Ids, owner status ...
        self.contacts = list()
        self.contacts_changed = False

        # --- res_inv_data is caching banking/swap/grant info
        self.res_inv_data = list()

    def connect_db(self):
        db = OraDB(usr=self.acu_user, pwd=self.acu_password, dsn=self.acu_dsn)
        self.error_message = db.connect()
        if self.error_message:
            print(self.error_message)
            return None
        return db

    def load_view(self, db_opt, view, cols, where, bind_vars=None):
        if db_opt:      # use existing db connection if passed by caller
            db = db_opt
            self.error_message = ""
        else:
            db = self.connect_db()
        if not self.error_message:
            self.error_message = db.select(view, cols, where, bind_vars)
        if self.error_message:
            print(self.error_message)
            ret = None
        else:
            ret = db.fetch_all()
        if db and not db_opt:  # close temporary db connection if not passed by caller
            db.close()
        return ret

    def get_ro_agency_objid(self, ro_code):
        return next((cols[1] for cols in self.ro_agencies if cols[0] == ro_code), None)

    def get_ro_agency_matchcode(self, ro_code):
        return next((cols[2] for cols in self.ro_agencies if cols[0] == ro_code), None)

    def get_ro_sihot_mkt_seg(self, ro_code):
        sihot_mkt_seg = next((cols[3] for cols in self.ro_agencies if cols[0] == ro_code), None)
        return sihot_mkt_seg or ro_code

    def get_ro_res_group(self, ro_code):
        return next((cols[4] for cols in self.ro_agencies if cols[0] == ro_code), None)

    def get_size_cat(self, rs_code, ap_size, ap_feats=None, allow_any=True):
        found = None
        if ap_feats:  # optional list of apartment feature ids (AFT_CODEs)
            var = 2 ** len(ap_feats)  # all possible ordered variations of apt features
            ap_feats = [str(ft) for ft in sorted(ap_feats)]
        for resort in [rs_code] + (['ANY'] if rs_code != 'ANY' and allow_any else list()):
            view = self.resort_cats[resort]
            if not view:
                continue
            key = ap_size
            if ap_feats:
                key += '_' + '_'.join(ap_feats)
            found = next((cols[1] for cols in view if cols[0] == key), None)

            if not found and ap_feats:
                for deg in range(var - 1):
                    key = ap_size \
                          + ('' if var - deg - 2 == 0 else '_') \
                          + '_'.join([ft for no, ft in enumerate(ap_feats) if 2 ** no & var - deg - 2])
                    found = next((cols[1] for cols in view if cols[0] == key), None)
                    if found:
                        break

            if found:
                break

        return found

    def get_room_cat(self, room_no):
        return next((cols[1] for cols in self.ap_cats if cols[0] == room_no), None)

    def get_hotel_ids(self, acu_rs_codes=None):
        if acu_rs_codes is None:
            hot_id_list = [cols[0] for cols in self.hotel_ids]
        else:
            hot_id_list = [cols[0] for cols in self.hotel_ids if cols[1] in acu_rs_codes]
        return hot_id_list

    # =================  helpers  =========================================================================

    def hotel_acu_to_sihot(self, rs_code):
        sh_hotel_id = 0
        for sh_hotel_id, acu_rs_code in self.hotel_ids:
            if acu_rs_code == rs_code:
                break
        return sh_hotel_id

    def hotel_sihot_to_acu(self, hotel_id):
        acu_rs_code = ''
        for sh_hotel_id, acu_rs_code in self.hotel_ids:
            if sh_hotel_id == hotel_id:
                break
        return acu_rs_code

    def rci_to_sihot_hotel_id(self, rc_resort_id):
        return self.cae.get_config(rc_resort_id, 'RcResortIds', default_value=-369)     # pass default for int type ret

    def rci_to_sihot_room_cat(self, sh_hotel_id, room_size):
        return self.get_size_cat(self.hotel_sihot_to_acu(sh_hotel_id), room_size)

    def rc_arr_to_year_week(self, arr_date):
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

    # =================  contacts  =========================================================================
    def fetch_contacts(self):
        """ Populates instance list self.contacts from Acumen and Salesforce with data lookup, check and merge """

        def _find_and_merge():  # c_idx, s_rec and a_rec are defined in the for loop in outer method:
            s_acu_id, s_sf_id, s_sh_id, s_ext_refs, s_owner = s_rec
            a_acu_id, a_sf_id, a_sh_id, a_ext_refs, a_owner = a_rec

            s_ext_refs = set(s_ext_refs.split(EXT_REFS_SEP)) if s_ext_refs else set()
            a_ext_refs = set(a_ext_refs.split(EXT_REFS_SEP)) if a_ext_refs else set()

            match = None
            if s_sf_id and s_sf_id == a_sf_id:
                match = 'SF=' + s_sf_id
            elif s_acu_id and s_acu_id == a_acu_id:
                match = 'ACU=' + s_acu_id
            elif s_sh_id and s_sh_id == a_sh_id:
                match = 'SH=' + s_sh_id
            elif s_ext_refs & a_ext_refs:  # check for matching RCI references/Ids via set intersection
                match = 'RCI=' + EXT_REFS_SEP.join(s_ext_refs & a_ext_refs)

            if match:
                msg_prefix = "SihotResImport.._find_and_merge(): Acumen/Salesforce discrepancy for " + match + " on "
                ctx = self._ctx_no_file + 'MergeClientData'
                if s_acu_id and a_acu_id and s_acu_id != a_acu_id:
                    self._warn(msg_prefix + "Acumen ID: Salesforce={}, Acumen={}".format(s_acu_id, a_acu_id), ctx)
                if s_sf_id and a_sf_id and s_sf_id != a_sf_id:
                    self._warn(msg_prefix + "Salesforce ID: Salesforce={}, Acumen={}".format(s_sf_id, a_sf_id), ctx)
                if s_sh_id and a_sh_id and s_sh_id != a_sh_id:
                    self._warn(msg_prefix + "Sihot ID: Salesforce={}, Acumen={}".format(s_sh_id, a_sh_id), ctx)
                if s_ext_refs <= a_ext_refs:  # (s_ext_refs and a_ext_refs and s_ext_refs <= a_ext_refs) or a_ext_refs:
                    self._warn(msg_prefix + "missing RCI IDs in Salesforce={}, Acumen={}".format(s_sh_id, a_sh_id), ctx)
                if s_owner != a_owner:
                    self._warn(msg_prefix + "Owner status: Salesforce={}, Acumen={}".format(s_owner, a_owner), ctx)
                # -- merge
                self.contacts[c_idx] = (s_acu_id or a_acu_id, s_sf_id or a_sf_id, s_sh_id or a_sh_id,
                                        EXT_REFS_SEP.join(s_ext_refs | a_ext_refs), s_owner or a_owner)
            return match

        # establish file lock
        file_lock = LockFile(self.cae.get_config('CONTACTS_LOCK_FILE', default_value='contacts.lock'))
        err_msg = file_lock.lock()
        if err_msg:
            return err_msg

        # check if file exists (or if it is instead the first run or a reset)
        contacts_file_name = self.cae.get_config('CONTACTS_DATA_FILE', default_value='contacts.data')
        if os.path.isfile(contacts_file_name):
            with open(contacts_file_name) as f:
                self.contacts = eval(f.read())
            file_lock.unlock()
            return ""

        # fetch from Acumen on first run or after reset (deleted cache files) - after locking cache files
        self._warn("Fetching client data from Acumen (needs some minutes)", self._ctx_no_file + 'FetchClientData',
                   importance=4)
        self.contacts = \
            self.load_view(None, 'V_ACU_CD_DATA',
                           ["CD_CODE", "SIHOT_SF_ID", "CD_SIHOT_OBJID",
                            "trim('" + EXT_REFS_SEP + "' from CD_RCI_REF || '" + EXT_REFS_SEP +
                            "' || replace(replace(EXT_REFS, 'RCIP=', ''), 'RCI=', '')) as EXT_REFS",
                            "case when instr(SIHOT_GUEST_TYPE, 'O') > 0 or instr(SIHOT_GUEST_TYPE, 'I') > 0"
                            " or instr(SIHOT_GUEST_TYPE, 'K') > 0 then 1 else 0 end as IS_OWNER",
                            ],
                           # found also SPX/TRC prefixes for RCI refs/ids in EXT_REFS/T_CR
                           "CD_SIHOT_OBJID is not NULL or CD_RCI_REF is not NULL or instr(EXT_REFS, 'RCI') > 0"
                           " or instr(EXT_REFS, 'SF=') > 0 or SIHOT_SF_ID is not NULL")

        # fetch from Salesforce all contacts/clients with main/external RCI Ids for to merge them into contacts
        sf_contacts = self.sales_force.contacts_with_rci_id(EXT_REFS_SEP)
        if self.sales_force.error_msg:
            return self.sales_force.error_msg
        # merging list of tuples (Acu-CD_CODE, Sf-Id, Sihot-Id, ext_refs, is_owner) into contacts
        for s_rec in sf_contacts:
            for c_idx, a_rec in enumerate(self.contacts):
                if _find_and_merge():
                    break   # sf contact found in acu and merged, so break inner loop for to check next sf contact
            else:   # sf contact not found, so add it to contacts
                self.contacts.append(s_rec)

        # check for duplicate and blocked RCI Ids in verbose debug mode
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            self._warn('Checking clients data for duplicates and resort IDs',
                       self._ctx_no_file + 'CheckClientsData', importance=3)
            self.check_contacts()

        # save fetched data to cache
        with open(contacts_file_name, 'w') as f:
            f.write(repr(self.contacts))

        file_lock.unlock()

        return ""

    def save_contacts(self):
        # establish file lock
        file_lock = LockFile(self.cae.get_config('CONTACTS_LOCK_FILE'))
        err_msg = file_lock.lock()
        if err_msg:
            return err_msg

        with open(self.cae.get_config('CONTACTS_DATA_FILE'), 'w') as f:
            f.write(repr(self.contacts))

        file_lock.unlock()

        return ""

    def check_contacts(self):
        resort_codes = self.cae.get_config('ClientRefsResortCodes').split(EXT_REFS_SEP)
        found_ids = dict()
        for c_rec in self.contacts:
            if c_rec[_EXT_REFS]:
                for rci_id in c_rec[_EXT_REFS].split(EXT_REFS_SEP):
                    if rci_id not in found_ids:
                        found_ids[rci_id] = [c_rec]
                    elif [_ for _ in found_ids[rci_id] if _[_ACU_ID] != c_rec[_ACU_ID]]:
                        found_ids[rci_id].append(c_rec)
                    if c_rec[_ACU_ID]:
                        if rci_id in self.client_refs_add_exclude and c_rec[_ACU_ID] not in resort_codes:
                            self._warn("Resort RCI ID {} found in client {}".format(rci_id, c_rec[_ACU_ID]),
                                       self._ctx_no_file + 'CheckClientsDataResortId')
                        elif c_rec[_ACU_ID] in resort_codes and rci_id not in self.client_refs_add_exclude:
                            self._warn("Resort {} is missing RCI ID {}".format(c_rec[_ACU_ID], rci_id),
                                       self._ctx_no_file + 'CheckClientsDataResortId')
        # prepare found duplicate ids, prevent duplicate printouts and re-order for to separate RCI refs from others
        dup_ids = list()
        for ref, recs in found_ids.items():
            if len(recs) > 1:
                dup_ids.append("Duplicate external {} ref {} found in clients: {}"
                               .format(ref.split('=')[0] if '=' in ref else 'RCI',
                                       repr(ref), ';'.join([_[_ACU_ID] for _ in recs])))
        for dup in sorted(dup_ids):
            self._warn(dup, self._ctx_no_file + 'CheckClientsDataExtRefDuplicates')

    def get_contact_index(self, imp_rci_ref, file_name, line_num):
        """ determine list index in cached contacts """
        # check first if client exists
        for list_idx, c_rec in enumerate(self.contacts):
            ext_refs = c_rec[_EXT_REFS]
            if ext_refs and imp_rci_ref in ext_refs.split(EXT_REFS_SEP):
                break
        else:
            sf_contact_id, dup_contacts = self.sales_force.contact_by_rci_id(imp_rci_ref)
            if self.sales_force.error_msg:
                self._err("get_contact_index() Salesforce connect/fetch error " + self.sales_force.error_msg,
                          file_name, line_num, importance=3)
            if len(dup_contacts) > 0:
                self._err("Found duplicate Salesforce client(s) with main or external RCI ID {}. Used client {}, dup={}"
                          .format(imp_rci_ref, sf_contact_id, dup_contacts), file_name, line_num)
            if sf_contact_id:
                sh_guest_id = self.sales_force.contact_sh_id(sf_contact_id)
                if self.sales_force.error_msg:
                    self._err("get_contact_index() sihot id fetch error " + self.sales_force.error_msg,
                              file_name, line_num,
                              importance=3)
            else:
                sh_guest_id = None
            client = (RCI_MATCH_AND_BOOK_CODE_PREFIX + imp_rci_ref, sf_contact_id, sh_guest_id, imp_rci_ref, 0)
            self.contacts.append(client)
            list_idx = len(self.contacts) - 1
            self.contacts_changed = True
        return list_idx

    def mkt_seg_grp(self, c_idx, is_guest, file_name, line_num):
        """ determine seg=RE RG RI RL  and  grp=RCI External, RCI Guest, RCI Internal, RCI External """
        if self.contacts[c_idx][_IS_OWNER]:
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

    def complete_contacts_with_sh_id(self, c_idx, sh_id):
        """ complete contacts with imported data and sihot objid """
        c_rec = self.contacts[c_idx]
        if not c_rec[_SH_ID] or c_rec[_SH_ID] != sh_id:
            if c_rec[_SH_ID]:
                self._warn("Sihot guest object id changed from {} to {} for Salesforce contact {}"
                           .format(c_rec[_SH_ID], sh_id, c_rec[_SF_ID]))
            self.contacts[c_idx] = (c_rec[_ACU_ID], c_rec[_SF_ID], sh_id, c_rec[_EXT_REFS], c_rec[_IS_OWNER])
            self.contacts_changed = True

    def sent_contacts(self):
        return [i for i, _ in enumerate(self.contacts) if _[_SH_ID]]

    def contact_acu_id(self, index):
        return self.contacts[index][_ACU_ID]

    def contact_sh_id(self, index):
        return self.contacts[index][_SH_ID]

    def contact_ext_refs(self, index):
        return self.contacts[index][_EXT_REFS].split(EXT_REFS_SEP)

    # =================  res_inv_data  =========================================================================

    def fetch_res_inv_data(self):
        inv_file_name = self.cae.get_config('RES_INV_DATA_FILE', default_value='res_inv.data')
        if os.path.isfile(inv_file_name):
            with open(inv_file_name) as f:
                self.res_inv_data = eval(f.read())
                return ""

        # file not exists (first run or reset)
        self._warn("Fetching reservation inventory from Acumen (needs some minutes)",
                   self._ctx_no_file + 'FetchResInv', importance=4)
        file_lock = LockFile(self.cae.get_config('RES_INV_LOCK_FILE', default_value='res_inv.lock'))
        err_msg = file_lock.lock()
        if err_msg:
            return err_msg

        # fetch from Acumen on first run or after reset (deleted cache files) - after locking cache files
        self.res_inv_data = self.load_view(None, 'T_AOWN_VIEW',
                                           ['AOWN_WKREF', 'AOWN_YEAR', 'AOWN_ROREF',  # 'AOWN_RSREF',
                                            'AOWN_SWAPPED_WITH', 'AOWN_GRANTED_TO'],
                                           "AOWN_YEAR >= to_char(sysdate, 'YYYY')"
                                           " and AOWN_RSREF in ('BHC', 'BHH', 'HMC', 'PBC')")
        with open(inv_file_name, 'w') as f:
            f.write(repr(self.res_inv_data))

        file_lock.unlock()

        return ""

    def allocated_room(self, room_no, arr_date):
        year, week = self.rc_arr_to_year_week(arr_date)
        for r_rec in self.res_inv_data:
            if r_rec[_WKREF] == room_no.lstrip('0') + '-' + ('0' + str(week))[:2] and r_rec[_YEAR] == year:
                if r_rec[_GRANTED] == 'HR' or not r_rec[_SWAPPED] \
                        or r_rec[_ROREF] in ('RW', 'RX', 'rW'):
                    return room_no
        return ''
