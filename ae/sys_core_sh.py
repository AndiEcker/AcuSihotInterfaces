# SiHOT xml interface
import datetime
import pprint
import re
import socket
import threading
import time
import socketserver
from traceback import format_exc

from abc import ABCMeta, abstractmethod

# import xml.etree.ElementTree as Et
from xml.etree.ElementTree import XMLParser, ParseError

from ae.core import (DATE_ISO, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE, DEBUG_LEVEL_TIMESTAMPED, DEF_ENCODE_ERRORS,
                     po, round_traditional)
from ae.sys_core import SystemConnectorBase


__version__ = '0.0.1'


SDI_SH = 'Sh'                               # Sihot Interfaces


SH_DEF_SEARCH_FIELD = 'ShId'    #: default search field for external systems (used by sys_data_sh.cl_field_data())

SDF_SH_KERNEL_PORT = 'shServerKernelPort'   #: Sihot Kernel Interface port
SDF_SH_WEB_PORT = 'shServerPort'            #: Sihot Web interfaces port
SDF_SH_CLIENT_PORT = 'shClientPort'         #: Sihot Server client port
SDF_SH_TIMEOUT = 'shTimeout'
SDF_SH_XML_ENCODING = 'shXmlEncoding'
SDF_SH_USE_KERNEL_FOR_CLIENT = 'shUseKernelForClient'
SDF_SH_USE_KERNEL_FOR_RES = 'shUseKernelForRes'
SDF_SH_CLIENT_MAP = 'shMapClient'
SDF_SH_RES_MAP = 'shMapRes'


# latin1 (synonym to ISO-8859-1) doesn't have the Euro-symbol
# .. so we use ISO-8859-15 instead ?!?!? (see
# .. http://www.gerd-riesselmann.net/webentwicklung/utf-8-latin1-aka-iso-8859-1-und-das-euro-zeichen/  and
# .. http://www.i18nqa.com/debug/table-iso8859-1-vs-windows-1252.html  and
# .. http://www.i18nqa.com/debug/table-iso8859-1-vs-iso8859-15.html   )
# SXML_DEF_ENCODING = 'ISO-8859-15'
# But even with ISO-8859-15 we are getting errors with e.g. ACUTE ACCENT' (U+00B4/0xb4) therefore next tried UTF8
# SXML_DEF_ENCODING = 'utf8'
# .. but then I get the following error in reading all the clients:
# .. 'charmap' codec can't decode byte 0x90 in position 2: character maps to <undefined>
# then added an output type handler to the connection (see db_core.py) which did not solve the problem (because
# .. the db_core.py module is not using this default encoding but the one in NLS_LANG env var
# For to fix showing umlaut character correctly tried cp1252 (windows charset)
# .. and finally this worked for all characters (because it has less undefined code points_import)
# SXML_DEF_ENCODING = 'cp1252'
# But with the added errors=DEF_ENCODE_ERRORS argument for the bytes() new/call used in the TcpClient.send_to_server()
# .. method we try sihot interface encoding again
# but SXML_DEF_ENCODING = 'ISO-8859-1' failed again with umlaut characters
# .. Y203585/HUN - Name decoded wrongly with ISO
SXML_DEF_ENCODING = 'cp1252'

# special error message prefixes
ERR_MESSAGE_PREFIX_CONTINUE = 'CONTINUE:'

TCP_CONNECTION_BROKEN_MSG = "socket connection broken!"

# private module constants
_TCP_MAXBUFLEN = 8192
_TCP_END_OF_MSG_CHAR = b'\x04'
_DEBUG_RUNNING_CHARS = "|/-\\"


ppf = pprint.PrettyPrinter(indent=12, width=96, depth=9).pformat


#  HELPER METHODS AND CLASSES ###################################

def elem_to_attr(elem):
    return elem.lower().replace('-', '_')


