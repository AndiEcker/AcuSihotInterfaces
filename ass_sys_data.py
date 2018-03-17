import datetime

from ae_db import OraDB, PostgresDB
from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE

from sfif import prepare_connection

# external reference separator and types (also used as Sihot Matchcode/GDS prefix)
EXT_REFS_SEP = ','
EXT_REF_TYPE_RCI = 'RCI'
EXT_REF_TYPE_RCIP = 'RCIP'


def ext_ref_type_sql():
    """
    :return: SQL column expression merging wrongly classified Acumen external ref types holding RCI member IDs.
    """
    # return "decode(CR_TYPE, '" + EXT_REF_TYPE_RCIP + "', '" + EXT_REF_TYPE_RCI + "', 'SPX', '"
    #  + EXT_REF_TYPE_RCI + "', CR_TYPE)"
    return "CASE WHEN CR_TYPE in ('" + EXT_REF_TYPE_RCIP + "', 'SPX') then '" + EXT_REF_TYPE_RCI + "' else CR_TYPE end"


# tuple indexes for Contacts data list (ass_cache.contacts/AssSysData.contacts)
_ASS_ID = 0
_AC_ID = 1
_SF_ID = 2
_SH_ID = 3
_EXT_REFS = 4
_IS_OWNER = 5

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


