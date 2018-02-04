"""
    AssCacheSync is a tool for to initialize, check, migrate and sync data between Acumen, Sihot, Salesforce
    and the ass_cache PostGreSQL database.

    0.1     first beta.
"""
import datetime
import pprint
from collections import OrderedDict

from ae_console_app import ConsoleApp, uprint
from ae_db import PostgresDB
from shif import ResBulkFetcher, elem_value, get_pax_count, get_gds_no, get_apt_wk_yr, elem_path_join, \
    SIHOT_DATE_FORMAT
from sfif import prepare_connection
from acu_sf_sh_sys_data import AssSysData
from ae_notification import Notification
from sxmlif import ResToSihot

__version__ = '0.1'

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)

cae = ConsoleApp(__version__, "Initialize, migrate and sync data from Acumen, Sihot and Salesforce into PG cache")

sh_rbf = ResBulkFetcher(cae)
sh_rbf.add_options()

cae.add_option('initializeCache', "Initialize/Wipe/Recreate ass_cache database (0=No, 1=Yes)", 0, 'I')
cae.add_option('syncCache', "Synchronize from (ac=Acumen, sh=Sihot, sf=Salesforce)"
                            " including (A=all, P=Product, R=Reservations)", '', 'S',
               choices=('acA', 'acP', 'acC', 'acR', 'shA', 'shR', 'sfA'))
cae.add_option('verifyCache', "Verify/Check against (ac=Acumen, sh=Sihot, sf=Salesforce)"
                              " including (A=all, P=Product, R=Reservations)", '', 'V',
               choices=('acA', 'acP', 'acC', 'acR', 'shA', 'shR', 'sfA'))

cae.add_option('acuUser', "User name of Acumen/Oracle system", '', 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", '', 'd')

cae.add_option('pgUser', "User account name for the postgres cache database", '', 'U')
cae.add_option('pgPassword', "User account password for the postgres cache database", '', 'P')
cae.add_option('pgDSN', "Database name of the postgres cache database", 'ass_cache', 'N')

cae.add_option('sfUser', "Salesforce account user name", '', 'y')
cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
cae.add_option('sfToken', "Salesforce account token string", '', 'o')
cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", list(), 'r')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", list(), 'v')

debug_level = cae.get_option('debugLevel')

acm_init = cae.get_option('initializeCache')
acm_sync = cae.get_option('syncCache')
acm_veri = cae.get_option('verifyCache')
uprint("Mode/Actions: ",
       "initialize" if acm_init else "",
       "sync from Acumen" if acm_sync[:2] == 'ac' else "",
       "sync from Sihot" if acm_sync[:2] == 'sh' else "",
       "sync from Salesforce" if acm_sync[:2] == 'sf' else "",
       "including" + (" Products" if acm_sync[2:] in 'AP' else "")
       + (" Contacts" if acm_sync[2:] in 'AC' else "")
       + (" Reservations" if acm_sync[2:] in 'AR' else "") if acm_sync else "",
       "verify against Acumen" if acm_veri[:2] == 'ac' else "",
       "verify against Sihot" if acm_veri[:2] == 'sh' else "",
       "verify against Salesforce" if acm_veri[:2] == 'sf' else "",
       "including" + (" Products" if acm_veri[2:] in 'AP' else "")
       + (" Contacts" if acm_veri[2:] in 'AC' else "")
       + (" Reservations" if acm_veri[2:] in 'AR' else "") if acm_veri else "")

sh_rbf.load_config()
sh_rbf.print_config()

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
        mail_body = "\n\n".join(import_log)
        send_err = notification.send_notification(mail_body, subject=subject)
        if send_err:
            uprint("****  {} send error: {}. mail-body='{}'.".format(subject, send_err, mail_body))
            if not exit_code:
                exit_code = 36
        if warning_notification_emails and error_log:
            mail_body = "ERRORS:\n\n" + ("\n\n".join(error_log) if error_log else "NONE") \
                + "\n\nPROTOCOL:\n\n" + ("\n\n".join(import_log) if import_log else "NONE")
            subject = "AssCacheSync Errors"
            send_err = notification.send_notification(mail_body, subject=subject, mail_to=warning_notification_emails)
            if send_err:
                uprint("****  {} warning send error: {}. mail-body='{}'.".format(subject, send_err, mail_body))
                if not exit_code:
                    exit_code = 39
    return exit_code


