"""
Acumen interface constants and helpers
"""
import datetime
from copy import deepcopy

from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE
from ae_db import OraDB
from ae_sys_data import ACTION_UPDATE, ACTION_DELETE, FAD_FROM
from shif import ClientToSihot, ResToSihot, ECM_TRY_AND_IGNORE_ERRORS, ECM_ENSURE_WITH_ERRORS, ECM_DO_NOT_SEND_CLIENT
from sxmlif import SihotXmlBuilder
from sys_data_ids import SDI_AC

ACU_DEF_USR = 'SIHOT_INTERFACE'
ACU_DEF_DSN = 'SP.TEST'

# second couple Acumen ID suffix
AC_ID_2ND_COUPLE_SUFFIX = 'P2'

# Acumen field name mapping tuple, having the following elements (put None if not needed for a field):
FMI_FLD_NAME = 0    # field name
FMI_COL_NAME = 1    # system view sql column name
FMI_SQL_EXPR = 2    # system view sql expression
FMI_CON_FUNC = 3    # field value converter - ONLY USED FOR EXT_REFS
CLI_FIELD_MAP = [       # client data
    ('AcId', 'CD_CODE',),
    ('SfId', 'SIHOT_SF_ID'),
    ('ShId', 'CD_SIHOT_OBJID'),
    ('Salutation', 'SIHOT_SALUTATION1'),
    ('Title', 'SIHOT_TITLE1'),
    ('GuestType', 'SIHOT_GUESTTYPE1'),
    ('Surname', 'CD_SNAM1'),
    ('Forename', 'CD_FNAM1'),
    ('Street', 'CD_ADD11'),
    ('POBox', 'CD_ADD12',
     "nvl(CD_ADD12, CD_ADD13)"),
    ('Postal', 'CD_POSTAL'),
    ('City', 'CD_CITY'),
    ('Country', 'SIHOT_COUNTRY'),
    ('State', 'SIHOT_STATE'),
    ('Language', 'SIHOT_LANG'),
    ('Comment', 'SH_COMMENT',
     "SIHOT_GUEST_TYPE || ' ExtRefs=' || EXT_REFS"),
    ('HomePhone', 'CD_HTEL1'),
    ('WorkPhone', 'CD_WTEL1'
     "CD_WTEL1 || CD_WEXT1"),
    ('MobilePhone', 'CD_MOBILE1'),
    ('MobilePhoneB', 'CD_LAST_SMS_TEL'),
    ('Fax', 'CD_FAX'),
    ('Email', 'CD_EMAIL'),
    ('EmailB', 'CD_SIGNUP_EMAIL'),
    ('DOB', 'CD_DOB1'),
    ('Password', 'CD_PASSWORD'),
    ('RCIRef', 'CD_RCI_REF'),
    ('ExtRefs', 'EXT_REFS',
     None,
     lambda f, v: f.string_to_records(v, ('Type', 'Id'))),
    ]
