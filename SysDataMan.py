"""
    SysDataMan is a tool for to initialize, pull, compare or push data between the available systems (like Acumen,
    AssCache, Sihot and/or Salesforce.

    0.1     first beta.
    0.2     refactored using add_ass_options() and init_ass_data().
    0.3     renamed (from AssCacheSync) into SysDataMan, refactoring to use AssCache as fourth system, migration of
            system data pull/push/compare actions onto ass_sys_data/ae_sys_data module methods and refactoring/move of
            command line options filterRecords, filterFields, matchRecords and matchFields into the pull/push/compare
            command line options.
"""
import argparse
import pprint
from traceback import format_exc

from sys_data_ids import DEBUG_LEVEL_VERBOSE, ALL_AVAILABLE_SYSTEMS, ALL_AVAILABLE_RECORD_TYPES, SRT_ID_LEN
from ae_sys_data import ACTION_PULL, ACTION_PUSH, ACTION_COMPARE
from ae_console_app import ConsoleApp, uprint
from ae_db import PostgresDB
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


notification = None             # declare early/here to ensure proper shutdown and display of startup errors on console
_debug_level = cae.get_option('debugLevel')

# ACTIONS, ACTION-FILTERS AND ACTION-MATCHES
actions = list()
act_init = cae.get_option('init')
if act_init:
    actions.append("Initialize")
act_pulls = cae.get_option('pull')
for act_pull in act_pulls:
    actions.append("Pull/Load " + ALL_AVAILABLE_RECORD_TYPES[act_pull[2:3]]
                   + " from " + ALL_AVAILABLE_SYSTEMS[act_pull[:2]])
act_compares = cae.get_option('compare')
for act_compare in act_compares:
    actions.append("Compare/Check " + ALL_AVAILABLE_RECORD_TYPES[act_compare[2:3]]
                   + " against " + ALL_AVAILABLE_SYSTEMS[act_compare[:2]])
act_pushes = cae.get_option('push')
for act_push in act_pushes:
    actions.append("Push/Fix " + ALL_AVAILABLE_RECORD_TYPES[act_push[2:3]]
                   + " onto " + ALL_AVAILABLE_SYSTEMS[act_push[:2]])
if not actions:
    uprint("\nNo Action option specified (using command line options init, pull, push and/or compare)\n")
    cae.show_help()
    cae.shutdown()
uprint("Actions: " + "\n         ".join(actions))
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

# LOGGING AND NOTIFICATION HELPERS
error_log = list()
warn_log = list()
notification = notification_warning_emails = None


def send_notification(exit_code=0):
    global warn_log, error_log
    all_warnings = all_errors = ""
    if warn_log:
        all_warnings = "WARNINGS:\n\n{}".format("\n\n".join(warn_log))
        uprint(all_warnings)
        warn_log = list()
    if error_log:
        all_errors = "ERRORS:\n\n{}".format("\n\n".join(error_log))
        uprint(all_errors)
        error_log = list()

    if notification and all_warnings:
        subject = "SysDataMan Warnings"
        send_err = notification.send_notification(all_warnings, subject=subject, mail_to=notification_warning_emails)
        if send_err:
            uprint("****  {} send error: {}. warnings='{}'.".format(subject, send_err, all_warnings))
            if not exit_code:
                exit_code = 36
    if notification and all_errors:
        subject = "SysDataMan Errors"
        send_err = notification.send_notification(all_errors, subject=subject)
        if send_err:
            uprint("****  {} send error: {}. errors='{}'.".format(subject, send_err, all_errors))
            if not exit_code:
                exit_code = 39

    return exit_code


def log_error(msg, ctx, *args, importance=2, exit_code=0, **kwargs):
    msg = " " * (4 - importance) + "*" * importance + "  " + ctx + "   " + msg
    if args and _debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += "; extra log_error args={}".format(args)
    if kwargs and _debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += "; extra log_error kwargs={}".format(kwargs)
    error_log.append(msg)
    warn_log.append(msg)
    uprint(msg)
    if exit_code or importance > 2:
        exit_code = send_notification(exit_code)
        if ass_data['breakOnErrors']:
            asd.close_dbs()
            cae.shutdown(exit_code)


def log_warning(msg, ctx, *args, importance=2, **kwargs):
    seps = '\n' * (importance - 2)
    msg = seps + " " * (4 - importance) + "#" * importance + "  " + ctx + "   " + msg
    if args and _debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += "; extra log_warning args={}".format(args)
    if kwargs and _debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += "; extra log_warning kwargs={}".format(kwargs)
    warn_log.append(msg)
    uprint(msg)