# LOGGING HELPERS
error_log = list()
import_log = list()


def log_error(msg, ctx, importance=2, exit_code=0):
    msg = " " * (4 - importance) + "*" * importance + "  " + ctx + "   " + msg
    error_log.append(msg)
    import_log.append(msg)
    uprint(msg)
    if exit_code:
        cae.shutdown(send_notification(exit_code))


def log_warning(msg, ctx, importance=2):
    seps = '\n' * (importance - 2)
    msg = seps + " " * (4 - importance) + "#" * importance + "  " + ctx + "   " + msg
    import_log.append(msg)
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
conf_data = AssSysData(cae, acu_user=acu_user, acu_password=acu_password, ass_user=pg_user, ass_password=pg_pw,
                       err_logger=log_error, warn_logger=log_warning)
if conf_data.error_message:
    log_error(conf_data.error_message, 'AcuUserLogOn', importance=4, exit_code=9)

# logon to and prepare ass_cache database
ass_db = PostgresDB(usr=pg_user, pwd=pg_pw, dsn=pg_dsn, debug_level=debug_level)
if ass_db.connect():
    log_error(ass_db.last_err_msg, 'PgUserLogOn', exit_code=12)


def ac_migrate_product_types():
    log_warning("Acumen product types synchronization/migration", 'syncCacheAcuProductTypes', importance=3)
    products = conf_data.load_view(None, 'T_RS', ['RS_CODE', 'RS_SIHOT_GUEST_TYPE', 'RS_NAME'],
                                   "RS_CLASS = 'CONSTRUCT' or RS_SIHOT_GUEST_TYPE is not NULL")
    if products is None:
        return conf_data.error_message
    for pr in products:
        if ass_db.upsert('product_types', OrderedDict([('pt_pk', pr[0]), ('pt_group', pr[1]), ('pt_name', pr[2])])):
            ass_db.rollback()
            return ass_db.last_err_msg

    if ass_db.upsert('product_types', OrderedDict([('pt_pk', 'HMF'), ('pt_group', 'I'), ('pt_name', "HMC Fraction")])):
        ass_db.rollback()
        return ass_db.last_err_msg

    ass_db.commit()
    return ""


