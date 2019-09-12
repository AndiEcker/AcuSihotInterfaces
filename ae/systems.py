""" manage user credentials and other config options for external systems (servers, databases, cloud stores, ...)
"""
from collections import OrderedDict
from typing import Callable, Tuple, Sequence, Dict, Any


class System:
    """ each instance of this class is representing an external system.
    """
    def __init__(self, sys_id: str, credentials: Dict, debug_level_disabled: int, debug_level_verbose: int,
                 features: Sequence = None):
        """ create new :class:`System` instance.

        :param sys_id:                  unique str for to identify a system (also used as prefix/suffix).
        :param credentials:             dict for to access system, containing e.g. user name, password, token, dsn
        :param debug_level_disabled:    disable debug level.
        :param debug_level_verbose:     verbose debug level.
        :param features:                optional list with special features for this system (see SDF_* constants).
        """
        self.sys_id = sys_id
        self.credentials = credentials
        self.debug_level_disabled = debug_level_disabled
        self.debug_level_verbose = debug_level_verbose
        self.features = features or list()

        self.connection = None
        self.conn_error = ""
        self.app_name = ''
        self.debug_level = debug_level_disabled

    def __repr__(self) -> str:
        ret = self.sys_id
        if self.conn_error:
            ret += "!" + self.conn_error
        if self.debug_level != self.debug_level_disabled:
            cre = self.credentials
            ret += "&" + (repr(cre) if self.debug_level >= self.debug_level_verbose else repr(cre.get('User')))
            ret += "_" + repr(self.features)
            ret += "@" + repr(self.app_name)
        return ret

    def connect(self, connector: Callable, app_name: str = '', debug_level: int = None, force_reconnect: bool = False
                ) -> str:
        """ connect this :class:`System` instance to his system using the passed :data:`connector` callable.

        :param connector:           connector callable for to connect this system.
        :param app_name:            application name.
        :param debug_level:         debug level.
        :param force_reconnect:     pass True to force re-connection.
        :return:                    error message or empty string in case of no errors while re-connecting.
        """
        if debug_level is None:
            debug_level = self.debug_level_disabled
        self.conn_error = ""
        if not self.connection or self.conn_error or force_reconnect:
            self.connection = connector(self.credentials, features=self.features,
                                        app_name=app_name, debug_level=debug_level)
            if callable(getattr(self.connection, 'connect', False)):
                self.conn_error = self.connection.connect()
                if self.conn_error:
                    self.connection = None
        self.app_name = app_name or 'ae.sys_data'
        self.debug_level = debug_level
        return self.conn_error

    def disconnect(self) -> str:
        """ disconnect this external system.

        :return:            error message string or empty string if no errors occurred on disconnection.
        """
        err_msg = ""
        if self.connection:
            if callable(getattr(self.connection, 'close', False)):
                err_msg = self.connection.close()
            elif callable(getattr(self.connection, 'disconnect', False)):
                err_msg = self.connection.disconnect()
            self.connection = None
        self.conn_error = err_msg
        return err_msg


