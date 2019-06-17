"""
    SysDataMan is a tool for to initialize, pull, compare or push data between the available systems (like Acumen,
    AssCache, Sihot and/or Salesforce.

    0.1     first beta.
    0.2     refactored using add_ass_options() and init_ass_data().
    0.3     renamed (from AssCacheSync) into SysDataMan, refactoring to use AssCache as fourth system, migration of
            system data pull/push/compare actions onto ass_sys_data/ae_.sys_data module methods and refactoring/move of
            command line options filterRecords, filterFields, matchRecords and matchFields into the pull/push/compare
            command line options.
"""
import argparse
import pprint
from traceback import format_exc

from sys_data_ids import (DEBUG_LEVEL_VERBOSE, ALL_AVAILABLE_SYSTEMS, ALL_AVAILABLE_RECORD_TYPES,
                          parse_system_option_args)
from ae.sys_data import ACTION_PULL, ACTION_PUSH, ACTION_COMPARE
from ae.console_app import ConsoleApp
from ae.db import PostgresDB
from ass_sys_data import add_ass_options, init_ass_data

__version__ = '0.3'

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)

cae = ConsoleApp(__version__, "Initialize, pull, compare or push AssCache data against Acumen, Sihot and/or Salesforce",
                 formatter_class=argparse.RawDescriptionHelpFormatter,
                 epilog="A dictionary holding additional key-word-arguments can be appended"
                        " directly after the system and record type ids"
                        " for each of the three action options: pull, push and compare."
                        "\n\nThe following key-word-arguments are supported:\n"
                        "\n\tcol_names: list of used system field names (default=use all fields)"
                        "\n\tchk_values: dict of system field values for record filtering (default=all records)"
                        "\n\twhere_group_order: WHERE clause suffix of data SELECT (only available on database systems)"
                        "\n\tbind_values: dict with system bind variable names and values (only on database systems)"
                        "\n\tfield_names: list of used field names (default=use all fields)"
                        "\n\tfilter_records: callable for record filtering (default=all records)"
                        "\n\tmatch_fields: list of field names used for to lookup and merge in record sets")

cae.add_option('init', "Initialize/Wipe/Recreate ass_cache database (0=No, 1=Yes)", 0, 'I')

opt_choices = tuple([s + rt for s in ALL_AVAILABLE_SYSTEMS.keys() for rt in ALL_AVAILABLE_RECORD_TYPES.keys()])
cae.add_option('pull', "Pull record type (e.g. {}) from system (e.g. {}, e.g. shC is pulling Client data from Sihot"
               .format(ALL_AVAILABLE_RECORD_TYPES, ALL_AVAILABLE_SYSTEMS),
               [], 'S', choices=opt_choices, multiple=True)
cae.add_option('push', "Push data of type (e.g. {}) from system (e.g. {}, e.g. sfR pushes Reservations to Salesforce"
               .format(ALL_AVAILABLE_RECORD_TYPES, ALL_AVAILABLE_SYSTEMS),
               [], 'W', choices=opt_choices, multiple=True)
cae.add_option('compare', "Compare/Check pulled data ({}) against {}, e.g. asP checks pulled Products against AssCache"
               .format(ALL_AVAILABLE_RECORD_TYPES, ALL_AVAILABLE_SYSTEMS),
               [], 'V', choices=opt_choices, multiple=True)

'''
cae.add_option('filterRecords', "Filter to restrict (dict keys: C=client, P=product, R=reservation) source records,"
                                " e.g. {'C':\\\"cl_ac_id='E123456'\\\"} pushes only the client with Acu ID E123456",
               {}, 'X')
cae.add_option('filterFields', "Restrict processed (dict keys: C=client, P=product, R=reservation) data fields,"
                               " e.g. {'C':['Phone']} processes (pull/compare/push) only the client field Phone",
               {}, 'Y')
cae.add_option('matchRecords', "Filter to restrict (dict keys: C=client, P=product, R=reservation) destination records,"
                               " e.g. {'C':'cl_phone is NULL'} pulls only client data with empty phone",
               {}, 'M')
cae.add_option('matchFields', "Specify (dict keys: C=client, P=product, R=reservation) fields for to match/lookup the "
                              "associated record e.g. {'C':['Phone']} is using Phone for to associate client records",
               {}, 'Z')
'''

