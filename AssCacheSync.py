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
from sfif import prepare_connection
from ass_sys_data import AssSysData, ext_ref_type_sql, EXT_REF_TYPE_RCI, EXT_REFS_SEP
from ae_notification import Notification

__version__ = '0.1'

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)

cae = ConsoleApp(__version__, "Initialize, sync and/or verify AssCache from/against Acumen, Sihot and Salesforce")

cae.add_option('initializeCache', "Initialize/Wipe/Recreate ass_cache database (0=No, 1=Yes)", 0, 'I')
sync_veri_choices = ('acC', 'acP', 'acR', 'shC', 'shR', 'sfC', 'sfP', 'sfR')
cae.add_option('syncCache', "Synchronize from (ac=Acumen, sh=Sihot, sf=Salesforce) including (C=Contacts, P=Products, "
                            "R=Reservations), e.g. shC is synchronizing contacts from Sihot",
               [], 'S', choices=sync_veri_choices, multiple=True)
cae.add_option('verifyCache', "Verify/Check against (ac=Acumen, sh=Sihot, sf=Salesforce) including (C=Contacts, "
                              "P=Products, R=Reservations), e.g. acR is checking reservations against Acumen",
               [], 'V', choices=sync_veri_choices, multiple=True)
cae.add_option('verifyFilters', "Filter to restrict the checked data (C=contact-, P=product-, R=reservation-filter), "
                                "e.g. {'C':\\\"co_ac_id='E123456'\\\"} checks only the contact with Acumen ID E123456",
               {}, 'W')

cae.add_option('pgUser', "User account name for the postgres cache database", '', 'U')
cae.add_option('pgPassword', "User account password for the postgres cache database", '', 'P')
cae.add_option('pgDSN', "Database name of the postgres cache database", 'ass_cache', 'N')

cae.add_option('acuUser', "User name of Acumen/Oracle system", '', 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", '', 'd')

cae.add_option('sfUser', "Salesforce account user name", '', 'y')
cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
cae.add_option('sfToken', "Salesforce account token string", '', 'o')
cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')

sh_rbf = ResBulkFetcher(cae)
sh_rbf.add_options()
# .. and for GuestBulkFetcher we need also the kernel interface port of Sihot
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", list(), 'r')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", list(), 'v')

debug_level = cae.get_option('debugLevel')

systems = dict(ac='Acumen', sh='Sihot', sf='Salesforce')
types = dict(C='Contacts', P='Products', R='Reservations')
acm_init = cae.get_option('initializeCache')
acm_syncs = cae.get_option('syncCache')
acm_veris = cae.get_option('verifyCache')
actions = list()
if acm_init:
    actions.append("Initialize")
for acm_sync in acm_syncs:
    actions.append("Synchronize/Migrate " + types[acm_sync[2:]] + " from " + systems[acm_sync[:2]])
for acm_veri in acm_veris:
    actions.append("Verify/Check " + types[acm_veri[2:]] + " against " + systems[acm_veri[:2]])
uprint("Actions: " + '\n         '.join(actions))
acm_veri_filters = cae.get_option('verifyFilters')
if acm_veri_filters:
    uprint("Verification filtering:", acm_veri_filters)

x = sh_rbf.load_config()
sh_rbf.print_config()
uprint("Sihot Kernel-port:", cae.get_option('serverKernelPort'))

acu_user = cae.get_option('acuUser')
acu_password = cae.get_option('acuPassword')
acu_dsn = cae.get_option('acuDSN')
uprint("Acumen user/DSN:", acu_user, acu_dsn)

pg_user = cae.get_option('pgUser')
pg_pw = cae.get_option('pgPassword')
pg_dsn = cae.get_option('pgDSN')
uprint("AssCache DB user@dbname:", pg_user, '@', pg_dsn)

sf_conn, sf_sandbox = prepare_connection(cae)
if not sf_conn:
    uprint("Salesforce account connection could not be established - please check your account data and credentials")
    cae.shutdown(20)

