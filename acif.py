"""
Acumen interface constants and helpers
"""
import datetime
from copy import deepcopy

from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE
from ae_db import OraDB
from sxmlif import (SihotXmlBuilder, ClientToSihot, ResToSihot, convert2date,
                    EXT_REF_COUNT, RES_MAX_ADULTS, RES_MAX_CHILDREN,
                    ECM_TRY_AND_IGNORE_ERRORS, ECM_ENSURE_WITH_ERRORS, ECM_DO_NOT_SEND_CLIENT)
from sys_data_ids import SDI_AC


ACU_DEF_USR = 'SIHOT_INTERFACE'
ACU_DEF_DSN = 'SP.TEST'

# second couple Acumen ID suffix
AC_ID_2ND_COUPLE_SUFFIX = 'P2'

# Acumen field name [0] mapping to view column name [1], SQL expression [2] and data value filter [3]
FIELD_MAP = [
    # client data
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
    ('MobilePhone2', 'CD_LAST_SMS_TEL'),
    ('Fax', 'CD_FAX'),
    ('Email', 'CD_EMAIL'),
    ('Email2', 'CD_SIGNUP_EMAIL'),
    ('DOB', 'CD_DOB1',
     convert2date  # 'valToAcuConverter':
     ),
    ('Password', 'CD_PASSWORD'),
    ('RCIRef', 'CD_RCI_REF'),
    ('ExtRefs', 'EXT_REFS'),
    # reservation data
    ('ResHotelId', 'RUL_SIHOT_HOTEL'),
    ('ResNumber', ''),
    ('ResSubNumber', ''),
    ('ResGdsNo', 'SIHOT_GDSNO',
     "nvl(SIHOT_GDSNO, case when RUL_SIHOT_RATE in ('TC', 'TK') then case when RUL_ACTION <> 'UPDATE'"
     " then (select 'TC' || RH_EXT_BOOK_REF from T_RH"
     " where RH_CODE = F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_RHREF'))"
     " else '(lost)' end else to_char(RUL_PRIMARY) end)"),  # RUL_PRIMARY needed for to delete/cancel res
    ('ResObjectId', ''),
    ('ResArrival', 'ARR_DATE',
     "case when ARR_DATE is not NULL then ARR_DATE when RUL_ACTION <> 'UPDATE'"
     " then to_date(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_FROM_DATE'), 'DD-MM-YY')"
     " end"),
    ('ResDeparture', 'DEP_DATE',
     "case when DEP_DATE is not NULL then DEP_DATE when RUL_ACTION <> 'UPDATE'"
     " then to_date(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_FROM_DATE'), 'DD-MM-YY')"
     " + to_number(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_DAYS'))"
     " end"),
    ('ResRoomCat', 'RUL_SIHOT_CAT',
     "F_SIHOT_CAT('RU' || RUL_PRIMARY)"),
    # "case when RUL_SIHOT_RATE in ('TC', 'TK') then F_SIHOT_CAT('RU' || RU_CODE) else RUL_SIHOT_CAT end"},
    ('ResPriceCat', 'SH_PRICE_CAT',
     "F_SIHOT_CAT('RU' || RUL_PRIMARY)"),
    ('ResRoomNo', 'RUL_SIHOT_ROOM'),
    ('ResOrdererMc', 'OC_CODE',
     "nvl(OC_CODE, CD_CODE)"),
    ('ResOrdererId', 'OC_SIHOT_OBJID',
     "to_char(nvl(OC_SIHOT_OBJID, CD_SIHOT_OBJID))",
     lambda f: not f.csv('ResOrdererId') and not f.csv('ShId')),
    ('ResStatus', 'SH_RES_TYPE',
     "case when RUL_ACTION = 'DELETE' then 'S' else nvl(SIHOT_RES_TYPE, 'S') end"),
    ('ResAction', 'RUL_ACTION'),
    ('ResVoucherNo', 'RH_EXT_BOOK_REF'),
    ('ResBooked', 'RH_EXT_BOOK_DATE'),
    ('ResBoard', 'RUL_SIHOT_PACK'),
    ('ResSource', 'RU_SOURCE'),
    ('ResMktGroup', 'RO_SIHOT_RES_GROUP'),      # Acumen value in RO_RES_GROUP
    ('ResMktGroup2', 'RO_SIHOT_SP_GROUP'),
    ('ResMktSegment', 'SIHOT_MKT_SEG',
     "nvl(SIHOT_MKT_SEG, RUL_SIHOT_RATE)"),     # SIHOT_MKT_SEG is NULL if RU is deleted
    ('ResRateSegment', 'SIHOT_RATE_SEGMENT'),
    ('ResNote', 'SIHOT_NOTE'),
    ('ResLongNote', 'SIHOT_TEC_NOTE'),
    ('ResFlightNo', 'SH_EXT_REF',
     "trim(RU_FLIGHT_NO || ' ' || RU_FLIGHT_PICKUP || ' ' || RU_FLIGHT_AIRPORT)"),
    ('ResFlightETA', 'RU_FLIGHT_LANDS'),
    ('ResAccount', 'SIHOT_PAYMENT_INST'),
    ('ResAllotmentNo', 'SIHOT_ALLOTMENT_NO'),
    ('ResAdults', 'RU_ADULTS'),
    ('ResChildren', 'RU_CHILDREN'),
    ('ResGroupNo', 'SIHOT_LINK_GROUP'),
    # only one room per reservation, so not needed: ('ResRooms', 'SH_ROOMS'),
    ]
