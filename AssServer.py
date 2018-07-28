"""
    AssServer is listening on the SIHOT SXML interface for to propagate room check-ins/check-outs/move
    and reservation changes onto the AssCache/Postgres database.

    0.1     first beta.
    0.2     refactored using add_ass_options() and init_ass_data().
    0.3     added shClientIP config variable (because Sihot SXML push interface needs localhost instead of external IP).
    0.4     refactored Salesforce reservation upload/upsert (now using new APEX method reservation_upsert()).
"""
import datetime
from traceback import format_exc

from ae_console_app import (ConsoleApp, uprint, missing_requirements,
                            DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE)
from ae_tcp import RequestXmlHandler, TcpServer, TCP_CONNECTION_BROKEN_MSG
from sxmlif import Request, ResChange, RoomChange, SihotXmlBuilder, ResFetch
from shif import elem_value, guest_data
from ass_sys_data import add_ass_options, init_ass_data, AssSysData

__version__ = '0.4'

cae = ConsoleApp(__version__, "Listening to Sihot SXML interface and updating AssCache/Postgres, Acumen and Salesforce",
                 multi_threading=True)
ass_options = add_ass_options(cae, client_port=12000)

debug_level = cae.get_option('debugLevel')
ass_data = init_ass_data(cae, ass_options)
sys_conns = ass_data['assSysData']
if sys_conns.error_message:
    uprint("AssServer startup error: ", sys_conns.error_message)
    cae.shutdown(exit_code=9)
mr = missing_requirements(sys_conns, [['ass_db'], ['acu_db'], ['sf_conn'], ['sh_conn']], bool_check=True)
if mr:
    uprint("Invalid connection-credentials/-configuration of the external systems:", mr)
    cae.shutdown(exit_code=12)
sys_conns = ass_data['assSysData'] = None       # del/free not thread-save sys db connections
notification = ass_data['notification']


def log_msg(msg, *args, **kwargs):
    is_error = kwargs.get('is_error', False)
    if debug_level < kwargs.get('minimum_debug_level', DEBUG_LEVEL_VERBOSE) and not is_error:
        return
    importance = kwargs.get('importance', 2)
    seps = '\n' * (importance - 2)
    msg = seps + ' ' * (4 - importance) + ('*' if is_error else '#') * importance + '  ' + msg
    if args:
        msg += " (args={})".format(args)
    uprint(msg)
    if notification and (is_error or kwargs.get('notify', False)):
        notification.send_notification(msg_body=msg, subject='AssServer notification')


def proc_context(recs_ctx):
    ctx_str = ""
    if 'procedure' in recs_ctx:
        ctx_str += recs_ctx['procedure']
    ctx_str += "("

    # check for record specific context within recs_ctx['records'][recs_ctx['record_idx']]
    rec_idx = recs_ctx['record_idx']
    rec_ctx = recs_ctx['records'][rec_idx] if rec_idx >= 0 else recs_ctx

    if 'extended_oc' in rec_ctx:
        ctx_str += rec_ctx['extended_oc']
    elif 'oc' in recs_ctx:
        ctx_str += recs_ctx['oc']
    else:
        ctx_str += "??"
    ctx_str += ", "

    if 'RoomNo' in rec_ctx:
        ctx_str += rec_ctx['RoomNo'] + ", "

    if 'ResId' in rec_ctx:
        ctx_str += rec_ctx['ResId']
    if "SubId" in rec_ctx:
        ctx_str += "/" + rec_ctx['SubId']
    if "HotelId" in rec_ctx:
        ctx_str += "@" + rec_ctx['HotelId']

    ctx_str += ")"

    return ctx_str


def oc_keep_alive(_, __, ___):
    # no request-/error-checks needed on operation codes: LA=Link Alive, TS=Time Sync, ACK=Acknowledge
    return ""