def ac_migrate_contacts():
    """ migrate contacts from Acumen and Salesforce into ass_cache/postgres """

    # fetch all couple-contacts from Acumen
    log_warning("Fetching couple contact data from Acumen (needs some minutes)", 'FetchAcuCoupleContacts', importance=3)
    a_c = conf_data.load_view(None, 'T_CD',
                              ["CD_CODE", "to_char(CD_SIHOT_OBJID)", "CD_SF_ID1", "CD_RCI_REF"],
                              "substr(CD_CODE, 1, 1) <> 'A' and CD_SNAM1 is not NULL and CD_FNAM1 is not NULL")
    if a_c is None:
        return conf_data.error_message
    a_2 = conf_data.load_view(None, 'T_CD',
                              ["CD_CODE || 'P2'", "to_char(CD_SIHOT_OBJID2)", "CD_SF_ID2", "NULL"],
                              "substr(CD_CODE, 1, 1) <> 'A' and CD_SNAM2 is not NULL and CD_FNAM2 is not NULL")
    if a_2 is None:
        return conf_data.error_message
    a_c += a_2
    a_c.sort(key=lambda _: _[0])

    # migrate to ass_cache including additional external IDs and owned products
    for idx, cont in enumerate(a_c):
        col_values = dict(co_sf_id=cont[2], co_sh_id=cont[1], co_ac_id=cont[0])
        if ass_db.upsert('contacts', col_values, chk_values=col_values, returning_column='co_pk'):
            break
        co_pk = ass_db.fetch_value()

        ers = conf_data.load_view(None, 'T_CR', ['CR_TYPE', 'CR_REF'], "CR_CDREF = :acu_id", dict(acu_id=cont[0]))
        if ers is None:
            break
        if cont[3]:
            ers.insert(0, 'RCI', cont[3])
        for er in ers:
            col_values = dict(er_co_fk=co_pk, er_type=er[0], er_id=er[1])
            if ass_db.upsert('external_refs', col_values, chk_values=col_values):
                break
        if ass_db.last_err_msg:
            break

        prs = conf_data.load_view(None, 'V_OWNED_WEEKS INNER JOIN T_RS ON AT_RSREF = RS_CODE',
                                  ['DW_WKREF', 'AT_RSREF'],
                                  "DW_OWREF = :acu_id and RS_SIHOT_GUEST_TYPE is not NULL", dict(acu_id=cont[0]))
        if prs is None:
            break
        for cp in prs:
            if ass_db.upsert('products', OrderedDict([('pr_pk', cp[0]), ('pr_pt_fk', cp[1])])):
                break
            col_values = dict(cp_co_fk=co_pk, cp_pr_fk=cp[0])
            if ass_db.upsert('contact_products', col_values, chk_values=col_values):
                break
        if ass_db.last_err_msg:
            break

        if idx + 1 % 1000 == 0:
            ass_db.commit()

    if ass_db.last_err_msg:
        ass_db.rollback()
        return ass_db.last_err_msg
    elif conf_data.error_message:
        ass_db.rollback()
        return conf_data.error_message
    ass_db.commit()

    return ""


def ac_migrate_res_inv():
    log_warning("Fetching reservation inventory from Acumen (needs some minutes)", 'FetchAcuResInv', importance=3)
    r_i = conf_data.load_view(None, 'T_AOWN_VIEW INNER JOIN T_WK ON AOWN_WKREF = WK_CODE'
                                    ' LEFT OUTER JOIN V_OWNED_WEEKS ON AOWN_WKREF = DW_WKREF',
                              ["case when AOWN_RSREF = 'PBC' and length(AOWN_APREF) = 3 then '0' end || AOWN_WKREF",
                               "(select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTEL' and LU_ID = AOWN_RSREF)",
                               'AOWN_YEAR', 'AOWN_ROREF', 'AOWN_SWAPPED_WITH', 'AOWN_GRANTED_TO',
                               'nvl(POINTS, WK_POINTS)'],
                              "AOWN_YEAR >= to_char(sysdate, 'YYYY') and AOWN_RSREF in ('BHC', 'BHH', 'HMC', 'PBC')")
    if r_i is None:
        return conf_data.error_message
    for inv in r_i:
        if ass_db.upsert('res_inventories',
                         dict(ri_pr_fk=inv[0], ri_hotel_id=inv[1], ri_usage_year=inv[2], ri_inv_type=inv[3],
                              ri_swapped_product_id=inv[4], ri_granted_to=inv[5], ri_used_points=inv[6]),
                         chk_values=dict(ri_pr_fk=inv[0], ri_usage_year=inv[2])):
            ass_db.rollback()
            return ass_db.last_err_msg
        # ri_pk = ass_db.fetch_value()

    ass_db.commit()
    return ""


