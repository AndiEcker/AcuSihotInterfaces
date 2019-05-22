"""
    BssServer is listening on the SIHOT SXML interface for to propagate room check-ins/check-outs/move
    and reservation changes onto the AssCache/Postgres database.

    0.1     first beta.
    0.2     refactored using add_ass_options() and init_ass_data().
    0.3     added shClientIP config variable (because Sihot SXML push interface needs localhost instead of external IP).
    0.4     refactored Salesforce reservation upload/upsert (now using new APEX method reservation_upsert()).
    0.5     added sync caching methods *_sync_to_sf() for better error handling and conflict clearing.
    0.6     removed check of re-sync within handle_xml(), fixed bugs in SQL queries for to fetch next unsynced res/room.
    0.7     reset/resend ResSfId/rgr_sf_id to SF on err message fragments and added pprint/ppf().
    0.8     added SSL to postgres connection.
    0.9     added email notification on empty return values on res send to SF (from sf_conn.res_upsert()) - merged to
            sys_data_generic branch.
    1.0     Q&D fix for to not send any rental reservations.
    1.1     Fixed bug to not store rgr_sf_id into ass_cache.
    1.2     Changed DB-Locks to RLocks and added outer locking on transaction commit level.
    1.3     Fixed bug to not overwrite rgr_sf_id.
    2.0     First version after merge of sys_data_generic branch.
    2.1     Added send of occupants on room move to Salesforce.
    2.2     beautified and hardened error notification and logging.
    2.3     enhanced debug messages and error logging.
"""
import datetime
import threading
import time
from functools import partial
from traceback import format_exc
import pprint

from ae_db import NAMED_BIND_VAR_PREFIX, bind_var_prefix
from sys_data_ids import DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, SDI_ASS, SDF_SH_CLIENT_PORT, SDF_SH_XML_ENCODING, \
    SDI_ACU
from ae_sys_data import Record, FAD_ONTO
from ae_console_app import ConsoleApp, uprint
from ae_tcp import RequestXmlHandler, TcpServer, TCP_CONNECTION_BROKEN_MSG
from sxmlif import Request, ResChange, RoomChange, SihotXmlBuilder
from shif import client_data, ResFetch
from ass_sys_data import add_ass_options, init_ass_data, AssSysData

__version__ = '2.3'

cae = ConsoleApp(__version__, "Listening to Sihot SXML interface and updating AssCache/Postgres and Salesforce",
                 multi_threading=True)
cae.add_option('cmdInterval', "sync interval in seconds (pass 0 for always running sync to SF)", 369, 'l')
ass_options = add_ass_options(cae, client_port=12000, add_kernel_port=True)

debug_level = cae.get_option('debugLevel')
ass_data = init_ass_data(cae, ass_options)

interval = cae.get_option('cmdInterval')
uprint("Sync to SF interval: {} seconds".format(interval))

sys_conns = ass_data['assSysData']
if sys_conns.error_message:
    uprint("BssServer startup error initializing AssSysData: ", sys_conns.error_message)
    cae.shutdown(exit_code=9)

notification = ass_data['notification']

sys_conns.close_dbs()
sys_conns = ass_data['assSysData'] = None  # del/free not thread-save sys db connections


ppf = pprint.PrettyPrinter(indent=6, width=96, depth=9).pformat


log_lock = threading.Lock()


def log_msg(msg, *args, **kwargs):
    with log_lock:
        is_error = kwargs.get('is_error', False)
        notify = kwargs.get('notify', False)
        if is_error or notify or debug_level >= kwargs.get('minimum_debug_level', DEBUG_LEVEL_ENABLED):
            importance = kwargs.get('importance', 2)
            seps = '\n' * (importance - 2)
            msg = seps + ' ' * (4 - importance) + ('*' if is_error else '#') * importance + '  ' + msg
            if args:
                msg += " (args={})".format(ppf(args))
            uprint(msg)
            if notification and (is_error or notify):
                notification.send_notification(msg_body=msg, subject='BssServer notification', body_style='plain')


