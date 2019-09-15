"""
    0.1     first beta (only support GUEST-CREATE/-CHANGE of WEB interface 9.0).
    0.2     extended to support SXML interface V9.0 Level 1 of Minibar/Wellness-center.
    0.3     made running-server-animation optional, specify debugLevel/logFile in INI and check/fix Transaction number
            passing/increment - is always duplicated '2' instead the one sent by Sihot (see Track-It closed WO #43242).
    0.4     added GDS number to alloc_trigger() - available since Sihot build/version 9.0.0.0787.CO.
    0.5     added shClientIP config variable (because Sihot SXML push interface needs localhost instead of external IP).
    0.6     refactored to use system field records and migrated client_to_acu() to acif.py/AcumenClient.save_client().
    0.7     beautified and hardened error notification and logging.
"""
from traceback import format_exc

from sys_data_ids import (SDF_SH_TIMEOUT,
                          SDF_SH_XML_ENCODING, SDF_SH_CLIENT_PORT)
from ae.core import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE
from ae.console_app import ConsoleApp
from ae_notification.notification import add_notification_options, init_notification
from ae_db.db import OraDB
from ae_tcp.tcp import RequestXmlHandler, TcpServer, TCP_CONNECTION_BROKEN_MSG
from acif import add_ac_options, AcumenClient
from sxmlif import Request, RoomChange, SihotXmlBuilder
from shif import add_sh_options, ClientFromSihot

__version__ = '0.7'


cae = ConsoleApp("Sync client and reservation data from SIHOT to Acumen/Oracle", multi_threading=True)
add_ac_options(cae)
add_sh_options(cae, client_port=11000)
add_notification_options(cae)

debug_level = cae.get_opt('debugLevel')
cae.po("Acumen Usr/DSN:", cae.get_opt('acuUser'), cae.get_opt('acuDSN'))
cae.po("TCP Timeout/XML Encoding:", cae.get_opt(SDF_SH_TIMEOUT), cae.get_opt(SDF_SH_XML_ENCODING))
notification, _ = init_notification(cae, cae.get_opt('acuDSN') + '/' + cae.get_opt('shServerIP'))


def notify(msg, minimum_debug_level=DEBUG_LEVEL_ENABLED):
    if debug_level >= minimum_debug_level:
        if notification:
            notification.send_notification(msg_body=msg, subject='AcuServer notification', body_style='plain')
        else:
            cae.po(msg)


