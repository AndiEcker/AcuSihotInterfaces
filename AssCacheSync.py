"""
    AssCacheSync is a tool for to initialize, check, migrate and sync data between Acumen, Sihot, Salesforce
    and the ass_cache PostGreSQL database.

    0.1     first beta.
"""
import datetime
import pprint

from ae_console_app import ConsoleApp, uprint
from ae_db import PostgresDB
from shif import ResBulkFetcher, get_col_val, get_pax_count, SIHOT_DATE_FORMAT, get_res_obj_id, get_apt_wk_yr
from sfif import prepare_connection
from acu_sf_sh_sys_data import AssSysData
from ae_notification import Notification

__version__ = '0.1'

startup_date = datetime.date.today()

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)

cae = ConsoleApp(__version__, "Initialize, migrate and sync data from Acumen, Sihot and Salesforce into PG database")

rbf = ResBulkFetcher(cae)
rbf.add_options()

cae.add_option('initializeCache', "Initialize/Wipe/Recreate postgres cache database (0=No, 1=Yes)", 0, 'I')
cae.add_option('syncCache', "Synchronize postgres cache database (0=No-only check, 1=Yes)", 0, 'S')

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

rbf.load_config()
rbf.print_config()

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
if cae.get_option('initializeCache'):
    log_warning("creating data base {} and user {}".format(pg_dsn, pg_user), 'initializeCache-createDBandUser')
    pg_db = PostgresDB(usr='postgres', pwd=cae.get_config('pgRootPw'), dsn='postgres', debug_level=debug_level)
    if pg_db.create_db(pg_dsn):
        log_error(pg_db.last_err_msg, 'initializeCache-createDB', exit_code=72)

    if pg_db.select('pg_user', 'count(*)', "usename = :pg_user", dict(pg_user=pg_user)):
        log_error(pg_db.last_err_msg, 'initializeCache-checkUser', exit_code=81)
    if not pg_db.fetch_value():
        if pg_db.execute_sql("CREATE USER " + pg_user + " WITH PASSWORD '" + pg_pw + "';", commit=True):
            log_error(pg_db.last_err_msg, 'initializeCache-createUser', exit_code=84)
        if pg_db.execute_sql("GRANT ALL PRIVILEGES ON DATABASE " + pg_dsn + " to " + pg_user + ";", commit=True):
            log_error(pg_db.last_err_msg, 'initializeCache-grantUser', exit_code=87)
    pg_db.close()

    log_warning("table creation", 'initializeCache-createTable')
    ass_db = PostgresDB(usr=pg_user, pwd=pg_pw, dsn=pg_dsn, debug_level=debug_level)
    if ass_db.connect():
        log_error(pg_db.last_err_msg, 'initializeCache-ctConnect', exit_code=90)
    if ass_db.execute_sql(open("sql/pg_create_schema.sql", "r").read(), commit=True):
        log_error(pg_db.last_err_msg, 'initializeCache-ctScript', exit_code=93)
else:
    ass_db = PostgresDB(usr=pg_user, pwd=pg_pw, dsn=pg_dsn, debug_level=debug_level)


# logon to and prepare Acumen, Salesforce, Sihot and config data env
conf_data = AssSysData(cae, acu_user=acu_user, acu_password=acu_password, ass_user=pg_user, ass_password=pg_pw,
                       err_logger=log_error, warn_logger=log_warning)
if conf_data.error_message:
    log_error(conf_data.error_message, 'UserLogOn', importance=4, exit_code=9)


def migrate_product_types():
    products = conf_data.load_view(None, 'T_RS', ['RS_CODE', 'RS_SIHOT_GUEST_TYPE', 'RS_NAME'],
                                   "RS_CLASS = 'CONSTRUCT' or RS_SIHOT_GUEST_TYPE is not NULL")
    if not products:
        return conf_data.error_message
    for pr in products:
        if ass_db.insert('product_types', dict(pt_pk=pr[0], pt_group=pr[1], pt_name=pr[2])):
            ass_db.rollback()
            return ass_db.last_err_msg

    if ass_db.insert('product_types', dict(pt_pk='HMF', pt_group='I', pt_name="HMC Fractional")):
        ass_db.rollback()
        return ass_db.last_err_msg

    ass_db.commit()
    return ""


