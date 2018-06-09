"""
    AssServer is listening on the SIHOT SXML interface for to propagate room check-ins/check-outs/move
    and reservation changes onto the AssCache/Postgres database.

    0.1     first beta.
    0.2     refactored using add_ass_options() and init_ass_data().
    0.3     added shClientIP config variable (because Sihot SXML push interface needs localhost instead of external IP).
"""
import datetime
from traceback import format_exc

from ae_console_app import (ConsoleApp, uprint, missing_requirements,
                            DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE)
from ae_tcp import RequestXmlHandler, TcpServer, TCP_CONNECTION_BROKEN_MSG
from sxmlif import Request, ResChange, RoomChange, SihotXmlBuilder
from ass_sys_data import add_ass_options, init_ass_data, AssSysData

__version__ = '0.3'

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


def oc_keep_alive(_, __):
    # no request-/error-checks needed on operation codes: LA=Link Alive, TS=Time Sync, ACK=Acknowledge
    return ""


def cache_room_change(conf_data, oc, sh_hotel_id, sh_res_id, sh_sub_id):
    """ move/check in/out guest from/into room_no

    :param conf_data:       AssSysData instance of current thread.
    :param oc:              operation code: either 'CI', 'CO', 'CI-RM' or 'CO-RM'.
    :param sh_hotel_id:     Sihot hotel id (e.g. '1'==BHC).
    :param sh_res_id:       Sihot reservation main id.
    :param sh_sub_id:       Sihot reservation sub id.
    :return:                Error message in case of error else empty string.
    """
    action_time = datetime.datetime.now()
    err_msg = ""
    upd_col_values = dict()
    if oc[:2] == 'CI':
        upd_col_values.update(rgr_time_in=action_time, rgr_time_out=None)
    elif oc[:2] == 'CO':
        upd_col_values.update(rgr_time_out=action_time)
    else:
        err_msg = "cache_room_change({}, {}, {}): Invalid operation code".format(oc, sh_hotel_id, sh_res_id)

    if not err_msg:
        err_msg = conf_data.rgr_upsert(upd_col_values, chk_values=dict(rgr_ho_fk=sh_hotel_id, rgr_res_id=sh_res_id,
                                                                       rgr_sub_id=sh_sub_id))

    return err_msg


def oc_room_change_ass(conf_data, req):
    error_msg = ""
    oc = req.oc
    ho_id = req.hn
    log_msg("AssCache Room change {} for res {}/{}@{} in room {}. xml={}"
            .format(oc, req.res_nr, req.sub_nr, ho_id, req.rn, req.get_xml()), importance=4)
    if oc == 'RM':
        error_msg = cache_room_change(conf_data, 'CO-RM', ho_id, req.res_nr, req.osub_nr)
        oc = 'CI-RM'
    if not error_msg:
        error_msg = cache_room_change(conf_data, oc, ho_id, req.res_nr, req.sub_nr)

    if error_msg:
        log_msg("oc_room_change_ass(): cache room change error=" + error_msg,
                minimum_debug_level=DEBUG_LEVEL_DISABLED, importance=3, is_error=True)
        em = conf_data.ass_db.rollback()
        if em:
            error_msg += "\n      " + em
    else:
        error_msg = conf_data.ass_db.commit()

    return error_msg


def oc_room_change_sf(conf_data, req):
    error_msg = ""
    oc = req.oc
    ho_id = req.hn
    log_msg("MISSING RES OBJECT ID - Sf Room change {} for res {}/{}@{} in room {}. xml={}"
            .format(oc, req.res_nr, req.sub_nr, ho_id, req.rn, req.get_xml()), importance=4)

    print(conf_data)

    return error_msg


def oc_res_change_ass(conf_data, req):
    oc = req.oc
    rgr_list = req.rgr_list
    for rgr in rgr_list:
        obj_id = rgr.get('rgr_obj_id', '')
        ho_id = rgr.get('rgr_ho_fk', '')
        res_id = rgr.get('rgr_res_id', '')
        sub_id = rgr.get('rgr_sub_id', '')
        # ?!?!?: identify orderer/client for to populate rgr_order_cl_fk
        log_msg("Reservation change {} to Ass for ShObjID {} and Res/Sub@Hotel {}/{}@{}. data={}"
                .format(oc, obj_id, res_id, sub_id, ho_id, rgr), importance=4)
        rec = rgr.copy()
        rgc_list = rec.pop('rgc')
        if conf_data.rgr_upsert(rec):
            break
        rgr_pk = conf_data.ass_db.fetch_value()
        room_seq = pers_seq = -1
        last_room_no = 'InvalidRoomId'
        for rgc in rgc_list:
            if rgc.get('rgc_room_id', '') != last_room_no:
                last_room_no = rgc.get('rgc_room_id', '')
                room_seq += 1
                pers_seq = 0
            else:
                pers_seq += 1
            ac_id = rgc.get('AcId', '')
            sh_id = rgc.get('ShId', '')
            if ac_id or sh_id:
                cae.dprint("Occupier matchcode / guest-obj-id:", ac_id, " / ", sh_id)
                cl_data = dict()
                if ac_id:
                    cl_data['AcId'] = ac_id
                if sh_id:
                    cl_data['ShId'] = sh_id
                if rgc.get('rgc_firstname', '') or rgc.get('rgc_surname', ''):
                    cl_data['Name'] = rgc.get('rgc_firstname', '') + ' ' + rgc.get('rgc_surname', '')
                if rgc.get('rgc_email', ''):
                    cl_data['Email'] = rgc['rgc_email']
                if rgc.get('rgc_phone', ''):
                    cl_data['Phone'] = rgc['rgc_phone']
                ass_id = conf_data.cl_save(cl_data, locked_cols=['AcId', 'ShId', 'Name', 'Email', 'Phone'])
                if not ass_id:
                    break
                rgc['rgc_occup_cl_fk'] = ass_id

            rec = rgc.copy()
            rec.pop('AcId', '')
            rec.pop('ShId', '')
            rec.update(rgc_rgr_fk=rgr_pk, rgc_room_seq=room_seq, rgc_pers_seq=pers_seq)
            if conf_data.rgc_upsert(rec):
                break

        if conf_data.error_message:
            break

    error_msg = conf_data.error_message
    if error_msg:
        error_msg += "\n      " + conf_data.ass_db.rollback()
    else:
        error_msg = conf_data.ass_db.commit()

    return error_msg


