# SiHOT xml interface
import datetime
from copy import deepcopy
from textwrap import wrap

# import xml.etree.ElementTree as Et
from xml.etree.ElementTree import XMLParser, ParseError

# fix_encoding() needed for to clean and re-parse XML on invalid char code exception/error
from ae_console_app import fix_encoding, uprint, round_traditional, DEBUG_LEVEL_VERBOSE, DEBUG_LEVEL_TIMESTAMPED
from ae_tcp import TcpClient

# data actions
ACTION_DELETE = 'DELETE'
ACTION_INSERT = 'INSERT'
ACTION_UPDATE = 'UPDATE'
ACTION_SEARCH = 'SEARCH'

# maximum number of external references per client
EXT_REF_COUNT = 10

# maximum number of named adults and children per reservation is currently restricted
RES_MAX_ADULTS = 6
RES_MAX_CHILDREN = 4


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

# ensure client modes (used by AcuResToSihot.send_row_to_sihot())
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
    :param elem_fld_map:        element field map dict in the form {elem_name: map entry} where each map_entry is also
                                a dict that got extended with other entries e.g. elemVal/elemListVal/elemPathValues/...
    :param elem_path_suffix:    element path (either full path or suffix, e.g. SIHOT-Document.ARESLIST.RESERVATION.ARR)
    :return:                    merged list of all parsed data in fld map with passed element path suffix
    """
    ret_list = list()
    for elem_map in elem_fld_map.values():
        if 'elemPathValues' in elem_map:
            for path_key, path_list in elem_map['elemPathValues'].items():
                if path_key.endswith(elem_path_suffix):
                    ret_list.extend(path_list)
    return ret_list


#  ELEMENT-FIELD-MAPS  #################################

# default map for GuestFromSihot.elem_fld_map instance and as read-only constant by AcuClientToSihot using the SIHOT
# .. KERNEL interface because SiHOT WEB V9 has missing fields: initials (CD_INIT1/2) and profession (CD_INDUSTRY1/2)
MAP_KERNEL_CLIENT = \
    (
        {'elemName': 'OBJID', 'fldName': 'ShId', 'elemHideInActions': ACTION_INSERT},
        {'elemName': 'MATCHCODE', 'fldName': 'AcId'},
        {'elemName': 'GUEST-NR', 'fldName': 'SH_GUEST_NO',  # only needed for GUEST-SEARCH/get_objid_by_guest_no()
         'elemHideIf': "'SH_GUEST_NO' not in c or not c['SH_GUEST_NO']"},
        {'elemName': 'FLAGS', 'fldName': 'SH_FLAGS',        # only needed for GUEST-SEARCH/get_objid_by_guest_no()
         'elemHideIf': "'SH_FLAGS' not in c or not c['SH_FLAGS']"},
        {'elemName': 'T-SALUTATION', 'fldName': 'Salutation'},  # also exists T-ADDRESS/T-PERSONAL-SALUTATION
        {'elemName': 'T-TITLE', 'fldName': 'Title'},
        {'elemName': 'T-GUEST', 'fldName': 'GuestType'},
        {'elemName': 'NAME-1', 'fldName': 'Surname'},
        {'elemName': 'NAME-2', 'fldName': 'Forename'},
        {'elemName': 'STREET', 'fldName': 'Street'},
        {'elemName': 'PO-BOX', 'fldName': 'POBox'},
        {'elemName': 'ZIP', 'fldName': 'Postal'},
        {'elemName': 'CITY', 'fldName': 'City'},
        {'elemName': 'T-COUNTRY-CODE', 'fldName': 'Country'},
        {'elemName': 'T-STATE', 'fldName': 'State',
         'elemHideIf': "'State' not in c or not c['State']"},
        {'elemName': 'T-LANGUAGE', 'fldName': 'Language'},
        {'elemName': 'COMMENT', 'fldName': 'Comment'},
        {'elemName': 'COMMUNICATION/',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'PHONE-1', 'fldName': 'HomePhone'},
        {'elemName': 'PHONE-2', 'fldName': 'WorkPhone'},
        {'elemName': 'FAX-1', 'fldName': 'Fax'},
        {'elemName': 'EMAIL-1', 'fldName': 'Email'},
        {'elemName': 'EMAIL-2', 'fldName': 'Email2'},
        {'elemName': 'MOBIL-1', 'fldName': 'MobilePhone'},
        {'elemName': 'MOBIL-2', 'fldName': 'MobilePhone2'},
        {'elemName': '/COMMUNICATION',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'ADD-DATA/',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'T-PERSON-GROUP', 'fldVal': "1A"},
        {'elemName': 'D-BIRTHDAY', 'fldName': 'DOB',
         'valToAcuConverter': convert2date},
        # 27-09-17: removed b4 migration of BHH/HMC because CD_INDUSTRY1/2 needs first grouping into 3-alphanumeric code
        # {'elemName': 'T-PROFESSION', 'fldName': 'CD_INDUSTRY1', 'buildExclude': True},
        {'elemName': 'INTERNET-PASSWORD', 'fldName': 'Password'},
        {'elemName': 'MATCH-ADM', 'fldName': 'RCIRef'},
        {'elemName': 'MATCH-SM', 'fldName': 'SfId'},
        {'elemName': '/ADD-DATA',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'L-EXTIDS/',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'EXTID/', 
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs']"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType1',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs']"},
        {'elemName': 'ID', 'fldName': 'ExtRefId1',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs']"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs']"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 1"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType2',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 1"},
        {'elemName': 'ID', 'fldName': 'ExtRefId2',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 1"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 1"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 2"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType3',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 2"},
        {'elemName': 'ID', 'fldName': 'ExtRefId3',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 2"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 2"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 3"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType4',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 3"},
        {'elemName': 'ID', 'fldName': 'ExtRefId4',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 3"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 3"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 4"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType5',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 4"},
        {'elemName': 'ID', 'fldName': 'ExtRefId5',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 4"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 4"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 5"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType6',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 5"},
        {'elemName': 'ID', 'fldName': 'ExtRefId6',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 5"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 5"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 6"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType7',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 6"},
        {'elemName': 'ID', 'fldName': 'ExtRefId7',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 6"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 6"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 7"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType8',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 7"},
        {'elemName': 'ID', 'fldName': 'ExtRefId8',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 7"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 7"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 8"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType9',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 8"},
        {'elemName': 'ID', 'fldName': 'ExtRefId9',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 8"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 8"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 9"},
        {'elemName': 'TYPE', 'fldName': 'ExtRefType10',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 9"},
        {'elemName': 'ID', 'fldName': 'ExtRefId10',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 9"},
        {'elemName': '/EXTID',
         'elemHideIf': "'ExtRefs' not in c or not c['ExtRefs'] or c['ExtRefs'].count(',') < 9"},
        {'elemName': '/L-EXTIDS',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'EXT_REFS', 'fldName': 'ExtRefs', 'buildExclude': True},  # only for elemHideIf expressions
        {'elemName': 'CDLREF', 'fldName': 'CDL_CODE', 'buildExclude': True},
        # {'elemName': 'STATUS', 'fldName': 'CD_STATUS', 'fldValToAcu': 500, 'buildExclude': True},
        # {'elemName': 'PAF_STAT', 'fldName': 'CD_PAF_STATUS', 'fldValToAcu': 0, 'buildExclude': True},
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
        {'elemName': 'ID', 'fldName': 'ResHotelId'},  # or use [RES-]HOTEL/IDLIST/MANDATOR-NO/EXTERNAL-SYSTEM-ID
        {'elemName': 'ARESLIST/'},
        {'elemName': 'RESERVATION/'},
        # ### main reservation info: orderer, status, external booking references, room/price category, ...
        # MATCHCODE, NAME, COMPANY and GUEST-ID are mutually exclusive
        # MATCHCODE/GUEST-ID needed for DELETE action for to prevent Sihot error:
        # .. "Could not find a key identifier for the client (name, matchcode, ...)"
        {'elemName': 'GUEST-ID', 'fldName': 'ResOrdererId',
         'elemHideIf': "not c.get('ResOrdererId') and not c.get['ShId']"},
        {'elemName': 'MATCHCODE', 'fldName': 'ResOrdererMc'},
        {'elemName': 'GDSNO', 'fldName': 'ResGdsNo'},
        {'elemName': 'VOUCHERNUMBER', 'fldName': 'ResVoucherNo', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'EXT-KEY', 'fldName': 'ResGroupNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'ResGroupNo' not in c"},
        {'elemName': 'FLAGS', 'fldVal': 'IGNORE-OVERBOOKING'},  # ;NO-FALLBACK-TO-ERRONEOUS'},
        {'elemName': 'RT', 'fldName': 'ResStatus'},
        # ResRoomCat results in error 1011 for tk->TC/TK bookings with room move and room with higher/different room
        # .. cat, therefore use price category as room category for Thomas Cook Bookings.
        # .. similar problems we experienced when we added the RCI Allotments (here the CAT need to be the default cat)
        # .. on the 24-05-2018 so finally we replaced the category of the (maybe) allocated room with the cat that
        # .. get determined from the requested room size
        {'elemName': 'CAT', 'fldName': 'ResRoomCat'},  # needed for DELETE action
        {'elemName': 'PCAT', 'fldName': 'ResPriceCat', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'ALLOTMENT-EXT-NO', 'fldName': 'ResAllotmentNo', 'fldVal': '',
         # 'elemHideInActions': ACTION_DELETE, removed while renaming ALLOTMENT-NO to ALLOTMENT-EXT-NO
         'elemHideIf': "'ResAllotmentNo' not in c"},
        {'elemName': 'PAYMENT-INST', 'fldName': 'ResAccount', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'ResAccount' not in c"},
        {'elemName': 'SALES-DATE', 'fldName': 'ResBooked', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "not c['ResBooked']"},
        {'elemName': 'RATE-SEGMENT', 'fldName': 'ResRateSegment', 'fldVal': '',
         'elemHideIf': "'ResRateSegment' not in c"},    # e.g. TK/tk have defined rate segment in SIHOT - see cfg
        {'elemName': 'RATE/'},  # package/arrangement has also to be specified in PERSON:
        {'elemName': 'R', 'fldName': 'ResBoard'},
        {'elemName': 'ISDEFAULT', 'fldVal': 'Y'},
        {'elemName': '/RATE'},
        {'elemName': 'RATE/', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResMktSegment'] not in ('ER')"},
        {'elemName': 'R', 'fldVal': 'GSC', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResMktSegment'] not in ('ER')"},
        {'elemName': 'ISDEFAULT', 'fldVal': 'N', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResMktSegment'] not in ('ER')"},
        {'elemName': '/RATE', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResMktSegment'] not in ('ER')"},
        # The following fallback rate results in error Package TO not valid for hotel 1
        # {'elemName': 'RATE/'},
        # {'elemName': 'R', 'fldName': 'RO_SIHOT_RATE', 'fldValFromAcu': "nvl(RO_SIHOT_RATE, ResMktSegment)"},
        # {'elemName': 'ISDEFAULT', 'fldVal': 'N'},
        # {'elemName': '/RATE'},
        # ### Reservation Channels - used for assignment of reservation to a allotment or to board payment
        {'elemName': 'RESCHANNELLIST/',
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'][:4] not in ('Owne', 'Prom', 'RCI ')"},
        {'elemName': 'RESCHANNEL/',
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'][:4] not in ('Owne', 'Prom', 'RCI ')"},
        # needed for to add RCI booking to RCI allotment
        {'elemName': 'IDX', 'fldVal': 1,
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'][:4] not in ('RCI ')"},
        {'elemName': 'MATCHCODE', 'fldVal': 'RCI',
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'][:4] not in ('RCI ')"},
        {'elemName': 'ISPRICEOWNER', 'fldVal': 1,
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'][:4] not in ('RCI ')"},
        # needed for marketing fly buys for board payment bookings
        {'elemName': 'IDX', 'fldVal': 1,
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'] not in ('Promo')"},
        {'elemName': 'MATCHCODE', 'fldVal': 'MAR01',
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'] not in ('Promo')"},
        {'elemName': 'ISPRICEOWNER', 'fldVal': 1,
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'] not in ('Promo')"},
        # needed for owner bookings for to select/use owner allotment
        {'elemName': 'IDX', 'fldVal': 2,
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'] not in ('Owner')"},
        {'elemName': 'MATCHCODE', 'fldVal': 'TSP',
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'] not in ('Owner')"},
        {'elemName': 'ISPRICEOWNER', 'fldVal': 1,
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'] not in ('Owner')"},
        {'elemName': '/RESCHANNEL',
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'][:4] not in ('Owne', 'Prom', 'RCI ')"},
        {'elemName': '/RESCHANNELLIST',
         'elemHideIf': "'ResAllotmentNo' not in c or not c['ResAllotmentNo']"
                       " or c['ResMktGroup'][:4] not in ('Owne', 'Prom', 'RCI ')"},
        # ### GENERAL RESERVATION DATA: arrival/departure, pax, market sources, comments
        {'elemName': 'ARR', 'fldName': 'ResArrival'},
        {'elemName': 'DEP', 'fldName': 'ResDeparture'},
        {'elemName': 'NOROOMS', 'fldVal': 1},  # needed for DELETE action
        {'elemName': 'NOPAX', 'fldName': 'ResAdults'},  # needed for DELETE action
        {'elemName': 'NOCHILDS', 'fldName': 'ResChildren', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'TEC-COMMENT', 'fldName': 'ResLongNote', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'COMMENT', 'fldName': 'ResNote', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'MARKETCODE-NO', 'fldName': 'ResMktSegment', 'elemHideInActions': ACTION_DELETE},
        # {'elemName': 'MEDIA'},
        {'elemName': 'SOURCE', 'fldName': 'ResSource', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'NN', 'fldName': 'ResMktGroup2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'ResMktGroup2' not in c"},
        {'elemName': 'CHANNEL', 'fldName': 'ResMktGroup', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'ResMktGroup' not in c"},
        # {'elemName': 'NN2', 'fldName': 'RO_RES_CLASS'},  # other option using Mkt-CM_NAME (see Q_SIHOT_SETUP#L244)
        {'elemName': 'EXT-REFERENCE', 'fldName': 'ResFlightNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'ResFlightNo' not in c"},   # see also currently unused PICKUP-COMMENT-ARRIVAL element
        {'elemName': 'ARR-TIME', 'fldName': 'ResFlightETA', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'ResFlightETA' not in c"},
        {'elemName': 'PICKUP-TIME-ARRIVAL', 'fldName': 'ResFlightETA', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'ResFlightETA' not in c or not c['ResFlightETA']"},
        {'elemName': 'PICKUP-TYPE-ARRIVAL', 'fldVal': 1,  # 1=car, 2=van
         'elemHideIf': "'ResFlightETA' not in c or not c['ResFlightETA']"},
        # ### PERSON/occupant details
        {'elemName': 'PERS-TYPE-LIST/'},
        {'elemName': 'PERS-TYPE/'},
        {'elemName': 'TYPE', 'fldVal': '1A'},
        {'elemName': 'NO', 'fldName': 'ResAdults'},
        {'elemName': '/PERS-TYPE'},
        {'elemName': 'PERS-TYPE/'},
        {'elemName': 'TYPE', 'fldVal': '2B'},
        {'elemName': 'NO', 'fldName': 'ResChildren'},
        {'elemName': '/PERS-TYPE'},
        {'elemName': '/PERS-TYPE-LIST'},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # First person/adult of reservation
         'elemHideIf': "c['ResAdults'] <= 0"},
        {'elemName': 'NAME', 'fldName': 'ResAdult1Surname', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0 or 'ResAdult1Surname' not in c or not c['ResAdult1Surname']"},
        {'elemName': 'NAME2', 'fldName': 'ResAdult1Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0 or 'ResAdult1Forename' not in c or not c['ResAdult1Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0 or 'ResAdult1Surname' not in c or not c['ResAdult1Surname']"
                       " or c['ResAdult1Surname'][:5] == 'Adult'"},
        {'elemName': 'MATCHCODE', 'fldName': 'AcId', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0 or 'AcId' not in c or c['ShId']"},
        {'elemName': 'GUEST-ID', 'fldName': 'ShId', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0 or 'ShId' not in c or not c['ShId']"},
        {'elemName': 'ROOM-SEQ', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0"},
        {'elemName': 'PERS-TYPE', 'fldVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResAdult1DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0 or 'ResAdult1DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 0"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Second adult of client
         'elemHideIf': "c['ResAdults'] <= 1"},
        # NAME element needed for clients with only one person but reservation with 2nd pax (ResAdults >= 2):
        # {'elemName': 'NAME', 'fldName': 'ResAdult2Surname', 'fldVal': '',
        # 'elemHideIf': "c['ResAdults'] <= 1 or 'ResAdult2Surname' not in c or not c['ResAdult2Surname']"},
        {'elemName': 'NAME', 'fldName': 'ResAdult2Surname', 'fldVal': 'Adult 2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1 or ('AcId2' in c and c['AcId2'])"},
        {'elemName': 'NAME2', 'fldName': 'ResAdult2Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1 or 'ResAdult2Forename' not in c or not c['ResAdult2Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1 or ('AcId2' in c and c['AcId2'])"},
        {'elemName': 'MATCHCODE', 'fldName': 'AcId2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1 or 'AcId2' not in c or c['ShId2']"},
        {'elemName': 'GUEST-ID', 'fldName': 'ShId2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1 or 'ShId2' not in c or not c['ShId2']"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1"},
        {'elemName': 'PERS-TYPE', 'fldVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResAdult2DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1 or 'ResAdult2DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 1"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Adult 3
         'elemHideIf': "c['ResAdults'] <= 2"},
        {'elemName': 'NAME', 'fldName': 'ResAdult3Surname', 'fldVal': 'Adult 3', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2"},
        {'elemName': 'NAME2', 'fldName': 'ResAdult3Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2 or 'ResAdult3Forename' not in c or not c['ResAdult3Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2"},
        {'elemName': 'PERS-TYPE', 'fldVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResAdult3DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2 or 'ResAdult3DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 2"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Adult 4
         'elemHideIf': "c['ResAdults'] <= 3"},
        {'elemName': 'NAME', 'fldName': 'ResAdult4Surname', 'fldVal': 'Adult 4', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3"},
        {'elemName': 'NAME2', 'fldName': 'ResAdult4Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3 or 'ResAdult4Forename' not in c or not c['ResAdult4Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '3', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3"},
        {'elemName': 'PERS-TYPE', 'fldVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResAdult4DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3 or 'ResAdult4DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 3"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Adult 5
         'elemHideIf': "c['ResAdults'] <= 4"},
        {'elemName': 'NAME', 'fldName': 'ResAdult5Surname', 'fldVal': 'Adult 5', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4"},
        {'elemName': 'NAME2', 'fldName': 'ResAdult5Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4 or 'ResAdult5Forename' not in c or not c['ResAdult5Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '4', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4"},
        {'elemName': 'PERS-TYPE', 'fldVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResAdult5DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4 or 'ResAdult5DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 4"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Adult 6
         'elemHideIf': "c['ResAdults'] <= 5"},
        {'elemName': 'NAME', 'fldName': 'ResAdult6Surname', 'fldVal': 'Adult 6', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5"},
        {'elemName': 'NAME2', 'fldName': 'ResAdult6Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5 or 'ResAdult6Forename' not in c or not c['ResAdult6Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '5', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5"},
        {'elemName': 'PERS-TYPE', 'fldVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResAdult6DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5 or 'ResAdult6DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResAdults'] <= 5"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Children 1
         'elemHideIf': "c['ResChildren'] <= 0"},
        {'elemName': 'NAME', 'fldName': 'ResChild1Surname', 'fldVal': 'Child 1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0"},
        {'elemName': 'NAME2', 'fldName': 'ResChild1Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0 or 'ResChild1Forename' not in c or not c['ResChild1Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '10', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0"},
        {'elemName': 'PERS-TYPE', 'fldVal': '2B', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResChild1DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0 or 'ResChild1DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 0"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Children 2
         'elemHideIf': "c['ResChildren'] <= 1"},
        {'elemName': 'NAME', 'fldName': 'ResChild2Surname', 'fldVal': 'Child 2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1"},
        {'elemName': 'NAME2', 'fldName': 'ResChild2Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1 or 'ResChild2Forename' not in c or not c['ResChild2Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '11', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1"},
        {'elemName': 'PERS-TYPE', 'fldVal': '2B', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResChild2DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1 or 'ResChild2DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 1"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Children 3
         'elemHideIf': "c['ResChildren'] <= 2"},
        {'elemName': 'NAME', 'fldName': 'ResChild3Surname', 'fldVal': 'Child 3', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2"},
        {'elemName': 'NAME2', 'fldName': 'ResChild3Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2 or 'ResChild3Forename' not in c or not c['ResChild3Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '12', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2"},
        {'elemName': 'PERS-TYPE', 'fldVal': '2B', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResChild3DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2 or 'ResChild3DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 2"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Children 4
         'elemHideIf': "c['ResChildren'] <= 3"},
        {'elemName': 'NAME', 'fldName': 'ResChild4Surname', 'fldVal': 'Child 4', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3"},
        {'elemName': 'NAME2', 'fldName': 'ResChild4Forename', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3 or 'ResChild4Forename' not in c or not c['ResChild4Forename']"},
        {'elemName': 'AUTO-GENERATED', 'fldVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3"},
        {'elemName': 'ROOM-SEQ', 'fldVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3"},
        {'elemName': 'ROOM-PERS-SEQ', 'fldVal': '13', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3"},
        {'elemName': 'PERS-TYPE', 'fldVal': '2B', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3"},
        {'elemName': 'R', 'fldName': 'ResBoard', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3"},
        {'elemName': 'RN', 'fldName': 'ResRoomNo', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3 or 'ResRoomNo' not in c or c['ResDeparture'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'fldName': 'ResChild4DOB', 'fldVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3 or 'ResChild4DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['ResChildren'] <= 3"},
        # ### EXTRA PARSING FIELDS (for to interpret reservation coming from the WEB interface)
        {'elemName': 'ACTION', 'fldName': 'ResAction', 'buildExclude': True},
        {'elemName': 'STATUS', 'fldName': 'RU_STATUS', 'buildExclude': True},
        {'elemName': 'RULREF', 'fldName': 'RUL_CODE', 'buildExclude': True},
        {'elemName': 'RUL_PRIMARY', 'fldName': 'RUL_PRIMARY', 'buildExclude': True},
        # {'elemName': 'RU_OBJID', 'fldName': 'RU_SIHOT_OBJID', 'buildExclude': True},
        {'elemName': 'RU_OBJID', 'fldName': 'RUL_SIHOT_OBJID', 'buildExclude': True},
        # {'elemName': 'RO_AGENCY_OBJID', 'fldName': 'RO_SIHOT_AGENCY_OBJID', 'buildExclude': True},
        {'elemName': 'OC_CODE', 'fldName': 'ResOrdererMc', 'buildExclude': True},
        {'elemName': 'OC_OBJID', 'fldName': 'ResOrdererId', 'buildExclude': True},
        {'elemName': 'RES_GROUP', 'fldName': 'ResMktGroup', 'buildExclude': True},  # needed for elemHideIf
        {'elemName': 'RES_OCC', 'fldName': 'ResMktSegment', 'buildExclude': True},  # needed for res_id_values
        {'elemName': 'CHANGES', 'fldName': 'RUL_CHANGES', 'buildExclude': True},  # needed for error notifications
        {'elemName': 'LAST_HOTEL', 'fldName': 'RUL_SIHOT_LAST_HOTEL', 'buildExclude': True},  # needed for HOTMOVE
        {'elemName': 'LAST_CAT', 'fldName': 'RUL_SIHOT_LAST_CAT', 'buildExclude': True},  # needed for HOTMOVE
        # field mappings needed only for parsing XML responses (using 'buildExclude': True)
        {'elemName': 'RES-HOTEL', 'buildExclude': True},
        {'elemName': 'RES-NR', 'buildExclude': True},
        {'elemName': 'SUB-NR', 'buildExclude': True},
        {'elemName': 'OBJID', 'buildExclude': True},
        {'elemName': 'EMAIL', 'buildExclude': True},
        {'elemName': 'PHONE', 'buildExclude': True},
        # PHONE1, MOBIL1 and EMAIL1 are only available in RES person scope/section but not in RES-SEARCH OC
        # {'elemName': 'PHONE1', 'buildExclude': True},
        # {'elemName': 'MOBIL1', 'buildExclude': True},
        {'elemName': 'DEP-TIME', 'buildExclude': True},
        {'elemName': 'COUNTRY', 'buildExclude': True},
        {'elemName': 'CITY', 'buildExclude': True},
        {'elemName': 'STREET', 'buildExclude': True},
        {'elemName': 'LANG', 'buildExclude': True},
        {'elemName': 'MARKETCODE', 'buildExclude': True},     # RES-SEARCH has no MARKETCODE-NO element/tag
        {'elemName': '/RESERVATION'},
        {'elemName': '/ARESLIST'},
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


class Request(SihotXmlParser):  # request from SIHOT to AcuServer
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
            self.rgr_list.append(dict(rgr_ho_fk=self.hn, rgc=list()))
        elif tag in ('FIRST-Person', 'SIHOT-Person'):       # FIRST-Person only seen in room change (CI) on first occ
            self.rgr_list[-1]['rgc'].append(dict())

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
            di, ik = self.rgr_list[-1]['rgc'][-1], 'ShId'
        elif self._curr_tag == 'MATCHCODE':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'AcId'
        elif self._curr_tag == 'SN':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'rgc_surname'
        elif self._curr_tag == 'CN':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'rgc_firstname'
        elif self._curr_tag == 'DOB':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'rgc_dob'
        elif self._curr_tag == 'PHONE':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'rgc_phone'
        elif self._curr_tag == 'EMAIL':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'rgc_email'
        elif self._curr_tag == 'LN':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'rgc_language'
        elif self._curr_tag == 'COUNTRY':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'rgc_country'
        elif self._curr_tag == 'RN':
            di, ik = self.rgr_list[-1]['rgc'][-1], 'rgc_room_id'

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

        self._key_elem_name = key_elem_name
        if not ret_elem_names:
            ret_elem_names = [_['elemName'] for _ in MAP_KERNEL_CLIENT]
        self._ret_elem_names = ret_elem_names    # list of names of XML-elements or response-base-attributes
        self._return_value_as_key = len(ret_elem_names) == 1 and ret_elem_names[0][0] == ':'

        self.ret_elem_values = dict() if self._return_value_as_key else list()
        self._key_elem_index = 0
        self._in_guest_profile = False
        self._elem_fld_map_parser = FldMapXmlParser(cae, deepcopy(MAP_KERNEL_CLIENT))

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
                key = getattr(self, self._key_elem_name)
                if self._key_elem_index > 1:
                    key += '_' + str(self._key_elem_index)
                self.ret_elem_values[key] = getattr(self, self._ret_elem_names[0][1:])
            else:
                keys = self._ret_elem_names
                if len(keys) == 1:
                    self.ret_elem_values.append(getattr(self, keys[0]))
                else:
                    values = dict()
                    for key in keys:
                        elem = self._elem_fld_map_parser.elem_fld_map[key]
                        elem_val = elem['elemListVal'] if 'elemListVal' in elem \
                            else (elem['elemVal'] if 'elemVal' in elem else None)
                        values[key] = getattr(self, key, elem_val)
                        # Q&D fix for search_agencies(): prevent to add elemListVal key/item in next run
                        if 'elemVal' in elem:
                            elem.pop('elemVal')
                    self.ret_elem_values.append(values)
        # for completeness call also SihotXmlParser.end() and FldMapXmlParser.end()
        return super(GuestSearchResponse, self).end(self._elem_fld_map_parser.end(tag))


class FldMapXmlParser(SihotXmlParser):
    def __init__(self, cae, elem_fld_map):
        # create mapping dict for all valid elements
        self.elem_fld_map = {c['elemName']: c for c in deepcopy(elem_fld_map)}
        # if c.get('buildExclude', False) and 'fldName' in c
        super(FldMapXmlParser, self).__init__(cae)

    # XMLParser interface

    def start(self, tag, attrib):
        # if super(FldMapXmlParser, self).start(tag, attrib) is None:
        #    return None  # processed by base class
        super(FldMapXmlParser, self).start(tag, attrib)
        if tag in self.elem_fld_map:
            if 'elemListVal' in self.elem_fld_map[tag]:
                self.elem_fld_map[tag]['elemListVal'].append('')
            elif 'elemVal' in self.elem_fld_map[tag]:  # 2nd time same tag then create list
                li = list([self.elem_fld_map[tag]['elemVal'], ''])
                self.elem_fld_map[tag]['elemListVal'] = li
            self.elem_fld_map[tag]['elemVal'] = ''
            self.elem_fld_map[tag]['elemPath'] = ELEM_PATH_SEP.join(self._elem_path)
            if 'elemPathValues' not in self.elem_fld_map[tag]:
                self.elem_fld_map[tag]['elemPathValues'] = dict()
            return None
        return tag

    def data(self, data):
        # if super(FldMapXmlParser, self).data(data) is None:
        #    return None  # already processed by base class
        super(FldMapXmlParser, self).data(data)
        tag = self._curr_tag
        if tag in self.elem_fld_map:
            self.elem_fld_map[tag]['elemVal'] += data
            if 'elemListVal' in self.elem_fld_map[tag]:
                # add string fragment to last list item
                self.elem_fld_map[tag]['elemListVal'][-1] += data
            return None
        return data

    def end(self, tag):
        super(FldMapXmlParser, self).end(tag)
        if tag in self.elem_fld_map:
            ev = self.elem_fld_map[tag]['elemVal']
            ep = self.elem_fld_map[tag]['elemPath']  # use instead of self._elem_path (got just wiped by super.end())
            epv = self.elem_fld_map[tag]['elemPathValues']
            if ep in epv:
                epv[ep].append(ev)
            else:
                epv[ep] = list([ev])

    def elem_path_values(self, elem_path_suffix):
        return elem_path_values(self.elem_fld_map, elem_path_suffix)


class GuestFromSihot(FldMapXmlParser):
    def __init__(self, cae, elem_fld_map=MAP_CLIENT_DEF):
        super(GuestFromSihot, self).__init__(cae, elem_fld_map)
        self.acu_fld_values = None  # dict() - initialized in self.end() with field names:values

    # XMLParser interface

    def end(self, tag):
        super(GuestFromSihot, self).end(tag)
        if tag == 'GUEST':  # using tag because self._curr_tag got reset by super method of end()
            self.cae.dprint("GuestFromSihot.end(): guest data parsed", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            self.acu_fld_values = dict()
            for c in self.elem_fld_map.keys():
                if 'elemVal' in self.elem_fld_map[c] and self.elem_fld_map[c]['elemVal']:
                    val = self.elem_fld_map[c]['fldValToAcu'] if 'fldValToAcu' in self.elem_fld_map[c] \
                        else self.elem_fld_map[c]['elemVal']
                    fld_name = self.elem_fld_map[c]['fldName']
                    if 'valToAcuConverter' in self.elem_fld_map[c]:
                        self.acu_fld_values[fld_name] = self.elem_fld_map[c]['valToAcuConverter'](val)
                    else:
                        self.acu_fld_values[fld_name] = val


class ResFromSihot(FldMapXmlParser):
    def __init__(self, cae, elem_fld_map=MAP_RES_DEF):
        super(ResFromSihot, self).__init__(cae, elem_fld_map)
        self.blank_elem_fld_map = deepcopy(self.elem_fld_map)
        self.res_list = list()

    # XMLParser interface

    def end(self, tag):
        super(ResFromSihot, self).end(tag)
        if tag == 'RESERVATION':  # using tag because self._curr_tag got reset by super method of end()
            if self.cae.get_option('debugLevel') >= DEBUG_LEVEL_VERBOSE:
                msg = list()
                for k in self.elem_fld_map:
                    if 'elemListVal' in self.elem_fld_map[k]:
                        msg.append(self.elem_fld_map[k]['elemName'] + '=' + str(self.elem_fld_map[k]['elemListVal']))
                    elif 'elemVal' in self.elem_fld_map[k]:
                        msg.append(self.elem_fld_map[k]['elemName'] + '=' + self.elem_fld_map[k]['elemVal'])

                self.cae.dprint("ResFromSihot.end(): reservation parsed:{}".format(",".join(msg)))
                # this could possibly replace the above for loop including the dprint() call
                uprint("ResFromSihot.end(): element path values:{}"
                       .format([c['elemPathValues'] for c in self.elem_fld_map.values() if 'elemPathValues' in c]))
            self.res_list.append(deepcopy(self.elem_fld_map))
            # reset elemVal and elemListVal for next reservation record in the same response
            self.elem_fld_map = deepcopy(self.blank_elem_fld_map)


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

    def __init__(self, cae, elem_fld_map=None, use_kernel=None):
        super(SihotXmlBuilder, self).__init__()
        self.cae = cae
        elem_fld_map = deepcopy(elem_fld_map or cae.get_option('mapRes'))
        self.elem_fld_map = elem_fld_map
        self.use_kernel_interface = cae.get_option('useKernelForRes') if use_kernel is None else use_kernel

        self.sihot_elem_fld = [(c['elemName'],
                                c['fldName'] if 'fldName' in c else None,
                                ((' or a in "' + c['elemHideInActions'] + '"' if 'elemHideInActions' in c else '')
                                 + (' or ' + c['elemHideIf'] if 'elemHideIf' in c else ''))[4:],
                                c['fldVal'] if 'fldVal' in c else None)
                               for c in elem_fld_map if not c.get('buildExclude', False)]
        # self.fix_fld_values = {c['fldName']: c['fldVal'] for c in elem_fld_map if 'fldName' in c and 'fldVal' in c}
        # acu_fld_names and acu_fld_expres need to be in sync
        # self.acu_fld_names = [c['fldName'] for c in elem_fld_map if 'fldName' in c and 'fldVal' not in c]
        # self.acu_fld_expres = [c['fldValFromAcu'] + " as " + c['fldName'] if 'fldValFromAcu' in c else c['fldName']
        #                       for c in elem_fld_map if 'fldName' in c and 'fldVal' not in c]
        # alternative version preventing duplicate field names
        self.fix_fld_values = dict()
        self.acu_fld_names = list()  # acu_fld_names and acu_fld_expres need to be in sync
        self.acu_fld_expres = list()
        for c in elem_fld_map:
            if 'fldName' in c:
                if 'fldVal' in c:
                    self.fix_fld_values[c['fldName']] = c['fldVal']
                elif c['fldName'] not in self.acu_fld_names:
                    self.acu_fld_names.append(c['fldName'])
                    self.acu_fld_expres.append(c['fldValFromAcu'] + " as " + c['fldName'] if 'fldValFromAcu' in c
                                               else c['fldName'])
        # mapping dicts between db field names and xml element names (not works for dup elems like MATCHCODE in RES)
        self.fld_elem = {c['fldName']: c['elemName'] for c in elem_fld_map if 'fldName' in c and 'elemName' in c}
        self.elem_fld = {c['elemName']: c['fldName'] for c in elem_fld_map if 'fldName' in c and 'elemName' in c}

        self.response = None

        self._recs = list()  # list of dicts, used by inheriting class for to store the records to send to SiHOT.PMS
        self._current_row_i = 0

        self._xml = ''
        self._indent = 0

    # --- recs/fields helpers

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
        for tag, fld, hide_expr, val in self.sihot_elem_fld:
            if hide_expr:
                local = dict()
                local['a'] = action  # provide short names for evaluation
                local['c'] = fld_values
                local['datetime'] = datetime
                try:
                    hide = eval(hide_expr, dict(), local)
                except (Exception, KeyError, NameError, SyntaxError, SyntaxWarning, TypeError) as ex:
                    uprint("SihotXmlBuilder.prepare_map_xml() ignoring expression evaluation error:", ex,
                           "Expr=", hide_expr)
                    continue
                if hide:
                    continue
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
                       debug_level=self.cae.get_option('debugLevel'))
        self.cae.dprint("SihotXmlBuilder.send_to_server(): responseParser={}, xml={}".format(response_parser, self.xml),
                        minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        err_msg = sc.send_to_server(self.xml)
        if not err_msg:
            self.response = response_parser or SihotXmlParser(self.cae)
            self.response.parse_xml(sc.received_xml)
            if self.response.server_error() != '0':
                err_msg = "**** SihotXmlBuilder.send_to_server() server return code " + \
                          self.response.server_error() + " error: " + self.response.server_err_msg()

        if err_msg:
            uprint("SihotXmlBuilder.send_to_server() error: ", err_msg)
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


class AcuServer(SihotXmlBuilder):
    def time_sync(self):
        self.beg_xml(operation_code='TS')
        self.add_tag('CDT', datetime.datetime.now().strftime('%y-%m-%d'))
        self.end_xml()

        err_msg = self.send_to_server()
        if err_msg:
            ret = err_msg
        else:
            ret = '' if self.response.rc == '0' else 'Time Sync Error code ' + self.response.rc

        return ret

    def link_alive(self, level='0'):
        self.beg_xml(operation_code='TS')
        self.add_tag('CDT', datetime.datetime.now().strftime('%y-%m-%d'))
        self.add_tag('STATUS', level)  # 0==request, 1==link OK
        self.end_xml()

        err_msg = self.send_to_server()
        if err_msg:
            ret = err_msg
        else:
            ret = '' if self.response.rc == '0' else 'Link Alive Error code ' + self.response.rc

        return ret


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
        super(GuestSearch, self).__init__(ca, elem_fld_map=MAP_KERNEL_CLIENT, use_kernel=True)

    def get_guest(self, obj_id):
        """ return dict with guest data OR None in case of error
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
            uprint("GuestSearch.guest_get() obj_id|error: ", obj_id, err_msg)
            ret = None
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
    def post_message(self, msg, level=3, system='AcuSihot.Interface'):
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
    def fetch_by_gds_no(self, ho_id, gds_no, scope='BASICDATAONLY'):
        self.beg_xml(operation_code='SS')
        self.add_tag('ID', ho_id)
        self.add_tag('GDSNO', gds_no)
        if scope:
            self.add_tag('SCOPE', scope)  # e.g. BASICDATAONLY (see 14.3.4 in WEB interface doc)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ResFromSihot(self.cae))
        # WEB interface return codes (RC): 29==res not found, 1==internal error - see 14.3.5 in WEB interface doc

        return err_msg or self.response.res_list[0]

    def fetch_by_res_id(self, ho_id, res_id, sub_id, scope='BASICDATAONLY'):
        self.beg_xml(operation_code='SS')
        self.add_tag('ID', ho_id)
        self.add_tag('RES-NR', res_id)
        self.add_tag('SUB-NR', sub_id)
        if scope:
            self.add_tag('SCOPE', scope)  # e.g. BASICDATAONLY (see 14.3.4 in WEB interface doc)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ResFromSihot(self.cae))
        # WEB interface return codes (RC): 29==res not found, 1==internal error - see 14.3.5 in WEB interface doc

        return err_msg or self.response.res_list[0]


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
            self.add_tag('CENTRAL-GUEST-ID', guest_id)  # this is not filtering nothing (tried GID from Sihot-To-Acu IF)
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

    def _send_res_to_sihot(self, crow, commit):
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
            acu_client = ClientToSihot(self.cae)
            err_msg = acu_client.send_client_to_sihot(crow)
            if not err_msg:
                # get client/occupant objid directly from acu_client.response
                crow['ShId'] = acu_client.response.objid

        if not err_msg and crow.get('ResOrdererMc') and len(crow['ResOrdererMc']) == 7:  # exclude OTAs like TCAG/TCRENT
            acu_client = ClientToSihot(self.cae)
            err_msg = acu_client.send_client_to_sihot(crow)
            if not err_msg:
                # get orderer objid directly from acu_client.response
                crow['ResOrdererId'] = acu_client.response.objid

        return "" if ensure_client_mode == ECM_TRY_AND_IGNORE_ERRORS else err_msg

    def send_row_to_sihot(self, crow=None, commit=False, ensure_client_mode=ECM_ENSURE_WITH_ERRORS):
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
                err_msg, warn_msg = self._send_res_to_sihot(crow, commit)
        else:
            err_msg = self.res_id_desc(crow, "AcuResToSihot.send_row_to_sihot(): sync with empty GDS number skipped")

        if err_msg:
            self.cae.dprint("ResToSihot.send_row_to_sihot() error: {}".format(err_msg))
        else:
            self.cae.dprint("ResToSihot.send_row_to_sihot() GDSNO={} RESPONDED OBJID={} MATCHCODE={}"
                            .format(gds_no, self.response.objid, self.response.matchcode),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg

    def send_rows_to_sihot(self, break_on_error=True, commit_per_row=False):
        ret_msg = ""
        for row in self.recs:
            err_msg = self.send_row_to_sihot(row, commit=commit_per_row)
            if err_msg:
                if break_on_error:
                    return err_msg  # BREAK/RETURN first error message
                ret_msg += "\n" + err_msg
        return ret_msg

    def res_id_label(self):
        return "GDS/VOUCHER/CD/RO" + ("/RU/RUL" if self.cae.get_option('debugLevel') else "")

    def res_id_values(self, crow):
        return str(crow.get('ResGdsNo')) + \
               "/" + str(crow.get('ResVoucherNo')) + \
               "/" + str(crow.get('AcId')) + "/" + str(crow.get('ResMktSegment')) + \
               ("/" + str(crow.get('RUL_PRIMARY')) + "/" + str(crow.get('RUL_CODE'))
                if self.cae.get_option('debugLevel') and 'RUL_PRIMARY' in crow and 'RUL_CODE' in crow
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