RES_FIELD_MAP = [       # reservation data
    ('ResHotelId', 'RUL_SIHOT_HOTEL'),
    # ('ResNo', ),
    # ('ResSubNo', ),
    ('ResGdsNo', 'SIHOT_GDSNO',
     "nvl(SIHOT_GDSNO, case when RUL_SIHOT_RATE in ('TC', 'TK') then case when RUL_ACTION <> '" + ACTION_UPDATE + "'"
     " then (select 'TC' || RH_EXT_BOOK_REF from T_RH"
     " where RH_CODE = F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_RHREF'))"
     " else '(lost)' end else to_char(RUL_PRIMARY) end)"),  # RUL_PRIMARY needed for to delete/cancel res
    ('ResObjId', 'RU_SIHOT_OBJID'),
    ('ResArrival', 'ARR_DATE',
     "case when ARR_DATE is not NULL then ARR_DATE when RUL_ACTION <> '" + ACTION_UPDATE + "'"
     " then to_date(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_FROM_DATE'), 'DD-MM-YY')"
     " end"),
    ('ResDeparture', 'DEP_DATE',
     "case when DEP_DATE is not NULL then DEP_DATE when RUL_ACTION <> '" + ACTION_UPDATE + "'"
     " then to_date(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_FROM_DATE'), 'DD-MM-YY')"
     " + to_number(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_DAYS'))"
     " end"),
    ('ResRoomCat', 'RUL_SIHOT_CAT',
     "F_SIHOT_CAT('RU' || RUL_PRIMARY)"),
    # "case when RUL_SIHOT_RATE in ('TC', 'TK') then F_SIHOT_CAT('RU' || RU_CODE) else RUL_SIHOT_CAT end"},
    ('ResPriceCat', 'SH_PRICE_CAT',
     "F_SIHOT_CAT('RU' || RUL_PRIMARY)"),
    ('ResRoomNo', 'RUL_SIHOT_ROOM'),
    ('AcId', 'OC_CODE',
     "nvl(OC_CODE, CD_CODE)"),
    ('ShId', 'OC_SIHOT_OBJID',
     "to_char(nvl(OC_SIHOT_OBJID, CD_SIHOT_OBJID))"),
    ('ResStatus', 'SH_RES_TYPE',
     "case when RUL_ACTION = '" + ACTION_DELETE + "' then 'S' else nvl(SIHOT_RES_TYPE, 'S') end"),
    ('ResAction', 'RUL_ACTION'),
    ('ResVoucherNo', 'RH_EXT_BOOK_REF'),
    ('ResBooked', 'RH_EXT_BOOK_DATE'),
    ('ResBoard', 'RUL_SIHOT_PACK'),
    ('ResSource', 'RU_SOURCE'),
    ('ResMktGroup', 'RO_SIHOT_RES_GROUP'),      # Acumen value in RO_RES_GROUP
    ('ResMktGroupNN', 'RO_SIHOT_SP_GROUP'),
    ('ResMktSegment', 'SIHOT_MKT_SEG',
     "nvl(SIHOT_MKT_SEG, RUL_SIHOT_RATE)"),     # SIHOT_MKT_SEG is NULL if RU is deleted
    ('ResRateSegment', 'RUL_SIHOT_RATE'),
    ('ResNote', 'SIHOT_NOTE'),
    ('ResLongNote', 'SIHOT_TEC_NOTE'),
    ('ResFlightArrComment', 'SH_EXT_REF',
     "trim(RU_FLIGHT_NO || ' ' || RU_FLIGHT_PICKUP || ' ' || RU_FLIGHT_AIRPORT)"),
    ('ResFlightETA', 'RU_FLIGHT_LANDS'),
    ('ResAccount', 'SIHOT_PAYMENT_INST'),
    ('ResAllotmentNo', 'SIHOT_ALLOTMENT_NO'),
    ('ResAdults', 'RU_ADULTS'),
    ('ResChildren', 'RU_CHILDREN'),
    ('ResGroupNo', 'SIHOT_LINK_GROUP'),
    # only one room per reservation, so not needed: ('ResRooms', 'SH_ROOMS'),
    # ('ResPersons', )
    ]