for idx in range(1, EXT_REF_COUNT + 1):
    FIELD_MAP.append(('ExtRefType' + str(idx), 'EXT_REF_TYPE' + str(idx),
                      "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, " + str(idx) + "), '[^=]+', 1, 1)"))
    FIELD_MAP.append(('ExtRefId' + str(idx), 'EXT_REF_ID' + str(idx),
                      "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, " + str(idx) + "), '[^=]+', 1, 2)"))
for idx in range(1, RES_MAX_ADULTS + 1):
    FIELD_MAP.append(('ResAdult' + str(idx) + 'Surname', 'SH_ADULT' + str(idx) + '_NAME'))      # ResAdult1Surname
    FIELD_MAP.append(('ResAdult' + str(idx) + 'Forename', 'SH_ADULT' + str(idx) + '_NAME2'))    # ResAdult1Forename
    FIELD_MAP.append(('ResAdult' + str(idx) + 'DOB', 'SH_ADULT' + str(idx) + '_DOB'))           # ResAdult1DOB
for idx in range(1, RES_MAX_CHILDREN + 1):
    FIELD_MAP.append(('ResChild' + str(idx) + 'Surname', 'SH_CHILD' + str(idx) + '_NAME'))      # ResChild1Surname
    FIELD_MAP.append(('ResChild' + str(idx) + 'Forename', 'SH_CHILD' + str(idx) + '_NAME2'))    # ResChild1Forename
    FIELD_MAP.append(('ResChild' + str(idx) + 'PaxSeq', 'SH_CHILD' + str(idx) + '_DOB'))        # ResChild1DOB


def add_ac_options(cae):
    cae.add_option('acuUser', "Acumen/Oracle user account name", ACU_DEF_USR, 'u')
    cae.add_option('acuPassword', "Acumen/Oracle user account password", '', 'p')
    cae.add_option('acuDSN', "Acumen/Oracle data source name", ACU_DEF_DSN, 'd')