ass_options = add_ass_options(cae, add_kernel_port=True, break_on_error=True, bulk_fetcher='Res')


# NOTIFICATION, LOGGING AND COMMAND LINE OPTION PARSING HELPERS
# declare notification early/here to ensure proper shutdown and display of startup errors on console
notification = notification_warning_emails = None
_debug_level = cae.get_option('debugLevel')

error_log = list()
warn_log = list()


def send_notification(exit_code=0):
    global warn_log, error_log
    all_warnings = all_errors = ""
    if warn_log:
        all_warnings = "WARNINGS:\n\n{}".format("\n\n".join(warn_log))
        cae.uprint(all_warnings)
        warn_log = list()
    if error_log:
        all_errors = "ERRORS:\n\n{}".format("\n\n".join(error_log))
        cae.uprint(all_errors)
        error_log = list()

    if notification and all_warnings:
        subject = "SysDataMan Warnings"
        send_err = notification.send_notification(all_warnings, subject=subject, mail_to=notification_warning_emails)
        if send_err:
            cae.uprint("****  {} send error: {}. warnings='{}'.".format(subject, send_err, all_warnings))
            if not exit_code:
                exit_code = 36
    if notification and all_errors:
        subject = "SysDataMan Errors"
        send_err = notification.send_notification(all_errors, subject=subject)
        if send_err:
            cae.uprint("****  {} send error: {}. errors='{}'.".format(subject, send_err, all_errors))
            if not exit_code:
                exit_code = 39

    return exit_code


def log_error(msg, *args, importance=2, exit_code=0, **kwargs):
    arg_cnt = len(args)
    ctx = args[0] if arg_cnt else ""
    msg = " " * (4 - importance) + "*" * importance + "  " + ctx + "   " + msg
    if arg_cnt > 1 and _debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += "; extra log_error args={}".format(args[1:])
    if kwargs and _debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += "; extra log_error kwargs={}".format(kwargs)
    error_log.append(msg)
    warn_log.append(msg)
    cae.uprint(msg)
    if exit_code or importance > 2:
        exit_code = send_notification(exit_code)
        if ass_data['breakOnErrors']:
            asd.close_dbs()
            cae.shutdown(exit_code)


def log_warning(msg, *args, importance=2, **kwargs):
    arg_cnt = len(args)
    ctx = args[0] if arg_cnt else ""
    seps = '\n' * (importance - 2)
    msg = seps + " " * (4 - importance) + "#" * importance + "  " + ctx + "   " + msg
    if arg_cnt > 1 and _debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += "; extra log_warning args={}".format(args[1:])
    if kwargs and _debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += "; extra log_warning kwargs={}".format(kwargs)
    warn_log.append(msg)
    cae.uprint(msg)


def parse_action_args(args_str, eval_kwargs=False):
    system, rec_type, arg_dict_str = parse_system_option_args(args_str)
    if eval_kwargs:
        # eval args after system and rec_type variables are set, also available are: ass_data, asd, action, ...
        kwargs = eval(arg_dict_str) if arg_dict_str else dict()
        return system, rec_type, kwargs

    return system, rec_type


# parse action command line options
actions = list()
act_init = cae.get_option('init')
if act_init:
    actions.append("Initialize/Clear all record type data within the AssCache system")
act_pulls = cae.get_option('pull')
for act_pull in act_pulls:
    sid, rty = parse_action_args(act_pull)
    actions.append("Pull/Load {} from {}".format(ALL_AVAILABLE_RECORD_TYPES.get(rty), ALL_AVAILABLE_SYSTEMS.get(sid)))