'''
for idx in range(1, EXT_REF_COUNT + 1):
    FIELD_MAP.append(('ExtRefs' + str(idx) + 'Type', 'EXT_REF_TYPE' + str(idx),
                      "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, " + str(idx) + "), '[^=]+', 1, 1)"))
    FIELD_MAP.append(('ExtRefs' + str(idx) + 'Id', 'EXT_REF_ID' + str(idx),
                      "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, " + str(idx) + "), '[^=]+', 1, 2)"))
for idx in range(1, RES_MAX_ADULTS + 1):
    FIELD_MAP.append(('ResPerson' + str(idx) + 'Surname', 'SH_ADULT' + str(idx) + '_NAME'))     # ResPersons1Surname
    FIELD_MAP.append(('ResPerson' + str(idx) + 'Forename', 'SH_ADULT' + str(idx) + '_NAME2'))   # ResPersons1Forename
    FIELD_MAP.append(('ResPerson' + str(idx) + 'DOB', 'SH_ADULT' + str(idx) + '_DOB'))          # ResPersons1DOB
for idx in range(1, RES_MAX_CHILDREN + 1):
    FIELD_MAP.append(('ResPerson' + str(idx) + 'Surname', 'SH_CHILD' + str(idx) + '_NAME'))     # ResPersons1Surname
    FIELD_MAP.append(('ResPerson' + str(idx) + 'Forename', 'SH_CHILD' + str(idx) + '_NAME2'))   # ResPersons1Forename
    FIELD_MAP.append(('ResPerson' + str(idx) + 'DOB', 'SH_CHILD' + str(idx) + '_DOB'))          # ResPersons1DOB
'''

row_field_name_map = {fmi[FMI_COL_NAME]: fmi[FMI_FLD_NAME] for fmi in CLI_FIELD_MAP + RES_FIELD_MAP}


def add_ac_options(cae):
    cae.add_option('acuUser', "Acumen/Oracle user account name", ACU_DEF_USR, 'u')
    cae.add_option('acuPassword', "Acumen/Oracle user account password", '', 'p')
    cae.add_option('acuDSN', "Acumen/Oracle data source name", ACU_DEF_DSN, 'd')


def remap_row_to_field_names(crow):
    fld_vals = dict()
    for k, v in crow.items():
        if k in row_field_name_map:
            fld_vals[row_field_name_map[k]] = v
    return fld_vals


def init_col_names(field_col_map, rec):
    return [fmi[FMI_COL_NAME] for fmi in field_col_map if fmi[FMI_FLD_NAME] in rec]


def init_col_expressions(field_col_map, col_names):
    return [fmi[FMI_SQL_EXPR] + " as " + fmi[FMI_COL_NAME]
            if len(fmi) > FMI_SQL_EXPR and fmi[FMI_SQL_EXPR]
            else fmi[FMI_COL_NAME]
            for fmi in field_col_map if fmi[FMI_COL_NAME] in col_names]