class _TcpClient:
    error_message = ""
    received_xml = ""

    def __init__(self, server_ip, server_port, timeout=3.6, encoding='utf8', debug_level=DEBUG_LEVEL_DISABLED):
        super().__init__()
        self.serverIP = server_ip
        self.serverPort = server_port
        self.timeout = timeout
        self.encoding = encoding
        self.debug_level = debug_level

    def send_to_server(self, xml):
        self.error_message = ""
        self.received_xml = ""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    po("TcpClient connecting to server ", self.serverIP, " on port ", self.serverPort,
                       " with encoding", self.encoding, " and timeout", self.timeout)
                # adding sock.setblocking(0) is resulting in a BlockingIOError exception
                sock.settimeout(self.timeout)
                sock.connect((self.serverIP, self.serverPort))
                bs = bytes(xml, encoding=self.encoding, errors=DEF_ENCODE_ERRORS)
                sock.sendall(bs + _TCP_END_OF_MSG_CHAR)
                self.received_xml = self._receive_response(sock)
        except Exception as ex:
            self.error_message = "TcpClient.send_to_server() exception: " + str(ex) \
                + (" (sent XML=" + xml + ")" + "\n" + format_exc() if self.debug_level >= DEBUG_LEVEL_VERBOSE else "")

        return self.error_message

    def _receive_response(self, sock):
        def _handle_err_gracefully(extra_msg=""):
            # socket connection broken, see https://docs.python.org/3/howto/sockets.html#socket-howto
            # .. and for 100054 see https://stackoverflow.com/questions/35542404
            self.error_message = "TcpClient._receive_response(): " + TCP_CONNECTION_BROKEN_MSG + extra_msg
            if self.debug_level:
                po(self.error_message)
        xml_recv = b""
        try:
            while xml_recv[-1:] != _TCP_END_OF_MSG_CHAR:
                chunk = sock.recv(_TCP_MAXBUFLEN)
                if not chunk:
                    _handle_err_gracefully()
                    break
                xml_recv += chunk
            xml_recv = xml_recv[:-1]        # remove TCP_END_OF_MSG_CHAR

        except Exception as ex:
            if 10054 in ex.args:
                # [ErrNo|WinError 10054] An existing connection was forcibly closed by the remote host
                _handle_err_gracefully(" ErrNo=10054 (data loss is possible)")
            else:
                self.error_message = "TcpClient._receive_response() err: " + str(ex) \
                                     + (" (received XML=" + str(xml_recv, self.encoding) + ")" + "\n" + format_exc()
                                        if self.debug_level >= DEBUG_LEVEL_VERBOSE else "")

        return str(xml_recv, self.encoding)


class RequestXmlHandler(socketserver.BaseRequestHandler, metaclass=ABCMeta):
    error_message = ""

    """
    def setup(self):
        # the socket is called request in the request handler
        self.request.settimeout(1.0)
        #self.request.setblocking(False)
    """

    def notify(self):
        po("****  " + self.error_message)

    def handle(self):
        xml_recv = b""
        try:
            while xml_recv[-1:] != _TCP_END_OF_MSG_CHAR:
                chunk = self.request.recv(_TCP_MAXBUFLEN)
                if not chunk:  # socket connection broken, see https://docs.python.org/3/howto/sockets.html#socket-howto
                    self.error_message = "RequestXmlHandler.handle(): " + TCP_CONNECTION_BROKEN_MSG
                    self.notify()
                    return
                xml_recv += chunk
            xml_recv = xml_recv[:-1]        # remove TCP_END_OF_MSG_CHAR
            resp = self.handle_xml(xml_recv) + _TCP_END_OF_MSG_CHAR
            self.request.sendall(resp)

        except Exception as ex:
            self.error_message = "RequestXmlHandler.handle() exception='" + str(ex) + "' (XML=" + str(xml_recv) + ")"\
                                 + "\n" + format_exc()
            self.notify()

    @abstractmethod
    def handle_xml(self, xml_from_client):
        pass


class _ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class TcpServer:

    def __init__(self, ip, port, cls_xml_handler, debug_level=DEBUG_LEVEL_DISABLED):
        self.debug_level = debug_level
        # cls_xml_handler is a RequestXmlHandler subclass with an overridden handle_xml() method
        server = _ThreadedServer((ip, port), cls_xml_handler)

        if debug_level >= DEBUG_LEVEL_VERBOSE:
            po("TcpServer initialized on ip/port: ", server.server_address)

        # start a thread with the server - which then start one more thread for each request/client-socket
        server_thread = threading.Thread(target=server.serve_forever)
        # exit server thread when main tread terminates
        server_thread.daemon = True
        server_thread.start()

        if debug_level >= DEBUG_LEVEL_VERBOSE:
            po("TcpServer running in thread:", server_thread.name)

        self.server = server

    def run(self, display_animation=False):
        try:
            sleep_time = 0.5 / len(_DEBUG_RUNNING_CHARS)
            index = 0
            while True:
                if display_animation:
                    index = (index + 1) % len(_DEBUG_RUNNING_CHARS)
                    po("Server is running " + _DEBUG_RUNNING_CHARS[index], end="\r", flush=True)
                time.sleep(sleep_time)
        except Exception as ex:
            po("Server killed with exception: ", ex)
            if self.debug_level:
                po(format_exc())
        self.server.shutdown()
        self.server.server_close()


