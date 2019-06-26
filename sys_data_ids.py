"""
System Data IDs, record types, needed credentials and Features
"""
import logging


SDI_ASS = 'Ass'                             # AssCache Interfaces
SDI_ACU = 'Acu'                             # Acumen Interfaces
SDI_SF = 'Sf'                               # Salesforce Interfaces
SDI_SH = 'Sh'                               # Sihot Interfaces
ALL_AVAILABLE_SYSTEMS = {SDI_ASS: 'AssCache', SDI_ACU: 'Acumen', SDI_SF: 'Salesforce', SDI_SH: 'Sihot'}

SRT_ID_LEN = 1
SRT_CLIENTS = 'C'
SRT_RES_DATA = 'R'
SRT_PRODUCTS = 'P'
# SRT_RES_INV = 'I'
ALL_AVAILABLE_RECORD_TYPES = {SRT_CLIENTS: 'Clients', SRT_RES_DATA: 'Reservations', SRT_PRODUCTS: 'Products'}

SYS_CRED_ITEMS = ['User', 'Password', 'DSN', 'Token', 'SslArgs', 'ServerIP']
SYS_CRED_NEEDED = {SDI_ASS: tuple(SYS_CRED_ITEMS[:3]),
                   SDI_ACU: tuple(SYS_CRED_ITEMS[:3]),
                   SDI_SF: tuple(SYS_CRED_ITEMS[:2] + SYS_CRED_ITEMS[3:4]),
                   SDI_SH: tuple(SYS_CRED_ITEMS[5:6]),
                   }

SDF_SF_SANDBOX = 'sfIsSandbox'
SDF_SH_KERNEL_PORT = 'shServerKernelPort'   # Sihot Kernel Interfaces
SDF_SH_WEB_PORT = 'shServerPort'            # Sihot Web interfaces
SDF_SH_CLIENT_PORT = 'shClientPort'         # Sihot Server client port
SDF_SH_TIMEOUT = 'shTimeout'
SDF_SH_XML_ENCODING = 'shXmlEncoding'
SDF_SH_USE_KERNEL_FOR_CLIENT = 'shUseKernelForClient'
SDF_SH_USE_KERNEL_FOR_RES = 'shUseKernelForRes'
SDF_SH_CLIENT_MAP = 'shMapClient'
SDF_SH_RES_MAP = 'shMapRes'
SYS_FEAT_ITEMS = [SDF_SF_SANDBOX,
                  SDF_SH_KERNEL_PORT, SDF_SH_WEB_PORT, SDF_SH_CLIENT_PORT, SDF_SH_TIMEOUT, SDF_SH_XML_ENCODING,
                  SDF_SH_USE_KERNEL_FOR_CLIENT, SDF_SH_USE_KERNEL_FOR_RES, SDF_SH_CLIENT_MAP, SDF_SH_RES_MAP,
                  ]


# supported debugging levels    ONLY SHOWING logging levels equal or above:
DEBUG_LEVEL_DISABLED = 0        # ERROR/CRITICAL
DEBUG_LEVEL_ENABLED = 1         # WARNING
DEBUG_LEVEL_VERBOSE = 2         # INFO/DEBUG
DEBUG_LEVEL_TIMESTAMPED = 3     # -"- plus timestamp in logging format
debug_levels = {0: 'disabled', 1: 'enabled', 2: 'verbose', 3: 'timestamped'}

logging_levels = {DEBUG_LEVEL_DISABLED: logging.ERROR, DEBUG_LEVEL_ENABLED: logging.WARNING,
                  DEBUG_LEVEL_VERBOSE: logging.INFO, DEBUG_LEVEL_TIMESTAMPED: logging.DEBUG}

# OTHER GLOBAL SYSTEM CONSTANTS


# special client record type ids
CLIENT_REC_TYPE_ID_OWNERS = '012w0000000MSyZAAW'  # 15 digit ID == 012w0000000MSyZ

# external references separator
EXT_REFS_SEP = ','

# external reference type=id separator and types (also used as Sihot Matchcode/GDS prefix)
EXT_REF_TYPE_ID_SEP = '='
EXT_REF_TYPE_RCI = 'RCI'
_EXT_REF_TYPE_RCIP = 'RCIP'      # only used in Acumen


# SQL column expression merging wrongly classified Acumen external ref types holding RCI member IDs
AC_SQL_EXT_REF_TYPE = "CASE WHEN CR_TYPE in ('" + _EXT_REF_TYPE_RCIP + "', 'SPX')" \
    " then '" + EXT_REF_TYPE_RCI + "' else CR_TYPE end"

FORE_SURNAME_SEP = ' '


def parse_system_option_args(args_str):
    """
    parse command line option string
    :param args_str:    command line option string to be parsed.
    :return:            system id, record type id and option arguments dict string
    """
    str_i = args_str.find('{')
    if str_i >= 0:
        arg_dict_str = args_str[str_i:]
    else:
        str_i = len(args_str)
        arg_dict_str = ""
    str_i -= SRT_ID_LEN
    rec_type = args_str[str_i:str_i + SRT_ID_LEN]
    system = args_str[:str_i]
    if rec_type in ALL_AVAILABLE_RECORD_TYPES and system in ALL_AVAILABLE_SYSTEMS:
        return system, rec_type, arg_dict_str
    return None, None, None
