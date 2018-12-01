"""
System Data IDs
"""

SDI_ASS = 'As'
SDI_AC = 'Ac'
SDI_SF = 'Sf'
SDI_SH = 'Sh'   # Sihot Interfaces
# SDI_SK = 'Sk'   # Sihot Kernel Interfaces
# SDI_SW = 'Sw'   # Sihot Web interfaces


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