def proc_context(rec_ctx):
    ctx_str = ""
    if 'procedure' in rec_ctx:
        ctx_str += rec_ctx['procedure']
    ctx_str += "("

    if 'extended_oc' in rec_ctx:
        ctx_str += rec_ctx['extended_oc']
    elif 'oc' in rec_ctx:
        ctx_str += rec_ctx['oc']
    else:
        ctx_str += "??"
    ctx_str += ", "

    if 'ResRoomNo' in rec_ctx:
        ctx_str += rec_ctx['ResRoomNo'] + ", "
    if 'ResId' in rec_ctx:
        ctx_str += rec_ctx['ResId']
    if 'ResSubId' in rec_ctx:
        ctx_str += "/" + rec_ctx['ResSubId']
    if 'ResHotelId' in rec_ctx:
        ctx_str += "@" + rec_ctx['ResHotelId']

    ctx_str += "): "

    return ctx_str


def check_res_change_data(rec_ctx):
    """ TODO: migrate as field checker to SysDataMan or as generic ass_sys_data method for system comparing/checking
    Compare data from SXML request (OCs: CR, CI, CO and RM) with reservation data loaded directly from Sihot/ResFetch.

    :param rec_ctx:     current rec context dict with:
                        req_res_data:   original Sihot notification request.
                        sh_res_data:    full Sihot reservation data (fetched with ResFetch()).
                        ass_res_data:   cached data (res_groups and res_group_clients).
    """
    rrd = rec_ctx['req_res_data']
    srd = rec_ctx['sh_res_data']
    ard = rec_ctx['ass_res_data']
    if not rrd['rgr_obj_id'] == srd.val('ResObjId') == ard['rgr_obj_id']:
        # fetched res has obj id in ['RESERVATION', 'OBJID'], req in ['SIHOT-Document', 'SIHOT-Reservation', 'OBJID']
        log_msg(proc_context(rec_ctx) + "Sihot Reservation Object Id mismatch req/sh/ass={}/{}/{}"
                .format(rrd['rgr_obj_id'], srd.val('ResObjId'), ard['rgr_obj_id']), notify=True)
    if not rrd['rgr_ho_fk'] == srd.val('ResHotelId') == ard['rgr_ho_fk']:
        log_msg(proc_context(rec_ctx) + "Sihot Hotel Id mismatch req/sh/ass={}/{}/{}"
                .format(rrd['rgr_ho_fk'], srd.val('ResHotelId'), ard['rgr_ho_fk']), notify=True)
    if not rrd['rgr_res_id'] == srd.val('ResId') == ard['rgr_res_id']:
        log_msg(proc_context(rec_ctx) + "Sihot Res Id mismatch req/sh/ass={}/{}/{}"
                .format(rrd['rgr_res_id'], srd.val('ResId'), ard['rgr_res_id']), notify=True)
    if not rrd['rgr_sub_id'] == srd.val('ResSubId') == ard['rgr_sub_id']:
        log_msg(proc_context(rec_ctx) + "Sihot Res Sub Id mismatch req/sh/ass={}/{}/{}"
                .format(rrd['rgr_sub_id'], srd.val('ResSubId'), ard['rgr_sub_id']), notify=True)
    if not rrd['rgr_room_id'] == srd.val('ResRoomNo') == ard['rgr_room_id']:
        log_msg(proc_context(rec_ctx) + "Sihot Room No (main) mismatch req/sh/ass={}/{}/{}"
                .format(rrd['rgr_room_id'], srd.val('ResRoomNo'), ard['rgr_room_id']), notify=True)
    for idx, rgc in enumerate(rrd['ResPersons']):
        ard_room = ard.get('ResPersons')
        if ard_room:
            ard_room = ard_room[min(idx, len(ard_room) - 1)].get('rgc_room_id', '')
        if ard_room == list():
            ard_room = None
        if not rgc.get('rgc_room_id') == srd.val(idx, 'ResRoomNo') == ard_room:
            log_msg(proc_context(rec_ctx) + "Sihot Room No (rooming list) mismatch req/sh/ass={}/{}/{}"
                    .format(rrd.get('rgc_room_id'), srd.val(idx, 'ResRoomNo'), ard_room), notify=True)