# check for to (re-)create and initialize PG database - HAS TO BE DONE BEFORE AssSysData init because pg user not exists
if act_init:
    ass_user = cae.get_option('assUser')
    ass_pw = cae.get_option('assPassword')
    ass_dsn = cae.get_option('assDSN')
    pg_dbname, pg_host = ass_dsn.split('@') if '@' in ass_dsn else (ass_dsn, '')
    pg_root_usr = cae.get_config('assRootUsr', default_value='postgres')
    pg_root_dsn = pg_root_usr + ('@' + pg_host if '@' in ass_dsn else '')
    log_warning("creating database {} and user {}".format(ass_dsn, ass_user), 'initCreateDBandUser')
    pg_db = PostgresDB(dict(User=pg_root_usr, Password=cae.get_config('assRootPwd'), DSN=pg_root_dsn,
                            SslArgs=cae.get_config('assSslArgs')),
                       app_name=cae.app_name() + "-CreateDb",
                       debug_level=_debug_level)
    if pg_db.execute_sql("CREATE DATABASE " + pg_dbname + ";", auto_commit=True):  # " LC_COLLATE 'C'"):
        log_error(pg_db.last_err_msg, 'initCreateDB', exit_code=72)

    if pg_db.select('pg_user', ['count(*)'], where_group_order="usename = :ass_user",
                    bind_vars=dict(ass_user=ass_user)):
        log_error(pg_db.last_err_msg, 'initCheckUser', exit_code=81)
    if not pg_db.fetch_value():
        if pg_db.execute_sql("CREATE USER " + ass_user + " WITH PASSWORD '" + ass_pw + "';", commit=True):
            log_error(pg_db.last_err_msg, 'initCreateUser', exit_code=84)
        if pg_db.execute_sql("GRANT ALL PRIVILEGES ON DATABASE " + pg_dbname + " to " + ass_user + ";", commit=True):
            log_error(pg_db.last_err_msg, 'initGrantUserConnect', exit_code=87)
    pg_db.close()

    log_warning("creating tables and audit trigger schema/extension", 'initCreateTableAndAudit')
    pg_db = PostgresDB(dict(User=cae.get_config('assRootUsr'), Password=cae.get_config('assRootPwd'), DSN=ass_dsn,
                            SslArgs=cae.get_config('assSslArgs')),
                       app_name=cae.app_name() + "-InitTables",
                       debug_level=_debug_level)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO "
                         + ass_user + ";"):
        log_error(pg_db.last_err_msg, 'initGrantUserTables', exit_code=90)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO " + ass_user + ";"):
        log_error(pg_db.last_err_msg, 'initGrantUserTables', exit_code=93)
    if pg_db.execute_sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO " + ass_user + ";"):
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


def parse_action_args(args_str):
    str_i = args_str.find('{')
    if str_i >= 0:
        arg_dict_str = args_str[str_i:]
        kwargs = eval(arg_dict_str)
    else:
        str_i = len(args_str)
        kwargs = dict()
    str_i -= SRT_ID_LEN
    rec_type = args_str[str_i:str_i + SRT_ID_LEN]
    system = args_str[:str_i - 1]
    return system, rec_type, kwargs


# process requested actions
for action, option_args in [(ACTION_PULL, a) for a in act_pulls] \
                           + [(ACTION_PUSH, a) for a in act_pushes] \
                           + [(ACTION_COMPARE, a) for a in act_compares]:
    try:
        sid, rty, kwa = parse_action_args(option_args)
        asd.system_records_action(system=sid, rec_type=rty, action=action, **kwa)
    except Exception as ex:
        uprint("Exception {} while processing {} action with {}:\n{}".format(ex, action, option_args, format_exc(ex)))
        if break_on_error:
            break


# shutdown application and notify users if there were any warnings and/or errors
cae.shutdown(send_notification(42 if error_log else 0))