class UsedSystems(OrderedDict):
    """ An instance of this class is keeping a dictionary of all the found and used systems of this application.
    """
    def __init__(self, debug_level_disabled: int, debug_level_verbose: int, *available_systems: str,
                 config_getters: Tuple[Callable[[str], Any], ...] = (), sys_cred_items: Sequence = (),
                 sys_cred_needed: Dict[str, Tuple] = None, sys_feat_items: Sequence = (), **sys_credentials: str):
        """ create new instance of :class:`UsedSystems`.

        :param debug_level_disabled:    disable debug level.
        :param debug_level_verbose:     verbose debug level.
        :param available_systems:       iterable of id string of all available systems.
        :param config_getters:          iterable of callable configuration getters (called with setting name as arg).
        :param sys_cred_items:          iterable of all supported credential setting names.
        :param sys_cred_needed:         dict having system ids as keys and a iterable of needed credential setting names
                                        for each system.
        :param sys_feat_items:          iterable of other/feature system setting names.
        :param sys_credentials:         dict of all available/loaded system credential values.
        """
        super().__init__()
        self.debug_messages = list()

        self._systems = self
        self._available_systems = available_systems
        if sys_cred_needed is None:
            sys_cred_needed = dict()

        self.debug_messages.append(
            "UsedSystems.__init__({}, {}, {}, {}, {}, {}, {}, {})"
            .format(debug_level_disabled, debug_level_verbose, available_systems,
                    config_getters, sys_cred_items, sys_cred_needed, sys_feat_items, sys_credentials))

        for sys_id in available_systems:
            self.debug_messages.append("Checking {} system:".format(sys_id))
            credentials = dict()
            for cred_item in sys_cred_items:
                sys_cred_item = sys_id.lower() + '_' + cred_item.lower()
                cfg_cred_item = sys_id.lower() + cred_item
                found_cred = None
                if sys_cred_item in sys_credentials:
                    found_cred = sys_credentials[sys_cred_item]
                else:
                    for get_conf_func in config_getters:
                        found_cred = get_conf_func(cfg_cred_item)
                        if found_cred:
                            break
                if found_cred is not None:
                    self.debug_messages.append("found credential {}={}".format(cred_item, found_cred))
                    credentials[cred_item] = found_cred
            for cred_item in sys_cred_needed.get(sys_id, ()):
                if cred_item not in credentials:
                    self.debug_messages.append("requested credential {} undefined/incomplete/ignored".format(cred_item))
                    self.debug_messages.append("Skipping unused/disabled system")
                    break    # ignore/skip not fully specified system - continue with next available system
            else:
                # now collect features for this system with complete credentials
                features = list()
                for feat_item in sys_feat_items:
                    if feat_item.startswith(sys_id.lower()):
                        for get_conf_func in config_getters:
                            found_feat = get_conf_func(feat_item)
                            if found_feat:
                                feat_item += '=' + str(found_feat)
                                break
                        features.append(feat_item)
                # finally add system to this used systems instance
                self._add_system(sys_id, credentials, debug_level_disabled, debug_level_verbose, features=features)
                self.debug_messages.append("added system features={}".format(features))
                self.debug_messages.append("System fully initialized")

    def _add_system(self, sys_id: str, credentials: Dict, debug_level_disabled: int, debug_level_verbose: int,
                    features: Sequence = None):
        """ add new :class:`System` instance to this :class:`UsedSystems` instance.

        :param sys_id:                  system id.
        :param credentials:             credentials of the new system to add.
        :param debug_level_disabled:    disabled debug level.
        :param debug_level_verbose:     verbose debug level.
        :param features:                optional list with special features for this system (see SDF_* constants).
        """
        assert sys_id in self._available_systems, "UsedSystems._add_system(): unsupported system id {}".format(sys_id)
        assert sys_id not in self._systems, "UsedSystems._add_system(): system id {} already specified".format(sys_id)
        system = System(sys_id, credentials, debug_level_disabled, debug_level_verbose, features=features)
        self._systems[sys_id] = system

    def connect(self, connectors: Dict[str, Callable], **connector_args: Any) -> str:
        """ connect this :class:`System` instance to his system using the passed :data:`connector` callable.

        :param connectors:      connector callables for to connect all available systems.
        :param connector_args:  additional connector arguments.
        :return:                error message or empty string in case of no errors while re-connecting.
        """
        errors = list()
        for sys_id, system in self._systems.items():
            assert sys_id in connectors, "UsedSystems.connect(): connector for system {} missing".format(sys_id)
            if system.connect(connectors[sys_id], **connector_args) or not system.connection:
                errors.append(system.conn_error or "UsedSystems.connect(): system {} connection failed".format(sys_id))
        return "\n      ".join(errors)

    def disconnect(self) -> str:
        """ disconnect all available and already connected systems.

        :return:                error message string or empty string if no errors occurred on disconnection.
        """
        err_msg = ""
        for system in self._systems.values():
            err_msg += system.disconnect()
        return err_msg