# XML PARSER ##############################################################################

class SihotXmlParser:  # XMLParser interface
    def __init__(self, cae):
        super(SihotXmlParser, self).__init__()
        self._xml = ''
        self._base_tags = ['ERROR-LEVEL', 'ERROR-TEXT', 'ID', 'MSG', 'OC', 'ORG', 'RC', 'TN', 'VER',
                           'MATCHCODE', 'OBJID']
        self._curr_tag = ''
        self._curr_attr = ''
        self._elem_path = list()    # element path implemented as list stack

        # main xml elements/items
        self.oc = ''
        self.tn = '0'
        self.id = '1'
        self.matchcode = None
        self.objid = None
        self.rc = '0'
        self.msg = ''
        self.ver = ''
        self.error_level = '0'  # used by kernel interface instead of RC/MSG
        self.error_text = ''
        self.cae = cae  # only needed for logging with debug_out()/dpo()
        self._parser = None  # reset to XMLParser(target=self) in self.parse_xml() and close in self.close()

    def parse_xml(self, xml):
        self.cae.dpo("SihotXmlParser.parse_xml():", xml)
        self._xml = xml
        self._parser = XMLParser(target=self)
        try:
            self._parser.feed(xml)
        except ParseError:
            # replacing '&#128;' with '€', '&#1;' with '¿1¿' and '&#7;' with '¿7¿' for Sihot XML
            self._xml = self._xml.replace('&#1;', '¿1¿').replace('&#7;', '¿7¿').replace('&#128;', '€')
            # replacing '&#NNN;' with chr(NNN) for Sihot XML
            self._xml = re.compile("&#([0-9]+);").sub(lambda m: chr(int(m.group(0)[2:-1])), self._xml)
            self._parser.feed(self._xml)

    def get_xml(self):
        return self._xml

    # xml parsing interface

    def start(self, tag, attrib):  # called for each opening tag
        self._curr_tag = tag
        self._curr_attr = None  # used as flag for a currently parsed base tag (for self.data())
        self._elem_path.append(tag)
        if tag in self._base_tags:
            self.cae.dpo("SihotXmlParser.start():", self._elem_path)
            self._curr_attr = elem_to_attr(tag)
            setattr(self, self._curr_attr, '')
            return None
        # collect extra info on error response (RC != '0') within the MSG tag field
        if tag[:4] in ('MSG-', "INDE", "VALU"):
            self._curr_attr = 'msg'
            # Q&D: by simply using tag[4:] for to remove MSG- prefix, INDEX will be shown as X= and VALUE as E=
            setattr(self, self._curr_attr, getattr(self, self._curr_attr, '') + " " + tag[4:] + "=")
            return None
        return tag

    def data(self, data):  # called on each chunk (separated by XMLParser on spaces, special chars, ...)
        if self._curr_attr and data.strip():
            self.cae.dpo("SihotXmlParser.data(): ", self._elem_path, data)
            setattr(self, self._curr_attr, getattr(self, self._curr_attr) + data)
            return None
        return data

    def end(self, tag):  # called for each closing tag
        self.cae.dpo("SihotXmlParser.end():", self._elem_path)
        self._curr_tag = ''
        self._curr_attr = ''
        if self._elem_path:     # Q&D Fix for TestGuestSearch for to prevent pop() on empty _elem_path list
            self._elem_path.pop()
        return tag

    def close(self):  # called when all data has been parsed.
        self._parser.close()
        return self  # ._max_depth

    def server_error(self):
        if self.rc != '0':
            return self.rc
        elif self.error_level != '0':
            return self.error_level
        return '0'

    def server_err_msg(self):
        if self.rc != '0':
            return self.msg
        elif self.error_level != '0':
            return self.error_text
        return ''


