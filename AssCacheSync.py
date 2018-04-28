"""
    AssCacheSync is a tool for to initialize, check, migrate and sync data between Acumen, Sihot, Salesforce
    and the ass_cache PostGreSQL database.

    0.1     first beta.
"""
import datetime
import pprint
from collections import OrderedDict

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from ae_db import PostgresDB
from sxmlif import ResToSihot, AC_ID_2ND_COUPLE_SUFFIX
from shif import ResBulkFetcher, elem_value, pax_count, gds_no, apt_wk_yr, elem_path_join, guest_data, SH_DATE_FORMAT
from sfif import add_sf_options, prepare_connection, correct_email, correct_phone, obj_from_id, ensure_long_id, \
    EXT_REF_TYPE_ID_SEP, EXT_REF_TYPE_RCI
from ass_sys_data import AssSysData, EXT_REFS_SEP, AC_SQL_EXT_REF_TYPE
from ae_notification import add_notification_options, init_notification

__version__ = '0.1'

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)

cae = ConsoleApp(__version__, "Initialize, sync and/or verify AssCache from/against Acumen, Sihot and Salesforce")

cae.add_option('initializeCache', "Initialize/Wipe/Recreate ass_cache database (0=No, 1=Yes)", 0, 'I')
sync_veri_choices = ('acC', 'acP', 'acR', 'shC', 'shR', 'sfC', 'sfP', 'sfR')
cae.add_option('syncCache', "Synchronize from (ac=Acumen, sh=Sihot, sf=Salesforce) including (C=Clients, P=Products, "
                            "R=Reservations), e.g. shC is synchronizing clients from Sihot",
               [], 'S', choices=sync_veri_choices, multiple=True)
cae.add_option('verifyCache', "Verify/Check against (ac=Acumen, sh=Sihot, sf=Salesforce) including (C=Clients, "
                              "P=Products, R=Reservations), e.g. acR is checking reservations against Acumen",
               [], 'V', choices=sync_veri_choices, multiple=True)
cae.add_option('pushFix', "Update system (ac=Acumen, sh=Sihot, sf=Salesforce) including (C=Clients, "
                          "P=Products, R=Reservations), e.g. acC is pushing/fixing client data within Acumen",
               [], 'X', choices=sync_veri_choices, multiple=True)

cae.add_option('filterRecords', "Filter to restrict processed (dict keys: C=client, P=product, R=reservation) records,"
                                " e.g. {'C':\\\"cl_ac_id='E123456'\\\"} processes only the client with Acu ID E123456",
               {}, 'W')
cae.add_option('filterFields', "Filter to restrict processed (dict keys: C=client, P=product, R=reservation) fields,"
                               " e.g. {'C':['Phone']} processes only the client field Phone",
               {}, 'Y')

cae.add_option('pgUser', "User account name for the postgres cache database", '', 'U')
cae.add_option('pgPassword', "User account password for the postgres cache database", '', 'P')
cae.add_option('pgDSN', "Database (and optional host) name of cache database (dbName[@host])", 'ass_cache', 'N')