def res_from_sh_to_sf(asd, ass_changed_res):
    ho_id, res_id, sub_id = ass_changed_res['rgr_ho_fk'], ass_changed_res['rgr_res_id'], ass_changed_res['rgr_sub_id']
    msg_pre = "res_from_sh_to_sf({}/{}@{}): ".format(res_id, sub_id, ho_id)
    log_msg(msg_pre + "sync reservation from SH Object Id={} to SF Opp Id={}"
            .format(ass_changed_res['rgr_obj_id'], ass_changed_res['rgr_sf_id']),
            importance=4, notify=debug_level >= DEBUG_LEVEL_VERBOSE)

    sh_res = ResFetch(cae).fetch_by_res_id(ho_id, res_id, sub_id)
    if not isinstance(sh_res, Record):
        return sh_res

    sh_cl = None
    sh_id = sh_res.val('ShId')     # ==ass_cache/rgr_order_cl_fk->cl_sh_id
    if sh_id:
        sh_cl = client_data(cae, sh_id)
    if not isinstance(sh_cl, dict):
        log_msg(msg_pre + "guest not found; objId={}; ass=\n{};\n sh_cl=\n{}"
                .format(sh_id, ppf(ass_changed_res), ppf(sh_cl)), notify=debug_level >= DEBUG_LEVEL_VERBOSE)
        sh_cl = Record()

    rgr_sf_id = ass_res_sf_id = ass_changed_res['rgr_sf_id']
    if not rgr_sf_id:
        # try to assign ResOpp-ID (of record type Service Center Booking) from Acumen MS_SF_DL_ID onto rgr_sf_id
        obj_id = ass_changed_res['rgr_obj_id']
        if obj_id:
            res = asd.load_view(asd.connection(SDI_ACU), 'T_RU inner join T_MS on RU_MLREF = MS_MLREF', ['MS_SF_DL_ID'],
                                "RU_SIHOT_OBJID = " + NAMED_BIND_VAR_PREFIX + bind_var_prefix + "obj_id",
                                dict(obj_id=obj_id))
            if res and res[0] and res[0][0]:
                rgr_sf_id = res[0][0]
        if not rgr_sf_id:
            log_msg(msg_pre + "Reservation Opportunity ID not found; ShResObjID={}; ass=\n{}; sh_res=\n{}; err?={}"
                    .format(obj_id, ppf(ass_changed_res), ppf(sh_res), asd.error_message),
                    notify=debug_level >= DEBUG_LEVEL_VERBOSE)

    ass_res = Record(system=SDI_ASS, direction=FAD_ONTO)
    if not asd.res_save(sh_res, ass_res_rec=ass_res):
        return asd.error_message

    # convert sh xml and ass_cache db columns to fields, and then push to Salesforce server via APEX method call
    err_msg = asd.sf_ass_res_upsert(rgr_sf_id, sh_cl, ass_res)
    if err_msg:
        ass_conn = asd.connection(SDI_ASS, raise_if_error=False)
        roll_back_msg = ass_conn.rollback() if ass_conn else "Ass Db connection broken"
        return msg_pre + "SF reservation push/update err='{}'; ass=\n{}; rollback='{}'" \
            .format(err_msg, ppf(ass_changed_res), roll_back_msg)

    # no errors on sync to SF, then set last sync timestamp
    chk_values = dict(rgr_ho_fk=ho_id, rgr_res_id=res_id, rgr_sub_id=sub_id)
    upd_values = dict(rgr_last_sync=ass_changed_res['rgr_last_sync'])
    if not ass_res_sf_id and rgr_sf_id:
        upd_values['rgr_sf_id'] = rgr_sf_id
    if not asd.rgr_upsert(upd_values, chk_values, commit=True):
        err_msg = msg_pre + "last reservation sync timestamp ass_cache update failed with err='{}'; ass=\n{}" \
                      .format(asd.error_message, ppf(ass_changed_res))

    return err_msg


