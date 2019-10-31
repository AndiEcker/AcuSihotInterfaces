from ae.core import DEBUG_LEVEL_VERBOSE
from ae.console import ConsoleApp
from ae.shif import ClientSearch

__version__ = '0.1'

cae = ConsoleApp("Get guest OBJID from passed matchcode", debug_level=DEBUG_LEVEL_VERBOSE)

cae.add_opt('matchcode', "Guest Matchcode", 'TCRENT')   # tk=TCAG, TK=TCRENT

cae.po('####  Preparing .........  ####')

cs = ClientSearch(cae)

oi = cs.client_id_by_matchcode(cae.get_opt('matchcode'))

cae.po('####  Result ............  ####')

cae.po(oi)

cae.po('####  Finished ..........  ####')
