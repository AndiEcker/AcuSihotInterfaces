# import os
import sys
import pytest

from configparser import ConfigParser
from ae_db import OraDB
from acu_sf_sh_sys_data import AssSysData
from sxmlif import PostMessage, ConfigDict, CatRooms, GuestSearch, ClientToSihot, ResToSihot
from sfif import SfInterface


@pytest.fixture(scope="module")
def console_app_env():
    return ConsoleApp()


@pytest.fixture()
def db_connected(console_app_env):
    ora_db = OraDB(console_app_env.get_option('acuUser'), console_app_env.get_option('acuPassword'),
                   console_app_env.get_option('acuDSN'), debug_level=console_app_env.get_option('debugLevel'))
    ora_db.connect()
    return ora_db


@pytest.fixture()
def config_data(console_app_env):
    return AssSysData(console_app_env)


@pytest.fixture()
def post_message(console_app_env):
    return PostMessage(console_app_env)


@pytest.fixture()
def config_dict(console_app_env):
    return ConfigDict(console_app_env)


@pytest.fixture()
def cat_rooms(console_app_env):
    return CatRooms(console_app_env)


@pytest.fixture()
def guest_info(console_app_env):
    return GuestSearch(console_app_env)


@pytest.fixture()
def acu_guest(console_app_env):
    return ClientToSihot(console_app_env)


@pytest.fixture()
def acu_res(console_app_env):
    return ResToSihot(console_app_env)


@pytest.fixture()
def create_test_guest(console_app_env):
    # prevent duplicate creation of test client
    mc = 'T800001'
    sn = 'Tester800001'
    fn = 'Pepe'
    gt = '1'    # Guest (not Company)
    gs = GuestSearch(console_app_env)
    objid = gs.get_objid_by_matchcode(mc)
    if objid and '\n' not in objid:
        guest = gs
    else:
        guest = ClientToSihot(console_app_env, connect_to_acu=False)
        col_values = {}
        for col in guest.acu_col_names:
            if col == 'CD_CODE':
                col_values[col] = mc
            elif col == 'CD_SNAM1':
                col_values[col] = sn
            elif col == 'CD_FNAM1':
                col_values[col] = fn
            elif col == 'SIHOT_GUESTTYPE1':
                col_values[col] = gt
            else:
                col_values[col] = None
        guest.send_client_to_sihot(col_values)
    guest.matchcode = mc     # added guest attributes for easier testing
    guest.objid = guest.response.objid
    guest.surname = sn
    guest.forename = fn
    guest.guest_type = gt

    return guest


@pytest.fixture(scope='module')
def salesforce_connection(console_app_env):
    usr = console_app_env.get_config('sfUser')
    return SfInterface(username=usr,
                       password=console_app_env.get_config('sfPassword'),
                       token=console_app_env.get_config('sfToken'),
                       sandbox=console_app_env.get_config('sfIsSandbox',
                                                          default_value='test' in usr.lower()
                                                                        or 'sandbox' in usr.lower()),
                       client_id=console_app_env.get_config('sfClientId', default_value='TestSfInterface'))


############################################################################
# mock-ups and stubs


def uprint(*objects, sep=' ', end='\n', file=sys.stdout, encode_errors_def='backslashreplace'):
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file)
    else:
        print(*map(lambda obj: str(obj).encode(enc, errors=encode_errors_def).decode(enc), objects),
              sep=sep, end=end, file=file)


class ConsoleApp:
    def __init__(self, *args):
        uprint("####  Initialization......  ####")
        uprint('ConsoleAppMock.__init__', args)
        cfg = ConfigParser()
        cfg.read('../.console_app_env.cfg')

        self._options = dict(serverIP=cfg.get('Settings', 'serverIP', fallback='10.103.222.70'),
                             # serverIP: DEV=10.103.222.71 or TEST=.70 or LIVE='tf-sh-sihot1v.acumen.es'
                             serverPort=cfg.get('Settings', 'serverPort', fallback=14777),
                             serverKernelPort=cfg.get('Settings', 'serverKernelPort', fallback=14772),
                             timeout=39.6, xmlEncoding='utf8',
                             acuDSN=cfg.get('Settings', 'acuDSN', fallback='SP.TEST'),
                             acuUser='SIHOT_INTERFACE', acuPassword=cfg.get('Settings', 'acuPassword'),
                             debugLevel=cfg.getint('Settings', 'debugLevel', fallback=2),  # 2==DEBUG_LEVEL_VERBOSE
                             warningFragments='',
                             sfUser=cfg.get('Settings', 'sfUser'), sfPassword=cfg.get('Settings', 'sfPassword'),
                             sfToken=cfg.get('Settings', 'sfToken'),
                             )

    def get_config(self, name, value=None):
        ret = self._options[name] if name in self._options else value
        uprint('ConsoleAppMock.get_config', name, '=', ret)
        return ret

    def get_option(self, name, value=None):
        ret = self._options[name] if name in self._options else value
        uprint('ConsoleAppMock.get_option', name, '=', ret)
        return ret

    def set_option(self, name, val, cfg_fnam=None, save_to_config=True):
        uprint('ConsoleAppMock.set_option', name, val, cfg_fnam, save_to_config)
        self._options[name]['val'] = val
        return ''

    def dprint(self, *objects, sep=' ', end='\n', file=sys.stdout, minimum_debug_level=1):  # 1==DEBUG_LEVEL_ENABLED
        if self.get_option('debugLevel') >= minimum_debug_level:
            uprint(*objects, sep=sep, end=end, file=file)

    @staticmethod
    def shutdown(exit_code=0):
        if exit_code:
            uprint("****  Non-zero exit code:", exit_code)
        uprint('####  Shutdown............  ####')