cae.add_option('acuUser', "User name of Acumen/Oracle system", '', 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", '', 'd')

add_sf_options(cae)

sh_rbf = ResBulkFetcher(cae)
sh_rbf.add_options()
# .. and for GuestBulkFetcher we need also the kernel interface port of Sihot
cae.add_option('shServerKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')

add_notification_options(cae)


_debug_level = cae.get_option('debugLevel')

systems = dict(ac='Acumen', sh='Sihot', sf='Salesforce')
types = dict(C='Clients', P='Products', R='Reservations')
acm_init = cae.get_option('initializeCache')
acm_syncs = cae.get_option('syncCache')
acm_veris = cae.get_option('verifyCache')
acm_fixes = cae.get_option('pushFix')
actions = list()
if acm_init:
    actions.append("Initialize")
for acm_sync in acm_syncs:
    actions.append("Synchronize/Migrate " + types[acm_sync[2:]] + " from " + systems[acm_sync[:2]])
for acm_veri in acm_veris:
    actions.append("Verify/Check " + types[acm_veri[2:]] + " against " + systems[acm_veri[:2]])
for acm_fix in acm_fixes:
    actions.append("Push/Fix " + types[acm_fix[2:]] + " within " + systems[acm_fix[:2]])
if not actions:
    uprint("\nNo Action option specified (using command line options initializeCache, syncCache and/or verifyCache)\n")
    cae.show_help()
    cae.shutdown()
uprint("Actions: " + '\n         '.join(actions))
acm_record_filters = cae.get_option('filterRecords')
if acm_record_filters:
    if not isinstance(acm_record_filters, dict):
        acm_record_filters = {k: acm_record_filters for (k, v) in types.items()}
    uprint("Data record filtering:", acm_record_filters)
acm_field_filters = cae.get_option('filterFields')
if acm_field_filters:
    if not isinstance(acm_field_filters, dict):
        acm_field_filters = {k: acm_field_filters for (k, v) in types.items()}
    uprint("Data field filtering:", acm_field_filters)

x = sh_rbf.load_config()
sh_rbf.print_config()
uprint("Sihot Kernel-port:", cae.get_option('shServerKernelPort'))

acu_user = cae.get_option('acuUser')
acu_password = cae.get_option('acuPassword')
acu_dsn = cae.get_option('acuDSN')
uprint("Acumen user/DSN:", acu_user, acu_dsn)

pg_user = cae.get_option('pgUser')
pg_pw = cae.get_option('pgPassword')
pg_dsn = cae.get_option('pgDSN')
uprint("AssCache user/dsn:", pg_user, pg_dsn)


# LOGGING AND NOTIFICATION HELPERS
error_log = list()
warn_log = list()


def send_notification(exit_code=0):
    if notification:
        subject = "AssCacheSync Protocol"
        mail_body = "\n\n".join(warn_log)
        send_err = notification.send_notification(mail_body, subject=subject)
        if send_err:
            uprint("****  {} send error: {}. mail-body='{}'.".format(subject, send_err, mail_body))
            if not exit_code:
                exit_code = 36
        if warning_notification_emails and error_log:
            mail_body = "ERRORS:\n\n" + ("\n\n".join(error_log) if error_log else "NONE") \
                + "\n\nPROTOCOL:\n\n" + ("\n\n".join(warn_log) if warn_log else "NONE")
            subject = "AssCacheSync Errors"
            send_err = notification.send_notification(mail_body, subject=subject, mail_to=warning_notification_emails)
            if send_err:
                uprint("****  {} warning send error: {}. mail-body='{}'.".format(subject, send_err, mail_body))
                if not exit_code:
                    exit_code = 39
    return exit_code


def log_error(msg, ctx, importance=2, exit_code=0, dbs=None):
    msg = " " * (4 - importance) + "*" * importance + "  " + ctx + "   " + msg
    error_log.append(msg)
    warn_log.append(msg)
    uprint(msg)
    for db in dbs or list():
        if db:
            db.close()
    if exit_code:
        cae.shutdown(send_notification(exit_code))


def log_warning(msg, ctx, importance=2):
    seps = '\n' * (importance - 2)
    msg = seps + " " * (4 - importance) + "#" * importance + "  " + ctx + "   " + msg
    warn_log.append(msg)
    uprint(msg)


# logon to and prepare AssCache and config data env, optional also connect to Acumen, Salesforce, Sihot
conf_data = AssSysData(cae, err_logger=log_error, warn_logger=log_warning)
if conf_data.error_message:
    log_error(conf_data.error_message, 'AssSysDataInit', importance=4, exit_code=9)

# logon to and prepare ass_cache database and optional to Acumen database
ass_db = conf_data.ass_db
if not ass_db:
    log_error("Connecting to AssCache database failed", 'AssUserLogOn', importance=4, exit_code=12, dbs=[ass_db])
acu_db = conf_data.acu_db
if not acu_db and [_ for _ in acm_syncs + acm_veris + acm_fixes if _[:2] == 'ac']:
    log_error("Connecting to Acumen database failed", 'AcuUserLogOn', importance=4, exit_code=15, dbs=[ass_db, acu_db])

sf_conn, sf_sandbox = prepare_connection(cae)
if not sf_conn and [_ for _ in acm_syncs + acm_veris + acm_fixes if _[:2] == 'sf']:
    uprint("Salesforce account connection could not be established - please check your account data and credentials")
    cae.shutdown(20)

notification, warning_notification_emails \
    = init_notification(cae, "{}/{}/{}".format(acu_dsn, cae.get_option('shServerIP'), "SBox" if sf_sandbox else "Prod"))


# check for to (re-)create and initialize PG database
if acm_init:
    pg_dbname, pg_host = pg_dsn.split('@') if '@' in pg_dsn else (pg_dsn, '')
    pg_root_dsn = 'postgres' + ('@' + pg_host if '@' in pg_dsn else '')
    log_warning("creating data base {} and user {}".format(pg_dsn, pg_user), 'initializeCache-createDBandUser')
    pg_db = PostgresDB(usr=cae.get_config('pgRootUsr'), pwd=cae.get_config('pgRootPwd'), dsn=pg_root_dsn,
                       debug_level=_debug_level)
    if pg_db.execute_sql("CREATE DATABASE " + pg_dbname + ";", auto_commit=True):  # " LC_COLLATE 'C'"):
        log_error(pg_db.last_err_msg, 'initializeCache-createDB', exit_code=72)

    if pg_db.select('pg_user', ['count(*)'], "usename = :pg_user", dict(pg_user=pg_user)):
        log_error(pg_db.last_err_msg, 'initializeCache-checkUser', exit_code=81)
    if not pg_db.fetch_value():
        if pg_db.execute_sql("CREATE USER " + pg_user + " WITH PASSWORD '" + pg_pw + "';", commit=True):
            log_error(pg_db.last_err_msg, 'initializeCache-createUser', exit_code=84)
        if pg_db.execute_sql("GRANT ALL PRIVILEGES ON DATABASE " + pg_dbname + " to " + pg_user + ";", commit=True):
            log_error(pg_db.last_err_msg, 'initializeCache-grantUserConnect', exit_code=87)
    pg_db.close()

    log_warning("creating tables and audit trigger schema/extension", 'initializeCache-createTableAndAudit')
    pg_db = PostgresDB(usr=cae.get_config('pgRootUsr'), pwd=cae.get_config('pgRootPwd'), dsn=pg_dsn,
                       debug_level=_debug_level)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO "
                         + pg_user + ";"):
        log_error(pg_db.last_err_msg, 'initializeCache-grantUserTables', exit_code=90)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO " + pg_user + ";"):
        log_error(pg_db.last_err_msg, 'initializeCache-grantUserTables', exit_code=93)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO " + pg_user + ";"):
        log_error(pg_db.last_err_msg, 'initializeCache-grantUserFunctions', exit_code=96)
    if pg_db.execute_sql(open("sql/dba_create_audit.sql", "r").read(), commit=True):
        log_error(pg_db.last_err_msg, 'initializeCache-createAudit', exit_code=99)
    if pg_db.execute_sql(open("sql/dba_create_ass_tables.sql", "r").read(), commit=True):
        log_error(pg_db.last_err_msg, 'initializeCache-ctScript', exit_code=102)
    pg_db.close()


# column expression SQL for to fetch client data from Acumen
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


