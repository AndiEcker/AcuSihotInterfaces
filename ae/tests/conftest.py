# import os
import sys
import datetime
import pytest

from configparser import ConfigParser

from ae.console import MAIN_SECTION_NAME
from ae.literal import Literal
from ae.db_ora import OraDB
from ae.sys_data import Record, FAD_ONTO
from ae.sys_core_sh import SDI_SH, SDF_SH_KERNEL_PORT, SDF_SH_WEB_PORT, SDF_SH_CLIENT_PORT, \
    AvailCatInfo, CatRooms, ConfigDict, PostMessage
from ae.sys_data_sh import ClientSearch, ClientToSihot, \
    USE_KERNEL_FOR_CLIENTS_DEF, SH_CLIENT_MAP, USE_KERNEL_FOR_RES_DEF, SH_RES_MAP
from sys_core_sf import SfSysConnector, SDF_SF_SANDBOX
from sys_data_ass import AssSysData


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
    ora_db = OraDB(dict(User=console_app_env.get_opt('acuUser'), Password=console_app_env.get_opt('acuPassword'),
                        DSN=console_app_env.get_opt('acuDSN')),
                   app_name='conftest', debug_level=console_app_env.get_opt('debugLevel'))
    ora_db.connect()
    return ora_db


# noinspection PyShadowingNames
@pytest.fixture()
def sys_data_ass(console_app_env):
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
    debug_level = cae.get_opt('debugLevel')
    sf_user = cae.get_opt('sfUser')
    if not sf_user:         # check if app is specifying Salesforce credentials, e.g. SihotResSync/SihotResImport do not
        cae.po("conftest.salesforce_connection(): skipped because of unspecified credentials")
        return None
    sf_pw = cae.get_opt('sfPassword')
    sf_token = cae.get_opt('sfToken')
    sf_sandbox = cae.get_opt(SDF_SF_SANDBOX, default_value='test' in sf_user.lower() or 'dbx' in sf_user.lower())
    sf_client = cae.app_name

    cae.po("Salesforce " + ("sandbox" if sf_sandbox else "production") + " user/client-id:", sf_user, sf_client)

    sf_conn = SfSysConnector(dict(User=sf_user, Password=sf_pw, Token=sf_token),
                             features=[SDF_SF_SANDBOX + '=True'] if sf_sandbox else None,
                             app_name=sf_client, debug_level=debug_level)

    return sf_conn


@pytest.fixture
def restore_app_env():
    """ restore app environment after test run - needed for tests instantiating AppBase/ConsoleApp. """
    # LOCAL IMPORT because some portions like e.g. ae_systems does not depend/use ae.core
    # noinspection PyProtectedMember
    from ae.core import app_inst_lock, _app_instances, _unregister_app_instance

    yield "a,n,y"
    # added outer list() because unregister does _app_instances.pop() calls
    # and added inner list() because the .keys() 'generator' object is not reversible
    with app_inst_lock:
        app_keys = list(reversed(list(_app_instances.keys())))
        for key in app_keys:
            _unregister_app_instance(key)   # remove app from ae.core app register/dict


############################################################################
# mock-ups and stubs


def print_out(*objects, sep=' ', end='\n', file=sys.stdout, encode_errors_def='backslashreplace'):
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file)
    else:
        print(*map(lambda obj: str(obj).encode(enc, errors=encode_errors_def).decode(enc), objects),
              sep=sep, end=end, file=file)


po = print_out


