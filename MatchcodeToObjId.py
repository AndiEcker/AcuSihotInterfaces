from sys_data_ids import DEBUG_LEVEL_VERBOSE
from ae.console_app import ConsoleApp, uprint
from shif import ClientSearch

__version__ = '0.1'

cae = ConsoleApp(__version__, "Get guest OBJID from passed matchcode", debug_level_def=DEBUG_LEVEL_VERBOSE)

cae.add_option('matchcode', "Guest Matchcode", 'TCRENT')   # tk=TCAG, TK=TCRENT

uprint('####  Preparing .........  ####')

cs = ClientSearch(cae)

oi = cs.client_id_by_matchcode(cae.get_option('matchcode'))

uprint('####  Result ............  ####')

uprint(oi)

uprint('####  Finished ..........  ####')
