"""
    AssServer is listening on the SIHOT SXML interface for to propagate room check-ins/check-outs/move
    and reservation changes onto the AssCache/Postgres database.

    0.1     first beta.
    0.2     refactored using add_ass_options() and init_ass_data().
"""
import datetime
from traceback import format_exc

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE
from ae_tcp import RequestXmlHandler, TcpServer, TCP_CONNECTION_BROKEN_MSG
from sxmlif import Request, ResChange, RoomChange, SihotXmlBuilder
from ass_sys_data import add_ass_options, init_ass_data

__version__ = '0.2'

cae = ConsoleApp(__version__, "Listening to Sihot SXML interface and updating AssCache/Postgres, Acumen and Salesforce")
ass_options = add_ass_options(cae, client_port=12000)

debug_level = cae.get_option('debugLevel')
ass_data = init_ass_data(cae, ass_options)
conf_data = ass_data['AssSysData']
if conf_data.error_message:
    uprint("AssServer startup error: ", conf_data.error_message)
    cae.shutdown(exit_code=9)
notification = ass_data['Notification']


def notify(msg, minimum_debug_level=DEBUG_LEVEL_VERBOSE):
    if debug_level >= minimum_debug_level:
        if notification:
            notification.send_notification(msg_body=msg, subject='AssServer notification')
        else:
            uprint(msg)


def oc_keep_alive(_):
    # no request-/error-checks needed on operation codes: LA=Link Alive, TS=Time Sync, ACK=Acknowledge
    return ""