class Request(SihotXmlParser):  # request from SIHOT
    def get_operation_code(self):
        return self.oc


class RoomChange(SihotXmlParser):
    def __init__(self, cae):
        super(RoomChange, self).__init__(cae)
        # add base tags for room/GDS number, old room/GDS number and guest objid
        self._base_tags.append('HN')
        self.hn = None  # added for to remove pycharm warning
        self._base_tags.append('RN')
        self.rn = None
        self._base_tags.append('ORN')
        self.orn = None
        self._base_tags.append('GDSNO')
        self.gdsno = None
        self._base_tags.append('RES-NR')
        self.res_nr = None
        self._base_tags.append('SUB-NR')
        self.sub_nr = None
        self._base_tags.append('OSUB-NR')
        self.osub_nr = None
        self._base_tags.append('GID')       # Sihot guest object id
        self.gid = None
        self._base_tags.append('MC')        # ae:05-12-2018 - added for to detect and suppress rental reservations
        self.mc = None


class ResChange(SihotXmlParser):
    def __init__(self, cae):
        super(ResChange, self).__init__(cae)
        self._base_tags.append('HN')    # def hotel ID as base tag, because is outside of 1st SIHOT-Reservation block
        self.hn = None                  # added instance var for to remove pycharm warning
        self.rgr_list = list()

    def start(self, tag, attrib):  # called for each opening tag
        if super(ResChange, self).start(tag, attrib) is None and tag not in ('MATCHCODE', 'OBJID'):
            return None  # processed by base class
        self.cae.dpo("ResChange.start():", self._elem_path)
        if tag == 'SIHOT-Reservation':
            self.rgr_list.append(dict(rgr_ho_fk=self.hn, ResPersons=list()))
        elif tag in ('FIRST-Person', 'SIHOT-Person'):       # FIRST-Person only seen in room change (CI) on first occ
            self.rgr_list[-1]['ResPersons'].append(dict())

    def data(self, data):
        if super(ResChange, self).data(data) is None and self._curr_tag not in ('MATCHCODE', 'OBJID'):
            return None  # processed by base class
        self.cae.dpo("ResChange.data():", self._elem_path, self.rgr_list)
        # flag for to detect and prevent multiple values
        append = True
        # because data can be sent in chunks on parsing, we first determine the dictionary (di) and the item key (ik)
        # rgr/reservation group elements
        if self._curr_tag == 'RNO':
            di, ik = self.rgr_list[-1], 'rgr_res_id'
        elif self._curr_tag == 'RSNO':
            di, ik = self.rgr_list[-1], 'rgr_sub_id'
        elif self._curr_tag == 'GDSNO':
            di, ik = self.rgr_list[-1], 'rgr_gds_no'
        elif self._elem_path == ['SIHOT-Document', 'SIHOT-Reservation', 'OBJID']:   # not provided by CI/CO/RM
            di, ik = self.rgr_list[-1], 'rgr_obj_id'
        elif self._elem_path == ['SIHOT-Document', 'SIHOT-Reservation', 'ARR']:
            di, ik = self.rgr_list[-1], 'rgr_arrival'
        elif self._elem_path == ['SIHOT-Document', 'SIHOT-Reservation', 'DEP']:
            di, ik = self.rgr_list[-1], 'rgr_departure'
        elif self._curr_tag == 'RT_SIHOT':                  # RT has different values (1=definitive, 2=tentative, 3=cxl)
            # data = 'S' if data == '3' else data           # .. so using undocumented RT_SIHOT to prevent conversion
            di, ik = self.rgr_list[-1], 'rgr_status'
        elif self._elem_path == ['SIHOT-Document', 'SIHOT-Reservation', 'NOPAX']:
            di, ik = self.rgr_list[-1], 'rgr_adults'
        elif self._elem_path == ['SIHOT-Document', 'SIHOT-Reservation', 'NOCHILDS']:  # not provided by CR
            di, ik = self.rgr_list[-1], 'rgr_children'

        # rgr/reservation group elements that are repeated (e.g. for each PAX in SIHOT-Person sections)
        elif self._curr_tag == 'CAT':
            di, ik = self.rgr_list[-1], 'rgr_room_cat_id'
            append = ik in di and len(di[ik]) < 4
        elif self._curr_tag == 'MC':
            di, ik = self.rgr_list[-1], 'rgr_mkt_segment'
            append = ik in di and len(di[ik]) < 2

        # rgc/reservation clients elements
        elif self._curr_tag == 'GID':                       # Sihot Guest object ID
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'PersShId'
        elif self._curr_tag == 'MATCHCODE':
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'PersAcuId'
        elif self._curr_tag == 'SN':
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'rgc_surname'
        elif self._curr_tag == 'CN':
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'rgc_firstname'
        elif self._curr_tag == 'DOB':
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'rgc_dob'
        elif self._curr_tag == 'PHONE':
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'rgc_phone'
        elif self._curr_tag == 'EMAIL':
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'rgc_email'
        elif self._curr_tag == 'LN':
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'rgc_language'
        elif self._curr_tag == 'COUNTRY':
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'rgc_country'
        elif self._curr_tag == 'RN':
            self.rgr_list[-1]['rgr_room_id'] = data     # update also rgr_room_id with same value
            di, ik = self.rgr_list[-1]['ResPersons'][-1], 'rgc_room_id'

        # unsupported elements
        else:
            self.cae.dpo("ResChange.data(): ignoring element ", self._elem_path, "; data chunk=", data,
                         minimum_debug_level=DEBUG_LEVEL_TIMESTAMPED)
            return

        # add data - after check if we need to add or to extend the dictionary item
        if ik not in di:
            di[ik] = data
        elif append:
            di[ik] += data