def migrate_contacts():
    """ migrate contacts from Acumen and Salesforce into ass_cache/postgres """

    # fetch all couple-contacts from Acumen
    log_warning("Fetching couple contact data from Acumen (needs some minutes)", 'FetchCoupleContacts', importance=4)
    a_c = conf_data.load_view(None, 'T_CD',
                              ["CD_CODE", "CD_SIHOT_OBJID", "CD_SF_ID1", "CD_RCI_REF"],
                              "substr(CD_CODE, 1, 1) <> 'A' and CD_SNAM1 is not NULL and CD_FNAM1 is not NULL")
    if not a_c:
        return conf_data.error_message
    a_2 = conf_data.load_view(None, 'T_CD',
                              ["CD_CODE || 'P2'", "CD_SIHOT_OBJID2", "CD_SF_ID2", "NULL"],
                              "substr(CD_CODE, 1, 1) <> 'A' and CD_SNAM2 is not NULL and CD_FNAM2 is not NULL")
    if not a_2:
        return conf_data.error_message
    a_c += a_2

    # migrate to ass_cache including additional external IDs and owned products
    for cont in a_c:
        if ass_db.insert('contacts', dict(co_sf_contact_id=cont[2], co_sh_guest_id=cont[1], co_sh_match_code=cont[0]),
                         returning_column='co_pk'):
            break
        co_pk = ass_db.fetch_value()
        ers = conf_data.load_view(None, 'T_CR', ['CR_TYPE', 'CR_REF'], "CR_CDREF = :acu_id", dict(acu_id=cont[0]))
        if not ers:
            break
        for er in ers:
            if ass_db.insert('external_refs', dict(er_co_fk=co_pk, er_type=er[0], er_id=er[1])):
                break
        prs = conf_data.load_view(None, 'V_OWNED_WEEKS INNER JOIN T_RS ON AT_RSREF = RS_CODE',
                                  ['DW_WKREF', 'AT_RSREF'],
                                  "DW_OWREF = :acu_id and RS_SIHOT_GUEST_TYPE is not NULL", dict(acu_id=cont[0]))
        if not prs:
            break
        for cp in prs:
            if ass_db.insert('products', dict(pr_pk=cp[0], pr_pt_fk=cp[1])):
                break
            if ass_db.insert('contact_products', dict(cp_co_fk=co_pk, cp_pr_fk=cp[0])):
                break
    if ass_db.last_err_msg:
        ass_db.rollback()
        return ass_db.last_err_msg
    elif conf_data.error_message:
        ass_db.rollback()
        return conf_data.error_message
    ass_db.commit()

    # TODO: fetch from Salesforce all contacts/clients and migrate/merge into ass_cache database

    return ""


def migrate_res_inv():
    log_warning("Fetching reservation inventory from Acumen (needs some minutes)", 'FetchResInv', importance=4)
    r_i = conf_data.load_view(None, 'T_AOWN_VIEW INNER JOIN T_WK ON AOWN_WKREF = WK_CODE'
                                    ' LEFT OUTER JOIN V_OWNED_WEEKS ON AOWN_WKREF = DW_WKREF',
                              ['AOWN_WKREF',
                               "(select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTEL' and LU_ID = AOWN_RSREF)",
                               'AOWN_YEAR', 'AOWN_ROREF', 'AOWN_SWAPPED_WITH', 'AOWN_GRANTED_TO',
                               'nvl(DW_POINTS, WK_POINTS)'],
                              "AOWN_YEAR >= to_char(sysdate, 'YYYY') and AOWN_RSREF in ('BHC', 'BHH', 'HMC', 'PBC')")
    for inv in r_i:
        if ass_db.insert('res_inventories',
                         dict(ri_pr_fk=inv[0], ri_hotel_id=inv[1], ri_usage_year=inv[2], ri_inv_type=inv[3],
                              ri_swapped_product_id=inv[4], ri_granted_to=inv[5], ri_used_points=inv[6])):
            ass_db.rollback()
            return ass_db.last_err_msg
        # ri_pk = ass_db.fetch_value()

    ass_db.commit()
    return ""