notification = warning_notification_emails = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system="{}/{}/{}".format(acu_dsn, cae.get_option('serverIP'),
                                                              "SBox" if sf_sandbox else "Prod"),
                                debug_level=cae.get_option('debugLevel'))
    uprint("SMTP Uri/From/To:", cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    warning_notification_emails = cae.get_option('warningsMailToAddr')
    if warning_notification_emails:
        uprint("Warnings SMTP receiver address(es):", warning_notification_emails)


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


# LOGGING HELPERS
error_log = list()
warn_log = list()


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


# check for to (re-)create and initialize PG database
if acm_init:
    log_warning("creating data base {} and user {}".format(pg_dsn, pg_user), 'initializeCache-createDBandUser')
    pg_db = PostgresDB(usr=cae.get_config('pgRootUsr'), pwd=cae.get_config('pgRootPwd'), dsn='postgres',
                       debug_level=debug_level)
    if pg_db.execute_sql("CREATE DATABASE " + pg_dsn + ";", auto_commit=True):  # " LC_COLLATE 'C'"):
        log_error(pg_db.last_err_msg, 'initializeCache-createDB', exit_code=72)

    if pg_db.select('pg_user', ['count(*)'], "usename = :pg_user", dict(pg_user=pg_user)):
        log_error(pg_db.last_err_msg, 'initializeCache-checkUser', exit_code=81)
    if not pg_db.fetch_value():
        if pg_db.execute_sql("CREATE USER " + pg_user + " WITH PASSWORD '" + pg_pw + "';", commit=True):
            log_error(pg_db.last_err_msg, 'initializeCache-createUser', exit_code=84)
        if pg_db.execute_sql("GRANT ALL PRIVILEGES ON DATABASE " + pg_dsn + " to " + pg_user + ";", commit=True):
            log_error(pg_db.last_err_msg, 'initializeCache-grantUserConnect', exit_code=87)
    pg_db.close()

    log_warning("creating tables and audit trigger schema/extension", 'initializeCache-createTableAndAudit')
    pg_db = PostgresDB(usr=cae.get_config('pgRootUsr'), pwd=cae.get_config('pgRootPwd'), dsn=pg_dsn,
                       debug_level=debug_level)
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


# logon to and prepare Acumen, Salesforce, Sihot and config data env
conf_data = AssSysData(cae, err_logger=log_error, warn_logger=log_warning)
if conf_data.error_message:
    log_error(conf_data.error_message, 'AssSysDataInit', importance=4, exit_code=9)

# logon to and prepare ass_cache database and optional to Acumen database
ass_db = conf_data.ass_db
if conf_data.error_message:
    log_error(conf_data.error_message, 'AssUserLogOn', importance=4, exit_code=12, dbs=[ass_db])
acu_db = conf_data.acu_db if [_ for _ in acm_syncs + acm_veris if _[:2] == 'ac'] else None
if conf_data.error_message:
    log_error(conf_data.error_message, 'AcuUserLogOn', importance=4, exit_code=15, dbs=[ass_db, acu_db])


def ac_migrate_contacts():
    """ migrate contacts from Acumen and Salesforce into ass_cache/postgres """

    # fetch all couple-contacts from Acumen
    log_warning("Fetching couple contact data from Acumen (needs some minutes)", 'FetchAcuCoupleContacts', importance=3)
    ac_cos = conf_data.load_view(acu_db, 'T_CD',
                                 ["CD_CODE", "CD_SF_ID1", "to_char(CD_SIHOT_OBJID)", "CD_RCI_REF"],
                                 "substr(CD_CODE, 1, 1) <> 'A' and CD_SNAM1 is not NULL and CD_FNAM1 is not NULL")
    if ac_cos is None:
        return conf_data.error_message
    ac_2 = conf_data.load_view(acu_db, 'T_CD',
                               ["CD_CODE || '" + AC_ID_2ND_COUPLE_SUFFIX + "'", "CD_SF_ID2", "to_char(CD_SIHOT_OBJID2)",
                                "NULL"],
                               "substr(CD_CODE, 1, 1) <> 'A' and CD_SNAM2 is not NULL and CD_FNAM2 is not NULL")
    if ac_2 is None:
        return conf_data.error_message
    ac_cos += ac_2
    ac_cos.sort(key=lambda _: _[0])

    # migrate to ass_cache including additional external refs/IDs (fetched from Acumen)
    for idx, ac_co in enumerate(ac_cos):
        co_pk = conf_data.co_save(ac_co[0], ac_co[1], ac_co[2], ext_refs=[(EXT_REF_TYPE_RCI, ac_co[3])])
        if co_pk is None:
            break
        if idx + 1 % 1000 == 0:
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
        co_pk = conf_data.co_ass_id_by_ac_id(cp[2])
        if co_pk is None:
            break
        col_values = dict(cp_co_fk=co_pk, cp_pr_fk=cp[0])
        if ass_db.upsert('contact_products', col_values, chk_values=col_values):
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
        ord_co_pk = conf_data.co_ass_id_by_ac_id(crow['OC_CODE'])
        if ord_co_pk is None:
            error_msg = conf_data.error_message
            ord_co_pk = conf_data.co_ass_id_by_sh_id(crow['OC_SIHOT_OBJID'])
            if ord_co_pk is None:
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
        upd_values.update(rgr_order_co_fk=ord_co_pk,
                          rgr_used_ri_fk=ri_pk,
                          rgr_arrival=crow['ARR_DATE'],
                          rgr_departure=crow['DEP_DATE'],
                          rgr_status=crow['SIHOT_RES_TYPE'],
                          rgr_adults=crow['RU_ADULTS'],
                          rgr_children=crow['RU_CHILDREN'],
                          rgr_mkt_segment=crow['SIHOT_MKT_SEG'],
                          rgr_mkt_group=crow['RO_SIHOT_RES_GROUP'],
                          rgr_room_cat_id=crow['RUL_SIHOT_CAT'],
                          rgr_sh_rate=crow['RUL_SIHOT_RATE'],
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
        occ_co_pk = conf_data.co_ass_id_by_ac_id(mc)
        if occ_co_pk is None:
            error_msg = conf_data.error_message
            break

        chk_values = dict(rgc_rgr_fk=rgr_pk, rgc_room_seq=0, rgc_pers_seq=0)
        upd_values = chk_values.copy()
        upd_values.update(rgc_surname=ac_cos['CD_SNAM1'],
                          rgc_firstname=ac_cos['CD_FNAM1'],
                          rgc_auto_generated='0',
                          rgc_occup_co_fk=occ_co_pk,
                          rgc_flight_arr_comment=crow['RU_FLIGHT_AIRPORT'] + " No=" + crow['RU_FLIGHT_NO'],
                          rgc_flight_arr_time=crow['RU_FLIGHT_LANDS'],
                          # occupation data
                          rgc_pers_type='1A',
                          rgc_sh_pack=crow['RUL_SIHOT_PACK'],
                          rgc_room_id=crow['RUL_SIHOT_ROOM'],
                          rgc_dob=ac_cos['CD_DOB1']
                          )
        if ass_db.upsert('res_group_contacts', upd_values, chk_values=chk_values):
            error_msg = ass_db.last_err_msg
            break
        # .. add 2nd couple to occupants/res_group_contacts
        occ_co_pk = conf_data.co_ass_id_by_ac_id(mc + AC_ID_2ND_COUPLE_SUFFIX)
        if occ_co_pk is None:
            error_msg = conf_data.error_message
            break
        upd_values['rgc_surname'] = ac_cos['CD_SNAM2']
        upd_values['rgc_surname'] = ac_cos['CD_SNAM2']
        upd_values['rgc_occup_co_fk'] = occ_co_pk
        upd_values['rgc_dob'] = ac_cos['CD_DOB2']
        upd_values['rgc_pers_seq'] = chk_values['rgc_pers_seq'] = 1
        if ass_db.upsert('res_group_contacts', upd_values, chk_values=chk_values):
            error_msg = ass_db.last_err_msg
            break

    return ass_db.rollback() if error_msg else ass_db.commit()


def sh_migrate_res_data():
    log_warning("Fetching reservation data from Sihot (needs some minutes)", 'FetchShResData', importance=3)
    rbf_groups = sh_rbf.fetch_all()
    error_msg = ""
    for rg in rbf_groups:
        mc = elem_value(rg, ['RESCHANNELLIST', 'RESCHANNEL', 'MATCHCODE'])
        ord_co_pk = conf_data.co_ass_id_by_ac_id(mc)
        if ord_co_pk is None:
            error_msg = conf_data.error_message
            sh_id = elem_value(rg, ['RESCHANNELLIST', 'RESCHANNEL', 'OBJID'])
            ord_co_pk = conf_data.co_ass_id_by_sh_id(sh_id)
            if ord_co_pk is None:
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
            chk_values.update(rgr_sh_res_id=elem_value(rg, 'RES-NR') + '/' + elem_value(rg, 'SUB-NR'))
        upd_values = chk_values.copy()
        upd_values\
            .update(rgr_order_co_fk=ord_co_pk,
                    rgr_used_ri_fk=ri_pk,
                    rgr_arrival=datetime.datetime.strptime(elem_value(rg, ['RESERVATION', 'ARR']), SH_DATE_FORMAT),
                    rgr_departure=datetime.datetime.strptime(elem_value(rg, ['RESERVATION', 'DEP']), SH_DATE_FORMAT),
                    rgr_status=elem_value(rg, 'RT'),
                    rgr_adults=elem_value(rg, 'NOPAX'),
                    rgr_children=elem_value(rg, 'NOCHILDS'),
                    rgr_mkt_segment=elem_value(rg, 'MARKETCODE'),
                    rgr_mkt_group=elem_value(rg, 'CHANNEL'),
                    rgr_room_cat_id=elem_value(rg, elem_path_join(['RESERVATION', 'CAT'])),
                    rgr_sh_rate=elem_value(rg, 'RATE-SEGMENT'),
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
            occ_co_pk = None
            if mc:
                occ_co_pk = conf_data.co_ass_id_by_ac_id(mc)
                if occ_co_pk is None:
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
                        rgc_occup_co_fk=occ_co_pk,
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
            if ass_db.upsert('res_group_contacts', upd_values, chk_values=chk_values):
                error_msg = ass_db.last_err_msg
                break

    return ass_db.rollback() if error_msg else ass_db.commit()


if acm_syncs:
    log_warning("Starting data synchronization/migration", 'syncCache', importance=4)
for acm_sync in acm_syncs:
    if acm_sync[:2] == 'ac':
        if acm_sync[2:] == 'C':
            err = ac_migrate_contacts()
            if err:
                log_error(err, 'syncCacheAcuContacts', importance=3, exit_code=111, dbs=[ass_db,  acu_db])
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

    elif acm_sync[:2] == 'sh':
        if acm_sync[2:] == 'R':
            err = sh_migrate_res_data()
            if err:
                log_error(err, 'syncCacheShResData', importance=3, exit_code=132, dbs=[ass_db,  acu_db])

    elif acm_sync[:2] == 'sf':
        log_error("Salesforce sync not implemented", 'syncCacheSf', importance=3, exit_code=135, dbs=[ass_db,  acu_db])


def ac_check_contacts():
    ac_cos = conf_data.load_view(acu_db, 'T_CD',
                                 ["CD_CODE",
                                  "CD_SF_ID1", "to_char(CD_SIHOT_OBJID)", "CD_SF_ID2", "to_char(CD_SIHOT_OBJID2)",
                                  "CD_RCI_REF", "case when CD_FNAM1 is not NULL and CD_SNAM1 is not NULL then 1 end"],
                                 "substr(CD_CODE, 1, 1) <> 'A'")
    if ac_cos is None:
        return conf_data.error_message
    ac_co_dict = dict((_[0], _[1:]) for _ in ac_cos)
    ac_co_ori_dict = ac_co_dict.copy()

    ctx = 'acChkCo'
    cnt = len(warn_log)
    for as_co in conf_data.contacts:
        ass_id, ac_id, sf_id, sh_id, ext_refs, _ = as_co
        if not ac_id:
            log_warning("{} - AssCache contact record without Acumen client reference: {}".format(ass_id, as_co), ctx)
            continue

        ac_id, offset = (ac_id[:-2], 2) if ac_id.endswith(AC_ID_2ND_COUPLE_SUFFIX) else (ac_id, 0)
        if ac_id not in ac_co_ori_dict:
            log_warning("{} - Acumen client reference {} not found in Acumen system".format(ass_id, ac_id), ctx)
            continue
        aco = ac_co_ori_dict[ac_id][offset:]
        if sf_id != aco[0]:     # co_sf_id
            log_warning("{} - Salesforce contact ID differs: ass={} acu={}".format(ass_id, sf_id, aco[0]), ctx)
        if sh_id != aco[1]:     # co_sh_id
            log_warning("{} - Sihot guest object ID differs: ass={} acu={}".format(ass_id, sh_id, aco[1]), ctx)

        if offset:              # no need to check again for 2nd contact/couple of Acumen contact
            continue
        if ac_id not in ac_co_dict:
            log_warning("{} - Acumen client id duplicates found in AssCache; records={}"
                        .format(ac_id, conf_data.co_list_by_ac_id(ac_id)), ctx)
            continue
        ac_co = ac_co_dict.pop(ac_id)

        # if ass_db.select('external_refs', ['er_type', 'er_id'], "er_co_fk = :co_pk", dict(co_pk=ass_id)):
        #     return ass_db.last_err_msg
        # as_ers = ass_db.fetch_all()
        as_ers = [tuple(_.split('=')) for _ in ext_refs.split(EXT_REFS_SEP)] if ext_refs else list()
        ac_ers = conf_data.load_view(acu_db, 'T_CR', ["DISTINCT " + ext_ref_type_sql(), "CR_REF"],
                                     "CR_CDREF = :ac", dict(ac=ac_id))
        if ac_ers is None:
            return conf_data.error_message
        if ac_co[4]:           # if CD_RCI_REF is populated and no dup then add it to the external refs list
            main_rci_ref = (EXT_REF_TYPE_RCI, ac_co[4])
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

    no_name = 0
    for ac_id, ac_co in ac_co_dict.items():
        if ac_co[5]:
            log_warning("Acumen client {} missing in AssCache: {}".format(ac_id, ac_co), ctx)
        else:
            no_name += 1
    if no_name:
        log_warning("Found {} clients in Acumen with empty first or second name".format(no_name), ctx, importance=1)

    log_warning("No Acumen discrepancies found" if len(warn_log) == cnt else "Number of Acumen discrepancies: {}"
                .format(len(warn_log) - cnt), ctx, importance=3)

    return ""


def sh_check_contacts():
    ctx = 'shChkCo'
    cnt = len(warn_log)
    for as_co in conf_data.contacts:
        ass_id, ac_id, sf_id, sh_id, _, _ = as_co
        if not sh_id:
            if debug_level >= DEBUG_LEVEL_VERBOSE:
                log_warning("{} - AssCache contact record without Sihot guest object ID: {}".format(ass_id, as_co), ctx)
            continue

        shd = guest_data(cae, sh_id)
        if not shd:
            log_warning("{} - AssCache guest object ID {} not found in Sihot: {}".format(ass_id, sh_id, as_co), ctx)
            continue

        if (ac_id or shd['MATCHCODE']) and ac_id != shd['MATCHCODE']:
            log_warning("{} - Acumen client reference mismatch. ass={}, sh={}".format(ass_id, ac_id, shd['MATCHCODE']),
                        ctx)
        if (sf_id or shd['MATCH-SM']) and sf_id != shd['MATCH-SM']:
            log_warning("{} - Salesforce contact ID mismatch. ass={} sh={}".format(ass_id, sf_id, shd['MATCH-SM']), ctx)

    log_warning("No Sihot discrepancies found" if len(warn_log) == cnt else "Number of Sihot discrepancies: {}"
                .format(len(warn_log) - cnt), ctx, importance=3)

    return ""


def sf_check_contacts():
    ctx = 'sfChkCo'
    cnt = len(warn_log)
    for as_co in conf_data.contacts:
        ass_id, ac_id, sf_id, sh_id, ext_refs, _ = as_co
        if not sf_id:
            if debug_level >= DEBUG_LEVEL_VERBOSE:
                log_warning("{} - AssCache contact record without Salesforce ID: {}".format(ass_id, as_co), ctx)
            continue

        sf_ass_id = sf_conn.contact_ass_id(sf_id)
        if ass_id != sf_ass_id:
            log_warning("{} - AssCache contact PKey mismatch. ass={}, sf={}".format(ass_id, ac_id, sf_ass_id), ctx)

        sf_ac_id = sf_conn.contact_ac_id(sf_id)
        if (ac_id or sf_ac_id) and ac_id != sf_ac_id:
            log_warning("{} - Acumen client reference mismatch. ass={}, sf={}".format(ass_id, ac_id, sf_ac_id), ctx)

        sf_sh_id = sf_conn.contact_sh_id(sf_id)
        if (sh_id or sf_sh_id) and sh_id != sf_sh_id:
            log_warning("{} - Salesforce contact ID mismatch. ass={} sf={}".format(ass_id, sh_id, sf_sh_id), ctx)

        ext_refs = [tuple(_.split('=')) for _ in ext_refs.split(EXT_REFS_SEP)] if ext_refs else list()
        sf_ext_refs = sf_conn.contact_ext_refs(sf_id)
        for er in ext_refs:
            if er not in sf_ext_refs:
                log_warning("{} - AssCache external reference {} missing in Salesforce".format(ass_id, er), ctx)
        for er in sf_ext_refs:
            if er not in ext_refs:
                log_warning("{} - Salesforce external reference {} missing in AssCache".format(ass_id, er), ctx)

    log_warning("No Salesforce discrepancies found" if len(warn_log) == cnt else "Number of Salesforce discrepancies={}"
                .format(len(warn_log) - cnt), ctx, importance=3)

    return ""


if acm_veris:
    log_warning("Preparing data check/verification", 'veriCache', importance=4)
    # fetch all contacts from AssCache
    err = conf_data.co_fetch_all(where_group_order=acm_veri_filters['C'] if 'C' in acm_veri_filters else "")
    if err:
        log_error("Contact cache load error: " + err, 'veriCache', importance=3, exit_code=300, dbs=[ass_db,  acu_db])
    # verify AssCache contact integrity
    if [_ for _ in acm_veris if _[2:] == 'C']:
        conf_data.co_check_ext_refs()
for acm_veri in acm_veris:
    if acm_veri[:2] == 'ac':
        if acm_veri[2:] == 'C':
            err = ac_check_contacts()
            if err:
                log_error(err, 'veriCacheAcContacts', importance=3, exit_code=303, dbs=[ass_db,  acu_db])
        elif acm_veri[2:] == 'P':
            log_error("Acumen Product Verification not implemented", 'veriCacheAcProd', importance=3, exit_code=330,
                      dbs=[ass_db,  acu_db])
        elif acm_veri[2:] == 'R':
            log_error("Acumen Reservation Verification not implemented", 'veriCacheAcRes', importance=3, exit_code=360,
                      dbs=[ass_db,  acu_db])

    elif acm_veri[:2] == 'sh':
        if acm_veri[2:] == 'C':
            err = sh_check_contacts()
            if err:
                log_error(err, 'veriCacheShContacts', importance=3, exit_code=402, dbs=[ass_db,  acu_db])
        else:
            log_error("Sihot veri. not implemented", 'veriCacheSh', importance=3, exit_code=495, dbs=[ass_db,  acu_db])

    elif acm_veri[:2] == 'sf':
        if acm_veri[2:] == 'C':
            err = sf_check_contacts()
            if err:
                log_error(err, 'veriCacheSfContacts', importance=3, exit_code=501, dbs=[ass_db,  acu_db])
        else:
            log_error("Salesforce verification not implemented", 'veriCacheSf', importance=3, exit_code=591,
                      dbs=[ass_db,  acu_db])


if acu_db:
    acu_db.close()
ass_db.close()
cae.shutdown(send_notification(42 if error_log else 0))