class AcuDbRow:
    def __init__(self, cae):
        self.cae = cae
        self.ora_db = OraDB(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'),
                            app_name=cae.app_name(), debug_level=cae.get_option('debugLevel'))
        err_msg = self.ora_db.connect()
        if err_msg:
            uprint("AcuDbRow.__init__() db connect error: {}".format(err_msg))

        # added for to store fetch_from_acu timestamp
        self._last_fetch = None

        self._rows = None

    def __del__(self):
        if self.ora_db:
            self.ora_db.close()

    def _add_to_acumen_sync_log(self, table, primary, action, status, message, logref):
        self.cae.dprint('AcuDbRow._add_to_acumen_sync_log() time/now:', self._last_fetch, datetime.datetime.now(),
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


class AcuXmlBuilder(AcuDbRow):
    def __init__(self, cae, elem_col_map=None, use_kernel=None):
        super(AcuXmlBuilder, self).__init__(cae)
        self.cae = cae
        elem_col_map = deepcopy(elem_col_map or cae.get_option('mapRes'))
        self.elem_col_map = elem_col_map
        self.use_kernel_interface = cae.get_option('useKernelForRes') if use_kernel is None else use_kernel

        self.sihot_elem_col = [(c['elemName'],
                                c['colName'] if 'colName' in c else None,
                                ((' or a in "' + c['elemHideInActions'] + '"' if 'elemHideInActions' in c else '')
                                 + (' or ' + c['elemHideIf'] if 'elemHideIf' in c else ''))[4:],
                                c['colVal'] if 'colVal' in c else None)
                               for c in elem_col_map if not c.get('buildExclude', False)]
        # self.fix_fld_values = {c['colName']: c['colVal'] for c in elem_col_map if 'colName' in c and 'colVal' in c}
        # acu_col_names and acu_col_expres need to be in sync
        # self.acu_col_names = [c['colName'] for c in elem_col_map if 'colName' in c and 'colVal' not in c]
        # self.acu_col_expres = [c['colValFromAcu'] + " as " + c['colName'] if 'colValFromAcu' in c else c['colName']
        #                       for c in elem_col_map if 'colName' in c and 'colVal' not in c]
        # alternative version preventing duplicate column names
        self.fix_fld_values = dict()
        self.acu_col_names = list()  # acu_col_names and acu_col_expres need to be in sync
        self.acu_col_expres = list()
        for c in elem_col_map:
            if 'colName' in c:
                if 'colVal' in c:
                    self.fix_fld_values[c['colName']] = c['colVal']
                elif c['colName'] not in self.acu_col_names:
                    self.acu_col_names.append(c['colName'])
                    self.acu_col_expres.append(c['colValFromAcu'] + " as " + c['colName'] if 'colValFromAcu' in c
                                               else c['colName'])
        # mapping dicts between db column names and xml element names (not works for dup elems like MATCHCODE in RES)
        self.col_elem = {c['colName']: c['elemName'] for c in elem_col_map if 'colName' in c and 'elemName' in c}
        self.elem_col = {c['elemName']: c['colName'] for c in elem_col_map if 'colName' in c and 'elemName' in c}

        self.response = None

        self._rows = list()  # list of dicts, used by inheriting class for to store the records to send to SiHOT.PMS
        self._current_row_i = 0

        self._xml = ''
        self._indent = 0

    # --- recs/fields helpers

    @property
    def cols(self):
        return self._rows[self._current_row_i] if len(self._rows) > self._current_row_i else dict()

    # def next_row(self): self._current_row_i += 1

    @property
    def row_count(self):
        return len(self._rows)

    @property
    def rows(self):
        return self._rows

    def fetch_all_from_acu(self):
        self._last_fetch = datetime.datetime.now()
        self._rows = list()
        plain_rows = self.ora_db.fetch_all()
        for r in plain_rows:
            col_values = self.fix_fld_values.copy()
            col_values.update(zip(self.acu_col_names, r))
            self._rows.append(col_values)
        self.cae.dprint("AcuDbRow.fetch_all_from_acu() at {} got {}, 1st row: {}"
                        .format(self._last_fetch, self.row_count, self.cols), minimum_debug_level=DEBUG_LEVEL_VERBOSE)


class AcuClientToSihot(ClientToSihot, AcuXmlBuilder):
    def __init__(self, cae):
        super(AcuClientToSihot, self).__init__(cae)
        self._rows = None

    def _fetch_from_acu(self, view, acu_id=''):
        where_group_order = ''
        if acu_id:
            where_group_order += "CD_CODE " + ("like" if '_' in acu_id or '%' in acu_id else "=") + " '" + acu_id + "'"

        err_msg = self.ora_db.select(view, self.acu_col_expres, where_group_order)
        if not err_msg:
            self.fetch_all_from_acu()
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
        err_msg, action = super(AcuClientToSihot, self)._send_person_to_sihot(c_row, first_person=first_person)

        if not err_msg and self.response:
            err_msg = self._store_sihot_objid('CD', first_person or c_row['CD_CODE'], self.response.objid,
                                              col_name_suffix="2" if first_person else "")
        return err_msg, action

    def send_client_to_sihot(self, c_row=None, commit=False):
        err_msg, action_p1 = super(AcuClientToSihot, self).send_client_to_sihot(c_row=c_row, commit=commit)

        couple_linkage = ''  # flag for logging if second person got linked (+P2) or unlinked (-P2)
        action_p2 = ''
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
            err_msg, action_p2 = self._send_person_to_sihot(crow2, c_row['CD_CODE'])
            couple_linkage = '+P2'

        action = action_p1 + ('/' + action_p2 if action_p2 else '')
        log_err = self._add_to_acumen_sync_log('CD', c_row['CD_CODE'],
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


class AcuResToSihot(ResToSihot, AcuXmlBuilder):
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
        err_msg = self.ora_db.select(view, self.acu_col_expres, where_group_order, hints=hints)
        if not err_msg:
            self.fetch_all_from_acu()
        return err_msg

    def fetch_from_acu_by_aru(self, where_group_order='', date_range=''):
        return self._fetch_from_acu('V_ACU_RES_UNSYNCED', where_group_order, date_range, hints='/*+ NO_CPU_COSTING */')

    def fetch_from_acu_by_cd(self, acu_id, date_range=''):
        where_group_order = "CD_CODE " + ("like" if '_' in acu_id or '%' in acu_id else "=") + " '" + acu_id + "'"
        return self._fetch_from_acu('V_ACU_RES_UNFILTERED', where_group_order, date_range)

    def fetch_all_valid_from_acu(self, where_group_order='', date_range=''):
        return self._fetch_from_acu('V_ACU_RES_FILTERED', where_group_order, date_range)

    def _send_res_to_sihot(self, crow):
        err_msg, warn_msg = super(AcuResToSihot, self)._send_res_to_sihot(crow)

        if not err_msg and self.response:
            err_msg = self._store_sihot_objid('RU', crow['RUL_PRIMARY'], self.response.objid)
        err_msg += self._add_to_acumen_sync_log('RU', crow['RUL_PRIMARY'],
                                                crow['RUL_ACTION'],
                                                "ERR" + (self.response.server_error() if self.response else "")
                                                if err_msg else "SYNCED",
                                                err_msg + ("W" + warn_msg if warn_msg else ""),
                                                crow['RUL_CODE'])
        return err_msg

    def _ensure_clients_exist_and_updated(self, crow, ensure_client_mode):
        if ensure_client_mode == ECM_DO_NOT_SEND_CLIENT:
            return ""
        err_msg = ""
        if 'CD_CODE' in crow and crow['CD_CODE']:
            acu_client = AcuClientToSihot(self.cae)
            client_synced = bool(crow['CD_SIHOT_OBJID'])
            if client_synced:
                err_msg = acu_client.fetch_from_acu_by_acu(crow['CD_CODE'])
            else:
                err_msg = acu_client.fetch_from_acu_by_cd(crow['CD_CODE'])
            if not err_msg:
                if acu_client.row_count:
                    err_msg = acu_client.send_client_to_sihot()
                elif not client_synced:
                    err_msg = "AcuResToSihot._ensure_clients_exist_and_updated(): client {} not found"\
                        .format(crow['CD_CODE'])
                if not err_msg:
                    err_msg = acu_client.fetch_from_acu_by_cd(crow['CD_CODE'])  # re-fetch OBJIDs
                if not err_msg and not acu_client.row_count:
                    err_msg = "AcuResToSihot._ensure_clients_exist_and_updated(): IntErr/client: " + crow['CD_CODE']
                if not err_msg:
                    # transfer just created guest OBJIDs from guest to reservation record
                    crow['OC_SIHOT_OBJID'] = crow['CD_SIHOT_OBJID'] = acu_client.cols['CD_SIHOT_OBJID']
                    crow['CD_SIHOT_OBJID2'] = acu_client.cols['CD_SIHOT_OBJID2']

        if not err_msg and 'OC_CODE' in crow and crow['OC_CODE'] \
                and len(crow['OC_CODE']) == 7:  # exclude pseudo client like TCAG/TCRENT
            acu_client = AcuClientToSihot(self.cae)
            client_synced = bool(crow['OC_SIHOT_OBJID'])
            if client_synced:
                err_msg = acu_client.fetch_from_acu_by_acu(crow['OC_CODE'])
            else:
                err_msg = acu_client.fetch_from_acu_by_cd(crow['OC_CODE'])
            if not err_msg:
                if acu_client.row_count:
                    err_msg = acu_client.send_client_to_sihot()
                elif not client_synced:
                    err_msg = "AcuResToSihot._ensure_clients_exist_and_updated(): invalid orderer {}"\
                        .format(crow['OC_CODE'])
                if not err_msg:
                    err_msg = acu_client.fetch_from_acu_by_cd(crow['OC_CODE'])
                if not err_msg and not acu_client.row_count:
                    err_msg = "AcuResToSihot._ensure_clients_exist_and_updated() error: orderer={} cols={} sync={}"\
                        .format(crow['OC_CODE'], repr(getattr(acu_client, 'cols', "unDef")), client_synced)
                if not err_msg:
                    # transfer just created guest OBJIDs from guest to reservation record
                    crow['OC_SIHOT_OBJID'] = acu_client.cols['CD_SIHOT_OBJID']

        return "" if ensure_client_mode == ECM_TRY_AND_IGNORE_ERRORS else err_msg

    def send_row_to_sihot(self, crow=None, ensure_client_mode=ECM_ENSURE_WITH_ERRORS):
        err_msg = super(AcuResToSihot, self).send_row_to_sihot(crow=crow, ensure_client_mode=ensure_client_mode)

        if "Could not find a key identifier" in err_msg and (crow['CD_SIHOT_OBJID'] or crow['CD_SIHOT_OBJID2']):
            self.cae.dprint("AcuResToSihot.send_row_to_sihot() ignoring CD_SIHOT_OBJID({}) error: {}"
                            .format(str(crow['CD_SIHOT_OBJID']) + "/" + str(crow['CD_SIHOT_OBJID2']), err_msg))
            crow['CD_SIHOT_OBJID'] = None  # use MATCHCODE instead
            crow['CD_SIHOT_OBJID2'] = None
            err_msg = self._send_res_to_sihot(crow)

        if err_msg:
            self.cae.dprint("AcuResToSihot.send_row_to_sihot() error: {}".format(err_msg))
        else:
            self.cae.dprint("AcuResToSihot.send_row_to_sihot() RESPONDED OBJID={} MATCHCODE={}, crow={}"
                            .format(self.response.objid, self.response.matchcode, crow),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg

    def send_rows_to_sihot(self, break_on_error=True, commit_last_row=True):
        ret_msg = super(AcuResToSihot, self).send_rows_to_sihot(break_on_error=break_on_error)
        if commit_last_row:
            if ret_msg:
                ret_msg += self.ora_db.rollback()
            else:
                ret_msg = self.ora_db.commit()
        return ret_msg


# currently still/only used by AcuSihotMonitor for testing purposes - can be deleted
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