def check_res_change_data(recs_ctx):
    """
    Compare data from SXML request (OCs: CR, CI, CO and RM) with reservation data loaded directly from Sihot/ResFetch.

    :param recs_ctx:    current context record, with records item containing for each idx:
                        req_res_data:   original Sihot notification request.
                        sh_res_data:    full Sihot reservation data (fetched with ResFetch()).
                        ass_res_data:   cached data (res_groups and res_group_clients).
    """
    log_msg(proc_context(recs_ctx) + "/check_res_change_data()")
    rec_ctx = recs_ctx['records'][recs_ctx['record_idx']]
    rrd = rec_ctx['req_res_data']
    srd = rec_ctx['sh_res_data']
    ard = rec_ctx['ass_res_data']
    assert rrd['rgr_sh_id'] == elem_value(srd, ['RESCHANNELLIST', 'RESCHANNEL', 'OBJID']) == ard['rgr_sh_id']
    assert rrd['rgr_ho_fk'] == elem_value(srd, 'RES-HOTEL') == ard['rgr_ho_fk']
    assert rrd['rgr_res_id'] == elem_value(srd, 'RES-NR') == ard['rgr_res_id']
    assert rrd['rgr_sub_id'] == elem_value(srd, 'SUB-NR') == ard['rgr_sub_id']
    for idx, rgc in enumerate(rrd['rgc_list']):
        assert rgc['rgc_room_id'] == elem_value(srd, ['PERSON', 'RN'], arri=idx) == ard['rgc_list'][idx]['rgc_room_id']


def oc_res_change_ass(conf_data, req, recs_ctx):
    """
    Process Sihot Change Reservation operation code (CR) by fetching full reservation data and saving it to ass_cache
    database. Note: this method has to be the first method in the CR slot because oc_res_change_sf() using the fetched
    reservation data records stored in recs_ctx['records'].
    :param conf_data:   AssSysData instance, created for this notification.
    :param req:         Reservation Response class instance (with parsed Sihot XML data of CR-notification).
    :param recs_ctx:    dict with records list and other context info.
    :return:            error message(s) or empty string/"" if no errors occurred.
    """
    recs_ctx['oc'] = req.oc     # == 'CR'
    # recs_ctx['record_idx'] = -1
    errors = list()
    rgr_list = req.rgr_list
    for idx, req_rgr in enumerate(rgr_list):
        obj_id = req_rgr.get('rgr_obj_id', '')
        ho_id = getattr(req, 'hn', None)
        res_id = req_rgr.get('rgr_res_id', '')
        sub_id = req_rgr.get('rgr_sub_id', '')
        room_no = req_rgr.get('rgc_list', [dict(), ])[0].get('rgc_room_id', '')
        recs_ctx['records'].append(dict(req_res_data=req_rgr,
                                        ObjId=obj_id, HotelId=ho_id, ResId=res_id, SubId=sub_id, RoomNo=room_no))
        assert idx == len(recs_ctx['records']) - 1
        recs_ctx['record_idx'] = idx
        log_msg(proc_context(recs_ctx) + " res change data={}".format(req_rgr), importance=4)

        res_data = ResFetch(cae).fetch_by_res_id(ho_id, res_id, sub_id)
        if not isinstance(res_data, dict):
            errors.append(proc_context(recs_ctx) + ":" + res_data)
            continue
        recs_ctx['records'][idx]['sh_res_data'] = res_data

        cached_rgr = dict()
        conf_data.sh_res_change_to_ass(res_data, rgr_dict=cached_rgr)
        if conf_data.error_message:
            errors.append(proc_context(recs_ctx) + ":" + conf_data.error_message)
            continue

        recs_ctx['records'][idx]['ass_res_data'] = cached_rgr
        if debug_level >= DEBUG_LEVEL_VERBOSE:  # only in verbose debug mode: compare res-changed and fetched rgr
            check_res_change_data(recs_ctx['records'][idx])

        if cached_rgr['rgr_order_cl_fk']:
            recs_ctx['records'][idx]['sh_cl_data'] = guest_data(conf_data.cae, cached_rgr['rgr_order_cl_fk'])

    return "\n".join(errors)