'''

ass_db = asd.connection(SDI_ASS)
acu_db = asd.connection(SDI_ACU)
sf_conn = asd.connection(SDI_SF)


# ACTION HELPERS
def sh_match_field_init(ctx):
    supported_match_fields = [SH_DEF_SEARCH_FIELD, 'AcuId', 'Name', 'Email']

    match_fields = act_match_fields.get('C')
    if match_fields:
        match_field = match_fields[0]
        if len(match_fields) > 1:
            err_msg = "sh_match_field_init(): Sihot client comparision only allows a single match field"
            log_error(err_msg, ctx, importance=4)
            return err_msg
        elif match_field not in supported_match_fields:
            err_msg = "sh_match_field_init(): Sihot only allows the match fields {} (so {} is not supported)"\
                .format(supported_match_fields, match_field)
            log_error(err_msg, ctx, importance=4)
            return err_msg
    else:
        match_field = SH_DEF_SEARCH_FIELD

    return match_field




def ac_pull_clients():
    """ migrate client data from Acumen into AssCache/Postgres """

    # fetch all couple-clients from Acumen
    log_warning("Fetching couple client data from Acumen", 'pullAcuCoupleClients', importance=4)
    where = act_record_filters.get('C')
    if where:
        where = "(" + where + ") and "
    # where clause template for CD_SNAM1, CD_FNAM1 and CD_SNAM2, CD_FNAM2
    where += "substr(CD_CODE, 1, 1) <> 'A' and (CD_SNAM{idx} is not NULL or CD_FNAM{idx} is not NULL)"
    ac_cls = asd.load_view(acu_db, 'T_CD',
                           [AC_SQL_AC_ID1, AC_SQL_SF_ID1, AC_SQL_SH_ID1, AC_SQL_NAME1, AC_SQL_EMAIL1,
                            AC_SQL_PHONE1, AC_SQL_MAIN_RCI],
                           where.format(idx="1"))
    if ac_cls is None:
        return asd.error_message
    ac_2 = asd.load_view(acu_db, 'T_CD',
                         [AC_SQL_AC_ID2, AC_SQL_SF_ID2, AC_SQL_SH_ID2, AC_SQL_NAME2, AC_SQL_EMAIL2,
                          "NULL", "NULL"],
                         where.format(idx="2"))
    if ac_2 is None:
        return asd.error_message
    ac_cls += ac_2
    ac_cls.sort(key=lambda _: _[0])

    # migrate to ass_cache including additional external refs/IDs (fetched from Acumen)
    save_fields = act_field_filters.get('C')
    match_fields = act_match_fields.get('C')
    for idx, ac_cl in enumerate(ac_cls):
        ext_refs = asd.load_view(acu_db, 'T_CR', ["DISTINCT " + AC_SQL_EXT_REF_TYPE, "CR_REF"],
                                 "CR_CDREF = :ac_id", dict(ac_id=ac_cl[0]))
        if ext_refs is None:
            ext_refs = list()
        if ac_cl[6]:
            ext_refs += [(EXT_REF_TYPE_RCI, ac_cl[6])]

        cl_dict = dict(AcuId=ac_cl[0], SfId=ac_cl[1], ShId=ac_cl[2], Name=ac_cl[3], Email=ac_cl[4], Phone=ac_cl[5])
        cl_pk = asd.cl_save(cl_dict, save_fields=save_fields, match_fields=match_fields, ext_refs=ext_refs)
        if cl_pk is None:
            break
        if (idx + 1) % 1000 == 0:
            ass_db.commit()

    if ass_db.last_err_msg:
        ass_db.rollback()
        return ass_db.last_err_msg
    elif asd.error_message:
        ass_db.rollback()
        return asd.error_message

    return ass_db.commit()


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
    acumen_req = AcuResToSihot(cae)
    error_msg = acumen_req.fetch_all_valid_from_acu(date_range='P', where_group_order=where)
    if error_msg:
        return error_msg
    for crow in acumen_req.recs:
        # TODO: refactor to use AssSysData.sh_res_change_to_ass()
        # determine orderer
        ord_cl_pk = asd.cl_ass_id_by_ac_id(crow['OC_CODE'])
        if ord_cl_pk is None:
            error_msg = asd.error_message
            ord_cl_pk = asd.cl_ass_id_by_sh_id(crow['OC_SIHOT_OBJID'])
            if ord_cl_pk is None:
                error_msg += asd.error_message
                break
            error_msg = ""

        # determine used reservation inventory
        year, week = asd.rci_arr_to_year_week(crow['ARR_DATE'])
        apt_wk = "{}-{:0>2}".format(crow['RUL_SIHOT_ROOM'], week)
        if ass_db.select('res_inventories', ['ri_pk'], where_group_order="ri_pr_fk = :aw AND ri_usage_year = :y",
                         bind_vars=dict(aw=apt_wk, y=year)):
            error_msg = ass_db.last_err_msg
            break
        ri_pk = ass_db.fetch_value()

        gds = crow['SIHOT_GDSNO']

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
        crow['TIMEIN'], crow['TIMEOUT'] = ac_res

        chk_values = dict(rgr_ho_fk=crow['RUL_SIHOT_HOTEL'], rgr_gds_no=gds)
        upd_values = chk_values.copy()
        upd_values.update(rgr_order_cl_fk=ord_cl_pk,
                          rgr_used_ri_fk=ri_pk,
                          # never added next two commented lines because ID-updates should only come from ID-system
                          # rgr_obj_id=crow['RU_SIHOT_OBJID'],
                          # rgr_sf_id=crow['ResSfId'],
                          rgr_status=crow['SIHOT_RES_TYPE'],
                          rgr_adults=crow['RU_ADULTS'],
                          rgr_children=crow['RU_CHILDREN'],
                          rgr_arrival=crow['ARR_DATE'],
                          rgr_departure=crow['DEP_DATE'],
                          rgr_mkt_segment=crow['SIHOT_MKT_SEG'],
                          rgr_mkt_group=crow['RO_SIHOT_RES_GROUP'],
                          rgr_room_id=crow['RUL_SIHOT_ROOM'],
                          rgr_room_cat_id=crow['RUL_SIHOT_CAT'],
                          rgr_room_rate=crow['RUL_SIHOT_RATE'],
                          rgr_ext_book_id=crow['RH_EXT_BOOK_REF'],
                          rgr_ext_book_day=crow['RH_EXT_BOOK_DATE'],
                          rgr_comment=crow['SIHOT_NOTE'],
                          rgr_long_comment=crow['SIHOT_TEC_NOTE'],
                          rgr_time_in=ac_res[0],
                          rgr_time_out=ac_res[1],
                          rgr_last_change=cae.startup_beg,
                          )
        if ass_db.upsert('res_groups', upd_values, chk_values=chk_values, returning_column='rgr_pk'):
            error_msg = ass_db.last_err_msg
            break
        rgr_pk = ass_db.fetch_value()

        # determine occupant(s)
        mc = crow['CD_CODE']
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


def sf_pull_clients():
    def _fetch(obj, where_sql):
        if where_sql:
            where_sql = "WHERE " + where_sql
        rel_name = 'External_References__pr' if obj == 'Account' else 'External_References__r'
        code_fields = ['AssId', 'AcuId', 'SfId', 'ShId', 'Name', 'Email', 'Phone',
                       'RecordType.Id', 'RciId',
                       "(SELECT Name, Reference_No_or_ID__c FROM {})".format(rel_name)]
        sf_fields = field_list_to_sf(code_fields, obj)
        return sf_conn.soql_query_all("SELECT {} FROM {} {}".format(", ".join(sf_fields), obj, where_sql))

    def _retrieve(result, obj):
        rel_name = 'External_References__pr' if obj == 'Account' else 'External_References__r'
        for c in result['records']:  # list of client OrderedDicts
            ers = list()
            if c[rel_name]['records']:
                ers.extend([(_['Name'], _['Reference_No_or_ID__c']) for _ in c[rel_name]['records']])
            rci_id = c[sf_fld_sys_name('RciId', obj)]
            if rci_id and not [_ for _ in ers if _[0] == EXT_REF_TYPE_RCI and _[1] == rci_id]:
                ext_refs.append((EXT_REF_TYPE_RCI, rci_id))
            client_tuples.append((field_dict_from_sf(c, obj), ers))

    log_warning("Fetching client data from Salesforce", 'pullSfClientData', importance=4)

    where = act_record_filters.get('C')
    client_tuples = list()
    sf_obj = 'Account'
    res = _fetch(sf_obj, where)
    if sf_conn.error_msg:
        asd.error_message = "sf_pull_clients(): " + sf_conn.error_msg
    elif res['totalSize'] > 0:
        _retrieve(res, sf_obj)

        sf_obj = 'Lead'
        res = _fetch(sf_obj, "IsConverted = false" + (" and (" + where + ")" if where else ""))
        if sf_conn.error_msg:
            asd.error_message = "sf_pull_clients(): " + sf_conn.error_msg
        elif res['totalSize'] > 0:
            _retrieve(res, sf_obj)

    save_fields = act_field_filters.get('C')
    match_fields = act_match_fields.get('C')
    for idx, cl_data_and_ext_refs in enumerate(client_tuples):
        cl_dict, ext_refs = cl_data_and_ext_refs[0], cl_data_and_ext_refs[1].split(EXT_REFS_SEP)
        cl_pk = asd.cl_save(cl_dict, save_fields=save_fields, match_fields=match_fields, ext_refs=ext_refs)
        if cl_pk is None:
            break
        if (idx + 1) % 1000 == 0:
            ass_db.commit()

    if ass_db.last_err_msg:
        ass_db.rollback()
        return ass_db.last_err_msg
    elif asd.error_message:
        ass_db.rollback()
        return asd.error_message

    return ass_db.commit()


def sf_pull_res_data():
    log_warning("Fetching reservation data from Salesforce (needs some minutes)", 'pullSfResData', importance=4)
    where = act_record_filters.get('R')

    res_all = sf_conn.soql_query_all("SELECT Id FROM Opportunity" + (" WHERE " + where if where else ""))
    if not res_all or sf_conn.error_msg:
        log_error("ResData cache load error: " + sf_conn.error_msg, 'pullSfResDataPrepErr', importance=3, exit_code=150)
    for res in res_all:
        sf_res_id = res['Id']
        err_msg = sf_conn.res_data(sf_res_id)
        if err_msg:
            log_error("ResData processing error: " + err_msg, 'pullSfResDataProcErr', importance=3, exit_code=153)
        asd.rgr_upsert()

    if ass_db.last_err_msg:
        ass_db.rollback()
        return ass_db.last_err_msg
    elif asd.error_message:
        ass_db.rollback()
        return asd.error_message

    return ass_db.commit()


def sh_pull_clients():
    ctx = 'shPullCl'
    # NOTE: Sihot/GuestBulkFetcher doesn't allow bulk fetches so only AssCache recs can be pulled/updated from Sihot
    if act_record_filters.get('C'):
        log_warning("filterRecords option not implemented for client pulls from Sihot", 'shPullClientsFilterNotImpl',
                    importance=3)

    if not asd.clients:
        # fetch all clients from AssCache
        err_msg = asd.as_clients_pull(where_group_order=act_record_matches.get('C'))
        if err_msg:
            log_error("Client cache load error: " + err_msg, 'pullShClientsPrepErr', importance=3, exit_code=300)

    match_field = sh_match_field_init(ctx)
    filter_fields = act_field_filters.get('C')
    if not filter_fields:
        filter_fields = rec_tpl.leaf_names(exclude_fields=[match_field])
    client_fld_names = list(_ for _ in filter_fields if _ not in ('AssId', 'ExtRefs', 'Products'))

    for as_cl in asd.clients:
        # ass_id, ac_id, _, sh_id, name, email, _, _, _ = as_cl
        ass_id = as_cl.val('AssId')
        match_val = as_cl.val(match_field)
        if not match_val:
            if _debug_level >= DEBUG_LEVEL_VERBOSE:
                log_warning("{} - AssCache client match field {} is empty: {}".format(ass_id, match_field, as_cl), ctx)
            continue

        if match_field == SH_DEF_SEARCH_FIELD:
            sh_id = match_val
        else:
            sh_ids = asd.sh_guest_ids(match_field, match_val)
            if not sh_ids:
                log_warning("{} - AssCache client Sihot guest id search via match field {}={} failed: {}"
                            .format(ass_id, match_field, match_val, as_cl), ctx)
                continue
            elif len(sh_ids) > 1:
                log_warning("{} - Skipping AssCache client because search via {}={} returned multiple/{} guests: {}"
                            .format(ass_id, match_field, match_val, len(sh_ids), as_cl), ctx, importance=3)
                continue
            sh_id = sh_ids[0]
        shd = client_data(cae, sh_id)
        if not shd:
            log_warning("{} - AssCache guest object ID {} does not exits in Sihot: {}".format(ass_id, sh_id, as_cl),
                        ctx, importance=4)
            continue

        di = "; REC: ass={} sh={}".format(as_cl, shd) if _debug_level >= DEBUG_LEVEL_VERBOSE else ""
        cl_rec = Record()
        for fld_name in client_fld_names:
            ass_val = as_cl.val(fld_name)
            sh_val = shd.val(fld_name)
            if not ass_val and not sh_val:
                continue
            elif isinstance(sh_val, list):
                if len(sh_val) > 1:
                    log_warning("{} - {} has multiple values - pulling/changing only first one. ass={} sh={}{}"
                                .format(ass_id, fld_name, ass_val, sh_val, di), ctx, importance=3)
                sh_val = sh_val[0]
            cl_rec[fld_name] = sh_val
        cl_pk = asd.cl_save(cl_rec, match_fields=[match_field])
        if cl_pk is None:
            break

        if 'ExtRefs' in filter_fields:
            pass    # NOT IMPLEMENTED
        if 'Products' in filter_fields:
            pass    # not implemented

    if ass_db.last_err_msg:
        ass_db.rollback()
        return ass_db.last_err_msg
    elif asd.error_message:
        ass_db.rollback()
        return asd.error_message

    return ass_db.commit()


def sh_pull_res_data():
    log_warning("Fetching reservation data from Sihot", 'pullShResData', importance=4)
    if act_record_filters.get('R'):
        log_warning("filterRecords option not implemented for reservation pulls from Sihot", 'pullShResFilterNotImpl',
                    importance=3)
    rbf_groups = ass_options['ResBulkFetcher'].fetch_all()
    error_msg = ""
    for shd in rbf_groups:
        error_msg = asd.sh_res_change_to_ass(shd)
        if error_msg:
            break

    return error_msg + "\n" + ass_db.rollback() if error_msg else ass_db.commit()


for act_pull in act_pulls:
    if act_pull[:2] == 'ac':
        if act_pull[2:3] == 'C':
            err = ac_pull_clients()
            if err:
                log_error(err, 'pullAcuClients', importance=3, exit_code=111)
        elif act_pull[2:3] == 'P':
            err = ac_pull_products()
            if err:
                log_error(err, 'pullAcuProductTypes', importance=3, exit_code=114)
        elif act_pull[2:3] == 'R':
            err = ac_pull_res_inv()  # load reservation inventory data
            if err:
                log_error(err, 'pullAcuResInv', importance=3, exit_code=117)
            err = ac_pull_res_data()
            if err:
                log_error(err, 'pullAcuResData', importance=3, exit_code=120)
        else:
            log_error("Acumen pull not implemented", 'pullAcuNotImp', importance=3, exit_code=129)

    elif act_pull[:2] == 'sf':
        if act_pull[2:3] == 'C':
            err = sf_pull_clients()
            if err:
                log_error(err, 'pullSfClients', importance=3, exit_code=141)
        elif act_pull[2:3] == 'R':
            err = sf_pull_res_data()
            if err:
                log_error(err, 'pullSfResData', importance=3, exit_code=142)
        else:
            log_error("Salesforce pull not implemented", 'pullSfNotImpl', importance=3, exit_code=149)

    elif act_pull[:2] == 'sh':
        if act_pull[2:3] == 'C':
            err = sh_pull_clients()
            if err:
                log_error(err, 'pullShClients', importance=3, exit_code=151)
        elif act_pull[2:3] == 'R':
            err = sh_pull_res_data()
            if err:
                log_error(err, 'pullShResData', importance=3, exit_code=152)
        else:
            log_error("Sihot pull not implemented", 'pullShNotImpl', importance=3, exit_code=159)


def ac_push_clients():
    """
    push from AssCache to Acumen for to fix there external references, email and phone data.
    :return: error message or "" in case of no errors.
    """
    ctx = 'acPushCl'
    unsupported_fld_names = ['AssId', 'Name', 'ExtRefs', 'Products']
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


def sf_push_clients():
    """
    push from AssCache to Salesforce for to fix there external references, email and phone data.
    :return: error message or "" in case of no errors.
    """
    ctx = 'sfPushCl'
    unsupported_fld_names = ['ExtRefs', 'Products']
    client_fld_names = rec_tpl.leaf_names(exclude_fields=unsupported_fld_names)

    match_fields = act_match_fields.get('C')
    if match_fields:
        if len(match_fields) != 1:
            err_msg = "sf_push_clients(): Salesforce client push only allows a single match field"
            log_warning(err_msg, ctx, importance=4)
        match_field = match_fields[0]
        if match_field not in client_fld_names or match_field in unsupported_fld_names:
            err_msg = "sf_push_clients(): Salesforce client push allows one of the match fields {}, not {}" \
                .format(client_fld_names, match_field)
            log_warning(err_msg, ctx, importance=4)
    else:
        match_field = SF_DEF_SEARCH_FIELD

    filter_fields = act_field_filters.get('C')
    if not filter_fields:
        filter_fields = rec_tpl.leaf_names(exclude_fields=unsupported_fld_names + [match_field])
    for filter_fld in filter_fields:
        if filter_fld not in client_fld_names or filter_fld in unsupported_fld_names:
            err_msg = "sf_push_clients(): Salesforce client push uses invalid filter field {}".format(filter_fld)
            log_error(err_msg, ctx, importance=4)
            return err_msg

    if match_field not in filter_fields:
        filter_fields.append(match_field)       # ensure SF ID for to specify indirectly object type and record

    errors = list()
    for as_cl in asd.clients:
        rec = Record(fields={_: as_cl.val(_) for _ in filter_fields})
        sf_id, err_msg, msg = asd.connection(SDI_SF).cl_upsert(rec)
        if err_msg:
            log_error("sf_push_clients(): Push client Salesforce error: " + err_msg, ctx, importance=4)
            errors.append(err_msg)

    return "\n".join(errors)


def sh_push_clients():
    """
    push from AssCache to Sihot for to fix there external references, email and phone data.
    :return: error message or "" in case of no errors.
    """
    ctx = 'shPushCl'
    unsupported_fld_names = ['ExtRefs', 'Products']
    client_fld_names = rec_tpl.leaf_names(exclude_fields=unsupported_fld_names)

    match_fields = act_match_fields.get('C')
    if match_fields:
        if len(match_fields) != 1:
            err_msg = "sh_push_clients(): Sihot client push only allows a single match field"
            log_warning(err_msg, ctx, importance=4)
        match_field = match_fields[0]
        if match_field not in client_fld_names or match_field in unsupported_fld_names:
            err_msg = "sh_push_clients(): Sihot client push allows one of the match fields {}, not {}" \
                .format(client_fld_names, match_field)
            log_warning(err_msg, ctx, importance=4)
    else:
        match_field = SH_DEF_SEARCH_FIELD

    filter_fields = act_field_filters.get('C')
    if not filter_fields:
        filter_fields = rec_tpl.leaf_names(exclude_fields=unsupported_fld_names + [match_field])
    for filter_fld in filter_fields:
        if filter_fld not in client_fld_names or filter_fld in unsupported_fld_names:
            err_msg = "sh_push_clients(): Sihot client push uses invalid filter field {}".format(filter_fld)
            log_error(err_msg, ctx, importance=4)
            return err_msg

    if match_field not in filter_fields:
        filter_fields.append(match_field)       # ensure SF ID for to specify indirectly object type and record

    errors = list()
    for as_cl in asd.clients:
        rec = Record(fields={_: as_cl.val(_) for _ in filter_fields})
        err_msg = ClientToSihot(cae).send_client_to_sihot(rec)
        if err_msg:
            log_error("sh_push_clients(): Push client Sihot error: " + err_msg, ctx, importance=4)
            errors.append(err_msg)

    return "\n".join(errors)


if [_ for _ in act_pushes if _[2:3] == 'C']:
    log_warning("Preparing client data push and fix", 'pushClientPrepare', importance=4)
    # fetch all (filtered) clients from AssCache if not loaded by a previous pull
    if not asd.clients:
        err = asd.as_clients_pull(where_group_order=act_record_filters.get('C'))
        if err:
            log_error("Client cache load error: " + err, 'pushClientPrepErr', importance=3, exit_code=600)
for act_push in act_pushes:
    if act_push[:2] == 'ac':
        if act_push[2:3] == 'C':
            err = ac_push_clients()
            if err:
                log_error(err, 'pushAcClients', importance=3, exit_code=303)
        elif act_push[2:3] == 'P':
            log_error("Acumen Product Fix not implemented", 'pushAcProd', importance=3, exit_code=630)
        elif act_push[2:3] == 'R':
            log_error("Acumen Reservation Fix not implemented", 'pushAcRes', importance=3, exit_code=660)

    elif act_push[:2] == 'sf':
        if act_push[2:3] == 'C':
            err = sf_push_clients()
            if err:
                log_error(err, 'pushSfClientErr', importance=3, exit_code=801)
        else:
            log_error("Salesforce fix not implemented", 'pushSfNotImpl', importance=3, exit_code=891)

    elif act_push[:2] == 'sh':
        if act_push[2:3] == 'C':
            err = sh_push_clients()
            if err:
                log_error(err, 'pushShClients', importance=3, exit_code=702)
        else:
            log_error("Sihot fix not implemented", 'pushShNotImpl', importance=3, exit_code=795)


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


def sf_compare_clients():
    ctx = 'sfChkCl'
    cnt = len(warn_log)
    client_fld_names = rec_tpl.leaf_names(exclude_fields=['ExtRefs', 'Products'])

    match_fields = act_match_fields.get('C')
    if match_fields:
        if len(match_fields) != 1:
            err_msg = "sf_compare_clients(): SF client comparision only allows a single match field"
            log_error(err_msg, ctx, importance=4)
            return err_msg
        match_field = match_fields[0]
    else:
        match_field = SF_DEF_SEARCH_FIELD

    filter_fields = act_field_filters.get('C')
    if not filter_fields:
        filter_fields = rec_tpl.leaf_names(exclude_fields=[match_field])

    for as_cl in asd.clients:
        ass_id, _, sf_id, _, _, email, phone, ass_ext_refs, _ = as_cl
        if match_field == SF_DEF_SEARCH_FIELD:
            if not sf_id:
                if _debug_level >= DEBUG_LEVEL_VERBOSE:
                    log_warning("{} - AssCache client without SF ID; ass={}".format(ass_id, as_cl), ctx, importance=1)
                found_by = ""
                sf_obj = 'Account'
                if email:
                    found_by = "Email={}".format(email)
                    sf_id = sf_conn.cl_field_data('SfId', email, search_field='Email', sf_obj=sf_obj)
                if not sf_id and phone:
                    found_by = "Phone={}".format(phone)
                    sf_id = sf_conn.cl_field_data('SfId', phone, search_field='Phone', sf_obj=sf_obj)
                if not sf_id and email:
                    sf_obj = 'Lead'
                    found_by = "Email={}".format(email)
                    sf_id = sf_conn.cl_field_data('SfId', email, search_field='Email', sf_obj=sf_obj)
                if not sf_id and phone:
                    sf_obj = 'Lead'
                    found_by = "Phone={}".format(phone)
                    sf_id = sf_conn.cl_field_data('SfId', phone, search_field='Phone', sf_obj=sf_obj)
                if not sf_id:
                    continue
                log_warning("{} - AssCache client without ASS SF ID found as {} ID {} via {}; ass={}"
                            .format(ass_id, sf_obj, sf_id, found_by, as_cl), ctx, importance=3)
            search_val = sf_id
        elif match_field in client_fld_names:
            search_val = as_cl.val(match_field)
        else:
            err_msg = "sf_compare_clients(): SF client comparision match field {} not supported." \
                      " Allowed match fields: {}".format(match_field, [_ for _ in client_fld_names])
            log_error(err_msg, ctx, importance=4)
            return err_msg

        log_warnings = list()
        sf_fld_vals = sf_conn.cl_field_data(client_fld_names, search_val, search_field=match_field,
                                            log_warnings=log_warnings)
        if not sf_fld_vals:
            if _debug_level >= DEBUG_LEVEL_VERBOSE:
                for msg in log_warnings:
                    log_warning("{} - {}; ass={}".format(ass_id, msg, as_cl), ctx, importance=1)
            log_warning("{} - {} ID {} not found as object ID nor in any of the reference ID fields; err={}; ass={}"
                        .format(ass_id, obj_from_id(sf_id), sf_id, asd.error_message, as_cl), ctx, importance=3)
            continue

        di = "; REC: ass={} sf={}".format(as_cl, sf_fld_vals) if _debug_level >= DEBUG_LEVEL_VERBOSE else ""
        for fld_name, fld_value in sf_fld_vals.items():
            if fld_name not in filter_fields:
                continue
            ass_val = as_cl.val(fld_name)
            if (ass_val or fld_value) and ass_val != fld_value:
                log_warning("{} - {} mismatch. ass={} sf={}{}".format(ass_id, fld_name, ass_val, fld_value, di), ctx)

        if 'ExtRefs' in filter_fields:
            ass_ext_refs = [tuple(_.split(EXT_REF_TYPE_ID_SEP)) for _ in ass_ext_refs.split(EXT_REFS_SEP)] \
                if ass_ext_refs else list()
            sf_ext_refs = sf_conn.cl_ext_refs(sf_id)
            di = "; REFS ass={} sf={}; REC ass={} sf={}".format(ass_ext_refs, sf_ext_refs, as_cl, sf_fld_vals) \
                if _debug_level >= DEBUG_LEVEL_VERBOSE else ""
            for er in ass_ext_refs:
                if er not in sf_ext_refs:
                    log_warning("{} - AssCache external reference {} missing in SF{}".format(ass_id, er, di), ctx)
            for er in sf_ext_refs:
                if er not in ass_ext_refs:
                    log_warning("{} - SF external reference {} missing in AssCache{}".format(ass_id, er, di), ctx)

        if 'Products' in filter_fields:
            pass    # not implemented

    log_warning("No Salesforce discrepancies found" if len(warn_log) == cnt else "Number of Salesforce discrepancies={}"
                .format(len(warn_log) - cnt), ctx, importance=4)

    return ""


def sh_compare_clients():
    ctx = 'shChkCl'
    cnt = len(warn_log)

    match_field = sh_match_field_init(ctx)
    filter_fields = act_field_filters.get('C')
    if not filter_fields:
        filter_fields = rec_tpl.leaf_names(exclude_fields=[match_field])
    client_fld_names = list(_ for _ in filter_fields if _ not in ('AssId', 'ExtRefs', 'Products'))

    for as_cl in asd.clients:
        # ass_id, ac_id, _, sh_id, name, email, _, _, _ = as_cl
        ass_id = as_cl.val('AssId')
        match_val = as_cl.val(match_field)
        if not match_val:
            if _debug_level >= DEBUG_LEVEL_VERBOSE:
                log_warning("{} - AssCache client has empty value within the match field {}: {}"
                            .format(ass_id, match_field, as_cl), ctx)
            continue

        if match_field == SH_DEF_SEARCH_FIELD:
            sh_ids = [match_val]
        else:
            sh_ids = asd.sh_guest_ids(match_field, match_val)
            if not sh_ids:
                log_warning("{} - AssCache client Sihot guest id search via match field {}={} failed: {}"
                            .format(ass_id, match_field, match_val, as_cl), ctx)
                continue
            elif len(sh_ids) > 1:
                log_warning("{} - AssCache client Sihot guest id search via {}={} returned multiple/{} guests: {}"
                            .format(ass_id, match_field, match_val, len(sh_ids), as_cl), ctx, importance=3)
        for sh_id in sh_ids:
            shd = client_data(cae, sh_id)
            if not shd:
                log_warning("{} - AssCache guest object ID {} not found in Sihot: {}".format(ass_id, sh_id, as_cl), ctx,
                            importance=4)
                continue

            di = "; REC: ass={} sh={}".format(as_cl, shd) if _debug_level >= DEBUG_LEVEL_VERBOSE else ""
            for fld_name in client_fld_names:
                ass_val = as_cl.val(fld_name)
                sh_val = shd.val(fld_name)
                if not ass_val and not sh_val:
                    continue
                if isinstance(sh_val, list):
                    sh_values = [to_ascii(_).lower() for _ in sh_val]     # always do a fuzzy compare of Sihot values
                    if to_ascii(ass_val).lower() not in sh_values:
                        log_warning("{} - {} not found. ass={} sh={}{}".format(ass_id, fld_name, ass_val, sh_val, di),
                                    ctx)
                elif to_ascii(ass_val).lower() != to_ascii(sh_val).lower():
                    log_warning("{} - {} mismatch. ass={} sh={}{}".format(ass_id, fld_name, ass_val, sh_val, di), ctx)

            if 'ExtRefs' in filter_fields:
                pass    # NOT IMPLEMENTED
            if 'Products' in filter_fields:
                pass    # not implemented

    log_warning("No Sihot discrepancies found" if len(warn_log) == cnt else "Number of Sihot discrepancies: {}"
                .format(len(warn_log) - cnt), ctx, importance=3)

    return ""


if [_ for _ in act_compares if _[2:3] == 'C']:
    log_warning("Preparing client data check/compare", 'veriPrep', importance=4)
    # fetch all (filtered) clients from AssCache if not loaded by a previous pull
    if not asd.clients:
        err = asd.as_clients_pull(where_group_order=act_record_filters.get('C'))
        if err:
            log_error("Clients load error: " + err, 'veriPrepErr', importance=3, exit_code=300)
for act_compare in act_compares:
    if act_compare[:2] == 'ac':
        if act_compare[2:3] == 'C':
            err = ac_compare_clients()
            if err:
                log_error(err, 'veriAcClients', importance=3, exit_code=303)
        elif act_compare[2:3] == 'P':
            log_error("Acumen Product Verification not implemented", 'veriAcProdNotImpl', importance=3, exit_code=330)
        elif act_compare[2:3] == 'R':
            log_error("Acumen Reservation Verification not implemented", 'veriAcRes', importance=3, exit_code=360)

    elif act_compare[:2] == 'sh':
        if act_compare[2:3] == 'C':
            err = sh_compare_clients()
            if err:
                log_error(err, 'veriShClients', importance=3, exit_code=402)
        else:
            log_error("Sihot Prod/Res verification not implemented", 'veriShNotImpl', importance=3, exit_code=495)

    elif act_compare[:2] == 'sf':
        if act_compare[2:3] == 'C':
            err = sf_compare_clients()
            if err:
                log_error(err, 'veriSfClients', importance=3, exit_code=501)
        else:
            log_error("Salesforce Prod/Res verification not implemented", 'veriSfNotImpl', importance=3, exit_code=591)
if [_ for _ in act_compares if _[2:3] == 'C'] and not act_record_filters.get('C') and not act_record_matches.get('C'):
    # if no record filters set, then also check/compare client external references integrity within the AssCache db
    asd.cl_compare_ext_refs()

'''
