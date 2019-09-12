# import os
import sys
import datetime
import pytest

from configparser import ConfigParser

from ae.sys_data import Record, FAD_ONTO
from ae.setting import Setting
from ae_db.db import OraDB
from ass_sys_data import AssSysData
from sxmlif import PostMessage, ConfigDict, CatRooms, AvailCatInfo
from sfif import SfInterface
from shif import ClientSearch, ClientToSihot, \
    USE_KERNEL_FOR_CLIENTS_DEF, SH_CLIENT_MAP, USE_KERNEL_FOR_RES_DEF, SH_RES_MAP
from sys_data_ids import SDF_SH_WEB_PORT, SDF_SH_KERNEL_PORT, SDF_SF_SANDBOX, SDF_SH_CLIENT_PORT, SDI_SH


@pytest.fixture(scope="module")
def console_app_env():
    return ConsoleApp()


# noinspection PyShadowingNames
@pytest.fixture()
def avail_cats(console_app_env):
    return AvailCatInfo(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def db_connected(console_app_env):
    ora_db = OraDB(dict(User=console_app_env.get_option('acuUser'), Password=console_app_env.get_option('acuPassword'),
                        DSN=console_app_env.get_option('acuDSN')),
                   app_name='conftest', debug_level=console_app_env.get_option('debugLevel'))
    ora_db.connect()
    return ora_db


# noinspection PyShadowingNames
@pytest.fixture()
def ass_sys_data(console_app_env):
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
def client_search(console_app_env):
    return ClientSearch(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def post_message(console_app_env):
    return PostMessage(console_app_env)


# noinspection PyShadowingNames
@pytest.fixture()
def create_test_client(console_app_env):
    # prevent duplicate creation of test client
    mc = 'T800001'
    sn = 'Tester800001'
    fn = 'Pepe'
    gt = '1'    # Guest (not Company)
    cs = ClientSearch(console_app_env)
    objid = cs.client_id_by_matchcode(mc)
    if objid and '\n' not in objid:
        client = cs
    else:
        client = ClientToSihot(console_app_env)
        col_values = Record(system=SDI_SH, direction=FAD_ONTO).add_system_fields(client.elem_map)
        col_values.clear_leafs()
        col_values['AcuId'] = mc
        col_values['Surname'] = sn
        col_values['Forename'] = fn
        col_values['GuestType'] = gt
        client.send_client_to_sihot(col_values)
    client.matchcode = mc     # added client attributes for easier testing
    client.objid = client.response.objid
    client.surname = sn
    client.forename = fn
    client.client_type = gt

    return client


# noinspection PyShadowingNames
@pytest.fixture(scope='module')
def salesforce_connection(console_app_env):
    cae = console_app_env
    debug_level = cae.get_option('debugLevel')
    sf_user = cae.get_option('sfUser')
    if not sf_user:         # check if app is specifying Salesforce credentials, e.g. SihotResSync/SihotResImport do not
        cae.uprint("conftest.salesforce_connection(): skipped because of unspecified credentials")
        return None
    sf_pw = cae.get_option('sfPassword')
    sf_token = cae.get_option('sfToken')
    sf_sandbox = cae.get_option(SDF_SF_SANDBOX, default_value='test' in sf_user.lower() or 'dbx' in sf_user.lower())
    sf_client = cae.app_name()

    cae.uprint("Salesforce " + ("sandbox" if sf_sandbox else "production") + " user/client-id:", sf_user, sf_client)

    sf_conn = SfInterface(dict(User=sf_user, Password=sf_pw, Token=sf_token),
                          features=[SDF_SF_SANDBOX + '=True'] if sf_sandbox else None,
                          app_name=sf_client, debug_level=debug_level)

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
        self.uprint = uprint
        self.uprint("####  TEST Initialization.. ####")
        self.uprint('ConsoleAppMock.__init__', args)
        cfg = ConfigParser()
        cfg.optionxform = str   # for case-sensitive config vars
        cfg.read(['../.app_env.cfg', '../.sys_envTEST.cfg'])

        self._options = dict(acuUser='SIHOT_INTERFACE', acuPassword=cfg.get('aeOptions', 'acuPassword'),
                             acuDSN=cfg.get('aeOptions', 'acuDSN', fallback='SP.TEST'),
                             debugLevel=cfg.getint('aeOptions', 'debugLevel', fallback=2),  # 2==DEBUG_LEVEL_VERBOSE
                             emailValidatorBaseUrl=cfg.get('aeOptions', 'emailValidatorBaseUrl'),
                             emailValidatorApiKey=cfg.get('aeOptions', 'emailValidatorApiKey'),
                             phoneValidatorBaseUrl=cfg.get('aeOptions', 'phoneValidatorBaseUrl'),
                             phoneValidatorApiKey=cfg.get('aeOptions', 'phoneValidatorApiKey'),
                             assUser=cfg.get('aeOptions', 'assUser'),
                             assPassword=cfg.get('aeOptions', 'assPassword'),
                             assRootUsr=cfg.get('aeOptions', 'assRootUsr'),
                             assRootPwd=cfg.get('aeOptions', 'assRootPwd'),
                             assDSN=cfg.get('aeOptions', 'assDSN', fallback='test'),
                             sfUser=cfg.get('aeOptions', 'sfUser'),
                             sfPassword=cfg.get('aeOptions', 'sfPassword'),
                             sfToken=cfg.get('aeOptions', 'sfToken'),
                             sfIsSandbox=cfg.get('aeOptions', SDF_SF_SANDBOX, fallback=True),
                             shClientPort=cfg.get('aeOptions', SDF_SH_CLIENT_PORT, fallback=12000),
                             shServerIP=cfg.get('aeOptions', 'shServerIP', fallback='10.103.222.70'),
                             shServerPort=cfg.get('aeOptions', SDF_SH_WEB_PORT, fallback=14777),
                             shServerKernelPort=cfg.get('aeOptions', SDF_SH_KERNEL_PORT, fallback=14772),
                             shTimeout=369.0, shXmlEncoding='utf8',
                             shUseKernelForClient=USE_KERNEL_FOR_CLIENTS_DEF, shMapClient=SH_CLIENT_MAP,
                             shUseKernelForRes=USE_KERNEL_FOR_RES_DEF, shMapRes=SH_RES_MAP,
                             warningFragments='',
                             )
        for cfg_key in ('hotelIds', 'resortCats', 'apCats', 'roAgencies', 'roomChangeMaxDaysDiff'):
            val = cfg.get('aeOptions', cfg_key)
            if val:
                self._options[cfg_key] = eval(val)

        self._env_cfg = cfg
        self.startup_beg = self.startup_end = datetime.datetime.now()
        self.sys_env_id = 'MOCK'

    def get_config(self, name, section=None, default_value=None):
        if section == 'SihotRateSegments':
            ret = 'CMM'     # quick fix for tests (for full fix need to include SihotMktSegExceptions.cfg)
        elif name in self._options:
            ret = self._options[name]
        elif section is None or section != 'aeOptions':
            # does not convert config value into list/dict:
            # .. ret = self._env_cfg.get(section or 'aeOptions', name, fallback=default_value)
            s = Setting(name=name, value=default_value, value_type=type(default_value))  # used only for conversion/eval
            s.value = self._env_cfg.get(section or 'aeOptions', name, fallback=s.value)
            ret = s.value
        else:
            ret = default_value
        self.uprint('ConsoleAppMock.get_config', name, '=', ret, 'section=' + str(section))
        return ret

    def get_option(self, name, default_value=None):
        ret = self._options[name] if name in self._options else default_value
        if name not in ('debugLevel', ):
            self.uprint('ConsoleAppMock.get_option', name, '=', ret)
        return ret

    def set_option(self, name, val, cfg_fnam=None, save_to_config=True):
        self.uprint('ConsoleAppMock.set_option', name, val, cfg_fnam, save_to_config)
        self._options[name]['val'] = val
        return ''

    @staticmethod
    def app_name():
        return "conftest.ConsoleApp.mock"

    def dprint(self, *objects, sep=' ', end='\n', file=sys.stdout, minimum_debug_level=1):  # 1==DEBUG_LEVEL_ENABLED
        if self.get_option('debugLevel') >= minimum_debug_level:
            self.uprint(*objects, sep=sep, end=end, file=file)

    def shutdown(self, exit_code=0):
        if exit_code:
            self.uprint("****  Non-zero exit code:", exit_code)
        self.uprint('####  Shutdown............  ####')