def room_change_to_sf(asd, ass_res):
    ho_id, res_id, sub_id = ass_res['rgr_ho_fk'], ass_res['rgr_res_id'], ass_res['rgr_sub_id']
    sf_res_id = ass_res['rgr_sf_id']
    msg_pre = "room_change_to_sf({}/{}@{}): ".format(res_id, sub_id, ho_id)
    log_msg(msg_pre + "sync room change from SH Object Id={} to SF Opp Id={}"
            .format(ass_res['rgr_obj_id'], sf_res_id),
            importance=4, notify=debug_level >= DEBUG_LEVEL_VERBOSE)

    err_msg = asd.sf_ass_room_change(sf_res_id, ass_res['rgr_time_in'], ass_res['rgr_time_out'], ass_res['rgr_room_id'])
    if err_msg:
        return msg_pre + "SF room push/update err='{}'; ass=\n{}".format(err_msg, ppf(ass_res))

    # no errors on sync to SF, then set last sync timestamp
    chk_values = dict(rgr_ho_fk=ho_id, rgr_res_id=res_id, rgr_sub_id=sub_id)
    if not asd.rgr_upsert(dict(rgr_room_last_sync=ass_res['rgr_room_last_sync']), chk_values, commit=True):
        err_msg = msg_pre + "last room sync timestamp ass_cache update err='{}'; ass=\n{}" \
                      .format(asd.error_message, ppf(ass_res))

    # optionally send occupants data if roomChangeWithOccupants config var is set (hot reloaded w/o server restart)
    with_occ = asd.cae.get_config('roomChangeWithOccupants')
    if with_occ:
        occ_msg = asd.sf_res_occupants_upsert(sf_res_id, ho_id, res_id, sub_id, with_occ)   # ignore any errors
        if occ_msg:
            log_msg(msg_pre + "occupants send err={}; SfOppId={}".format(sf_res_id, occ_msg),
                    notify=debug_level >= DEBUG_LEVEL_VERBOSE)

    return err_msg


# variables for to control sync runs (using separate timer-thread)
sync_run_requested = None
sync_timer = None
sync_lock = threading.Lock()
lock_timeout = datetime.timedelta(seconds=interval * 18)


def check_and_init_sync_to_sf(wait=0.0):
    global sync_run_requested, sync_timer

    # experienced strange locking where sync_run_requested was set but run_sync_to_sf() was no longer running
    now = datetime.datetime.now()
    if sync_run_requested and now - sync_run_requested > lock_timeout:
        log_msg("check_and_init_sync_to_sf({}): {}locked sync lock timeout after {}; resetting timer {} requested at {}"
                .format(wait, "" if sync_lock.locked() else "UN", lock_timeout, sync_timer, sync_run_requested),
                importance=4, notify=True)
        sync_run_requested = None
        if sync_timer:
            sync_timer.cancel()
            sync_timer = None
        if sync_lock:
            sync_lock.release()

    # check if run_sync_to_sf() is running or requested to run soon, and if not then start new timer
    locked = sync_run_requested or sync_timer or not sync_lock.acquire(blocking=False)
    if locked:
        log_msg("check_and_init_sync_to_sf({}): sync to SF request blocked; last request was at {}; timer-obj={}"
                .format(wait, sync_run_requested, sync_timer),
                importance=4, notify=debug_level >= DEBUG_LEVEL_VERBOSE)
    else:
        sync_run_requested = now
        sync_timer = threading.Timer(wait, run_sync_to_sf)
        log_msg("check_and_init_sync_to_sf({}): new sync to SF; requested at {}; will run at {}; timer-obj={}"
                .format(wait, sync_run_requested, sync_run_requested + datetime.timedelta(seconds=wait), sync_timer),
                importance=4, notify=debug_level > DEBUG_LEVEL_VERBOSE)
        sync_timer.start()

    return not locked


