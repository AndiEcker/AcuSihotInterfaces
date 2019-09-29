from ae.systems import System, UsedSystems

SS = 'Ss'       # test system ids
SX = 'Xx'
SY = 'Yy'

CREDENTIAL1 = 'User'
SYS_CRED_USER = SS.lower() + '_' + CREDENTIAL1.lower()
USER_NAME1 = 'test_user'
SYS_CREDENTIALS = {SYS_CRED_USER: USER_NAME1,
                   SX.lower() + '_' + CREDENTIAL1.lower(): USER_NAME1,
                   SY.lower() + '_' + CREDENTIAL1.lower(): USER_NAME1}
SYS_CRED_ITEMS = (CREDENTIAL1,)
SYS_CRED_NEEDED = {SS: SYS_CRED_ITEMS, SX: SYS_CRED_ITEMS, SY: SYS_CRED_ITEMS}
FEATURE1 = 'ss_extra_feature'
SYS_FEAT_ITEMS = (FEATURE1,)
SYS_FEATURES = [FEATURE1]
APP_NAME = 'test_sys_app_name'
DBG_LEVEL_DISABLED = -1
DBG_LEVEL_VERBOSE = 99


class SystemConnectionSuccessMock:
    def connect(self):
        return not self or ''

    def close(self):
        return not self or ''

    def disconnect(self):
        return not self or ''


class SystemConnectionFailureMock:
    def connect(self):
        return 'ConnectError' or self


class SystemDisconnectionFailureMock:
    def connect(self):
        return not self or ''

    def close(self):
        return 'CloseError' or self

    def disconnect(self):
        return 'DisconnectError' or self


def check_connector_args(cre, fea, ana, dlv):
    assert cre == SYS_CREDENTIALS or CREDENTIAL1 in cre and cre[CREDENTIAL1] == USER_NAME1, \
        "check_connect_args() SYS_CREDENTIALS failure"
    assert fea == SYS_FEATURES or fea == list(), "check_connect_args() SYS_FEATURES failure"
    assert ana == APP_NAME, "check_connect_args() application name failure"
    assert dlv == DBG_LEVEL_DISABLED or dlv == DBG_LEVEL_VERBOSE, "check_connect_args() DBG_LEVEL_VERBOSE failure"


def connector_success_mock(credentials, features, app_name, debug_level):
    check_connector_args(credentials, features, app_name, debug_level)
    return SystemConnectionSuccessMock()


def connector_failure_mock(credentials, features, app_name, debug_level):
    check_connector_args(credentials, features, app_name, debug_level)
    return SystemConnectionFailureMock()


def disconnect_failure_mock(credentials, features, app_name, debug_level):
    check_connector_args(credentials, features, app_name, debug_level)
    return SystemDisconnectionFailureMock()


CONNECTORS = {SS: connector_success_mock, SX: connector_failure_mock, SY: disconnect_failure_mock}