def oc_res_change_sf(conf_data, req, recs_ctx):
    # already set in oc_res_change_ass: recs_ctx['oc'] = req.oc  # == 'CR'
    errors = list()
    for idx, res_cached in enumerate(recs_ctx['records']):
        recs_ctx['record_idx'] = idx
        ard = res_cached['ass_res_data']
        obj_id = ard['rgr_obj_id']

        if debug_level >= DEBUG_LEVEL_VERBOSE:  # only in verbose debug mode: compare res-changed and fetched rgr
            assert req.rgr_list[idx] == res_cached['req_res_data']
            check_res_change_data(recs_ctx)

        # determine SF Reservation Opportunity ID - if already exists
        rgr_sf_id = None
        rgr_pk = ard['rgr_pk']
        res = conf_data.rgr_fetch_list(['rgr_sf_id'], dict(rgr_pk=rgr_pk))    # SF Reservation Opportunity ID
        if conf_data.error_message:
            errors.append(proc_context(recs_ctx) + ":" + conf_data.error_message)
            conf_data.error_message = ""
            continue
        if res and res[0] and res[0][0]:
            rgr_sf_id = res[0][0]
        else:
            res = conf_data.load_view(conf_data.acu_db, 'T_RU inner join T_MS on RU_MLREF = MS_MLREF', ['MS_SF_DL_ID'],
                                      "RU_SIHOT_OBJID = :obj_id", dict(obj_id=obj_id))
            if res and res[0] and res[0][0]:
                rgr_sf_id = res[0][0]
            else:
                err_msg = conf_data.error_message
                log_msg(proc_context(recs_ctx) + " Sihot Opportunity ID {} not found; err={}".format(obj_id, err_msg))
                conf_data.error_message = ""

        # convert sh xml and ass_cache db columns to fields, and then push to Salesforce server via APEX method call
        err_msg = conf_data.sf_res_upsert(rgr_sf_id, res_cached.get('sh_cl_data'), ard)
        # !!!!  MERGE WITH NEXT VERSION sys_data_generic BRANCH
        # res_fields = conf_data.flds_from_sh(res_cached.get('sh_cl_data'))
        # res_fields.update(conf_data.flds_from_ass(ard))
        # err_msg = conf_data.sf_res_upsert(res_fields, dict(rgr_sf_id=rgr_sf_id))  # (col_values, chk_values)

        if err_msg:
            errors.append(proc_context(recs_ctx) + ": SF Opportunity push/update err={}".format(err_msg))
            conf_data.ass_db.rollback()
        else:
            conf_data.acu_db.commit()

    return "\n".join(errors)


def oc_room_change_ass(conf_data, req, recs_ctx):
    recs_ctx['oc'] = oc = req.oc     # == 'CI'|'CO'|'RM'
    recs_ctx['record_idx'] = idx = -1
    error_msg = ""
    action_time = datetime.datetime.now()

    ho_id = req.hn
    log_msg(proc_context(recs_ctx) + ": ass room change xml={}".format(req.get_xml()), importance=4)
    if oc == 'RM':
        oc = 'CO-RM'
        idx += 1
        recs_ctx['records'].append(dict(HotelId=ho_id, ResId=req.res_nr, SubId=req.osub_nr, RoomNo=req.orn,
                                        extended_oc=oc, action_time=action_time))
        recs_ctx['record_idx'] = idx
        error_msg = conf_data.sh_room_change_to_ass(oc, ho_id, req.ores_nr, req.osub_nr, action_time)
        if not error_msg:
            oc = 'CI-RM'
    if not error_msg:
        idx += 1
        recs_ctx['records'].append(dict(HotelId=ho_id, ResId=req.res_nr, SubId=req.sub_nr, RoomNo=req.rn,
                                        extended_oc=oc, action_time=action_time))
        recs_ctx['record_idx'] = idx
        error_msg = conf_data.sh_room_change_to_ass(oc, ho_id, req.res_nr, req.sub_nr, action_time)

    if error_msg:
        log_msg(proc_context(recs_ctx) + " room change error={}".format(error_msg),
                minimum_debug_level=DEBUG_LEVEL_DISABLED, importance=3, is_error=True)
        em = conf_data.ass_db.rollback()
        if em:
            error_msg += "\n      " + em
    else:
        error_msg = conf_data.ass_db.commit()

    return error_msg


def oc_room_change_sf(conf_data, req, recs_ctx):
    errors = list()
    for idx, chg_cached in enumerate(recs_ctx['records']):
        recs_ctx['record_idx'] = idx
        log_msg(proc_context(recs_ctx) + ": SF room change xml={}".format(req.get_xml()), importance=4)
        # oc = chg_cached['extended_oc']
        ho_id = chg_cached['HotelId']
        res_id = chg_cached['ResId']
        sub_id = chg_cached['SubId']
        res = conf_data.rgr_fetch_list(['rgr_sf_id', 'rgr_time_in', 'rgr_time_out'],
                                       dict(rgr_ho_fk=ho_id, rgr_res_id=res_id, rgr_sub_id=sub_id))
        if conf_data.error_message or not res or not res[0] or not res[0][0] or not res[0][1] or not res[0][2]:
            errors.append(proc_context(recs_ctx) + ": AssCache fetch {} err={}".format(res, conf_data.error_message))
            continue

        sf_opp_id, err_msg = conf_data.sf_conn.room_change(*res[0])
        if err_msg:
            errors.append(proc_context(recs_ctx) + ": " + err_msg)
        elif not sf_opp_id or conf_data.error_message:
            errors.append(proc_context(recs_ctx) + ": SF APEX method err={}".format(conf_data.error_message))

    return "\n".join(errors)