class AcuDbRows:
    def __init__(self, cae):
        self.cae = cae

        self._last_fetch = None     # store fetch_from_acu timestamp

        self.ora_db = OraDB(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'),
                            app_name=cae.app_name(), debug_level=cae.get_option('debugLevel'))
        err_msg = self.ora_db.connect()
        if err_msg:
            uprint("AcuDbRows.__init__() db connect error: {}".format(err_msg))

    '''
    def __init__(self, cae, elem_col_map=None, use_kernel=None):
        super(_AcuXmlBuilder, self).__init__(cae)
        self.cae = cae
        elem_col_map = deepcopy(elem_col_map)
        self.elem_col_map = elem_col_map
        self.use_kernel_interface = cae.get_option('useKernelForRes') if use_kernel is None else use_kernel

        self.fix_fld_vals = dict()
        self.acu_col_names = list()  # acu_col_names and acu_col_expres need to be in sync
        self.acu_col_expres = list()
        for c in elem_col_map:
            if 'colVal' in c:
                self.fix_fld_vals[c['colName']] = c['colVal']
            elif c['colName'] not in self.acu_col_names:
                self.acu_col_names.append(c['colName'])
                self.acu_col_expres.append(c['colValFromAcu'] + " as " + c['colName'] if 'colValFromAcu' in c
                                           else c['colName'])
        self.response = None

        self._rows = list()  # list of dicts, used by inheriting class for to store the records to send to SiHOT.PMS
        self._recs = Records()  # used by inheriting class for to store the Record instances to be send to SiHOT.PMS
        self._current_rec_i = 0

        self._xml = ''
        self._indent = 0
    '''

    def __del__(self):
        if self.ora_db:
            self.ora_db.close()

    def _add_to_acumen_sync_log(self, table, primary, action, status, message, logref):
        self.cae.dprint('AcuDbRows._add_to_acumen_sync_log() fetched/now:', self._last_fetch, datetime.datetime.now(),
                        minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        return self.ora_db.insert('T_SRSL',
                                  {'SRSL_TABLE': table[:6],
                                   'SRSL_PRIMARY': str(primary)[:12],
                                   'SRSL_ACTION': action[:15],
                                   'SRSL_STATUS': status[:12],
                                   'SRSL_MESSAGE': message[:1998],
                                   'SRSL_LOGREF': logref,  # NUMBER(10)
                                   # before SRSL_DATE was set to SYSDATE by Oracle column default value
                                   # PLEASE NOTE THAT THIS IS FAILING (see WO #58116) if query is slow and the
                                   # .. reservation got meanwhile changed again (before calling this method);
                                   # .. Therefore added the self._last_fetch timestamp explicitly to the SRSL record.
                                   'SRSL_DATE': self._last_fetch,
                                   })

    def _store_sihot_objid(self, table, pkey, objid, col_name_suffix=""):
        obj_id = objid if str(objid) else '-' + (pkey[2:] if table == 'CD' else str(pkey))
        id_col = table + "_SIHOT_OBJID" + col_name_suffix
        pk_col = table + "_CODE"
        return self.ora_db.update('T_' + table, {id_col: obj_id}, pk_col + " = :pk", bind_vars=dict(pk=str(pkey)))

    def fetch_all_from_acu(self, col_names):
        self._last_fetch = datetime.datetime.now()
        ret_rows = list()
        plain_rows = self.ora_db.fetch_all()
        for row in plain_rows:
            ret_rows.append(dict(zip(col_names, row)))
        self.cae.dprint("AcuDbRows.fetch_all_from_acu() at {} got {}, 1st row: {}"
                        .format(self._last_fetch, len(ret_rows), ret_rows), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        return ret_rows


class AcuClientToSihot(ClientToSihot):
    def __init__(self, cae):
        super(AcuClientToSihot, self).__init__(cae)
        self.acu_db = AcuDbRows(cae)
        self._col_names = init_col_names(CLI_FIELD_MAP, self.elem_fld_rec)
        self._col_expressions = init_col_expressions(CLI_FIELD_MAP, self._col_names)
        self.rows = ()

    def __del__(self):
        self.acu_db = None

    def _fetch_from_acu(self, view, acu_id=''):
        where_group_order = ''
        if acu_id:
            where_group_order += "CD_CODE " + ("like" if '_' in acu_id or '%' in acu_id else "=") + " '" + acu_id + "'"

        err_msg = self.acu_db.ora_db.select(view, self._col_expressions, where_group_order)
        if err_msg:
            self.rows = ()
        else:
            rows = self.acu_db.fetch_all_from_acu(self._col_names)
            for col_values in rows:
                for col, val in col_values.items():
                    if col in self.elem_fld_rec:
                        self.elem_fld_rec.set_val(val, col, system=SDI_AC, direction=FAD_FROM)
        return err_msg

    # use for sync only not for migration because we have clients w/o log entries
    def fetch_from_acu_by_acu(self, acu_id=''):
        return self._fetch_from_acu('V_ACU_CD_UNSYNCED', acu_id=acu_id)

    # use for migration
    def fetch_all_valid_from_acu(self):
        return self._fetch_from_acu('V_ACU_CD_FILTERED')

    # use for unfiltered client fetches
    def fetch_from_acu_by_cd(self, acu_id):
        return self._fetch_from_acu('V_ACU_CD_UNFILTERED', acu_id=acu_id)

    def _send_person_to_sihot(self, c_row, first_person=""):  # pass CD_CODE of first person for to send 2nd person
        err_msg = super()._send_person_to_sihot(remap_row_to_field_names(c_row), first_person=first_person)

        if not err_msg and self.response:
            err_msg = self.acu_db._store_sihot_objid('CD', first_person or c_row['CD_CODE'], self.response.objid,
                                                     col_name_suffix="2" if first_person else "")
        return err_msg

    def send_client_to_sihot(self, c_row=None):
        err_msg = super().send_client_to_sihot(rec=remap_row_to_field_names(c_row))

        action = self.action
        couple_linkage = ''  # flag for logging if second person got linked (+P2) or unlinked (-P2)
        if c_row.get('CD_CODE2') and not err_msg:  # check for second person
            crow2 = deepcopy(c_row)
            crow2['CD_CODE'] = c_row['CD_CODE2']
            crow2['CD_SIHOT_OBJID'] = c_row['CD_SIHOT_OBJID2']
            crow2['SIHOT_SALUTATION1'] = c_row['SIHOT_SALUTATION2']
            crow2['SIHOT_TITLE1'] = c_row['SIHOT_TITLE2']
            crow2['SIHOT_GUESTTYPE1'] = c_row['SIHOT_GUESTTYPE2']
            crow2['CD_SNAM1'] = c_row['CD_SNAM2']
            crow2['CD_FNAM1'] = c_row['CD_FNAM2']
            crow2['CD_DOB1'] = c_row['CD_DOB2']
            # crow2['CD_INDUSTRY1'] = c_row['CD_INDUSTRY2']
            err_msg = self._send_person_to_sihot(crow2, c_row['CD_CODE'])
            action += '/' + self.action
            couple_linkage = '+P2'

        log_err = self.acu_db._add_to_acumen_sync_log('CD', c_row['CD_CODE'],
                                                      action,
                                                      'ERR' + (self.response.server_error() if self.response else '')
                                                      if err_msg else 'SYNCED' + couple_linkage,
                                                      err_msg,
                                                      c_row.get('CDL_CODE', -966) or -969)
        if log_err:
            err_msg += "\n      LogErr=" + log_err

        if err_msg:
            self.cae.dprint("AcuClientToSihot.send_client_to_sihot() error: row={} action-p1/2={} err={}"
                            .format(c_row, action, err_msg))
        else:
            self.cae.dprint("AcuClientToSihot.send_client_to_sihot() with client={} RESPONDED OBJID={}/MATCHCODE={}"
                            .format(c_row['CD_CODE'], self.response.objid, self.response.matchcode),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg


class AcuResToSihot(ResToSihot):
    def __init__(self, cae):
        super(AcuResToSihot, self).__init__(cae)
        self.acu_db = AcuDbRows(cae)
        self._col_names = init_col_names(RES_FIELD_MAP, self.elem_fld_rec)
        self._col_expressions = init_col_expressions(RES_FIELD_MAP, self._col_names)
        self.rows = ()

    def __del__(self):
        self.acu_db = None

    def _fetch_from_acu(self, view, where_group_order, date_range, hints=''):
        if date_range == 'H':
            where_group_order += (" and " if where_group_order else "") + "ARR_DATE < trunc(sysdate)"
        elif date_range == 'M':
            where_group_order += (" and " if where_group_order else "") \
                                 + "DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31"
        elif date_range and date_range[0] == 'Y':     # temporary/interim solution for migration of BHH/HMC - plan B
            where_group_order += (" and (" if where_group_order else "") \
                + "DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31" \
                + " or RUL_SIHOT_HOTEL in (1, 4, 999) or RUL_SIHOT_LAST_HOTEL in (1, 4, 999)" \
                + (" or ROWNUM <= " + date_range[1:6] if date_range[1:] else "") \
                + (")" if where_group_order else "")
        elif date_range == 'P':
            where_group_order += (" and " if where_group_order else "") + "DEP_DATE >= trunc(sysdate)"
        elif date_range == 'F':
            where_group_order += (" and " if where_group_order else "") + "ARR_DATE >= trunc(sysdate)"

        err_msg = self.acu_db.ora_db.select(view, self._col_expressions, where_group_order, hints=hints)
        if err_msg:
            self.rows = ()
        else:
            self.rows = self.acu_db.fetch_all_from_acu(self._col_names)
            for col_values in self.rows:
                for col, val in col_values.items():
                    if col in self.elem_fld_rec:
                        self.elem_fld_rec.set_val(val, col, system=SDI_AC, direction=FAD_FROM)
        return err_msg

    def fetch_from_acu_by_aru(self, where_group_order='', date_range=''):
        return self._fetch_from_acu('V_ACU_RES_UNSYNCED', where_group_order, date_range, hints='/*+ NO_CPU_COSTING */')

    def fetch_from_acu_by_cd(self, acu_id, date_range=''):
        where_group_order = "CD_CODE " + ("like" if '_' in acu_id or '%' in acu_id else "=") + " '" + acu_id + "'"
        return self._fetch_from_acu('V_ACU_RES_UNFILTERED', where_group_order, date_range)

    def fetch_all_valid_from_acu(self, where_group_order='', date_range=''):
        return self._fetch_from_acu('V_ACU_RES_FILTERED', where_group_order, date_range)

    def _sending_res_to_sihot(self, crow):
        err_msg, warn_msg = super()._sending_res_to_sihot(remap_row_to_field_names(crow))

        if not err_msg and self.response:
            err_msg = self.acu_db._store_sihot_objid('RU', crow['RUL_PRIMARY'], self.response.objid)
        err_msg += self.acu_db._add_to_acumen_sync_log('RU', crow['RUL_PRIMARY'],
                                                       crow['RUL_ACTION'],
                                                       "ERR" + (self.response.server_error() if self.response else "")
                                                       if err_msg else "SYNCED",
                                                       err_msg + ("W" + warn_msg if warn_msg else ""),
                                                       crow['RUL_CODE'])
        return err_msg

    def _ensure_clients_exist_and_updated(self, fld_vals, ensure_client_mode):
        if ensure_client_mode == ECM_DO_NOT_SEND_CLIENT:
            return ""
        err_msg = ""
        if 'CD_CODE' in fld_vals and fld_vals['CD_CODE']:
            acu_client = AcuClientToSihot(self.cae)
            client_synced = bool(fld_vals['CD_SIHOT_OBJID'])
            if client_synced:
                err_msg = acu_client.fetch_from_acu_by_acu(fld_vals['CD_CODE'])
            else:
                err_msg = acu_client.fetch_from_acu_by_cd(fld_vals['CD_CODE'])
            if not err_msg:
                if acu_client.rows:
                    err_msg = acu_client.send_client_to_sihot()
                elif not client_synced:
                    err_msg = "AcuResToSihot._ensure_clients_exist_and_updated(): client {} not found"\
                        .format(fld_vals['CD_CODE'])
                if not err_msg:
                    err_msg = acu_client.fetch_from_acu_by_cd(fld_vals['CD_CODE'])  # re-fetch OBJIDs
                if not err_msg and not acu_client.rows:
                    err_msg = "AcuResToSihot._ensure_clients_exist_and_updated(): IntErr/client: " + fld_vals['CD_CODE']
                if not err_msg:
                    # transfer just created guest OBJIDs from guest to reservation record
                    fld_vals['OC_SIHOT_OBJID'] = fld_vals['CD_SIHOT_OBJID'] = acu_client.cols['CD_SIHOT_OBJID']
                    fld_vals['CD_SIHOT_OBJID2'] = acu_client.cols['CD_SIHOT_OBJID2']

        if not err_msg and 'OC_CODE' in fld_vals and fld_vals['OC_CODE'] \
                and len(fld_vals['OC_CODE']) == 7:  # exclude pseudo client like TCAG/TCRENT
            acu_client = AcuClientToSihot(self.cae)
            client_synced = bool(fld_vals['OC_SIHOT_OBJID'])
            if client_synced:
                err_msg = acu_client.fetch_from_acu_by_acu(fld_vals['OC_CODE'])
            else:
                err_msg = acu_client.fetch_from_acu_by_cd(fld_vals['OC_CODE'])
            if not err_msg:
                if acu_client.rows:
                    err_msg = acu_client.send_client_to_sihot()
                elif not client_synced:
                    err_msg = "AcuResToSihot._ensure_clients_exist_and_updated(): invalid orderer {}"\
                        .format(fld_vals['OC_CODE'])
                if not err_msg:
                    err_msg = acu_client.fetch_from_acu_by_cd(fld_vals['OC_CODE'])
                if not err_msg and not acu_client.rows:
                    err_msg = "AcuResToSihot._ensure_clients_exist_and_updated() error: orderer={} cols={} sync={}"\
                        .format(fld_vals['OC_CODE'], repr(getattr(acu_client, 'cols', "unDef")), client_synced)
                if not err_msg:
                    # transfer just created guest OBJIDs from guest to reservation record
                    fld_vals['OC_SIHOT_OBJID'] = acu_client.cols['CD_SIHOT_OBJID']

        return "" if ensure_client_mode == ECM_TRY_AND_IGNORE_ERRORS else err_msg

    def send_res_to_sihot(self, crow, ensure_client_mode=ECM_ENSURE_WITH_ERRORS):
        err_msg = super().send_res_to_sihot(rec=remap_row_to_field_names(crow),
                                            ensure_client_mode=ensure_client_mode)

        if "Could not find a key identifier" in err_msg and (crow['CD_SIHOT_OBJID'] or crow['CD_SIHOT_OBJID2']):
            self.cae.dprint("AcuResToSihot.send_res_to_sihot() ignoring CD_SIHOT_OBJID({}) error: {}"
                            .format(str(crow['CD_SIHOT_OBJID']) + "/" + str(crow['CD_SIHOT_OBJID2']), err_msg))
            crow['CD_SIHOT_OBJID'] = None  # use MATCHCODE instead
            crow['CD_SIHOT_OBJID2'] = None
            err_msg = self._sending_res_to_sihot(crow)

        if err_msg:
            self.cae.dprint("AcuResToSihot.send_res_to_sihot() error: {}".format(err_msg))
        else:
            self.cae.dprint("AcuResToSihot.send_res_to_sihot() RESPONDED OBJID={} MATCHCODE={}, crow={}"
                            .format(self.response.objid, self.response.matchcode, crow),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg

    def send_res_recs_to_sihot(self, break_on_error=True, commit_last_row=True):
        ret_msg = ""
        for fld_vals in self.recs:
            err_msg = self.send_res_to_sihot(fld_vals)
            if err_msg:
                if break_on_error:
                    return err_msg  # BREAK/RETURN first error message
                ret_msg += "\n" + err_msg

        if commit_last_row:
            if ret_msg:
                ret_msg += self.ora_db.rollback()
            else:
                ret_msg = self.ora_db.commit()

        return ret_msg


# only used by AcuSihotMonitor for testing purposes
class AcuServer(SihotXmlBuilder):
    def time_sync(self):
        self.beg_xml(operation_code='TS')
        self.add_tag('CDT', datetime.datetime.now().strftime('%y-%m-%d'))
        self.end_xml()

        err_msg = self.send_to_server()
        if err_msg:
            ret = err_msg
        else:
            ret = '' if self.response.rc == '0' else 'Time Sync Error code ' + self.response.rc

        return ret

    def link_alive(self, level='0'):
        self.beg_xml(operation_code='TS')
        self.add_tag('CDT', datetime.datetime.now().strftime('%y-%m-%d'))
        self.add_tag('STATUS', level)  # 0==request, 1==link OK
        self.end_xml()

        err_msg = self.send_to_server()
        if err_msg:
            ret = err_msg
        else:
            ret = '' if self.response.rc == '0' else 'Link Alive Error code ' + self.response.rc

        return ret
