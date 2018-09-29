# SiHOT xml interface
import datetime
from copy import deepcopy
from textwrap import wrap

# import xml.etree.ElementTree as Et
from xml.etree.ElementTree import XMLParser, ParseError

from ae_sys_data import FAT_NAME, FAT_REC, FAT_VAL, FAT_FLT, FAD_FROM, FAD_ONTO, Field, Record, Records
# fix_encoding() needed for to clean and re-parse XML on invalid char code exception/error
from ae_console_app import fix_encoding, uprint, round_traditional, DEBUG_LEVEL_VERBOSE, DEBUG_LEVEL_TIMESTAMPED
from ae_tcp import TcpClient

from sys_data_ids import SDI_SW, SDI_SH

# data actions
ACTION_DELETE = 'DELETE'
ACTION_INSERT = 'INSERT'
ACTION_UPDATE = 'UPDATE'
ACTION_SEARCH = 'SEARCH'

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

# ensure client modes (used by ResToSihot.send_row_to_sihot())
ECM_ENSURE_WITH_ERRORS = 0
ECM_TRY_AND_IGNORE_ERRORS = 1
ECM_DO_NOT_SEND_CLIENT = 2

ELEM_PATH_SEP = '.'


#  HELPER METHODS  ###################################

def _strip_error_message(error_msg):
    pos1 = error_msg.find('error:')
    if pos1 != -1:
        pos1 += 5  # put to position - 1 (for to allow -1 as valid pos if nothing got found)
    else:
        pos1 = error_msg.find('::')
    pos1 += 1

    pos2 = error_msg.find('.', pos1)
    pos3 = error_msg.find('!', pos1)
    if max(pos2, pos3) - pos1 <= 30:
        pos2 = len(error_msg)

    return error_msg[pos1: max(pos2, pos3)]


def convert2date(xml_string):
    """ needed for the maps in the valToAcuConverter dict item """
    return datetime.datetime.strptime(xml_string, '%Y-%m-%d')


def elem_path_values(elem_fld_map, elem_path_suffix):
    """
    determine list of data values from the passed elem_fld_map (extended by FldMapXmlParser) of all element paths
    ending with the passed elem_path_suffix string value.
    :param elem_fld_map:        element field map dict in the form {elem_name: sys-data-Field}.
    :param elem_path_suffix:    element path (either full path or suffix, e.g. SIHOT-Document.ARESLIST.RESERVATION.ARR)
    :return:                    merged list of all parsed data in fld map with passed element path suffix
    """
    ret_list = list()
    for fld in elem_fld_map.values():
        paths_values = fld.paths(system=SDI_SW, direction=FAD_FROM)
        if paths_values:
            for path_key, values in paths_values:
                if path_key.endswith(elem_path_suffix):
                    ret_list.extend(values)
    return ret_list


#  ELEMENT-FIELD-MAPS  #################################

MTI_ELEM_NAME = 0
MTI_FIELD_NAME = 1
MTI_HIDE_IF = 2
MTI_FIELD_VAL = 3
MTI_FIELD_TYPE = 4
MTI_FIELD_CON = 5   # currently only needed for kernel DOB field

# mapping element name in tuple item 0 onto field name in [1], hideIf callable in [2] and default field value in [3]
# default map for GuestFromSihot.elem_fld_map instance and as read-only constant by AcuClientToSihot using the SIHOT
# .. KERNEL interface because SiHOT WEB V9 has missing fields: initials (CD_INIT1/2) and profession (CD_INDUSTRY1/2)
MAP_KERNEL_CLIENT = \
    (
        ('OBJID', 'ShId',
         lambda f: f.ica(ACTION_INSERT)),
        ('MATCHCODE', 'AcId'),
        ('GUEST-NR', 'SH_GUEST_NO',  # only needed for GUEST-SEARCH/get_objid_by_guest_no()
         lambda f: not f.csv()),
        ('FLAGS', 'SH_FLAGS',        # only needed for GUEST-SEARCH/get_objid_by_guest_no()
         lambda f: not f.csv()),
        ('T-SALUTATION', 'Salutation'),  # also exists T-ADDRESS/T-PERSONAL-SALUTATION
        ('T-TITLE', 'Title'),
        ('T-GUEST', 'GuestType'),
        ('NAME-1', 'Surname'),
        ('NAME-2', 'Forename'),
        ('STREET', 'Street'),
        ('PO-BOX', 'POBox'),
        ('ZIP', 'Postal'),
        ('CITY', 'City'),
        ('T-COUNTRY-CODE', 'Country'),
        ('T-STATE', 'State',
         lambda f: not f.csv()),
        ('T-LANGUAGE', 'Language'),
        ('COMMENT', 'Comment'),
        ('COMMUNICATION/', None,
         lambda f: f.ica(ACTION_SEARCH)),
        ('PHONE-1', 'HomePhone'),
        ('PHONE-2', 'WorkPhone'),
        ('FAX-1', 'Fax'),
        ('EMAIL-1', 'Email'),
        ('EMAIL-2', 'Email2'),
        ('MOBIL-1', 'MobilePhone'),
        ('MOBIL-2', 'MobilePhone2'),
        ('/COMMUNICATION', None,
         lambda f: f.ica(ACTION_SEARCH)),
        ('ADD-DATA/', None,
         lambda f: f.ica(ACTION_SEARCH)),
        ('T-PERSON-GROUP', None, "1A"),
        ('D-BIRTHDAY', 'DOB',
         None, None, None, lambda f, v: convert2date(v)),
        # 27-09-17: removed b4 migration of BHH/HMC because CD_INDUSTRY1/2 needs first grouping into 3-alphanumeric code
        # ('T-PROFESSION', 'CD_INDUSTRY1'),
        ('INTERNET-PASSWORD', 'Password'),
        ('MATCH-ADM', 'RCIRef'),
        ('MATCH-SM', 'SfId'),
        ('/ADD-DATA', None,
         lambda f: f.ica(ACTION_SEARCH)),
        ('L-EXTIDS/', None,
         lambda f: f.ica(ACTION_SEARCH)),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs')),
        ('TYPE', 'ExtRefType1',
         lambda f: not f.csv('ExtRefs')),
        ('ID', 'ExtRefId1',
         lambda f: not f.csv('ExtRefs')),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs')),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 1),
        ('TYPE', 'ExtRefType2',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 1),
        ('ID', 'ExtRefId2',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 1),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 1),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 2),
        ('TYPE', 'ExtRefType3',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 2),
        ('ID', 'ExtRefId3',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 2),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 2),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 3),
        ('TYPE', 'ExtRefType4',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 3),
        ('ID', 'ExtRefId4',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 3),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 3),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 4),
        ('TYPE', 'ExtRefType5',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 4),
        ('ID', 'ExtRefId5',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 4),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 4),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 5),
        ('TYPE', 'ExtRefType6',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 5),
        ('ID', 'ExtRefId6',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 5),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 5),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 6),
        ('TYPE', 'ExtRefType7',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 6),
        ('ID', 'ExtRefId7',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 6),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 6),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 7),
        ('TYPE', 'ExtRefType8',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 7),
        ('ID', 'ExtRefId8',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 7),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 7),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 8),
        ('TYPE', 'ExtRefType9',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 8),
        ('ID', 'ExtRefId9',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 8),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 8),
        ('EXTID/', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 9),
        ('TYPE', 'ExtRefType10',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 9),
        ('ID', 'ExtRefId10',
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 9),
        ('/EXTID', None,
         lambda f: not f.csv('ExtRefs') or f.csv('ExtRefs').count(', ') > 9),
        ('/L-EXTIDS', None,
         lambda f: f.ica(ACTION_SEARCH)),
    )