def alloc_trigger(oc, sh_hotel_id, sh_res_id, sh_sub_id, asd):
    """ move/check in/out guest from/into room_no

    :param oc:              operation code: either 'CI', 'CO', 'CI-RM' or 'CO-RM'.
    :param sh_hotel_id:     Sihot hotel id (e.g. '1'==BHC).
    :param sh_res_id:       Sihot reservation main id.
    :param sh_sub_id:       Sihot reservation sub id.
    :param asd              AssSysDate instance (for to upsert to ass_db).
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
        err_msg = "alloc_trigger({}, {}, {}): Invalid operation code".format(oc, sh_hotel_id, sh_res_id)

    if not err_msg:
        err_msg = asd.rgr_upsert(upd_col_values, sh_hotel_id, res_id=sh_res_id, sub_id=sh_sub_id)

    return err_msg


def oc_room_change(req):
    error_msg = ""
    oc = req.oc
    ho_id = req.hn
    notify("####  Room change {} for res {}/{}@{} in room {}. xml={}"
           .format(oc, req.res_nr, req.sub_nr, ho_id, req.rn, req.get_xml()))
    if oc == 'RM':
        error_msg = alloc_trigger('CO-RM', ho_id, req.res_nr, req.osub_nr, conf_data)
        oc = 'CI-RM'
    if not error_msg:
        error_msg = alloc_trigger(oc, ho_id, req.res_nr, req.sub_nr, conf_data)

    if error_msg:
        notify("****  oc_room_change() alloc_trigger error=" + error_msg, minimum_debug_level=DEBUG_LEVEL_DISABLED)
        error_msg += "\n      " + conf_data.ass_db.rollback()
    else:
        error_msg = conf_data.ass_db.commit()

    return error_msg


def oc_res_change(req):
    oc = req.oc
    rgr_list = req.rgr_list
    for rgr in rgr_list:
        ho_id = rgr.get('rgr_ho_fk', '')
        res_id = rgr.get('rgr_res_id', '')
        sub_id = rgr.get('rgr_sub_id', '')
        notify("####  Reservation change {} for res {}/{}@{}. data={}".format(oc, res_id, sub_id, ho_id, rgr))
        rgc_list = rgr.pop('rgc')
        # TODO: identify orderer/client for to populate rgr_order_cl_fk
        if conf_data.rgr_upsert(rgr, ho_id, res_id=res_id, sub_id=sub_id):
            break
        rgr_pk = conf_data.ass_db.fetch_value()
        room_seq = pers_seq = -1
        room_no = 'InvalidRoomId'
        for rgc in rgc_list:
            if rgc.get('rgc_room_id', '') != room_no:
                room_no = rgc.get('rgc_room_id', '')
                room_seq += 1
                pers_seq = 0
            else:
                pers_seq += 1
            ac_id = rgc.pop('AcId', '')
            sh_id = rgc.pop('ShId', '')
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
            if conf_data.rgc_upsert(rgc, rgr_pk, room_seq, pers_seq):
                break
        if conf_data.error_message:
            break

    error_msg = conf_data.error_message
    if error_msg:
        error_msg += "\n      " + conf_data.ass_db.rollback()
    else:
        error_msg = conf_data.ass_db.commit()

    return error_msg


# supported operation codes (stored in AssServer.ini) with related request class and operation code handler/processor
SUPPORTED_OCS = dict()
# operation codes that will not be processed (no notification will be sent to user, only ACK will be send back to Sihot)
IGNORED_OCS = []


def reload_oc_config():
    """ allow to change processing of OCs without the need to restart this server """
    global SUPPORTED_OCS, IGNORED_OCS
    if not cae:         # added for to hide PyCharm warnings (Unused import)
        _ = (Request, ResChange, RoomChange)
    SUPPORTED_OCS = cae.get_config('SUPPORTED_OCS')
    if not SUPPORTED_OCS or not isinstance(SUPPORTED_OCS, dict):
        return "SUPPORTED_OCS is not or wrongly defined in main CFG/INI file"   # cae._cfg_fnam
    module_declarations = globals()
    for oc, slots in SUPPORTED_OCS.items():
        if not isinstance(slots, list):
            return "SUPPORTED_OCS {} slots syntax error - list expected but got {}".format(oc, slots)
        for slot in slots:
            if not isinstance(slot, dict):
                return "SUPPORTED_OCS {} slot syntax error - dict expected but got {}".format(oc, slot)
            if 'reqClass' not in slot or 'ocProcessor' not in slot:
                return "SUPPORTED_OCS {} slot keys reqClass/ocProcessor missing - dict has only {}".format(oc, slot)

            req_class = slot['reqClass']
            if req_class not in module_declarations:
                return "SUPPORTED_OCS {} slot key reqClass {} is not implemented".format(oc, req_class)
            slot['reqClass'] = module_declarations[req_class]

            oc_processor = slot['ocProcessor']
            if oc_processor not in module_declarations:
                return "SUPPORTED_OCS {} slot key ocProcessor {} is not implemented".format(oc, oc_processor)
            slot['ocProcessor'] = module_declarations[oc_processor]

    IGNORED_OCS = cae.get_config('IGNORED_OCS')
    if not isinstance(IGNORED_OCS, list):
        return "IGNORED_OCS is not or wrongly defined in main CFG/INI file - invalid value {}".format(IGNORED_OCS)

    return ""


def operation_code(request):
    oc = ''
    pos1 = request.find('<OC>')
    if pos1 != -1:
        pos1 += 4
        pos2 = request.find('</OC>', pos1)
        if pos2 - pos1 > 0:
            oc = request[pos1:pos2]
    return oc


def ack_response(req, ret_code, msg='', status=''):
    resp = SihotXmlBuilder(cae)
    resp.beg_xml(operation_code='ACK', transaction_number=getattr(req, 'tn', '69'))
    resp.add_tag('RC', ret_code)
    if msg:
        resp.add_tag('MSG', msg)
    if status:
        resp.add_tag('STATUS', status)
    org = getattr(req, 'org', '')
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
                uprint("****  " + self.error_message)

    def handle_xml(self, xml_from_client):
        """ types of parameter xml_from_client and return value are bytes """
        xml_request = str(xml_from_client, encoding=cae.get_option('shXmlEncoding'))
        notify("AssServer.SihotRequestXmlHandler.handle_xml() request: '" + xml_request + "'")

        parsed_req = None
        last_err = '0'
        messages = list()
        oc = operation_code(xml_request)

        try:
            msg = reload_oc_config()
            if msg:
                msg += " (OC={})".format(oc)
                last_err = '90'
                messages.append(msg)
        except Exception as ex:
            msg = "SihotRequestXmlHandler.handle_xml() load config {} exception: '{}'\n{}".format(oc, ex, format_exc())
            messages.append(msg)
            last_err = '93'

        if oc in SUPPORTED_OCS:
            try:
                for slot in SUPPORTED_OCS[oc]:
                    parsed_req = slot['reqClass'](cae)
                    parsed_req.parse_xml(xml_request)
                    notify("Before call of {}() with xml request {}".format(slot['ocProcessor'].__name__, xml_request))
                    msg = slot['ocProcessor'](parsed_req)
                    if msg:
                        notify("Error after call of {}(): {}".format(slot['ocProcessor'].__name__, msg))
                        messages.append(slot['ocProcessor'].__name__ + "() call error: " + msg)
                        last_err = '96'
            except Exception as ex:
                messages.append("SihotRequestXmlHandler.handle_xml() call exception: '{}'\n{}".format(ex, format_exc()))
                last_err = '99'
        elif oc in IGNORED_OCS:
            messages.append("(ignored operation-code/OC '{}')".format(oc))
        else:
            messages.append("SihotRequestXmlHandler.handle_xml(): empty/invalid operation code '{}'".format(oc))
            last_err = '102'

        for msg in messages:
            if msg[0] != '(':
                notify(msg, minimum_debug_level=DEBUG_LEVEL_DISABLED)
            elif debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint(msg)

        xml_response = ack_response(parsed_req, last_err, "\n      ".join(messages), status='1' if oc == 'LA' else '')
        notify("####  OC {} processing xml response: {}".format(oc, xml_response))

        return bytes(xml_response, cae.get_option('shXmlEncoding'))


try:
    server = TcpServer(cae.get_option('shServerIP'), cae.get_option('shClientPort'), SihotRequestXmlHandler,
                       debug_level=debug_level)
    server.run(display_animation=cae.get_config('displayAnimation', default_value=False))
except (OSError, Exception) as tcp_ex:
    uprint("****  TCP server could not be started. Exception: ", tcp_ex)
    cae.shutdown(369)

cae.shutdown()