act_pushes = cae.get_option('push')
for act_push in act_pushes:
    sid, rty = parse_action_args(act_push)
    actions.append("Push/Fix {} onto {}".format(ALL_AVAILABLE_RECORD_TYPES.get(rty), ALL_AVAILABLE_SYSTEMS.get(sid)))
act_compares = cae.get_option('compare')
for act_compare in act_compares:
    sid, rty = parse_action_args(act_compare)
    actions.append("Compare {} with {}".format(ALL_AVAILABLE_RECORD_TYPES.get(rty), ALL_AVAILABLE_SYSTEMS.get(sid)))
if not actions:
    cae.uprint("\nNo Action option specified (using command line options init, pull, push and/or compare)\n")
    cae.show_help()
    cae.shutdown()
cae.uprint("Actions: " + "\n         ".join(actions))
'''
act_record_filters = cae.get_option('filterRecords')
if not isinstance(act_record_filters, dict) or not act_record_filters:
    act_record_filters = {k: act_record_filters or "" for (k, v) in ALL_AVAILABLE_RECORD_TYPES.items()}
uprint("Source record filtering:", act_record_filters)
act_field_filters = cae.get_option('filterFields')
if not isinstance(act_field_filters, dict) or not act_field_filters:
    act_field_filters = {k: act_field_filters or "" for (k, v) in ALL_AVAILABLE_RECORD_TYPES.items()}
uprint("Filtered/Used data fields:", act_field_filters)
act_record_matches = cae.get_option('matchRecords')
if not isinstance(act_record_matches, dict) or not act_record_matches:
    act_record_matches = {k: act_record_matches or "" for (k, v) in ALL_AVAILABLE_RECORD_TYPES.items()}
uprint("Destination record filtering:", act_record_matches)
act_match_fields = cae.get_option('matchFields')
if not isinstance(act_match_fields, dict) or not act_match_fields:
    act_match_fields = {k: act_match_fields or "" for (k, v) in ALL_AVAILABLE_RECORD_TYPES.items()}
uprint("User-defined/Processed match fields:", act_match_fields)
'''

# check for to (re-)create and initialize PG database - HAS TO BE DONE BEFORE AssSysData init because pg user not exists
if act_init:
    ass_user = cae.get_option('assUser')
    ass_pw = cae.get_option('assPassword')
    ass_dsn = cae.get_option('assDSN')
    ass_ssl = cae.get_config('assSslArgs')
    pg_dbname, pg_host = ass_dsn.split('@') if '@' in ass_dsn else (ass_dsn, '')
    pg_root_usr = cae.get_config('assRootUsr', default_value='postgres')
    pg_root_pw = cae.get_config('assRootPwd')
    pg_root_dsn = pg_root_usr + ('@' + pg_host if '@' in ass_dsn else '')
    log_warning("creating database {} and user {}".format(ass_dsn, ass_user), 'initCreateDBandUser')
    pg_db = PostgresDB(dict(User=pg_root_usr, Password=pg_root_pw, DSN=pg_root_dsn, SslArgs=ass_ssl),
                       app_name=cae.app_name() + "-CreateDb", debug_level=_debug_level)
    if pg_db.execute_sql("CREATE DATABASE {};".format(pg_dbname), auto_commit=True):  # " LC_COLLATE 'C'"):
        log_error(pg_db.last_err_msg, 'initCreateDB', exit_code=72)

    if pg_db.select('pg_user', ['count(*)'], where_group_order="usename = :ass_user",
                    bind_vars=dict(ass_user=ass_user)):
        log_error(pg_db.last_err_msg, 'initCheckUser', exit_code=81)
    if not pg_db.fetch_value():
        if pg_db.execute_sql("CREATE USER {} WITH PASSWORD '{}';".format(ass_user, ass_pw), commit=True):
            log_error(pg_db.last_err_msg, 'initCreateUser', exit_code=84)
        if pg_db.execute_sql("GRANT ALL PRIVILEGES ON DATABASE {} TO {};".format(pg_dbname, ass_user), commit=True):
            log_error(pg_db.last_err_msg, 'initGrantUserConnect', exit_code=87)
    pg_db.close()

    log_warning("creating tables and audit trigger schema/extension", 'initCreateTableAndAudit')
    pg_db = PostgresDB(dict(User=pg_root_usr, Password=pg_root_pw, DSN=ass_dsn, SslArgs=ass_ssl),
                       app_name=cae.app_name() + "-InitTables", debug_level=_debug_level)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO {};"
                         .format(ass_user)):
        log_error(pg_db.last_err_msg, 'initGrantUserTables', exit_code=90)
    if pg_db.execute_sql("GRANT DELETE ON TABLE {} TO {};".format('external_refs', ass_user)):
        log_error(pg_db.last_err_msg, 'initGrantExtRefsTable', exit_code=91)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {};".format(ass_user)):
        log_error(pg_db.last_err_msg, 'initGrantUserSchemas', exit_code=93)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO {};".format(ass_user)):
        log_error(pg_db.last_err_msg, 'initGrantUserFunctions', exit_code=96)
    if pg_db.execute_sql(open("sql/dba_create_audit.sql").read(), commit=True):
        log_error(pg_db.last_err_msg, 'initCreateAudit', exit_code=99)
    if pg_db.execute_sql(open("sql/dba_create_ass_tables.sql").read(), commit=True):
        log_error(pg_db.last_err_msg, 'initCtScript', exit_code=102)
    pg_db.close()