def migrate_res_data():
    log_warning("Fetching reservation data from Sihot/Acumen (needs some minutes)", 'FetchResData', importance=4)

    for rg in rbf_groups:
        rgr_pk = get_res_obj_id(rg)
        g_id = get_col_val(rg, 'GUEST-ID', arri=0)
        if ass_db.select('contacts', ['co_pk'], "co_sh_guest_id = :g_id", dict(g_id=g_id)):
            ass_db.rollback()
            return ass_db.last_err_msg
        ord_co_pk = ass_db.fetch_value()

        for arri in range(get_pax_count(rg)):
            g_id = get_col_val(rg, 'GUEST-ID', arri=arri+1)
            occ_co_pk = None
            if g_id:
                if ass_db.select('contacts', ['co_pk'], "co_sh_guest_id = :g_id", dict(g_id=g_id)):
                    ass_db.rollback()
                    return ass_db.last_err_msg
                occ_co_pk = ass_db.fetch_value()
            ad = dict(rgc_rgr_fk=rgr_pk,
                      rgc_surname=get_col_val(rg, 'NAME', arri=arri),
                      rgc_firstname=get_col_val(rg, 'NAME2', arri=arri),
                      rgc_auto_generated=get_col_val(rg, 'AUTO-GENERATED', arri=arri),
                      rgc_occup_co_fk=occ_co_pk,
                      rgc_room_seq=int(get_col_val(rg, 'ROOM-SEQ', arri=arri)),
                      rgc_pers_seq=int(get_col_val(rg, 'ROOM-PERS-SEQ', arri=arri)),
                      rgc_pers_type=get_col_val(rg, 'PERS-TYPE', arri=arri),
                      rgc_sh_pack=get_col_val(rg, 'R', arri=arri),
                      rgc_room_id=get_col_val(rg, 'RN', arri=arri),
                      rgc_dob=datetime.datetime.strptime(get_col_val(rg, 'DOB', arri=arri), SIHOT_DATE_FORMAT)
                      )
            if ass_db.insert('res_group_contacts', ad):
                ass_db.rollback()
                return ass_db.last_err_msg

        apt, wk, year = get_apt_wk_yr(rg, cae)
        if ass_db.select('res_inventories', ['ri_pk'], "ri_pk = :aw and ri_usage_year = :y", dict(aw=apt_wk, y=year)):
            ass_db.rollback()
            return ass_db.last_err_msg

        ad = dict(rgr_pk=rgr_pk,
                  rgr_order_co_fk=ord_co_pk,
                  rgr_used_ri_fk
                  rgr_rci_deposit_ri_fk
                  rgr_sh_gds_id
                  rgr_sh_res_id
                  rgr_arrival
                  rgr_departure
                  rgr_status
                  rgr_adults
                  rgr_children
                  rgr_mkt_segment
                  rgr_hotel_id
                  rgr_room_cat_id
                  rgr_sh_rate
                  rgr_sh_pack
                  rgr_payment_inst
                  rgr_ext_book_id
                  rgr_ext_book_day
                  rgr_flight_arr_airport
                  rgr_flight_arr_number
                  rgr_flight_arr_time
                  rgr_flight_pickup
                  rgr_flight_dep_airport
                  rgr_flight_dep_number
                  rgr_flight_dep_time
                  rgr_comment
                  rgr_long_comment
                  rgr_time_in
                  rgr_time_out
                  rgr_created_by
                  rgr_created_when
                  rgr_last_change
                  rgr_last_sync
                  )

        # complete Sihot data with Acumen data (check-in/-out time...)
        a_r = conf_data.load_view(None, 'T_ARO',
                                  ['ARO_TIMEIN', 'ARO_TIMEOUT'],
                                  "RU_CODE = :gds_no")
        if ass_db.insert('res_groups', ad):
            ass_db.rollback()
            return ass_db.last_err_msg

    ass_db.commit()
    return ""


# synchronize from Sihot or check the cached data against Sihot data
rbf_groups = rbf.fetch_all()
if cae.get_option('syncCache'):
    log_warning("product types synchronization/migration", 'syncCache-productTypes')
    err = migrate_product_types()
    if err:
        log_error(err, 'syncCache-productTypes', importance=3, exit_code=111)

    log_warning("contact data synchronization/migration", 'syncCache-contacts')
    err = migrate_contacts()
    if err:
        log_error(err, 'syncCache-contacts', importance=3, exit_code=111)

    log_warning("reservation inventory data synchronization/migration", 'syncCache-resInv')
    err = migrate_res_inv()  # load reservation inventory data
    if err:
        log_error(err, 'syncCache-resInv', importance=3, exit_code=114)

    log_warning("reservation booking data synchronization/migration", 'syncCache-resData')
    err = migrate_res_data()  # load reservation booking data
    if err:
        log_error(err, 'syncCache-resData', importance=3, exit_code=114)

else:
    log_warning("product type data check", 'checkCache')
    log_warning("contact data check", 'checkCache')
    log_warning("reservation inventory data check", 'checkCache')
    log_warning("reservation booking data check", 'checkCache')


ass_db.close()
cae.shutdown(send_notification(42 if error_log else 0))