class ResResponse(SihotXmlParser):  # response xml parser for kernel or web interfaces
    def __init__(self, cae):
        super(ResResponse, self).__init__(cae)
        # web and kernel (guest/client and reservation) interface response elements
        self._base_tags.extend(['GDSNO', 'RES-NR', 'SUB-NR'])
        self.gdsno = self.res_nr = self.sub_nr = None


class AvailCatInfoResponse(SihotXmlParser):
    """ processing response of CATINFO operation code of the WEB interface """
    def __init__(self, cae):
        super(AvailCatInfoResponse, self).__init__(cae)
        self._curr_cat = None
        self._curr_day = None
        self.avail_room_cats = dict()

    def data(self, data):
        if super(AvailCatInfoResponse, self).data(data) is None:
            return None
        if self._curr_tag == 'CAT':
            self.avail_room_cats[data] = dict()
            self._curr_cat = data
        elif self._curr_tag == 'D':
            self.avail_room_cats[self._curr_cat][data] = dict()
            self._curr_day = data
        elif self._curr_tag in ('TOTAL', 'OOO'):
            self.avail_room_cats[self._curr_cat][self._curr_day][self._curr_tag] = int(data)
        elif self._curr_tag == 'OCC':
            self.avail_room_cats[self._curr_cat][self._curr_day][self._curr_tag] = float(data)
            day = self.avail_room_cats[self._curr_cat][self._curr_day]
            day['AVAIL'] = int(round_traditional(day['TOTAL'] * (1.0 - day['OCC'] / 100.0))) - day['OOO']
        return data


class CatRoomResponse(SihotXmlParser):
    def __init__(self, cae):
        super(CatRoomResponse, self).__init__(cae)
        # ALLROOMS response of the WEB interface
        self._base_tags += ('NAME', 'RN')
        self.name = None  # added for to remove pycharm warning
        self.rn = None
        self.cat_rooms = dict()  # for to store the dict with all key values

    def end(self, tag):
        if super(CatRoomResponse, self).end(tag) is None:
            return None  # tag used/processed by base class
        elif tag == 'NAME':
            self.cat_rooms[self.name] = list()
        elif tag == 'RN':
            self.cat_rooms[self.name].append(self.rn)
        return tag


class ConfigDictResponse(SihotXmlParser):
    def __init__(self, cae):
        super(ConfigDictResponse, self).__init__(cae)
        # response to GCF operation code of the WEB interface
        self._base_tags += ('KEY', 'VALUE')  # VALUE for key value (remove from additional error info - see 'VALU')
        self.value = None  # added for to remove pycharm warning
        self.key = None
        self.key_values = dict()  # for to store the dict with all key values

    def end(self, tag):
        if super(ConfigDictResponse, self).end(tag) is None:
            return None  # tag used/processed by base class
        elif tag == 'SIHOT-CFG':
            self.key_values[self.key] = self.value
        return tag