# logon to and prepare AssCache and config data env, optional also connect to Acumen, Salesforce, Sihot
ass_data = init_ass_data(cae, ass_options, err_logger=log_error, warn_logger=log_warning)
asd = ass_data['assSysData']
if asd.error_message:
    log_error(asd.error_message, 'AssSysDataInit', importance=4, exit_code=9)
notification = ass_data['notification']
notification_warning_emails = ass_data['warningEmailAddresses']
break_on_error = ass_data['breakOnError']


# process the other requested actions (apart from the init action)
for action, option_args in [(ACTION_PULL, a) for a in act_pulls] \
                           + [(ACTION_PUSH, a) for a in act_pushes] \
                           + [(ACTION_COMPARE, a) for a in act_compares]:
    try:
        sid, rty, kwa = parse_action_args(option_args, eval_kwargs=True)
        asd.system_records_action(system=sid, rec_type=rty, action=action, **kwa)
    except Exception as ex:
        log_error("Exception {} in processing {} action with {}:\n{}".format(ex, action, option_args, format_exc(ex)))
        if break_on_error:
            break


# shutdown application and notify users if there were any warnings and/or errors
cae.shutdown(send_notification(42 if error_log else 0))


'''

ass_db = asd.connection(SDI_ASS)
acu_db = asd.connection(SDI_ACU)
sf_conn = asd.connection(SDI_SF)


# ACTION HELPERS

def ac_pull_products():
    log_warning("Pulling Acumen product types", 'pullAcuProductTypes', importance=4)
    where = act_record_filters.get('P')
    if where:
        where = " and (" + where + ")"
    pts = asd.load_view(acu_db, 'T_RS', ['RS_CODE', 'RS_SIHOT_GUEST_TYPE', 'RS_NAME'],
                        "(RS_CLASS = 'CONSTRUCT' or RS_SIHOT_GUEST_TYPE is not NULL)" + where)
    if pts is None:
        return asd.error_message
    for pt in pts:
        if ass_db.upsert('product_types', OrderedDict([('pt_pk', pt[0]), ('pt_group', pt[1]), ('pt_name', pt[2])])):
            ass_db.rollback()
            return ass_db.last_err_msg

    if ass_db.upsert('product_types', OrderedDict([('pt_pk', 'HMF'), ('pt_group', 'I'), ('pt_name', "HMC Fraction")])):
        ass_db.rollback()
        return ass_db.last_err_msg

    prs = asd.load_view(acu_db, 'T_WK INNER JOIN T_AP ON WK_APREF = AP_CODE INNER JOIN T_AT ON AP_ATREF = AT_CODE'
                        ' INNER JOIN T_RS ON AT_RSREF = RS_CODE',
                        ['WK_CODE', 'AT_RSREF'], "RS_SIHOT_GUEST_TYPE is not NULL" + where)
    for pr in prs:
        if ass_db.upsert('products', OrderedDict([('pr_pk', pr[0]), ('pr_pt_fk', pr[1])])):
            break

    cps = asd.load_view(acu_db, 'V_OWNED_WEEKS INNER JOIN T_RS ON AT_RSREF = RS_CODE',
                        ['DW_WKREF', 'AT_RSREF', 'DW_OWREF'],
                        "substr(DW_OWREF, 1, 1) <> 'A' and RS_SIHOT_GUEST_TYPE is not NULL" + where)
    if cps is None:
        return asd.error_message
    for cp in cps:
        cl_pk = asd.cl_ass_id_by_ac_id(cp[2])
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


def ac_pull_res_inv():
    log_warning("Fetching reservation inventory from Acumen (needs some minutes)", 'pullAcuResInv', importance=4)
    where = act_record_filters.get('R')
    if where:
        where = " and (" + where + ")"
    invs = asd.load_view(acu_db, 'T_AOWN_VIEW INNER JOIN T_WK ON AOWN_WKREF = WK_CODE'
                                 ' LEFT OUTER JOIN V_OWNED_WEEKS ON AOWN_WKREF = DW_WKREF',
                         ["case when AOWN_RSREF = 'PBC' and length(AOWN_APREF) = 3 then '0' end || AOWN_WKREF",
                          "(select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTEL' and LU_ID = AOWN_RSREF)",
                          'AOWN_YEAR', 'AOWN_ROREF', 'AOWN_SWAPPED_WITH', 'AOWN_GRANTED_TO',
                          'nvl(POINTS, WK_POINTS)'],
                         "AOWN_YEAR >= to_char(sysdate, 'YYYY') and AOWN_RSREF in ('BHC', 'BHH', 'HMC', 'PBC')"
                         + where)
    if invs is None:
        return asd.error_message
    for inv in invs:
        if ass_db.upsert('res_inventories',
                         dict(ri_pr_fk=inv[0], ri_ho_fk=inv[1], ri_usage_year=inv[2], ri_inv_type=inv[3],
                              ri_swapped_product_id=inv[4], ri_granted_to=inv[5], ri_used_points=inv[6]),
                         chk_values=dict(ri_pr_fk=inv[0], ri_usage_year=inv[2])):
            ass_db.rollback()
            return ass_db.last_err_msg

    ass_db.commit()
    return ""


def ac_pull_res_data():
    log_warning("Fetching reservation data from Acumen (needs some minutes)", 'pullAcuResData', importance=4)
    where = act_record_filters.get('R')
    if where:
        where = "(" + where + ")"
    acumen_res = AcuResToSihot(cae)
    error_msg = acumen_res.fetch_all_valid_from_acu(date_range='P', where_group_order=where)
    if error_msg:
        return error_msg
    for rec in acumen_res.recs:
        # TODO: refactor to use AssSysData.res_save()
        # determine orderer
        ord_cl_pk = asd.cl_ass_id_by_ac_id(rec['OC_CODE'])
        if ord_cl_pk is None:
            error_msg = asd.error_message
            ord_cl_pk = asd.cl_ass_id_by_sh_id(rec['OC_SIHOT_OBJID'])
            if ord_cl_pk is None:
                error_msg += asd.error_message
                break
            error_msg = ""

        # determine used reservation inventory
        year, week = asd.rci_arr_to_year_week(rec['ARR_DATE'])
        apt_wk = "{}-{:0>2}".format(rec['RUL_SIHOT_ROOM'], week)
        if ass_db.select('res_inventories', ['ri_pk'], where_group_order="ri_pr_fk = :aw AND ri_usage_year = :y",
                         bind_vars=dict(aw=apt_wk, y=year)):
            error_msg = ass_db.last_err_msg
            break
        ri_pk = ass_db.fetch_value()

        gds = rec['SIHOT_GDSNO']

        # complete res data with check-in/-out time...
        ac_res = asd.load_view(acu_db,
                               "T_ARO INNER JOIN T_RU ON ARO_RHREF = RU_RHREF and ARO_EXP_ARRIVE = RU_FROM_DATE",
                               ['ARO_TIMEIN', 'ARO_TIMEOUT'],
                               "ARO_STATUS <> 120 and RU_STATUS <> 120 and RU_CODE = :gds_no",
                               dict(gds_no=gds))
        if ac_res is None:
            error_msg = asd.error_message
            break
        elif not ac_res:
            ac_res = (None, None)
        rec['TIMEIN'], rec['TIMEOUT'] = ac_res

        chk_values = dict(rgr_ho_fk=rec['RUL_SIHOT_HOTEL'], rgr_gds_no=gds)
        upd_values = chk_values.copy()
        upd_values.update(rgr_order_cl_fk=ord_cl_pk,
                          rgr_used_ri_fk=ri_pk,
                          # never added next two commented lines because ID-updates should only come from ID-system
                          # rgr_obj_id=rec['RU_SIHOT_OBJID'],
                          # rgr_sf_id=rec['ResSfId'],
                          rgr_status=rec['SIHOT_RES_TYPE'],
                          rgr_adults=rec['RU_ADULTS'],
                          rgr_children=rec['RU_CHILDREN'],
                          rgr_arrival=rec['ARR_DATE'],
                          rgr_departure=rec['DEP_DATE'],
                          rgr_mkt_segment=rec['SIHOT_MKT_SEG'],
                          rgr_mkt_group=rec['RO_SIHOT_RES_GROUP'],
                          rgr_room_id=rec['RUL_SIHOT_ROOM'],
                          rgr_room_cat_id=rec['RUL_SIHOT_CAT'],
                          rgr_room_rate=rec['RUL_SIHOT_RATE'],
                          rgr_ext_book_id=rec['RH_EXT_BOOK_REF'],
                          rgr_ext_book_day=rec['RH_EXT_BOOK_DATE'],
                          rgr_comment=rec['SIHOT_NOTE'],
                          rgr_long_comment=rec['SIHOT_TEC_NOTE'],
                          rgr_time_in=ac_res[0],
                          rgr_time_out=ac_res[1],
                          rgr_last_change=cae.startup_beg,
                          )
        if ass_db.upsert('res_groups', upd_values, chk_values=chk_values, returning_column='rgr_pk'):
            error_msg = ass_db.last_err_msg
            break
        rgr_pk = ass_db.fetch_value()

        # determine occupant(s)
        mc = rec['CD_CODE']
        ac_cos = asd.load_view(acu_db, "T_CD",
                               ['CD_SNAM1', 'CD_FNAM1', 'CD_DOB1', 'CD_SNAM2', 'CD_FNAM2', 'CD_DOB2'],
                               "CD_CODE = :ac_id", dict(ac_id=mc))
        if ac_cos is None:
            error_msg = asd.error_message
            break
        occ_cl_pk = asd.cl_ass_id_by_ac_id(mc)
        if occ_cl_pk is None:
            error_msg = asd.error_message
            break

        chk_values = dict(rgc_rgr_fk=rgr_pk, rgc_room_seq=0, rgc_pers_seq=0)
        upd_values = chk_values.copy()
        upd_values.update(rgc_surname=ac_cos['CD_SNAM1'],
                          rgc_firstname=ac_cos['CD_FNAM1'],
                          rgc_auto_generated='0',
                          rgc_occup_cl_fk=occ_cl_pk,
                          rgc_flight_arr_comment=rec['RU_FLIGHT_AIRPORT'] + " No=" + rec['RU_FLIGHT_NO'],
                          rgc_flight_arr_time=rec['RU_FLIGHT_LANDS'],
                          # occupation data
                          rgc_pers_type='1A',
                          rgc_sh_pack=rec['RUL_SIHOT_PACK'],
                          rgc_room_id=rec['RUL_SIHOT_ROOM'],
                          rgc_dob=ac_cos['CD_DOB1']
                          )
        if ass_db.upsert('res_group_clients', upd_values, chk_values=chk_values):
            error_msg = ass_db.last_err_msg
            break
        # .. add 2nd couple to occupants/res_group_clients
        occ_cl_pk = asd.cl_ass_id_by_ac_id(mc + AC_ID_2ND_COUPLE_SUFFIX)
        if occ_cl_pk is None:
            error_msg = asd.error_message
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



def ac_push_clients():
    """
    push from AssCache to Acumen for to fix there external references, email and phone data.
    :return: error message or "" in case of no errors.
    """
    ctx = 'acPushCl'
    unsupported_fld_names = ['AssId', 'Surname', 'ExtRefs', 'Products']
    client_fld_names = rec_tpl.leaf_names(exclude_fields=unsupported_fld_names)

    match_fields = act_match_fields.get('C')
    if match_fields:
        if len(match_fields) != 1:
            err_msg = "ac_push_clients(): Acumen client push only allows a single match field"
            log_warning(err_msg, ctx, importance=4)
        match_field = match_fields[0]
        if match_field not in client_fld_names or match_field in unsupported_fld_names:
            err_msg = "ac_push_clients(): Acumen client push allows one of the match fields {}, not {}"\
                .format(client_fld_names, match_field)
            log_warning(err_msg, ctx, importance=4)
    else:
        match_field = 'AcuId'

    filter_fields = act_field_filters.get('C')
    if not filter_fields:
        filter_fields = rec_tpl.leaf_names(exclude_fields=unsupported_fld_names + [match_field])
    for filter_fld in filter_fields:
        if filter_fld not in client_fld_names or filter_fld in unsupported_fld_names:
            err_msg = "ac_push_clients(): Acumen client push uses invalid filter field {}".format(filter_fld)
            log_error(err_msg, ctx, importance=4)
            return err_msg

    for as_cl in asd.clients:
        match_val = as_cl.val(match_field)
        cols = {as_cl[_].name(system=SDI_ACU): as_cl.val(_) for _ in filter_fields if as_cl[_].name(system=SDI_ACU)}
        if acu_db.update("T_CD", cols, where="{} = '{}'".format(as_cl[match_field].name(system=SDI_ACU), match_val)):
            log_error("ac_push_clients(): Push client Acumen error: " + acu_db.last_err_msg, ctx, importance=4)

    return acu_db.commit()



def ac_compare_clients():
    where = act_record_matches.get('C')
    if where:
        where = "(" + where + ") and "
    ac_cls = asd.load_view(acu_db, 'T_CD', [AC_SQL_AC_ID1,
                                            AC_SQL_PHONE1, AC_SQL_MAIN_RCI,
                                            AC_SQL_SF_ID1, AC_SQL_SH_ID1, AC_SQL_NAME1, AC_SQL_EMAIL1,
                                            AC_SQL_SF_ID2, AC_SQL_SH_ID2, AC_SQL_NAME2, AC_SQL_EMAIL2],
                           where + "substr(CD_CODE, 1, 1) <> 'A'")
    if ac_cls is None:
        return asd.error_message
    ac_cl_dict = dict((_[0], _[1:]) for _ in ac_cls)
    ac_cl_ori_dict = ac_cl_dict.copy()

    ctx = 'acChkCl'
    cnt = len(warn_log)
    for as_cl in asd.clients:
        ass_id, ac_id, sf_id, sh_id, name, email, phone, ext_refs, _ = as_cl
        if not ac_id:
            if _debug_level >= DEBUG_LEVEL_VERBOSE:
                log_warning("{} - AssCache client without Acumen client reference: {}".format(ass_id, as_cl), ctx)
            continue

        ac_id, offset, first = (ac_id[:-len(AC_ID_2ND_COUPLE_SUFFIX)], 6, False) \
            if ac_id.endswith(AC_ID_2ND_COUPLE_SUFFIX) else (ac_id, 2, True)
        if ac_id not in ac_cl_ori_dict:
            log_warning("{} - Acumen client reference {} not found in Acumen {}".format(ass_id, ac_id, where), ctx)
            continue

        ac_sf_id, ac_sh_id, ac_name, ac_email, *_ = ac_cl_ori_dict[ac_id][offset:]
        ac_sf_id = ensure_long_id(ac_sf_id)
        if sf_id and ac_sf_id and sf_id != ac_sf_id and (first or obj_from_id(sf_id) != 'Lead'):
            log_warning("{} - Salesforce client ID differs: ass={} acu={}".format(ass_id, sf_id, ac_sf_id), ctx)
        if sh_id and ac_sh_id and sh_id != ac_sh_id:
            log_warning("{} - Sihot guest object ID differs: ass={} acu={}".format(ass_id, sh_id, ac_sh_id), ctx)
        if name and ac_name and to_ascii(name).lower() != to_ascii(ac_name).lower():
            log_warning("{} - Client name differs: ass={} acu={}".format(ass_id, name, ac_name), ctx)
        ac_email, _ = correct_email(ac_email)
        if email and ac_email and email != ac_email:
            log_warning("{} - Client email differs: ass={} acu={}".format(ass_id, email, ac_email), ctx)
        elif not asd.email_is_valid(ac_email):
            log_warning("{} - Client email {} contains invalid fragment".format(ass_id, ac_email), ctx)

        if not first:              # further checks not needed for 2nd client/couple of Acumen client
            continue

        if ac_id not in ac_cl_dict:
            log_warning("{} - Acumen client reference duplicates found in AssCache; records={}"
                        .format(ac_id, asd.cl_list_by_ac_id(ac_id)), ctx)
            continue
        ac_phone, ac_rci_main, *_ = ac_cl_dict.pop(ac_id)

        ac_phone, _ = correct_phone(ac_phone)
        if phone and ac_phone and phone != ac_phone:
            log_warning("{} - Client phone differs: ass={} acu={}".format(ass_id, phone, ac_phone), ctx)

        as_ers = [tuple(_.split(EXT_REF_TYPE_ID_SEP)) for _ in ext_refs.split(EXT_REFS_SEP)] if ext_refs else list()
        ac_ers = asd.load_view(acu_db, 'T_CR', ["DISTINCT " + AC_SQL_EXT_REF_TYPE, "CR_REF"],
                               "CR_CDREF = :ac", dict(ac=ac_id))
        if ac_ers is None:
            return asd.error_message
        if ac_rci_main:         # if CD_RCI_REF is populated and no dup then add it to the external refs list
            main_rci_ref = (EXT_REF_TYPE_RCI, ac_rci_main)
            if main_rci_ref not in ac_ers:
                ac_ers.append(main_rci_ref)
        if len(as_ers) != len(ac_ers):
            log_warning("{} - Number of External References differ: ass={}/{}, acu={}/{}"
                        .format(ass_id, len(as_ers), as_ers, len(ac_ers), ac_ers), ctx)
        for as_er in as_ers:
            if not [_ for _ in ac_ers if _ == as_er]:
                log_warning("{} - External Ref {}={} missing in Acumen".format(ass_id, as_er[0], as_er[1]), ctx)
        for ac_er in ac_ers:
            if not [_ for _ in as_ers if _ == ac_er]:
                log_warning("{} - External Ref {}={} missing in AssCache".format(ass_id, ac_er[0], ac_er[1]), ctx)

    # finally and if no filters specified then also log clients that are in Acumen but missing in AssCache
    if not where and not act_record_filters.get('C'):
        for ac_id, ac_cl in ac_cl_dict.items():
            log_warning("Acumen client {} missing in AssCache: ac={}".format(ac_id, ac_cl), ctx)

    log_warning("No Acumen discrepancies found" if len(warn_log) == cnt else "Number of Acumen discrepancies: {}"
                .format(len(warn_log) - cnt), ctx, importance=3)

    return ""


'''