def ac_migrate_res_data():
    log_warning("Fetching reservation data from Acumen (needs some minutes)", 'FetchAcuResData', importance=3)
    acumen_req = ResToSihot(cae)
    error_msg = acumen_req.fetch_all_valid_from_acu(date_range='P')
    if error_msg:
        return error_msg
    for crow in acumen_req.rows:
        # determine orderer and occupants
        g_mc = crow['OC_CODE']
        if ass_db.select('contacts', ['co_pk'], "co_ac_id = :g_mc", dict(g_mc=g_mc)):
            ass_db.rollback()
            return ass_db.last_err_msg
        ord_co_pk = ass_db.fetch_value()
        if not ord_co_pk:
            g_id = crow['OC_SIHOT_OBJID']
            if ass_db.select('contacts', ['co_pk'], "co_sh_id = :g_id", dict(g_id=g_id)):
                ass_db.rollback()
                return ass_db.last_err_msg
            ord_co_pk = ass_db.fetch_value()

        # determine used reservation inventory
        year, week = conf_data.rc_arr_to_year_week(crow['ARR_DATE'])
        apt_wk = "{}-{:0>2}".format(crow['RUL_SIHOT_ROOM'], week)
        if ass_db.select('res_inventories', ['ri_pk'], "ri_pk = :aw and ri_usage_year = :y", dict(aw=apt_wk, y=year)):
            ass_db.rollback()
            return ass_db.last_err_msg
        ri_pk = ass_db.fetch_value()

        gds_no = crow['SIHOT_GDSNO']

        g_mc = crow['CD_CODE']
        a_c = conf_data.load_view(None, "T_CD", ['CD_SNAM1', 'CD_FNAM1', 'CD_DOB1', 'CD_SNAM2', 'CD_FNAM2', 'CD_DOB2'],
                                  "CD_CODE = :g_mc", dict(gds_no=gds_no))
        if a_c is None:
            return conf_data.error_message
        if ass_db.select('contacts', ['co_pk'], "co_ac_id = :g_mc", dict(g_mc=g_mc)):
            ass_db.rollback()
            return ass_db.last_err_msg
        occ_co_pk = ass_db.fetch_value()
        ad = dict(rgc_rgr_fk=gds_no,
                  rgc_surname=a_c['CD_SNAM1'],
                  rgc_firstname=a_c['CD_FNAM1'],
                  rgc_auto_generated='0',
                  rgc_occup_co_fk=occ_co_pk,
                  rgc_flight_arr_comment=crow['RU_FLIGHT_AIRPORT'] + " No=" + crow['RU_FLIGHT_NO'],
                  rgc_flight_arr_time=crow['RU_FLIGHT_LANDS'],
                  # occupation data
                  rgc_room_seq=0,
                  rgc_pers_seq=0,
                  rgc_pers_type='1A',
                  rgc_sh_pack=crow['RUL_SIHOT_PACK'],
                  rgc_room_id=crow['RUL_SIHOT_ROOM'],
                  rgc_dob=a_c['CD_DOB1']
                  )
        if ass_db.upsert('res_group_contacts', ad, chk_values=dict(rgc_rgr_fk=gds_no, rgc_room_seq=0, rgc_pers_seq=0)):
            ass_db.rollback()
            return ass_db.last_err_msg

        if ass_db.select('contacts', ['co_pk'], "co_ac_id = :g_mc", dict(g_mc=g_mc + 'P2')):
            ass_db.rollback()
            return ass_db.last_err_msg
        occ_co_pk = ass_db.fetch_value()
        ad['rgc_surname'] = a_c['CD_SNAM2']
        ad['rgc_surname'] = a_c['CD_SNAM2']
        ad['rgc_occup_co_fk'] = occ_co_pk
        ad['rgc_pers_seq'] = 1
        ad['rgc_dob'] = a_c['CD_DOB2']
        if ass_db.upsert('res_group_contacts', ad, chk_values=dict(rgc_rgr_fk=gds_no, rgc_room_seq=0, rgc_pers_seq=1)):
            ass_db.rollback()
            return ass_db.last_err_msg

        # complete with check-in/-out time...
        a_r = conf_data.load_view(None,
                                  "T_ARO INNER JOIN T_RU ON ARO_RHREF = RU_RHREF and ARO_EXP_ARRIVE = RU_FROM_DATE",
                                  ['ARO_TIMEIN', 'ARO_TIMEOUT'],
                                  "ARO_STATUS <> 120 and RU_STATUS <> 120 and RU_CODE = :gds_no",
                                  dict(gds_no=gds_no))
        if a_r is None:
            return conf_data.error_message
        elif not a_r:
            a_r = (None, None)
        crow['TIMEIN'], crow['TIMEOUT'] = a_r

        ad = dict(rgr_pk=gds_no,
                  rgr_order_co_fk=ord_co_pk,
                  rgr_used_ri_fk=ri_pk,
                  rgr_arrival=crow['ARR_DATE'],
                  rgr_departure=crow['DEP_DATE'],
                  rgr_status=crow['SIHOT_RES_TYPE'],
                  rgr_adults=crow['RU_ADULTS'],
                  rgr_children=crow['RU_CHILDREN'],
                  rgr_mkt_segment=crow['SIHOT_MKT_SEG'],
                  rgr_mkt_group=crow['RO_SIHOT_RES_GROUP'],
                  rgr_hotel_id=crow['RUL_SIHOT_HOTEL'],
                  rgr_room_cat_id=crow['RUL_SIHOT_CAT'],
                  rgr_sh_rate=crow['RUL_SIHOT_RATE'],
                  rgr_ext_book_id=crow['RH_EXT_BOOK_REF'],
                  rgr_ext_book_day=crow['RH_EXT_BOOK_DATE'],
                  rgr_comment=crow['SIHOT_NOTE'],
                  rgr_long_comment=crow['SIHOT_TEC_NOTE'],
                  rgr_time_in=a_r[0],
                  rgr_time_out=a_r[1],
                  rgr_created_by=pg_user,
                  rgr_created_when=cae.startup_beg,
                  rgr_last_change=cae.startup_beg,
                  rgr_last_sync=cae.startup_beg
                  )

        if ass_db.upsert('res_groups', ad, chk_values=dict(rgr_pk=gds_no)):
            ass_db.rollback()
            return ass_db.last_err_msg

    ass_db.commit()
    return ""