class ResKernelResponse(SihotXmlParser):
    """
    response to the RESERVATION-GET oc/request of the KERNEL interface
    """
    def __init__(self, cae):
        super(ResKernelResponse, self).__init__(cae)
        self._base_tags.append('HN')
        self._base_tags.append('RES-NR')
        self._base_tags.append('SUB-NR')
        self._base_tags.append('GDS-NR')


# XML BUILDER ##############################################################################


class SihotXmlBuilder:
    tn = '1'

    def __init__(self, cae, use_kernel=False):
        self.cae = cae
        self.debug_level = cae.get_opt('debugLevel')
        self.use_kernel_interface = use_kernel
        self.response = None

        self._xml = ''

    def beg_xml(self, operation_code, add_inner_xml='', transaction_number=''):
        enc = self.cae.get_opt(SDF_SH_XML_ENCODING) or ""
        if enc:
            enc = f' encoding="{enc.lower()}"'
        self._xml = f'<?xml version="1.0"{enc}?>\n<SIHOT-Document>\n'
        if self.use_kernel_interface:
            self._xml += '<SIHOT-XML-REQUEST>\n'
            self.add_tag('REQUEST-TYPE', operation_code)
        else:
            self.add_tag('OC', operation_code)
            if transaction_number:
                self.tn = transaction_number
            else:
                try:
                    self.tn = str(int(self.tn) + 1)
                except OverflowError as _:
                    self.tn = '1'
            self.add_tag('TN', self.tn)
        self._xml += add_inner_xml

    def end_xml(self):
        if self.use_kernel_interface:
            self._xml += '\n</SIHOT-XML-REQUEST>'
        self._xml += '\n</SIHOT-Document>'

    def add_tag(self, tag, val=''):
        self._xml += self.new_tag(tag, val)

    def send_to_server(self, response_parser=None):
        sc = _TcpClient(self.cae.get_opt('shServerIP'),
                        self.cae.get_opt(SDF_SH_KERNEL_PORT if self.use_kernel_interface else SDF_SH_WEB_PORT),
                        timeout=self.cae.get_opt(SDF_SH_TIMEOUT),
                        encoding=self.cae.get_opt(SDF_SH_XML_ENCODING),
                        debug_level=self.debug_level)
        self.cae.dpo("SihotXmlBuilder.send_to_server(): resp_parser={}\nxml=\n{}".format(response_parser, self.xml))
        err_msg = sc.send_to_server(self.xml)
        if not err_msg:
            self.response = response_parser or SihotXmlParser(self.cae)
            self.response.parse_xml(sc.received_xml)
            err_num = self.response.server_error()
            if err_num != '0':
                err_msg = self.response.server_err_msg()
                if err_msg:
                    err_msg = "msg='{}'".format(err_msg)
                elif err_num == '29':
                    err_msg = "No Reservations Found"
                if err_num != '1' or self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    err_msg += "; sent xml='{}'; got xml='{}'".format(self.xml, sc.received_xml)[0 if err_msg else 2:]
                err_msg = "server return code {} {}".format(err_num, err_msg)

        if err_msg:
            self.cae.po("****  SihotXmlBuilder.send_to_server() error: {}".format(err_msg))
        return err_msg

    @staticmethod
    def new_tag(tag, val='', opening=True, closing=True):
        return ('<' + tag + '>' if opening else '') \
               + str(val or '') \
               + ('</' + tag + '>' if closing else '')

    @staticmethod
    def convert_value_to_xml_string(value):
        # ret = str(val) if val else ''  # not working with zero value
        ret = '' if value is None else str(value)  # convert None to empty string
        if isinstance(value, (datetime.datetime, datetime.date)) and ret.endswith(' 00:00:00'):
            ret = ret[:-9]
        # escape special characters while preserving already escaped characters - by first un-escape then escape again
        for key, val in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;')]:
            ret = ret.replace(key, val)
        return ret

    @property
    def xml(self):
        return self._xml

    @xml.setter
    def xml(self, value):
        self.cae.dpo('SihotXmlBuilder.xml-set:', value)
        self._xml = value