def ac_migrate_clients():
    """ migrate clients from Acumen into ass_cache/postgres """

    # fetch all couple-clients from Acumen
    log_warning("Fetching couple client data from Acumen (needs some minutes)", 'FetchAcuCoupleClients', importance=3)
    ac_cos = conf_data.load_view(acu_db, 'T_CD',
                                 [AC_SQL_AC_ID1, AC_SQL_SF_ID1, AC_SQL_SH_ID1, AC_SQL_NAME1, AC_SQL_EMAIL1,
                                  AC_SQL_PHONE1, AC_SQL_MAIN_RCI],
                                 "substr(CD_CODE, 1, 1) <> 'A' and (CD_SNAM1 is not NULL or CD_FNAM1 is not NULL)")
    if ac_cos is None:
        return conf_data.error_message
    ac_2 = conf_data.load_view(acu_db, 'T_CD',
                               [AC_SQL_AC_ID2, AC_SQL_SF_ID2, AC_SQL_SH_ID2, AC_SQL_NAME2, AC_SQL_EMAIL2,
                                "NULL", "NULL"],
                               "substr(CD_CODE, 1, 1) <> 'A' and (CD_SNAM2 is not NULL or CD_FNAM2 is not NULL)")
    if ac_2 is None:
        return conf_data.error_message
    ac_cos += ac_2
    ac_cos.sort(key=lambda _: _[0])

    # migrate to ass_cache including additional external refs/IDs (fetched from Acumen)
    for idx, ac_co in enumerate(ac_cos):
        ext_refs = [(EXT_REF_TYPE_RCI, ac_co[6])] if ac_co[6] else None
        cl_pk = conf_data.cl_save(ac_co[0], ac_co[1], ac_co[2], ac_co[3], ac_co[4], ac_co[5], ext_refs=ext_refs)
        if cl_pk is None:
            break
        if (idx + 1) % 1000 == 0:
            ass_db.commit()

    if ass_db.last_err_msg:
        ass_db.rollback()
        return ass_db.last_err_msg
    elif conf_data.error_message:
        ass_db.rollback()
        return conf_data.error_message

    return ass_db.commit()


def ac_migrate_products():
    log_warning("Acumen product types synchronization/migration", 'syncCacheAcuProductTypes', importance=3)
    pts = conf_data.load_view(acu_db, 'T_RS', ['RS_CODE', 'RS_SIHOT_GUEST_TYPE', 'RS_NAME'],
                              "RS_CLASS = 'CONSTRUCT' or RS_SIHOT_GUEST_TYPE is not NULL")
    if pts is None:
        return conf_data.error_message
    for pt in pts:
        if ass_db.upsert('product_types', OrderedDict([('pt_pk', pt[0]), ('pt_group', pt[1]), ('pt_name', pt[2])])):
            ass_db.rollback()
            return ass_db.last_err_msg

    if ass_db.upsert('product_types', OrderedDict([('pt_pk', 'HMF'), ('pt_group', 'I'), ('pt_name', "HMC Fraction")])):
        ass_db.rollback()
        return ass_db.last_err_msg

    prs = conf_data.load_view(acu_db, 'T_WK INNER JOIN T_AP ON WK_APREF = AP_CODE INNER JOIN T_AT ON AP_ATREF = AT_CODE'
                                      ' INNER JOIN T_RS ON AT_RSREF = RS_CODE',
                              ['WK_CODE', 'AT_RSREF'], "RS_SIHOT_GUEST_TYPE is not NULL")
    for pr in prs:
        if ass_db.upsert('products', OrderedDict([('pr_pk', pr[0]), ('pr_pt_fk', pr[1])])):
            break

    cps = conf_data.load_view(acu_db, 'V_OWNED_WEEKS INNER JOIN T_RS ON AT_RSREF = RS_CODE',
                              ['DW_WKREF', 'AT_RSREF', 'DW_OWREF'],
                              "substr(DW_OWREF, 1, 1) <> 'A' and RS_SIHOT_GUEST_TYPE is not NULL")
    if cps is None:
        return conf_data.error_message
    for cp in cps:
        cl_pk = conf_data.cl_ass_id_by_ac_id(cp[2])
        if cl_pk is None:
            break
        col_values = dict(cp_cl_fk=cl_pk, cp_pr_fk=cp[0])
        if ass_db.upsert('client_products', col_values, chk_values=col_values):
            break

    if ass_db.last_err_msg:
        ass_db.rollback()
        return ass_db.last_err_msg
    ass_db.commit()
    return ""


def ac_migrate_res_inv():
    log_warning("Fetching reservation inventory from Acumen (needs some minutes)", 'FetchAcuResInv', importance=3)
    invs = conf_data.load_view(acu_db, 'T_AOWN_VIEW INNER JOIN T_WK ON AOWN_WKREF = WK_CODE'
                                       ' LEFT OUTER JOIN V_OWNED_WEEKS ON AOWN_WKREF = DW_WKREF',
                               ["case when AOWN_RSREF = 'PBC' and length(AOWN_APREF) = 3 then '0' end || AOWN_WKREF",
                                "(select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTEL' and LU_ID = AOWN_RSREF)",
                                'AOWN_YEAR', 'AOWN_ROREF', 'AOWN_SWAPPED_WITH', 'AOWN_GRANTED_TO',
                                'nvl(POINTS, WK_POINTS)'],
                               "AOWN_YEAR >= to_char(sysdate, 'YYYY') and AOWN_RSREF in ('BHC', 'BHH', 'HMC', 'PBC')")
    if invs is None:
        return conf_data.error_message
    for inv in invs:
        if ass_db.upsert('res_inventories',
                         dict(ri_pr_fk=inv[0], ri_ho_fk=inv[1], ri_usage_year=inv[2], ri_inv_type=inv[3],
                              ri_swapped_product_id=inv[4], ri_granted_to=inv[5], ri_used_points=inv[6]),
                         chk_values=dict(ri_pr_fk=inv[0], ri_usage_year=inv[2])):
            ass_db.rollback()
            return ass_db.last_err_msg

    ass_db.commit()
    return ""