def run_sync_to_sf():
    global sync_run_requested, sync_timer
    asd = None
    err_msg = ""
    sync_count = 0
    try:
        asd = AssSysData(cae, err_logger=partial(log_msg, is_error=True), warn_logger=log_msg)
        ass_id_cols = ['rgr_sf_id', 'rgr_obj_id', 'rgr_ho_fk', 'rgr_res_id', 'rgr_sub_id']
        room_cols = ['rgr_room_last_change', 'rgr_time_in', 'rgr_time_out', 'rgr_room_id'] + ass_id_cols
        while True:
            res_changed = room_changed = None
            action_time = datetime.datetime.now()

            res_list = asd.rgr_fetch_list(['rgr_last_change', ] + ass_id_cols,
                                          where_group_order="(rgr_last_sync IS null OR rgr_last_change > rgr_last_sync)"
                                                            " AND rgr_last_change IS NOT null"
                                                            " ORDER BY rgr_last_change LIMIT 1")
            if res_list:
                res_changed = res_list[0][0]
            elif asd.error_message:
                err_msg = asd.error_message
                break

            room_list = asd.rgr_fetch_list(room_cols, where_group_order="rgr_sf_id != '' "
                                                                        "AND rgr_room_last_change IS NOT null "
                                                                        "AND (rgr_room_last_sync IS null"
                                                                        " OR rgr_room_last_change > rgr_room_last_sync)"
                                                                        " ORDER BY rgr_room_last_change LIMIT 1")
            if room_list:
                room_changed = room_list[0][0]
            elif asd.error_message:
                err_msg = asd.error_message
                break

            if res_changed and (not room_changed or res_changed <= room_changed):
                ass_res = dict(zip(ass_id_cols, res_list[0][1:]))
                ass_res['rgr_last_sync'] = action_time
                log_msg("run_sync_to_sf() fetch from Sihot and send to SF the changed res=\n{}".format(ppf(ass_res)),
                        notify=debug_level >= DEBUG_LEVEL_VERBOSE)
                err_msg = res_from_sh_to_sf(asd, ass_res)
            elif room_changed and (not res_changed or room_changed < res_changed):
                ass_res = dict(zip(room_cols, room_list[0]))
                ass_res['rgr_room_last_sync'] = action_time
                log_msg("run_sync_to_sf() send to SF the room change ass=\n{}".format(ppf(ass_res)),
                        notify=debug_level >= DEBUG_LEVEL_VERBOSE)
                err_msg = room_change_to_sf(asd, ass_res)
            else:
                break
            if err_msg:
                break
            sync_count += 1

    except Exception as ex:
        err_msg += "exception='{}'\n{}".format(ex, format_exc())
    finally:
        if asd:
            asd.close_dbs()

    notify = debug_level > DEBUG_LEVEL_VERBOSE or debug_level > DEBUG_LEVEL_ENABLED and sync_count
    log_msg("run_sync_to_sf() requested at {}; processed {} syncs; finished at {}; err?={}"
            .format(sync_run_requested, sync_count, datetime.datetime.now(), err_msg),
            importance=3, is_error=bool(err_msg), notify=notify)

    sync_timer = None
    sync_run_requested = None
    sync_lock.release()

    while not check_and_init_sync_to_sf(interval):
        time.sleep(interval)


def oc_keep_alive(_, __, ___):
    # no request-/error-checks needed on operation codes: LA=Link Alive, TS=Time Sync, ACK=Acknowledge
    return ""


def oc_res_change(asd, req, rec_ctx):
    """
    Process Sihot Change Reservation operation code (CR) by saving Ids and update timestamp to ass_cache database.
    :param asd:         AssSysData instance, created for this notification.
    :param req:         Reservation Response class instance (with parsed Sihot XML data of CR-notification).
    :param rec_ctx:     dict with context info (ids and actions).
    :return:            error message(s) or empty string/"" if no errors occurred.
    """
    action_time = datetime.datetime.now()
    errors = list()
    rec_ctx['oc'] = req.oc     # == 'CR'
    rgr_list = req.rgr_list
    for idx, req_rgr in enumerate(rgr_list):
        rooming_list_room_no = (req_rgr.get('ResPersons') or [dict(), ])[0].get('rgc_room_id', '')
        rec_ctx.update(req_res_data=req_rgr,
                       ResObjId=req_rgr.get('rgr_obj_id', ''),
                       ResHotelId=getattr(req, 'hn', None),
                       ResId=req_rgr.get('rgr_res_id', ''),
                       ResSubId=req_rgr.get('rgr_sub_id', ''),
                       ResRoomNo=req_rgr.get('rgr_room_id', rooming_list_room_no),
                       )
        log_msg(proc_context(rec_ctx) + "res change data=\n{}".format(ppf(req_rgr)),
                importance=4, notify=debug_level >= DEBUG_LEVEL_VERBOSE)

        # QUICK&DIRTY FIX: prevent the send of rental client reservations using roAgencies ini variable (rgr_mkt_group
        # .. is empty (?!?!?) for most of the rental bookings, but should be 'RS')
        if req_rgr.get('rgr_mkt_segment', '') in [a[0] for a in asd.ro_agencies]:
            # rental mkt segment found in CR request via the element path: ['SIHOT-Reservation', 'SIHOT-Person', 'MC']
            log_msg(proc_context(rec_ctx) + "RES CHANGE SKIP", importance=4, notify=debug_level >= DEBUG_LEVEL_VERBOSE)
            return ""

        chk_values = {k: v for k, v in req_rgr.items() if k in ['rgr_res_id', 'rgr_sub_id']}
        chk_values.update(rgr_ho_fk=getattr(req, 'hn', None))
        upd_col_values = chk_values.copy()
        upd_col_values.update(rgr_last_change=action_time)
        if req_rgr.get('rgr_obj_id', ''):
            upd_col_values.update(rgr_obj_id=req_rgr.get('rgr_obj_id', ''))
        asd.rgr_upsert(upd_col_values, chk_values=chk_values, commit=True)
        if asd.error_message:
            err_msg = proc_context(rec_ctx) + "ass res change error='{}'".format(asd.error_message)
            log_msg(err_msg, importance=3, is_error=True)
            errors.append(err_msg)
            asd.error_message = ""

    return "\n".join(errors)


