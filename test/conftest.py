# import os
import sys
import pytest

from configparser import ConfigParser
from ae_db import OraDB
from ass_sys_data import AssSysData
from sxmlif import PostMessage, ConfigDict, CatRooms, GuestSearch, ClientToSihot, ResToSihot, AvailCatInfo
from sfif import prepare_connection


@pytest.fixture(scope="module")
def console_app_env():
    return ConsoleApp()


# noinspection PyShadowingNames
@pytest.fixture()
def acu_guest(console_app_env):
    return ClientToSihot(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def acu_res(console_app_env):
    return ResToSihot(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def avail_cats(console_app_env):
    return AvailCatInfo(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def db_connected(console_app_env):
    ora_db = OraDB(console_app_env.get_option('acuUser'), console_app_env.get_option('acuPassword'),
                   console_app_env.get_option('acuDSN'), debug_level=console_app_env.get_option('debugLevel'))
    ora_db.connect()
    return ora_db


# noinspection PyShadowingNames
@pytest.fixture()
def config_data(console_app_env):
    return AssSysData(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def config_dict(console_app_env):
    return ConfigDict(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def cat_rooms(console_app_env):
    return CatRooms(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def guest_search(console_app_env):
    return GuestSearch(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def post_message(console_app_env):
    return PostMessage(console_app_env)


# noinspection PyShadowingNames
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
        col_values = dict()
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


# noinspection PyShadowingNames
@pytest.fixture(scope='module')
def salesforce_connection(console_app_env):
    sf_conn, sf_sandbox = prepare_connection(console_app_env)
    return sf_conn


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
        uprint("####  TEST Initialization.. ####")
        uprint('ConsoleAppMock.__init__', args)
        cfg = ConfigParser()
        cfg.optionxform = str   # for case-sensitive config vars
        cfg.read('../.console_app_env.cfg')

        self._options = dict(acuUser='SIHOT_INTERFACE', acuPassword=cfg.get('Settings', 'acuPassword'),
                             acuDSN=cfg.get('Settings', 'acuDSN', fallback='SP.TEST'),
                             debugLevel=cfg.getint('Settings', 'debugLevel', fallback=2),  # 2==DEBUG_LEVEL_VERBOSE
                             emailValidatorBaseUrl=cfg.get('Settings', 'emailValidatorBaseUrl'),
                             emailValidatorApiKey=cfg.get('Settings', 'emailValidatorApiKey'),
                             phoneValidatorBaseUrl=cfg.get('Settings', 'phoneValidatorBaseUrl'),
                             phoneValidatorApiKey=cfg.get('Settings', 'phoneValidatorApiKey'),
                             pgUser=cfg.get('Settings', 'pgUser'), pgPassword=cfg.get('Settings', 'pgPassword'),
                             pgRootUsr=cfg.get('Settings', 'pgRootUsr'), pgRootPwd=cfg.get('Settings', 'pgRootPwd'),
                             pgDSN=cfg.get('Settings', 'pgDSN', fallback='test'),
                             sfUser=cfg.get('Settings', 'sfUser'), sfPassword=cfg.get('Settings', 'sfPassword'),
                             sfToken=cfg.get('Settings', 'sfToken'),
                             sfClientId=cfg.get('Settings', 'sfClientId', fallback='AcuSihotInterfaces_TEST'),
                             sfIsSandbox=cfg.get('Settings', 'sfIsSandbox', fallback=True),
                             shClientPort=cfg.get('Settings', 'shClientPort', fallback=12000),
                             shServerIP=cfg.get('Settings', 'shServerIP', fallback='10.103.222.70'),
                             shServerPort=cfg.get('Settings', 'shServerPort', fallback=14777),
                             shServerKernelPort=cfg.get('Settings', 'shServerKernelPort', fallback=14772),
                             shTimeout=369.0, shXmlEncoding='utf8',
                             warningFragments='',
                             )
        for cfg_key in ('hotelIds', 'resortCats', 'apCats', 'roAgencies', 'roomChangeMaxDaysDiff'):
            val = cfg.get('Settings', cfg_key)
            if val:
                self._options[cfg_key] = eval(val)

    def get_config(self, name, section=None, default_value=None):
        if section == 'SihotRateSegments':
            ret = 'CMM'     # quick fix for tests (for full fix need to include SihotMktSegExceptions.cfg)
        else:
            ret = self._options[name] if name in self._options else default_value
        uprint('ConsoleAppMock.get_config', name, '=', ret, 'section=' + str(section))
        return ret

    def get_option(self, name, default_value=None):
        ret = self._options[name] if name in self._options else default_value
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