def ac_migrate_res_data():
    log_warning("Fetching reservation data from Acumen (needs some minutes)", 'FetchAcuResData', importance=3)
    acumen_req = ResToSihot(cae)
    error_msg = acumen_req.fetch_all_valid_from_acu(date_range='P')
    if error_msg:
        return error_msg
    for crow in acumen_req.rows:
        # determine orderer
        ord_cl_pk = conf_data.cl_ass_id_by_ac_id(crow['OC_CODE'])
        if ord_cl_pk is None:
            error_msg = conf_data.error_message
            ord_cl_pk = conf_data.cl_ass_id_by_sh_id(crow['OC_SIHOT_OBJID'])
            if ord_cl_pk is None:
                error_msg += conf_data.error_message
                break
            error_msg = ""

        # determine used reservation inventory
        year, week = conf_data.rci_arr_to_year_week(crow['ARR_DATE'])
        apt_wk = "{}-{:0>2}".format(crow['RUL_SIHOT_ROOM'], week)
        if ass_db.select('res_inventories', ['ri_pk'], "ri_pk = :aw AND ri_usage_year = :y", dict(aw=apt_wk, y=year)):
            error_msg = ass_db.last_err_msg
            break
        ri_pk = ass_db.fetch_value()

        gds = crow['SIHOT_GDSNO']

        # complete res data with check-in/-out time...
        ac_res = conf_data.load_view(acu_db,
                                     "T_ARO INNER JOIN T_RU ON ARO_RHREF = RU_RHREF and ARO_EXP_ARRIVE = RU_FROM_DATE",
                                     ['ARO_TIMEIN', 'ARO_TIMEOUT'],
                                     "ARO_STATUS <> 120 and RU_STATUS <> 120 and RU_CODE = :gds_no",
                                     dict(gds_no=gds))
        if ac_res is None:
            error_msg = conf_data.error_message
            break
        elif not ac_res:
            ac_res = (None, None)
        crow['TIMEIN'], crow['TIMEOUT'] = ac_res

        chk_values = dict(rgr_ho_fk=crow['RUL_SIHOT_HOTEL'], rgr_gds_no=gds)
        upd_values = chk_values.copy()
        upd_values.update(rgr_order_cl_fk=ord_cl_pk,
                          rgr_used_ri_fk=ri_pk,
                          rgr_arrival=crow['ARR_DATE'],
                          rgr_departure=crow['DEP_DATE'],
                          rgr_status=crow['SIHOT_RES_TYPE'],
                          rgr_adults=crow['RU_ADULTS'],
                          rgr_children=crow['RU_CHILDREN'],
                          rgr_mkt_segment=crow['SIHOT_MKT_SEG'],
                          rgr_mkt_group=crow['RO_SIHOT_RES_GROUP'],
                          rgr_room_cat_id=crow['RUL_SIHOT_CAT'],
                          rgr_room_rate=crow['RUL_SIHOT_RATE'],
                          rgr_ext_book_id=crow['RH_EXT_BOOK_REF'],
                          rgr_ext_book_day=crow['RH_EXT_BOOK_DATE'],
                          rgr_comment=crow['SIHOT_NOTE'],
                          rgr_long_comment=crow['SIHOT_TEC_NOTE'],
                          rgr_time_in=ac_res[0],
                          rgr_time_out=ac_res[1],
                          rgr_created_by=pg_user,
                          rgr_created_when=cae.startup_beg,
                          rgr_last_change=cae.startup_beg,
                          rgr_last_sync=cae.startup_beg
                          )
        if ass_db.upsert('res_groups', upd_values, chk_values=chk_values, returning_column='rgr_pk'):
            error_msg = ass_db.last_err_msg
            break
        rgr_pk = ass_db.fetch_value()

        # determine occupant(s)
        mc = crow['CD_CODE']
        ac_cos = conf_data.load_view(acu_db, "T_CD",
                                     ['CD_SNAM1', 'CD_FNAM1', 'CD_DOB1', 'CD_SNAM2', 'CD_FNAM2', 'CD_DOB2'],
                                     "CD_CODE = :ac_id", dict(ac_id=mc))
        if ac_cos is None:
            error_msg = conf_data.error_message
            break
        occ_cl_pk = conf_data.cl_ass_id_by_ac_id(mc)
        if occ_cl_pk is None:
            error_msg = conf_data.error_message
            break

        chk_values = dict(rgc_rgr_fk=rgr_pk, rgc_room_seq=0, rgc_pers_seq=0)
        upd_values = chk_values.copy()
        upd_values.update(rgc_surname=ac_cos['CD_SNAM1'],
                          rgc_firstname=ac_cos['CD_FNAM1'],
                          rgc_auto_generated='0',
                          rgc_occup_cl_fk=occ_cl_pk,
                          rgc_flight_arr_comment=crow['RU_FLIGHT_AIRPORT'] + " No=" + crow['RU_FLIGHT_NO'],
                          rgc_flight_arr_time=crow['RU_FLIGHT_LANDS'],
                          # occupation data
                          rgc_pers_type='1A',
                          rgc_sh_pack=crow['RUL_SIHOT_PACK'],
                          rgc_room_id=crow['RUL_SIHOT_ROOM'],
                          rgc_dob=ac_cos['CD_DOB1']
                          )
        if ass_db.upsert('res_group_clients', upd_values, chk_values=chk_values):
            error_msg = ass_db.last_err_msg
            break
        # .. add 2nd couple to occupants/res_group_clients
        occ_cl_pk = conf_data.cl_ass_id_by_ac_id(mc + AC_ID_2ND_COUPLE_SUFFIX)
        if occ_cl_pk is None:
            error_msg = conf_data.error_message
            break
        upd_values['rgc_surname'] = ac_cos['CD_SNAM2']
        upd_values['rgc_surname'] = ac_cos['CD_SNAM2']
        upd_values['rgc_occup_cl_fk'] = occ_cl_pk
        upd_values['rgc_dob'] = ac_cos['CD_DOB2']
        upd_values['rgc_pers_seq'] = chk_values['rgc_pers_seq'] = 1
        if ass_db.upsert('res_group_clients', upd_values, chk_values=chk_values):
            error_msg = ass_db.last_err_msg
            break

    return ass_db.rollback() if error_msg else ass_db.commit()


