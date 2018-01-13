"""
    AssCacheSync is a tool for to initialize, check, migrate and sync data between Acumen, Sihot, Salesforce
    and the ass_cache PostGreSQL database.

    0.1     first beta.
"""
import datetime
import time
import re
from traceback import print_exc
import pprint

from copy import deepcopy

import psycopg2

from ae_console_app import ConsoleApp, uprint, DATE_ISO, DEBUG_LEVEL_VERBOSE
from ae_db import ACU_DEF_USR, ACU_DEF_DSN
from sxmlif import ResSearch, SXML_DEF_ENCODING, PARSE_ONLY_TAG_PREFIX
from sfif import prepare_connection, CONTACT_REC_TYPE_RENTALS, correct_email, correct_phone
from acu_sf_sh_sys_data import AssSysData
from ae_notification import Notification

__version__ = '0.1'

startup_date = datetime.date.today()

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)

cae = ConsoleApp(__version__, "Initialize, migrate and sync data from Acumen, Sihot and Salesforce into PG database")
cae.add_option('initializeCache', "Initialize/Wipe/Recreate postgres cache database (0=No, 1=Yes)", 0, 'I')
cae.add_option('syncCache', "Synchronize postgres cache database (0=No-only check, 1=Yes)", 0, 'S')

cae.add_option('dateFrom', "Date of first arrival to be migrated", startup_date - datetime.timedelta(days=1), 'F')
cae.add_option('dateTill', "Date of last arrival to be migrated", startup_date - datetime.timedelta(days=1), 'T')