class TestSystem:
    def test_init(self):
        s = System(SX, SYS_CREDENTIALS, DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, features=SYS_FEATURES)
        assert s.sys_id == SX
        assert s.credentials == SYS_CREDENTIALS
        assert s.debug_level_disabled == DBG_LEVEL_DISABLED
        assert s.debug_level_verbose == DBG_LEVEL_VERBOSE
        assert s.features == SYS_FEATURES
        assert s.connection is None
        assert s.conn_error == ''
        assert s.app_name == ''
        assert s.debug_level == DBG_LEVEL_DISABLED

    def test_repr(self):
        s = System(SS, SYS_CREDENTIALS, DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, features=SYS_FEATURES)
        assert SS in repr(s)
        assert s.connect(connector_failure_mock, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == 'ConnectError'
        assert s.conn_error in repr(s)

        assert s.connect(connector_success_mock, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == ''
        rep = repr(s)
        assert s.credentials.get(SYS_CRED_USER) in rep
        assert repr(s.features) in rep
        assert APP_NAME in rep

    def test_connect_and_close(self):
        s = System(SX, SYS_CREDENTIALS, DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, features=SYS_FEATURES)
        assert s.connect(connector_success_mock, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == ''
        assert s.conn_error == ''
        assert s.disconnect() == ''
        assert s.conn_error == ''

        s = System(SX, SYS_CREDENTIALS, DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, features=SYS_FEATURES)
        assert s.connect(connector_success_mock, app_name=APP_NAME) == ''
        assert s.conn_error == ''
        s.connection.close = None
        assert s.disconnect() == ''
        assert s.conn_error == ''

    def test_connect_error(self):
        s = System(SX, SYS_CREDENTIALS, DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, features=SYS_FEATURES)
        assert s.connect(connector_failure_mock, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == 'ConnectError'
        assert s.conn_error == 'ConnectError'
        assert s.disconnect() == ''
        assert s.conn_error == ''

        s = System(SX, SYS_CREDENTIALS, DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, features=SYS_FEATURES)
        assert s.connect(connector_failure_mock, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == 'ConnectError'
        assert s.conn_error == 'ConnectError'
        assert s.disconnect() == ''
        assert s.conn_error == ''

        s = System(SX, SYS_CREDENTIALS, DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, features=SYS_FEATURES)
        assert s.connect(disconnect_failure_mock, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == ''
        assert s.conn_error == ''
        assert s.disconnect() == 'CloseError'
        assert s.conn_error == 'CloseError'

        s = System(SX, SYS_CREDENTIALS, DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, features=SYS_FEATURES)
        assert s.connect(disconnect_failure_mock, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == ''
        s.connection.close = None
        assert s.disconnect() == 'DisconnectError'
        assert s.conn_error == 'DisconnectError'


class TestUsedSystems:
    def test_init(self):
        def get_opt(opt):
            ret = None
            if opt.endswith(CREDENTIAL1):
                ret = USER_NAME1
            elif opt == FEATURE1:
                ret = FEATURE1
            return ret

        us = UsedSystems(DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SS, SX, SY, **SYS_CREDENTIALS)
        assert SS in us._available_systems and SX in us._available_systems and SY in us._available_systems
        assert SS in us and SX in us and SY in us

        us = UsedSystems(
            DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SS, SX, SY,
            config_getters=(get_opt, ), sys_cred_items=SYS_CRED_ITEMS, sys_cred_needed=SYS_CRED_NEEDED,
            sys_feat_items=SYS_FEAT_ITEMS)
        print("\n".join(us.debug_messages))
        assert SS in us._available_systems and SX in us._available_systems and SY in us._available_systems
        assert SS in us and SX in us and SY in us

        us = UsedSystems(
            DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SS, SX, SY,
            config_getters=(get_opt, ), sys_cred_needed=SYS_CRED_NEEDED, sys_feat_items=SYS_FEAT_ITEMS,
            **SYS_CREDENTIALS)
        print("\n".join(us.debug_messages))
        assert SS in us._available_systems and SX in us._available_systems and SY in us._available_systems
        assert SS not in us and SX not in us and SY not in us

        us = UsedSystems(
            DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SS, SX, SY,
            config_getters=(get_opt, ), sys_cred_items=SYS_CRED_ITEMS, sys_cred_needed=SYS_CRED_NEEDED,
            sys_feat_items=SYS_FEAT_ITEMS,
            **SYS_CREDENTIALS)
        print("\n".join(us.debug_messages))
        assert SS in us._available_systems and SX in us._available_systems and SY in us._available_systems
        assert SS in us and SX in us and SY in us

    def test_connect_and_close(self):
        us = UsedSystems(DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SS,
                         sys_cred_items=SYS_CRED_ITEMS, sys_cred_needed=SYS_CRED_NEEDED, sys_feat_items=SYS_FEAT_ITEMS,
                         **SYS_CREDENTIALS)
        assert us.connect(CONNECTORS, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == ''
        assert us.disconnect() == ''

        us = UsedSystems(DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SS,
                         sys_cred_items=SYS_CRED_ITEMS, sys_cred_needed=SYS_CRED_NEEDED, sys_feat_items=SYS_FEAT_ITEMS,
                         **SYS_CREDENTIALS)
        assert us.connect(CONNECTORS, app_name=APP_NAME) == ''
        assert us.disconnect() == ''

        us = UsedSystems(DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SX,
                         sys_cred_items=SYS_CRED_ITEMS, sys_cred_needed=SYS_CRED_NEEDED, sys_feat_items=SYS_FEAT_ITEMS,
                         **SYS_CREDENTIALS)
        assert us.connect(CONNECTORS, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == 'ConnectError'
        assert us.disconnect() == ''

        us = UsedSystems(DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SX,
                         sys_cred_items=SYS_CRED_ITEMS, sys_cred_needed=SYS_CRED_NEEDED, sys_feat_items=SYS_FEAT_ITEMS,
                         **SYS_CREDENTIALS)
        assert us.connect(CONNECTORS, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == 'ConnectError'
        assert us.disconnect() == ''

        us = UsedSystems(DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SY,
                         sys_cred_items=SYS_CRED_ITEMS, sys_cred_needed=SYS_CRED_NEEDED, sys_feat_items=SYS_FEAT_ITEMS,
                         **SYS_CREDENTIALS)
        assert us.connect(CONNECTORS, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == ''
        assert us.disconnect() == 'CloseError'

        us = UsedSystems(DBG_LEVEL_DISABLED, DBG_LEVEL_VERBOSE, SY,
                         sys_cred_items=SYS_CRED_ITEMS, sys_cred_needed=SYS_CRED_NEEDED, sys_feat_items=SYS_FEAT_ITEMS,
                         **SYS_CREDENTIALS)
        assert us.connect(CONNECTORS, app_name=APP_NAME, debug_level=DBG_LEVEL_VERBOSE) == ''
        assert us.disconnect() == 'CloseError'
