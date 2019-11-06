# SIHOT high level interface (based on the low level interfaces provided by sys_core_sh)
import datetime
import time
from traceback import format_exc, print_exc
from copy import deepcopy
from textwrap import wrap
import pprint
from typing import Union, Tuple

from ae.core import DATE_ISO, DEBUG_LEVEL_ENABLED, full_stack_trace, parse_date
from ae.sys_data import (ACTION_INSERT, ACTION_UPDATE, ACTION_DELETE, ACTION_SEARCH, ACTION_BUILD,
                         FAT_IDX, FAD_FROM, FAD_ONTO, LIST_TYPES, ALL_FIELDS, CALLABLE_SUFFIX,
                         Record, Records, Value, get_current_index, compose_current_index, set_current_index,
                         field_name_idx_path)
from ae.sys_core_sh import (ResKernelGet, ResResponse, SihotXmlParser, SihotXmlBuilder,
                            SXML_DEF_ENCODING, ERR_MESSAGE_PREFIX_CONTINUE, SDI_SH, SDF_SH_KERNEL_PORT, SDF_SH_WEB_PORT,
                            SDF_SH_CLIENT_PORT, SDF_SH_TIMEOUT, SDF_SH_XML_ENCODING, SDF_SH_USE_KERNEL_FOR_CLIENT,
                            SDF_SH_USE_KERNEL_FOR_RES, SDF_SH_CLIENT_MAP, SDF_SH_RES_MAP)

from sys_data_ids import (FORE_SURNAME_SEP)

__version__ = '0.0.1'


SH_DATE_FORMAT = DATE_ISO

SH_RES_SUB_SEP = '/'

ELEM_PATH_SEP = '.'

ELEM_MISSING = "(missing)"
ELEM_EMPTY = "(empty)"

# ensure client modes (used by ResToSihot.send_res_to_sihot())
ECM_ENSURE_WITH_ERRORS = 0
ECM_TRY_AND_IGNORE_ERRORS = 1
ECM_DO_NOT_SEND_CLIENT = 2


ppf = pprint.PrettyPrinter(indent=12, width=96, depth=9).pformat


def convert_date_from_sh(xml_string):
    return parse_date(xml_string, ret_date=True) if xml_string else ''


def convert_date_onto_sh(date):
    return (date if isinstance(date, str) else datetime.date.strftime(date, DATE_ISO)) if date else ''


#  ELEMENT-FIELD-MAP-TUPLE-INDEXES  #################################
# mapping element name in tuple item [0] onto field name in [1], default field value in [2], hideIf callable in [3],
# .. from-converter in [4] and onto-converter in [5]
MTI_ELEM_NAME = 0
MTI_FLD_NAME = 1
MTI_FLD_VAL = 2
MTI_FLD_FILTER = 3
MTI_FLD_CNV_FROM = 4
MTI_FLD_CNV_ONTO = 5

