# SIHOT high level interface (based on the low level interfaces provided by sxmlif)
import datetime
import time
from traceback import format_exc, print_exc
from copy import deepcopy
from textwrap import wrap
import pprint

from sys_data_ids import SDI_SH
from ae_sys_data import ACTION_INSERT, ACTION_UPDATE, ACTION_DELETE, ACTION_SEARCH, FAD_FROM, FAD_ONTO, \
    Field, Record, Records
from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE, full_stack_trace
from sxmlif import (ResKernelGet, ResResponse, SihotXmlParser, SihotXmlBuilder, elem_to_attr,
                    SXML_DEF_ENCODING, ELEM_PATH_SEP, ERR_MESSAGE_PREFIX_CONTINUE)

SH_DATE_FORMAT = '%Y-%m-%d'

SH_RES_SUB_SEP = '/'

ELEM_MISSING = "(missing)"
ELEM_EMPTY = "(empty)"

# ensure client modes (used by ResToSihot.send_res_to_sihot())
ECM_ENSURE_WITH_ERRORS = 0
ECM_TRY_AND_IGNORE_ERRORS = 1
ECM_DO_NOT_SEND_CLIENT = 2


ppf = pprint.PrettyPrinter(indent=12, width=96, depth=9).pformat


def convert_date_from_sh(xml_string):
    return datetime.datetime.strptime(xml_string, '%Y-%m-%d') if xml_string else ''


def convert_date_onto_sh(date):
    return datetime.datetime.strftime(date, '%Y-%m-%d') if date else ''


#  ELEMENT-FIELD-MAP-TUPLE-INDEXES  #################################
MTI_ELEM_NAME = 0
MTI_FLD_NAME = 1
MTI_FLD_FILTER = 2
MTI_FLD_VAL = 3
MTI_FLD_CNV_FROM = 4
MTI_FLD_CNV_ONTO = 5

DUP_FLD_NAME_PREFIX = '+'

# mapping element name in tuple item 0 onto field name in [1], hideIf callable in [2] and default field value in [3]
# default map for GuestFromSihot.elem_fld_map instance and as read-only constant by AcuClientToSihot using the SIHOT
# .. KERNEL interface because SiHOT WEB V9 has missing fields: initials (CD_INIT1/2) and profession (CD_INDUSTRY1/2)
MAP_KERNEL_CLIENT = \
    (
        ('OBJID', 'ShId',
         lambda f: f.ina(ACTION_INSERT) or not f.val()),
        ('MATCHCODE', 'AcId'),
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
         lambda f: not f.val()),
        ('T-LANGUAGE', 'Language'),
        ('COMMENT', 'Comment'),
        ('COMMUNICATION/', None,
         lambda f: f.ina(ACTION_SEARCH)),
        ('PHONE-1', 'HomePhone'),
        ('PHONE-2', 'WorkPhone'),
        ('FAX-1', 'Fax'),
        ('EMAIL-1', 'Email'),
        ('EMAIL-2', 'EmailB'),
        ('MOBIL-1', 'MobilePhone'),
        ('MOBIL-2', 'MobilePhoneB'),
        ('/COMMUNICATION', None,
         lambda f: f.ina(ACTION_SEARCH)),
        ('ADD-DATA/', None,
         lambda f: f.ina(ACTION_SEARCH)),
        ('T-PERSON-GROUP', None, "1A"),
        ('D-BIRTHDAY', 'DOB',
         None,
         None, lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        # 27-09-17: removed b4 migration of BHH/HMC because CD_INDUSTRY1/2 needs first grouping into 3-alphanumeric code
        # ('T-PROFESSION', 'CD_INDUSTRY1'),
        ('INTERNET-PASSWORD', 'Password'),
        ('MATCH-ADM', 'RCIRef'),
        ('MATCH-SM', 'SfId'),
        ('/ADD-DATA', None,
         lambda f: f.ina(ACTION_SEARCH)),
        ('L-EXTIDS/', None,
         lambda f: f.ina(ACTION_SEARCH)),
        ('EXTID/', ('ExtRefs', ),
         lambda f: not f.rfv('ExtRefs')),
        ('EXTID.TYPE', ('ExtRefs', 0, 'Type'),
         lambda f: not f.rfv('ExtRefs')),
        ('EXTID.ID', ('ExtRefs', 0, 'Id'),
         lambda f: not f.rfv('ExtRefs')),
        ('/EXTID', None,
         lambda f: not f.rfv('ExtRefs')),
        # ('EXTID/', None,
        #  lambda f: not f.rfv('ExtRefs') or f.rfv('ExtRefs').count(', ') > 1),
        # ('TYPE', 'ExtRefType2',
        #  lambda f: not f.rfv('ExtRefs') or f.rfv('ExtRefs').count(', ') > 1),
        # ('ID', 'ExtRefId2',
        #  lambda f: not f.rfv('ExtRefs') or f.rfv('ExtRefs').count(', ') > 1),
        # ('/EXTID', None,
        #  lambda f: not f.rfv('ExtRefs') or f.rfv('ExtRefs').count(', ') > 1),
        ('/L-EXTIDS', None,
         lambda f: f.ina(ACTION_SEARCH)),
    )