def sh_migrate_res_data():
    log_warning("Fetching reservation data from Sihot (needs some minutes)", 'FetchShResData', importance=3)
    rbf_groups = sh_rbf.fetch_all()
    error_msg = ""
    for rg in rbf_groups:
        mc = elem_value(rg, ['RESCHANNELLIST', 'RESCHANNEL', 'MATCHCODE'])
        ord_cl_pk = conf_data.cl_ass_id_by_ac_id(mc)
        if ord_cl_pk is None:
            error_msg = conf_data.error_message
            sh_id = elem_value(rg, ['RESCHANNELLIST', 'RESCHANNEL', 'OBJID'])
            ord_cl_pk = conf_data.cl_ass_id_by_sh_id(sh_id)
            if ord_cl_pk is None:
                error_msg += conf_data.error_message
                break
            error_msg = ""

        apt, wk, year = apt_wk_yr(rg, cae)
        apt_wk = "{}-{:0>2}".format(apt, wk)
        if ass_db.select('res_inventories', ['ri_pk'], "ri_pk = :aw and ri_usage_year = :y", dict(aw=apt_wk, y=year)):
            error_msg = ass_db.last_err_msg
            break
        ri_pk = ass_db.fetch_value()

        gds = gds_no(rg)
        chk_values = dict(rgr_ho_fk=elem_value(rg, 'RES-HOTEL'))  # hotelID returned by RES-SEARCH (missing ID elem)
        if gds:
            chk_values.update(rgr_gds_no=gds)
        else:
            chk_values.update(rgr_res_id=elem_value(rg, 'RES-NR'), rgr_sub_id=elem_value(rg, 'SUB-NR'))
        upd_values = chk_values.copy()
        upd_values\
            .update(rgr_order_cl_fk=ord_cl_pk,
                    rgr_used_ri_fk=ri_pk,
                    rgr_arrival=datetime.datetime.strptime(elem_value(rg, ['RESERVATION', 'ARR']), SH_DATE_FORMAT),
                    rgr_departure=datetime.datetime.strptime(elem_value(rg, ['RESERVATION', 'DEP']), SH_DATE_FORMAT),
                    rgr_status=elem_value(rg, 'RT'),
                    rgr_adults=elem_value(rg, 'NOPAX'),
                    rgr_children=elem_value(rg, 'NOCHILDS'),
                    rgr_mkt_segment=elem_value(rg, 'MARKETCODE'),
                    rgr_mkt_group=elem_value(rg, 'CHANNEL'),
                    rgr_room_cat_id=elem_value(rg, elem_path_join(['RESERVATION', 'CAT'])),
                    rgr_room_rate=elem_value(rg, 'RATE-SEGMENT'),
                    rgr_payment_inst=elem_value(rg, 'PAYMENT-INST'),
                    rgr_ext_book_id=elem_value(rg, elem_path_join(['RESERVATION', 'VOUCHERNUMBER'])),
                    rgr_ext_book_day=elem_value(rg, 'SALES-DATE'),
                    rgr_comment=elem_value(rg, elem_path_join(['RESERVATION', 'COMMENT'])),
                    rgr_long_comment=elem_value(rg, 'TEC-COMMENT'),
                    rgr_created_by=pg_user,
                    rgr_created_when=cae.startup_beg,
                    rgr_last_change=cae.startup_beg,
                    rgr_last_sync=cae.startup_beg
                    )
        if ass_db.upsert('res_groups', upd_values, chk_values=chk_values, returning_column='rgr_pk'):
            error_msg = ass_db.last_err_msg
            break
        rgr_pk = ass_db.fetch_value()

        for arri in range(pax_count(rg)):
            mc = elem_value(rg, ['PERSON', 'MATCHCODE'], arri=arri)
            occ_cl_pk = None
            if mc:
                occ_cl_pk = conf_data.cl_ass_id_by_ac_id(mc)
                if occ_cl_pk is None:
                    error_msg = conf_data.error_message
                    break
            room_seq = int(elem_value(rg, ['PERSON', 'ROOM-SEQ'], arri=arri))
            pers_seq = int(elem_value(rg, ['PERSON', 'ROOM-PERS-SEQ'], arri=arri))
            chk_values = dict(rgc_rgr_fk=rgr_pk, rgc_room_seq=room_seq, rgc_pers_seq=pers_seq)
            upd_values = chk_values.copy()
            upd_values\
                .update(rgc_surname=elem_value(rg, ['PERSON', 'NAME'], arri=arri),
                        rgc_firstname=elem_value(rg, ['PERSON', 'NAME2'], arri=arri),
                        rgc_auto_generated=elem_value(rg, ['PERSON', 'AUTO-GENERATED'], arri=arri),
                        rgc_occup_cl_fk=occ_cl_pk,
                        # Sihot offers also PICKUP-TYPE-ARRIVAL(1=car, 2=van), we now use PICKUP-TIME-ARRIVAL
                        # .. instead of ARR-TIME for the flight arr/dep (pg converts str into time object/value)
                        rgc_flight_arr_comment=elem_value(rg, ['PERSON', 'PICKUP-COMMENT-ARRIVAL']),
                        rgc_flight_arr_time=elem_value(rg, ['PERSON', 'PICKUP-TIME-ARRIVAL']),
                        rgc_flight_dep_comment=elem_value(rg, ['PERSON', 'PICKUP-COMMENT-DEPARTURE']),
                        rgc_flight_dep_time=elem_value(rg, ['PERSON', 'PICKUP-TIME-DEPARTURE']),
                        # occupation data
                        rgc_pers_type=elem_value(rg, ['PERSON', 'PERS-TYPE'], arri=arri),
                        rgc_sh_pack=elem_value(rg, ['PERSON', 'R'], arri=arri),
                        rgc_room_id=elem_value(rg, ['PERSON', 'RN'], arri=arri),
                        rgc_dob=datetime.datetime.strptime(elem_value(rg, ['PERSON', 'DOB'], arri=arri), SH_DATE_FORMAT)
                        )
            if ass_db.upsert('res_group_clients', upd_values, chk_values=chk_values):
                error_msg = ass_db.last_err_msg
                break

    return ass_db.rollback() if error_msg else ass_db.commit()


