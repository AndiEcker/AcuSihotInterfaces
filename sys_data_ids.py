"""
System Data IDs, record types, needed credentials and Features
"""

# OTHER GLOBAL SYSTEM CONSTANTS


# external references separator
EXT_REFS_SEP = ','  # migrate as REC_SEP_DEF to ae.sys_data (string_to_records() arg default value)

# external reference type=id separator and types (also used as Sihot Matchcode/GDS prefix)
EXT_REF_TYPE_ID_SEP = '='  # migrate as FLD_SEP_DEF to ae.sys_data (string_to_records() arg default value)
EXT_REF_TYPE_RCI = 'RCI'
_EXT_REF_TYPE_RCIP = 'RCIP'      # only used in Acumen


# SQL column expression merging wrongly classified Acumen external ref types holding RCI member IDs
AC_SQL_EXT_REF_TYPE = "CASE WHEN CR_TYPE in ('" + _EXT_REF_TYPE_RCIP + "', 'SPX')" \
    " then '" + EXT_REF_TYPE_RCI + "' else CR_TYPE end"

FORE_SURNAME_SEP = ' '