# supported operation codes (stored in AssServer.ini) with related request class and operation code handler/processor
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
            return "SUPPORTED_OCS {} slots syntax error - list expected but got {}".format(oc, slots)
        for slot in slots:
            if not isinstance(slot, dict):
                return "SUPPORTED_OCS {} slot syntax error - dict expected but got {}".format(oc, slot)
            if 'reqClass' not in slot or 'ocProcessors' not in slot:
                return "SUPPORTED_OCS {} slot keys reqClass/ocProcessors missing - dict has only {}".format(oc, slot)

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
            if notification:
                notification.send_notification(msg_body=self.error_message, subject="AssServer handler notification")
            else:
                log_msg(self.error_message, is_error=True, importance=4)

    def handle_xml(self, xml_from_client):
        """ types of parameter xml_from_client and return value are bytes """
        xml_enc = cae.get_option('shXmlEncoding')
        xml_request = str(xml_from_client, encoding=xml_enc)
        log_msg("AssServer.handle_xml(): request='{}'".format(xml_request))

        # classify request for to also respond on error (e.g. if config_reload/xml_parsing failed)
        oc = operation_code(xml_request)
        tn = transaction_no(xml_request)
        org = organization_name(xml_request)

        err_messages = list()

        err_code = 0
        try:
            msg = reload_oc_config()
            if msg:
                msg += " (OC={})".format(oc)
                err_code = 90
        except Exception as ex:
            msg = "load config {} exception: '{}'\n{}".format(oc, ex, format_exc())
            err_code = 93
        if msg:
            err_messages.append((err_code, msg))
        elif oc in SUPPORTED_OCS:
            sys_connections = None
            try:
                sys_connections = AssSysData(cae, err_logger=log_msg, warn_logger=log_msg)
                if sys_connections.error_message or not sys_connections.ass_db:
                    err_messages.append((95, "AssSysData initialization error: {}; ass_db={}"
                                             .format(sys_connections.error_message, sys_connections.ass_db)))
                else:
                    recs_ctx = dict(records=list(), record_idx=-1, procedure='sys_conn')
                    for slot in SUPPORTED_OCS[oc]:
                        req_class = slot['reqClass']
                        recs_ctx['procedure'] = req_class.__name__
                        req = req_class(cae)
                        req.parse_xml(xml_request)
                        if debug_level >= DEBUG_LEVEL_VERBOSE:
                            err_messages.append((0, "Slot {}:{} parsed xml: {}".format(slot, req, req.get_xml())))
                        for proc in slot['ocProcessors']:
                            recs_ctx['procedure'] = proc.__name__
                            try:
                                msg = proc(sys_connections, req, recs_ctx)
                                if msg:
                                    err_messages.append((96, proc_context(recs_ctx) + " call error: {}".format(msg)))
                            except Exception as ex:
                                err_messages.append((97, proc_context(recs_ctx)
                                                     + " call exception: '{}'\n{}".format(ex, format_exc())))
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
                log_msg(msg + " Err=" + str(err_code), is_error=True, importance=3)
                last_err = err_code
            else:
                log_msg(msg, minimum_debug_level=DEBUG_LEVEL_ENABLED)

        msg = "AssServer.handle_xml(): " + ("\n    ** ".join([_[1] for _ in err_messages if _[0]]) or "OK")
        xml_response = ack_response(tn, last_err, org=org, msg=msg, status='1' if oc == 'LA' else '')
        log_msg("####  OC {} processed; xml response: {}".format(oc, xml_response))

        return bytes(xml_response, xml_enc)


try:
    # ?!?!?: if sihot is connecting as client then our listening server ip has to be either localhost or 127.0.0.1
    # .. and for connect to the Sihot WEB/KERNEL interfaces only the external IP address of the Sihot server is working
    ip_addr = cae.get_config('shClientIP', default_value=cae.get_option('shServerIP'))
    server = TcpServer(ip_addr, cae.get_option('shClientPort'), SihotRequestXmlHandler, debug_level=debug_level)
    server.run(display_animation=cae.get_config('displayAnimation', default_value=False))
except (OSError, Exception) as tcp_ex:
    log_msg("TCP server could not be started. Exception: ", tcp_ex, is_error=True)
    cae.shutdown(369)

cae.shutdown()