if acm_syncs:
    log_warning("Starting data synchronization/migration", 'syncCache', importance=4)
for acm_sync in acm_syncs:
    if acm_sync[:2] == 'ac':
        if acm_sync[2:] == 'C':
            err = ac_migrate_clients()
            if err:
                log_error(err, 'syncCacheAcuClients', importance=3, exit_code=111, dbs=[ass_db,  acu_db])
        if acm_sync[2:] == 'P':
            err = ac_migrate_products()
            if err:
                log_error(err, 'syncCacheAcuProductTypes', importance=3, exit_code=114, dbs=[ass_db,  acu_db])
        if acm_sync[2:] == 'R':
            err = ac_migrate_res_inv()  # load reservation inventory data
            if err:
                log_error(err, 'syncCacheAcuResInv', importance=3, exit_code=117, dbs=[ass_db,  acu_db])
            err = ac_migrate_res_data()
            if err:
                log_error(err, 'syncCacheAcuResData', importance=3, exit_code=120, dbs=[ass_db,  acu_db])

    elif acm_sync[:2] == 'sf':
        log_error("Salesforce sync not implemented", 'syncCacheSf', importance=3, exit_code=135, dbs=[ass_db, acu_db])

    elif acm_sync[:2] == 'sh':
        if acm_sync[2:] == 'R':
            err = sh_migrate_res_data()
            if err:
                log_error(err, 'syncCacheShResData', importance=3, exit_code=132, dbs=[ass_db,  acu_db])


def ac_check_clients():
    ac_cls = conf_data.load_view(acu_db, 'T_CD', [AC_SQL_AC_ID1,
                                                  AC_SQL_PHONE1, AC_SQL_MAIN_RCI,
                                                  AC_SQL_SF_ID1, AC_SQL_SH_ID1, AC_SQL_NAME1, AC_SQL_EMAIL1,
                                                  AC_SQL_SF_ID2, AC_SQL_SH_ID2, AC_SQL_NAME2, AC_SQL_EMAIL2],
                                 "substr(CD_CODE, 1, 1) <> 'A'")
    if ac_cls is None:
        return conf_data.error_message
    ac_cl_dict = dict((_[0], _[1:]) for _ in ac_cls)
    ac_cl_ori_dict = ac_cl_dict.copy()

    ctx = 'acChkCl'
    cnt = len(warn_log)
    for as_cl in conf_data.clients:
        ass_id, ac_id, sf_id, sh_id, name, email, phone, ext_refs, _ = as_cl
        if not ac_id:
            if _debug_level >= DEBUG_LEVEL_VERBOSE:
                log_warning("{} - AssCache client without Acumen client reference: {}".format(ass_id, as_cl), ctx)
            continue

        ac_id, offset = (ac_id[:-len(AC_ID_2ND_COUPLE_SUFFIX)], 6) if ac_id.endswith(AC_ID_2ND_COUPLE_SUFFIX) \
            else (ac_id, 2)
        if ac_id not in ac_cl_ori_dict:
            log_warning("{} - Acumen client reference {} not found in Acumen system".format(ass_id, ac_id), ctx)
            continue

        ac_sf_id, ac_sh_id, ac_name, ac_email, *_ = ac_cl_ori_dict[ac_id][offset:]
        ac_sf_id = ensure_long_id(ac_sf_id)
        if sf_id != ac_sf_id:
            log_warning("{} - Salesforce client ID differs: ass={} acu={}".format(ass_id, sf_id, ac_sf_id), ctx)
        if sh_id != ac_sh_id:
            log_warning("{} - Sihot guest object ID differs: ass={} acu={}".format(ass_id, sh_id, ac_sh_id), ctx)
        if name != ac_name:
            log_warning("{} - Client name differs: ass={} acu={}".format(ass_id, name, ac_name), ctx)
        ac_email, _ = correct_email(ac_email)
        if email != ac_email:
            log_warning("{} - Client email differs: ass={} acu={}".format(ass_id, email, ac_email), ctx)

        if offset:              # further checks not needed for 2nd client/couple of Acumen client
            continue

        if ac_id not in ac_cl_dict:
            log_warning("{} - Acumen client reference duplicates found in AssCache; records={}"
                        .format(ac_id, conf_data.cl_list_by_ac_id(ac_id)), ctx)
            continue
        ac_phone, ac_rci_main, *_ = ac_cl_dict.pop(ac_id)

        ac_phone, _ = correct_phone(ac_phone)
        if phone != ac_phone:
            log_warning("{} - Client phone differs: ass={} acu={}".format(ass_id, phone, ac_phone), ctx)

        as_ers = [tuple(_.split(EXT_REF_TYPE_ID_SEP)) for _ in ext_refs.split(EXT_REFS_SEP)] if ext_refs else list()
        ac_ers = conf_data.load_view(acu_db, 'T_CR', ["DISTINCT " + AC_SQL_EXT_REF_TYPE, "CR_REF"],
                                     "CR_CDREF = :ac", dict(ac=ac_id))
        if ac_ers is None:
            return conf_data.error_message
        if ac_rci_main:         # if CD_RCI_REF is populated and no dup then add it to the external refs list
            main_rci_ref = (EXT_REF_TYPE_RCI, ac_rci_main)
            if main_rci_ref not in ac_ers:
                ac_ers.append(main_rci_ref)
        if len(as_ers) != len(ac_ers):
            log_warning("{} - Number of ext. refs differ: ass={}, acu={}".format(ass_id, len(as_ers), len(ac_ers)), ctx)
        for as_er in as_ers:
            if not [_ for _ in ac_ers if _ == as_er]:
                log_warning("{} - External Ref {}={} missing in Acumen".format(ass_id, as_er[0], as_er[1]), ctx)
        for ac_er in ac_ers:
            if not [_ for _ in as_ers if _ == ac_er]:
                log_warning("{} - External Ref {}={} missing in AssCache".format(ass_id, ac_er[0], ac_er[1]), ctx)

    # finally log clients that are in Acumen but missing in AssCache
    for ac_id, ac_cl in ac_cl_dict.items():
        log_warning("Acumen client {} missing in AssCache: {}".format(ac_id, ac_cl), ctx)

    log_warning("No Acumen discrepancies found" if len(warn_log) == cnt else "Number of Acumen discrepancies: {}"
                .format(len(warn_log) - cnt), ctx, importance=3)

    return ""


