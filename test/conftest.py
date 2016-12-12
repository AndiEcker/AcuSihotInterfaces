# import os
import sys
import pytest

from configparser import ConfigParser
from db import OraDB
from acu_sihot_config import Data
from sxmlif import PostMessage, ConfigDict, CatRooms, GuestInfo, ClientToSihot, ResToSihot


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
    return Data(console_app_env.get_option('acuUser'), console_app_env.get_option('acuPassword'),
                console_app_env.get_option('acuDSN'))


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
    return GuestInfo(console_app_env)


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
    gi = GuestInfo(console_app_env)
    objid = gi.get_objid_by_matchcode(mc)
    if objid:
        guest = gi
        guest.matchcode = mc
        guest.objid = objid
    else:
        guest = ClientToSihot(console_app_env, connect_to_acu=False)
        col_values = {}
        for col in guest.acu_col_names:
            if col == 'CD_CODE':
                col_values[col] = mc
            elif col == 'CD_SNAM1':
                col_values[col] = 'Tester800001'
            elif col == 'CD_FNAM1':
                col_values[col] = 'Pepe'
            elif col == 'SIHOT_GUESTTYPE1':
                col_values[col] = '1A'
            else:
                col_values[col] = None
        guest.send_client_to_sihot(col_values)
        guest.matchcode = col_values['CD_CODE']     # added for easier testing
        guest.objid = guest.response.objid

    return guest


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
                             debugLevel=2)  # 2==DEBUG_LEVEL_VERBOSE

    def get_option(self, name, value=None):
        uprint('ConsoleAppMock.get_option', name)
        return self._options[name] if name in self._options else value

    def set_option(self, name, val):
        uprint('ConsoleAppMock.set_option', name, val)
        self._options[name]['val'] = str(val)
        return ''

    def dprint(self, *objects, sep=' ', end='\n', file=sys.stdout, minimum_debug_level=1):  # 1==DEBUG_LEVEL_ENABLED
        if self.get_option('debugLevel') >= minimum_debug_level:
            uprint(*objects, sep=sep, end=end, file=file)

    @staticmethod
    def shutdown(exit_code=0):
        if exit_code:
            uprint("****  Non-zero exit code:", exit_code)
        uprint('####  Shutdown............  ####')
