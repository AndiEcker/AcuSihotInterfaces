from console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from sxmlif import GuestInfo

__version__ = '0.1'

cae = ConsoleApp(__version__, "Get guest OBJID from passed matchcode", debug_level_def=DEBUG_LEVEL_VERBOSE)

cae.add_option('matchcode', "Guest Matchcode", 'TCRENT')   # tk=TCAG, TK=TCRENT

uprint('####  Preparing .........  ####')

gi = GuestInfo(cae)

oi = gi.get_objid_by_matchcode(cae.get_option('matchcode'))

uprint('####  Result ............  ####')

uprint(oi)

uprint('####  Finished ..........  ####')