class ConsoleApp:
    def __init__(self, *args):
        self.po = self.print_out = print_out
        self.po("####  TEST Initialization.. ####")
        self.po('ConsoleAppMock.__init__', args)
        cfg = ConfigParser()
        cfg.optionxform = str   # for case-sensitive config vars
        cfg.read(['../.app_env.cfg', '../.sys_envTEST.cfg'])

        self._options = dict(acuUser='SIHOT_INTERFACE',
                             acuPassword=cfg.get(MAIN_SECTION_NAME, 'acuPassword'),
                             acuDSN=cfg.get(MAIN_SECTION_NAME, 'acuDSN', fallback='SP.TEST'),
                             debugLevel=cfg.getint(MAIN_SECTION_NAME, 'debugLevel', fallback=2),  # =DEBUG_LEVEL_VERBOSE
                             emailValidatorBaseUrl=cfg.get(MAIN_SECTION_NAME, 'emailValidatorBaseUrl'),
                             emailValidatorApiKey=cfg.get(MAIN_SECTION_NAME, 'emailValidatorApiKey'),
                             phoneValidatorBaseUrl=cfg.get(MAIN_SECTION_NAME, 'phoneValidatorBaseUrl'),
                             phoneValidatorApiKey=cfg.get(MAIN_SECTION_NAME, 'phoneValidatorApiKey'),
                             assUser=cfg.get(MAIN_SECTION_NAME, 'assUser'),
                             assPassword=cfg.get(MAIN_SECTION_NAME, 'assPassword'),
                             assRootUsr=cfg.get(MAIN_SECTION_NAME, 'assRootUsr'),
                             assRootPwd=cfg.get(MAIN_SECTION_NAME, 'assRootPwd'),
                             assDSN=cfg.get(MAIN_SECTION_NAME, 'assDSN', fallback='test'),
                             sfUser=cfg.get(MAIN_SECTION_NAME, 'sfUser'),
                             sfPassword=cfg.get(MAIN_SECTION_NAME, 'sfPassword'),
                             sfToken=cfg.get(MAIN_SECTION_NAME, 'sfToken'),
                             sfIsSandbox=cfg.get(MAIN_SECTION_NAME, SDF_SF_SANDBOX, fallback=True),
                             shClientPort=cfg.get(MAIN_SECTION_NAME, SDF_SH_CLIENT_PORT, fallback=12000),
                             shServerIP=cfg.get(MAIN_SECTION_NAME, 'shServerIP', fallback='10.103.222.70'),
                             shServerPort=cfg.get(MAIN_SECTION_NAME, SDF_SH_WEB_PORT, fallback=14777),
                             shServerKernelPort=cfg.get(MAIN_SECTION_NAME, SDF_SH_KERNEL_PORT, fallback=14772),
                             shTimeout=369.0, shXmlEncoding='utf8',
                             shUseKernelForClient=USE_KERNEL_FOR_CLIENTS_DEF, shMapClient=SH_CLIENT_MAP,
                             shUseKernelForRes=USE_KERNEL_FOR_RES_DEF, shMapRes=SH_RES_MAP,
                             warningFragments='',
                             )
        for cfg_key in ('hotelIds', 'resortCats', 'apCats', 'roAgencies', 'roomChangeMaxDaysDiff'):
            val = cfg.get(MAIN_SECTION_NAME, cfg_key)
            if val:
                self._options[cfg_key] = eval(val)

        self._env_cfg = cfg
        self.app_name = 'conftest.ConsoleApp.mock'
        self.startup_beg = self.startup_end = datetime.datetime.now()
        self.sys_env_id = 'MOCK'

    def get_var(self, name, section=None, default_value=None):
        if section == 'SihotRateSegments':
            ret = 'CMM'     # quick fix for tests (for full fix need to include SihotMktSegExceptions.cfg)
        elif name in self._options:
            ret = self._options[name]
        elif section is None or section != MAIN_SECTION_NAME:
            # does not convert config value into list/dict:
            # .. ret = self._env_cfg.get(section or MAIN_SECTION_NAME, name, fallback=default_value)
            s = Literal(literal_or_value=default_value, value_type=type(default_value), name=name)  # conversion/eval
            s.value = self._env_cfg.get(section or MAIN_SECTION_NAME, name, fallback=s.value)
            ret = s.value
        else:
            ret = default_value
        self.po('ConsoleAppMock.get_var', name, '=', ret, 'section=' + str(section))
        return ret

    def get_opt(self, name, default_value=None):
        ret = self._options[name] if name in self._options else default_value
        if name not in ('debugLevel', ):
            self.po('ConsoleAppMock.get_opt', name, '=', ret)
        return ret

    def set_opt(self, name, val, cfg_fnam=None, save_to_config=True):
        self.po('ConsoleAppMock.set_opt', name, val, cfg_fnam, save_to_config)
        self._options[name]['val'] = val
        return ''

    def debug_out(self, *objects, sep=' ', end='\n', file=sys.stdout, minimum_debug_level=1):  # 1==DEBUG_LEVEL_ENABLED
        if self.get_opt('debugLevel') >= minimum_debug_level:
            self.po(*objects, sep=sep, end=end, file=file)

    dpo = debug_out

    def shutdown(self, exit_code=0):
        if exit_code:
            self.po("****  Non-zero exit code:", exit_code)
        self.po('####  Shutdown............  ####')
