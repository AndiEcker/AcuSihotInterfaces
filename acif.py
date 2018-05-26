"""
Acumen interface constants and helpers
"""

ACU_DEF_USR = 'SIHOT_INTERFACE'
ACU_DEF_DSN = 'SP.TEST'


def add_ac_options(cae):
    cae.add_option('acuUser', "Acumen/Oracle user account name", ACU_DEF_USR, 'u')
    cae.add_option('acuPassword', "Acumen/Oracle user account password", '', 'p')
    cae.add_option('acuDSN', "Acumen/Oracle data source name", ACU_DEF_DSN, 'd')