MAP_PARSE_KERNEL_CLIENT = \
    (
        ('EXT_REFS', DUP_FLD_NAME_PREFIX + 'ExtRefs'),  # only for elemHideIf expressions
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
        ('RESERVATION.GUEST-ID', 'ResOrdererId',
         lambda f: not f.val() and not f.rfv('ShId')),
        ('RESERVATION.MATCHCODE', 'ResOrdererMc'),
        ('GDSNO', 'ResGdsNo'),
        ('VOUCHERNUMBER', 'ResVoucherNo',
         lambda f: f.ina(ACTION_DELETE)),
        ('EXT-KEY', 'ResGroupNo',
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
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
         lambda f: f.ina(ACTION_DELETE)),
        ('ALLOTMENT-EXT-NO', 'ResAllotmentNo',
         lambda f: not f.val(),  ''),
        ('PAYMENT-INST', 'ResAccount',
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('SALES-DATE', 'ResBooked',
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('RATE-SEGMENT', 'ResRateSegment',
         lambda f: not f.val(), ''),
        ('RATE/', ),  # package/arrangement has also to be specified in PERSON:
        ('R', 'ResBoard'),
        ('ISDEFAULT', None, None, 'Y'),
        ('/RATE', ),
        ('RATE/', None,
         lambda f: f.ina(ACTION_DELETE) or f.rfv('ResMktSegment') not in ('ER', )),
        ('R', None,
         lambda f: f.ina(ACTION_DELETE) or not f.rfv('ResMktSegment') not in ('ER', ), 'GSC'),
        ('ISDEFAULT', None,
         lambda f: f.ina(ACTION_DELETE) or not f.rfv('ResMktSegment') not in ('ER', ), 'N'),
        ('/RATE', None,
         lambda f: f.ina(ACTION_DELETE) or not f.rfv('ResMktSegment') not in ('ER', )),
        # The following fallback rate results in error Package TO not valid for hotel 1
        # ('RATE/', ),
        # ('R', 'RO_SIHOT_RATE'},
        # ('ISDEFAULT', None, None, 'N'),
        # ('/RATE', ),
        # ### Reservation Channels - used for assignment of reservation to a allotment or to board payment
        ('RESCHANNELLIST/', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup')[:4] not in ('Owne', 'Prom', 'RCI ')),
        ('RESCHANNEL/', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup')[:4] not in ('Owne', 'Prom', 'RCI ')),
        # needed for to add RCI booking to RCI allotment
        ('RESCHANNEL.IDX', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup')[:4] not in ('RCI ', ),
         1),
        ('RESCHANNEL.MATCHCODE', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup')[:4] not in ('RCI ', ),
         'RCI'),
        ('RESCHANNEL.ISPRICEOWNER', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup')[:4] not in ('RCI ', ),
         1),
        # needed for marketing fly buys for board payment bookings
        ('RESCHANNEL.IDX', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('Promo', ),
         1),
        ('RESCHANNEL.MATCHCODE', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('Promo', ),
         'MAR01'),
        ('RESCHANNEL.ISPRICEOWNER', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('Promo', ),
         1),
        # needed for owner bookings for to select/use owner allotment
        ('RESCHANNEL.IDX', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('Owner', ),
         2),
        ('RESCHANNEL.MATCHCODE', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('Owner', ),
         'TSP'),
        ('RESCHANNEL.ISPRICEOWNER', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('Owner', ),
         1),
        ('/RESCHANNEL', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup')[:4] not in ('Owne', 'Prom', 'RCI ')),
        ('/RESCHANNELLIST', None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup')[:4] not in ('Owne', 'Prom', 'RCI ')),
        # ### GENERAL RESERVATION DATA: arrival/departure, pax, market sources, comments
        ('ARR', 'ResArrival',
         None,
         None, lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        ('DEP', 'ResDeparture',
         None,
         None, lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        ('NOROOMS', None,
         None,
         1),     # needed for DELETE action
        ('NOPAX', 'ResAdults',          # needed for DELETE action
         None,
         None, lambda f, v: int(v), lambda f, v: str(v)),
        ('NOCHILDS', 'ResChildren',
         lambda f: f.ina(ACTION_DELETE),
         None, lambda f, v: int(v), lambda f, v: str(v)),
        ('TEC-COMMENT', 'ResLongNote',
         lambda f: f.ina(ACTION_DELETE)),
        ('COMMENT', 'ResNote',
         lambda f: f.ina(ACTION_DELETE)),
        ('MARKETCODE-NO', 'ResMktSegment',
         lambda f: f.ina(ACTION_DELETE)),
        # ('MEDIA', ),
        ('SOURCE', 'ResSource',
         lambda f: f.ina(ACTION_DELETE)),
        ('NN', 'ResMktGroupNN',
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('CHANNEL', 'ResMktGroup',
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        # ('NN2', 'ResSfId',
        # lambda f: not f.val()),
        ('EXT-REFERENCE', 'ResFlightArrComment',
         lambda f: f.ina(ACTION_DELETE) or not f.val()),    # see also currently unused PICKUP-COMMENT-ARRIVAL element
        ('ARR-TIME', 'ResCheckIn',      # was ResFlightETA (but changed because cannot have duplicate field names)
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PICKUP-TIME-ARRIVAL', 'ResFlightETA',
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PICKUP-TYPE-ARRIVAL', None,                       # 1=car, 2=van
         lambda f: f.ina(ACTION_DELETE) or not f.rfv('ResFlightETA'),
         1),
        # ### PERSON/occupant details
        ('PERS-TYPE-LIST/', ),
        ('PERS-TYPE/', ),
        ('TYPE', None,
         None,
         '1A'),
        ('NO', DUP_FLD_NAME_PREFIX + 'ResAdults'),
        ('/PERS-TYPE', ),
        ('PERS-TYPE/', ),
        ('TYPE', None,
         None,
         '2B'),
        ('NO', DUP_FLD_NAME_PREFIX + 'ResChildren'),
        ('/PERS-TYPE', ),
        ('/PERS-TYPE-LIST', ),
        # Person Records
        ('PERSON/', ('ResPersons', 0),
         lambda f: f.ina(ACTION_DELETE)),
        ('PERSON.NAME', ('ResPersons', 0, 'Surname'),
         lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('AcId') or f.rfv('ShId'),
         lambda f: ("Adult " + str(f.idx()) if f.idx() is None or f.idx() < f.rfv('ResAdults')
                    else "Child " + str(f.idx() - f.rfv('ResAdults') + 1))),
        ('PERSON.NAME2', ('ResPersons', 0, 'Forename'),
         lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('AcId') or f.rfv('ShId')),
        ('AUTO-GENERATED', None,
         lambda f: f.ina(ACTION_DELETE) or (f.rfv('ResAdults') <= 2 and (f.rfv('AcId') or f.rfv('ShId'))),
         '1'),
        ('PERSON.MATCHCODE', ('ResPersons', 0, 'AcId'),
         lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('ShId')),
        ('PERSON.GUEST-ID', ('ResPersons', 0, 'ShId'),
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('ROOM-SEQ', None,
         lambda f: f.ina(ACTION_DELETE),
         '0'),
        ('ROOM-PERS-SEQ', None,
         lambda f: f.ina(ACTION_DELETE),
         lambda f: (str(f.idx()))),
        ('PERSON.PERS-TYPE', None,
         lambda f: f.ina(ACTION_DELETE),
         lambda f: ('1A' if f.idx() < f.rfv('ResAdults') else '2B')),
        ('PERSON.R', DUP_FLD_NAME_PREFIX + 'ResBoard',
         lambda f: f.ina(ACTION_DELETE)),
        ('PERSON.RN', ('ResPersons', 0, 'ResRoomNo'),
         lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('ResDeparture') < datetime.datetime.now()),
        ('PERSON.DOB', ('ResPersons', 0, 'DOB'),
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('/PERSON', None,
         lambda f: f.ina(ACTION_DELETE) or f.rfv('ResAdults') <= 0),
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


def add_sh_options(cae, client_port=None, add_kernel_port=False, add_maps_and_kernel_usage=False):
    cae.add_option('shServerIP', "IP address of the Sihot WEB/KERNEL server", 'localhost', 'i')
    cae.add_option('shServerPort', "IP port of the Sihot WEB interface", 14777, 'w')
    if client_port:
        # default is 14773 for Acumen and 14774 for the Sihot side (always the next higher port number)
        cae.add_option('shClientPort', "IP port of SXML interface provided by this server for Sihot", client_port, 'm')
    if add_kernel_port:
        # e.g. for GuestBulkFetcher we need also the kernel interface port of Sihot
        cae.add_option('shServerKernelPort', "IP port of the KERNEL interface of the Sihot server", 14772, 'k')
    cae.add_option('shTimeout', "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
    cae.add_option('shXmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')
    if add_maps_and_kernel_usage:
        cae.add_option('useKernelForClient', "Used interface for clients (0=web, 1=kernel)", USE_KERNEL_FOR_CLIENTS_DEF,
                       'g', choices=(0, 1))
        cae.add_option('mapClient', "Guest/Client mapping of xml to db items", MAP_CLIENT_DEF, 'm')
        cae.add_option('useKernelForRes', "Used interface for reservations (0=web, 1=kernel)", USE_KERNEL_FOR_RES_DEF,
                       'z', choices=(0, 1))
        cae.add_option('mapRes', "Reservation mapping of xml to db items", MAP_RES_DEF, 'n')


def print_sh_options(cae):
    uprint("Sihot server IP/WEB-interface-port:", cae.get_option('shServerIP'), cae.get_option('shServerPort'))
    client_port = cae.get_option('shClientPort')
    if client_port:
        ip_addr = cae.get_config('shClientIP', default_value=cae.get_option('shServerIP'))
        uprint("Sihot client IP/port for listening:", ip_addr, client_port)
    kernel_port = cae.get_option('shServerKernelPort')
    if kernel_port:
        uprint("Sihot server KERNEL-interface-port:", kernel_port)
    uprint("Sihot TCP Timeout/XML Encoding:", cae.get_option('shTimeout'), cae.get_option('shXmlEncoding'))


def guest_data(cae, obj_id):
    guest_search = GuestSearch(cae)
    ret = guest_search.get_guest(obj_id)
    return ret


def elem_path_join(elem_names):
    """
    convert list of element names to element path.
    :param elem_names:  list of element names.
    :return:            element path.
    """
    return ELEM_PATH_SEP.join(elem_names)


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
        paths_values = fld.paths(system=SDI_SH, direction=FAD_FROM)
        if paths_values:
            for path_key, values in paths_values:
                if path_key.endswith(elem_path_suffix):
                    ret_list.extend(values)
    return ret_list


def elem_value(shd, elem_name_or_path, arri=0, verbose=False, default_value=None):
    """
    get the xml element value from the shd row_dict variable, using array index (arri) in case of multiple values

    :param shd:                 dict of sihot data row with the element names as the dict keys.
    :param elem_name_or_path:   either single element name (str), element path (str) or list of path element names.
    :param arri:                index of element array value (starting with 0).
    :param verbose:             pass True to get ELEM_EMPTY/ELEM_MISSING pseudo values instead of default_value value.
    :param default_value:       default element value.
    :return:                    element value.
    """
    elem_path = ""
    if isinstance(elem_name_or_path, list):
        if len(elem_name_or_path) > 1:
            elem_path = elem_path_join(elem_name_or_path)
        else:
            elem_name_or_path = elem_name_or_path[0]
    elif ELEM_PATH_SEP in elem_name_or_path:
        elem_path = elem_name_or_path
    elem_nam = elem_path.rsplit(ELEM_PATH_SEP, 1)[1] if elem_path else elem_name_or_path

    elem_val = None
    if elem_nam not in shd:
        elem_val = ELEM_MISSING if verbose else default_value
    elif elem_path:
        val_arr = elem_path_values(shd, elem_path)
        if 0 <= arri < len(val_arr):
            elem_val = val_arr[arri]
    else:
        elem_def = shd[elem_nam]
        if 'elemListVal' in elem_def and len(elem_def['elemListVal']) > arri:
            elem_val = elem_def['elemListVal'][arri]
        else:
            elem_val = ""
        if not elem_val and elem_def.get('elemVal'):
            elem_val = elem_def['elemVal']

    if not elem_val:
        elem_val = ELEM_EMPTY if verbose else default_value

    return elem_val


def hotel_and_res_id(shd):
    ho_id = elem_value(shd, 'RES-HOTEL')
    res_nr = elem_value(shd, 'RES-NR')
    sub_nr = elem_value(shd, 'SUB-NR')
    if not ho_id or not res_nr:
        return None, None
    return ho_id, res_nr + (SH_RES_SUB_SEP + sub_nr if sub_nr else '') + '@' + ho_id


def pax_count(shd):
    adults = elem_value(shd, 'NOPAX')
    if not adults:
        adults = 0
    else:
        adults = int(adults)
    children = elem_value(shd, 'NOCHILDS')
    if not children:
        children = 0
    else:
        children = int(children)
    return adults + children


def gds_number(shd):
    return elem_value(shd, 'GDSNO')


def date_range_chunks(date_from, date_till, fetch_max_days):
    one_day = datetime.timedelta(days=1)
    add_days = datetime.timedelta(days=fetch_max_days) - one_day
    chunk_till = date_from - one_day
    while chunk_till < date_till:
        chunk_from = chunk_till + one_day
        chunk_till = min(chunk_from + add_days, date_till)
        yield chunk_from, chunk_till


def gds_no_to_ids(cae, hotel_id, gdsno):
    ids = dict(ResHotelId=hotel_id, ResGdsNo=gdsno)
    rfr = ResFetch(cae).fetch_by_gds_no(hotel_id, gdsno)
    if isinstance(rfr, dict):
        ids['ResObjId'] = elem_value(rfr, ['SIHOT-Document', 'RESERVATION', 'OBJID'])
        ids['ResNo'] = elem_value(rfr, 'RES-NR')
        ids['ResSubNo'] = elem_value(rfr, 'SUB-NR')
        ids['ResSfId'] = elem_value(rfr, 'NN2')
    return ids


def gds_no_to_obj_id(cae, hotel_id, gdsno):
    return gds_no_to_ids(cae, hotel_id, gdsno).get('ResObjId')


def res_no_to_ids(cae, hotel_id, res_id, sub_id):
    ret = dict(ResHotelId=hotel_id, ResNo=res_id, ResSubNo=sub_id)
    rfr = ResFetch(cae).fetch_by_res_id(hotel_id, res_id, sub_id)
    if isinstance(rfr, dict):
        ret['ResObjId'] = elem_value(rfr, ['SIHOT-Document', 'RESERVATION', 'OBJID'])
        ret['ResGdsNo'] = elem_value(rfr, 'GDSNO')
        ret['ResSfId'] = elem_value(rfr, 'NN2')
    else:
        ret = rfr
    return ret


def res_no_to_obj_id(cae, hotel_id, res_id, sub_id):
    return res_no_to_ids(cae, hotel_id, res_id, sub_id).get('ResObjId')


def res_search(cae, date_from, date_till=None, mkt_sources=None, mkt_groups=None, max_los=28,
               search_flags='', search_scope='', chunk_pause=1):
    """
    search reservations with the criteria specified by the parameters.

    :param cae:             instance of the application environment specifying searched Sihot server.
    :param date_from:       date of first day of included arrivals.
    :param date_till:       date of last day of included arrivals.
    :param mkt_sources:     list of market source codes.
    :param mkt_groups:      list of market group codes.
    :param max_los:         integer with maximum length of stay.
    :param search_flags:    string with search flag words (separated with semicolon).
    :param search_scope:    string with search scope words (separated with semicolon).
    :param chunk_pause:     integer with seconds to pause between fetch of date range chunks.
    :return:                string with error message if error or list of Sihot reservations.
    """
    if not date_till:
        date_till = date_from

    err_msg = ""
    all_rows = list()
    try:
        rs = ResSearch(cae)
        # the from/to date range filter of WEB ResSearch filters the arrival date only (not date range/departure)
        # adding flag ;WITH-PERSONS results in getting the whole reservation duplicated for each PAX in rooming list
        # adding scope NOORDERER prevents to include/use LANG/COUNTRY/NAME/EMAIL of orderer
        for chunk_beg, chunk_end in date_range_chunks(date_from, date_till, max_los):
            chunk_rows = rs.search(from_date=chunk_beg, to_date=chunk_end, flags=search_flags,
                                   scope=search_scope)
            if chunk_rows and isinstance(chunk_rows, str):
                err_msg = "Sihot.PMS reservation search error: {}".format(chunk_rows)
                break
            elif not chunk_rows or not isinstance(chunk_rows, list):
                err_msg = "Unspecified Sihot.PMS reservation search error"
                break
            cae.dprint("  ##  Fetched {} reservations from Sihot with arrivals between {} and {} - flags={}, scope={}"
                       .format(len(chunk_rows), chunk_beg, chunk_end, search_flags, search_scope))
            valid_rows = list()
            for res in chunk_rows:
                reasons = list()
                check_in = res['ResArrival'].val()
                check_out = res['ResDeparture'].val()
                if not check_in or not check_out:
                    reasons.append("incomplete check-in={} check-out={}".format(check_in, check_out))
                if not (date_from <= check_in <= date_till):
                    reasons.append("arrival {} not between {} and {}".format(check_in, date_from, date_till))
                mkt_src = elem_value(res, 'MARKETCODE')
                if mkt_sources and mkt_src not in mkt_sources:
                    reasons.append("disallowed market source {}".format(mkt_src))
                mkt_group = elem_value(res, 'CHANNEL')
                if mkt_groups and mkt_group not in mkt_groups:
                    reasons.append("disallowed market group/channel {}".format(mkt_group))
                if reasons:
                    cae.dprint("  ##  Skipped Sihot reservation:", res, " reason(s):", reasons,
                               minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                    continue
                valid_rows.append(res)

            all_rows.extend(valid_rows)
            time.sleep(chunk_pause)
    except Exception as ex:
        err_msg = "Sihot interface reservation fetch exception: {}\n{}".format(ex, format_exc())

    return err_msg or all_rows


def obj_id_to_res_no(cae, obj_id):
    """
    using RESERVATION-GET oc from KERNEL interface (see 7.3 in SIHOT KERNEL interface doc).
    :param cae:         Console App Environment instance.
    :param obj_id:      Sihot Reservation Object Id.
    :return:            reservation number as tuple of (hotel_id, res_id, sub_id) or None if not found
    """
    return ResKernelGet(cae).fetch_res_no(obj_id)


def _strip_err_msg(error_msg):
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


class GuestSearchResponse(SihotXmlParser):
    def __init__(self, cae, ret_elem_names=None, key_elem_name=None):
        """
        response to the GUEST-GET request oc of the KERNEL interface

        :param cae:             app environment instance.
        :param ret_elem_names:  list of xml element names (or response attributes) to return. If there is only one
                                list element with a leading ':' character then self.ret_elem_values will be a dict
                                with the search value as the key. If ret_elem_names consists of exact one item then
                                ret_elem_values will be a list with the plain return values. If ret_elem_names contains
                                more than one item then self.ret_elem_values will be a dict where the ret_elem_names
                                are used as keys. If the ret_elem_names list is empty (or None) then the returned
                                self.ret_elem_values list of dicts will provide all elements that are returned by the
                                Sihot interface and defined within the used map (MAP_KERNEL_CLIENT).
        :param key_elem_name:   element name used for the search (only needed if self._return_value_as_key==True).
        """
        super(GuestSearchResponse, self).__init__(cae)
        self._base_tags.append('GUEST-NR')
        self.guest_nr = None

        full_map = MAP_KERNEL_CLIENT + MAP_PARSE_KERNEL_CLIENT

        self._key_elem_name = key_elem_name
        if not ret_elem_names:
            ret_elem_names = [_[MTI_ELEM_NAME].strip('/') for _ in full_map]
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
                elem = getattr(self, elem_to_attr(self._key_elem_name))
                if self._key_elem_index > 1:
                    elem += '_' + str(self._key_elem_index)
                self.ret_elem_values[elem] = getattr(self, elem_to_attr(self._ret_elem_names[0][1:]))
            else:
                elem_names = self._ret_elem_names
                if len(elem_names) == 1:
                    self.ret_elem_values.append(getattr(self, elem_to_attr(elem_names[0])))
                else:
                    values = dict()
                    for elem in elem_names:
                        if elem in self._elem_fld_map_parser.elem_fld_map:
                            field = self._elem_fld_map_parser.elem_fld_map[elem]
                            values[elem] = getattr(self, elem_to_attr(elem),
                                                   field.val(system=SDI_SH, direction=FAD_FROM))
                    self.ret_elem_values.append(values)
        # for completeness call also SihotXmlParser.end() and FldMapXmlParser.end()
        return super(GuestSearchResponse, self).end(self._elem_fld_map_parser.end(tag))


class FldMapXmlParser(SihotXmlParser):
    def __init__(self, cae, elem_map):
        super(FldMapXmlParser, self).__init__(cae)
        self._current_field = None
        self._current_data = None
        self._current_idx_path = list()
        self._rec = Record(system=SDI_SH, direction=FAD_FROM)

        # create field data parsing record and mapping dict for all elements having a field value
        self.elem_fld_map = dict()
        for fas in elem_map:
            map_len = len(fas)
            if map_len <= MTI_FLD_NAME:
                continue
            field_name = field_idx = fas[MTI_FLD_NAME]
            if not field_name:
                continue
            if isinstance(field_name, tuple):
                if len(field_name) == 1:
                    field_idx = field_name[0]
                field_name = field_name[-1]
            elif field_name.startswith(DUP_FLD_NAME_PREFIX):
                continue

            elem_name = fas[MTI_ELEM_NAME].strip('/')
            field = Field()
            field.name = field_name
            field.set_name(elem_name, system=SDI_SH, direction=FAD_FROM, protect=True)
            field.set_rec(self._rec)
            # add additional aspects: first always add converter (for to create separate system value)
            if map_len > MTI_FLD_CNV_FROM and fas[MTI_FLD_CNV_FROM]:
                field.set_converter(fas[MTI_FLD_CNV_FROM], system=SDI_SH, direction=FAD_FROM, extend=True)
            if map_len > MTI_FLD_FILTER and fas[MTI_FLD_FILTER]:
                field.set_filter(fas[MTI_FLD_FILTER], system=SDI_SH, direction=FAD_FROM, protect=True)
            if map_len > MTI_FLD_VAL and fas[MTI_FLD_VAL] is not None:
                val_or_cal = fas[MTI_FLD_VAL]
                if callable(val_or_cal):
                    field.set_calculator(val_or_cal, system=SDI_SH, direction=FAD_FROM, protect=True)
                else:
                    field.set_val(val_or_cal, system=SDI_SH, direction=FAD_FROM)

            self._rec.add_field(field, idx=field_idx)
            self.elem_fld_map[elem_name] = field

    def clear_rec(self):
        self._rec.clear_vals(system=self._rec.system, direction=self._rec.direction)
        return self

    @property
    def rec(self):
        return self._rec

    def find_field(self, tag):
        if tag in self.elem_fld_map:
            elem_name = tag
            field = self.elem_fld_map[elem_name]
        else:
            full_path = ELEM_PATH_SEP.join(self._elem_path)
            for elem_name, field in self.elem_fld_map.items():
                if elem_name == full_path or full_path.endswith(ELEM_PATH_SEP + elem_name):
                    break
            else:
                elem_name, field = None, None
        return elem_name, field

    def fld_idx_path(self, fld_path):
        fld_path_len = len(fld_path)
        cur_path = self._current_idx_path
        cur_path_len = len(cur_path)
        if fld_path_len == cur_path_len:
            idx_path = cur_path[:-1]
            idx_path.append(fld_path[-1])
        else:
            match = 0
            while match < min(fld_path_len, cur_path_len) and fld_path[match] == cur_path[match]:
                match += 1
            idx_path = list(fld_path)
            if match:
                idx_pos = min(match, cur_path_len - 1)
                if fld_path_len > cur_path_len >= match \
                        and isinstance(fld_path[idx_pos], int) and isinstance(cur_path[idx_pos], int):
                    idx_path[match] = cur_path[idx_pos] + 1
                elif fld_path_len < cur_path_len:
                    idx_path.append(cur_path[fld_path_len])
        return idx_path

    # XMLParser interface

    def start(self, tag, attrib):
        super(FldMapXmlParser, self).start(tag, attrib)
        elem_name, field = self.find_field(tag)
        if not field:
            self._current_field = None
            return tag

        if isinstance(field.name, tuple):   # deeper structure?
            self._current_idx_path = self.fld_idx_path(field.name)
        self._current_field = Field(**field.aspects).set_rec(self._rec, system=SDI_SH, direction=FAD_FROM)

        # TODO: remove after refactoring
        '''
        if field.append_record(system=SDI_SH, direction=FAD_FROM):
            recs = field.value(system=SDI_SH, direction=FAD_FROM)
            self._current_idx_path = len(recs) - 1   # set current Records idx to new/just-appended Record instance
            self._current_field = None
            return tag
        field = Field(**field.aspects).set_rec(self._rec, system=SDI_SH, direction=FAD_FROM)
        if self._current_idx_path is not None:
            field.set_idx(self._current_idx_path)
        self._current_field = self.elem_fld_map[elem_name] = field
        '''

        self._current_data = ''
        return None

    def data(self, data):
        super(FldMapXmlParser, self).data(data)
        if self._current_field:
            self._current_data += data
            return None
        return data

    def end(self, tag):
        if self._current_field:
            self._current_field.set_val(self._current_data, *self._current_idx_path, system=SDI_SH, direction=FAD_FROM)
            self._current_field = None
        super(FldMapXmlParser, self).end(tag)


class GuestFromSihot(FldMapXmlParser):
    def __init__(self, cae, elem_map=MAP_CLIENT_DEF):
        super(GuestFromSihot, self).__init__(cae, elem_map)
        self.guest_list = Records()

    # XMLParser interface

    def end(self, tag):
        super(GuestFromSihot, self).end(tag)
        if tag == 'GUEST':  # using tag arg here because self._curr_tag got reset by super method of end()
            self.guest_list.append(deepcopy(self._rec))
            self.clear_rec()


class ResFromSihot(FldMapXmlParser):
    def __init__(self, cae, elem_map=MAP_RES_DEF):
        super(ResFromSihot, self).__init__(cae, elem_map)
        self.res_list = Records()

    # XMLParser interface

    def end(self, tag):
        super(ResFromSihot, self).end(tag)
        if tag == 'RESERVATION':  # using tag because self._curr_tag got reset by super method of end()
            self.res_list.append(deepcopy(self._rec))
            self.clear_rec()


class GuestSearch(SihotXmlBuilder):
    def __init__(self, cae):
        super().__init__(cae, use_kernel=True)

    def get_guest(self, obj_id):
        """ return dict with guest data OR str with error message in case of error.
        """
        msg = "GuestSearch.get_guest({}) ".format(obj_id)
        self.beg_xml(operation_code='GUEST-GET')
        self.add_tag('GUEST-PROFILE', self.new_tag('OBJID', obj_id))
        self.end_xml()

        rp = GuestSearchResponse(self.cae)
        err_msg = self.send_to_server(response_parser=rp)
        if not err_msg and self.response:
            ret = self.response.ret_elem_values[0]
            self.cae.dprint(msg + "xml='{}'; result={}".format(self.xml, ret), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        else:
            ret = msg + "error='{}'".format(err_msg)
        return ret

    def get_guest_nos_by_matchcode(self, matchcode, exact_matchcode=True):
        search_for = {'MATCHCODE': matchcode,
                      'FLAGS': 'FIND-ALSO-DELETED-GUESTS' + (';MATCH-EXACT-MATCHCODE' if exact_matchcode else ''),
                      }
        return self.search_guests(search_for, ['guest_nr'])

    def get_objid_by_guest_no(self, guest_no):
        search_for = {'GUEST-NR': guest_no,
                      'FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        ret = self.search_guests(search_for, ['objid'])
        return ret[0] if len(ret) > 0 else None

    def get_objids_by_guest_name(self, name):
        forename, surname = name.split(' ', maxsplit=1)
        search_for = {'NAME-1': surname,
                      'NAME-2': forename,
                      'FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(search_for, ['objid'])

    def get_objids_by_guest_names(self, surname, forename):
        search_for = {'NAME-1': surname,
                      'NAME-2': forename,
                      'FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(search_for, ['objid'])

    def get_objids_by_email(self, email):
        search_for = {'EMAIL-1': email,
                      'FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(search_for, ['objid'])

    def get_objids_by_matchcode(self, matchcode, exact_matchcode=True):
        search_for = {'MATCHCODE': matchcode,
                      'FLAGS': 'FIND-ALSO-DELETED-GUESTS' + (';MATCH-EXACT-MATCHCODE' if exact_matchcode else ''),
                      }
        return self.search_guests(search_for, ['objid'])

    def get_objid_by_matchcode(self, matchcode, exact_matchcode=True):
        search_for = {'MATCHCODE': matchcode,
                      'FLAGS': 'FIND-ALSO-DELETED-GUESTS' + (';MATCH-EXACT-MATCHCODE' if exact_matchcode else ''),
                      }
        ret = self.search_guests(search_for, [':objid'], key_elem_name='matchcode')
        if ret:
            return self._check_and_get_objid_of_matchcode_search(ret, matchcode, exact_matchcode)

    def search_agencies(self):
        search_for = {'T-GUEST': 7,     # 1=Guest, 7=Company (numbers wrong documented in Sihot KERNEL PDF)
                      'FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(search_for, ['OBJID', 'MATCHCODE'])

    def search_guests(self, search_for, ret_elem_names, key_elem_name=None):
        """ return dict with search element/attribute value as the dict key if len(ret_elem_names)==1 and if
            ret_elem_names[0][0]==':' (in this case key_elem_name has to provide the search element/attribute name)
            OR return list of values if len(ret_elem_names) == 1
            OR return list of dict with ret_elem_names keys if len(ret_elem_names) >= 2
            OR return None in case of error.
        """
        msg = "GuestSearch.search_guests({}, {}, {})".format(search_for, ret_elem_names, key_elem_name)
        self.beg_xml(operation_code='GUEST-SEARCH')
        self.add_tag('GUEST-SEARCH-REQUEST', ''.join([self.new_tag(e, v) for e, v in search_for.items()]))
        self.end_xml()

        rp = GuestSearchResponse(self.cae, ret_elem_names, key_elem_name=key_elem_name)
        err_msg = self.send_to_server(response_parser=rp)
        if not err_msg and self.response:
            ret = self.response.ret_elem_values
            self.cae.dprint(msg + " xml='{}'; result={}".format(self.xml, ret), minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        else:
            uprint(msg + " error: {}".format(err_msg))
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
            # ask Gubse to implement/fix guest_id search/filter option on RES-SEARCH operation of Sihot WEB interface.
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


class FldMapXmlBuilder(SihotXmlBuilder):
    def __init__(self, cae, use_kernel=None, elem_map=None):
        super().__init__(cae, use_kernel=use_kernel)

        self._recs = list()  # list of dicts, used by inheriting class for to store the records to send to SiHOT.PMS
        self._current_rec_i = 0

        self.action = ''
        self.elem_map = deepcopy(elem_map or cae.get_option('mapRes'))
        self.elem_fld_rec = Record(system=SDI_SH, direction=FAD_ONTO)
        for fas in self.elem_map:
            map_len = len(fas)
            if map_len <= MTI_FLD_NAME or fas[MTI_FLD_NAME] is None:
                continue
            field_name = field_idx = fas[MTI_FLD_NAME]
            if not field_name:
                continue
            elif isinstance(field_name, tuple):
                if len(field_name) == 1:
                    field_idx = field_name[-1]
                field_name = field_name[-1]
            elif field_name.startswith(DUP_FLD_NAME_PREFIX):
                continue

            elem_name = fas[MTI_ELEM_NAME].strip('/')
            field = Field()
            field.name = field_name
            field.set_name(elem_name, system=SDI_SH, direction=FAD_ONTO, protect=True)
            field.set_rec(self.elem_fld_rec)
            # add additional aspects: first always add converter (for to create separate system value)
            if map_len > MTI_FLD_CNV_ONTO and fas[MTI_FLD_CNV_ONTO]:
                field.set_converter(fas[MTI_FLD_CNV_ONTO], system=SDI_SH, direction=FAD_ONTO, extend=True)
            if map_len > MTI_FLD_FILTER and fas[MTI_FLD_FILTER]:
                field.set_filter(fas[MTI_FLD_FILTER], system=SDI_SH, direction=FAD_ONTO, protect=True)
            if map_len > MTI_FLD_VAL and fas[MTI_FLD_VAL] is not None:
                val_or_cal = fas[MTI_FLD_VAL]
                if callable(val_or_cal):
                    field.set_calculator(val_or_cal, system=SDI_SH, direction=FAD_ONTO, protect=True)
                else:
                    field.set_val(val_or_cal, system=SDI_SH, direction=FAD_ONTO)

            self.elem_fld_rec.add_field(field, idx=field_idx)

        self.rec_link_field = Field().set_rec(self.elem_fld_rec)

        # TODO: remove after refactoring
        ''' 
        self.sihot_elem_fld = [(c[MTI_ELEM_NAME],
                                c[MTI_FLD_NAME] if len(c) > MTI_FLD_NAME else None,
                                c[MTI_FLD_VAL] if len(c) > MTI_FLD_VAL else None,
                                c[MTI_FLD_FILTER] if len(c) > MTI_FLD_FILTER else None,
                                )
                               for c in elem_map]
        self.fix_fld_vals = dict()
        self.acu_fld_names = list()  # acu_fld_names and acu_fld_expres need to be in sync
        self.acu_fld_expres = list()
        self.fld_elem = dict()
        self.elem_fld = dict()
        for c in elem_map:
            if len(c) > MTI_FLD_NAME and c[MTI_FLD_NAME]:
                if len(c) > MTI_FLD_VAL:
                    self.fix_fld_vals[c[MTI_FLD_NAME]] = c[MTI_FLD_VAL]
                elif c[MTI_FLD_NAME] not in self.acu_fld_names:
                    self.acu_fld_names.append(c[MTI_FLD_NAME])
                    self.acu_fld_expres.append(c['fldValFromAcu'] + " as " + c[MTI_FLD_NAME] if 'fldValFromAcu' in c
                                               else c[MTI_FLD_NAME])
                # mapping dicts between db col names and xml elem names (not works for dup elems like MATCHCODE in RES)
                self.fld_elem[c[MTI_FLD_NAME]] = c[MTI_ELEM_NAME]
                self.elem_fld[c[MTI_ELEM_NAME]] = c[MTI_FLD_NAME]
        '''

    # --- rec/fld_vals helpers

    @property
    def fields(self):
        return self._recs[self._current_rec_i] if len(self._recs) > self._current_rec_i else dict()

    # def next_rec(self): self._current_rec_i += 1

    @property
    def rec_count(self):
        return len(self._recs)

    @property
    def recs(self):
        return self._recs

    def prepare_map_xml(self, fld_vals, include_empty_values=True):
        self.elem_fld_rec.clear_vals()
        for k, v in fld_vals.items():
            self.elem_fld_rec[k].set_val(v)
        self.elem_fld_rec.push(SDI_SH)

        old_act = self.elem_fld_rec.action
        self.elem_fld_rec.action = self.action
        inner_xml = ''
        for elem_map_item in self.elem_map:
            tag = elem_map_item[MTI_ELEM_NAME]
            fld = elem_map_item[MTI_FLD_NAME] if len(elem_map_item) > MTI_FLD_NAME else None
            if fld:
                if not isinstance(fld, tuple):
                    fld = fld.strip(DUP_FLD_NAME_PREFIX)
                field = self.elem_fld_rec[fld]
                val = field.val(system=SDI_SH, direction=FAD_ONTO)
            else:
                field = self.rec_link_field
                val = None
            filter_func = field.filter(system=SDI_SH, direction=FAD_ONTO)
            if filter_func:
                assert callable(filter_func), "filter aspect {} must be callable".format(filter_func)
                if filter_func(field):
                    continue

            if tag.endswith('/'):
                self._indent += 1
                inner_xml += '\n' + ' ' * self._indent + self.new_tag(tag[:-1], closing=False)
            elif tag.startswith('/'):
                self._indent -= 1
                inner_xml += self.new_tag(tag[1:], opening=False)
            elif include_empty_values or (fld and fld in fld_vals) or val:
                inner_xml += self.new_tag(tag, self.convert_value_to_xml_string(fld_vals[fld]
                                                                                if fld and fld in fld_vals else val))
        self.elem_fld_rec.action = old_act
        return inner_xml


class ClientToSihot(FldMapXmlBuilder):
    def __init__(self, cae):
        super().__init__(cae,
                         use_kernel=cae.get_option('useKernelForClient'),
                         elem_map=cae.get_option('mapClient') or MAP_KERNEL_CLIENT)

    def _prepare_guest_xml(self, fld_vals, fld_name_suffix=''):
        if not self.action:
            self.action = ACTION_UPDATE if fld_vals.get('ShId' + fld_name_suffix) else ACTION_INSERT
        self.beg_xml(operation_code='GUEST-CHANGE' if self.action == ACTION_UPDATE else 'GUEST-CREATE')
        self.add_tag('GUEST-PROFILE', self.prepare_map_xml(fld_vals))
        self.end_xml()
        self.cae.dprint("ClientToSihot._prepare_guest_xml() fld_vals/action/result: ",
                        fld_vals, self.action, self.xml, minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    def _prepare_guest_link_xml(self, mc1, mc2):
        mct1 = self.new_tag('MATCHCODE-GUEST', self.convert_value_to_xml_string(mc1))
        mct2 = self.new_tag('CONTACT',
                            self.new_tag('MATCHCODE', self.convert_value_to_xml_string(mc2)) +
                            self.new_tag('FLAG', 'DELETE' if self.action == ACTION_DELETE else ''))
        self.beg_xml(operation_code='GUEST-CONTACT')
        self.add_tag('CONTACTLIST', mct1 + mct2)
        self.end_xml()
        self.cae.dprint("ClientToSihot._prepare_guest_link_xml() mc1/mc2/result: ", mc1, mc2, self.xml,
                        minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    def _send_link_to_sihot(self, pk1, pk2):
        self._prepare_guest_link_xml(pk1, pk2)
        return self.send_to_server()

    def _send_person_to_sihot(self, fld_vals, first_person=""):  # pass AcId of first person for to send 2nd person
        self._prepare_guest_xml(fld_vals, fld_name_suffix='2' if first_person else '')
        err_msg = self.send_to_server()
        if 'guest exists already' in err_msg and self.action == ACTION_INSERT:
            self.action = ACTION_UPDATE
            self._prepare_guest_xml(fld_vals, fld_name_suffix='2' if first_person else '')
            err_msg = self.send_to_server()
        return err_msg

    def send_client_to_sihot(self, fld_vals=None):
        if not fld_vals:
            fld_vals = self.fields
        msg = "ClientToSihot.send_client_to_sihot({}): action={}".format(fld_vals, self.action)
        err_msg = self._send_person_to_sihot(fld_vals)
        if err_msg:
            self.cae.dprint(msg + "; err='{}'".format(err_msg))
        else:
            self.cae.dprint(msg + "; client={} RESPONDED OBJID={}/MATCHCODE={}"
                            .format(fld_vals['AcId'], self.response.objid, self.response.matchcode),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg


class ResToSihot(FldMapXmlBuilder):
    def __init__(self, cae):
        super().__init__(cae,
                         use_kernel=cae.get_option('useKernelForRes'),
                         elem_map=cae.get_config('mapRes') or MAP_WEB_RES)
        self._warning_frags = self.cae.get_config('warningFragments') or list()  # list of warning text fragments
        self._warning_msgs = ""
        self._gds_errors = dict()

    def _add_sihot_configs(self, fld_vals):
        mkt_seg = fld_vals.get('ResMktSegment', '')
        hotel_id = str(fld_vals.get('ResHotelId', 999))
        arr_date = fld_vals.get('arr_date')
        today = datetime.datetime.today()
        cf = self.cae.get_config

        if arr_date and arr_date > today:            # Sihot doesn't accept allotment for reservations in the past
            val = cf(mkt_seg + '_' + hotel_id, section='SihotAllotments',
                     default_value=cf(mkt_seg, section='SihotAllotments'))
            if val:
                fld_vals['ResAllotmentNo'] = val

        if not fld_vals.get('ResRateSegment'):  # not specified? FYI: this field is not included in V_ACU_RES_DATA
            val = cf(mkt_seg, section='SihotRateSegments', default_value=mkt_seg)
            if val:
                fld_vals['ResRateSegment'] = val

        val = cf(mkt_seg, section='SihotPaymentInstructions')
        if val:
            fld_vals['ResAccount'] = val

        if self.action != ACTION_DELETE and fld_vals.get('RU_STATUS', 0) != 120 and arr_date and arr_date > today:
            val = cf(mkt_seg, section='SihotResTypes')
            if val:
                fld_vals['ResStatus'] = val

    def _prepare_res_xml(self, fld_vals):
        self.action = fld_vals.get('ResAction', ACTION_INSERT)
        self._add_sihot_configs(fld_vals)
        inner_xml = self.prepare_map_xml(fld_vals)
        if self.use_kernel_interface:
            if self.action == ACTION_INSERT:
                self.beg_xml(operation_code='RESERVATION-CREATE')
            else:
                self.beg_xml(operation_code='RESERVATION-DATA-CHANGE')
            self.add_tag('RESERVATION-PROFILE', inner_xml)
        else:
            self.beg_xml(operation_code='RES', add_inner_xml=inner_xml)
        self.end_xml()
        self.cae.dprint("ResToSihot._prepare_res_xml() result: ", self.xml,
                        minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    def _sending_res_to_sihot(self, fld_vals):
        self._prepare_res_xml(fld_vals)

        err_msg, warn_msg = self._handle_error(fld_vals, self.send_to_server(response_parser=ResResponse(self.cae)))
        return err_msg, warn_msg

    def _handle_error(self, fld_vals, err_msg):
        warn_msg = ""
        if [frag for frag in self._warning_frags if frag in err_msg]:
            warn_msg = self.res_id_desc(fld_vals, err_msg, separator="\n")
            self._warning_msgs += "\n\n" + warn_msg
            err_msg = ""
        elif err_msg:
            assert fld_vals['ResGdsNo']
            assert fld_vals['ResGdsNo'] not in self._gds_errors
            self._gds_errors[fld_vals['ResGdsNo']] = (fld_vals, err_msg)
        return err_msg, warn_msg

    def _ensure_clients_exist_and_updated(self, fld_vals, ensure_client_mode):
        if ensure_client_mode == ECM_DO_NOT_SEND_CLIENT:
            return ""
        err_msg = ""

        # check main Occupant
        if fld_vals.get('AcId'):
            client = ClientToSihot(self.cae)
            err_msg = client.send_client_to_sihot(fld_vals)
            if not err_msg:
                # get client/occupant objid directly from client.response
                fld_vals['ShId'] = client.response.objid

        # check also Orderer but exclude OTAs like TCAG/TCRENT with a MATCHCODE that is no normal Acumen-CDREF
        if not err_msg and fld_vals.get('ResOrdererMc') and len(fld_vals['ResOrdererMc']) == 7:
            client = ClientToSihot(self.cae)
            err_msg = client.send_client_to_sihot(fld_vals)
            if not err_msg:
                # get orderer objid directly from client.response
                fld_vals['ResOrdererId'] = client.response.objid

        return "" if ensure_client_mode == ECM_TRY_AND_IGNORE_ERRORS else err_msg

    def send_res_to_sihot(self, fld_vals=None, ensure_client_mode=ECM_ENSURE_WITH_ERRORS):
        if not fld_vals:
            fld_vals = self.fields
        gds_no = fld_vals.get('ResGdsNo', '')
        if gds_no:
            if gds_no in self._gds_errors:    # prevent send of follow-up changes on erroneous bookings (w/ same GDS)
                old_id = self.res_id_desc(*self._gds_errors[gds_no], separator="\n")
                warn_msg = "\n\n" + "Synchronization skipped because GDS number {} had errors in previous send: {}" \
                           + "\nSkipped reservation: {}"
                self._warning_msgs += warn_msg.format(gds_no, old_id, self.res_id_desc(fld_vals, "", separator="\n"))
                return self._gds_errors[gds_no][1]    # return same error message

            err_msg = self._ensure_clients_exist_and_updated(fld_vals, ensure_client_mode)
            if not err_msg:
                err_msg, warn_msg = self._sending_res_to_sihot(fld_vals)
                if warn_msg:
                    self._warning_msgs += warn_msg
        else:
            err_msg = self.res_id_desc(fld_vals, "ResToSihot.send_res_to_sihot(): sync with empty GDS number skipped")

        if err_msg:
            self.cae.dprint("ResToSihot.send_res_to_sihot() error: {}".format(err_msg))
        else:
            self.cae.dprint("ResToSihot.send_res_to_sihot() GDSNO={} RESPONDED OBJID={} MATCHCODE={}"
                            .format(gds_no, self.response.objid, self.response.matchcode),
                            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg

    def send_res_recs_to_sihot(self, break_on_error=True):
        ret_msg = ""
        for fld_vals in self.recs:
            err_msg = self.send_res_to_sihot(fld_vals)
            if err_msg:
                if break_on_error:
                    return err_msg  # BREAK/RETURN first error message
                ret_msg += "\n" + err_msg
        return ret_msg

    def res_id_label(self):
        return "GDS/VOUCHER/CD/RO" + ("/RU/RUL" if self.debug_level else "")

    def res_id_values(self, fld_vals):
        return str(fld_vals.get('SIHOT_GDSNO')) + \
               "/" + str(fld_vals.get('RH_EXT_BOOK_REF')) + \
               "/" + str(fld_vals.get('CD_CODE')) + "/" + str(fld_vals.get('RUL_SIHOT_RATE')) + \
               ("/" + str(fld_vals.get('RUL_PRIMARY')) + "/" + str(fld_vals.get('RUL_CODE'))
                if self.debug_level and 'RUL_PRIMARY' in fld_vals and 'RUL_CODE' in fld_vals
                else "")

    def res_id_desc(self, fld_vals, error_msg, separator="\n\n"):
        indent = 8
        return fld_vals.get('ResAction', self.action) + " RESERVATION: " \
            + (fld_vals['ResArrival'].strftime('%d-%m') if fld_vals.get('ResArrival') else "unknown") + ".." \
            + (fld_vals['ResDeparture'].strftime('%d-%m-%y') if fld_vals.get('ResDeparture') else "unknown") \
            + " in " + (fld_vals['ResRoomNo'] + "=" if fld_vals.get('ResRoomNo') else "") \
            + str(fld_vals.get('ResRoomCat')) \
            + ("!" + fld_vals['ResPriceCat']
               if fld_vals.get('ResPriceCat') and fld_vals.get('ResPriceCat') != fld_vals.get('ResRoomCat') else "") \
            + " at hotel " + str(fld_vals.get('ResHotelId')) \
            + separator + " " * indent + self.res_id_label() + "==" + self.res_id_values(fld_vals) \
            + (separator + "\n".join(wrap("ERROR: " + _strip_err_msg(error_msg), subsequent_indent=" " * indent))
               if error_msg else "") \
            + (separator + "\n".join(wrap("TRAIL: " + fld_vals['RUL_CHANGES'], subsequent_indent=" " * indent))
               if fld_vals.get('RUL_CHANGES') else "")

    def get_warnings(self):
        return self._warning_msgs + "\n\nEnd_Of_Message\n" if self._warning_msgs else ""

    def wipe_warnings(self):
        self._warning_msgs = ""

    def wipe_gds_errors(self):
        self._gds_errors = dict()


class BulkFetcherBase:
    def __init__(self, cae, add_kernel_port=True):
        self.cae = cae
        self.add_kernel_port = add_kernel_port
        self.debug_level = None
        self.startup_date = cae.startup_beg.date()
        self.all_rows = None

    def add_options(self):
        add_sh_options(self.cae, add_kernel_port=self.add_kernel_port)

    def load_options(self):
        self.debug_level = self.cae.get_option('debugLevel')

    def print_options(self):
        print_sh_options(self.cae)


class GuestBulkFetcher(BulkFetcherBase):
    """
    WIP/NotUsed/NoTests: the problem is with GUEST-SEARCH is that there is no way to bulk fetch all guests
    because the search criteria is not providing range search for to split in slices. Fetching all 600k clients
    is resulting in a timeout error after 30 minutes (the Sihot interface 'shTimeout' option value)
    """
    def fetch_all(self):
        cae = self.cae
        self.all_rows = list()
        try:
            guest_search = GuestSearch(cae)
            search_criteria = dict(FLAGS='FIND-ALSO-DELETED-GUESTS', SORT='GUEST-NR')
            search_criteria['MAX-ELEMENTS'] = 600000
            # MATCH-SM (holding the Salesforce/SF client ID) is not available in Kernel GUEST-SEARCH (only GUEST-GET)
            self.all_rows = guest_search.search_guests(search_criteria, ['MATCHCODE', 'OBJID', 'MATCH-SM'])
        except Exception as ex:
            uprint(" ***  Sihot interface guest bulk fetch exception:", str(ex))
            print_exc()
            cae.shutdown(2130)

        return self.all_rows


class ResBulkFetcher(BulkFetcherBase):
    def __init__(self, cae, allow_future_arrivals=True):
        super(ResBulkFetcher, self).__init__(cae, add_kernel_port=False)

        self.allow_future_arrivals = allow_future_arrivals

        self.date_from = None
        self.date_till = None
        self.max_length_of_stay = None
        self.fetch_chunk_pause_seconds = None
        self.search_flags = None
        self.search_scope = None
        self.allowed_mkt_src = None
        self.allowed_mkt_grp = None

        self.adult_pers_types = None

    def add_options(self):
        super(ResBulkFetcher, self).add_options()
        self.cae.add_option('dateFrom', "Date of first arrival", self.startup_date - datetime.timedelta(days=1), 'F')
        self.cae.add_option('dateTill', "Date of last arrival", self.startup_date - datetime.timedelta(days=1), 'T')

    def load_options(self):
        super(ResBulkFetcher, self).load_options()

        cae = self.cae
        self.date_from = cae.get_option('dateFrom')
        self.date_till = cae.get_option('dateTill')
        if self.date_from > self.date_till:
            uprint("Specified date range is invalid - dateFrom({}) has to be before dateTill({})."
                   .format(self.date_from, self.date_till))
            cae.shutdown(3318)
        elif not self.allow_future_arrivals and self.date_till > self.startup_date:
            uprint("Future arrivals cannot be migrated - dateTill({}) has to be before {}.".format(self.date_till,
                                                                                                   self.startup_date))
            cae.shutdown(3319)

        # fetch given date range in chunks for to prevent timeouts and Sihot server blocking issues
        self.max_length_of_stay = min(max(1, cae.get_config('shFetchMaxDays', default_value=7)), 31)
        self.fetch_chunk_pause_seconds = cae.get_config('shFetchPauseSeconds', default_value=1)

        self.search_flags = cae.get_config('ResSearchFlags', default_value='ALL-HOTELS')
        self.search_scope = cae.get_config('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')

        self.allowed_mkt_src = cae.get_config('MarketSources', default_value=list())
        self.allowed_mkt_grp = cae.get_config('MarketGroups', default_value=list())

        self.adult_pers_types = cae.get_config('shAdultPersTypes')

    def print_options(self):
        super(ResBulkFetcher, self).print_options()

        uprint("Date range including check-ins from", self.date_from.strftime(SH_DATE_FORMAT),
               'and till/before', self.date_till.strftime(SH_DATE_FORMAT))
        uprint("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", self.max_length_of_stay,
               " and -pause in seconds between fetches", self.fetch_chunk_pause_seconds)
        uprint("Search flags:", self.search_flags)
        uprint("Search scope:", self.search_scope)
        uprint("Allowed Market Sources:", self.allowed_mkt_src or "ALL")
        uprint("Allowed Market Groups/Channels:", self.allowed_mkt_grp or "ALL")

    def date_range_str(self):
        from_date = self.date_from.strftime(SH_DATE_FORMAT)
        return "ON " + from_date if self.date_till != self.date_from else \
            ("BETWEEN" + from_date + " AND " + self.date_till.strftime(SH_DATE_FORMAT))

    def fetch_all(self):
        self.all_rows = res_search(self.cae, self.date_from, self.date_till,
                                   mkt_sources=self.allowed_mkt_src, mkt_groups=self.allowed_mkt_grp,
                                   max_los=self.max_length_of_stay,
                                   search_flags=self.search_flags, search_scope=self.search_scope,
                                   chunk_pause=self.fetch_chunk_pause_seconds)
        return self.all_rows


class ResSender(ResToSihot):
    @staticmethod
    def complete_res_data(rec):
        """
        complete reservation data row (rec) with the default values (specified in default_values underneath), while
        the following fields are mandatory:
            ResHotelId, ResArrival, ResDeparture, ResRoomCat, ResMktSegment, ResOrdererMc, ResGdsNo.

        :param rec:     reservation data Record instance.
        :return:        completed reservation data Record instance.

        These fields will not be completed/changed at all:
            ResRoomNo, ResNote, ResLongNote, ResFlightArrComment (flight no...), ResAllotmentNo, ResVoucherNo.

        optional fields:
            ResOrdererId (alternatively usable instead of matchcode value ResOrdererMc).
            ResAdult1Surname and ResAdult1Forename (surname and firstname)
            ResAdult2Surname and ResAdult2Forename ( ... )
        optional auto-populated fields (see default_values dict underneath).
        """
        default_values = dict(ResStatus='1',
                              AcId=rec['ResOrdererMc'].val() if 'ResOrdererMc' in rec else '',
                              ShId=rec['ResOrdererId'].val() if 'ResOrdererId' in rec else '',
                              ResAction=ACTION_INSERT,
                              ResBooked=datetime.datetime.today(),
                              ResPriceCat=rec['ResRoomCat'].val() if 'ResRoomCat' in rec else '',
                              ResBoard='RO',  # room only (no board/meal-plan)
                              ResAccount=1,
                              ResSource='A',
                              ResRateSegment=rec['ResMktSegment'].val() if 'ResMktSegment' in rec else '',
                              ResMktGroup='RS',
                              ResAdults=2,
                              ResChildren=0,
                              )
        for field_name, field_value in default_values.items():
            if field_name not in rec or not rec[field_name].val():
                rec.set_val(field_value, field_name)
        return rec

    def send_rec(self, rec):
        msg = ""
        rec = self.complete_res_data(rec)
        rec.push(SDI_SH)
        try:
            err = self.send_res_to_sihot(rec, ensure_client_mode=ECM_DO_NOT_SEND_CLIENT)
        except Exception as ex:
            err = "ResSender.send_rec() exception: {}".format(full_stack_trace(ex))
        if err:
            if err.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                msg = "Ignoring error sending res: " + str(rec)
                err = ""
            elif 'setDataRoom not available!' in err:  # was: 'A_Persons::setDataRoom not available!'
                err = "Apartment {} occupied between {} and {} - created GDS-No {} for manual allocation." \
                                .format(rec['ResRoomNo'], rec['ResArrival'].strftime('%d-%m-%Y'),
                                        rec['ResDeparture'].strftime('%d-%m-%Y'), rec['ResGdsNo']) \
                      + (" Original error: " + err if self.debug_level >= DEBUG_LEVEL_VERBOSE else "")
        elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
            msg = "Sent res: " + str(rec)
        return err, msg

    def get_res_no(self):
        return obj_id_to_res_no(self.cae, self.response.objid)
