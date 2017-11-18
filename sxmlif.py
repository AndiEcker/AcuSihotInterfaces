# SiHOT xml interface
import datetime
from copy import deepcopy
from textwrap import wrap

# import xml.etree.ElementTree as Et
from xml.etree.ElementTree import XMLParser, ParseError

# fix_encoding() needed for to clean and re-parse XML on invalid char code exception/error
from ae_console_app import fix_encoding, uprint, DEBUG_LEVEL_VERBOSE
from ae_tcp import TcpClient
from ae_db import OraDB, MAX_STRING_LENGTH

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

# SIHOT GUEST TYPE for investors/owners (affiliated company)
SIHOT_AFF_COMPANY = 6

# special error message prefixes
ERR_MESSAGE_PREFIX_CONTINUE = 'CONTINUE:'

# elemName prefix for column mappings that are parsed (*Parsed classes) but are not included into XML (*Builder classes)
PARSE_ONLY_TAG_PREFIX = '_'

# ensure client modes (used by ResToSihot.send_row_to_sihot())
ECM_ENSURE_WITH_ERRORS = 0
ECM_TRY_AND_IGNORE_ERRORS = 1
ECM_DO_NOT_SEND_CLIENT = 2


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


#  ELEMENT-COLUMN-MAPS  #################################

# used as WEB interface template for GuestFromSihot.elem_col_map instance and as read-only constant by ClientToSihot
# missing fields in SiHOT for initials (CD_INIT1/2) and profession (CD_INDUSTRY1/2 - only in WEB9 interface)
MAP_WEB_CLIENT = \
    (
        {'elemName': 'MATCHCODE', 'colName': 'CD_CODE'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_MATCHCODE', 'colName': 'CD_CODE2'},
        {'elemName': 'PWD', 'colName': 'CD_PASSWORD'},
        {'elemName': 'ADDRESS', 'colName': 'SIHOT_SALUTATION1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_ADDRESS', 'colName': 'SIHOT_SALUTATION2'},
        {'elemName': 'TITLE', 'colName': 'SIHOT_TITLE1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_TITLE', 'colName': 'SIHOT_TITLE2'},
        {'elemName': 'GUESTTYPE', 'colName': 'SIHOT_GUESTTYPE1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_GUESTTYPE', 'colName': 'SIHOT_GUESTTYPE2'},
        {'elemName': 'PERS-TYPE', 'colName': 'SH_PTYPE',
         'colValFromAcu': "'1A'"},
        {'elemName': 'NAME', 'colName': 'CD_SNAM1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_NAME', 'colName': 'CD_SNAM2'},
        {'elemName': 'NAME2', 'colName': 'CD_FNAM1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_NAME2', 'colName': 'CD_FNAM2'},
        {'elemName': 'DOB', 'colName': 'CD_DOB1',
         'valToAcuConverter': convert2date},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_DOB', 'colName': 'CD_DOB2',
         'valToAcuConverter': convert2date},
        {'elemName': 'STREET', 'colName': 'CD_ADD11'},
        {'elemName': 'POBOX', 'colName': 'CD_ADD12',
         'colValFromAcu': "nvl(CD_ADD12, CD_ADD13)"},
        {'elemName': 'ZIP', 'colName': 'CD_POSTAL'},
        {'elemName': 'CITY', 'colName': 'CD_CITY'},
        {'elemName': 'COUNTRY', 'colName': 'SIHOT_COUNTRY'},
        {'elemName': 'LANG', 'colName': 'SIHOT_LANG'},
        {'elemName': 'PHONE1', 'colName': 'CD_HTEL1'},
        {'elemName': 'PHONE2', 'colName': 'CD_WTEL1'},
        {'elemName': 'FAX1', 'colName': 'CD_FAX'},
        {'elemName': 'FAX2', 'colName': 'CD_WEXT1'},
        {'elemName': 'EMAIL1', 'colName': 'CD_EMAIL'},
        {'elemName': 'EMAIL2', 'colName': 'CD_SIGNUP_EMAIL'},
        {'elemName': 'MOBIL1', 'colName': 'CD_MOBILE1'},
        {'elemName': 'MOBIL2', 'colName': 'CD_LAST_SMS_TEL'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'CDLREF', 'colName': 'CDL_CODE'},
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'STATUS', 'colName': 'CD_STATUS', 'colValToAcu': 500},
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'PAF_STAT', 'colName': 'CD_PAF_STATUS', 'colValToAcu': 0},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'OBJID', 'colName': 'CD_SIHOT_OBJID'},
        # {'elemName': 'COMMENT', 'colName' : 'CD_'}
    )