# default map for ClientFromSihot.elem_fld_map instance and as read-only constant by AcuClientToSihot using the SIHOT
# .. KERNEL interface because SiHOT WEB V9 has missing fields: initials (CD_INIT1/2) and profession (CD_INDUSTRY1/2)
SH_CLIENT_MAP = \
    (
        ('OBJID', 'ShId', None,
         lambda f: f.ina(ACTION_INSERT) or not f.val()),
        ('MATCHCODE', 'AcuId'),
        ('T-SALUTATION', 'Salutation'),  # also exists T-ADDRESS/T-PERSONAL-SALUTATION
        ('T-TITLE', 'Title'),
        ('T-GUEST', 'GuestType', '1'),
        ('NAME-1', 'Surname'),
        ('NAME-2', 'Forename'),
        ('STREET', 'Street'),
        ('PO-BOX', 'POBox'),
        ('ZIP', 'Postal'),
        ('CITY', 'City'),
        ('T-COUNTRY-CODE', 'Country'),
        ('T-STATE', 'State', None,
         lambda f: not f.val()),
        ('T-LANGUAGE', 'Language'),
        ('T-NATION', 'Nationality', None,
         lambda f: not f.val()),
        ('COMMENT', 'Comment'),
        ('COMMUNICATION/', None, None,
         lambda f: f.ina(ACTION_SEARCH)),
        # both currency fields are greyed out in Sihot UI (can be sent but does not be returned by Kernel interface)
        # ('T-STANDARD-CURRENCY', 'Currency', None,     # alternatively use T-PROFORMA-CURRENCY
        # lambda f: not f.val()),
        ('PHONE-1', 'Phone'),
        ('PHONE-2', 'WorkPhone'),
        ('FAX-1', 'Fax'),
        ('EMAIL-1', 'Email'),
        ('EMAIL-2', 'EmailB'),
        ('MOBIL-1', 'MobilePhone'),
        ('MOBIL-2', 'MobilePhoneB'),
        ('/COMMUNICATION', None, None,
         lambda f: f.ina(ACTION_SEARCH)),
        ('ADD-DATA/', None, None,
         lambda f: f.ina(ACTION_SEARCH)),
        ('T-PERSON-GROUP', None, '1A'),
        ('D-BIRTHDAY', 'DOB', None,
         None, lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        # 27-09-17: removed b4 migration of BHH/HMC because CD_INDUSTRY1/2 needs first grouping into 3-alphanumeric code
        # ('T-PROFESSION', 'CD_INDUSTRY1'),
        ('INTERNET-PASSWORD', 'Password'),
        ('MATCH-ADM', 'RciId'),
        ('MATCH-SM', 'SfId'),
        ('/ADD-DATA', None, None,
         lambda f: f.ina(ACTION_SEARCH)),
        # uncomment/implement ExtRefs after Sihot allowing multiple identical TYPE values (e.g. for RCI)
        # ('L-EXTIDS/', None, None,
        #  lambda f: f.ina(ACTION_SEARCH)),
        # ('EXTID/', None, None,
        #  lambda f: not f.rfv('ExtRefs')),
        # ('EXTID' + ELEM_PATH_SEP + 'TYPE', ('ExtRefs', 0, 'Type'), None,
        #  lambda f: not f.rfv('ExtRefs') or not f.srv()),
        # ('EXTID' + ELEM_PATH_SEP + 'ID', ('ExtRefs', 0, 'Id'), None,
        #  lambda f: not f.rfv('ExtRefs') or not f.srv()),
        # ('/EXTID', None, None,
        #  lambda f: not f.rfv('ExtRefs')),
        # ('/L-EXTIDS', None, None,
        #  lambda f: f.ina(ACTION_SEARCH)),
    )

'''
SH_CLIENT_PARSE_MAP = \
    (
        ('EXT_REFS', 'ExtRefs'),  # only for elemHideIf expressions
        ('CDLREF', 'CDL_CODE'),
        # ('STATUS', 'CD_STATUS', 500),
        # ('PAF_STAT', 'CD_PAF_STATUS', 0),
    )
'''

# Reservation interface mappings
# .. first the mapping for the WEB interface
""" taken from SIHOT.WEB IF doc page 58:
    The first scope contains the following mandatory fields for all external systems and for SIHOT.PMS:

        <GDSNO>, <RT>, <ARR>, <DEP>, <LAST-MOD>, <CAT>, <NOPAX>, <NOCHILDS>, <NOROOMS>, <NAME> or <COMPANY>.

    With reservations from external systems is <PRICE-TOTAL> a mandatory field. With reservations for SIHOT.PMS,
    <MATCHCODE> and <PWD> are mandatory fields.
"""
SH_RES_MAP = \
    (
        ('SIHOT-Document' + ELEM_PATH_SEP + 'ID', 'ResHotelId'),  # [RES-]HOTEL/IDLIST/MANDATOR-NO/EXTERNAL-SYSTEM-ID
        ('ARESLIST/', ),
        ('RESERVATION/', ),
        # ### main reservation info: orderer, status, external booking references, room/price category, ...
        ('RESERVATION' + ELEM_PATH_SEP + 'RES-HOTEL', 'ResHotelId'),
        ('RESERVATION' + ELEM_PATH_SEP + 'RES-NR', 'ResId', None,
         lambda f: not f.val()),
        ('RESERVATION' + ELEM_PATH_SEP + 'SUB-NR', 'ResSubId', None,
         lambda f: not f.val()),
        ('RESERVATION' + ELEM_PATH_SEP + 'OBJID', 'ResObjId', None,
         lambda f: not f.val()),
        ('GDSNO', 'ResGdsNo'),
        # ('NN2', 'ResSfId', None,
        # lambda f: not f.val()),
        # MATCHCODE, NAME, COMPANY and GUEST-ID are mutually exclusive
        # MATCHCODE/GUEST-ID needed for DELETE action for to prevent Sihot error:
        # .. "Could not find a key identifier for the client (name, matchcode, ...)"
        # ('GUEST-ID', 'ShId', None,
        #  lambda f: not f.rfv('ShId')},
        ('RESERVATION' + ELEM_PATH_SEP + 'GUEST-ID', 'ShId'),   # , None, lambda f: not f.val()),
        # GUEST-OBJID used in SS/RES-SEARCH responses instead of GUEST-ID for parsing orderer - always hide in xml build
        ('RESERVATION' + ELEM_PATH_SEP + 'GUEST-OBJID', 'ShId'),
        ('RESERVATION' + ELEM_PATH_SEP + 'MATCHCODE', 'AcuId'),
        ('RESERVATION' + ELEM_PATH_SEP + 'NAME', 'Surname'),
        ('VOUCHERNUMBER', 'ResVoucherNo', None,
         lambda f: f.ina(ACTION_DELETE)),
        ('EXT-KEY', 'ResGroupNo', None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('FLAGS', None, 'IGNORE-OVERBOOKING'),  # ;NO-FALLBACK-TO-ERRONEOUS'),
        ('RT', 'ResStatus'),
        # ResRoomCat results in error 1011 for tk->TC/TK bookings with room move and room with higher/different room
        # .. cat, therefore use price category as room category for Thomas Cook Bookings.
        # .. similar problems we experienced when we added the RCI Allotments (here the CAT need to be the default cat)
        # .. on the 24-05-2018 so finally we replaced the category of the (maybe) allocated room with the cat that
        # .. get determined from the requested room size
        ('CAT', 'ResRoomCat'),  # needed for DELETE action
        ('PCAT', 'ResPriceCat', None,
         lambda f: f.ina(ACTION_DELETE)),
        ('ALLOTMENT-EXT-NO', 'ResAllotmentNo', '',
         lambda f: not f.val()),
        ('PAYMENT-INST', 'ResAccount', None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('SALES-DATE', 'ResBooked', None,
         lambda f: f.ina(ACTION_DELETE) or not f.val(),
         lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        ('RATE-SEGMENT', 'ResRateSegment', None,
         lambda f: not f.val(), ''),
        ('RATE/', None, None,               # default package/arrangement has also to be specified in ResPersons/PERSON
         lambda f: f.ina(ACTION_DELETE) or f.srv('ResRates', 0, 'RateAmount')),
        ('RATE' + ELEM_PATH_SEP + 'R', 'ResBoard', None,
         lambda f: f.ina(ACTION_DELETE) or f.srv('ResRates', 0, 'RateAmount')),
        ('RATE' + ELEM_PATH_SEP + 'ISDEFAULT', None, 'Y',
         lambda f: f.ina(ACTION_DELETE) or f.srv('ResRates', 0, 'RateAmount')),
        ('/RATE', None, None,
         lambda f: f.ina(ACTION_DELETE) or f.srv('ResRates', 0, 'RateAmount')),
        ('RATE/', None, None,               # alternative to previous default RATE section for to specify daily prices
         lambda f: f.ina(ACTION_DELETE) or not f.srv('ResRates', 0, 'RateAmount')),
        ('RATE' + ELEM_PATH_SEP + 'R', 'ResRateBoard', None,
         lambda f: f.ina(ACTION_DELETE) or not f.srv('ResRates', 0, 'RateAmount')),
        ('RATE' + ELEM_PATH_SEP + 'ISDEFAULT', None, 'Y',
         lambda f: f.ina(ACTION_DELETE) or not f.srv('ResRates', 0, 'RateAmount')),
        ('RATE' + ELEM_PATH_SEP + 'DAYS/', None, None,
         lambda f: f.ina(ACTION_DELETE) or not f.srv('ResRates', 0, 'RateAmount')),
        ('RATE' + ELEM_PATH_SEP + 'DAYS' + ELEM_PATH_SEP + 'D', ('ResRates', 0, 'RateDay'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.rfv('ResRates', f.crx(), 'RateAmount'),
         lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        ('RATE' + ELEM_PATH_SEP + 'DAYS' + ELEM_PATH_SEP + 'PRICE', ('ResRates', 0, 'RateAmount'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.rfv('ResRates', f.crx(), 'RateAmount')),
        ('RATE' + ELEM_PATH_SEP + '/DAYS', None, None,
         lambda f: f.ina(ACTION_DELETE) or not f.srv('ResRates', 0, 'RateAmount')),
        ('/RATE', None, None,
         lambda f: f.ina(ACTION_DELETE) or not f.srv('ResRates', 0, 'RateAmount')),
        ('RATE/', None, None,               # additional RATE section for external rental GSC package
         lambda f: f.ina(ACTION_DELETE) or f.rfv('ResMktSegment') not in ('ER', )),
        ('RATE' + ELEM_PATH_SEP + 'R', None, 'GSC',
         lambda f: f.ina(ACTION_DELETE) or f.rfv('ResMktSegment') not in ('ER', )),
        ('RATE' + ELEM_PATH_SEP + 'ISDEFAULT', None, 'N',
         lambda f: f.ina(ACTION_DELETE) or f.rfv('ResMktSegment') not in ('ER', )),
        ('/RATE', None, None,
         lambda f: f.ina(ACTION_DELETE) or f.rfv('ResMktSegment') not in ('ER', )),
        # The following fallback rate results in error Package TO not valid for hotel 1
        # ('RATE/', ),
        # ('R', 'RO_SIHOT_RATE'},
        # ('ISDEFAULT', None, 'N'),
        # ('/RATE', ),
        # ### Reservation Channels - used for assignment of reservation to a allotment or to board payment
        ('RESCHANNELLIST/', None, None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('OW', 'FB', 'RE', 'RI')),
        ('RESCHANNEL/', None, None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('OW', 'FB', 'RE', 'RI')),
        # needed for to add RCI booking to RCI allotment
        ('RESCHANNEL' + ELEM_PATH_SEP + 'IDX', None, 1,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('RE', 'RI')),
        ('RESCHANNEL' + ELEM_PATH_SEP + 'MATCHCODE', None, 'RCI',
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('RE', 'RI')),
        ('RESCHANNEL' + ELEM_PATH_SEP + 'ISPRICEOWNER', None, 1,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('RE', 'RI')),
        # needed for marketing fly buys for board payment bookings
        ('RESCHANNEL' + ELEM_PATH_SEP + 'IDX', None, 1,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') != 'FB'),
        ('RESCHANNEL' + ELEM_PATH_SEP + 'MATCHCODE', None, 'MAR01',
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') != 'FB'),
        ('RESCHANNEL' + ELEM_PATH_SEP + 'ISPRICEOWNER', None, 1,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') != 'FB'),
        # needed for owner bookings for to select/use owner allotment
        ('RESCHANNEL' + ELEM_PATH_SEP + 'IDX', None, 2,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') != 'OW'),
        ('RESCHANNEL' + ELEM_PATH_SEP + 'MATCHCODE', None, 'TSP',
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') != 'OW'),
        ('RESCHANNEL' + ELEM_PATH_SEP + 'ISPRICEOWNER', None, 1,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') != 'OW'),
        ('/RESCHANNEL', None, None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('OW', 'FB', 'RE', 'RI')),
        ('/RESCHANNELLIST', None, None,
         lambda f: not f.rfv('ResAllotmentNo') or f.rfv('ResMktGroup') not in ('OW', 'FB', 'RE', 'RI')),
        # ### GENERAL RESERVATION DATA: arrival/departure, pax, market sources, comments
        ('ARR', 'ResArrival', None,
         None,
         lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        ('DEP', 'ResDeparture', None,
         None,
         lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        ('NOROOMS', None, 1),     # mandatory field, also needed for DELETE action
        # ('NOPAX', None, None,   # needed for DELETE action
        #  lambda f: f.rfv('ResAdults') + f.rfv('ResChildren'), lambda f, v: int(v), lambda f, v: str(v)),
        ('NOPAX', 'ResAdults', None,          # NOPAX is sum of adults + children
         None,
         # converters: FROM-converter has to use system value because field value could still be unset by field.pull()
         # .. additional: NOCHILDS can be omitted in Sihot xml response - therefore use '0' as default
         # lambda f, v: int(v) if v else 2,
         lambda f, v: int(v) - int(f.srv('ResChildren', system=SDI_SH, direction=FAD_FROM) or '0') if v else 2,
         # lambda f, v: str(v + f.rfv('ResChildren'))),
         lambda f, v: str(v)),
        ('NOCHILDS', 'ResChildren', None,
         lambda f: f.ina(ACTION_DELETE),
         lambda f, v: int(v) if v else 0, lambda f, v: str(v)),
        ('TEC-COMMENT', 'ResLongNote', None,
         lambda f: f.ina(ACTION_DELETE)),
        ('COMMENT', 'ResNote', None,
         lambda f: f.ina(ACTION_DELETE)),
        # oc SS/RES-SEARCH have MARKETCODE and RES has MARKETCODE-NO element
        ('MARKETCODE-NO', 'ResMktSegment', None,
         lambda f: f.ina(ACTION_DELETE)),
        ('MARKETCODE', 'ResMktSegment'),
        # ('MEDIA', ),
        ('SOURCE', 'ResSource', None,
         lambda f: f.ina(ACTION_DELETE)),
        ('NN', 'ResMktGroupNN', None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('CHANNEL', 'ResMktGroup', None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('EXT-REFERENCE', 'ResFlightArrComment', None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),    # see also currently unused PICKUP-COMMENT-ARRIVAL element
        ('ARR-TIME', 'ResFlightETA'),
        ('PICKUP-TIME-ARRIVAL', 'ResFlightETA', None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PICKUP-TYPE-ARRIVAL', None, 1,                 # 1=car, 2=van
         lambda f: f.ina(ACTION_DELETE) or not f.rfv('ResFlightETA')),
        # ### PERSON/occupant details
        # ('PERS-TYPE-LIST/', ),
        # ('PERS-TYPE/', ),
        # ('TYPE', None, '1A'),
        # ('NO', 'ResAdults'),
        # ('/PERS-TYPE', ),
        # ('PERS-TYPE/', ),
        # ('TYPE', None, '2B'),
        # ('NO', 'ResChildren'),
        # ('/PERS-TYPE', ),
        # ('/PERS-TYPE-LIST', ),
        # Person Records - each rec also used as root rec for to upsert occupants as client (so FAT_CAL lambda has to
        # .. check also if the reservation data is available in PersSurname and TypeOfPerson!!!)
        ('PERSON/', None, None,
         lambda f: f.ina(ACTION_DELETE)),
        ('PERSON' + ELEM_PATH_SEP + 'GUEST-ID', ('ResPersons', 0, 'PersShId'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'MATCHCODE', ('ResPersons', 0, 'PersAcuId'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()
            or f.rfv('ResPersons', f.crx(), 'PersShId')),
        ('PERSON' + ELEM_PATH_SEP + 'NAME', ('ResPersons', 0, 'PersSurname'), None,
         lambda f: f.ina(ACTION_DELETE)
            or f.rfv('ResPersons', f.crx(), 'PersAcuId')
            or f.rfv('ResPersons', f.crx(), 'PersShId')),
        ('PERSON' + ELEM_PATH_SEP + 'NAME2', ('ResPersons', 0, 'PersForename'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()
            or f.rfv('ResPersons', f.crx(), 'PersAcuId') or f.rfv('ResPersons', f.crx(), 'PersShId')),
        ('PERSON' + ELEM_PATH_SEP + 'AUTO-GENERATED', ('ResPersons', 0, 'AutoGen'), '1',
         lambda f: f.ina(ACTION_DELETE)
            or f.rfv('ResPersons', f.crx(), 'PersAcuId')
            or f.rfv('ResPersons', f.crx(), 'PersShId')
            or f.rfv('ResPersons', f.crx(), 'PersSurname')
            or f.rfv('ResPersons', f.crx(), 'PersForename')),
        ('PERSON' + ELEM_PATH_SEP + 'ROOM-SEQ', ('ResPersons', 0, 'RoomSeq'), None,
         lambda f: f.ina(ACTION_DELETE)),
        ('PERSON' + ELEM_PATH_SEP + 'ROOM-PERS-SEQ', ('ResPersons', 0, 'RoomPersSeq'), None,
         lambda f: f.ina(ACTION_DELETE)),
        ('PERSON' + ELEM_PATH_SEP + 'PERS-TYPE', ('ResPersons', 0, 'TypeOfPerson'), None,
         lambda f: f.ina(ACTION_DELETE)),
        ('PERSON' + ELEM_PATH_SEP + 'RN', ('ResPersons', 0, 'RoomNo'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('ResDeparture') < datetime.date.today()),
        ('PERSON' + ELEM_PATH_SEP + 'DOB', ('ResPersons', 0, 'PersDOB'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val(),
         lambda f, v: convert_date_from_sh(v), lambda f, v: convert_date_onto_sh(v)),
        ('PERSON' + ELEM_PATH_SEP + 'COUNTRY-CODE', ('ResPersons', 0, 'PersCountry'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'EMAIL', ('ResPersons', 0, 'PersEmail'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'LANG', ('ResPersons', 0, 'PersLanguage'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'PHONE', ('ResPersons', 0, 'PersPhone'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'PERS-RATE' + ELEM_PATH_SEP + 'R', ('ResPersons', 0, 'Board'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'PICKUP-COMMENT-ARRIVAL', ('ResPersons', 0, 'FlightArrComment'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'PICKUP-TIME-ARRIVAL', ('ResPersons', 0, 'FlightETA'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'PICKUP-COMMENT-DEPARTURE', ('ResPersons', 0, 'FlightDepComment'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('PERSON' + ELEM_PATH_SEP + 'PICKUP-TIME-DEPARTURE', ('ResPersons', 0, 'FlightETD'), None,
         lambda f: f.ina(ACTION_DELETE) or not f.val()),
        ('/PERSON', None, None,
         lambda f: f.ina(ACTION_DELETE)),
        ('/RESERVATION',),
        ('/ARESLIST',),
    )

'''
MAP_PARSE_WEB_RES = \
    (   # ### EXTRA PARSING FIELDS (for to interpret reservation coming from the WEB interface)
        ('ACTION', 'ResAction'),
        ('STATUS', 'RU_STATUS'),
        ('RULREF', 'RUL_CODE'),
        ('RUL_PRIMARY', 'RUL_PRIMARY'),
        # ('RU_SIHOT_OBJID', 'RU_SIHOT_OBJID'),
        ('RU_SIHOT_OBJID', 'RUL_SIHOT_OBJID'),
        # ('RO_AGENCY_OBJID', 'RO_SIHOT_AGENCY_OBJID'),
        ('OC_CODE', 'AcuId'),
        ('OC_OBJID', 'ShId'),
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
'''

# default values for used interfaces (see email from Sascha Scheer from 28 Jul 2016 13:48 with answers from JBerger):
# .. use kernel for clients and web for reservations
USE_KERNEL_FOR_CLIENTS_DEF = True
USE_KERNEL_FOR_RES_DEF = False


def add_sh_options(cae, client_port=None, add_kernel_port=False, add_maps_and_kernel_usage=False):
    cae.add_opt('shServerIP', "IP address of the Sihot WEB/KERNEL server", 'localhost', 'i')
    cae.add_opt(SDF_SH_WEB_PORT, "IP port of the Sihot WEB interface", 14777, 'w')
    if client_port:
        # default is 14773 for Acumen and 14774 for the Sihot side (always the next higher port number)
        cae.add_opt(SDF_SH_CLIENT_PORT, "IP port of SXML interface of this server for Sihot", client_port, 'm')
    if add_kernel_port:
        # e.g. for GuestBulkFetcher we need also the kernel interface server port of Sihot
        cae.add_opt(SDF_SH_KERNEL_PORT, "IP port of the KERNEL interface of the Sihot server", 14772, 'k')
    cae.add_opt(SDF_SH_TIMEOUT, "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
    cae.add_opt(SDF_SH_XML_ENCODING, "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')
    if add_maps_and_kernel_usage:
        cae.add_opt(SDF_SH_USE_KERNEL_FOR_CLIENT, "Used interface for clients (0=web, 1=kernel)",
                    USE_KERNEL_FOR_CLIENTS_DEF, 'g', choices=(0, 1))
        cae.add_opt(SDF_SH_CLIENT_MAP, "Guest/Client mapping of xml to db items", SH_CLIENT_MAP, 'm')
        cae.add_opt(SDF_SH_USE_KERNEL_FOR_RES, "Used interface for reservations (0=web, 1=kernel)",
                    USE_KERNEL_FOR_RES_DEF, 'z', choices=(0, 1))
        cae.add_opt(SDF_SH_RES_MAP, "Reservation mapping of xml to db items", SH_RES_MAP, 'n')


def print_sh_options(cae):
    cae.po("Sihot server IP/WEB-interface-port:", cae.get_opt('shServerIP'), cae.get_opt(SDF_SH_WEB_PORT))
    client_port = cae.get_opt(SDF_SH_CLIENT_PORT)
    if client_port:
        ip_addr = cae.get_var('shClientIP', default_value=cae.get_opt('shServerIP'))
        cae.po("Sihot client IP/port for listening:", ip_addr, client_port)
    kernel_port = cae.get_opt(SDF_SH_KERNEL_PORT)
    if kernel_port:
        cae.po("Sihot server KERNEL-interface-port:", kernel_port)
    cae.po("Sihot TCP Timeout/XML Encoding:", cae.get_opt(SDF_SH_TIMEOUT), cae.get_opt(SDF_SH_XML_ENCODING))


def client_data(cae, obj_id):
    client_fetch = ClientFetch(cae)
    ret = client_fetch.fetch_client(obj_id)
    return ret


def complete_res_data(rec):
    """
    complete reservation data row (rec) with default values.

    :param rec:     reservation data Record instance.
    :return:        completed reservation data Record instance.

    un-changed fields:
        ResRoomNo, ResNote, ResLongNote, ResFlightArrComment (flight no...), ResAllotmentNo, ResVoucherNo.
    mandatory fields:
        ShId or AcuId or Surname (to specify the orderer of the reservation), ResHotelId, ResArrival, ResDeparture,
        ResRoomCat, ResMktSegment, ResGdsNo, ResAdults, ResChildren.
    optional fields:
        ResPersons0PersSurname and ResPersons0PersForename (surname and forename)
        ResPersons1PersSurname and ResPersons1PersForename ( ... )
    optional auto-populated fields:
        see the default values - specified in default_values dict underneath.
    """
    default_values = dict(ResStatus='1',
                          ResAction=ACTION_INSERT,
                          ResBooked=datetime.datetime.today(),
                          # removed for Nitesh SihotResImport:
                          # ResPriceCat=rec.val('ResRoomCat', system='', direction=''),
                          ResBoard='RO',  # room only (no board/meal-plan)
                          ResAccount='1',
                          ResSource='A',
                          ResRateSegment=rec.val('ResMktSegment', system='', direction=''),
                          ResMktGroup='RS',
                          ResAdults=2,
                          ResChildren=0,
                          )
    for field_name, field_value in default_values.items():
        if not rec.val(field_name, system='', direction='') and field_value not in ('', None):
            rec.set_val(field_value, field_name, system='', direction='')

    if 'ResSfId' in rec and not rec.val('ResSfId') and rec['ResGdsNo'].startswith('006'):
        rec.set_val(rec['ResGdsNo'], 'ResSfId', system='', direction='')

    if rec.val('ResPersons', system='', direction=''):
        adults = rec.val('ResAdults', system='', direction='')
        pax = adults + rec.val('ResChildren', system='', direction='')
        root_idx = ('ResPersons',)  # type: Tuple[Union[str, int]]
        recs = rec.value('ResPersons', flex_sys_dir=True)
        recs_len = len(recs)
        if recs_len > pax:
            for _ in range(recs_len - pax):  # remove invalid/surplus occupant recs
                recs.pop()
        elif recs_len < pax:
            for _ in range(pax - recs_len):  # add rec, copied from recs[0] and establish init/default field values
                recs.append_record(root_rec=rec, root_idx=root_idx)

        for pers_seq, occ_rec in enumerate(recs):
            rix = root_idx + (pers_seq,)

            if not occ_rec.val('RoomSeq', system='', direction=''):
                occ_rec.set_val('0', 'RoomSeq', system='', direction='', root_rec=rec, root_idx=rix)

            if not occ_rec.val('RoomPersSeq', system='', direction=''):
                occ_rec.set_val(str(pers_seq), 'RoomPersSeq', system='', direction='', root_rec=rec, root_idx=rix)

            if not occ_rec.val('TypeOfPerson', system='', direction=''):
                guest_type = '1A' if pers_seq < adults else '2B'
                occ_rec.set_val(guest_type, 'TypeOfPerson', system='', direction='', root_rec=rec, root_idx=rix)

            if not occ_rec.val('PersAcuId', system='', direction='') \
                    and not occ_rec.val('PersShId', system='', direction='') \
                    and not occ_rec.val('PersSurname', system='', direction='') \
                    and not occ_rec.val('PersForename', system='', direction=''):
                if pers_seq < adults:
                    name = "Adult " + str(pers_seq + 1)
                else:
                    name = "Child " + str(pers_seq - adults + 1)
                occ_rec.set_val(name, 'PersSurname', system='', direction='', root_rec=rec, root_idx=rix)
                auto_gen = '1'
            else:
                auto_gen = '0'
            occ_rec.set_val(auto_gen, 'AutoGen', system='', direction='', root_rec=rec, root_idx=rix)

            if not occ_rec.val('RoomNo', system='', direction=''):
                room_no = rec.val('ResRoomNo', system='', direction='')
                if room_no:
                    occ_rec.set_val(room_no, 'RoomNo', system='', direction='', root_rec=rec, root_idx=rix)

    return rec


def elem_path_join(elem_names):
    """
    convert list of element names to element path.
    :param elem_names:  list of element names.
    :return:            element path.
    """
    return ELEM_PATH_SEP.join(elem_names)


def hotel_and_res_id(shd):
    ho_id = shd.val('ResHotelId')
    res_nr = shd.val('ResId')
    sub_nr = shd.val('ResSubId')
    if not ho_id or not res_nr:
        return None, None
    return ho_id, res_nr + (SH_RES_SUB_SEP + sub_nr if sub_nr else '') + '@' + ho_id


def pax_count(shd):
    adults = shd.val('ResAdults')
    if not adults:
        adults = 0
    else:
        adults = int(adults)
    children = shd.val('ResChildren')
    if not children:
        children = 0
    else:
        children = int(children)
    return adults + children


def date_range_chunks(date_from, date_till, fetch_max_days):
    one_day = datetime.timedelta(days=1)
    add_days = datetime.timedelta(days=fetch_max_days) - one_day
    chunk_till = date_from - one_day
    while chunk_till < date_till:
        chunk_from = chunk_till + one_day
        chunk_till = min(chunk_from + add_days, date_till)
        yield chunk_from, chunk_till


def gds_no_to_ids(cae, hotel_id, gds_no):
    ids = dict(ResHotelId=hotel_id, ResGdsNo=gds_no)
    rfr = ResFetch(cae).fetch_by_gds_no(hotel_id, gds_no)
    if isinstance(rfr, Record):
        ids['ResObjId'] = rfr.val('ResObjId') or ''
        ids['ResId'] = rfr.val('ResId') or ''
        ids['ResSubId'] = rfr.val('ResSubId') or ''
        ids['ResSfId'] = rfr.val('ResSfId') or ''

    if not ids['ResSfId'] and gds_no.startswith('006'):
        ids['ResSfId'] = gds_no

    return ids


def gds_no_to_obj_id(cae, hotel_id, gds_no):
    return gds_no_to_ids(cae, hotel_id, gds_no).get('ResObjId')


def res_no_to_ids(cae, hotel_id, res_id, sub_id):
    ret = dict(ResHotelId=hotel_id, ResId=res_id, ResSubId=sub_id)
    rfr = ResFetch(cae).fetch_by_res_id(hotel_id, res_id, sub_id)
    if isinstance(rfr, Record):
        ret['ResObjId'] = rfr.val('ResObjId') or ''
        ret['ResGdsNo'] = rfr.val('ResGdsNo') or ''
        ret['ResSfId'] = rfr.val('ResSfId') or ''
        if not ret['ResSfId'] and ret['ResGdsNo'].startswith('006'):
            ret['ResSfId'] = ret['ResGdsNo']
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
    :return:                string with error message if error or Records/list of Sihot reservations (Record instances).
    """
    if not date_till:
        date_till = date_from

    err_msg = ""
    all_recs = Records()
    try:
        rs = ResSearch(cae)
        # the from/to date range filter of WEB ResSearch filters the arrival date only (not date range/departure)
        # adding flag ;WITH-PERSONS results in getting the whole reservation duplicated for each PAX in rooming list
        # adding scope NOORDERER prevents to include/use LANG/COUNTRY/NAME/EMAIL of orderer
        for chunk_beg, chunk_end in date_range_chunks(date_from, date_till, max_los):
            chunk_recs = rs.search_res(from_date=chunk_beg, to_date=chunk_end, flags=search_flags,
                                       scope=search_scope)
            if chunk_recs and isinstance(chunk_recs, str):
                err_msg = "Sihot.PMS reservation search error: {}".format(chunk_recs)
                break
            elif not chunk_recs or not isinstance(chunk_recs, list):
                err_msg = "Unspecified Sihot.PMS reservation search error"
                break
            cae.dpo(" ###  Fetched {} reservations from Sihot with arrivals between {} and {} - flags={}, scope={}"
                    .format(len(chunk_recs), chunk_beg, chunk_end, search_flags, search_scope),
                    minimum_debug_level=DEBUG_LEVEL_ENABLED)
            valid_recs = Records()
            for res_rec in chunk_recs:
                reasons = list()
                check_in = res_rec.val('ResArrival')
                check_out = res_rec.val('ResDeparture')
                if not check_in or not check_out:
                    reasons.append("incomplete check-in={} check-out={}".format(check_in, check_out))
                if not (date_from.toordinal() <= check_in.toordinal() <= date_till.toordinal()):
                    reasons.append("arrival {} not between {} and {}".format(check_in, date_from, date_till))
                mkt_src = res_rec.val('ResMktSegment')
                if mkt_sources and mkt_src not in mkt_sources:
                    reasons.append("disallowed market source {}".format(mkt_src))
                mkt_group = res_rec.val('ResMktGroup')
                if mkt_groups and mkt_group not in mkt_groups:
                    reasons.append("disallowed market group/channel {}".format(mkt_group))
                if reasons:
                    cae.dpo("  ##  Skipped Sihot reservation:", res_rec, " reason(s):", reasons)
                    continue
                valid_recs.append(res_rec)

            all_recs.extend(valid_recs)
            time.sleep(chunk_pause)
    except Exception as ex:
        err_msg = "Sihot interface reservation fetch exception: {}\n{}".format(ex, format_exc())

    return err_msg or all_recs


def obj_id_to_res_no(cae, obj_id):
    """
    using RESERVATION-GET oc from KERNEL interface (see 7.3 in SIHOT KERNEL interface doc).
    :param cae:         Console App Environment instance.
    :param obj_id:      Sihot Reservation Object Id.
    :return:            reservation ids as tuple of (hotel_id, res_id, sub_id, gds_no) or (None, "error") if not found
    """
    if not obj_id:
        return None, "obj_id_to_res_no() expects non-empty Sihot Reservation Object Id"
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


'''
class OldGuestSearchResponse(SihotXmlParser):
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
                                Sihot interface and defined within the used map (SH_CLIENT_MAP).
        :param key_elem_name:   element name used for the search (only needed if self._return_value_as_key==True).
        """
        super().__init__(cae)
        self._base_tags.append('GUEST-NR')
        self.guest_nr = None

        full_map = SH_CLIENT_MAP + SH_CLIENT_PARSE_MAP

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
        super().parse_xml(xml)
        self._key_elem_index = 0
        self._in_guest_profile = False

    def start(self, tag, attrib):
        if self._in_guest_profile:
            self._elem_fld_map_parser.start(tag, attrib)
        if super().start(tag, attrib) is None:
            return None  # processed by base class
        if tag == 'GUEST-PROFILE':
            self._key_elem_index += 1
            self._in_guest_profile = True
            return None
        return tag

    def data(self, data):
        if self._in_guest_profile:
            self._elem_fld_map_parser.data(data)
        if super().data(data) is None:
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
        return super().end(self._elem_fld_map_parser.end(tag))
'''


class FldMapXmlParser(SihotXmlParser):
    def __init__(self, cae, elem_map):
        super(FldMapXmlParser, self).__init__(cae)
        self._elem_map = elem_map
        self._collected_fields = list()
        self._current_data = ''
        self.elem_fld_map = None

        self._rec = None
        self.clear_rec()

    def clear_rec(self):
        # clear_leafs does clear also the copied rec from the last reservation, therefore simply recreate new template
        # self._rec.clear_leafs(system=self._rec.system, direction=self._rec.direction)
        # create field data parsing record and mapping dict for all elements having a field value
        self._rec = Record(system=SDI_SH, direction=FAD_FROM).add_system_fields(self._elem_map)
        self.elem_fld_map = self._rec.sys_name_field_map

        return self

    @property
    def rec(self):
        return self._rec

    # XMLParser interface

    def start(self, tag, attrib):
        super(FldMapXmlParser, self).start(tag, attrib)
        self._collected_fields = self._rec.collect_system_fields(self._elem_path, ELEM_PATH_SEP)
        if self._collected_fields:
            self._current_data = ''
            return None

        return tag

    def data(self, data):
        super(FldMapXmlParser, self).data(data)
        if self._collected_fields:
            self._current_data += data
            return None
        return data

    def end(self, tag):
        msg = "FldMapXmlParser.end({}) ".format(tag)
        for cf in self._collected_fields:
            idx_path = cf.root_idx(system=SDI_SH, direction=FAD_FROM)
            if idx_path:
                curr_idx = compose_current_index(self._rec, idx_path, Value((1, )))
                val = self._current_data
                # fix Sihot bug sending sometimes a value of 1 (greater 0) within ROOM-SEQ|ResPersons.<N>.RoomSeq
                if len(curr_idx) == 3 and curr_idx[2] == 'PERSON.ROOM-SEQ' and val != '0':
                    self.cae.dpo(msg + "auto-correction of {} RoomSeq value {!r} to '0'".format(curr_idx, val))
                    val = '0'
                self.cae.dpo(msg + "setting field {} to {!r}".format(curr_idx, val))
                self._rec.set_val(val, *curr_idx, system=SDI_SH, direction=FAD_FROM)
        self._collected_fields = list()

        for elem_name, *_ in self._elem_map:
            if elem_name == '/' + tag:
                self._rec.set_current_system_index(tag, ELEM_PATH_SEP)

        return super(FldMapXmlParser, self).end(tag)


class ClientFromSihot(FldMapXmlParser):
    def __init__(self, cae, elem_map=SH_CLIENT_MAP):
        super(ClientFromSihot, self).__init__(cae, elem_map)
        self.client_list = Records()

    # XMLParser interface

    def end(self, tag):
        if tag == 'GUEST-PROFILE':
            rec = self._rec.copy(deepness=-1)
            rec.pull(SDI_SH)
            self.client_list.append(rec)
            self.clear_rec()
        return super(ClientFromSihot, self).end(tag)


class ResFromSihot(FldMapXmlParser):
    def __init__(self, cae):
        super(ResFromSihot, self).__init__(cae, SH_RES_MAP)
        self.res_list = Records()

    # XMLParser interface

    def end(self, tag):
        if tag == 'RESERVATION':
            rec = complete_res_data(self._rec.copy(deepness=-1))
            rec.pull(SDI_SH)
            self.res_list.append(rec)
            self.clear_rec()
        return super(ResFromSihot, self).end(tag)


'''
class GuestSearchResponse(FldMapXmlParser):
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
                                Sihot interface and defined within the used map (SH_CLIENT_MAP).
        :param key_elem_name:   element name used for the search (only needed if self._return_value_as_key==True).
        """
        full_map = SH_CLIENT_MAP + SH_CLIENT_PARSE_MAP
        super().__init__(cae, full_map)
        self._base_tags.append('GUEST-NR')
        self.guest_nr = None

        if not ret_elem_names:
            ret_elem_names = [_[MTI_ELEM_NAME].strip('/') for _ in full_map]
        self._ret_elem_names = ret_elem_names    # list of names of XML-elements or response-base-attributes
        self._return_value_as_key = len(ret_elem_names) == 1 and ret_elem_names[0][0] == ':'
        self._key_elem_name = key_elem_name

        self.ret_elem_values = dict() if self._return_value_as_key else list()
        self._key_elem_index = 0

    def parse_xml(self, xml):
        super().parse_xml(xml)
        self._key_elem_index = 0

    def start(self, tag, attrib):
        if super().start(tag, attrib) is None:
            return None  # processed by base class
        if tag == 'GUEST-PROFILE':
            self._key_elem_index += 1
            return None
        return tag

    def data(self, data):
        if super().data(data) is None:
            return None  # processed by base class
        return data

    def end(self, tag):
        if tag == 'GUEST-PROFILE':
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
                        if elem in self.elem_fld_map:
                            field = self.elem_fld_map[elem]
                            values[elem] = getattr(self, elem_to_attr(elem),
                                                   field.val(system=SDI_SH, direction=FAD_FROM))
                    self.ret_elem_values.append(values)
        return super().end(tag)
'''


class ClientFetch(SihotXmlBuilder):
    def __init__(self, cae):
        super().__init__(cae, use_kernel=True)

    def fetch_client(self, obj_id, field_names=()):
        """ return Record with guest data OR str with error message in case of error.
        """
        self.beg_xml(operation_code='GUEST-GET')
        self.add_tag('GUEST-PROFILE', self.new_tag('OBJID', obj_id))
        self.end_xml()

        rec = None
        err_msg = self.send_to_server(response_parser=ClientFromSihot(self.cae))
        if err_msg or not self.response:
            err_msg = "fetch_client({}) error='{}'".format(obj_id, err_msg or "response is empty")
        elif self.response.client_list:
            recs = self.response.client_list
            if len(recs) > 1:
                self.cae.dpo("fetch_client({}): multiple clients found: {}".format(obj_id, recs),
                             minimum_debug_level=DEBUG_LEVEL_ENABLED)
            rec = recs[0].copy(deepness=2, filter_fields=lambda f: f.name() not in field_names if field_names else None)

        return err_msg or rec


class ClientSearch(SihotXmlBuilder):
    def __init__(self, cae):
        super().__init__(cae, use_kernel=True)

    def search_clients(self, matchcode='', exact_matchcode=True, name='', forename='', surname='',
                       guest_no='', email='', guest_type='', flags='FIND-ALSO-DELETED-GUESTS', order_by='', limit=0,
                       field_names=('ShId', ), **kwargs) -> Union[str, list, Records]:
        if kwargs:
            return "ClientSearch.search_clients() does not support the argument(s)=\n{}".format(ppf(kwargs))

        self.beg_xml(operation_code='GUEST-SEARCH')
        search_for = ""
        if matchcode:
            search_for += self.new_tag('MATCHCODE', matchcode)
            if exact_matchcode:
                flags += ';' + 'MATCH-EXACT-MATCHCODE'
        if name:
            forename, surname = name.split(FORE_SURNAME_SEP, maxsplit=1)
        if forename:
            search_for += self.new_tag('NAME-2', forename)
        if surname:
            search_for += self.new_tag('NAME-1', surname)

        if guest_no:    # agencies: 'OTS'=='31', 'SF'=='62', 'TCAG'=='12', 'TCRENT'=='19'
            search_for += self.new_tag('GUEST-NR', guest_no)
        if email:
            search_for += self.new_tag('EMAIL-1', email)
        if guest_type:
            search_for += self.new_tag('T-GUEST', guest_type)

        if flags:
            search_for += self.new_tag('FLAGS', flags)
        if order_by:    # e.g. 'GUEST-NR'
            search_for += self.new_tag('SORT', order_by)
        if limit:
            search_for += self.new_tag('MAX-ELEMENTS', limit)

        self.add_tag('GUEST-SEARCH-REQUEST', search_for)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ClientFromSihot(self.cae))
        if err_msg or not self.response:
            return "search_clients() error='{}';\nxml=\n{}\n".format(err_msg or "response not instantiated", self._xml)

        records = self.response.client_list
        if field_names:
            if len(field_names) == 1:
                records = [rec.val(field_names[0]) for rec in records]
            else:
                records = records.copy(deepness=2, filter_fields=lambda f: f.name() not in field_names)

        return records

    '''
    def search_clients_old(self, search_for, ret_elem_names, key_elem_name=None):
        """ return dict with search element/attribute value as the dict key if len(ret_elem_names)==1 and if
            ret_elem_names[0][0]==':' (in this case key_elem_name has to provide the search element/attribute name)
            OR return list of values if len(ret_elem_names) == 1
            OR return list of dict with ret_elem_names keys if len(ret_elem_names) >= 2
            OR return None in case of error.
        """
        msg = "ClientSearch.search_clients({}, {}, {})".format(search_for, ret_elem_names, key_elem_name)
        self.beg_xml(operation_code='GUEST-SEARCH')
        self.add_tag('GUEST-SEARCH-REQUEST', ''.join([self.new_tag(e, v) for e, v in search_for.items()]))
        self.end_xml()

        # rp = GuestSearchResponse(self.cae, ret_elem_names, key_elem_name=key_elem_name)
        rp = ClientFromSihot(self.cae)
        err_msg = self.send_to_server(response_parser=rp)
        if not err_msg and self.response:
            ret = self.response.ret_elem_values
            self.cae.dpo(msg + " xml='{}'; result={}".format(self.xml, ret))
        else:
            po(msg + " error: {}".format(err_msg))
            ret = None
        return ret
    '''

    def client_id_by_matchcode(self, matchcode):
        ids_or_err = self.search_clients(matchcode=matchcode)
        if isinstance(ids_or_err, str):
            return ids_or_err

        cnt = len(ids_or_err)
        if cnt > 1:
            self.cae.dpo("client_id_by_matchcode({}): multiple clients found".format(matchcode),
                         minimum_debug_level=DEBUG_LEVEL_ENABLED)
        if cnt:
            return ids_or_err[0]        # else RETURN None


class ResFetch(SihotXmlBuilder):
    def fetch_res(self, ho_id, gds_no=None, res_id=None, sub_id=None, scope='USEISODATE') -> Union[str, Record]:
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

        if err_msg or not self.response:
            err_msg = "fetch_res({}) error='{}'".format(self._xml, err_msg or "response is empty")
        elif len(self.response.res_list) > 1:
            self.cae.dpo("fetch_res({}): multiple reservations found".format(self._xml),
                         minimum_debug_level=DEBUG_LEVEL_ENABLED)

        return err_msg or self.response.res_list[0]

    def fetch_by_gds_no(self, ho_id, gds_no, scope='USEISODATE'):
        return self.fetch_res(ho_id, gds_no=gds_no, scope=scope)

    def fetch_by_res_id(self, ho_id, res_id, sub_id, scope='USEISODATE'):
        return self.fetch_res(ho_id, res_id=res_id, sub_id=sub_id, scope=scope)


class ResSearch(SihotXmlBuilder):
    def search_res(self, hotel_id=None, from_date=datetime.date.today(), to_date=datetime.date.today(),
                   matchcode=None, name=None, gds_no=None, flags='', scope=None, guest_id=None):
        self.beg_xml(operation_code='RES-SEARCH')
        if hotel_id:
            self.add_tag('ID', hotel_id)
        elif 'ALL-HOTELS' not in flags:
            flags += (';' if flags else '') + 'ALL-HOTELS'
        self.add_tag('FROM', datetime.date.strftime(from_date, DATE_ISO))  # mandatory?
        self.add_tag('TO', datetime.date.strftime(to_date, DATE_ISO))
        if matchcode:
            self.add_tag('MATCHCODE', matchcode)
        if name:
            self.add_tag('NAME', name)
        if gds_no:
            self.add_tag('GDSNO', gds_no)
        if flags:
            self.add_tag('FLAGS', flags if flags[0] != ';' else flags[1:])
        if scope:
            self.add_tag('SCOPE', scope)  # e.g. EXPORTEXTENDEDCOMMENT;FORCECALCDAYPRICE;CALCSUMDAYPRICE
        if guest_id:
            # ask Gubse to implement/fix guest_id search/filter option on RES-SEARCH operation of Sihot WEB interface.
            self.add_tag('CENTRAL-GUEST-ID', guest_id)  # this is not filtering nothing (tried GID)
        self.end_xml()

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
        err_msg = self.send_to_server(response_parser=ResFromSihot(self.cae))
        if err_msg or not self.response:
            err_msg = "search_res() error='{}';\nxml=\n{}".format(err_msg or "response is empty", self._xml)
        return err_msg or self.response.res_list


class FldMapXmlBuilder(SihotXmlBuilder):
    def __init__(self, cae, use_kernel=None, elem_map=None):
        super().__init__(cae, use_kernel=use_kernel)
        self.elem_map = deepcopy(elem_map or cae.get_opt(SDF_SH_RES_MAP))

        self.action = ''
        self._warning_frags = self.cae.get_var('warningFragments') or list()  # list of warning text fragments
        self._warning_msgs = list()

    def get_warnings(self):
        return "\n\n".join(self._warning_msgs) + "\n\nEnd_Of_Message\n" if self._warning_msgs else ""

    def wipe_warnings(self):
        self._warning_msgs = list()

    def prepare_rec(self, rec):
        ori_rec = rec.copy(deepness=-1)
        if rec.system != SDI_SH or rec.direction != FAD_ONTO:
            rec.set_env(system=SDI_SH, direction=FAD_ONTO)
            rec.add_system_fields(self.elem_map)
        rec.clear_leafs(reset_lists=False)     # reestablish default values - leave ResPersons occupants list untouched
        rec.merge_leafs(ori_rec)    # , extend=False)

    def prepare_map_xml(self, rec, include_empty_values=True):
        self.prepare_rec(rec)
        rec.push(SDI_SH)        # TODO: maybe REMOVE the other/1st push (2nd push could increment ResAdults value)
        rec.action = self.action or ACTION_BUILD

        recs = None
        inner_xml = ''
        map_i = group_i = -1
        indent = 0
        while True:
            map_i += 1
            if map_i >= len(self.elem_map):
                break

            elem_map_item = self.elem_map[map_i]
            tag = elem_map_item[MTI_ELEM_NAME]
            if ELEM_PATH_SEP in tag:
                tag = tag[tag.rfind(ELEM_PATH_SEP) + 1:]
            idx = elem_map_item[MTI_FLD_NAME] if len(elem_map_item) > MTI_FLD_NAME else None
            if idx:
                fld = rec.node_child(idx, use_curr_idx=Value((1, )))
                if fld is None:
                    fld = rec.node_child(idx)  # use template field
                    if fld is None:
                        continue        # skip xml creation for missing field (in current and template rec)
                field = fld
                idx_path = idx if isinstance(idx, (tuple, list)) else (field_name_idx_path(idx) or (idx, ))
                val = rec.val(*idx_path, system=SDI_SH, direction=FAD_ONTO, use_curr_idx=Value((1, )))
                filter_fields = field.filterer(system=SDI_SH, direction=FAD_ONTO)
                ''' finally not needed if clear_leafs() are called with reset_lists=False
                if not filter_fields and len(idx_path) >= 3 and isinstance(idx_path[1], int) and idx_path[1] > 0:
                    fld = rec.node_child(idx)  # use template field's filter if not in sub-records 2..n
                    filter_fields = fld.filter(system=SDI_SH, direction=FAD_ONTO)
                '''
            else:
                # field recycling has buggy side effects because last map item can refer to different/changed record:
                # if field is None:   # try to use field of last map item (especially for to get crx())
                field = next(iter(rec.values()))
                val = elem_map_item[MTI_FLD_VAL] if len(elem_map_item) > MTI_FLD_VAL else ''
                if callable(val):
                    val = val(field)
                filter_fields = elem_map_item[MTI_FLD_FILTER] if len(elem_map_item) > MTI_FLD_FILTER else None
            if filter_fields:
                assert callable(filter_fields), "filter aspect {} has to be a callable".format(filter_fields)
                if filter_fields(field):
                    continue

            if tag.endswith('/'):   # opening tag
                if not inner_xml.endswith("\n"):
                    inner_xml += "\n"
                inner_xml += " " * indent + self.new_tag(tag[:-1], closing=False)
                indent += 1
                if recs is None and map_i + 1 < len(self.elem_map):
                    nel = self.elem_map[map_i + 1]
                    if len(nel) > MTI_FLD_NAME and isinstance(nel[MTI_FLD_NAME], (tuple, list)):
                        root_field = rec.node_child((nel[MTI_FLD_NAME][0], ))
                        if root_field:
                            recs = root_field.value()
                            if isinstance(recs, LIST_TYPES):
                                set_current_index(recs, idx=recs.idx_min)
                                group_i = map_i - 1
                            else:
                                recs = None     # set to None also if recs is empty/False

            elif tag.startswith('/'):   # closing tag
                if inner_xml.endswith("\n"):
                    inner_xml += " " * indent
                inner_xml += self.new_tag(tag[1:], opening=False) + "\n"
                indent -= 1
                if recs:
                    if get_current_index(recs) >= len(recs) - 1:
                        recs = None
                    else:
                        set_current_index(recs, add=1)
                        map_i = group_i     # jump back to begin of xml group

            elif include_empty_values or val not in ('', None):
                inner_xml += self.new_tag(tag, self.convert_value_to_xml_string(val))

        return inner_xml


class ClientToSihot(FldMapXmlBuilder):
    def __init__(self, cae):
        super().__init__(cae,
                         use_kernel=cae.get_opt(SDF_SH_USE_KERNEL_FOR_CLIENT),
                         elem_map=cae.get_opt(SDF_SH_CLIENT_MAP) or SH_CLIENT_MAP)

    @staticmethod
    def _complete_client_data(rec):
        if not rec.val('GuestType', system='', direction=''):
            rec.set_val('1', 'GuestType', system='', direction='')

    def prepare_rec(self, rec):
        super().prepare_rec(rec)
        self._complete_client_data(rec)

    def _prepare_guest_xml(self, rec, fld_name_suffix=''):
        # if not self.action:
        self.action = ACTION_UPDATE if rec.val('ShId' + fld_name_suffix) else ACTION_INSERT
        self.beg_xml(operation_code='GUEST-CHANGE' if self.action == ACTION_UPDATE else 'GUEST-CREATE')
        self.add_tag('GUEST-PROFILE', self.prepare_map_xml(rec))
        self.end_xml()
        self.cae.dpo("ClientToSihot._prepare_guest_xml() action={} rec={}".format(self.action, rec))

    def _prepare_guest_link_xml(self, mc1, mc2):
        mct1 = self.new_tag('MATCHCODE-GUEST', self.convert_value_to_xml_string(mc1))
        mct2 = self.new_tag('CONTACT',
                            self.new_tag('MATCHCODE', self.convert_value_to_xml_string(mc2)) +
                            self.new_tag('FLAG', 'DELETE' if self.action == ACTION_DELETE else ''))
        self.beg_xml(operation_code='GUEST-CONTACT')
        self.add_tag('CONTACTLIST', mct1 + mct2)
        self.end_xml()
        self.cae.dpo("ClientToSihot._prepare_guest_link_xml(): mc1={} mc2={}".format(mc1, mc2))

    def _send_link_to_sihot(self, pk1, pk2):
        self._prepare_guest_link_xml(pk1, pk2)
        return self.send_to_server()

    def _send_person_to_sihot(self, rec, first_person=""):  # pass AcuId of first person for to send 2nd person
        self._prepare_guest_xml(rec, fld_name_suffix='_P' if first_person else '')
        err_msg = self.send_to_server()
        if 'guest exists already' in err_msg and self.action == ACTION_INSERT:
            self.action = ACTION_UPDATE
            self._prepare_guest_xml(rec, fld_name_suffix='_P' if first_person else '')
            err_msg = self.send_to_server()
        if not err_msg and self.response and self.response.objid and not rec.val('ShId'):
            rec.set_val(self.response.objid, 'ShId')
        return err_msg

    def send_client_to_sihot(self, rec):
        msg = "ClientToSihot.send_client_to_sihot({}): action={}".format(rec, self.action)
        err_msg = self._send_person_to_sihot(rec)
        if err_msg:
            self.cae.dpo(msg + "; err='{}'".format(err_msg), minimum_debug_level=DEBUG_LEVEL_ENABLED)
        else:
            self.cae.dpo(msg + "; client={} RESPONDED OBJID={} MATCHCODE={}"
                         .format(rec.val('AcuId'), self.response.objid, self.response.matchcode))

        return err_msg


class ResToSihot(FldMapXmlBuilder):
    def __init__(self, cae):
        super().__init__(cae,
                         use_kernel=cae.get_opt(SDF_SH_USE_KERNEL_FOR_RES),
                         elem_map=cae.get_var(SDF_SH_RES_MAP) or SH_RES_MAP)
        self._gds_errors = dict()
        self._in_error_handling = False

    def _add_sihot_configs(self, rec):
        mkt_seg = rec.val('ResMktSegment', system='', direction='')
        hotel_id = rec.val('ResHotelId', system='', direction='')
        arr_date = rec.val('ResArrival', system='', direction='')   # system/direction needed for to get date type
        today = datetime.datetime.today()
        cf = self.cae.get_var
        extra_comments = list()

        if self.action != ACTION_DELETE and rec.val('ResStatus', system='', direction='') != 'S':
            val = cf(mkt_seg + '_' + hotel_id, section='SihotResTypes',
                     default_value=cf(mkt_seg, section='SihotResTypes'))
            if val:
                if arr_date and arr_date.toordinal() > today.toordinal():
                    rec.set_val(val, 'ResStatus', system='', direction='')
                else:
                    extra_comments.append("RT={}".format(val))

        val = cf(mkt_seg + '_' + hotel_id, section='SihotAllotments',
                 default_value=cf(mkt_seg, section='SihotAllotments'))
        if val:
            if arr_date and arr_date.toordinal() > today.toordinal():
                rec.set_val(val, 'ResAllotmentNo', system='', direction='')
            else:   # Sihot doesn't accept allotment for reservations in the past
                extra_comments.append("AllotNo={}".format(val))

        # not specified? FYI: this field is not included in V_ACU_RES_DATA, default==RUL_SIHOT_RATE/SIHOT_MKT_SEG
        rate_seg = rec.val('ResRateSegment', system='', direction='') or mkt_seg
        val = cf(rate_seg, section='SihotRateSegments', default_value=rate_seg)
        if val != rate_seg or not rate_seg:
            rec.set_val(val, 'ResRateSegment', system='', direction='')

        val = cf(mkt_seg, section='SihotPaymentInstructions')
        if val:
            rec.set_val(val, 'ResAccount', system='', direction='')

        for comment in extra_comments:
            res_cmt = rec.val('ResComment', system='', direction='')
            if res_cmt and comment not in res_cmt:
                rec.set_val(comment + "; " + res_cmt, 'ResComment', system='', direction='')

    def prepare_rec(self, rec):
        super().prepare_rec(rec)

        self._add_sihot_configs(rec)
        complete_res_data(rec)

    def _prepare_res_xml(self, rec):
        self.action = rec.val('ResAction') or ACTION_INSERT
        inner_xml = self.prepare_map_xml(rec)
        if self.use_kernel_interface:
            if self.action == ACTION_INSERT:
                self.beg_xml(operation_code='RESERVATION-CREATE')
            else:
                self.beg_xml(operation_code='RESERVATION-DATA-CHANGE')
            self.add_tag('RESERVATION-PROFILE', inner_xml)
        else:
            self.beg_xml(operation_code='RES', add_inner_xml=inner_xml)
        self.end_xml()
        self.cae.dpo("ResToSihot._prepare_res_xml(): action={}; rec=\n{}".format(self.action, ppf(rec)))

    def _sending_res_to_sihot(self, rec):
        self._prepare_res_xml(rec)

        err_msg = self.send_to_server(response_parser=ResResponse(self.cae))
        if err_msg:
            err_msg = self._handle_error(rec, err_msg)
        if not err_msg:
            obj_id = rec.val('ResObjId')
            if not obj_id:
                rec.set_val(self.response.objid, 'ResObjId')
            elif obj_id != self.response.objid and self.response.objid:
                self._warning_msgs.append("ResObjId mismatch: {!r} != {!r}".format(obj_id, self.response.objid))
            res_id = rec.val('ResId')
            if not res_id:
                rec.set_val(self.response.res_nr, 'ResId')
            elif res_id != self.response.res_nr and self.response.res_nr:
                self._warning_msgs.append("ResId mismatch: {!r} != {!r}".format(res_id, self.response.res_nr))
            sub_id = rec.val('ResSubId')
            if not sub_id:
                rec.set_val(self.response.sub_nr, 'ResSubId')
            elif sub_id != self.response.sub_nr and self.response.sub_nr:
                self._warning_msgs.append("ResSubId mismatch: {!r} != {!r}".format(sub_id, self.response.sub_nr))

        return err_msg

    def _handle_error(self, rec, err_msg):
        msg = "##    ResToSihot._handle_error(): {}; data=" if self.debug_level >= DEBUG_LEVEL_ENABLED else "{}"
        msg += "\n{}".format(self.res_id_desc(rec, err_msg, separator="\n"))

        obj_id = rec.val('ResObjId')
        if [frag for frag in self._warning_frags if frag in err_msg]:
            self._warning_msgs.append(msg.format("reinterpreting Sihot interface error as warning"))
            err_msg = ""

        elif self._in_error_handling:
            self._warning_msgs.append(msg.format("skipping and ignoring this follow-up error"))
            err_msg = ""

        elif "Could not find a key identifier" in err_msg and (rec.val('ShId') or rec.val('ShId_P')):
            self.cae.dpo(msg.format("ignoring client obj-id {}/{}".format(rec.val('ShId'), rec.val('ShId_P'))),
                         minimum_debug_level=DEBUG_LEVEL_ENABLED)
            rec.set_val('ShId', '')             # use AcId/MATCHCODE instead
            rec.set_val('ShId_P', '')
            err_msg = self._sending_res_to_sihot(rec)

        elif ("A database error has occurred." in err_msg or 'Room not available!' in err_msg) and obj_id:
            self.cae.dpo(msg.format("resetting reservation with obj-id={}".format(obj_id)),
                         minimum_debug_level=DEBUG_LEVEL_ENABLED)
            try:
                self._in_error_handling = True      # prevent recursion in handling follow-up errors
                del_rec = rec.copy(deepness=-1)
                del_rec.set_env(system=SDI_SH, direction=FAD_ONTO)
                del_rec.set_val(ACTION_DELETE, 'ResAction')
                err_msg = self._sending_res_to_sihot(del_rec)
            except Exception as ex:
                err_msg = msg.format("Exception {} occurred in deletion of orphan res".format(ex))
            finally:
                self._in_error_handling = False
            self.cae.dpo("    .. orphan res deletion; obj-id={}; ignorable err?={}".format(obj_id, err_msg),
                         minimum_debug_level=DEBUG_LEVEL_ENABLED)
            rec['ResObjId'] = ''        # resend with wiped orphan/invalid obj_id, using ResHotelId+ResGdsNo instead
            err_msg = self._sending_res_to_sihot(rec)

        if err_msg:
            gds_no = rec.val('ResGdsNo')
            if gds_no in self._gds_errors:
                rec, last_msg = self._gds_errors[gds_no]
                err_msg = last_msg + "\n" + err_msg
            self._gds_errors[gds_no] = (rec, err_msg)

        return err_msg

    def _ensure_clients_exist_and_updated(self, rec, ensure_client_mode):
        if ensure_client_mode == ECM_DO_NOT_SEND_CLIENT:
            return ""
        err_msg = ""

        # check occupants that are already registered (having a client reference)
        sent_clients = list()
        if rec.val('ResPersons'):
            for occ_rec in rec.value('ResPersons', flex_sys_dir=True):
                if occ_rec.val('PersAcuId'):
                    client = ClientToSihot(self.cae)
                    crc = occ_rec.copy(deepness=-1,
                                       filter_fields=lambda f: not f.name().startswith('Pers'),
                                       fields_patches={ALL_FIELDS: {FAT_IDX + CALLABLE_SUFFIX: lambda f: f.name()[4:]}})
                    crc.set_env(system=SDI_SH, direction=FAD_ONTO)
                    err_msg = client.send_client_to_sihot(crc)
                    if err_msg:
                        break
                    sent_clients.append(crc.val('AcuId'))
                    if crc.val('ShId') and not rec.val('ShId') and crc.val('AcuId') == rec.val('AcuId'):
                        rec.set_val(crc.val('ShId'), 'ShId')     # pass new Guest Object Id to orderer

        # check also Orderer but exclude OTAs like TCAG/TCRENT with a MATCHCODE that is no normal Acumen-CDREF
        if not err_msg and rec.val('AcuId') and len(rec.val('AcuId')) == 7 and rec.val('AcuId') not in sent_clients:
            client = ClientToSihot(self.cae)
            err_msg = client.send_client_to_sihot(rec)

        return "" if ensure_client_mode == ECM_TRY_AND_IGNORE_ERRORS else err_msg

    def send_res_to_sihot(self, rec, ensure_client_mode=ECM_ENSURE_WITH_ERRORS):
        req_fields = ('ResHotelId', ('ResGdsNo', 'ResId', 'ResObjId'), 'ResMktSegment', 'ResRoomCat', 'ResArrival',
                      'ResDeparture')
        action = rec.val('ResAction')
        if action != ACTION_DELETE:
            # for reservations deleted within Acumen there will be no ShId/AcuId/Surname
            req_fields += (('ShId', 'AcuId', 'Surname'), )
        missing = rec.missing_fields(req_fields)
        if missing:
            return "ResToSihot.send_res_to_sihot() expects non-empty value in fields {}; rec=\n{}".format(missing, rec)

        err_msg = ""
        gds_no = rec.val('ResGdsNo')
        if gds_no:
            if gds_no in self._gds_errors:    # prevent send of follow-up changes on erroneous bookings (w/ same GDS)
                old_id = self.res_id_desc(*self._gds_errors[gds_no], separator="\n")
                self._warning_msgs.append("Sync skipped because GDS number {} had errors in previous send: {}"
                                          "\nres: {}".format(gds_no, old_id, self.res_id_desc(rec, "", separator="\n")))
                return self._gds_errors[gds_no][1]    # return same error message

            if action != ACTION_DELETE:
                err_msg = self._ensure_clients_exist_and_updated(rec, ensure_client_mode)
            if not err_msg:
                err_msg = self._sending_res_to_sihot(rec)
        else:
            err_msg = self.res_id_desc(rec, "ResToSihot.send_res_to_sihot(): sync with empty GDS number skipped")

        warn_msg = self.get_warnings()
        if err_msg:
            self.cae.po("ResToSihot.send_res_to_sihot() error={}; warnings={}".format(err_msg, warn_msg))
        else:
            self.cae.dpo("ResToSihot.send_res_to_sihot() GDSNO={} RESPONDED OBJID={} MATCHCODE={} warnings={}"
                         .format(gds_no, self.response.objid, self.response.matchcode, warn_msg))

        return err_msg

    @staticmethod
    def res_id_label():
        return "ResId+GDS+VOUCHER+CD+RO+Room"

    @staticmethod
    def res_id_values(rec):
        sh_res_id = str(rec.val('ResId')) or ''
        if sh_res_id:
            sh_sub_id = str(rec.val('ResSubId'))
            if sh_sub_id != '1':
                sh_res_id += "/" + sh_sub_id
        sh_res_id += "@"
        ret = sh_res_id + str(rec.val('ResHotelId')) + \
            "+" + str(rec.val('ResGdsNo')) + \
            "+" + str(rec.val('ResVoucherNo')) + \
            "+" + str(rec.val('AcuId')) + \
            "+" + str(rec.val('ResMktSegment')) + \
            "+" + str(rec.val('ResRoomNo'))
        return ret

    def res_id_desc(self, rec, err_msg, separator="\n\n", indent=8):
        arr = rec.val('ResArrival', system='', direction='')
        dep = rec.val('ResDeparture', system='', direction='')

        ret = self.action + " RESERVATION: " \
            + (arr.strftime('%d-%m') if arr else "unknown") + ".." \
            + (dep.strftime('%d-%m-%y') if dep else "unknown") \
            + " in " + (rec.val('ResRoomNo') + "=" if rec.val('ResRoomNo') else "") + rec.val('ResRoomCat') \
            + ("!" + rec.val('ResPriceCat')
               if rec.val('ResPriceCat') and rec.val('ResPriceCat') != rec.val('ResRoomCat') else "") \
            + " at hotel " + rec.val('ResHotelId') \
            + separator + " " * indent + self.res_id_label() + "==" + self.res_id_values(rec)

        if err_msg:
            ret += separator + "\n".join(wrap("ERROR: " + _strip_err_msg(err_msg), subsequent_indent=" " * indent))

        return ret

    def wipe_gds_errors(self):
        self._gds_errors = dict()


class BulkFetcherBase:
    def __init__(self, cae, add_kernel_port=True):
        self.cae = cae
        self.add_kernel_port = add_kernel_port
        self.debug_level = None
        self.startup_date = cae.startup_beg.date()
        self.all_recs = None

    def add_options(self):
        add_sh_options(self.cae, add_kernel_port=self.add_kernel_port)

    def load_options(self):
        self.debug_level = self.cae.get_opt('debugLevel')

    def print_options(self):
        print_sh_options(self.cae)


class GuestBulkFetcher(BulkFetcherBase):
    """
    WIP/NotUsed/NoTests: the problem is with GUEST-SEARCH is that there is no way to bulk fetch all guests
    because the search criteria is not providing range search for to split in slices. Fetching all 600k clients
    is resulting in a timeout error after 30 minutes (see Sihot interface SDF_SH_TIMEOUT/'shTimeout' option value)
    """
    def fetch_all(self):
        cae = self.cae
        self.all_recs = Records()
        try:
            # MATCH-SM (holding the Salesforce/SF client ID) is not available in Kernel GUEST-SEARCH (only GUEST-GET)
            self.all_recs = ClientSearch(cae).search_clients(order_by='GUEST-NR', limit=600000)
        except Exception as ex:
            cae.po(" ***  Sihot interface guest bulk fetch exception: {}".format(ex))
            print_exc()
            cae.shutdown(2130)

        return self.all_recs


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
        self.cae.add_opt('dateFrom', "Date of first arrival", self.startup_date - datetime.timedelta(days=1), 'F')
        self.cae.add_opt('dateTill', "Date of last arrival", self.startup_date - datetime.timedelta(days=1), 'T')

    def load_options(self):
        super(ResBulkFetcher, self).load_options()

        cae = self.cae
        self.date_from = cae.get_opt('dateFrom')
        self.date_till = cae.get_opt('dateTill')
        if self.date_from > self.date_till:
            cae.po("Specified date range is invalid - dateFrom({}) has to be before dateTill({})."
                   .format(self.date_from, self.date_till))
            cae.shutdown(3318)
        elif not self.allow_future_arrivals and self.date_till > self.startup_date:
            cae.po("Future arrivals cannot be migrated - dateTill({}) has to be before {}."
                   .format(self.date_till, self.startup_date))
            cae.shutdown(3319)

        # fetch given date range in chunks for to prevent timeouts and Sihot server blocking issues
        self.max_length_of_stay = min(max(1, cae.get_var('shFetchMaxDays', default_value=7)), 31)
        self.fetch_chunk_pause_seconds = cae.get_var('shFetchPauseSeconds', default_value=1)

        self.search_flags = cae.get_var('ResSearchFlags', default_value='ALL-HOTELS')
        self.search_scope = cae.get_var('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')

        self.allowed_mkt_src = cae.get_var('MarketSources', default_value=list())
        self.allowed_mkt_grp = cae.get_var('MarketGroups', default_value=list())

        self.adult_pers_types = cae.get_var('shAdultPersTypes')

    def print_options(self):
        super(ResBulkFetcher, self).print_options()

        cae = self.cae
        cae.po("Date range including check-ins from", self.date_from.strftime(SH_DATE_FORMAT),
               "and till/before", self.date_till.strftime(SH_DATE_FORMAT))
        cae.po("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", self.max_length_of_stay,
               " and -pause in seconds between fetches", self.fetch_chunk_pause_seconds)
        cae.po("Search flags:", self.search_flags)
        cae.po("Search scope:", self.search_scope)
        cae.po("Allowed Market Sources:", self.allowed_mkt_src or "ALL")
        cae.po("Allowed Market Groups/Channels:", self.allowed_mkt_grp or "ALL")

    def date_range_str(self):
        from_date = self.date_from.strftime(SH_DATE_FORMAT)
        return "ON " + from_date if self.date_till != self.date_from else \
            ("BETWEEN" + from_date + " AND " + self.date_till.strftime(SH_DATE_FORMAT))

    def fetch_all(self):
        self.all_recs = res_search(self.cae, self.date_from, self.date_till,
                                   mkt_sources=self.allowed_mkt_src, mkt_groups=self.allowed_mkt_grp,
                                   max_los=self.max_length_of_stay,
                                   search_flags=self.search_flags, search_scope=self.search_scope,
                                   chunk_pause=self.fetch_chunk_pause_seconds)
        return self.all_recs


class ResSender(ResToSihot):
    def send_rec(self, rec):
        msg = ""
        try:
            err = self.send_res_to_sihot(rec, ensure_client_mode=ECM_DO_NOT_SEND_CLIENT)
        except Exception as ex:
            err = "ResSender.send_rec() exception: {}".format(full_stack_trace(ex))
        if err:
            if err.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                msg = "Ignoring error '{}' in sending res-rec {}; WARNINGS={}".format(err, rec, self.get_warnings())
                err = ""
            elif 'setDataRoom not available!' in err:  # was: 'A_Persons::setDataRoom not available!'
                err = "Apartment {} occupied between {} and {} - created GDS-No {} for manual allocation." \
                    .format(rec.val('ResRoomNo'), rec.val('ResArrival'), rec.val('ResDeparture'), rec.val('ResGdsNo')) \
                      + (" Original error: {}; WARNINGS={}".format(err, self.get_warnings())
                         if self.debug_level >= DEBUG_LEVEL_ENABLED else "")
        elif self.debug_level >= DEBUG_LEVEL_ENABLED:
            msg = "Sent res: " + str(rec)
        warn_msg = self.get_warnings()
        if warn_msg:
            msg += "\nwarnings={}".format(warn_msg)
        return err, msg

    def get_res_no(self):
        return obj_id_to_res_no(self.cae, self.response.objid)
