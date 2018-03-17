"""
    AssServer is listening on the SIHOT SXML interface for to propagate room check-ins/check-outs/move
    and reservation changes onto the ass_cache postgres database.

    0.1     first beta.
"""
import datetime
from traceback import format_exc

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE
from ae_notification import add_notification_options, init_notification
from ae_tcp import RequestXmlHandler, TcpServer, TIMEOUT_ERR_MSG
from sxmlif import Request, ResChange, RoomChange, SihotXmlBuilder, SXML_DEF_ENCODING
from ass_sys_data import AssSysData

__version__ = '0.1'

cae = ConsoleApp(__version__, "Listening to Sihot interface for to update the ass_cache PG database")

cae.add_option('pgUser', "User account name for ass_cache postgres cache database", 'postgres', 'U')
cae.add_option('pgPassword', "User account password for ass_cache postgres cache database", '', 'P')
cae.add_option('pgDSN', "Database name of the ass_cache postgres cache database", 'ass_cache', 'N')

cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the interface of this server", 11000, 'w')

cae.add_option('timeout', "Timeout value for TCP/IP connections", 69.3)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

add_notification_options(cae)

debug_level = cae.get_option('debugLevel')
uprint('AssCache Database/User:', cae.get_option('pgDSN'), cae.get_option('pgUser'))
uprint('Sihot IP/port:', cae.get_option('serverIP'), cae.get_option('serverPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))
notification, _ = init_notification(cae, cae.get_option('pgDSN') + '/' + cae.get_option('serverIP'))


def notify(msg, minimum_debug_level=DEBUG_LEVEL_VERBOSE):
    if debug_level >= minimum_debug_level:
        if notification:
            notification.send_notification(msg_body=msg, subject='AssServer notification')
        else:
            uprint(msg)


def create_ack_response(req, ret_code, msg='', status=''):
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


def oc_keep_alive(req):
    # process operation codes: Link Alive, Time Sync, Acknowledge
    response_xml = create_ack_response(req, '0', status='1' if req.oc == 'LA' else '')
    notify("####  oc_keep_alive() response: " + response_xml)
    return response_xml


def alloc_trigger(oc, sh_hotel_id, sh_res_id, sh_sub_id):
    """ move/check in/out guest from/into room_no

    :param oc:              operation code: either 'CI', 'CO', 'CI-RM' or 'CO-RM'
    :param sh_hotel_id:     Sihot hotel id (e.g. '1'==BHC)
    :param sh_res_id:       Sihot reservation main id
    :param sh_sub_id:       Sihot reservation sub id
    :return:                Error message in case of error else empty string
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
        ass = AssSysData(cae)
        err_msg = ass.rgr_upsert(upd_col_values, sh_hotel_id, res_id=sh_res_id, sub_id=sh_sub_id, commit=True)

    return err_msg


def oc_room_change(req):
    error_msg = ""
    oc = req.oc
    ho_id = req.hn
    notify("####  Room change {} for res {}/{}@{} in room {}. xml={}"
           .format(oc, req.res_nr, req.sub_nr, ho_id, req.rn, req.get_xml()))
    if oc == 'RM':
        error_msg = alloc_trigger('CO-RM', ho_id, req.res_nr, req.osub_nr)
        oc = 'CI-RM'

    if not error_msg:
        error_msg = alloc_trigger(oc, ho_id, req.res_nr, req.sub_nr)

    if error_msg:
        notify("****  oc_room_change() alloc_trigger error=" + error_msg, minimum_debug_level=DEBUG_LEVEL_DISABLED)

    response_xml = create_ack_response(req, '1' if error_msg else '0', msg=error_msg)
    notify("####  oc_room_change() response: " + response_xml)
    return response_xml


def oc_res_change(req):
    oc = req.oc
    rgr_list = req.rgr_list
    ass = AssSysData(cae)
    for rgr in rgr_list:
        ho_id = rgr['rgr_ho_fk']
        res_id = rgr['rgr_res_id']
        sub_id = rgr['rgr_sub_id']
        notify("####  Reservation change {} for res {}/{}@{}. data={}".format(oc, res_id, sub_id, ho_id, rgr))
        rgc_list = rgr.pop('rgc')
        if ass.rgr_upsert(rgr, ho_id, res_id=res_id, sub_id=sub_id):
            break
        rgr_pk = ass.ass_db.fetch_value()
        for rgc in rgc_list:
            if ass.rgc_upsert(rgc, rgr_pk):
                break
        if ass.error_message:
            break

    error_msg = ass.error_message
    if error_msg:
        ass.ass_db.rollback()
    else:
        ass.ass_db.commit()

    response_xml = create_ack_response(req, '1' if error_msg else '0', msg=error_msg)
    notify("####  oc_res_change() response: " + response_xml)
    return response_xml


# supported operation codes with related request class and operation code handler/processor
SUPPORTED_OCS = {
    #  old guest sync tests Sihot -> Postgres
    # 'GUEST-CREATE': {'reqClass': GuestFromSihot, 'ocProcessor': oc_client_to_ass, },
    # 'GUEST-CHANGE': {'reqClass': GuestFromSihot, 'ocProcessor': oc_client_to_ass, },
    #  keep alive SXML interfaces
    'ACK': dict(reqClass=Request, ocProcessor=oc_keep_alive),
    'LA': dict(reqClass=Request, ocProcessor=oc_keep_alive),
    'TS': dict(reqClass=Request, ocProcessor=oc_keep_alive),
    #  reservation changes SXML interface
    'CR': dict(reqClass=ResChange, ocProcessor=oc_res_change),
    #  SXML interface for allocation notification on room-checkin/-out/-move
    # we actually only need Minibar/Wellness System Level I: CI, CO, RM and ACK (see SXML doc page 57)
    # currently not supported: CR=change reservation, PCO=PreCheckOut, GC=Guest Change, PRECHECKIN
    'CI': dict(reqClass=RoomChange, ocProcessor=oc_room_change),
    'CO': dict(reqClass=RoomChange, ocProcessor=oc_room_change),
    'RM': dict(reqClass=RoomChange, ocProcessor=oc_room_change),
}

# operation codes that will not be processed (no notification will be sent to user, only ACK will be send back to Sihot)
IGNORED_OCS = []


class SihotRequestXmlHandler(RequestXmlHandler):
    def notify(self):
        # hide timeout or dropped connection error if not verbose debug level
        if TIMEOUT_ERR_MSG not in self.error_message or debug_level >= DEBUG_LEVEL_VERBOSE:
            if notification:
                notification.send_notification(msg_body=self.error_message, subject="AssServer handler notification")
            else:
                uprint("**** " + self.error_message)

    def handle_xml(self, xml_from_client):
        """ types of parameter xml_from_client and return value are bytes """
        xml_request = str(xml_from_client, encoding=cae.get_option('xmlEncoding'))
        notify("SihotRequestXmlHandler.handle_xml() request: '" + xml_request + "'")
        req = Request(cae)
        req.parse_xml(xml_request)
        cae.dprint("OC: ", getattr(req, 'oc', '?'), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        cae.dprint("TN: ", getattr(req, 'tn', '?'), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        cae.dprint("ID: ", getattr(req, 'id', '?'), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        cae.dprint("RC: ", getattr(req, 'rc', '?'), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        cae.dprint("MSG: ", getattr(req, 'msg', ''), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        cae.dprint("ORG: ", getattr(req, 'org', ''), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        cae.dprint("VER: ", getattr(req, 'ver', '?'), minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        oc = req.get_operation_code()
        if not oc or oc not in SUPPORTED_OCS:
            if oc in IGNORED_OCS:
                msg = "(ignored)"
            else:
                msg = "****  SihotRequestXmlHandler.handle_xml(): empty or unsupported operation code '" + oc + "'!"
                notify(msg, minimum_debug_level=DEBUG_LEVEL_ENABLED)
            xml_response = create_ack_response(req, '99', msg)
        else:
            try:
                req = SUPPORTED_OCS[oc]['reqClass'](cae)
                req.parse_xml(xml_request)
                cae.dprint("Before call of", SUPPORTED_OCS[oc]['ocProcessor'], "xml-request:", xml_request)
                xml_response = SUPPORTED_OCS[oc]['ocProcessor'](req)
                cae.dprint("After call of", SUPPORTED_OCS[oc]['ocProcessor'], "xml-response:", xml_response)
            except Exception as ex:
                msg = "SihotRequestXmlHandler.handle_xml() exception: '" + str(ex) + "'\n" + str(format_exc())
                notify(msg, minimum_debug_level=DEBUG_LEVEL_DISABLED)
                xml_response = create_ack_response(req, '969', msg)

        return bytes(xml_response, cae.get_option('xmlEncoding'))


try:
    server = TcpServer(cae.get_option('serverIP'), cae.get_option('serverPort'), SihotRequestXmlHandler,
                       debug_level=debug_level)
    server.run(display_animation=cae.get_config('displayAnimation', default_value=False))
except (OSError, Exception) as tcp_ex:
    uprint("****  TCP server could not be started. Exception: ", tcp_ex)
    cae.shutdown(369)

cae.shutdown()