def _dummy_stub(*args, **kwargs):
    uprint("******  Unexpected call of ass_sys_data._dummy_stub()", args, kwargs)


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

        self.hotel_ids = cae.get_config('hotelIds')
        if self.hotel_ids:      # fetch config data from INI/CFG
            self.resort_cats = cae.get_config('resortCats')
            self.ap_cats = cae.get_config('apCats')
            self.ro_agencies = cae.get_config('roAgencies')
            self.room_change_max_days_diff = cae.get_config('roomChangeMaxDaysDiff', default_value=3)
        else:               # fetch config data from Acumen
            db = self.acu_db
            if not db:      # logon/connect error
                self.error_message = "Missing credentials for to open Acumen database"
                cae.dprint(self.error_message)
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
        self.contacts_changed = list()      # list indexes of changed records within self.contacts

        # --- res_inv_data is caching banking/swap/grant info
        self.res_inv_data = list()

    def connect_acu_db(self, force_reconnect=False):
        if not self.acu_db or force_reconnect:
            self.acu_db = OraDB(usr=self.acu_user, pwd=self.acu_password, dsn=self.acu_dsn,
                                debug_level=self.debug_level)
            self.error_message = self.acu_db.connect()
            if self.error_message:
                print(self.error_message)
                self.acu_db = None
        return self.acu_db

    def connect_ass_db(self, force_reconnect=False):
        if not self.ass_db or force_reconnect:
            self.ass_db = PostgresDB(usr=self.ass_user, pwd=self.ass_password, dsn=self.ass_dsn,
                                     debug_level=self.debug_level)
            self.error_message = self.ass_db.connect()
            if self.error_message:
                print(self.error_message)
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
            print(self.error_message)
            ret = None
        else:
            ret = db.fetch_all()
        if db and not db_opt:  # close temporary db connection if not passed by caller
            db.close()
        return ret

    # ############################  hotel/resort data helpers  ##################################################

    def cat_by_size(self, rs_or_ho_id, ap_size, ap_feats=None, allow_any=True):
        found = None
        if ap_feats:  # optional list of apartment feature ids (AFT_CODEs)
            var = 2 ** len(ap_feats)  # all possible ordered variations of apt features
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

    # ############################  contact data helpers  #########################################################

    def co_fetch_all(self, where_group_order=""):
        if self.ass_db.select('v_contacts_refs_owns', where_group_order=where_group_order):
            return self.ass_db.last_err_msg

        self.contacts = self.ass_db.fetch_all()
        return self.ass_db.last_err_msg

    def co_save(self, ac_id, sf_id, sh_id, ext_refs=None, ass_idx=None, commit=False):
        """
        save/upsert contact data into AssCache database.

        :param ac_id:       Acumen client reference.
        :param sf_id:       Salesforce contact/personal-account id.
        :param sh_id:       Sihot guest object id.
        :param ext_refs:    List of external reference tuples (type, id) to save - used instead of acu_db.
        :param ass_idx:     self.contacts list index of contact record.
        :param commit:      Boolean flag if AssCache data changes should be committed (def=False).
        :return:            Primary Key of upserted AssCache contact record or None on error (see self.error_message).
        """
        col_values = dict(co_ac_id=ac_id, co_sf_id=sf_id, co_sh_id=sh_id)
        if self.ass_db.upsert('contacts', col_values, chk_values=col_values, returning_column='co_pk', commit=commit):
            self.error_message = self.ass_db.last_err_msg
            return None
        co_pk = self.ass_db.fetch_value()

        if self.acu_db and ac_id:
            ers = self.load_view(self.acu_db, 'T_CR', ["DISTINCT " + ext_ref_type_sql(), "CR_REF"],
                                 "CR_CDREF = :ac_id", dict(ac_id=ac_id))
            if ers is None:
                return None
            if ext_refs:
                ers += ext_refs
        else:
            ers = ext_refs
        for er in ers:
            col_values = dict(er_co_fk=co_pk, er_type=er[0], er_id=er[1])
            if self.ass_db.upsert('external_refs', col_values, chk_values=col_values, commit=commit):
                break
        if self.ass_db.last_err_msg:
            self.error_message = self.ass_db.last_err_msg
            return None

        if not ass_idx:
            ass_idx = self.co_idx_by_ass_id(co_pk)
            if ass_idx is None:
                self.contacts.append((co_pk, ac_id, sf_id, sh_id, EXT_REFS_SEP.join(ers), 0))
        else:
            self.contacts[ass_idx][_ASS_ID] = co_pk

        return co_pk

    def co_flush(self):
        for idx in self.contacts_changed:
            co = self.contacts[idx]
            co_pk = self.co_save(co[_AC_ID], co[_SF_ID], co[_SH_ID], ext_refs=co[_EXT_REFS].split(EXT_REFS_SEP),
                                 ass_idx=idx)
            if co_pk is None:
                return self.error_message

        return self.ass_db.commit()

    def co_check_ext_refs(self):
        resort_codes = self.cae.get_config('ClientRefsResortCodes').split(EXT_REFS_SEP)
        found_ids = dict()
        for c_rec in self.contacts:
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
                               .format(ref.split('=')[0] if '=' in ref else EXT_REF_TYPE_RCI,
                                       repr(ref), ';'.join([_[_AC_ID] for _ in recs])))
        for dup in sorted(dup_ids):
            self._warn(dup, self._ctx_no_file + 'CheckClientsDataExtRefDuplicates')

    def co_ass_id_by_idx(self, index):
        return self.contacts[index][_ASS_ID]

    def co_ass_id_by_ac_id(self, ac_id):
        """
        :param ac_id:   Acumen client reference/ID.
        :return:        AssCache contact primary key.
        """
        ''' alternatively:
        if ass_db.select('contacts', ['co_pk'], "co_ac_id = :ac_id", dict(ac_id=ac_id)):
            break
        co_pk = ass_db.fetch_value()
        '''
        co_pk = None
        for co_rec in self.contacts:
            if co_rec[_AC_ID] == ac_id:
                co_pk = co_rec[_ASS_ID]
                break
        else:
            self.error_message = "co_ass_id_by_ac_id(): Acumen client ID {} not found in AssCache".format(ac_id)
        return co_pk

    def co_ass_id_by_sh_id(self, sh_id):
        """
        :param sh_id:   Sihot guest object ID.
        :return:        AssCache contact primary key.
        """
        ''' alternatively:
        if ass_db.select('contacts', ['co_pk'], "co_sh_id = :sh_id", dict(sh_id=sh_id)):
            break
        co_pk = ass_db.fetch_value()
        '''
        co_pk = None
        for co_rec in self.contacts:
            if co_rec[_SH_ID] == sh_id:
                co_pk = co_rec[_ASS_ID]
                break
        else:
            self.error_message = "co_ass_id_by_sh_id(): Sihot guest object ID {} not found in AssCache".format(sh_id)
        return co_pk

    def co_ac_id_by_idx(self, index):
        return self.contacts[index][_AC_ID]

    def co_sh_id_by_idx(self, index):
        return self.contacts[index][_SH_ID]

    def co_ext_refs_by_idx(self, index):
        return self.contacts[index][_EXT_REFS].split(EXT_REFS_SEP)

    def co_idx_by_ass_id(self, ass_id):
        for list_idx, c_rec in enumerate(self.contacts):
            if c_rec[_ASS_ID] == ass_id:
                return list_idx
        return None

    def co_idx_by_rci_id(self, imp_rci_ref, file_name, line_num):
        """ determine list index in cached contacts """
        # check first if client exists
        for list_idx, c_rec in enumerate(self.contacts):
            ext_refs = c_rec[_EXT_REFS]
            if ext_refs and imp_rci_ref in ext_refs.split(EXT_REFS_SEP):
                break
        else:
            sf_id, dup_contacts = self.sales_force.client_by_rci_id(imp_rci_ref)
            if self.sales_force.error_msg:
                self._err("co_idx_by_rci_id() Salesforce connect/fetch error " + self.sales_force.error_msg,
                          file_name, line_num, importance=3)
            if len(dup_contacts) > 0:
                self._err("Found duplicate Salesforce client(s) with main or external RCI ID {}. Used client {}, dup={}"
                          .format(imp_rci_ref, sf_id, dup_contacts), file_name, line_num)
            if sf_id:
                ass_id = self.sales_force.co_ass_id_by_idx(sf_id)
                if self.sales_force.error_msg:
                    self._err("co_idx_by_rci_id() AssCache id fetch error " + self.sales_force.error_msg,
                              file_name, line_num,
                              importance=3)
                ac_id = self.sales_force.co_ac_id_by_idx(sf_id)
                if self.sales_force.error_msg:
                    self._err("co_idx_by_rci_id() Acumen id fetch error " + self.sales_force.error_msg,
                              file_name, line_num,
                              importance=3)
                sh_id = self.sales_force.co_sh_id_by_idx(sf_id)
                if self.sales_force.error_msg:
                    self._err("co_idx_by_rci_id() Sihot id fetch error " + self.sales_force.error_msg,
                              file_name, line_num,
                              importance=3)
            else:
                ass_id = None
                ac_id = None    # EXT_REF_TYPE_RCI + imp_rci_ref
                sh_id = None
            self.contacts.append((ass_id, ac_id, sf_id, sh_id, imp_rci_ref, 0))
            list_idx = len(self.contacts) - 1
            self.contacts_changed.append(list_idx)
        return list_idx

    def co_complete_with_sh_id(self, c_idx, sh_id):
        """ complete contacts with imported data and sihot objid """
        c_rec = self.contacts[c_idx]
        if not c_rec[_SH_ID] or c_rec[_SH_ID] != sh_id:
            if c_rec[_SH_ID]:
                self._warn("Sihot guest object id changed from {} to {} for Salesforce contact {}"
                           .format(c_rec[_SH_ID], sh_id, c_rec[_SF_ID]))
            self.contacts[c_idx] = (c_rec[_ASS_ID], c_rec[_AC_ID], c_rec[_SF_ID], sh_id, c_rec[_EXT_REFS],
                                    c_rec[_IS_OWNER])
            self.contacts_changed.append(c_idx)

    def co_sent_to_sihot(self):
        return [i for i, _ in enumerate(self.contacts) if _[_SH_ID]]

    def co_list_by_ac_id(self, ac_id):
        return [_ for _ in self.contacts if _[_AC_ID] == ac_id]

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
        where_vars = dict(ho_id=ho_id)
        if gds_no:
            where_vars.update(rgr_gds_no=gds_no)
        else:
            where_vars.update(rgr_res_id=res_id, rgr_sub_id=sub_id)
        self.error_message = self.ass_db.upsert('res_groups', upd_col_values, where_vars, 'rgr_pk', commit=commit)
        if not self.error_message and self.ass_db.curs.rowcount != 1:
            self.error_message = "rgr_upsert({}, {}, {}): Invalid affected row count; expected 1 but got {}"\
                .format(upd_col_values, ho_id, where_vars, self.ass_db.curs.rowcount)

        return self.error_message

    def rgc_upsert(self, upd_col_values, rgr_pk, commit=False):
        where_vars = dict(rgc_rgr_fk=rgr_pk)
        self.error_message = self.ass_db.upsert('res_group_contacts', upd_col_values, where_vars, commit=commit)
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