def _room_change_ass(asd, req, rec_ctx, oc, sub_no, room_id, action_time):
    ho_id = req.hn
    res_no = req.res_nr
    rec_ctx.update(ResHotelId=ho_id, ResId=res_no, ResSubId=sub_no, ResRoomNo=room_id,
                   extended_oc=oc, action_time=action_time)
    log_msg(proc_context(rec_ctx) + "{} room change; ctx=\n{}\nxml=\n{}".format(oc, ppf(rec_ctx), req.get_xml()),
            importance=3, notify=debug_level >= DEBUG_LEVEL_VERBOSE)

    # QUICK&DIRTY FIX: prevent the send of rental client allocations using roAgencies ini variable
    if req.mc in [a[0] for a in asd.ro_agencies]:           # rental mkt segment found in MC element of CI/CO/RM request
        log_msg(proc_context(rec_ctx) + "ROOM CHANGE SKIP", importance=4, notify=debug_level >= DEBUG_LEVEL_VERBOSE)
        return ""
    # RM oc gets normally changed into CI-RM/CO-RM/RC-RM, but in this case (SUB-NR > 1) we simply ignoring this RM
    if oc == 'RM':
        log_msg(proc_context(rec_ctx) + "IGNORING ROOM CHANGE", importance=4, notify=debug_level >= DEBUG_LEVEL_VERBOSE)
        return ""

    rgr_sf_id = asd.sh_room_change_to_ass(oc, ho_id, res_no, sub_no, room_id, action_time)
    if rgr_sf_id:
        rec_ctx.update(ResSfId=rgr_sf_id)
        err_msg = ""
    else:
        err_msg = asd.error_message

    return err_msg


def oc_room_change(asd, req, rec_ctx):
    action_time = datetime.datetime.now()
    rec_ctx['oc'] = oc = req.oc     # == 'CI'|'CO'|'RM'
    err_msg = ""

    if oc == 'RM':
        if req.osub_nr:
            err_msg = _room_change_ass(asd, req, rec_ctx, 'CO-RM', req.osub_nr, req.orn, action_time)
            oc = 'CI-RM'
        elif req.sub_nr == '1':
            ''' received meanwhile also RM notifications w/o OSUB-NR and with SUB-NR > 1 (see Sihot AssCache log entry):
            20180922 010727.305[XML-IF]: onReceive: RM
            : <OC>RM</OC><HN>4</HN>...<RN>0525</RN>...<ORN>0425</ORN>
            ...<GDSNO>BDC-1099776257</GDSNO>...<RES-NR>77729</RES-NR><SUB-NR>2</SUB-NR>
            20180922 010727.305[XML-IF]: Hotel number = 4 found
            '''
            oc = 'RC-RM'            # reservation and in/out dates keep the same, only room number will be changed
    err_msg += _room_change_ass(asd, req, rec_ctx, oc, req.sub_nr, req.rn, action_time)

    if err_msg:
        log_msg(proc_context(rec_ctx) + "ass room change error='{}'".format(err_msg), importance=3, is_error=True)

    return err_msg