def oc_client_to_acu(req):
    acu_cl = AcumenClient(cae)
    error_msg, pk = acu_cl.save_client(req.client_list[0])
    notify("####  Guest inserted or updated within Acumen with pk=" + pk if not error_msg
           else "****  Acumen guest data insert/update error: " + error_msg)
    resp = SihotXmlBuilder(cae)
    resp.beg_xml(operation_code=req.oc)
    resp.add_tag('RC', '1' if error_msg else '0')
    resp.add_tag('MATCHCODE', pk)
    resp.add_tag('PWD')
    resp.add_tag('MSG', error_msg)
    resp.end_xml()
    xml_response = resp.xml
    notify("Sending GUEST-CREATE answer back to client: " + xml_response, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
    return xml_response


def alloc_trigger(oc, guest_id, room_no, old_room_no, gds_no, sihot_xml):
    room_no = room_no.lstrip('0')       # remove leading zero from 3-digit PBC Sihot room number
    if old_room_no:
        old_room_no = old_room_no.lstrip('0')
    # move/check in/out guest from/into room_no
    ora_db = OraDB(dict(User=cae.get_opt('acuUser'), Password=cae.get_opt('acuPassword'),
                        DSN=cae.get_opt('acuDSN')),
                   app_name=cae.app_name, debug_level=debug_level)
    err_msg = ora_db.connect()
    extra_info = ''
    if not err_msg:
        ref_var = ora_db.prepare_ref_param(sihot_xml)
        err_msg = ora_db.call_proc('P_SIHOT_ALLOC', (ref_var, oc, room_no, old_room_no, gds_no))
        if err_msg:
            ora_db.rollback()
        else:
            if debug_level >= DEBUG_LEVEL_VERBOSE:
                extra_info = ' REQ:' + sihot_xml
            changes = ora_db.get_value(ref_var)
            if changes:
                extra_info += ' CHG:' + changes

    db_err = ora_db.insert('T_SRSL', {'SRSL_TABLE': 'ARO',
                                      'SRSL_PRIMARY': (old_room_no + '-' if old_room_no else '') + room_no,
                                      'SRSL_ACTION': oc,
                                      'SRSL_STATUS': 'ERR' if err_msg else 'SYNCED',
                                      'SRSL_MESSAGE': (str(gds_no) + '='        # gds_no could be None/NoneType
                                                       + (err_msg + extra_info if err_msg else extra_info[1:]))[:1998],
                                      'SRSL_LOGREF': guest_id or -1,
                                      },
                           commit=True)              # COMMIT
    if db_err:
        err_msg += "AcuServer.alloc_trigger() db insert error: " + db_err
        cae.po(err_msg)

    db_err = ora_db.close()      # commit and close
    if db_err:
        err_msg += "AcuServer.alloc_trigger() db close error: " + db_err
        cae.po(err_msg)

    return err_msg


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


def oc_room_change(req):
    notify("####  {} room change for guest {} in room {}".format(req.oc, req.gid, req.rn),
           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
    error_msg = alloc_trigger(req.oc, req.gid, req.rn, req.orn, req.gdsno, req.get_xml())
    if error_msg:
        notify("****  oc_room_change() alloc_trigger error=" + error_msg, minimum_debug_level=DEBUG_LEVEL_DISABLED)

    response_xml = create_ack_response(req, '1' if error_msg else '0', msg=error_msg)
    notify("####  oc_room_change() response: " + response_xml, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
    return response_xml


def oc_keep_alive(req):
    # process operation codes: Link Alive, Time Sync, Acknowledge
    response_xml = create_ack_response(req, '0', status='1' if req.oc == 'LA' else '')
    notify("####  oc_keep_alive() response: " + response_xml, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
    return response_xml


# supported operation codes with related request class and operation code handler/processor
SUPPORTED_OCS = {
    #  old guest sync tests Sihot -> Acumen
    'GUEST-CREATE': {'reqClass': ClientFromSihot, 'ocProcessor': oc_client_to_acu, },
    'GUEST-CHANGE': {'reqClass': ClientFromSihot, 'ocProcessor': oc_client_to_acu, },
    #  keep alive and other basic SXML interfaces
    'ACK': {'reqClass': Request, 'ocProcessor': oc_keep_alive, },
    'LA': {'reqClass': Request, 'ocProcessor': oc_keep_alive, },
    'TS': {'reqClass': Request, 'ocProcessor': oc_keep_alive, },
    #  SXML interface for allocation notification on room-checkin/-out/-move
    # we actually only need Minibar/Wellness System Level I: CI, CO, RM and ACK (see SXML doc page 57)
    # currently not supported: CR=change reservation, PCO=PreCheckOut, GC=Guest Change, PRECHECKIN
    'CI': {'reqClass': RoomChange, 'ocProcessor': oc_room_change, },
    'CO': {'reqClass': RoomChange, 'ocProcessor': oc_room_change, },
    'RM': {'reqClass': RoomChange, 'ocProcessor': oc_room_change, },
}

# operation codes that will not be processed (no notification will be sent to user, only ACK will be send back to Sihot)
IGNORED_OCS = ['CR']


class SihotRequestXmlHandler(RequestXmlHandler):
    def notify(self):
        # hide timeout or dropped connection error (Sihot client does not close connection properly)
        if TCP_CONNECTION_BROKEN_MSG not in self.error_message:
            if notification:
                notification.send_notification(msg_body=self.error_message, subject="AcuServer handler notification")
            else:
                cae.po("**** " + self.error_message)

    def handle_xml(self, xml_from_client):
        """ types of parameter xml_from_client and return value are bytes """
        xml_request = str(xml_from_client, encoding=cae.get_opt(SDF_SH_XML_ENCODING))
        notify("SihotRequestXmlHandler.handle_xml() request: '" + xml_request + "'",
               minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        req = Request(cae)
        req.parse_xml(xml_request)
        cae.dpo("OC: ", getattr(req, 'oc', '?'))
        cae.dpo("TN: ", getattr(req, 'tn', '?'))
        cae.dpo("ID: ", getattr(req, 'id', '?'))
        cae.dpo("RC: ", getattr(req, 'rc', '?'))
        cae.dpo("MSG: ", getattr(req, 'msg', ''))
        cae.dpo("ORG: ", getattr(req, 'org', ''))
        cae.dpo("VER: ", getattr(req, 'ver', '?'))

        oc = req.get_operation_code()
        if not oc or oc not in SUPPORTED_OCS:
            if oc in IGNORED_OCS:
                msg = "(ignored)"
            else:
                msg = "****  SihotRequestXmlHandler.handle_xml(): empty or unsupported operation code '" + oc + "'!"
                notify(msg)
            xml_response = create_ack_response(req, '99', msg)
        else:
            try:
                req = SUPPORTED_OCS[oc]['reqClass'](cae)
                req.parse_xml(xml_request)
                cae.dpo("Before call of", SUPPORTED_OCS[oc]['ocProcessor'], "xml:", xml_request)
                xml_response = SUPPORTED_OCS[oc]['ocProcessor'](req)
                cae.dpo("After call of", SUPPORTED_OCS[oc]['ocProcessor'], "xml:", xml_response)
            except Exception as ex:
                msg = "SihotRequestXmlHandler.handle_xml() exception: '" + str(ex) + "'\n" + str(format_exc())
                notify(msg, minimum_debug_level=DEBUG_LEVEL_DISABLED)
                xml_response = create_ack_response(req, '969', msg)

        return bytes(xml_response, cae.get_opt(SDF_SH_XML_ENCODING))


if __name__ == '__main__':
    ip_addr = cae.get_var('shClientIP', default_value=cae.get_opt('shServerIP'))
    cae.po("Sihot client IP/port:", ip_addr, cae.get_opt(SDF_SH_CLIENT_PORT))
    server = TcpServer(ip_addr, cae.get_opt(SDF_SH_CLIENT_PORT), SihotRequestXmlHandler, debug_level=debug_level)
    server.run(display_animation=cae.get_var('displayAnimation', default_value=False))

    cae.shutdown()