# used as KERNEL interface element/column-mapping template by ClientToSihot instance
MAP_KERNEL_CLIENT = \
    (
        {'elemName': 'OBJID', 'colName': 'CD_SIHOT_OBJID', 'elemHideInActions': ACTION_INSERT},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_OBJID', 'colName': 'CD_SIHOT_OBJID2',
         'elemHideInActions': ACTION_INSERT},
        {'elemName': 'MATCHCODE', 'colName': 'CD_CODE'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_MATCHCODE', 'colName': 'CD_CODE2'},
        {'elemName': 'GUEST-NR', 'colName': 'SH_GUEST_NO',
         'colValFromAcu': "''",
         'elemHideIf': "'SH_GUEST_NO' not in c or not c['SH_GUEST_NO']"},   # for GUEST-SEARCH only
        {'elemName': 'FLAGS', 'colName': 'SH_FLAGS',
         'colValFromAcu': "''",
         'elemHideIf': "'SH_FLAGS' not in c or not c['SH_FLAGS']"},         # for GUEST-SEARCH only
        {'elemName': 'T-SALUTATION', 'colName': 'SIHOT_SALUTATION1'},  # also exists T-ADDRESS/T-PERSONAL-SALUTATION
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_T-SALUTATION', 'colName': 'SIHOT_SALUTATION2'},
        {'elemName': 'T-TITLE', 'colName': 'SIHOT_TITLE1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_T-TITLE', 'colName': 'SIHOT_TITLE2'},
        {'elemName': 'T-GUEST', 'colName': 'SIHOT_GUESTTYPE1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_T-GUEST', 'colName': 'SIHOT_GUESTTYPE2'},
        {'elemName': 'NAME-1', 'colName': 'CD_SNAM1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_NAME-1', 'colName': 'CD_SNAM2'},
        {'elemName': 'NAME-2', 'colName': 'CD_FNAM1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_NAME-2', 'colName': 'CD_FNAM2'},
        {'elemName': 'STREET', 'colName': 'CD_ADD11'},
        {'elemName': 'PO-BOX', 'colName': 'CD_ADD12',
         'colValFromAcu': "nvl(CD_ADD12, CD_ADD13)"},
        {'elemName': 'ZIP', 'colName': 'CD_POSTAL'},
        {'elemName': 'CITY', 'colName': 'CD_CITY'},
        {'elemName': 'T-COUNTRY-CODE', 'colName': 'SIHOT_COUNTRY'},
        {'elemName': 'T-STATE', 'colName': 'SIHOT_STATE',
         'colValFromAcu': "''",
         'elemHideIf': "'SIHOT_STATE' not in c or not c['SIHOT_STATE']"},
        {'elemName': 'T-LANGUAGE', 'colName': 'SIHOT_LANG'},
        {'elemName': 'COMMENT', 'colName': 'SH_COMMENT',
         'colValFromAcu': "SIHOT_GUEST_TYPE || ' ExtRefs=' || EXT_REFS"},
        {'elemName': 'COMMUNICATION/',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'PHONE-1', 'colName': 'CD_HTEL1'},
        {'elemName': 'PHONE-2', 'colName': 'CD_WTEL1'},
        {'elemName': 'FAX-1', 'colName': 'CD_FAX'},
        {'elemName': 'FAX-2', 'colName': 'CD_WEXT1'},
        {'elemName': 'EMAIL-1', 'colName': 'CD_EMAIL'},
        {'elemName': 'EMAIL-2', 'colName': 'CD_SIGNUP_EMAIL'},
        {'elemName': 'MOBIL-1', 'colName': 'CD_MOBILE1'},
        {'elemName': 'MOBIL-2', 'colName': 'CD_LAST_SMS_TEL'},
        {'elemName': '/COMMUNICATION',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'ADD-DATA/',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'T-PERSON-GROUP', 'colName': 'SH_PTYPE',
         'colValFromAcu': "'1A'"},
        {'elemName': 'D-BIRTHDAY', 'colName': 'CD_DOB1',
         'valToAcuConverter': convert2date},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_D-BIRTHDAY', 'colName': 'CD_DOB2',
         'valToAcuConverter': convert2date},
        # 27-09-17: removed b4 migration of BHH/HMC because CD_INDUSTRY1/2 needs first grouping into 3-alphanumeric code
        # {'elemName': 'T-PROFESSION', 'colName': 'CD_INDUSTRY1'},
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'P2_T-PROFESSION', 'colName': 'CD_INDUSTRY2'},
        {'elemName': 'INTERNET-PASSWORD', 'colName': 'CD_PASSWORD'},
        {'elemName': 'MATCH-ADM', 'colName': 'CD_RCI_REF'},
        {'elemName': 'MATCH-SM', 'colName': 'SIHOT_SF_ID'},
        {'elemName': '/ADD-DATA',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'L-EXTIDS/',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': 'EXTID/', 'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS']"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE1',
         'colValFromAcu': "substr(EXT_REFS, 1, instr(EXT_REFS, '=') - 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS']"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID1',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 1), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS']"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS']"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 1"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE2',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 2), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 1"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID2',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 2), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 1"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 1"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 2"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE3',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 3), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 2"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID3',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 3), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 2"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 2"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 3"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE4',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 4), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 3"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID4',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 4), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 3"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 3"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 4"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE5',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 5), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 4"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID5',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 5), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 4"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 4"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 5"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE6',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 6), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 5"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID6',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 6), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 5"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 5"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 6"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE7',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 7), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 6"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID7',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 7), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 6"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 6"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 7"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE8',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 8), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 7"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID8',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 8), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 7"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 7"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 8"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE9',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 9), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 8"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID9',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 9), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 8"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 8"},
        {'elemName': 'EXTID/',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 9"},
        {'elemName': 'TYPE', 'colName': 'EXT_REF_TYPE10',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 10), '[^=]+', 1, 1)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 9"},
        {'elemName': 'ID', 'colName': 'EXT_REF_ID10',
         'colValFromAcu': "regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 10), '[^=]+', 1, 2)",
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 9"},
        {'elemName': '/EXTID',
         'elemHideIf': "'EXT_REFS' not in c or not c['EXT_REFS'] or c['EXT_REFS'].count(',') < 9"},
        {'elemName': '/L-EXTIDS',
         'elemHideInActions': ACTION_SEARCH},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'EXT_REFS', 'colName': 'EXT_REFS'},  # only for elemHideIf expressions
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'CDLREF', 'colName': 'CDL_CODE'},
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'STATUS', 'colName': 'CD_STATUS', 'colValToAcu': 500},
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'PAF_STAT', 'colName': 'CD_PAF_STATUS', 'colValToAcu': 0},
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
        {'elemName': 'ID', 'colName': 'RUL_SIHOT_HOTEL'},  # or use [RES-]HOTEL/IDLIST/MANDATOR-NO/EXTERNAL-SYSTEM-ID
        {'elemName': 'ARESLIST/'},
        {'elemName': 'RESERVATION/'},
        # MATCHCODE, NAME, COMPANY and GUEST-ID are mutually exclusive
        # MATCHCODE/GUEST-ID needed for DELETE action for to prevent Sihot error:
        # .. "Could not find a key identifier for the client (name, matchcode, ...)"
        {'elemName': 'GUEST-ID', 'colName': 'SH_OBJID',
         'elemHideIf': "not c['OC_SIHOT_OBJID'] and ('CD_SIHOT_OBJID' not in c or not c['CD_SIHOT_OBJID'])",
         'colValFromAcu': "to_char(nvl(OC_SIHOT_OBJID, CD_SIHOT_OBJID))"},
        {'elemName': 'MATCHCODE', 'colName': 'SH_MC',
         'colValFromAcu': "nvl(OC_CODE, CD_CODE)"},
        {'elemName': 'GDSNO', 'colName': 'SIHOT_GDSNO',
         'colValFromAcu': "nvl(SIHOT_GDSNO, case when RUL_SIHOT_RATE in ('TC', 'TK') then"
                          " case when RUL_ACTION <> 'UPDATE' then"
                          " (select 'TC' || RH_EXT_BOOK_REF from T_RH where"
                          " RH_CODE = F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_RHREF'))"
                          " else '(lost)' end"
                          " else to_char(RUL_PRIMARY) end)"},  # RUL_PRIMARY needed for to delete/cancel res
        {'elemName': 'VOUCHERNUMBER', 'colName': 'RH_EXT_BOOK_REF', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'EXT-KEY', 'colName': 'SIHOT_LINK_GROUP', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'SIHOT_LINK_GROUP' not in c"},
        {'elemName': 'FLAGS', 'colVal': 'IGNORE-OVERBOOKING'},  # ;NO-FALLBACK-TO-ERRONEOUS'},
        {'elemName': 'RT', 'colName': 'SH_RES_TYPE',
         'colValFromAcu': "case when RUL_ACTION = 'DELETE' then 'S' else nvl(SIHOT_RES_TYPE, 'S') end"},
        # {'elemName': 'CAT', 'colName': 'RUL_SIHOT_CAT'},  # mandatory but could be empty (to get PMS fallback-default)
        #  'colValFromAcu': "'2TIC'"},   # mandatory but could be empty (to get PMS fallback-default)
        # RUL_SIHOT_CAT results in error 1011 for tk->TC/TK bookings with room move and room with higher/different room
        # .. cat, therefore use price category as room category for Thomas Cook Bookings.
        {'elemName': 'CAT', 'colName': 'RUL_SIHOT_CAT',  # needed for DELETE action
         'colValFromAcu': "case when RUL_SIHOT_RATE in ('TC', 'TK')"
                          " then F_SIHOT_CAT('RU' || RU_CODE) else RUL_SIHOT_CAT end"},
        {'elemName': 'PCAT', 'colName': 'SH_PRICE_CAT', 'elemHideInActions': ACTION_DELETE,
         'colValFromAcu': "F_SIHOT_CAT('RU' || RU_CODE)"},
        # {'elemName': 'PCAT', 'colName': 'SIHOT_CAT',
        #  'colValFromAcu': "'1TIC'"},
        {'elemName': 'ALLOTMENT-NO', 'colName': 'SIHOT_ALLOTMENT_NO', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c"},
        {'elemName': 'PAYMENT-INST', 'colName': 'SIHOT_PAYMENT_INST', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'SIHOT_PAYMENT_INST' not in c"},
        {'elemName': 'SALES-DATE', 'colName': 'RH_EXT_BOOK_DATE', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "not c['RH_EXT_BOOK_DATE']"},
        {'elemName': 'RATE-SEGMENT', 'colName': 'SIHOT_RATE_SEGMENT', 'colVal': '',
         'elemHideIf': "'SIHOT_RATE_SEGMENT' not in c"},    # e.g. TK/tk have defined rate segment in SIHOT - see cfg
        {'elemName': 'RATE/'},  # package/arrangement has also to be specified in PERSON:
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK'},
        {'elemName': 'ISDEFAULT', 'colVal': 'Y'},
        {'elemName': '/RATE'},
        {'elemName': 'RATE/', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RUL_SIHOT_RATE'] not in ('ER')"},
        {'elemName': 'R', 'colVal': 'GSC', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RUL_SIHOT_RATE'] not in ('ER')"},
        {'elemName': 'ISDEFAULT', 'colVal': 'N', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RUL_SIHOT_RATE'] not in ('ER')"},
        {'elemName': '/RATE', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RUL_SIHOT_RATE'] not in ('ER')"},
        # The following fallback rate results in error Package TO not valid for hotel 1
        # {'elemName': 'RATE/'},
        # {'elemName': 'R', 'colName': 'RO_SIHOT_RATE', 'colValFromAcu': "nvl(RO_SIHOT_RATE, RUL_SIHOT_RATE)"},
        # {'elemName': 'ISDEFAULT', 'colVal': 'N'},
        # {'elemName': '/RATE'},
        {'elemName': 'RESCHANNELLIST/',
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'][:5] not in ('Owner', 'Promo')"},
        {'elemName': 'RESCHANNEL/',
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'][:5] not in ('Owner', 'Promo')"},
        # needed for marketing fly buys for board payment bookings
        {'elemName': 'IDX', 'colVal': 1,
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'] not in ('Promo')"},
        {'elemName': 'MATCHCODE', 'colVal': 'MAR01',
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'] not in ('Promo')"},
        {'elemName': 'ISPRICEOWNER', 'colVal': 1,
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'] not in ('Promo')"},
        # needed for owner bookings for to select/use owner allotment
        {'elemName': 'IDX', 'colVal': 2,
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'] not in ('Owner')"},
        {'elemName': 'MATCHCODE', 'colVal': 'TSP',
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'] not in ('Owner')"},
        {'elemName': 'ISPRICEOWNER', 'colVal': 1,
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'] not in ('Owner')"},
        {'elemName': '/RESCHANNEL',
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'][:5] not in ('Owner', 'Promo')"},
        {'elemName': '/RESCHANNELLIST',
         'elemHideIf': "'SIHOT_ALLOTMENT_NO' not in c or not c['SIHOT_ALLOTMENT_NO']"
                       " or c['RO_RES_GROUP'][:5] not in ('Owner', 'Promo')"},
        {'elemName': 'ARR', 'colName': 'ARR_DATE',
         'colValFromAcu': "case when ARR_DATE is not NULL then ARR_DATE when RUL_ACTION <> 'UPDATE' then"
                          " to_date(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_FROM_DATE'),"
                          " 'DD-MM-YY') end"},
        {'elemName': 'DEP', 'colName': 'DEP_DATE',
         'colValFromAcu': "case when DEP_DATE is not NULL then DEP_DATE when RUL_ACTION <> 'UPDATE' then"
                          " to_date(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_FROM_DATE'),"
                          " 'DD-MM-YY') + "
                          "to_number(F_KEY_VAL(replace(replace(RUL_CHANGES, ' (', '='''), ')', ''''), 'RU_DAYS')) end"},
        {'elemName': 'NOROOMS', 'colName': 'SH_ROOMS', 'colVal': 1},  # needed for DELETE action
        {'elemName': 'NOPAX', 'colName': 'RU_ADULTS'},  # needed for DELETE action
        {'elemName': 'NOCHILDS', 'colName': 'RU_CHILDREN', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'TEC-COMMENT', 'colName': 'SIHOT_TEC_NOTE', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'COMMENT', 'colName': 'SIHOT_NOTE', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'MARKETCODE-NO', 'colName': 'RUL_SIHOT_RATE', 'elemHideInActions': ACTION_DELETE},
        # {'elemName': 'MEDIA'},
        {'elemName': 'SOURCE', 'colName': 'RU_SOURCE', 'elemHideInActions': ACTION_DELETE},
        {'elemName': 'NN', 'colName': 'RO_SIHOT_SP_GROUP', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'RO_SIHOT_SP_GROUP' not in c"},
        {'elemName': 'CHANNEL', 'colName': 'RO_SIHOT_RES_GROUP', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'RO_SIHOT_RES_GROUP' not in c"},
        # {'elemName': 'NN2', 'colName': 'RO_RES_CLASS'},  # other option using Mkt-CM_NAME (see Q_SIHOT_SETUP#L244)
        {'elemName': 'EXT-REFERENCE', 'colName': 'SH_EXT_REF', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'RU_FLIGHT_NO' not in c",
         'colValFromAcu': "trim(RU_FLIGHT_NO || ' ' || RU_FLIGHT_PICKUP || ' ' || RU_FLIGHT_AIRPORT)"},
        {'elemName': 'ARR-TIME', 'colName': 'RU_FLIGHT_LANDS', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'RU_FLIGHT_LANDS' not in c"},
        {'elemName': 'PICKUP-TIME-ARRIVAL', 'colName': 'RU_FLIGHT_LANDS', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "'RU_FLIGHT_LANDS' not in c or not c['RU_FLIGHT_PICKUP']"},
        {'elemName': 'PICKUP-TYPE-ARRIVAL', 'colVal': 1,  # 1=car, 2=van
         'elemHideIf': "'RU_FLIGHT_PICKUP' not in c or not c['RU_FLIGHT_PICKUP']"},
        {'elemName': 'PERS-TYPE-LIST/'},
        {'elemName': 'PERS-TYPE/'},
        {'elemName': 'TYPE', 'colVal': '1A'},
        {'elemName': 'NO', 'colName': 'RU_ADULTS'},
        {'elemName': '/PERS-TYPE'},
        {'elemName': 'PERS-TYPE/'},
        {'elemName': 'TYPE', 'colVal': '2B'},
        {'elemName': 'NO', 'colName': 'RU_CHILDREN'},
        {'elemName': '/PERS-TYPE'},
        {'elemName': '/PERS-TYPE-LIST'},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # First person/adult of reservation
         'elemHideIf': "c['RU_ADULTS'] <= 0"},
        {'elemName': 'NAME', 'colName': 'SH_ADULT1_NAME', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0 or 'SH_ADULT1_NAME' not in c or not c['SH_ADULT1_NAME']"},
        {'elemName': 'NAME2', 'colName': 'SH_ADULT1_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0 or 'SH_ADULT1_NAME2' not in c or not c['SH_ADULT1_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0 or 'SH_ADULT1_NAME' not in c or not c['SH_ADULT1_NAME']"
                       " or c['SH_ADULT1_NAME'][:5] == 'Adult'"},
        {'elemName': 'MATCHCODE', 'colName': 'CD_CODE', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0 or 'CD_CODE' not in c or c['CD_SIHOT_OBJID']"},
        {'elemName': 'GUEST-ID', 'colName': 'CD_SIHOT_OBJID', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0 or 'CD_SIHOT_OBJID' not in c or not c['CD_SIHOT_OBJID']"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ1', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ1', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0"},
        {'elemName': 'PERS-TYPE', 'colVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_ADULT1_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0 or 'SH_ADULT1_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 0"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Second adult of client
         'elemHideIf': "c['RU_ADULTS'] <= 1"},
        # NAME element needed for clients with only one person but reservation with 2nd pax (RU_ADULTS >= 2):
        # {'elemName': 'NAME', 'colName': 'SH_ADULT2_NAME', 'colVal': '',
        # 'elemHideIf': "c['RU_ADULTS'] <= 1 or 'SH_ADULT2_NAME' not in c or not c['SH_ADULT2_NAME']"},
        {'elemName': 'NAME', 'colName': 'SH_ADULT2_NAME', 'colVal': 'Adult 2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1 or ('CD_CODE2' in c and c['CD_CODE2'])"},
        {'elemName': 'NAME2', 'colName': 'SH_ADULT2_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1 or 'SH_ADULT2_NAME2' not in c or not c['SH_ADULT2_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1 or ('CD_CODE2' in c and c['CD_CODE2'])"},
        {'elemName': 'MATCHCODE', 'colName': 'CD_CODE2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1 or 'CD_CODE2' not in c or c['CD_SIHOT_OBJID2']"},
        {'elemName': 'GUEST-ID', 'colName': 'CD_SIHOT_OBJID2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1 or 'CD_SIHOT_OBJID2' not in c or not c['CD_SIHOT_OBJID2']"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ2', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ2', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1"},
        {'elemName': 'PERS-TYPE', 'colVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_ADULT2_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1 or 'SH_ADULT2_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 1"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Adult 3
         'elemHideIf': "c['RU_ADULTS'] <= 2"},
        {'elemName': 'NAME', 'colName': 'SH_ADULT3_NAME', 'colVal': 'Adult 3', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2"},
        {'elemName': 'NAME2', 'colName': 'SH_ADULT3_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2 or 'SH_ADULT3_NAME2' not in c or not c['SH_ADULT3_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ3', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ3', 'colVal': '2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2"},
        {'elemName': 'PERS-TYPE', 'colVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_ADULT3_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2 or 'SH_ADULT3_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 2"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Adult 4
         'elemHideIf': "c['RU_ADULTS'] <= 3"},
        {'elemName': 'NAME', 'colName': 'SH_ADULT4_NAME', 'colVal': 'Adult 4', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3"},
        {'elemName': 'NAME2', 'colName': 'SH_ADULT4_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3 or 'SH_ADULT4_NAME2' not in c or not c['SH_ADULT4_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ4', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ4', 'colVal': '3', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3"},
        {'elemName': 'PERS-TYPE', 'colVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_ADULT4_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3 or 'SH_ADULT4_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 3"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Adult 5
         'elemHideIf': "c['RU_ADULTS'] <= 4"},
        {'elemName': 'NAME', 'colName': 'SH_ADULT5_NAME', 'colVal': 'Adult 5', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4"},
        {'elemName': 'NAME2', 'colName': 'SH_ADULT5_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4 or 'SH_ADULT5_NAME2' not in c or not c['SH_ADULT5_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ5', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ5', 'colVal': '4', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4"},
        {'elemName': 'PERS-TYPE', 'colVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_ADULT5_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4 or 'SH_ADULT5_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 4"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Adult 6
         'elemHideIf': "c['RU_ADULTS'] <= 5"},
        {'elemName': 'NAME', 'colName': 'SH_ADULT6_NAME', 'colVal': 'Adult 6', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5"},
        {'elemName': 'NAME2', 'colName': 'SH_ADULT6_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5 or 'SH_ADULT6_NAME2' not in c or not c['SH_ADULT6_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ6', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ6', 'colVal': '5', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5"},
        {'elemName': 'PERS-TYPE', 'colVal': '1A', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_ADULT6_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5 or 'SH_ADULT6_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_ADULTS'] <= 5"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Children 1
         'elemHideIf': "c['RU_CHILDREN'] <= 0"},
        {'elemName': 'NAME', 'colName': 'SH_CHILD1_NAME', 'colVal': 'Child 1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0"},
        {'elemName': 'NAME2', 'colName': 'SH_CHILD1_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0 or 'SH_CHILD1_NAME2' not in c or not c['SH_CHILD1_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ11', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ11', 'colVal': '10', 'elemHideInActions': ACTION_DELETE,
         # 'colValFromAcu': "to_char(RU_ADULTS + 0)",  # commented out for optimization - RUNNING SEQ not needed
         'elemHideIf': "c['RU_CHILDREN'] <= 0"},
        {'elemName': 'PERS-TYPE', 'colVal': '2B', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_CHILD1_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0 or 'SH_CHILD1_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 0"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Children 2
         'elemHideIf': "c['RU_CHILDREN'] <= 1"},
        {'elemName': 'NAME', 'colName': 'SH_CHILD2_NAME', 'colVal': 'Child 2', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1"},
        {'elemName': 'NAME2', 'colName': 'SH_CHILD2_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1 or 'SH_CHILD2_NAME2' not in c or not c['SH_CHILD2_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ12', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ12', 'colVal': '11', 'elemHideInActions': ACTION_DELETE,
         # 'colValFromAcu': "to_char(RU_ADULTS + 1)",
         'elemHideIf': "c['RU_CHILDREN'] <= 1"},
        {'elemName': 'PERS-TYPE', 'colVal': '2B', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_CHILD2_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1 or 'SH_CHILD2_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 1"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Children 3
         'elemHideIf': "c['RU_CHILDREN'] <= 2"},
        {'elemName': 'NAME', 'colName': 'SH_CHILD3_NAME', 'colVal': 'Child 3', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2"},
        {'elemName': 'NAME2', 'colName': 'SH_CHILD3_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2 or 'SH_CHILD3_NAME2' not in c or not c['SH_CHILD3_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ13', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ13', 'colVal': '12', 'elemHideInActions': ACTION_DELETE,
         # 'colValFromAcu': "to_char(RU_ADULTS + 2)",
         'elemHideIf': "c['RU_CHILDREN'] <= 2"},
        {'elemName': 'PERS-TYPE', 'colVal': '2B', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_CHILD3_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2 or 'SH_CHILD3_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 2"},
        {'elemName': 'PERSON/', 'elemHideInActions': ACTION_DELETE,  # Children 4
         'elemHideIf': "c['RU_CHILDREN'] <= 3"},
        {'elemName': 'NAME', 'colName': 'SH_CHILD4_NAME', 'colVal': 'Child 4', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3"},
        {'elemName': 'NAME2', 'colName': 'SH_CHILD4_NAME2', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3 or 'SH_CHILD4_NAME2' not in c or not c['SH_CHILD4_NAME2']"},
        {'elemName': 'AUTO-GENERATED', 'colVal': '1', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3"},
        {'elemName': 'ROOM-SEQ', 'colName': 'SH_ROOM_SEQ14', 'colVal': '0', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3"},
        {'elemName': 'ROOM-PERS-SEQ', 'colName': 'SH_PERS_SEQ14', 'colVal': '13', 'elemHideInActions': ACTION_DELETE,
         # 'colValFromAcu': "to_char(RU_ADULTS + 3)",
         'elemHideIf': "c['RU_CHILDREN'] <= 3"},
        {'elemName': 'PERS-TYPE', 'colVal': '2B', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3"},
        {'elemName': 'R', 'colName': 'RUL_SIHOT_PACK', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3"},
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3 or 'RUL_SIHOT_ROOM' not in c or c['DEP_DATE'] < datetime.datetime.now()"},
        {'elemName': 'DOB', 'colName': 'SH_CHILD4_DOB', 'colVal': '', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3 or 'SH_CHILD4_DOB' not in c"},
        {'elemName': '/PERSON', 'elemHideInActions': ACTION_DELETE,
         'elemHideIf': "c['RU_CHILDREN'] <= 3"},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'ACTION', 'colName': 'RUL_ACTION'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'STATUS', 'colName': 'RU_STATUS'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RULREF', 'colName': 'RUL_CODE'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RUL_PRIMARY', 'colName': 'RUL_PRIMARY'},
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'RU_OBJID', 'colName': 'RU_SIHOT_OBJID'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RU_OBJID', 'colName': 'RUL_SIHOT_OBJID'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RU_FLIGHT_PICKUP', 'colName': 'RU_FLIGHT_PICKUP'},
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'RO_AGENCY_OBJID', 'colName': 'RO_SIHOT_AGENCY_OBJID'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'OC_CODE', 'colName': 'OC_CODE'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'OC_OBJID', 'colName': 'OC_SIHOT_OBJID'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RES_GROUP', 'colName': 'RO_RES_GROUP'},  # needed for elemHideIf
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RES_OCC', 'colName': 'RUL_SIHOT_RATE'},  # needed for res_id_values
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'CHANGES', 'colName': 'RUL_CHANGES'},  # needed for error notifications
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'LAST_HOTEL', 'colName': 'RUL_SIHOT_LAST_HOTEL'},  # needed for HOTMOVE
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'LAST_CAT', 'colName': 'RUL_SIHOT_LAST_CAT'},  # needed for HOTMOVE
        # column mappings needed only for parsing XML responses (using PARSE_ONLY_TAG_PREFIX)
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RES-HOTEL'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RES-NR'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'SUB-NR'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'OBJID'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'EMAIL'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'PHONE'},
        # PHONE1, MOBIL1 and EMAIL1 are only available in RES person scope/section but not in RES-SEARCH OC
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'PHONE1'},
        # {'elemName': PARSE_ONLY_TAG_PREFIX + 'MOBIL1'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'DEP-TIME'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'COUNTRY'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'CITY'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'STREET'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'LANG'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'MARKETCODE'},     # RES-SEARCH has no MARKETCODE-NO element/tag
        {'elemName': '/RESERVATION'},
        {'elemName': '/ARESLIST'},
    )

# .. then the mapping for the KERNEL interface
MAP_KERNEL_RES = \
    (
        {'elemName': 'OBJID', 'colName': 'RU_SIHOT_OBJID', 'elemHideInActions': ACTION_INSERT},
        {'elemName': 'ORDERER/', 'elemHideInActions': ACTION_UPDATE},
        {'elemName': 'GUEST-PROFILE/', 'elemHideInActions': ACTION_UPDATE},
        {'elemName': 'OBJID', 'colName': 'CD_SIHOT_OBJID', 'elemHideInActions': ACTION_UPDATE},
        {'elemName': '/GUEST-PROFILE', 'elemHideInActions': ACTION_UPDATE},
        {'elemName': '/ORDERER', 'elemHideInActions': ACTION_UPDATE},
        {'elemName': 'NR-ROOMS', 'colName': 'SH_NOROOMS', 'colVal': '1'},
        {'elemName': 'T-CATEGORY', 'colName': 'RUL_SIHOT_CAT'},  # mandatory, could be empty to get PMS fallback-default
        {'elemName': 'T-RATE', 'colName': 'RUL_SIHOT_RATE', 'colVal': 'OW'},
        {'elemName': 'ID', 'colName': 'RUL_SIHOT_HOTEL'},  # or use [RES-]HOTEL/IDLIST
        {'elemName': 'RN', 'colName': 'RUL_SIHOT_ROOM'},
        {'elemName': 'D-FROM', 'colName': 'ARR_DATE'},
        {'elemName': 'D-TO', 'colName': 'DEP_DATE'},
        {'elemName': 'NR-PERSONS', 'colName': 'SH_PAX',
         'colValFromAcu': "RU_ADULTS + RU_CHILDREN"},
        {'elemName': 'NOTE', 'colName': 'SIHOT_TEC_NOTE'},
        {'elemName': 'T-MARKET-SEGMENT', 'colName': 'RUL_SIHOT_RATE'},
        {'elemName': 'GDS-NR', 'colName': 'SH_GDSNO',  # EXT-REFERENCE or VOUCHERNUMBER are not mandatory
         'colValFromAcu': "'RU__' || RUL_PRIMARY"},
        {'elemName': 'VOUCHERNUMBER', 'colName': 'RH_EXT_BOOK_REF'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'ACTION', 'colName': 'RUL_ACTION'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'STATUS', 'colName': 'RU_STATUS', 'colValFromAcu': "nvl(RU_STATUS, 120)"},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'RULREF', 'colName': 'RUL_CODE'},
        {'elemName': PARSE_ONLY_TAG_PREFIX + 'CDREF', 'colName': 'CD_CODE'},
    )

# default values for used interfaces (see email from Sascha Scheer from 28 Jul 2016 13:48 with answers from JBerger):
# .. use kernel for clients and web for reservations
USE_KERNEL_FOR_CLIENTS_DEF = True
MAP_CLIENT_DEF = MAP_KERNEL_CLIENT

USE_KERNEL_FOR_RES_DEF = False
MAP_RES_DEF = MAP_WEB_RES


class SihotXmlParser:  # XMLParser interface
    def __init__(self, ca):
        super(SihotXmlParser, self).__init__()
        self._xml = ''
        self._base_tags = ['ERROR-LEVEL', 'ERROR-TEXT', 'ID', 'MSG', 'OC', 'ORG', 'RC', 'TN', 'VER']
        self._curr_tag = ''
        self._curr_attr = ''

        # main xml elements/items
        self.oc = ''
        self.tn = '0'
        self.id = '1'
        self.rc = '0'
        self.msg = ''
        self.ver = ''
        self.error_level = '0'  # used by kernel interface instead of RC/MSG
        self.error_text = ''
        self.ca = ca  # only needed for logging with dprint()
        self._parser = None  # reset to XMLParser(target=self) in self.parse_xml() and close in self.close()

    def parse_xml(self, xml):
        self.ca.dprint("SihotXmlParser.parse_xml():", xml, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
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
        if tag in self._base_tags:
            self._curr_attr = tag.lower().replace('-', '_')
            setattr(self, self._curr_attr, '')
            return None
        return tag

    def end(self, tag):  # called for each closing tag
        self._curr_tag = ''
        self._curr_attr = ''
        return tag

    def data(self, data):  # called on each chunk (separated by XMLParser on spaces, special chars, ...)
        if self._curr_attr and data.strip():
            self.ca.dprint("SihotXmlParser.data(): ", self._curr_tag, data, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            setattr(self, self._curr_attr, getattr(self, self._curr_attr) + data)
            return None
        return data

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
    def __init__(self, ca):
        super(RoomChange, self).__init__(ca)
        # add base tags for room/GDS number, old room/GDS number and guest objid
        self._base_tags.append('RN')
        self.rn = None  # added for to remove pycharm warning
        self._base_tags.append('ORN')
        self.orn = None
        self._base_tags.append('GDSNO')
        self.gdsno = None
        self._base_tags.append('OGDSNO')
        self.ogdsno = None
        self._base_tags.append('GID')
        self.gid = None


class Response(SihotXmlParser):  # response xml parser for kernel or web interfaces
    def __init__(self, ca):
        super(Response, self).__init__(ca)
        # web and kernel (guest/client) interface response elements
        self._base_tags.append('MATCHCODE')
        self.matchcode = None  # added for to remove pycharm warning
        # reservation interface response elements
        self._base_tags += ('OBJID', 'GDSNO')  # , 'RESERVATION ACCOUNT-ID')
        self.objid = None
        self.gdsno = None

    def start(self, tag, attrib):  # called for each opening tag
        if super(Response, self).start(tag, attrib) is None:
            return None  # processed by base class
        # collect extra info on error response (RC != '0') within the MSG tag field
        if tag[:4] in ('MSG-', "INDE", "VALU"):
            self._curr_attr = 'msg'
            # Q&D: by simply using tag[4:] for to remove MSG- prefix, INDEX will be shown as X= and VALUE as E=
            setattr(self, self._curr_attr, getattr(self, self._curr_attr, '') + " " + tag[4:] + "=")
            return None
        return tag


class AvailCatsResponse(Response):
    def __init__(self, ca):
        super(AvailCatsResponse, self).__init__(ca)
        self._curr_cat = None
        self._curr_day = None
        self.avail_room_cats = dict()

    def data(self, data):
        if super(AvailCatsResponse, self).data(data) is None:
            return None
        if self._curr_tag == 'CAT':
            self.avail_room_cats[data] = dict()
            self._curr_cat = data
        elif self._curr_tag == 'D':
            self._curr_day = data
        elif self._curr_tag == 'TOTAL':
            self.avail_room_cats[self._curr_cat][self._curr_day] = int(data)
        elif self._curr_tag == 'OOO':
            self.avail_room_cats[self._curr_cat][self._curr_day] -= int(data)
        elif self._curr_tag == 'OCC':
            self.avail_room_cats[self._curr_cat][self._curr_day] *= (1.0 - float(data) / 100.0)
        return data


class CatRoomResponse(Response):
    def __init__(self, ca):
        super(CatRoomResponse, self).__init__(ca)
        # guest/client interface response elements
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


class ConfigDictResponse(Response):
    def __init__(self, ca):
        super(ConfigDictResponse, self).__init__(ca)
        # guest/client interface response elements
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


class GuestSearchResponse(Response):
    def __init__(self, ca, ret_elem_names=None, key_elem_name=None):
        """ ret_elem_names is a list of xml element names (or response attributes) to return. If there is only one
             list element with a leading ':' character then self.ret_elem_values will be a dict with the search value
             as the key. If ret_elem_names consists of exact one item then ret_elem_values will be a list with the
             plain return values. If ret_elem_names contains more than one item then self.ret_elem_values will be
             a dict where the ret_elem_names are used as keys. If the ret_elem_names list is empty (or None) then the
             returned self.ret_elem_values list of dicts will provide all elements that are returned by the
             Sihot interface and defined within the used map (MAP_KERNEL_CLIENT).

            key_elem_name is the element name used for the search (only needed if self._return_value_as_key==True)
        """
        super(GuestSearchResponse, self).__init__(ca)
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
        self._col_map_parser = ColMapXmlParser(ca, deepcopy(MAP_KERNEL_CLIENT))

    def parse_xml(self, xml):
        super(GuestSearchResponse, self).parse_xml(xml)
        self._key_elem_index = 0
        self._in_guest_profile = False

    def start(self, tag, attrib):
        if self._in_guest_profile:
            self._col_map_parser.start(tag, attrib)
        if super(GuestSearchResponse, self).start(tag, attrib) is None:
            return None  # processed by base class
        if tag == 'GUEST-PROFILE':
            self._key_elem_index += 1
            self._in_guest_profile = True
            return None
        return tag

    def data(self, data):
        if self._in_guest_profile:
            self._col_map_parser.data(data)
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
                        elem = self._col_map_parser.elem_col_map[key]
                        elem_val = elem['elemListVal'] if 'elemListVal' in elem \
                            else (elem['elemVal'] if 'elemVal' in elem else None)
                        values[key] = getattr(self, key, elem_val)
                        # Q&D fix for search_agencies(): prevent to add elemListVal key/item in next run
                        if 'elemVal' in elem:
                            elem.pop('elemVal')
                    self.ret_elem_values.append(values)
        # for completeness call also SihotXmlParser.end() and ColMapXmlParser.end()
        return super(GuestSearchResponse, self).end(self._col_map_parser.end(tag))


class ColMapXmlParser(SihotXmlParser):
    def __init__(self, ca, col_map):
        # create mapping dict for all valid elements (excluding all starting with an underscore including _P2 elements)
        self.elem_col_map = {c['elemName']: c for c in deepcopy(col_map)}
        # if not c['elemName'].startswith(PARSE_ONLY_TAG_PREFIX) and 'colName' in c}
        super(ColMapXmlParser, self).__init__(ca)

    # XMLParser interface

    def start(self, tag, attrib):
        # if super(ColMapXmlParser, self).start(tag, attrib) is None:
        #    return None  # processed by base class
        super(ColMapXmlParser, self).start(tag, attrib)
        if tag not in self.elem_col_map and PARSE_ONLY_TAG_PREFIX + tag in self.elem_col_map:
            tag = PARSE_ONLY_TAG_PREFIX + tag
        if tag in self.elem_col_map:
            if 'elemListVal' in self.elem_col_map[tag]:
                self.elem_col_map[tag]['elemListVal'].append('')
            elif 'elemVal' in self.elem_col_map[tag]:  # 2nd time same tag then create list
                li = list([self.elem_col_map[tag]['elemVal'], ''])
                self.elem_col_map[tag]['elemListVal'] = li
            self.elem_col_map[tag]['elemVal'] = ''
            return None
        return tag

    def data(self, data):
        # if super(ColMapXmlParser, self).data(data) is None:
        #    return None  # already processed by base class
        super(ColMapXmlParser, self).data(data)
        tag = self._curr_tag
        if tag not in self.elem_col_map and PARSE_ONLY_TAG_PREFIX + tag in self.elem_col_map:
            tag = PARSE_ONLY_TAG_PREFIX + tag
        if tag in self.elem_col_map:
            self.elem_col_map[tag]['elemVal'] += data
            if 'elemListVal' in self.elem_col_map[tag]:
                # add string fragment to last list item
                self.elem_col_map[tag]['elemListVal'][-1] += data
            return None
        return data


class GuestFromSihot(ColMapXmlParser):
    def __init__(self, ca, col_map=MAP_CLIENT_DEF):
        super(GuestFromSihot, self).__init__(ca, col_map)
        self.acu_col_values = None  # dict() - initialized in self.end() with acu column names:values

    # XMLParser interface

    def end(self, tag):
        super(GuestFromSihot, self).end(tag)
        if tag == 'GUEST':  # using tag because self._curr_tag got reset by super method of end()
            self.ca.dprint("GuestFromSihot.end(): guest data parsed", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            self.acu_col_values = dict()
            for c in self.elem_col_map.keys():
                if 'elemVal' in self.elem_col_map[c] and self.elem_col_map[c]['elemVal']:
                    val = self.elem_col_map[c]['colValToAcu'] if 'colValToAcu' in self.elem_col_map[c] \
                        else self.elem_col_map[c]['elemVal']
                    col_name = self.elem_col_map[c]['colName']
                    if 'valToAcuConverter' in self.elem_col_map[c]:
                        self.acu_col_values[col_name] = self.elem_col_map[c]['valToAcuConverter'](val)
                    else:
                        self.acu_col_values[col_name] = val


class ResFromSihot(ColMapXmlParser):
    def __init__(self, ca, col_map=MAP_RES_DEF):
        super(ResFromSihot, self).__init__(ca, col_map)
        self.blank_elem_col_map = deepcopy(self.elem_col_map)
        self.res_list = list()

    # XMLParser interface

    def end(self, tag):
        super(ResFromSihot, self).end(tag)
        if tag == 'RESERVATION':  # using tag because self._curr_tag got reset by super method of end()
            if self.ca.get_option('debugLevel') >= DEBUG_LEVEL_VERBOSE:
                msg = list()
                for k in self.elem_col_map:
                    if 'elemListVal' in self.elem_col_map[k]:
                        msg.append(self.elem_col_map[k]['elemName'] + '=' + str(self.elem_col_map[k]['elemListVal']))
                    elif 'elemVal' in self.elem_col_map[k]:
                        msg.append(self.elem_col_map[k]['elemName'] + '=' + self.elem_col_map[k]['elemVal'])
                self.ca.dprint("ResFromSihot.end() reservation parsed:{}".format(",".join(msg)))
            self.res_list.append(deepcopy(self.elem_col_map))
            # reset elemVal and elemListVal for next reservation record in the same response
            self.elem_col_map = deepcopy(self.blank_elem_col_map)


class SihotXmlBuilder:
    tn = '1'

    def __init__(self, ca, col_map=(), use_kernel_interface=False, connect_to_acu=False):
        super(SihotXmlBuilder, self).__init__()
        self.ca = ca
        self.use_kernel_interface = use_kernel_interface
        col_map = deepcopy(col_map)
        self.sihot_elem_col = [(c['elemName'],
                                c['colName'] if 'colName' in c else None,
                                ((' or a in "' + c['elemHideInActions'] + '"' if 'elemHideInActions' in c else '')
                                 + (' or ' + c['elemHideIf'] if 'elemHideIf' in c else ''))[4:],
                                c['colVal'] if 'colVal' in c else None)
                               for c in col_map if not c['elemName'].startswith(PARSE_ONLY_TAG_PREFIX)]
        # self.fix_col_values = {c['colName']: c['colVal'] for c in col_map if 'colName' in c and 'colVal' in c}
        # acu_col_names and acu_col_expres need to be in sync
        # self.acu_col_names = [c['colName'] for c in col_map if 'colName' in c and 'colVal' not in c]
        # self.acu_col_expres = [c['colValFromAcu'] + " as " + c['colName'] if 'colValFromAcu' in c else c['colName']
        #                       for c in col_map if 'colName' in c and 'colVal' not in c]
        # alternative version preventing duplicate column names
        self.fix_col_values = dict()
        self.acu_col_names = list()  # acu_col_names and acu_col_expres need to be in sync
        self.acu_col_expres = list()
        for c in col_map:
            if 'colName' in c:
                if 'colVal' in c:
                    self.fix_col_values[c['colName']] = c['colVal']
                elif c['colName'] not in self.acu_col_names:
                    self.acu_col_names.append(c['colName'])
                    self.acu_col_expres.append(c['colValFromAcu'] + " as " + c['colName'] if 'colValFromAcu' in c
                                               else c['colName'])
        # mapping dicts between db column names and xml element names (not works for dup elems like MATCHCODE in RES)
        self.col_elem = {c['colName']: c['elemName'] for c in col_map if 'colName' in c and 'elemName' in c}
        self.elem_col = {c['elemName']: c['colName'] for c in col_map if 'colName' in c and 'elemName' in c}

        self.response = None

        self.acu_connected = False
        if connect_to_acu:
            self.ora_db = OraDB(ca.get_option('acuUser'), ca.get_option('acuPassword'), ca.get_option('acuDSN'),
                                debug_level=ca.get_option('debugLevel'))
            err_msg = self.ora_db.connect()
            if err_msg:
                uprint("SihotXmlBuilder.__init__() db connect error:", err_msg)
            else:
                self.acu_connected = connect_to_acu  # ==True
        self._rows = list()  # list of dicts, used by inheriting class for to store the rows to send to SiHOT.PMS
        self._current_row_i = 0

        self._xml = ''
        self._indent = 0

    def __del__(self):
        if self.acu_connected and self.ora_db:
            self.ora_db.close()

    # --- rows/cols helpers

    @property
    def cols(self):
        return self._rows[self._current_row_i] if len(self._rows) > self._current_row_i else dict()

    # def next_row(self): self._current_row_i += 1

    @property
    def row_count(self):
        return len(self._rows)

    @property
    def rows(self):
        return self._rows

    # --- database fetching

    def fetch_all_from_acu(self):
        self._rows = list()
        plain_rows = self.ora_db.fetch_all()
        for r in plain_rows:
            col_values = self.fix_col_values.copy()
            col_values.update(zip(self.acu_col_names, r))
            self._rows.append(col_values)
        self.ca.dprint("SihotXmlBuilder.fetch_all_from_acu() got {}, 1st row: {}"
                       .format(self.row_count, self.cols), minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    def beg_xml(self, operation_code, add_inner_xml='', transaction_number=''):
        self._xml = '<?xml version="1.0" encoding="' + self.ca.get_option('xmlEncoding').lower() + \
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

    def prepare_map_xml(self, col_values, action='', include_empty_values=True):
        inner_xml = ''
        for tag, col, hide_expr, val in self.sihot_elem_col:
            if hide_expr:
                local = dict()
                local['a'] = action  # provide short names for evaluation
                local['c'] = col_values
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
            elif include_empty_values or (col and col in col_values) or val:
                inner_xml += self.new_tag(tag, self.convert_value_to_xml_string(col_values[col]
                                                                                if col and col in col_values else val))
        return inner_xml

    def send_to_server(self, response_parser=None):
        sc = TcpClient(self.ca.get_option('serverIP'),
                       self.ca.get_option('serverKernelPort' if self.use_kernel_interface else 'serverPort'),
                       timeout=self.ca.get_option('timeout'),
                       encoding=self.ca.get_option('xmlEncoding'),
                       debug_level=self.ca.get_option('debugLevel'))
        self.ca.dprint("SihotXmlBuilder.send_to_server(): response_parser={}, xml={}".format(response_parser, self.xml),
                       minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        err_msg = sc.send_to_server(self.xml)
        if not err_msg:
            self.response = response_parser or Response(self.ca)
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
        self.ca.dprint('SihotXmlBuilder.xml-set:', value, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self._xml = value

    def _add_to_acumen_sync_log(self, table, primary, action, status, message, logref, commit=False):
        return self.ora_db.insert('T_SRSL',
                                  {'SRSL_TABLE': table[:6],
                                   'SRSL_PRIMARY': str(primary)[:12],
                                   'SRSL_ACTION': action[:15],
                                   'SRSL_STATUS': status[:12],
                                   'SRSL_MESSAGE': message[:MAX_STRING_LENGTH - 1],
                                   'SRSL_LOGREF': logref,  # NUMBER(10)
                                   },
                                  commit=commit)

    def _store_sihot_objid(self, table, pkey, response, col_name_suffix=""):
        obj_id = response.objid if str(response.objid) else '-' + (pkey[2:] if table == 'CD' else str(pkey))
        id_col = table + "_SIHOT_OBJID" + col_name_suffix
        pk_col = table + "_CODE"
        return self.ora_db.update('T_' + table, {id_col: obj_id}, pk_col + " = :pk", bind_vars=dict(pk=str(pkey)))


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


class AvailCats(SihotXmlBuilder):
    def avail_rooms(self, hotel_id='', room_cat='', from_date=datetime.date.today(), to_date=datetime.date.today(),
                    flags=''):  # SKIP-HIDDEN-ROOM-TYPES'):
        self.beg_xml(operation_code='CATINFO')
        if hotel_id:
            self.add_tag('ID', hotel_id)
        self.add_tag('FROM', datetime.date.strftime(from_date, '%Y-%m-%d'))     # mandatory
        self.add_tag('TO', datetime.date.strftime(to_date, '%Y-%m-%d'))
        if room_cat:
            self.add_tag('CAT', room_cat)
        if flags:
            self.add_tag('FLAGS', flags)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=AvailCatsResponse(self.ca))

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

        err_msg = self.send_to_server(response_parser=CatRoomResponse(self.ca))

        return err_msg or self.response.cat_rooms


class ClientToSihot(SihotXmlBuilder):
    def __init__(self, ca, use_kernel_interface=USE_KERNEL_FOR_CLIENTS_DEF, map_client=MAP_CLIENT_DEF,
                 connect_to_acu=True):
        super(ClientToSihot, self).__init__(ca, col_map=map_client, use_kernel_interface=use_kernel_interface,
                                            connect_to_acu=connect_to_acu)

    def _fetch_from_acu(self, view, acu_id=''):
        where_group_order = ''
        if acu_id:
            where_group_order += "CD_CODE " + ("like" if '_' in acu_id or '%' in acu_id else "=") + " '" + acu_id + "'"

        err_msg = self.ora_db.select(view, self.acu_col_expres, where_group_order)
        if not err_msg:
            self.fetch_all_from_acu()
        return err_msg

    # use for sync only not for migration because we have clients w/o log entries
    def fetch_from_acu_by_acu(self, acu_id=''):
        return self._fetch_from_acu('V_ACU_CD_UNSYNCED', acu_id=acu_id)

    # use for migration
    def fetch_all_valid_from_acu(self):
        return self._fetch_from_acu('V_ACU_CD_FILTERED')

    # use for unfiltered client fetches
    def fetch_from_acu_by_cd(self, acu_id):
        return self._fetch_from_acu('V_ACU_CD_UNFILTERED', acu_id=acu_id)

    def _prepare_guest_xml(self, c_row, action=None, col_name_suffix=''):
        if not action:
            action = ACTION_UPDATE if c_row['CD_SIHOT_OBJID' + col_name_suffix] else ACTION_INSERT
        self.beg_xml(operation_code='GUEST-CHANGE' if action == ACTION_UPDATE else 'GUEST-CREATE')
        self.add_tag('GUEST-PROFILE' if self.use_kernel_interface else 'GUEST',
                     self.prepare_map_xml(c_row, action))
        self.end_xml()
        self.ca.dprint("ClientToSihot._prepare_guest_xml() col_values/action/result: ",
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
        self.ca.dprint("ClientToSihot._prepare_guest_link_xml() mc1/mc2/result: ", mc1, mc2, self.xml,
                       minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    def _send_link_to_sihot(self, pk1, pk2, delete=False):
        self._prepare_guest_link_xml(pk1, pk2, delete)
        return self.send_to_server()

    def _send_person_to_sihot(self, c_row, first_person=""):  # pass CD_CODE of first person for to send 2nd person
        action = self._prepare_guest_xml(c_row, col_name_suffix='2' if first_person else '')
        err_msg = self.send_to_server()
        if 'guest exists already' in err_msg and action == ACTION_INSERT:  # and not self.use_kernel_interface:
            action = ACTION_UPDATE
            self._prepare_guest_xml(c_row, action=action, col_name_suffix='2' if first_person else '')
            err_msg = self.send_to_server()
        if not err_msg and self.acu_connected and self.response:
            err_msg = self._store_sihot_objid('CD', first_person or c_row['CD_CODE'], self.response,
                                              col_name_suffix="2" if first_person else "")
        return err_msg, action

    def send_client_to_sihot(self, c_row=None, commit=False):
        if not c_row:
            c_row = self.cols
        err_msg, action_p1 = self._send_person_to_sihot(c_row)
        couple_linkage = ''  # flag for logging if second person got linked (+P2) or unlinked (-P2)
        action_p2 = ''
        if not err_msg and 'CD_CODE2' in c_row and c_row['CD_CODE2']:  # check for second contact person
            crow2 = deepcopy(c_row)
            for col_name in c_row.keys():
                elem_name = PARSE_ONLY_TAG_PREFIX + 'P2_' + self.col_elem[col_name]
                if elem_name in self.elem_col:
                    crow2[col_name] = c_row[self.elem_col[elem_name]]
            err_msg, action_p2 = self._send_person_to_sihot(crow2, c_row['CD_CODE'])
            if not err_msg and action_p2 == ACTION_INSERT and c_row['SIHOT_GUESTTYPE1'] == SIHOT_AFF_COMPANY \
                    and not self.use_kernel_interface:  # only link owners/investors
                couple_linkage = '=P2'
                err_msg = self._send_link_to_sihot(c_row['CD_CODE'], c_row['CD_CODE2'])
            else:
                couple_linkage = '+P2'
        elif not err_msg and action_p1 == ACTION_INSERT and c_row['SIHOT_GUESTTYPE1'] == SIHOT_AFF_COMPANY \
                and not self.use_kernel_interface:
            # unlink second person if no longer exists in Acumen
            couple_linkage = '-P2'
            err_msg = self._send_link_to_sihot(c_row['CD_CODE'], '', delete=True)
        action = action_p1 + ('/' + action_p2 if action_p2 else '')

        if self.acu_connected:
            log_err = self._add_to_acumen_sync_log('CD', c_row['CD_CODE'],
                                                   action,
                                                   'ERR' + (self.response.server_error() if self.response else '')
                                                   if err_msg else 'SYNCED' + couple_linkage,
                                                   err_msg,
                                                   c_row.get('CDL_CODE', -966) or -969,
                                                   commit=commit)
            if log_err:
                err_msg += "\nLogErr=" + log_err

        if err_msg:
            self.ca.dprint("ClientToSihot.send_client_to_sihot() row|action p1/2|err: ", c_row, action, err_msg)
        else:
            self.ca.dprint("ClientToSihot.send_client_to_sihot() client={} RESPONDED OBJID={}/MATCHCODE={}"
                           .format(c_row['CD_CODE'], self.response.objid, self.response.matchcode),
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg


class ConfigDict(SihotXmlBuilder):
    def get_key_values(self, config_type, hotel_id='1', language='EN'):
        self.beg_xml(operation_code='GCF')
        self.add_tag('CFTYPE', config_type)
        self.add_tag('HN', hotel_id)  # mandatory
        self.add_tag('LN', language)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ConfigDictResponse(self.ca))

        return err_msg or self.response.key_values


class GuestSearch(SihotXmlBuilder):
    def __init__(self, ca):
        super(GuestSearch, self).__init__(ca, col_map=MAP_KERNEL_CLIENT, use_kernel_interface=True)

    def get_guest(self, obj_id):
        """ return dict with guest data OR None in case of error
        """
        self.beg_xml(operation_code='GUEST-GET')
        self.add_tag('GUEST-PROFILE',
                     self.prepare_map_xml({'CD_SIHOT_OBJID': obj_id}, action=ACTION_SEARCH, include_empty_values=False))
        self.end_xml()

        rp = GuestSearchResponse(self.ca)
        err_msg = self.send_to_server(response_parser=rp)
        if not err_msg and self.response:
            ret = self.response.ret_elem_values[0]
            self.ca.dprint("GuestSearch.guest_get() obj_id|xml|result: ", obj_id, self.xml, ret,
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        else:
            uprint("GuestSearch.guest_get() obj_id|error: ", obj_id, err_msg)
            ret = None
        return ret

    def get_guest_nos_by_matchcode(self, matchcode, exact_matchcode=True):
        col_values = {'CD_CODE': matchcode,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS' + (';MATCH-EXACT-MATCHCODE' if exact_matchcode else ''),
                      }
        return self.search_guests(col_values, ['guest_nr'])

    def get_objid_by_guest_no(self, guest_no):
        col_values = {'SH_GUEST_NO': guest_no,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        ret = self.search_guests(col_values, ['objid'])
        return ret[0] if len(ret) > 0 else None

    def get_objids_by_guest_names(self, surname, forename):
        col_values = {'CD_SNAM1': surname,
                      'CD_FNAM1': forename,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(col_values, ['objid'])

    def get_objids_by_email(self, email):
        col_values = {'CD_EMAIL': email,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(col_values, ['objid'])

    def get_objid_by_matchcode(self, matchcode, exact_matchcode=True):
        col_values = {'CD_CODE': matchcode,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS' + (';MATCH-EXACT-MATCHCODE' if exact_matchcode else ''),
                      }
        ret = self.search_guests(col_values, [':objid'], key_elem_name='matchcode')
        if ret:
            return self._check_and_get_objid_of_matchcode_search(ret, matchcode, exact_matchcode)

    def search_agencies(self):
        col_values = {'SIHOT_GUESTTYPE1': 7,
                      'SH_FLAGS': 'FIND-ALSO-DELETED-GUESTS',
                      }
        return self.search_guests(col_values, ['OBJID', 'MATCHCODE'])

    def search_guests(self, col_values, ret_elem_names, key_elem_name=None):
        """ return dict with search element/attribute value as the dict key if len(ret_elem_names)==1 and if
            ret_elem_names[0][0]==':' (in this case key_elem_name has to provide the search element/attribute name)
            OR return list of values if len(ret_elem_names) == 1
            OR return list of dict with ret_elem_names keys if len(ret_elem_names) >= 2
            OR return None in case of error.
        """
        self.beg_xml(operation_code='GUEST-SEARCH')
        self.add_tag('GUEST-SEARCH-REQUEST',
                     self.prepare_map_xml(col_values, action=ACTION_SEARCH, include_empty_values=False))
        self.end_xml()

        rp = GuestSearchResponse(self.ca, ret_elem_names, key_elem_name=key_elem_name)
        err_msg = self.send_to_server(response_parser=rp)
        if not err_msg and self.response:
            ret = self.response.ret_elem_values
            self.ca.dprint("GuestSearch.search_guests() col_values|xml|result: ", col_values, self.xml, ret,
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        else:
            uprint("GuestSearch.search_guests() col_values|error: ", col_values, err_msg)
            ret = None
        return ret

    @staticmethod
    def _check_and_get_objid_of_matchcode_search(ret_elem_values, key_elem_value, exact_matchcode):
        s = '\n   ...'
        if key_elem_value in ret_elem_values:
            ret = ret_elem_values[key_elem_value]
        elif key_elem_value + 'P2' in ret_elem_values:
            ret = ret_elem_values[key_elem_value + 'P2'] + s + "Only found OBJID of 2nd person matchcode: "
        elif key_elem_value[-2:] == 'P2' and key_elem_value[:-2] in ret_elem_values:
            ret = ret_elem_values[key_elem_value[:-2]] + s + "Only found OBJID of 1st person matchcode: "
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
            self.add_tag('CENTRAL-GUEST-ID', guest_id)  # this is not filtering nothing (tried GID from Sihot-To-Acu IF)
        self.end_xml()

        err_msg = self.send_to_server(response_parser=ResFromSihot(self.ca))

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


class ResToSihot(SihotXmlBuilder):
    def __init__(self, ca,
                 use_kernel_interface=USE_KERNEL_FOR_RES_DEF, use_kernel_for_new_clients=USE_KERNEL_FOR_CLIENTS_DEF,
                 map_res=MAP_RES_DEF, map_client=MAP_CLIENT_DEF,
                 connect_to_acu=True):
        super(ResToSihot, self).__init__(ca, col_map=map_res, use_kernel_interface=use_kernel_interface,
                                         connect_to_acu=connect_to_acu)
        self.use_kernel_for_new_clients = use_kernel_for_new_clients
        self.map_client = map_client

        self._warning_frags = self.ca.get_config('warningFragments') or list()  # list of fragments to identify warnings
        self._warning_msgs = ""
        self._gds_err_rows = dict()

    def _fetch_from_acu(self, view, where_group_order, date_range, hints=''):
        if date_range == 'H':
            where_group_order += (" and " if where_group_order else "") + "ARR_DATE < trunc(sysdate)"
        elif date_range == 'M':
            where_group_order += (" and " if where_group_order else "") \
                                 + "DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31"
        elif date_range and date_range[0] == 'Y':     # temporary/interim solution for migration of BHH/HMC - plan B
            where_group_order += (" and (" if where_group_order else "") \
                + "DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31" \
                + " or RUL_SIHOT_HOTEL in (1, 4, 999) or RUL_SIHOT_LAST_HOTEL in (1, 4, 999)" \
                + (" or ROWNUM <= " + date_range[1:6] if date_range[1:] else "") \
                + (")" if where_group_order else "")
        elif date_range == 'P':
            where_group_order += (" and " if where_group_order else "") + "DEP_DATE >= trunc(sysdate)"
        elif date_range == 'F':
            where_group_order += (" and " if where_group_order else "") + "ARR_DATE >= trunc(sysdate)"
        err_msg = self.ora_db.select(view, self.acu_col_expres, where_group_order, hints=hints)
        if not err_msg:
            self.fetch_all_from_acu()
        return err_msg

    def fetch_from_acu_by_aru(self, where_group_order='', date_range=''):
        return self._fetch_from_acu('V_ACU_RES_UNSYNCED', where_group_order, date_range, hints='/*+ NO_CPU_COSTING */')

    def fetch_from_acu_by_cd(self, acu_id, date_range=''):
        where_group_order = "CD_CODE " + ("like" if '_' in acu_id or '%' in acu_id else "=") + " '" + acu_id + "'"
        return self._fetch_from_acu('V_ACU_RES_UNFILTERED', where_group_order, date_range)

    def fetch_all_valid_from_acu(self, where_group_order='', date_range=''):
        return self._fetch_from_acu('V_ACU_RES_FILTERED', where_group_order, date_range)

    def _add_sihot_configs(self, crow):
        mkt_seg = crow.get('SIHOT_MKT_SEG', crow.get('RUL_SIHOT_RATE', ''))  # SIHOT_MKT_SEG not available if RU deleted
        hotel_id = str(crow.get('RUL_SIHOT_HOTEL', 999))
        arr_date = crow.get('ARR_DATE')
        today = datetime.datetime.today()
        cf = self.ca.get_config

        if arr_date and arr_date > today:            # Sihot doesn't accept allotment for reservations in the past
            val = cf(mkt_seg + '_' + hotel_id, section='SihotAllotments',
                     default_value=cf(mkt_seg, section='SihotAllotments'))
            if val:
                crow['SIHOT_ALLOTMENT_NO'] = val

        if not crow.get('SIHOT_RATE_SEGMENT'):  # not specified? FYI: this column is not included in V_ACU_RES_DATA
            val = cf(mkt_seg, section='SihotRateSegments', default_value=crow['RUL_SIHOT_RATE'])
            if val:
                crow['SIHOT_RATE_SEGMENT'] = val

        val = cf(mkt_seg, section='SihotPaymentInstructions')
        if val:
            crow['SIHOT_PAYMENT_INST'] = val

        if crow.get('RUL_ACTION', '') != 'DELETE' and crow.get('RU_STATUS', 0) != 120 and arr_date and arr_date > today:
            val = cf(mkt_seg, section='SihotResTypes')
            if val:
                crow['SH_RES_TYPE'] = val

    def _prepare_res_xml(self, crow):
        self._add_sihot_configs(crow)
        action = crow['RUL_ACTION']
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
        self.ca.dprint("ResToSihot._prepare_res_xml() result: ", self.xml,
                       minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    def _send_res_to_sihot(self, crow, commit):
        self._prepare_res_xml(crow)

        err_msg, warn_msg = self._handle_error(crow, self.send_to_server())
        if self.acu_connected:
            if not err_msg and self.response:
                err_msg = self._store_sihot_objid('RU', crow['RUL_PRIMARY'], self.response)
            err_msg += self._add_to_acumen_sync_log('RU', crow['RUL_PRIMARY'],
                                                    crow['RUL_ACTION'],
                                                    "ERR" + (self.response.server_error() if self.response else "")
                                                    if err_msg else "SYNCED",
                                                    err_msg + ("W" + warn_msg if warn_msg else ""),
                                                    crow['RUL_CODE'],
                                                    commit=commit)
        return err_msg

    def _handle_error(self, crow, err_msg):
        warn_msg = ""
        if [frag for frag in self._warning_frags if frag in err_msg]:
            warn_msg = self.res_id_desc(crow, err_msg, separator="\n")
            self._warning_msgs += "\n\n" + warn_msg
            err_msg = ""
        elif err_msg:
            assert crow['SIHOT_GDSNO']
            assert crow['SIHOT_GDSNO'] not in self._gds_err_rows
            self._gds_err_rows[crow['SIHOT_GDSNO']] = (crow, err_msg)
        return err_msg, warn_msg

    def _ensure_clients_exist_and_updated(self, crow, ensure_client_mode):
        if ensure_client_mode == ECM_DO_NOT_SEND_CLIENT:
            return ""
        err_msg = ""
        if 'CD_CODE' in crow and crow['CD_CODE']:
            acu_client = ClientToSihot(self.ca, use_kernel_interface=self.use_kernel_for_new_clients,
                                       map_client=self.map_client, connect_to_acu=self.acu_connected)
            if self.acu_connected:
                client_synced = bool(crow['CD_SIHOT_OBJID'])
                if client_synced:
                    err_msg = acu_client.fetch_from_acu_by_acu(crow['CD_CODE'])
                else:
                    err_msg = acu_client.fetch_from_acu_by_cd(crow['CD_CODE'])
                if not err_msg:
                    if acu_client.row_count:
                        err_msg = acu_client.send_client_to_sihot()
                    elif not client_synced:
                        err_msg = "ResToSihot._ensure_clients_exist_and_updated(): client not found: " + crow['CD_CODE']
                    if not err_msg:
                        err_msg = acu_client.fetch_from_acu_by_cd(crow['CD_CODE'])  # re-fetch OBJIDs
                    if not err_msg and not acu_client.row_count:
                        err_msg = "ResToSihot._ensure_clients_exist_and_updated(): IntErr/client: " + crow['CD_CODE']
                    if not err_msg:
                        # transfer just created guest OBJIDs from guest to reservation record
                        crow['CD_SIHOT_OBJID'] = acu_client.cols['CD_SIHOT_OBJID']
                        crow['SH_OBJID'] = crow['OC_SIHOT_OBJID'] or acu_client.cols['CD_SIHOT_OBJID']
                        crow['CD_SIHOT_OBJID2'] = acu_client.cols['CD_SIHOT_OBJID2']
            else:
                err_msg = acu_client.send_client_to_sihot(crow)
                if not err_msg:
                    # get client/occupant objid directly from acu_client.response
                    crow['CD_SIHOT_OBJID'] = acu_client.response.objid

        if not err_msg and 'OC_CODE' in crow and crow['OC_CODE'] \
                and len(crow['OC_CODE']) == 7:  # exclude pseudo client like TCAG/TCRENT
            acu_client = ClientToSihot(self.ca, use_kernel_interface=self.use_kernel_for_new_clients,
                                       map_client=self.map_client, connect_to_acu=self.acu_connected)
            if self.acu_connected:
                client_synced = bool(crow['OC_SIHOT_OBJID'])
                if client_synced:
                    err_msg = acu_client.fetch_from_acu_by_acu(crow['OC_CODE'])
                else:
                    err_msg = acu_client.fetch_from_acu_by_cd(crow['OC_CODE'])
                if not err_msg:
                    if acu_client.row_count:
                        err_msg = acu_client.send_client_to_sihot()
                    elif not client_synced:
                        err_msg = "ResToSihot._ensure_clients_exist_and_updated(): invalid orderer " + crow['OC_CODE']
                    if not err_msg:
                        err_msg = acu_client.fetch_from_acu_by_cd(crow['OC_CODE'])
                    if not err_msg and not acu_client.row_count:
                        err_msg = "ResToSihot._ensure_clients_exist_and_updated(): IntErr/orderer: " + crow['OC_CODE'] \
                            + ", cols=" + repr(getattr(acu_client, 'cols', "unDef")) + ", synced=" + str(client_synced)
                    if not err_msg:
                        # transfer just created guest OBJIDs from guest to reservation record
                        crow['SH_OBJID'] = crow['OC_SIHOT_OBJID'] = acu_client.cols['CD_SIHOT_OBJID']
            else:
                err_msg = acu_client.send_client_to_sihot(crow)
                if not err_msg:
                    # get orderer objid directly from acu_client.response
                    crow['SH_OBJID'] = crow['OC_SIHOT_OBJID'] = acu_client.response.objid

        return "" if ensure_client_mode == ECM_TRY_AND_IGNORE_ERRORS else err_msg

    def send_row_to_sihot(self, crow=None, commit=False, ensure_client_mode=ECM_ENSURE_WITH_ERRORS):
        if not crow:
            crow = self.cols
        gds_no = crow['SIHOT_GDSNO']
        if gds_no:
            if gds_no in self._gds_err_rows:    # prevent send of follow-up changes on erroneous bookings (w/ same GDS)
                old_id = self.res_id_desc(*self._gds_err_rows[gds_no], separator="\n")
                warn_msg = "\n\n" + "Synchronization skipped because GDS number {} had errors in previous send: {}" \
                           + "\nSkipped reservation: {}"
                self._warning_msgs += warn_msg.format(gds_no, old_id, self.res_id_desc(crow, "", separator="\n"))
                return ""

            err_msg = self._ensure_clients_exist_and_updated(crow, ensure_client_mode)
            if not err_msg:
                err_msg = self._send_res_to_sihot(crow, commit)
                if self.acu_connected and (crow['CD_SIHOT_OBJID'] or crow['CD_SIHOT_OBJID2']) \
                        and "Could not find a key identifier" in err_msg:  # WEB interface
                    self.ca.dprint("ResToSihot.send_row_to_sihot() ignoring CD_SIHOT_OBJID(" +
                                   str(crow['CD_SIHOT_OBJID']) + "/" + str(crow['CD_SIHOT_OBJID2']) + ") error: " +
                                   err_msg)
                    crow['CD_SIHOT_OBJID'] = None  # use MATCHCODE instead
                    crow['CD_SIHOT_OBJID2'] = None
                    err_msg = self._send_res_to_sihot(crow, commit)
        else:
            err_msg = self.res_id_desc(crow, "ResToSihot.send_row_to_sihot(): sync with empty GDS number skipped")

        if err_msg:
            self.ca.dprint("ResToSihot.send_row_to_sihot() error: " + err_msg)
        else:
            self.ca.dprint("ResToSihot.send_row_to_sihot() GDSNO={} RESPONDED OBJID={}|MATCHCODE={}"
                           .format(gds_no, self.response.objid, self.response.matchcode),
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return err_msg

    def send_rows_to_sihot(self, break_on_error=True, commit_per_row=False, commit_last_row=True):
        ret_msg = ""
        for row in self.rows:
            err_msg = self.send_row_to_sihot(row, commit=commit_per_row)
            if err_msg:
                if break_on_error:
                    return err_msg  # BREAK/RETURN first error message
                ret_msg += "\n" + err_msg
        if commit_last_row:
            ret_msg += self.ora_db.commit()
        return ret_msg

    def res_id_label(self):
        return "GDS/VOUCHER/CD/RO" + ("/RU/RUL" if self.ca.get_option('debugLevel') else "")

    def res_id_values(self, crow):
        return str(crow.get('SIHOT_GDSNO')) + \
               "/" + str(crow.get('RH_EXT_BOOK_REF')) + \
               "/" + str(crow.get('CD_CODE')) + "/" + str(crow.get('RUL_SIHOT_RATE')) + \
               ("/" + str(crow.get('RUL_PRIMARY')) + "/" + str(crow.get('RUL_CODE'))
                if self.ca.get_option('debugLevel') and 'RUL_PRIMARY' in crow and 'RUL_CODE' in crow
                else "")

    def res_id_desc(self, crow, error_msg, separator="\n\n"):
        indent = 8
        return crow.get('RUL_ACTION', '') + " RESERVATION: " \
            + (crow['ARR_DATE'].strftime('%d-%m') if crow.get('ARR_DATE') else "unknown") + ".." \
            + (crow['DEP_DATE'].strftime('%d-%m-%y') if crow.get('DEP_DATE') else "unknown") \
            + " in " + (crow['RUL_SIHOT_ROOM'] + "=" if crow.get('RUL_SIHOT_ROOM') else "") \
            + str(crow.get('RUL_SIHOT_CAT')) \
            + ("!" + crow.get('SH_PRICE_CAT', '')
               if crow.get('SH_PRICE_CAT') and crow.get('SH_PRICE_CAT') != crow.get('RUL_SIHOT_CAT') else "") \
            + " at hotel " + str(crow.get('RUL_SIHOT_HOTEL')) \
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