# supported operation codes (stored in BssServer.ini) with related request class and operation code handler/processor
SUPPORTED_OCS = dict()
# operation codes that will not be processed (no notification will be sent to user, only ACK will be send back to Sihot)
IGNORED_OCS = []


def reload_oc_config():
    """ allow to change processing of OCs without the need to restart this server """
    global SUPPORTED_OCS, IGNORED_OCS
    _ = (Request, ResChange, RoomChange)    # added for to hide PyCharm warnings (Unused import)

    # always reload on server startup, else first check if main config file has changed since server startup
    if SUPPORTED_OCS and not cae.config_main_file_modified():
        return ""

    # main config file has changed - so reload the changed configuration settings
    cae.load_config()
    SUPPORTED_OCS = cae.get_config('SUPPORTED_OCS')
    if not SUPPORTED_OCS or not isinstance(SUPPORTED_OCS, dict):
        return "SUPPORTED_OCS is not or wrongly defined in main CFG/INI file"   # cae._main_cfg_fnam
    module_declarations = globals()
    for oc, slots in SUPPORTED_OCS.items():
        if not isinstance(slots, list):
            return "SUPPORTED_OCS {} slots syntax error - list expected but got {}".format(oc, ppf(slots))
        for slot in slots:
            if not isinstance(slot, dict):
                return "SUPPORTED_OCS {} slot syntax error - dict expected but got {}".format(oc, ppf(slot))
            if 'reqClass' not in slot or 'ocProcessors' not in slot:
                return "SUPPORTED_OCS {} slot keys reqClass/ocProcessors missing - got {}".format(oc, ppf(slot))

            req_class = slot['reqClass']
            if req_class not in module_declarations:
                return "SUPPORTED_OCS {} slot key reqClass {} is not implemented".format(oc, req_class)
            slot['reqClass'] = module_declarations[req_class]

            mod_decs = list()
            for proc in slot['ocProcessors']:
                if proc not in module_declarations:
                    return "SUPPORTED_OCS {} slot key ocProcessor {} is not implemented".format(oc, proc)
                mod_decs.append(module_declarations[proc])
            slot['ocProcessors'] = mod_decs

    IGNORED_OCS = cae.get_config('IGNORED_OCS')
    if not isinstance(IGNORED_OCS, list):
        return "IGNORED_OCS is not or wrongly defined in main CFG/INI file - invalid value {}".format(IGNORED_OCS)

    return ""


def _parse_core_value(request, tag, default=''):
    """
    mini parser for to get the main/core values from a xml request
    :param request:     xml request string.
    :return:            string value of tag/element value.
    """
    ret = default
    pos1 = request.find('<' + tag + '>')
    if pos1 != -1:
        pos1 += len(tag) + 2
        pos2 = request.find('</' + tag + '>', pos1)
        if pos2 - pos1 > 0:
            ret = request[pos1:pos2]
    return ret


def operation_code(request):
    return _parse_core_value(request, 'OC')


def transaction_no(request):
    return _parse_core_value(request, 'TN', default='696969')


def organization_name(request):
    return _parse_core_value(request, 'ORG')


def ack_response(transaction_number, ret_code, org='', msg='', status=''):
    resp = SihotXmlBuilder(cae)
    resp.beg_xml(operation_code='ACK', transaction_number=transaction_number)
    resp.add_tag('RC', str(ret_code))
    if msg:
        resp.add_tag('MSG', msg)
    if status:
        resp.add_tag('STATUS', status)
    if org:
        resp.add_tag('ORG', org)
    resp.end_xml()
    return resp.xml