cae.add_option('acuUser', "User name of Acumen/Oracle system", ACU_DEF_USR, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", ACU_DEF_DSN, 'd')

cae.add_option('pgUser', "User account name for ass_cache postgres cache database", 'postgres', 'U')
cae.add_option('pgPassword', "User account password for ass_cache postgres cache database", '', 'P')

cae.add_option('sfUser', "Salesforce account user name", '', 'y')
cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
cae.add_option('sfToken', "Salesforce account token string", '', 'o')
cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')

cae.add_option('serverIP', "IP address of the Sihot interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the Sihot WEB interface", 14777, 'w')
cae.add_option('timeout', "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
cae.add_option('xmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", list(), 'r')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", list(), 'v')

debug_level = cae.get_option('debugLevel')

acu_user = cae.get_option('acuUser')
acu_password = cae.get_option('acuPassword')
uprint("Acumen user/DSN:", acu_user, cae.get_option('acuDSN'))

pg_user = cae.get_option('pgUser')
pg_pw = cae.get_option('pgPassword')
uprint("AssCache DB user:", pg_user)

uprint("Sihot Server IP/Web-port:", cae.get_option('serverIP'), cae.get_option('serverPort'))
uprint("Sihot TCP Timeout/XML Encoding:", cae.get_option('timeout'), cae.get_option('xmlEncoding'))

date_from = cae.get_option('dateFrom')
date_till = cae.get_option('dateTill')
uprint("Date range including check-ins from", date_from.strftime(DATE_ISO),
       'and till/before', date_till.strftime(DATE_ISO))
if date_from > date_till:
    uprint("Specified date range is invalid - dateFrom({}) has to be before dateTill({}).".format(date_from, date_till))
    cae.shutdown(18)
elif date_till > startup_date:
    uprint("Future arrivals cannot be migrated - dateTill({}) has to be before {}.".format(date_till, startup_date))
    cae.shutdown(19)
# fetch given date range in chunks for to prevent timeouts and Sihot server blocking issues
sh_fetch_max_days = min(max(1, cae.get_config('shFetchMaxDays', default_value=7)), 31)
sh_fetch_pause_seconds = cae.get_config('shFetchPauseSeconds', default_value=1)
uprint("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", sh_fetch_max_days,
       " and -pause in seconds between fetches", sh_fetch_pause_seconds)

search_flags = cae.get_config('ResSearchFlags', default_value='ALL-HOTELS')
uprint("Search flags:", search_flags)
search_scope = cae.get_config('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')
uprint("Search scope:", search_scope)

allowed_mkt_src = cae.get_config('MarketSources', default_value=list())
uprint("Allowed Market Sources:", allowed_mkt_src)

sf_conn, sf_sandbox = prepare_connection(cae)
if not sf_conn:
    uprint("Salesforce account connection could not be established - please check your account data and credentials")
    cae.shutdown(20)

notification = warning_notification_emails = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system=cae.get_option('serverIP') + '/Salesforce ' + ("sandbox" if sf_sandbox
                                                                                           else "production"),
                                debug_level=cae.get_option('debugLevel'))
    uprint("SMTP Uri/From/To:", cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    warning_notification_emails = cae.get_option('warningsMailToAddr')
    if warning_notification_emails:
        uprint("Warnings SMTP receiver address(es):", warning_notification_emails)


# LOGGING HELPERS
error_log = list()
import_log = list()


def log_error(msg, ctx, line=-1, importance=2):
    error_log.append(dict(message=msg, context=ctx, line=line + 1))
    import_log.append(dict(message=msg, context=ctx, line=line + 1))
    msg = ' ' * (4 - importance) + '*' * importance + '  ' + msg
    uprint(msg)


def log_warning(msg, ctx, line=-1, importance=2):
    seps = '\n' * (importance - 2)
    import_log.append(dict(message=seps + msg, context=ctx, line=line + 1))
    msg = seps + ' ' * (4 - importance) + '#' * importance + '  ' + msg
    uprint(msg)


# logon to and prepare Acumen, Salesforce, Sihot and config data env
conf_data = AssSysData(cae, acu_user=acu_user, acu_password=acu_password,
                       err_logger=log_error, warn_logger=log_warning)
if conf_data.error_message:
    log_error(conf_data.error_message, 'UserLogOn', importance=4)
    cae.shutdown(9)


# check for to (re-)create and initialize PG database
if cae.get_option('initializeCache'):
    conn = None
    try:
        conn = psycopg2.connect(dbname='postgres', user=pg_user, password=pg_pw)
        log_warning("DB creation. Server-Version={}, API-level={}".format(conn.server_version, psycopg2.apilevel),
                    'initializeCache')
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        curs = conn.cursor()
        curs.execute("CREATE DATABASE ass_cache;")  # " LC_COLLATE 'C'")
        curs.close()
        conn.close()

        conn = psycopg2.connect(dbname='ass_cache', user=pg_user, password=pg_pw)
        log_warning("table creation", 'initializeCache')
        curs = conn.cursor()
        curs.execute(open("sql/pg_create_schema.sql", "r").read())
        curs.close()
        conn.commit()

        log_warning("core data migration", 'initializeCache')
        curs = conn.cursor()
        curs.execute("INSERT INTO contacts(co_sf_contact_id, co_sh_guest_id, co_sh_match_code)"
                     " VALUES(%s, %s, %s) RETURNING co_pk;", ('sf_id', 'guest_id', 'matchcode'))
        co_pk = curs.fetchone()[0]
        log_warning("pk of contact={}".format(co_pk), 'initializeCache', importance=1)
        conn.commit()
        curs.close()

        # test named bind parameters
        curs = conn.cursor()
        print(curs.mogrify("SELECT * from contacts where co_pk = :pk", dict(pk=co_pk)))
        print(curs.mogrify("SELECT * from contacts where co_pk = %(pk)s", dict(pk=co_pk)))
        # results in "syntax error at or near ":"": curs.execute("SELECT * from contacts where co_pk = :pk", dict(pk=co_pk))
        curs.execute("SELECT * from contacts where co_pk = %(pk)s and co_pk = %(pk)s", dict(pk=co_pk))
        print(curs.fetchall())

    except (Exception, psycopg2.DatabaseError) as err:
        log_error("DB initialization error: {}".format(err), 'initializeCache', importance=4)
        cae.shutdown(3)
    finally:
        if conn is not None:
            conn.close()
