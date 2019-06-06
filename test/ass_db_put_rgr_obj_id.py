from ae.console_app import ConsoleApp, uprint
from ae.db import PostgresDB
from shif import add_sh_options, print_sh_options, res_no_to_obj_id


__version__ = '0.1'

cae = ConsoleApp(__version__, "Fix rgr_obj_id in ASS_DB", additional_cfg_files=['../.console_app_env.cfg'])
cae.add_option('assUser', "User account name for the AssCache/Postgres database", '', 'U')  # ass_interfaces
cae.add_option('assPassword', "User account password for the AssCache/Postgres database", '', 'P')
cae.add_option('assDSN', "Name of the AssCache/Postgres database", '', 'N')

add_sh_options(cae, add_kernel_port=True)


debug_level = cae.get_option('debugLevel')

# ass_user = cae.get_option('assUser')  TODO: only root user postgres can connect
# ass_pw = cae.get_option('assPassword')
ass_user = cae.get_config('assRootUsr')
ass_pw = cae.get_config('assRootPwd')
cae.set_option('assDSN', 'ass_cache@tf-sh-sihot1v.acumen.es', save_to_config=False)
ass_dsn = cae.get_option('assDSN')
uprint("AssCache credentials:", ass_user, "with", ass_pw, "on", ass_dsn)

cae.set_option('shServerIP', 'tf-sh-sihot1v.acumen.es', save_to_config=False)
print_sh_options(cae)


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


# logon to and prepare AssCache db
'''
asd = AssSysData(cae, err_logger=log_error, warn_logger=log_warning)
if asd.error_message:
    log_error(asd.error_message, 'AssSysDataInit', importance=4, exit_code=9)
'''
# prepare ass_cache database
ass_db = PostgresDB(dict(User=ass_user, Password=ass_pw, DSN=ass_dsn, SslArgs=cae.get_config('assSslArgs')),
                    app_name=cae.app_name(), debug_level=debug_level)
if ass_db.connect():
    log_error(ass_db.last_err_msg, 'assUserLogOn', exit_code=12)


log_warning("Fetching records with empty object id", 'FetchAssInvalids', importance=3)
if ass_db.select('res_groups', ["rgr_ho_fk", "rgr_res_id", "rgr_sub_id"], where_group_order="rgr_obj_id is NULL"):
    log_error("SELECT from res_groups failed with error " + ass_db.last_err_msg, 'FetchAssError', exit_code=15)

rgr_records = ass_db.fetch_all()
if rgr_records is None:
    log_error("FETCH_ALL from res_groups failed with error " + ass_db.last_err_msg, 'FetchAllError', exit_code=99)


log_warning("Populate reservation object id on {} res_group records".format(len(rgr_records)), 'PutObjId', importance=3)
updated = 0
for rgr_rec in rgr_records:
    obj_id = res_no_to_obj_id(cae, rgr_rec[0], rgr_rec[1], rgr_rec[2])
    rgr_dict = dict(rgr_ho_fk=rgr_rec[0], rgr_res_id=rgr_rec[1], rgr_sub_id=rgr_rec[2])
    if not obj_id:
        log_warning("No reservation object id found for res_no {}".format(rgr_dict), 'FetchObjId', importance=3)
        continue
    elif ass_db.update('res_groups', dict(rgr_obj_id=obj_id), rgr_dict):
        break
    updated += 1

log_warning("Updated {} res_group records".format(updated), 'Summary')
if ass_db.last_err_msg:
    ass_db.rollback()
    print(ass_db.last_err_msg)
else:
    ass_db.commit()
cae.shutdown(exit_code=111 if ass_db.last_err_msg else 0)
