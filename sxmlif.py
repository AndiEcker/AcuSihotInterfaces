# SiHOT xml interface
import datetime
import pprint

# import xml.etree.ElementTree as Et
from xml.etree.ElementTree import XMLParser, ParseError

from sys_data_ids import DEBUG_LEVEL_VERBOSE, DEBUG_LEVEL_TIMESTAMPED, SDF_SH_KERNEL_PORT, SDF_SH_WEB_PORT, \
    SDF_SH_TIMEOUT, SDF_SH_XML_ENCODING
# fix_encoding() needed for to clean and re-parse XML on invalid char code exception/error
from ae_console_app import fix_encoding, uprint, round_traditional
from ae_tcp import TcpClient

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
# then added an output type handler to the connection (see db.py) which did not solve the problem (because
# .. the db.py module is not using this default encoding but the one in NLS_LANG env var
# For to fix showing umlaut character correctly tried cp1252 (windows charset)
# .. and finally this worked for all characters (because it has less undefined code points_import)
# SXML_DEF_ENCODING = 'cp1252'
# But with the added errors='backslashreplace' argument for the bytes() new/call used in the TcpClient.send_to_server()
# .. method we try sihot interface encoding again
# but SXML_DEF_ENCODING = 'ISO-8859-1' failed again with umlaut characters
# .. Y203585/HUN - Name decoded wrongly with ISO
SXML_DEF_ENCODING = 'cp1252'

# special error message prefixes
ERR_MESSAGE_PREFIX_CONTINUE = 'CONTINUE:'


ppf = pprint.PrettyPrinter(indent=12, width=96, depth=9).pformat


#  HELPER METHODS  ###################################

def elem_to_attr(elem):
    return elem.lower().replace('-', '_')


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
        self.cae = cae  # only needed for logging with dprint()
        self._parser = None  # reset to XMLParser(target=self) in self.parse_xml() and close in self.close()

    def parse_xml(self, xml):
        self.cae.dprint("SihotXmlParser.parse_xml():", xml, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        try_counter = 0
        xml_cleaned = xml
        while True:
            try:
                self._xml = xml_cleaned
                self._parser = XMLParser(target=self)
                self._parser.feed(xml_cleaned)
                break
            except ParseError as pex:
                xml_cleaned = fix_encoding(xml_cleaned, try_counter=try_counter, pex=pex,
                                           context="SihotXmlParser.parse_xml() ParseError exception")
                if not xml_cleaned:
                    raise
            try_counter += 1

    def get_xml(self):
        return self._xml

    # xml parsing interface

    def start(self, tag, attrib):  # called for each opening tag
        self._curr_tag = tag
        self._curr_attr = None  # used as flag for a currently parsed base tag (for self.data())
        self._elem_path.append(tag)
        if tag in self._base_tags:
            self.cae.dprint("SihotXmlParser.start():", self._elem_path, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
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
            self.cae.dprint("SihotXmlParser.data(): ", self._elem_path, data, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            setattr(self, self._curr_attr, getattr(self, self._curr_attr) + data)
            return None
        return data

    def end(self, tag):  # called for each closing tag
        self.cae.dprint("SihotXmlParser.end():", self._elem_path, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
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
        self.cae.dprint("ResChange.start():", self._elem_path, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        if tag == 'SIHOT-Reservation':
            self.rgr_list.append(dict(rgr_ho_fk=self.hn, ResPersons=list()))
        elif tag in ('FIRST-Person', 'SIHOT-Person'):       # FIRST-Person only seen in room change (CI) on first occ
            self.rgr_list[-1]['ResPersons'].append(dict())

    def data(self, data):
        if super(ResChange, self).data(data) is None and self._curr_tag not in ('MATCHCODE', 'OBJID'):
            return None  # processed by base class
        self.cae.dprint("ResChange.data():", self._elem_path, self.rgr_list, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
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
            self.cae.dprint("ResChange.data(): ignoring element ", self._elem_path, "; data chunk=", data,
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


class SihotXmlBuilder:
    tn = '1'

    def __init__(self, cae, use_kernel=False):
        self.cae = cae
        self.debug_level = cae.get_option('debugLevel')
        self.use_kernel_interface = use_kernel
        self.response = None

        self._xml = ''

    def beg_xml(self, operation_code, add_inner_xml='', transaction_number=''):
        self._xml = '<?xml version="1.0" encoding="' + self.cae.get_option(SDF_SH_XML_ENCODING).lower() + \
                    '"?>\n<SIHOT-Document>\n'
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
        sc = TcpClient(self.cae.get_option('shServerIP'),
                       self.cae.get_option(SDF_SH_KERNEL_PORT if self.use_kernel_interface else SDF_SH_WEB_PORT),
                       timeout=self.cae.get_option(SDF_SH_TIMEOUT),
                       encoding=self.cae.get_option(SDF_SH_XML_ENCODING),
                       debug_level=self.debug_level)
        self.cae.dprint("SihotXmlBuilder.send_to_server(): response_parser={}\nxml=\n{}"
                        .format(response_parser, self.xml), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
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
            uprint("****  SihotXmlBuilder.send_to_server() error: {}".format(err_msg))
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
        self.cae.dprint('SihotXmlBuilder.xml-set:', value, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self._xml = value


class AvailCatInfo(SihotXmlBuilder):
    def avail_rooms(self, hotel_id='', room_cat='', from_date=datetime.date.today(), to_date=datetime.date.today()):
        # flags=''):  # SKIP-HIDDEN-ROOM-TYPES'):
        self.beg_xml(operation_code='CATINFO')
        if hotel_id:
            self.add_tag('ID', hotel_id)
        self.add_tag('FROM', datetime.date.strftime(from_date, '%Y-%m-%d'))     # mandatory
        self.add_tag('TO', datetime.date.strftime(to_date, '%Y-%m-%d'))
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
        self.add_tag('FROM', datetime.date.strftime(from_date, '%Y-%m-%d'))  # mandatory
        self.add_tag('TO', datetime.date.strftime(to_date, '%Y-%m-%d'))
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
    def post_message(self, msg, level=3, system='sxmlif_module'):
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
        """
        msg = "ResKernelGet.fetch_res_no({}, {}) ".format(obj_id, scope)
        self.beg_xml(operation_code='RESERVATION-GET')
        self.add_tag('RESERVATION-PROFILE', self.new_tag('OBJID', obj_id) + self.new_tag('SCOPE', scope))
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ResKernelResponse(self.cae))
        if not err_msg and self.response:
            res_no = (self.response.hn, self.response.res_nr, self.response.sub_nr)
            self.cae.dprint(msg + "res_no={};\nxml=\n{}".format(res_no, self.xml),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        else:
            res_no = None
            uprint(msg + "error='{}'".format(err_msg))
        return res_no