class AvailCatInfo(SihotXmlBuilder):
    def avail_rooms(self, hotel_id='', room_cat='', from_date=datetime.date.today(), to_date=datetime.date.today()):
        # flags=''):  # SKIP-HIDDEN-ROOM-TYPES'):
        self.beg_xml(operation_code='CATINFO')
        if hotel_id:
            self.add_tag('ID', hotel_id)
        self.add_tag('FROM', datetime.date.strftime(from_date, DATE_ISO))     # mandatory
        self.add_tag('TO', datetime.date.strftime(to_date, DATE_ISO))
        if room_cat:
            self.add_tag('CAT', room_cat)
        # if flags:
        #     self.add_tag('FLAGS', flags)    # there is no FLAGS element for the CATINFO oc?!?!?
        self.end_xml()

        err_msg = self.send_to_server(response_parser=AvailCatInfoResponse(self.cae))

        return err_msg or self.response.avail_room_cats


class CatRooms(SihotXmlBuilder):
    def get_cat_rooms(self, hotel_id='1', from_date=datetime.date.today(), to_date=datetime.date.today(),
                      scope=None):
        self.beg_xml(operation_code='ALLROOMS')
        self.add_tag('ID', hotel_id)  # mandatory
        self.add_tag('FROM', datetime.date.strftime(from_date, DATE_ISO))  # mandatory
        self.add_tag('TO', datetime.date.strftime(to_date, DATE_ISO))
        if scope:
            self.add_tag('SCOPE', scope)  # pass 'DESC' for to get room description
        self.end_xml()

        err_msg = self.send_to_server(response_parser=CatRoomResponse(self.cae))

        return err_msg or self.response.cat_rooms


class ConfigDict(SihotXmlBuilder):
    def get_key_values(self, config_type, hotel_id='1', language='EN'):
        self.beg_xml(operation_code='GCF')
        self.add_tag('CFTYPE', config_type)
        self.add_tag('HN', hotel_id)  # mandatory
        self.add_tag('LN', language)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ConfigDictResponse(self.cae))

        return err_msg or self.response.key_values


class PostMessage(SihotXmlBuilder):
    def post_message(self, msg, level=3, system='sys_core_sh_module'):
        self.beg_xml(operation_code='SYSMESSAGE')
        self.add_tag('MSG', msg)
        self.add_tag('LEVEL', str(level))
        self.add_tag('SYSTEM', system)
        self.end_xml()

        err_msg = self.send_to_server()
        if err_msg:
            ret = err_msg
        else:
            ret = '' if self.response.rc == '0' else 'Error code ' + self.response.rc

        return ret


class ResKernelGet(SihotXmlBuilder):
    def __init__(self, cae):
        super(ResKernelGet, self).__init__(cae, use_kernel=True)

    def fetch_res_no(self, obj_id, scope='GET'):
        """
        return dict with guest data OR None in case of error

        :param obj_id:  Sihot reservation object id.
        :param scope:   search scope string (see 7.3.1.2 in Sihot KERNEL interface doc V 9.0)
        :return:        reservation ids as tuple of (hotel_id, res_id, sub_id, gds_no) or (None, "error") if not found
        """
        msg = "ResKernelGet.fetch_res_no({}, {}) ".format(obj_id, scope)
        self.beg_xml(operation_code='RESERVATION-GET')
        self.add_tag('RESERVATION-PROFILE', self.new_tag('OBJID', obj_id) + self.new_tag('SCOPE', scope))
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ResKernelResponse(self.cae))
        if not err_msg and self.response:
            res_no = (self.response.hn, self.response.res_nr, self.response.sub_nr, self.response.gds_nr)
            self.cae.dpo(msg + "res_no={};\nxml=\n{}".format(res_no, self.xml))
        else:
            res_no = (None, err_msg)
            self.cae.po(msg + "error='{}'".format(err_msg))
        return res_no


class ShSysConnector(SystemConnectorBase):
    def connect(self) -> str:
        """ not needed - lazy connection """
        return self.last_err_msg

    @staticmethod
    def clients_match_field_init(match_fields):
        msg = "ShSysConnector.clients_match_field_init({}) expects ".format(match_fields)
        supported_match_fields = [SH_DEF_SEARCH_FIELD, 'AcuId', 'Surname', 'Email']

        if match_fields:
            match_field = match_fields[0]
            if len(match_fields) > 1:
                return msg + "single match field"
            elif match_field not in supported_match_fields:
                return "only one of the match fields {} (not {})".format(supported_match_fields, match_field)
        else:
            match_field = SH_DEF_SEARCH_FIELD

        return match_field