def sh_migrate_res_data():
    log_warning("Fetching reservation data from Sihot (needs some minutes)", 'FetchShResData', importance=3)
    rbf_groups = sh_rbf.fetch_all()
    for rg in rbf_groups:
        g_mc = elem_value(rg, elem_path_join(['RESCHANNELLIST', 'RESCHANNEL', 'MATCHCODE']), arri=0)
        if ass_db.select('contacts', ['co_pk'], "co_ac_id = :g_mc", dict(g_mc=g_mc)):
            ass_db.rollback()
            return ass_db.last_err_msg
        ord_co_pk = ass_db.fetch_value()
        if not ord_co_pk:
            g_id = elem_value(rg, elem_path_join(['RESCHANNELLIST', 'RESCHANNEL', 'OBJID']), arri=0)
            if ass_db.select('contacts', ['co_pk'], "co_sh_id = :g_id", dict(g_id=g_id)):
                ass_db.rollback()
                return ass_db.last_err_msg
            ord_co_pk = ass_db.fetch_value()

        gds_no = get_gds_no(rg)
        for arri in range(get_pax_count(rg)):
            g_mc = elem_value(rg, elem_path_join(['PERSON', 'MATCHCODE']), arri=arri)
            occ_co_pk = None
            if g_mc:
                if ass_db.select('contacts', ['co_pk'], "co_ac_id = :g_mc", dict(g_mc=g_mc)):
                    ass_db.rollback()
                    return ass_db.last_err_msg
                occ_co_pk = ass_db.fetch_value()
            room_seq = int(elem_value(rg, elem_path_join(['PERSON', 'ROOM-SEQ']), arri=arri))
            pers_seq = int(elem_value(rg, elem_path_join(['PERSON', 'ROOM-PERS-SEQ']), arri=arri))
            ad = dict(rgc_rgr_fk=gds_no,
                      rgc_surname=elem_value(rg, elem_path_join(['PERSON', 'NAME']), arri=arri),
                      rgc_firstname=elem_value(rg, elem_path_join(['PERSON', 'NAME2']), arri=arri),
                      rgc_auto_generated=elem_value(rg, elem_path_join(['PERSON', 'AUTO-GENERATED']), arri=arri),
                      rgc_occup_co_fk=occ_co_pk,
                      # Sihot offers also PICKUP-TYPE-ARRIVAL(1=car, 2=van), we now use PICKUP-TIME-ARRIVAL instead of
                      # .. ARR-TIME for the flight arr/dep (pg converts str into time object/value)
                      rgc_flight_arr_comment=elem_value(rg, elem_path_join(['PERSON', 'PICKUP-COMMENT-ARRIVAL'])),
                      rgc_flight_arr_time=elem_value(rg, elem_path_join(['PERSON', 'PICKUP-TIME-ARRIVAL'])),
                      rgc_flight_dep_comment=elem_value(rg, elem_path_join(['PERSON', 'PICKUP-COMMENT-DEPARTURE'])),
                      rgc_flight_dep_time=elem_value(rg, elem_path_join(['PERSON', 'PICKUP-TIME-DEPARTURE'])),
                      # occupation data
                      rgc_room_seq=room_seq,
                      rgc_pers_seq=pers_seq,
                      rgc_pers_type=elem_value(rg, elem_path_join(['PERSON', 'PERS-TYPE']), arri=arri),
                      rgc_sh_pack=elem_value(rg, elem_path_join(['PERSON', 'R']), arri=arri),
                      rgc_room_id=elem_value(rg, elem_path_join(['PERSON', 'RN']), arri=arri),
                      rgc_dob=datetime.datetime.strptime(elem_value(rg, elem_path_join(['PERSON', 'DOB']), arri=arri),
                                                         SIHOT_DATE_FORMAT)
                      )
            if ass_db.upsert('res_group_contacts', ad,
                             chk_values=dict(rgc_rgr_fk=gds_no, rgc_room_seq=room_seq, rgc_pers_seq=pers_seq)):
                ass_db.rollback()
                return ass_db.last_err_msg

        apt, wk, year = get_apt_wk_yr(rg, cae)
        apt_wk = "{}-{:0>2}".format(apt, wk)
        if ass_db.select('res_inventories', ['ri_pk'], "ri_pk = :aw and ri_usage_year = :y", dict(aw=apt_wk, y=year)):
            ass_db.rollback()
            return ass_db.last_err_msg
        ri_pk = ass_db.fetch_value()

        ad = dict(rgr_pk=gds_no,
                  rgr_order_co_fk=ord_co_pk,
                  rgr_used_ri_fk=ri_pk,
                  rgr_sh_gds_id=gds_no,
                  rgr_sh_res_id=elem_value(rg, 'RES-NR') + '/' + elem_value(rg, 'SUB-NR'),
                  rgr_arrival=datetime.datetime.strptime(elem_value(rg, elem_path_join(['RESERVATION', 'ARR'])),
                                                         SIHOT_DATE_FORMAT),
                  rgr_departure=datetime.datetime.strptime(elem_value(rg, elem_path_join(['RESERVATION', 'DEP'])),
                                                           SIHOT_DATE_FORMAT),
                  rgr_status=elem_value(rg, 'RT'),
                  rgr_adults=elem_value(rg, 'NOPAX'),
                  rgr_children=elem_value(rg, 'NOCHILDS'),
                  rgr_mkt_segment=elem_value(rg, 'MARKETCODE'),
                  rgr_mkt_group=elem_value(rg, 'CHANNEL'),
                  rgr_hotel_id=elem_value(rg, 'RES-HOTEL'),  # hotel ID returned by RES-SEARCH (missing ID element)
                  rgr_room_cat_id=elem_value(rg, elem_path_join(['RESERVATION', 'CAT'])),
                  rgr_sh_rate=elem_value(rg, 'RATE-SEGMENT'),
                  rgr_ext_book_id=elem_value(rg, elem_path_join(['RESERVATION', 'VOUCHERNUMBER'])),
                  rgr_ext_book_day=elem_value(rg, 'SALES-DATE'),
                  rgr_comment=elem_value(rg, elem_path_join(['RESERVATION', 'COMMENT'])),
                  rgr_long_comment=elem_value(rg, 'TEC-COMMENT'),
                  rgr_created_by=pg_user,
                  rgr_created_when=cae.startup_beg,
                  rgr_last_change=cae.startup_beg,
                  rgr_last_sync=cae.startup_beg
                  )

        if ass_db.upsert('res_groups', ad, chk_values=dict(rgr_pk=gds_no)):
            ass_db.rollback()
            return ass_db.last_err_msg

    ass_db.commit()
    return ""