class SihotRequestXmlHandler(RequestXmlHandler):
    def notify(self):
        # hide timeout or dropped connection error (Sihot client does not close connection properly)
        if TCP_CONNECTION_BROKEN_MSG not in self.error_message:
            log_msg(self.error_message, is_error=True, importance=4)

    def handle_xml(self, xml_from_client):
        """ types of parameter xml_from_client and return value are bytes """
        xml_enc = cae.get_option(SDF_SH_XML_ENCODING)
        xml_request = str(xml_from_client, encoding=xml_enc)
        log_msg("BssServer.handle_xml(): req='{}'".format(xml_request), minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        # classify request for to also respond on error (e.g. if config_reload/xml_parsing failed)
        oc = operation_code(xml_request)
        tn = transaction_no(xml_request)
        org = organization_name(xml_request)

        err_messages = list()

        try:
            msg = reload_oc_config()
            if msg:
                err_messages.append((90, msg + " (OC={})".format(oc)))
        except Exception as ex:
            err_messages.append((93, "load config {} exception: '{}'\n{}".format(oc, ex, format_exc())))

        if err_messages:
            pass
        elif oc in SUPPORTED_OCS:
            sys_connections = None
            try:
                sys_connections = AssSysData(cae, err_logger=partial(log_msg, is_error=True), warn_logger=log_msg)
                if sys_connections.error_message or not sys_connections.connection(SDI_ASS, raise_if_error=False):
                    err_messages.append((95, "AssSysData instantiation fail: {}".format(sys_connections.error_message)))
                else:
                    rec_ctx = dict(procedure='sys_conn')
                    for slot in SUPPORTED_OCS[oc]:
                        req_class = slot['reqClass']
                        rec_ctx['procedure'] = req_class.__name__
                        req = req_class(cae)
                        req.parse_xml(xml_request)
                        if debug_level >= DEBUG_LEVEL_VERBOSE:
                            err_messages.append((0, "Slot {}:\n{}\ngot xml=\n{}".format(slot, ppf(req), req.get_xml())))
                        for proc in slot['ocProcessors']:
                            rec_ctx['procedure'] = proc.__name__
                            try:
                                msg = proc(sys_connections, req, rec_ctx)
                                if msg:
                                    err_messages.append((96, proc_context(rec_ctx) + "call error '{}'".format(msg)))
                            except Exception as ex:
                                err_messages.append((97, proc_context(rec_ctx)
                                                     + "call exception: '{}'\n{}".format(ex, format_exc())))
                            sys_connections.error_message = ""  # reset error message for next loop/proc
            except Exception as ex:
                err_messages.append((99, "slot exception: '{}'\n{}".format(ex, format_exc())))
            finally:
                if sys_connections:
                    err = sys_connections.close_dbs()
                    if err:
                        err_messages.append((101, "database disconnection error: {}".format(err)))
        elif oc in IGNORED_OCS:
            if debug_level >= DEBUG_LEVEL_VERBOSE:
                err_messages.append((0, "(ignored operation-code/OC '{}')".format(oc)))
        else:
            err_messages.append((102, "empty/invalid operation code '{}'".format(oc)))

        last_err = 0
        for err_code, msg in err_messages:
            if err_code:
                log_msg(msg + " Err={}".format(err_code), is_error=True, importance=3)
                last_err = err_code
            else:
                log_msg(msg, minimum_debug_level=DEBUG_LEVEL_ENABLED)

        msg = "BssServer.handle_xml(): " + ("\n    ** ".join([_[1] for _ in err_messages if _[0]]) or "OK")
        xml_response = ack_response(tn, last_err, org=org, msg=msg, status='1' if oc == 'LA' else '')
        log_msg("OC {} processed; xml response: {}".format(oc, xml_response), importance=4)

        # directly sync to Salesforce if not already running (also in case the time thread died)
        # ae:25-09-18 13:39 commented out next line
        # check_and_init_sync_to_sf()

        return bytes(xml_response, xml_enc)


try:
    # before starting server try to sync all the past reservation changes to SF
    check_and_init_sync_to_sf()

    # ?!?!?: if sihot is connecting as client then our listening server ip has to be either localhost or 127.0.0.1
    # .. and for connect to the Sihot WEB/KERNEL interfaces only the external IP address of the Sihot server is working
    ip_addr = cae.get_config('shClientIP', default_value=cae.get_option('shServerIP'))
    uprint("Sihot client IP/port:", ip_addr, cae.get_option(SDF_SH_CLIENT_PORT))
    server = TcpServer(ip_addr, cae.get_option(SDF_SH_CLIENT_PORT), SihotRequestXmlHandler, debug_level=debug_level)
    server.run(display_animation=cae.get_config('displayAnimation', default_value=False))
except (OSError, Exception) as tcp_ex:
    log_msg("TCP server could not be started. Exception: {}".format(tcp_ex), is_error=True)
    cae.shutdown(369)

if sync_timer:
    sync_timer.cancel()
cae.shutdown()