def sf_check_clients():
    ctx = 'sfChkCl'
    cnt = len(warn_log)
    for as_co in conf_data.clients:
        ass_id, ac_id, sf_id, sh_id, name, email, phone, ass_ext_refs, products = as_co
        if not sf_id:
            if _debug_level >= DEBUG_LEVEL_VERBOSE:
                log_warning("{} - AssCache client without SF ID: {}".format(ass_id, as_co), ctx, importance=1)
            continue

        fld_names = acm_field_filters.get('C')
        if not fld_names:
            fld_names = list(_ for _ in conf_data.client_fields.keys() if _ != 'SfId')
        sf_fld_names = list(_ for _ in fld_names if _ not in ('ExtRefs', 'Products'))
        log_warnings = list()
        sf_fld_values = sf_conn.client_field_data(sf_fld_names, sf_id, log_warnings=log_warnings)
        if not sf_fld_values:
            if _debug_level >= DEBUG_LEVEL_VERBOSE:
                for msg in log_warnings:
                    log_warning("{} - {}: {}".format(ass_id, msg, as_co), ctx, importance=1)
            log_warning("{} - {} ID {} not found as object ID nor in any of the reference/redirect ID fields: {}"
                        .format(ass_id, obj_from_id(sf_id), sf_id, as_co), ctx, importance=3)
            continue

        for fld_name, fld_value in sf_fld_values.items():
            desc = conf_data.client_fields[fld_name]['Desc']
            ass_val = as_co[conf_data.client_fields[fld_name]['ColIdx']]
            if (ass_val or fld_value) and ass_val != fld_value:
                log_warning("{} - {} mismatch. ass={} sf={}: {}".format(ass_id, desc, ass_val, fld_value, as_co), ctx)

        if 'ExtRefs' in fld_names:
            ext_refs = [tuple(_.split(EXT_REF_TYPE_ID_SEP)) for _ in ass_ext_refs.split(EXT_REFS_SEP)] \
                if ass_ext_refs else list()
            sf_ext_refs = sf_conn.client_ext_refs(sf_id)
            for er in ext_refs:
                if er not in sf_ext_refs:
                    log_warning("{} - AssCache external reference {} missing in SF: {}".format(ass_id, er, as_co), ctx)
            for er in sf_ext_refs:
                if er not in ext_refs:
                    log_warning("{} - SF external reference {} missing in AssCache: {}".format(ass_id, er, as_co), ctx)

        if 'Products' in fld_names:
            pass    # not implemented

    log_warning("No Salesforce discrepancies found" if len(warn_log) == cnt else "Number of Salesforce discrepancies={}"
                .format(len(warn_log) - cnt), ctx, importance=3)

    return ""