def oc_res_change_sf(conf_data, req):
    oc = req.oc
    rgr_list = req.rgr_list
    for rgr in rgr_list:
        obj_id = rgr.get('rgr_obj_id', '')
        res = conf_data.load_view(conf_data.acu_db, 'T_RU inner join T_MS on RU_MLREF = MS_MLREF', ['MS_SF_DL_ID'],
                                  "RU_SIHOT_OBJID = :obj_id", dict(obj_id=obj_id))
        if not res or not res[0][0]:
            log_msg("Reservation with Sihot Object ID {} not found in Acumen RU_SIHOT_OBJID/Surveys; err={}"
                    .format(obj_id, conf_data.error_message))
            continue
        sf_opp_id = res[0][0]
        ho_id = rgr.get('rgr_ho_fk', '')
        res_id = rgr.get('rgr_res_id', '')
        sub_id = rgr.get('rgr_sub_id', '')
        rgc_list = rgr.get('rgc', list([dict()]))
        log_msg("Reservation change {} to Sf for ShObjID {} and Res/Sub@Hotel {}/{}@{}. room list={}"
                .format(oc, obj_id, res_id, sub_id, ho_id, rgc_list), importance=4)

        opp_obj = conf_data.sf_conn.sf_obj('Opportunity')
        if not opp_obj:
            log_msg("Opportunity object not retrievable; errors={}/{}"
                    .format(conf_data.error_message, conf_data.sf_conn.error_msg), is_error=True, importance=3)
            continue
        fields = dict(Resort__c=conf_data.ho_id_resort(ho_id),
                      Room_Number__c=rgc_list[0].get('rgc_room_id', ''),
                      REQ_Acm_Arrival_Date__c=rgr.get('rgr_arrival', ''),
                      REQ_Acm_Departure_Date__c=rgr.get('rgr_departure', ''))
        try:
            ret = opp_obj.update(sf_opp_id, fields)
            log_msg("Opportunity ID {} updated with {}. ret={}".format(sf_opp_id, fields, ret),
                    importance=3, minimum_debug_level=DEBUG_LEVEL_ENABLED, notify=True)
        except Exception as ex:
            log_msg("Update of Opportunity object {} with ID {} and fields {} raised exception {}"
                    .format(opp_obj, sf_opp_id, fields, ex), importance=3, is_error=True)


# supported operation codes (stored in AssServer.ini) with related request class and operation code handler/processor
SUPPORTED_OCS = dict()
# operation codes that will not be processed (no notification will be sent to user, only ACK will be send back to Sihot)
IGNORED_OCS = []


def reload_oc_config():
    """ allow to change processing of OCs without the need to restart this server """
    global SUPPORTED_OCS, IGNORED_OCS
    _ = (Request, ResChange, RoomChange)    # added for to hide PyCharm warnings (Unused import)

    # first check if main config file has changed since server startup
    if not cae.config_main_file_modified():
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
    return _parse_core_value(request, 'TN', default='69')


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
        xml_request = str(xml_from_client, encoding=cae.get_option('shXmlEncoding'))
        log_msg("AssServer.SihotRequestXmlHandler.handle_xml() request: '" + xml_request + "'")

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
                    for slot in SUPPORTED_OCS[oc]:
                        parsed_req = slot['reqClass'](cae)
                        parsed_req.parse_xml(xml_request)
                        for proc in slot['ocProcessors']:
                            err_messages.append((0, "{}(); parsed xml: {}".format(proc.__name__, parsed_req.get_xml())))
                            try:
                                msg = proc(sys_connections, parsed_req)
                                if msg:
                                    err_messages.append((96, proc.__name__ + "() call error: " + msg))
                            except Exception as ex:
                                err_messages.append((97, "call exception: '{}'\n{}".format(ex, format_exc())))
            except Exception as ex:
                err_messages.append((99, "slot exception: '{}'\n{}".format(ex, format_exc())))
            finally:
                if sys_connections:
                    sys_connections.close_dbs()
        elif oc in IGNORED_OCS:
            err_messages.append((0, "(ignored operation-code/OC '{}')".format(oc)))
        else:
            err_messages.append((102, "empty/invalid operation code '{}'".format(oc)))

        last_err = 0
        for err_code, msg in err_messages:
            if err_code:
                log_msg(msg + " LastError=" + str(err_code), is_error=True, importance=3)
            else:
                log_msg(msg)
            last_err = err_code

        err_string = "SihotRequestXmlHandler.handle_xml(): " + "\n      +++".join([_[1] for _ in err_messages])
        xml_response = ack_response(tn, last_err, org=org, msg=err_string, status='1' if oc == 'LA' else '')
        log_msg("####  OC {} processing xml response: {}".format(oc, xml_response))

        return bytes(xml_response, cae.get_option('shXmlEncoding'))


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