if acm_sync:
    log_warning("Starting data synchronization/migration", 'syncCache', importance=4)
if acm_sync[:2] == 'ac':
    if acm_sync[2:] in 'AP':
        err = ac_migrate_product_types()
        if err:
            log_error(err, 'syncCacheAcuProductTypes', importance=3, exit_code=111)
    if acm_sync[2:] in 'AC':
        err = ac_migrate_contacts()
        if err:
            log_error(err, 'syncCacheAcuContacts', importance=3, exit_code=114)
    if acm_sync[2:] in 'AR':
        err = ac_migrate_res_inv()  # load reservation inventory data
        if err:
            log_error(err, 'syncCacheAcuResInv', importance=3, exit_code=117)
        err = ac_migrate_res_data()
        if err:
            log_error(err, 'syncCacheAcuResData', importance=3, exit_code=120)

elif acm_sync[:2] == 'sh':
    if acm_sync[2:] in 'AR':
        err = sh_migrate_res_data()
        if err:
            log_error(err, 'syncCacheShResData', importance=3, exit_code=132)

elif acm_sync[:2] == 'sf':
    log_error("Salesforce synchronization not implemented", 'syncCacheSf', importance=3, exit_code=135)


def ac_check_contacts():
    if not ass_db.select('contacts'):
        return ass_db.last_err_msg
    contacts = ass_db.fetch_all()

    ca = conf_data.load_view(None, 'T_CD', ["CD_CODE",
                                            "to_char(CD_SIHOT_OBJID)", "CD_SF_ID1",
                                            "to_char(CD_SIHOT_OBJID2)", "CD_SF_ID2"],
                             "substr(CD_CODE, 1, 1) <> 'A'"
                             )
    if ca is None:
        return conf_data.error_message
    cad = dict((_[0], _[1:]) for _ in ca)

    dis = list()
    for co in contacts:
        if not co[3]:
            dis.append("Ass Cache Contact without Acumen client reference: {}".format(co))
        else:
            main_aci, offset = (co[3][:-2], 2) if co[3].endswith('P2') else (co[3], 0)
            if main_aci in cad:
                cat = cad[main_aci][offset:]
                if co[1] != cat[0]:     # co_sh_id
                    dis.append("{} - Sihot guest object ID differs: ass={} acu={}".format(co[3], co[1], cat[0]))
                if co[2] != cat[1]:     # co_sf_id
                    dis.append("{} - Salesforce contact ID differs: ass={} acu={}".format(co[3], co[2], cat[1]))
            else:
                dis.append("Acumen client references {} not found in Acumen system".format(co[3]))


if acm_veri:
    log_warning("Starting data check/verification", 'veriCache', importance=3)
if acm_veri[:2] == 'ac':
    if acm_sync[2:] in 'AC':
        err = ac_check_contacts()
        if err:
            log_error(err, 'veriCacheAcContacts', importance=3, exit_code=300)

elif acm_veri[:2] == 'sh':
    log_error("Sihot verification not implemented", 'veriCacheSh', importance=3, exit_code=171)

elif acm_veri[:2] == 'sf':
    log_error("Salesforce verification not implemented", 'syncCacheSf', importance=3, exit_code=192)


ass_db.close()
cae.shutdown(send_notification(42 if error_log else 0))