def sh_check_clients():
    ctx = 'shChkCl'
    cnt = len(warn_log)
    for as_co in conf_data.clients:
        ass_id, ac_id, sf_id, sh_id, name, email, phone, _, _ = as_co
        if not sh_id:
            if _debug_level >= DEBUG_LEVEL_VERBOSE:
                log_warning("{} - AssCache client record without Sihot guest object ID: {}".format(ass_id, as_co), ctx)
            continue

        shd = guest_data(cae, sh_id)
        if not shd:
            log_warning("{} - AssCache guest object ID {} not found in Sihot: {}".format(ass_id, sh_id, as_co), ctx)
            continue

        if (ac_id or shd['MATCHCODE']) and ac_id != shd['MATCHCODE']:
            log_warning("{} - Acumen client ref mismatch. ass={}, sh={}".format(ass_id, ac_id, shd['MATCHCODE']), ctx)
        if (sf_id or shd['MATCH-SM']) and sf_id != shd['MATCH-SM']:
            log_warning("{} - Salesforce client ID mismatch. ass={} sh={}".format(ass_id, sf_id, shd['MATCH-SM']), ctx)
        sh_name = shd['NAME-2'] + ' ' + shd['NAME-1']
        if name != sh_name:
            log_warning("{} - Client name differs: ass={} sh={}".format(ass_id, name, sh_name), ctx)
        sh_email, _ = correct_email(shd['EMAIL-1'])
        if email != sh_email:
            log_warning("{} - Client email differs: ass={} sh={}".format(ass_id, email, sh_email), ctx)
        sh_phone1, _ = correct_phone(shd['PHONE-1'])
        sh_phone2, _ = correct_phone(shd['MOBIL-1'])
        if phone != sh_phone1 and phone != sh_phone2:
            sh_phones = sh_phone1 + " or " + sh_phone2
            log_warning("{} - Client phone differs: ass={} sh={}".format(ass_id, email, sh_phones), ctx)

    log_warning("No Sihot discrepancies found" if len(warn_log) == cnt else "Number of Sihot discrepancies: {}"
                .format(len(warn_log) - cnt), ctx, importance=3)

    return ""


if acm_veris:
    log_warning("Preparing data check/verification", 'veriCache', importance=4)
    # fetch all clients from AssCache
    err = conf_data.cl_fetch_all(where_group_order=acm_record_filters['C'] if 'C' in acm_record_filters else "")
    if err:
        log_error("Client cache load error: " + err, 'veriCache', importance=3, exit_code=300, dbs=[ass_db,  acu_db])
    # verify AssCache client integrity
    if [_ for _ in acm_veris if _[2:] == 'C']:
        conf_data.cl_check_ext_refs()
for acm_veri in acm_veris:
    if acm_veri[:2] == 'ac':
        if acm_veri[2:] == 'C':
            err = ac_check_clients()
            if err:
                log_error(err, 'veriCacheAcClients', importance=3, exit_code=303, dbs=[ass_db,  acu_db])
        elif acm_veri[2:] == 'P':
            log_error("Acumen Product Verification not implemented", 'veriCacheAcProd', importance=3, exit_code=330,
                      dbs=[ass_db,  acu_db])
        elif acm_veri[2:] == 'R':
            log_error("Acumen Reservation Verification not implemented", 'veriCacheAcRes', importance=3, exit_code=360,
                      dbs=[ass_db,  acu_db])

    elif acm_veri[:2] == 'sh':
        if acm_veri[2:] == 'C':
            err = sh_check_clients()
            if err:
                log_error(err, 'veriCacheShClients', importance=3, exit_code=402, dbs=[ass_db,  acu_db])
        else:
            log_error("Sihot veri. not implemented", 'veriCacheSh', importance=3, exit_code=495, dbs=[ass_db,  acu_db])

    elif acm_veri[:2] == 'sf':
        if acm_veri[2:] == 'C':
            err = sf_check_clients()
            if err:
                log_error(err, 'veriCacheSfClients', importance=3, exit_code=501, dbs=[ass_db,  acu_db])
        else:
            log_error("Salesforce verification not implemented", 'veriCacheSf', importance=3, exit_code=591,
                      dbs=[ass_db,  acu_db])


def ac_fix_clients():
    """
    push from AssCache to Acumen for to fix there external references, email and phone data.
    :return: error message or "" in case of no errors.
    """
    return ""


def sf_fix_clients():
    """
    push from AssCache to Salesforce for to fix there external references, email and phone data.
    :return: error message or "" in case of no errors.
    """
    return ""


def sh_fix_clients():
    """
    push from AssCache to Sihot for to fix there external references, email and phone data.
    :return: error message or "" in case of no errors.
    """
    return ""


if acm_fixes:
    log_warning("Preparing data push and fix", 'pushFix', importance=4)
    # fetch all clients from AssCache
    err = conf_data.cl_fetch_all(where_group_order=acm_record_filters['C'] if 'C' in acm_record_filters else "")
    if err:
        log_error("Client cache load error: " + err, 'veriCache', importance=3, exit_code=600, dbs=[ass_db,  acu_db])
for acm_fix in acm_fixes:
    if acm_fix[:2] == 'ac':
        if acm_fix[2:] == 'C':
            err = ac_fix_clients()
            if err:
                log_error(err, 'pushFixAcClients', importance=3, exit_code=303, dbs=[ass_db,  acu_db])
        elif acm_fix[2:] == 'P':
            log_error("Acumen Product Fix not implemented", 'pushFixAcProd', importance=3, exit_code=630,
                      dbs=[ass_db,  acu_db])
        elif acm_fix[2:] == 'R':
            log_error("Acumen Reservation Fix not implemented", 'pushFixAcRes', importance=3, exit_code=660,
                      dbs=[ass_db,  acu_db])

    elif acm_fix[:2] == 'sf':
        if acm_fix[2:] == 'C':
            err = sf_fix_clients()
            if err:
                log_error(err, 'pushFixSfClients', importance=3, exit_code=801, dbs=[ass_db,  acu_db])
        else:
            log_error("Salesforce fix not implemented", 'pushFixSf', importance=3, exit_code=891,
                      dbs=[ass_db,  acu_db])

    elif acm_fix[:2] == 'sh':
        if acm_fix[2:] == 'C':
            err = sh_fix_clients()
            if err:
                log_error(err, 'pushFixShClients', importance=3, exit_code=702, dbs=[ass_db,  acu_db])
        else:
            log_error("Sihot fix not implemented", 'pushFixSh', importance=3, exit_code=795, dbs=[ass_db,  acu_db])


if acu_db:
    acu_db.close()
if ass_db:
    ass_db.close()
cae.shutdown(send_notification(42 if error_log else 0))