MAP_PARSE_KERNEL_CLIENT = \
    (
        ('EXT_REFS', 'ExtRefs'),  # only for elemHideIf expressions
        ('CDLREF', 'CDL_CODE'),
        # ('STATUS', 'CD_STATUS', 'fldValToAcu': 500),
        # ('PAF_STAT', 'CD_PAF_STATUS', 'fldValToAcu': 0),
    )

# Reservation interface mappings
# .. first the mapping for the WEB interface
""" taken from SIHOT.WEB IF doc page 58:
    The first scope contains the following mandatory fields for all external systems and for SIHOT.PMS:

        <GDSNO>, <RT>, <ARR>, <DEP>, <LAST-MOD>, <CAT>, <NOPAX>, <NOCHILDS>, <NOROOMS>, <NAME> or <COMPANY>.

    With reservations from external systems is <PRICE-TOTAL> a mandatory field. With reservations for SIHOT.PMS,
    <MATCHCODE> and <PWD> are mandatory fields.
"""
MAP_WEB_RES = \
    (
        ('ID', 'ResHotelId'),  # ID elem or use [RES-]HOTEL/IDLIST/MANDATOR-NO/EXTERNAL-SYSTEM-ID
        ('ARESLIST/', ),
        ('RESERVATION/', ),
        # ### main reservation info: orderer, status, external booking references, room/price category, ...
        # MATCHCODE, NAME, COMPANY and GUEST-ID are mutually exclusive
        # MATCHCODE/GUEST-ID needed for DELETE action for to prevent Sihot error:
        # .. "Could not find a key identifier for the client (name, matchcode, ...)"
        # ('GUEST-ID', 'ResOrdererId',
        #  'elemHideIf':  "not c.get('ResOrdererId') and not c.get['ShId']"},
        ('GUEST-ID', 'ResOrdererId',
         lambda f: not f.csv() and not f.csv('ShId')),
        ('MATCHCODE', 'ResOrdererMc'),
        ('GDSNO', 'ResGdsNo'),
        ('VOUCHERNUMBER', 'ResVoucherNo',
         lambda f: f.ica(ACTION_DELETE)),
        ('EXT-KEY', 'ResGroupNo',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        ('FLAGS', None,
         None, 'IGNORE-OVERBOOKING'),  # ;NO-FALLBACK-TO-ERRONEOUS'),
        ('RT', 'ResStatus'),
        # ResRoomCat results in error 1011 for tk->TC/TK bookings with room move and room with higher/different room
        # .. cat, therefore use price category as room category for Thomas Cook Bookings.
        # .. similar problems we experienced when we added the RCI Allotments (here the CAT need to be the default cat)
        # .. on the 24-05-2018 so finally we replaced the category of the (maybe) allocated room with the cat that
        # .. get determined from the requested room size
        ('CAT', 'ResRoomCat'),  # needed for DELETE action
        ('PCAT', 'ResPriceCat',
         lambda f: f.ica(ACTION_DELETE)),
        ('ALLOTMENT-EXT-NO', 'ResAllotmentNo',
         lambda f: not f.csv(),  ''),
        ('PAYMENT-INST', 'ResAccount',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        ('SALES-DATE', 'ResBooked',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        ('RATE-SEGMENT', 'ResRateSegment',
         lambda f: not f.csv(), ''),
        ('RATE/', ),  # package/arrangement has also to be specified in PERSON:
        ('R', 'ResBoard'),
        ('ISDEFAULT', None, None, 'Y'),
        ('/RATE', ),
        ('RATE/', None,
         lambda f: f.ica(ACTION_DELETE) or f.csv('ResMktSegment') not in ('ER', )),
        ('R', None,
         lambda f: f.ica(ACTION_DELETE) or not f.csv('ResMktSegment') not in ('ER', ), 'GSC'),
        ('ISDEFAULT', None,
         lambda f: f.ica(ACTION_DELETE) or not f.csv('ResMktSegment') not in ('ER', ), 'N'),
        ('/RATE', None,
         lambda f: f.ica(ACTION_DELETE) or not f.csv('ResMktSegment') not in ('ER', )),
        # The following fallback rate results in error Package TO not valid for hotel 1
        # ('RATE/', ),
        # ('R', 'RO_SIHOT_RATE'},
        # ('ISDEFAULT', None, None, 'N'),
        # ('/RATE', ),
        # ### Reservation Channels - used for assignment of reservation to a allotment or to board payment
        ('RESCHANNELLIST/', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup')[:4] not in ('Owne', 'Prom', 'RCI ')),
        ('RESCHANNEL/', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup')[:4] not in ('Owne', 'Prom', 'RCI ')),
        # needed for to add RCI booking to RCI allotment
        ('IDX', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup')[:4] not in ('RCI ', ), 1),
        ('MATCHCODE', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup')[:4] not in ('RCI ', ), 'RCI'),
        ('ISPRICEOWNER', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup')[:4] not in ('RCI ', ), 1),
        # needed for marketing fly buys for board payment bookings
        ('IDX', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup') not in ('Promo', ), 1),
        ('MATCHCODE', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup') not in ('Promo', ), 'MAR01'),
        ('ISPRICEOWNER', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup') not in ('Promo', ), 1),
        # needed for owner bookings for to select/use owner allotment
        ('IDX', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup') not in ('Owner', ), 2),
        ('MATCHCODE', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup') not in ('Owner', ), 'TSP'),
        ('ISPRICEOWNER', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup') not in ('Owner', ), 1),
        ('/RESCHANNEL', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup')[:4] not in ('Owne', 'Prom', 'RCI ')),
        ('/RESCHANNELLIST', None,
         lambda f: not f.csv('ResAllotmentNo') or f.csv('ResMktGroup')[:4] not in ('Owne', 'Prom', 'RCI ')),
        # ### GENERAL RESERVATION DATA: arrival/departure, pax, market sources, comments
        ('ARR', 'ResArrival'),
        ('DEP', 'ResDeparture'),
        ('NOROOMS', None, None, 1),  # needed for DELETE action
        ('NOPAX', 'ResAdults'),  # needed for DELETE action
        ('NOCHILDS', 'ResChildren',
         lambda f: f.ica(ACTION_DELETE)),
        ('TEC-COMMENT', 'ResLongNote',
         lambda f: f.ica(ACTION_DELETE)),
        ('COMMENT', 'ResNote',
         lambda f: f.ica(ACTION_DELETE)),
        ('MARKETCODE-NO', 'ResMktSegment',
         lambda f: f.ica(ACTION_DELETE)),
        # ('MEDIA', ),
        ('SOURCE', 'ResSource',
         lambda f: f.ica(ACTION_DELETE)),
        ('NN', 'ResMktGroup2',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        ('CHANNEL', 'ResMktGroup',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        # ('NN2', 'ResSfId',
        # lambda f: not f.csv()),
        ('EXT-REFERENCE', 'ResFlightNo',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),    # see also currently unused PICKUP-COMMENT-ARRIVAL element
        ('ARR-TIME', 'ResFlightETA',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        ('PICKUP-TIME-ARRIVAL', 'ResFlightETA',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        ('PICKUP-TYPE-ARRIVAL', None,                       # 1=car, 2=van
         lambda f: f.ica(ACTION_DELETE) or not f.csv('ResFlightETA'), 1),
        # ### PERSON/occupant details
        ('PERS-TYPE-LIST/', ),
        ('PERS-TYPE/', ),
        ('TYPE', None, None, '1A'),
        ('NO', 'ResAdults'),
        ('/PERS-TYPE', ),
        ('PERS-TYPE/', ),
        ('TYPE', None, None, '2B'),
        ('NO', 'ResChildren'),
        ('/PERS-TYPE', ),
        ('/PERS-TYPE-LIST', ),
        # Person Records
        ('PERSON/', 'ResPersons',
         lambda f: f.ica(ACTION_DELETE),
         None, Records),
        ('NAME', 'ResPersonSurname',
         lambda f: f.ica(ACTION_DELETE) or not f.csv() or f.csv('AcId') or f.csv('ShId'),
         lambda f: "Adult " + str(f.idx()) if f.idx() < f.csv('ResAdults')
            else "Child " + str(f.idx() - f.csv('ResAdults') + 1)),
        ('NAME2', 'ResPersonForename',
         lambda f: f.ica(ACTION_DELETE) or not f.csv() or f.csv('AcId') or f.csv('ShId')),
        ('AUTO-GENERATED', 'ResPersonAutoGenerated',
         lambda f: f.ica(ACTION_DELETE) or (f.csv('ResAdults') <= 2 and (f.csv('AcId') or f.csv('ShId'))), '1'),
        ('MATCHCODE', 'AcId',
         lambda f: f.ica(ACTION_DELETE) or not f.csv() or f.csv('ShId')),
        ('GUEST-ID', 'ShId',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        ('ROOM-SEQ', None,
         lambda f: f.ica(ACTION_DELETE), '0'),
        ('ROOM-PERS-SEQ', None,
         lambda f: f.ica(ACTION_DELETE), lambda f: str(f.idx())),
        ('PERS-TYPE', None,
         lambda f: f.ica(ACTION_DELETE), lambda f: '1A' if f.idx() < f.csv('ResAdults') else '2B'),
        ('R', 'ResBoard',
         lambda f: f.ica(ACTION_DELETE)),
        ('RN', 'ResRoomNo',
         lambda f: f.ica(ACTION_DELETE) or not f.csv() or f.csv('ResDeparture') < datetime.datetime.now()),
        ('DOB', 'ResPersonDOB',
         lambda f: f.ica(ACTION_DELETE) or not f.csv()),
        ('/PERSON', None,
         lambda f: f.ica(ACTION_DELETE) or f.csv('ResAdults') <= 0),
        ('/RESERVATION',),
        ('/ARESLIST',),
    )

MAP_PARSE_WEB_RES = \
    (   # ### EXTRA PARSING FIELDS (for to interpret reservation coming from the WEB interface)
        ('ACTION', 'ResAction'),
        ('STATUS', 'RU_STATUS'),
        ('RULREF', 'RUL_CODE'),
        ('RUL_PRIMARY', 'RUL_PRIMARY'),
        # ('RU_OBJID', 'RU_SIHOT_OBJID'),
        ('RU_OBJID', 'RUL_SIHOT_OBJID'),
        # ('RO_AGENCY_OBJID', 'RO_SIHOT_AGENCY_OBJID'),
        ('OC_CODE', 'ResOrdererMc'),
        ('OC_OBJID', 'ResOrdererId'),
        ('RES_GROUP', 'ResMktGroup'),  # needed for elemHideIf
        ('RES_OCC', 'ResMktSegment'),  # needed for res_id_values
        ('CHANGES', 'RUL_CHANGES'),  # needed for error notifications
        ('LAST_HOTEL', 'RUL_SIHOT_LAST_HOTEL'),  # needed for HOTMOVE
        ('LAST_CAT', 'RUL_SIHOT_LAST_CAT'),  # needed for HOTMOVE
        # field mappings needed only for parsing XML responses (using 'buildExclude': True)
        ('RES-HOTEL', ),
        ('RES-NR', ),
        ('SUB-NR', ),
        ('OBJID', ),
        ('EMAIL', ),
        ('PHONE', ),
        # PHONE1, MOBIL1 and EMAIL1 are only available in RES person scope/section but not in RES-SEARCH OC
        # ('PHONE1', ),
        # ('MOBIL1', ),
        ('DEP-TIME', ),
        ('COUNTRY', ),
        ('CITY', ),
        ('STREET', ),
        ('LANG', ),
        ('MARKETCODE', ),     # RES-SEARCH has no MARKETCODE-NO element/tag
    )

# default values for used interfaces (see email from Sascha Scheer from 28 Jul 2016 13:48 with answers from JBerger):
# .. use kernel for clients and web for reservations
USE_KERNEL_FOR_CLIENTS_DEF = True
MAP_CLIENT_DEF = MAP_KERNEL_CLIENT

USE_KERNEL_FOR_RES_DEF = False
MAP_RES_DEF = MAP_WEB_RES


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
                self._parser = XMLParser(target=self)
                self._parser.feed(xml_cleaned)
                self._xml = xml_cleaned
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
            self._curr_attr = tag.lower().replace('-', '_')
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
        self.cae.dprint("SihotXmlParser.end():", self._elem_path, tag, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
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
            self.rgr_list.append(dict(rgr_ho_fk=self.hn, rgc_list=list()))
        elif tag in ('FIRST-Person', 'SIHOT-Person'):       # FIRST-Person only seen in room change (CI) on first occ
            self.rgr_list[-1]['rgc_list'].append(dict())

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
        elif self._elem_path == ['SIHOT-Document', 'SIHOT-Reservation', 'OBJID']:   # TODO: not provided by CI/CO/RM
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
        elif self._elem_path == ['SIHOT-Document', 'SIHOT-Reservation', 'NOCHILDS']:  # TODO: not provided by CR
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
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'ShId'
        elif self._curr_tag == 'MATCHCODE':
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'AcId'
        elif self._curr_tag == 'SN':
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'rgc_surname'
        elif self._curr_tag == 'CN':
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'rgc_firstname'
        elif self._curr_tag == 'DOB':
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'rgc_dob'
        elif self._curr_tag == 'PHONE':
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'rgc_phone'
        elif self._curr_tag == 'EMAIL':
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'rgc_email'
        elif self._curr_tag == 'LN':
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'rgc_language'
        elif self._curr_tag == 'COUNTRY':
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'rgc_country'
        elif self._curr_tag == 'RN':
            self.rgr_list[-1]['rgr_room_id'] = data     # update also rgr_room_id with same value
            di, ik = self.rgr_list[-1]['rgc_list'][-1], 'rgc_room_id'

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
        self._base_tags.append('GDSNO')
        self.gdsno = None


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


class GuestSearchResponse(SihotXmlParser):
    def __init__(self, cae, ret_elem_names=None, key_elem_name=None):
        """
        response to the GUEST-GET request oc of the KERNEL interface

        ret_elem_names is a list of xml element names (or response attributes) to return. If there is only one
        list element with a leading ':' character then self.ret_elem_values will be a dict with the search value
        as the key. If ret_elem_names consists of exact one item then ret_elem_values will be a list with the
        plain return values. If ret_elem_names contains more than one item then self.ret_elem_values will be
        a dict where the ret_elem_names are used as keys. If the ret_elem_names list is empty (or None) then the
        returned self.ret_elem_values list of dicts will provide all elements that are returned by the
        Sihot interface and defined within the used map (MAP_KERNEL_CLIENT).

        key_elem_name is the element name used for the search (only needed if self._return_value_as_key==True)
        """
        super(GuestSearchResponse, self).__init__(cae)
        self._base_tags.append('GUEST-NR')
        self.guest_nr = None

        full_map = MAP_KERNEL_CLIENT + MAP_PARSE_KERNEL_CLIENT

        self._key_elem_name = key_elem_name
        if not ret_elem_names:
            ret_elem_names = [_[MTI_ELEM_NAME] for _ in full_map]
        self._ret_elem_names = ret_elem_names    # list of names of XML-elements or response-base-attributes
        self._return_value_as_key = len(ret_elem_names) == 1 and ret_elem_names[0][0] == ':'

        self.ret_elem_values = dict() if self._return_value_as_key else list()
        self._key_elem_index = 0
        self._in_guest_profile = False
        self._elem_fld_map_parser = FldMapXmlParser(cae, deepcopy(full_map))

    def parse_xml(self, xml):
        super(GuestSearchResponse, self).parse_xml(xml)
        self._key_elem_index = 0
        self._in_guest_profile = False

    def start(self, tag, attrib):
        if self._in_guest_profile:
            self._elem_fld_map_parser.start(tag, attrib)
        if super(GuestSearchResponse, self).start(tag, attrib) is None:
            return None  # processed by base class
        if tag == 'GUEST-PROFILE':
            self._key_elem_index += 1
            self._in_guest_profile = True
            return None
        return tag

    def data(self, data):
        if self._in_guest_profile:
            self._elem_fld_map_parser.data(data)
        if super(GuestSearchResponse, self).data(data) is None:
            return None  # processed by base class
        return data

    def end(self, tag):
        if tag == 'GUEST-PROFILE':
            self._in_guest_profile = False
            if self._return_value_as_key:
                elem = getattr(self, self._key_elem_name)
                if self._key_elem_index > 1:
                    elem += '_' + str(self._key_elem_index)
                self.ret_elem_values[elem] = getattr(self, self._ret_elem_names[0][1:])
            else:
                elem_names = self._ret_elem_names
                if len(elem_names) == 1:
                    self.ret_elem_values.append(getattr(self, elem_names[0]))
                else:
                    values = dict()
                    for elem in elem_names:
                        field = self._elem_fld_map_parser.elem_fld_map[elem]
                        values[elem] = getattr(self, elem, field.val(system=SDI_SW, direction=FAD_FROM))
                        # Q&D fix for search_agencies(): prevent to add elemListVal elem/item in next run
                        # if 'elemVal' in field:
                        #     field.pop('elemVal')
                    self.ret_elem_values.append(values)
        # for completeness call also SihotXmlParser.end() and FldMapXmlParser.end()
        return super(GuestSearchResponse, self).end(self._elem_fld_map_parser.end(tag))


class FldMapXmlParser(SihotXmlParser):
    def __init__(self, cae, elem_map):
        super(FldMapXmlParser, self).__init__(cae)
        self._current_field = None
        self._current_data = None
        self._rec = Record(current_system=SDI_SH, current_direction=FAD_FROM)
        self._parent_recs = list()

        # create field data parsing record and mapping dict for all elements having a field value
        self.elem_fld_map = dict()
        for fas in elem_map:
            mi = len(fas) - 1
            if mi <= MTI_FIELD_NAME:
                continue
            field_name = fas[MTI_FIELD_NAME]
            if not field_name:
                continue

            elem_name = fas[MTI_ELEM_NAME]
            if elem_name.endswith('/'):
                elem_name = elem_name[:-1]
            aspects = dict()
            aspects[FAT_REC] = self._rec
            aspects[FAT_NAME] = field_name
            field = Field(**aspects)
            field.add_name(elem_name, SDI_SH, FAD_FROM)
            if mi > MTI_HIDE_IF and fas[MTI_HIDE_IF]:
                field.add_filter(fas[MTI_HIDE_IF], SDI_SH, FAD_FROM)
            if mi > MTI_FIELD_TYPE and fas[MTI_FIELD_TYPE]:
                field.set_value_type(fas[MTI_FIELD_TYPE], SDI_SH, FAD_FROM)
            if mi > MTI_FIELD_VAL and fas[MTI_FIELD_VAL] is not None:
                val_or_cal = fas[MTI_FIELD_VAL]
                if callable(val_or_cal):
                    field.add_calculator(val_or_cal, SDI_SH, FAD_FROM)
                else:
                    field.set_value(val_or_cal, SDI_SH, FAD_FROM)
            if mi > MTI_FIELD_CON and fas[MTI_FIELD_CON]:
                field.add_converter(fas[MTI_FIELD_CON], SDI_SH, FAD_FROM)

            self.elem_fld_map[elem_name] = field

    def clear_rec(self):
        for field in self._rec.fields.values():
            field.del_value(system=self._rec.current_system, direction=self._rec.current_direction)

    def find_field(self, tag):
        field = None
        if tag in self.elem_fld_map:
            field = self.elem_fld_map[tag]
        else:
            full_path = ELEM_PATH_SEP.join(self._elem_path)
            for elem_path_suffix, field in self.elem_fld_map:
                if full_path.endswith(elem_path_suffix):
                    break
        return field

    @property
    def rec(self):
        return self._rec

    # XMLParser interface

    def start(self, tag, attrib):
        super(FldMapXmlParser, self).start(tag, attrib)
        field = self.find_field(tag)
        if not field:
            self._current_field = None
            return tag
        if field.value_type(SDI_SH, FAD_FROM) == Records:
            field.set_value(Records(), SDI_SH, FAD_FROM)
            rec = Record(current_system=SDI_SH, current_direction=FAD_FROM)
            field.value(SDI_SH, FAD_FROM).append(rec)
            self._parent_recs.append(self._rec)
            self._rec = rec
            self._current_field = None
            return tag
        self._current_field = self.elem_fld_map[tag] = Field(**field.aspects).set_rec(self._rec)
        self._current_data = ''
        return None

    def data(self, data):
        super(FldMapXmlParser, self).data(data)
        if self._current_field:
            self._current_data += data
            return None
        return data

    def end(self, tag):
        super(FldMapXmlParser, self).end(tag)
        if self._current_field:
            self._current_field.set_value(self._current_data, SDI_SH, FAD_FROM)
            self._current_field = None
        else:
            field = self.find_field(tag)
            if field and field.value_type(SDI_SH, FAD_FROM) == Records:
                self._rec = self._parent_recs.pop()


class GuestFromSihot(FldMapXmlParser):
    def __init__(self, cae, elem_map=MAP_CLIENT_DEF):
        super(GuestFromSihot, self).__init__(cae, elem_map)
        self.guest_list = list()

    # XMLParser interface

    def end(self, tag):
        super(GuestFromSihot, self).end(tag)
        if tag == 'GUEST':  # using tag because self._curr_tag got reset by super method of end()
            self.guest_list.append(deepcopy(self._rec))
            self.clear_rec()


class ResFromSihot(FldMapXmlParser):
    def __init__(self, cae, elem_map=MAP_RES_DEF):
        super(ResFromSihot, self).__init__(cae, elem_map)
        self.res_list = list()

    # XMLParser interface

    def end(self, tag):
        super(ResFromSihot, self).end(tag)
        if tag == 'RESERVATION':  # using tag because self._curr_tag got reset by super method of end()
            self.res_list.append(deepcopy(self._rec))
            self.clear_rec()


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

    def __init__(self, cae, elem_map=None, use_kernel=None):
        super(SihotXmlBuilder, self).__init__(cae)
        self.cae = cae
        self.debug_level = cae.get_option('debugLevel')
        elem_map = deepcopy(elem_map or cae.get_option('mapRes'))
        values = ((fld_args[0], elem_name, ) + fld_args[1:] for elem_name, *fld_args in elem_map
                  if len(fld_args) and fld_args[0])
        fields = zip((FAT_NAME, FAT_VAL, FAT_FLT, ), values)
        self.elem_fld_rec = Record(fields=fields, current_system=SDI_SH, current_direction=FAD_ONTO)
        self.use_kernel_interface = cae.get_option('useKernelForRes') if use_kernel is None else use_kernel

        '''
        self.sihot_elem_fld = [(c[MTI_ELEM_NAME],
                                c[MTI_FIELD_NAME] if len(c) > MTI_FIELD_NAME else None,
                                c[MTI_FIELD_VAL] if len(c) > MTI_FIELD_VAL else None,
                                c[MTI_HIDE_IF] if len(c) > MTI_HIDE_IF else None,
                                )
                               for c in elem_map]
        self.fix_fld_values = dict()
        self.acu_fld_names = list()  # acu_fld_names and acu_fld_expres need to be in sync
        self.acu_fld_expres = list()
        self.fld_elem = dict()
        self.elem_fld = dict()
        for c in elem_map:
            if len(c) > MTI_FIELD_NAME and c[MTI_FIELD_NAME]:
                if len(c) > MTI_FIELD_VAL:
                    self.fix_fld_values[c[MTI_FIELD_NAME]] = c[MTI_FIELD_VAL]
                elif c[MTI_FIELD_NAME] not in self.acu_fld_names:
                    self.acu_fld_names.append(c[MTI_FIELD_NAME])
                    self.acu_fld_expres.append(c['fldValFromAcu'] + " as " + c[MTI_FIELD_NAME] if 'fldValFromAcu' in c
                                               else c[MTI_FIELD_NAME])
                # mapping dicts between db col names and xml elem names (not works for dup elems like MATCHCODE in RES)
                self.fld_elem[c[MTI_FIELD_NAME]] = c[MTI_ELEM_NAME]
                self.elem_fld[c[MTI_ELEM_NAME]] = c[MTI_FIELD_NAME]
        '''
        self.response = None

        self._recs = list()  # list of dicts, used by inheriting class for to store the records to send to SiHOT.PMS
        self._current_row_i = 0

        self._xml = ''
        self._indent = 0

    # --- rows/cols helpers

    @property
    def fields(self):
        return self._recs[self._current_row_i] if len(self._recs) > self._current_row_i else dict()

    # def next_row(self): self._current_row_i += 1

    @property
    def rec_count(self):
        return len(self._recs)

    @property
    def recs(self):
        return self._recs

    def beg_xml(self, operation_code, add_inner_xml='', transaction_number=''):
        self._xml = '<?xml version="1.0" encoding="' + self.cae.get_option('shXmlEncoding').lower() + \
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

    def prepare_map_xml(self, fld_values, action='', include_empty_values=True):
        inner_xml = ''
        filtered_rec = Record(current_action=action)
        self.elem_fld_rec.copy(to_rec=filtered_rec, filter_fields=True)
        for fld, field in filtered_rec.fields().items():
            tag = field.aspect_value(FAT_NAME, SDI_SH)
            val = field.val(SDI_SH)
            if tag.endswith('/'):
                self._indent += 1
                inner_xml += '\n' + ' ' * self._indent + self.new_tag(tag[:-1], closing=False)
            elif tag.startswith('/'):
                self._indent -= 1
                inner_xml += self.new_tag(tag[1:], opening=False)
            elif include_empty_values or (fld and fld in fld_values) or val:
                inner_xml += self.new_tag(tag, self.convert_value_to_xml_string(fld_values[fld]
                                                                                if fld and fld in fld_values else val))
        return inner_xml

    def send_to_server(self, response_parser=None):
        sc = TcpClient(self.cae.get_option('shServerIP'),
                       self.cae.get_option('shServerKernelPort' if self.use_kernel_interface else 'shServerPort'),
                       timeout=self.cae.get_option('shTimeout'),
                       encoding=self.cae.get_option('shXmlEncoding'),
                       debug_level=self.debug_level)
        self.cae.dprint("SihotXmlBuilder.send_to_server(): responseParser={}, xml={}".format(response_parser, self.xml),
                        minimum_debug_level=DEBUG_LEVEL_VERBOSE)
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
            uprint("****  SihotXmlBuilder.send_to_server() error: ", err_msg)
        return err_msg

    @staticmethod
    def new_tag(tag, val='', opening=True, closing=True):
        return ('<' + tag + '>' if opening else '') \
               + (val or '') \
               + ('</' + tag + '>' if closing else '')

    @staticmethod
    def convert_value_to_xml_string(value):
        # ret = str(val) if val else ''  # not working with zero value
        ret = '' if value is None else str(value)  # convert None to empty string
        if type(value) is datetime.datetime and ret.endswith(' 00:00:00'):
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


class ClientToSihot(SihotXmlBuilder):
    def __init__(self, cae):
        super(ClientToSihot, self).__init__(cae)

    def _prepare_guest_xml(self, c_row, action=None, fld_name_suffix=''):
        if not action:
            action = ACTION_UPDATE if c_row['ShId' + fld_name_suffix] else ACTION_INSERT
        self.beg_xml(operation_code='GUEST-CHANGE' if action == ACTION_UPDATE else 'GUEST-CREATE')
        self.add_tag('GUEST-PROFILE' if self.use_kernel_interface else 'GUEST',
                     self.prepare_map_xml(c_row, action))
        self.end_xml()
        self.cae.dprint("ClientToSihot._prepare_guest_xml() fld_values/action/result: ",
                        c_row, action, self.xml, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        return action

    def _prepare_guest_link_xml(self, mc1, mc2, action):
        mct1 = self.new_tag('MATCHCODE-GUEST', self.convert_value_to_xml_string(mc1))
        mct2 = self.new_tag('CONTACT',
                            self.new_tag('MATCHCODE', self.convert_value_to_xml_string(mc2)) +
                            self.new_tag('FLAG', 'DELETE' if action == ACTION_DELETE else ''))
        self.beg_xml(operation_code='GUEST-CONTACT')
        self.add_tag('CONTACTLIST', mct1 + mct2)
        self.end_xml()
        self.cae.dprint("ClientToSihot._prepare_guest_link_xml() mc1/mc2/result: ", mc1, mc2, self.xml,
                        minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    def _send_link_to_sihot(self, pk1, pk2, delete=False):
        self._prepare_guest_link_xml(pk1, pk2, delete)
        return self.send_to_server()

    def _send_person_to_sihot(self, c_row, first_person=""):  # pass AcId of first person for to send 2nd person
        action = self._prepare_guest_xml(c_row, fld_name_suffix='2' if first_person else '')
        err_msg = self.send_to_server()
        if 'guest exists already' in err_msg and action == ACTION_INSERT:  # and not self.use_kernel_interface:
            action = ACTION_UPDATE
            self._prepare_guest_xml(c_row, action=action, fld_name_suffix='2' if first_person else '')
            err_msg = self.send_to_server()
        return err_msg, action

    def send_client_to_sihot(self, c_row=None, commit=False):
        if not c_row:
            c_row = self.fields
        err_msg, action = self._send_person_to_sihot(c_row)
        if err_msg:
            self.cae.dprint("ClientToSihot.send_client_to_sihot() row|action|err: ", c_row, action, err_msg)
        else:
            self.cae.dprint("ClientToSihot.send_client_to_sihot() client={} RESPONDED OBJID={}/MATCHCODE={}"
                            .format(c_row['AcId'], self.response.objid, self.response.matchcode),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg, action


class ConfigDict(SihotXmlBuilder):
    def get_key_values(self, config_type, hotel_id='1', language='EN'):
        self.beg_xml(operation_code='GCF')
        self.add_tag('CFTYPE', config_type)
        self.add_tag('HN', hotel_id)  # mandatory
        self.add_tag('LN', language)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ConfigDictResponse(self.cae))

        return err_msg or self.response.key_values


class GuestSearch(SihotXmlBuilder):
    def __init__(self, ca):
        super(GuestSearch, self).__init__(ca, elem_map=MAP_KERNEL_CLIENT, use_kernel=True)

    def get_guest(self, obj_id):
        """ return dict with guest data OR str with error message in case of error.
        """
        self.beg_xml(operation_code='GUEST-GET')
        self.add_tag('GUEST-PROFILE',
                     self.prepare_map_xml({'ShId': obj_id}, action=ACTION_SEARCH, include_empty_values=False))
        self.end_xml()

        rp = GuestSearchResponse(self.cae)
        err_msg = self.send_to_server(response_parser=rp)
        if not err_msg and self.response:
            ret = self.response.ret_elem_values[0]
            self.cae.dprint("GuestSearch.guest_get() obj_id|xml|result: ", obj_id, self.xml, ret,
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        else:
            ret = "GuestSearch.guest_get() obj_id={}; err='{}'".format(obj_id, err_msg)
        return ret

    def get_guest_nos_by_matchcode(self, matchcode, exact_matchcode=True):
        fld_values = {'AcId': matchcode,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS' + (';MATCH-EXACT-MATCHCODE' if exact_matchcode else ''),
                      }
        return self.search_guests(fld_values, ['guest_nr'])

    def get_objid_by_guest_no(self, guest_no):
        fld_values = {'SH_GUEST_NO': guest_no,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        ret = self.search_guests(fld_values, ['objid'])
        return ret[0] if len(ret) > 0 else None

    def get_objids_by_guest_name(self, name):
        forename, surname = name.split(' ', maxsplit=1)
        fld_values = {'Surname': surname,
                      'Forename': forename,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(fld_values, ['objid'])

    def get_objids_by_guest_names(self, surname, forename):
        fld_values = {'Surname': surname,
                      'Forename': forename,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(fld_values, ['objid'])

    def get_objids_by_email(self, email):
        fld_values = {'Email': email,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(fld_values, ['objid'])

    def get_objids_by_matchcode(self, matchcode, exact_matchcode=True):
        fld_values = {'AcId': matchcode,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS' + (';MATCH-EXACT-MATCHCODE' if exact_matchcode else ''),
                      }
        return self.search_guests(fld_values, ['objid'])

    def get_objid_by_matchcode(self, matchcode, exact_matchcode=True):
        fld_values = {'AcId': matchcode,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS' + (';MATCH-EXACT-MATCHCODE' if exact_matchcode else ''),
                      }
        ret = self.search_guests(fld_values, [':objid'], key_elem_name='matchcode')
        if ret:
            return self._check_and_get_objid_of_matchcode_search(ret, matchcode, exact_matchcode)

    def search_agencies(self):
        fld_values = {'GuestType': 7,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(fld_values, ['OBJID', 'MATCHCODE'])

    def search_guests(self, fld_values, ret_elem_names, key_elem_name=None):
        """ return dict with search element/attribute value as the dict key if len(ret_elem_names)==1 and if
            ret_elem_names[0][0]==':' (in this case key_elem_name has to provide the search element/attribute name)
            OR return list of values if len(ret_elem_names) == 1
            OR return list of dict with ret_elem_names keys if len(ret_elem_names) >= 2
            OR return None in case of error.
        """
        self.beg_xml(operation_code='GUEST-SEARCH')
        self.add_tag('GUEST-SEARCH-REQUEST',
                     self.prepare_map_xml(fld_values, action=ACTION_SEARCH, include_empty_values=False))
        self.end_xml()

        rp = GuestSearchResponse(self.cae, ret_elem_names, key_elem_name=key_elem_name)
        err_msg = self.send_to_server(response_parser=rp)
        if not err_msg and self.response:
            ret = self.response.ret_elem_values
            self.cae.dprint("GuestSearch.search_guests() fld_values|xml|result: ", fld_values, self.xml, ret,
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        else:
            uprint("GuestSearch.search_guests() fld_values|error: ", fld_values, err_msg)
            ret = None
        return ret

    @staticmethod
    def _check_and_get_objid_of_matchcode_search(ret_elem_values, key_elem_value, exact_matchcode):
        s = '\n   ...'
        if key_elem_value in ret_elem_values:
            ret = ret_elem_values[key_elem_value]
        else:
            ret = s + "OBJID of matchcode {} not found!!!".format(key_elem_value)
        if len(ret_elem_values) > 1 and not exact_matchcode:
            ret += s + "Found more than one guest - full Response (all returned values):" + s + str(ret_elem_values)
        return ret


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


class ResFetch(SihotXmlBuilder):
    def fetch_res(self, ho_id, gds_no=None, res_id=None, sub_id=None, scope='USEISODATE'):
        self.beg_xml(operation_code='SS')
        self.add_tag('ID', ho_id)
        if gds_no:
            self.add_tag('GDSNO', gds_no)
        else:
            self.add_tag('RES-NR', res_id)
            self.add_tag('SUB-NR', sub_id)
        if scope:
            # e.g. BASICDATAONLY only sends RESERVATION xml block (see 14.3.4 in WEB interface doc)
            self.add_tag('SCOPE', scope)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ResFromSihot(self.cae))
        # WEB interface return codes (RC): 29==res not found, 1==internal error - see 14.3.5 in WEB interface doc

        return err_msg or self.response.res_list[0]

    def fetch_by_gds_no(self, ho_id, gds_no, scope='USEISODATE'):
        return self.fetch_res(ho_id, gds_no=gds_no, scope=scope)

    def fetch_by_res_id(self, ho_id, res_id, sub_id, scope='USEISODATE'):
        return self.fetch_res(ho_id, res_id=res_id, sub_id=sub_id, scope=scope)


class ResKernelGet(SihotXmlBuilder):
    def __init__(self, cae):
        super(ResKernelGet, self).__init__(cae, use_kernel=True)

    def fetch_res_no(self, obj_id, scope='GET'):
        """
        return dict with guest data OR None in case of error

        :param obj_id:  Sihot reservation object id.
        :param scope:   search scope string (see 7.3.1.2 in Sihot KERNEL interface doc V 9.0)
        """
        self.beg_xml(operation_code='RESERVATION-GET')
        self.add_tag('RESERVATION-PROFILE', self.new_tag('OBJID', obj_id) + self.new_tag('SCOPE', scope))
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ResKernelResponse(self.cae))
        if not err_msg and self.response:
            res_no = (self.response.hn, self.response.res_nr, self.response.sub_nr)
            self.cae.dprint("ResKernelGet.fetch() obj_id|xml|res_no: ", obj_id, self.xml, res_no,
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        else:
            res_no = None
            uprint("ResKernelGet.fetch() obj_id|error: ", obj_id, err_msg)
        return res_no


class ResSearch(SihotXmlBuilder):
    def search(self, hotel_id=None, from_date=datetime.date.today(), to_date=datetime.date.today(),
               matchcode=None, name=None, gdsno=None, flags='', scope=None, guest_id=None):
        self.beg_xml(operation_code='RES-SEARCH')
        if hotel_id:
            self.add_tag('ID', hotel_id)
        elif 'ALL-HOTELS' not in flags:
            flags += (';' if flags else '') + 'ALL-HOTELS'
        self.add_tag('FROM', datetime.date.strftime(from_date, '%Y-%m-%d'))  # mandatory?
        self.add_tag('TO', datetime.date.strftime(to_date, '%Y-%m-%d'))
        if matchcode:
            self.add_tag('MATCHCODE', matchcode)
        if name:
            self.add_tag('NAME', name)
        if gdsno:
            self.add_tag('GDSNO', gdsno)
        if flags:
            self.add_tag('FLAGS', flags if flags[0] != ';' else flags[1:])
        if scope:
            self.add_tag('SCOPE', scope)  # e.g. EXPORTEXTENDEDCOMMENT;FORCECALCDAYPRICE;CALCSUMDAYPRICE
        if guest_id:
            # TODO: ask Gubse to fix guest_id search/filter option on RES-SEARCH operation of Sihot WEB interface.
            self.add_tag('CENTRAL-GUEST-ID', guest_id)  # this is not filtering nothing (tried GID)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ResFromSihot(self.cae))

        """
        20.5 Return Codes (RC):

            0  == The search was successful. If no reservation with the given search criteria was found,
                  the <MSG> element returns the respective information.
            1  == The data inside the element <RT> is not a valid reservation type.
            2  == There is no guest with this central guest ID available.
            3  == There is no guest with this matchcode available.
            4  == The given search data is not valid
            5  == An (internal) error occurred when searching for reservations.
        """
        return err_msg or self.response.res_list

    def elem_path_values(self, elem_path_suffix):
        """
        return list of parsed data values where the element path is ending with the passed element path suffix.
        Has to be called after self.search().
        :param      elem_path_suffix:    element path suffix.
        :return:    list of parsed data values.
        """
        return elem_path_values(self.response.res_list, elem_path_suffix)


class ResToSihot(SihotXmlBuilder):
    def __init__(self, cae):
        super(ResToSihot, self).__init__(cae)
        self.use_kernel_for_new_clients = cae.get_option('useKernelForClient')
        self.map_client = cae.get_option('mapClient')

        self._warning_frags = self.cae.get_config('warningFragments') or list()  # list of warning text fragments
        self._warning_msgs = ""
        self._gds_err_rows = dict()

    def _add_sihot_configs(self, crow):
        mkt_seg = crow.get('ResMktSegment', '')
        hotel_id = str(crow.get('ResHotelId', 999))
        arr_date = crow.get('arr_date')
        today = datetime.datetime.today()
        cf = self.cae.get_config

        if arr_date and arr_date > today:            # Sihot doesn't accept allotment for reservations in the past
            val = cf(mkt_seg + '_' + hotel_id, section='SihotAllotments',
                     default_value=cf(mkt_seg, section='SihotAllotments'))
            if val:
                crow['ResAllotmentNo'] = val

        if not crow.get('ResRateSegment'):  # not specified? FYI: this field is not included in V_ACU_RES_DATA
            val = cf(mkt_seg, section='SihotRateSegments', default_value=crow['ResMktSegment'])
            if val:
                crow['ResRateSegment'] = val

        val = cf(mkt_seg, section='SihotPaymentInstructions')
        if val:
            crow['ResAccount'] = val

        if crow.get('ResAction', '') != 'DELETE' and crow.get('RU_STATUS', 0) != 120 and arr_date and arr_date > today:
            val = cf(mkt_seg, section='SihotResTypes')
            if val:
                crow['ResStatus'] = val

    def _prepare_res_xml(self, crow):
        self._add_sihot_configs(crow)
        action = crow['ResAction']
        inner_xml = self.prepare_map_xml(crow, action)
        if self.use_kernel_interface:
            if action == ACTION_INSERT:
                self.beg_xml(operation_code='RESERVATION-CREATE')
            else:
                self.beg_xml(operation_code='RESERVATION-DATA-CHANGE')
            self.add_tag('RESERVATION-PROFILE', inner_xml)
        else:
            self.beg_xml(operation_code='RES', add_inner_xml=inner_xml)
        self.end_xml()
        self.cae.dprint("ResToSihot._prepare_res_xml() result: ", self.xml,
                        minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    def _send_res_to_sihot(self, crow):
        self._prepare_res_xml(crow)

        err_msg, warn_msg = self._handle_error(crow, self.send_to_server(response_parser=ResResponse(self.cae)))
        return err_msg, warn_msg

    def _handle_error(self, crow, err_msg):
        warn_msg = ""
        if [frag for frag in self._warning_frags if frag in err_msg]:
            warn_msg = self.res_id_desc(crow, err_msg, separator="\n")
            self._warning_msgs += "\n\n" + warn_msg
            err_msg = ""
        elif err_msg:
            assert crow['ResGdsNo']
            assert crow['ResGdsNo'] not in self._gds_err_rows
            self._gds_err_rows[crow['ResGdsNo']] = (crow, err_msg)
        return err_msg, warn_msg

    def _ensure_clients_exist_and_updated(self, crow, ensure_client_mode):
        if ensure_client_mode == ECM_DO_NOT_SEND_CLIENT:
            return ""
        err_msg = ""
        if 'AcId' in crow and crow['AcId']:
            client = ClientToSihot(self.cae)
            err_msg = client.send_client_to_sihot(crow)
            if not err_msg:
                # get client/occupant objid directly from client.response
                crow['ShId'] = client.response.objid

        if not err_msg and crow.get('ResOrdererMc') and len(crow['ResOrdererMc']) == 7:  # exclude OTAs like TCAG/TCRENT
            client = ClientToSihot(self.cae)
            err_msg = client.send_client_to_sihot(crow)
            if not err_msg:
                # get orderer objid directly from client.response
                crow['ResOrdererId'] = client.response.objid

        return "" if ensure_client_mode == ECM_TRY_AND_IGNORE_ERRORS else err_msg

    def send_row_to_sihot(self, crow=None, ensure_client_mode=ECM_ENSURE_WITH_ERRORS):
        if not crow:
            crow = self.fields
        gds_no = crow.get('ResGdsNo', '')
        if gds_no:
            if gds_no in self._gds_err_rows:    # prevent send of follow-up changes on erroneous bookings (w/ same GDS)
                old_id = self.res_id_desc(*self._gds_err_rows[gds_no], separator="\n")
                warn_msg = "\n\n" + "Synchronization skipped because GDS number {} had errors in previous send: {}" \
                           + "\nSkipped reservation: {}"
                self._warning_msgs += warn_msg.format(gds_no, old_id, self.res_id_desc(crow, "", separator="\n"))
                return self._gds_err_rows[gds_no][1]    # return same error message

            err_msg = self._ensure_clients_exist_and_updated(crow, ensure_client_mode)
            if not err_msg:
                err_msg, warn_msg = self._send_res_to_sihot(crow)
        else:
            err_msg = self.res_id_desc(crow, "ResToSihot.send_row_to_sihot(): sync with empty GDS number skipped")

        if err_msg:
            self.cae.dprint("ResToSihot.send_row_to_sihot() error: {}".format(err_msg))
        else:
            self.cae.dprint("ResToSihot.send_row_to_sihot() GDSNO={} RESPONDED OBJID={} MATCHCODE={}"
                            .format(gds_no, self.response.objid, self.response.matchcode),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg

    def send_rows_to_sihot(self, break_on_error=True):
        ret_msg = ""
        for row in self.recs:
            err_msg = self.send_row_to_sihot(row)
            if err_msg:
                if break_on_error:
                    return err_msg  # BREAK/RETURN first error message
                ret_msg += "\n" + err_msg
        return ret_msg

    def res_id_label(self):
        return "GDS/VOUCHER/CD/RO" + ("/RU/RUL" if self.debug_level else "")

    def res_id_values(self, crow):
        return str(crow.get('SIHOT_GDSNO')) + \
               "/" + str(crow.get('RH_EXT_BOOK_REF')) + \
               "/" + str(crow.get('CD_CODE')) + "/" + str(crow.get('RUL_SIHOT_RATE')) + \
               ("/" + str(crow.get('RUL_PRIMARY')) + "/" + str(crow.get('RUL_CODE'))
                if self.debug_level and 'RUL_PRIMARY' in crow and 'RUL_CODE' in crow
                else "")

    def res_id_desc(self, crow, error_msg, separator="\n\n"):
        indent = 8
        return crow.get('ResAction', '') + " RESERVATION: " \
            + (crow['ResArrival'].strftime('%d-%m') if crow.get('ResArrival') else "unknown") + ".." \
            + (crow['ResDeparture'].strftime('%d-%m-%y') if crow.get('ResDeparture') else "unknown") \
            + " in " + (crow['ResRoomNo'] + "=" if crow.get('ResRoomNo') else "") \
            + str(crow.get('ResRoomCat')) \
            + ("!" + crow.get('ResPriceCat', '')
               if crow.get('ResPriceCat') and crow.get('ResPriceCat') != crow.get('ResRoomCat') else "") \
            + " at hotel " + str(crow.get('ResHotelId')) \
            + separator + " " * indent + self.res_id_label() + "==" + self.res_id_values(crow) \
            + (separator + "\n".join(wrap("ERROR: " + _strip_error_message(error_msg), subsequent_indent=" " * indent))
               if error_msg else "") \
            + (separator + "\n".join(wrap("TRAIL: " + crow.get('RUL_CHANGES', ''), subsequent_indent=" " * indent))
               if 'RUL_CHANGES' in crow and crow.get('RUL_CHANGES') else "")

    def get_warnings(self):
        return self._warning_msgs + "\n\nEnd_Of_Message\n" if self._warning_msgs else ""

    def wipe_warnings(self):
        self._warning_msgs = ""

    def wipe_gds_errors(self):
        self._gds_err_rows = dict()
