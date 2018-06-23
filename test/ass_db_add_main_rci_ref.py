from ae_console_app import ConsoleApp, uprint
from ae_db import PostgresDB
from acif import add_ac_options
from ass_sys_data import AssSysData, EXT_REF_TYPE_RCI


__version__ = '0.1'

cae = ConsoleApp(__version__, "Extend ASS_DB with main Acumen RCI member ID")
add_ac_options(cae)

cae.add_option('assUser', "User account name for the AssCache/Postgres database", '', 'U')
cae.add_option('assPassword', "User account password for the AssCache/Postgres database", '', 'P')
cae.add_option('assDSN', "Name of the AssCache/Postgres database", 'ass_cache', 'N')

debug_level = cae.get_option('debugLevel')

acu_user = cae.get_option('acuUser')
acu_password = cae.get_option('acuPassword')
acu_dsn = cae.get_option('acuDSN')
uprint("Acumen user/DSN:", acu_user, acu_dsn)

pg_user = cae.get_option('assUser')
pg_pw = cae.get_option('assPassword')
pg_dsn = cae.get_option('assDSN')
uprint("AssCache DB user@dbname:", pg_user, '@', pg_dsn)


# LOGGING HELPERS
error_log = list()
import_log = list()


def log_error(msg, ctx, importance=2, exit_code=0):
    msg = " " * (4 - importance) + "*" * importance + "  " + ctx + "   " + msg
    error_log.append(msg)
    import_log.append(msg)
    uprint(msg)
    if exit_code:
        cae.shutdown(exit_code)


def log_warning(msg, ctx, importance=2):
    seps = '\n' * (importance - 2)
    msg = seps + " " * (4 - importance) + "#" * importance + "  " + ctx + "   " + msg
    import_log.append(msg)
    uprint(msg)


# logon to and prepare Acumen, Salesforce, Sihot and config data env
conf_data = AssSysData(cae, err_logger=log_error, warn_logger=log_warning)
if conf_data.error_message:
    log_error(conf_data.error_message, 'AcuUserLogOn', importance=4, exit_code=9)
    cae.shutdown(exit_code=33)

# logon to and prepare ass_cache database
ass_db = PostgresDB(usr=pg_user, pwd=pg_pw, dsn=pg_dsn, app_name=cae.app_name(), debug_level=debug_level)
if ass_db.connect():
    log_error(ass_db.last_err_msg, 'assUserLogOn', exit_code=12)
    cae.shutdown(exit_code=66)


log_warning("Fetching main RCI member id from Acumen (needs some minutes)", 'FetchAcuMainRciId', importance=3)
a_c = conf_data.load_view(None, 'T_CD', ["CD_CODE", "CD_RCI_REF"],
                          "substr(CD_CODE, 1, 1) <> 'A' and CD_SNAM1 is not NULL and CD_FNAM1 is not NULL"
                          " and CD_RCI_REF is not NULL"
                          " and not exists (select NULL from T_CR where CR_CDREF = CD_CODE and CR_REF = CD_RCI_REF)")
if a_c is None:
    print(conf_data.error_message)
    cae.shutdown(exit_code=99)


log_warning("Storing main RCI member id into ass_cache database (needs some minutes)", 'StoreMainRciId', importance=3)
for cont in a_c:
    if ass_db.select('clients', ["cl_pk"], "cl_ac_id = :cl_ac_id", dict(cl_ac_id=cont[0])):
        break
    cl_pk = ass_db.fetch_value()

    col_values = dict(er_cl_fk=cl_pk, er_type=EXT_REF_TYPE_RCI, er_id=cont[1])
    if ass_db.insert('external_refs', col_values, commit=True):
        break


if ass_db.last_err_msg:
    ass_db.rollback()
    print(ass_db.last_err_msg)
elif conf_data.error_message:
    ass_db.rollback()
    print(conf_data.error_message)
ass_db.commit()
cae.shutdown()
