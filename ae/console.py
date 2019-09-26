"""
console application environment
===============================

The :class:`ConsoleApp` allows your application the easy declaration of command line
arguments and options. It will additionally extend your application with dynamically
configurable logging and debugging features.


Basic Usage
-----------

.. _app-title:
.. _app-version:

At the top of your python application main file/module create an instance of the class :class:`ConsoleApp`::

    '' '' ''  docstring of your application main module  '' '' ''
    from console import ConsoleApp

    __version__ = '1.2.3'

    ca = ConsoleApp()

In the above example the :class:`ConsoleApp` instance will automatically use the docstring of your application
main module as application title and the string in the module variable __version___ as application version.
Alternatively you can specify your application title and version string by passing them as the first two
arguments (:paramref:`~ConsoleApp.app_title` and :paramref:`~ConsoleApp.app_version`)
to the instantiation call of :class:`ConsoleApp`.

.. _app-name:

:class:`ConsoleApp` also determines automatically the name/id of your application from the file base name
of your application main/startup module (e.g. <app_name>.py or main.py). Also other application environment
vars/options (like e.g. the application startup folder path and the current working directory path) will be
automatically initialized for your application.


With the methods :meth:`~ConsoleApp.add_argument` and :meth:`~ConsoleApp.add_option` of your just created
:class:`ConsoleApp` instance you can then define the command line arguments and
the :ref:`config options <config-options>` of your application::

    ca.add_argument('argument_name_or_id', help="Help text for this command line argument")
    ca.add_option('option_name_or_id', "help text for this command line option", "default_value")
    ...

After all arguments and config options are defined your application can gather their values with the methods
:meth:`~ConsoleApp.get_argument` and :meth:`~ConsoleApp.get_option` of your :class:`ConsoleApp` instance.

Additional configuration values of your application can be provided by :ref:`INI/CFG files <config-files>`
and gathered with the :class:`ConsoleApp` method :meth:`~ConsoleApp.get_variable`.


Configuration Files, Sections, Variables And Options
----------------------------------------------------

.. _config-files:

Config Files
............

You can create and use separate config files for each of your applications, used system environments and data domains.
A config file consists of config sections, each section provides config variables and config options
for to parametrize your application at run-time.

While the config file names and extensions for data domains can be freely chosen (like any_name.txt), there
are also some hard-coded file names that are recognized:

+----------------------------+---------------------------------------------------+
|  config file               |  used for .... config variables and options       |
+============================+===================================================+
| <any_path_name_and_ext>    |  application/domain specific                      |
+----------------------------+---------------------------------------------------+
| <app_name>.ini             |  application specific (read-/write-able)          |
+----------------------------+---------------------------------------------------+
| <app_name>.cfg             |  application specific (read-only)                 |
+----------------------------+---------------------------------------------------+
| .app_env.cfg               |  application/suite specific (read-only)           |
+----------------------------+---------------------------------------------------+
| .sys_env.cfg               |  general system (read-only)                       |
+----------------------------+---------------------------------------------------+
| .sys_env<SYS_ENV_ID>.cfg   |  the system with SYS_ID (read-only)               |
+----------------------------+---------------------------------------------------+

The config files in the above table are ordered by their preference, so domain specific
config variables/options will always precede/overwrite any application and system
specific config values. Additionally only domain-specific config files can have any
file extension and can be placed into any accessible folder. In contrary all
non-domain-specific config files get only loaded if they are either in the application
installation folder, in the current working directory or up to two levels above
the current working.

.. _config-sections:

Config sections
...............

This module is supporting the `config file format <https://en.wikipedia.org/wiki/INI_file>`_ of
Pythons built-in :class:`~configparser.ConfigParser` class, and also extends it with
:ref:`complex config value types <config-value-types>`.

The following examples shows a config file with two config sections containing one config option (named
`logFile`) and two config variables (`configVar1` and `configVar2`)::

    [aeOptions]
    logFile = './logs/your_log_file.log'

    [YourSectionName]
    configVar1 = ['list-element1', ('list-element2-1', 'list-element2-2', ), dict()]
    configVar2 = {'key1': 'value 1', 'key2': 2222, 'key3': datetime.datetime.now()}

.. _config-main-section:

The ae modules are using the main config section `aeOptions` (defined by :data:`MAIN_SECTION_DEF`)
for to store the values of any pre-defined :ref:`config option <config-options>` and
:ref:`config variables <config-variables>`.

.. _config-variables:

Config Variables
................

Config variables can be defined in any config section and can hold any data type. In the example
config file above the config variable `configVar1` has a list with 3 elements: the first element
is a string the second element is a tuple and the third element is an empty dict.

The complex data type support of this module allows to specify a config value as a string that can be
evaluated with the built-in :func:`eval` function. The value of the evaluated string is taken as the
resulting config value of this config variable.

From within your application simply call the :meth:`~ConsoleApp.get_variable` method with the
name and section names of the config variable for to fetch their config value.

The default value of a config variable can also be set/changed directly from within your application
by calling the :meth:`~ConsoleApp.set_variable` method.

The following pre-defined config variables in the :ref:`main config section <config-main-section>` are recognized
by :mod:`this module <ae.console>` as well as by :mod:`ae.core`.

* `logging_params` : general logging configuration parameters (py and ae logging)
  - :meth:`documented here <core.AppBase.init_logging>`.
* ``py_logging_params`` : configuration parameters for to activate python logging
  - :meth:`documented here <logging.conf.dictConfig>`.
* `logFile` : log file name for ae logging (this is also a config option - set-able as command line arg).


.. _config-options:

Config Options
..............

Config options are config variables that are defined exclusively in the hard-coded section
:data:`aeOptions <MAIN_SECTION_DEF>`. The value of a config option can optionally be given/overwritten
on the command line by adding the option name or id with two leading hyphen characters, followed by an equal
character and the option value)::

    $ your_application --logFile='your_new_log_file.log'

If a command line option is not specified on the command line then :class:`ConsoleApp` is searching if a default value
for this config option got specified either in a config file or in the call of :meth:`~ConsoleApp.add_option`.
The order of this default value search is documented :meth:`here <ConsoleApp.get_option>`.

For to query the resulting value of a config option, simply call the :meth:`~ConsoleApp.get_option` method
of your :class:`ConsoleApp` instance::

    option_value = cae.get_option('option_id')

For to read the default value of a config option or variable directly from the available configuration files use the
:meth:`~ConsoleApp.get_variable` method instead. The default value of a config option or variable can also be
set/changed directly from within your application by calling the :meth:`~ConsoleApp.set_variable` method.

Use the :meth:`~ConsoleApp.set_option` if you want to change the value of a configuration option at run-time.


.. _config-value-types:

Config Value Types
..................

A configuration options can be of any type. With the :paramref:`~ConsoleApp.add_option.value` argument and
:attr:`special encapsulated strings <ae.literal.Literal.value>` you're able to specify any type
for your config options and variables (like dict/list/tuple/datetime/... or any other object type).


Pre-defined Configuration Options
.................................

.. _pre-defined-config-options:

For a more verbose output you can specify on the command line or in one of your configuration files
the pre-defined config option `debugLevel` (or as short option -D) with a value of 2 (for verbose) or 3 (verbose and
with timestamp). The supported config option values are documented :data:`here <ae.core.DEBUG_LEVELS>`.

The value of the second pre-defined config option `logFile` specifies the log file path/file_name, which can
be abbreviated on the command line with the short option -L.


"""
import os
import datetime

import threading
from typing import Any, Callable, Dict, Iterable, Optional, Type, Sequence

from configparser import ConfigParser
from argparse import ArgumentParser, ArgumentError, HelpFormatter, Namespace

from ae.core import (
    DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, DEBUG_LEVELS, DATE_TIME_ISO, DATE_ISO,
    main_app_instance, ori_std_out, sys_env_text, _logger,
    AppBase)
from ae.literal import Literal


INI_EXT: str = '.ini'                   #: INI file extension
MAIN_SECTION_DEF: str = 'aeOptions'     #: default name of main config section

# Lock for to prevent errors in config var value changes and reloads/reads
config_lock = threading.Lock()


class ConsoleApp(AppBase):
    """ provides command line arguments and options, config options, logging and debugging for your application.

    Most applications only need a single instance of this class. Each instance is encapsulating a ConfigParser and
    a ArgumentParser instance. So only apps with threads and different sets of config options for each
    thread could create a separate instance of this class.

    Instance Attributes (ordered alphabetically - ignoring underscore characters):

    * :attr:`_arg_parser`           ArgumentParser instance.
    * :attr:`cfg_opt_choices`       valid choices for pre-/user-defined options.
    * :attr:`cfg_opt_eval_vars`     additional dynamic variable values that are getting set via
      the :paramref:`~.ConsoleApp.cfg_opt_eval_vars` argument of the method :meth:`ConsoleApp.__init__`
      and get then used in the evaluation of :ref:`evaluable config option values <evaluable-literal-formats>`.
    * :attr:`_cfg_files`            iterable of config file names that are getting loaded and parsed (specify
      additional configuration/INI files via the :paramref:`~ConsoleApp.additional_cfg_files` argument).
    * :attr:`cfg_options`           pre-/user-defined options (dict of :class:`~ae.literal.Literal` instances defined
      via :meth:`~ConsoleApp.add_option`).
    * :attr:`_cfg_parser`           ConfigParser instance.
    * :attr:`_main_cfg_fnam`        main config file name.
    * :attr:`_main_cfg_mod_time`    last modification datetime of main config file.
    * :attr:`_cfg_opt_val_stripper` callable to strip option values.
    * :attr:`_parsed_args`          ArgumentParser.parse_args() return.
    """
    def __init__(self, app_title: str = '', app_version: str = '', sys_env_id: str = '',
                 debug_level: int = DEBUG_LEVEL_DISABLED, multi_threading: bool = False, suppress_stdout: bool = False,
                 cfg_opt_eval_vars: Optional[dict] = None, additional_cfg_files: Iterable = (),
                 cfg_opt_val_stripper: Optional[Callable] = None,
                 formatter_class: Optional[Type[HelpFormatter]] = None, epilog: str = "",
                 **logging_params):
        """ initialize a new :class:`ConsoleApp` instance.

        :param app_title:               application title/description (def=value of main module docstring
                                        - :ref:`example <app-title>`).
        :param app_version:             application version (def=value of global __version__ in call stack).
        :param sys_env_id:              system environment id used as file name suffix for to load all
                                        the system config variables in sys_env<suffix>.cfg (def='', pass e.g. 'LIVE'
                                        for to init second ConsoleApp instance with values from sys_envLIVE.cfg).
        :param debug_level:             default debug level (def=DEBUG_LEVEL_DISABLED).
        :param multi_threading:         pass True if instance is used in multi-threading app.
        :param suppress_stdout:         pass True (for wsgi apps) for to prevent any python print outputs to stdout.
        :param cfg_opt_eval_vars:       dict of additional application specific data values that are used in eval
                                        expressions (e.g. AcuSihotMonitor.ini).
        :param additional_cfg_files:    iterable of additional CFG/INI file names (opt. incl. abs/rel. path).
        :param cfg_opt_val_stripper:   callable for to strip/reformat/normalize the option choices values.
        :param formatter_class:         alternative formatter class passed onto ArgumentParser instantiation.
        :param epilog:                  optional epilog text for command line arguments/options help text (passed
                                        onto ArgumentParser instantiation).
        :param logging_params:          all other kwargs are interpreted as logging configuration values - the
                                        supported kwargs are all the method kwargs of
                                        :meth:`~core.AppBase.init_logging`.
        """
        super().__init__(app_title=app_title, app_version=app_version, sys_env_id=sys_env_id,
                         debug_level=debug_level, multi_threading=multi_threading, suppress_stdout=suppress_stdout)

        with config_lock:
            self._cfg_parser: ConfigParser = ConfigParser()                 #: ConfigParser instance
            self.cfg_options: Dict[str, Literal] = dict()                   #: all config options
            self.cfg_opt_choices: Dict[str, Sequence] = dict()              #: all valid config option choices
            self.cfg_opt_eval_vars: dict = cfg_opt_eval_vars or dict()      #: app-specific vars for init of cfg options

            # prepare config files, including determine default config file (last existing INI/CFG file) for
            # .. to write to and if there is no INI file at all then create on demand a <app_name>.INI file in the cwd
            self._cfg_files: list = list()                                  #: list of all found INI/CFG files
            self._main_cfg_fnam: Optional[str] = None                       #: main config file name
            self._main_cfg_mod_time: Optional[int] = None                   #: main config file modification datetime
            self.add_cfg_files(additional_cfg_files)
            self._cfg_opt_val_stripper: Optional[Callable] = cfg_opt_val_stripper
            #: callable to strip or normalize config option choice values

            self._parsed_args: Optional[Namespace] = None
            """ used for to retrieve command line args and also as a flag (if is not None) for to ensure that
            the command line arguments get re-parsed if :meth:`~ConsoleApp.add_option` get called after a first
            method call which is initiating the re-fetch of the args and INI/cfg vars 
            (like e.g. :meth:`~ConsoleApp.get_option` or :meth:`ConsoleApp.debug_out`). 
            """
        self.load_cfg_files()

        log_file_name = self._init_logging(logging_params)

        self.po(self.app_name, " V", app_version, " Startup", self.startup_beg, self.app_title, logger=_logger)
        self.po("####  Initialization......  ####", logger=_logger)

        # prepare argument parser
        formatter_class = formatter_class or HelpFormatter
        self._arg_parser: ArgumentParser = ArgumentParser(
            description=self.app_title, epilog=epilog, formatter_class=formatter_class)   #: ArgumentParser instance
        self.add_argument = self._arg_parser.add_argument       #: redirect this method to our ArgumentParser instance

        # create pre-defined config options
        self.add_opt('debugLevel', "Verbosity of debug messages send to console and log files", debug_level, 'D',
                     choices=DEBUG_LEVELS.keys())
        if log_file_name is not None:
            self.add_opt('logFile', "Log file path", log_file_name, 'L')

    def _init_logging(self, logging_params: Dict[str, Any]) -> Optional[str]:
        """ determine and init logging config.

        :param logging_params:      logging config dict passed as args by user that will be amended with cfg values.
        :return:                    None if py logging is active, log file name if ae logging is set in cfg or args
                                    or empty string if no logging got configured in cfg/args.

        The logging configuration can be specified in several alternative places. The precedence
        on various existing configurations is (highest precedence first):

        * :ref:`logFile  <pre-defined-config-options>` :ref:`configuration option <config-options>` specifies
          the name of the used ae log file (will be read after initialisation of this app instance)
        * `logging_params` :ref:`configuration variable <config-variables>` dict with a `py_logging_params` key
          for to activate python logging
        * `logging_params` :ref:`configuration variable <config-variables>` dict with the ae log file name
          in the key `log_file_name`
        * `py_logging_params` :ref:`configuration variable <config-variables>` for to use the python logging module
        * `logFile` :ref:`configuration variable <config-variables>` specifying ae log file
        * :paramref:`~_init_logging.logging_params` dict passing the python logging configuration in the
          key `py_logging_params` to this method
        * :paramref:`~_init_logging.logging_params` dict passing the ae log file in the logging
          key `log_file_name` to this method

        """
        log_file_name = ""
        cfg_logging_params = self.get_var('logging_params')
        if cfg_logging_params:
            logging_params = cfg_logging_params
            if 'py_logging_params' not in logging_params:                       # .. there then cfg py_logging params
                log_file_name = logging_params.get('log_file_name', '')         # .. then cfg logging_params log file
        if 'py_logging_params' not in logging_params and not log_file_name:
            lcd = self.get_var('py_logging_params')
            if lcd:
                logging_params['py_logging_params'] = lcd                       # .. then cfg py_logging params directly
            else:
                log_file_name = self.get_var('logFile', default_value=logging_params.get('log_file_name', ''))
                logging_params['log_file_name'] = log_file_name                 # .. finally cfg logFile or log file arg
        super().init_logging(**logging_params)

        return None if 'py_logging_params' in logging_params else log_file_name

    def __del__(self):
        """ deallocate this app instance by calling :func:`AppBase.shutdown`. """
        self.shutdown(exit_code=None)

    def add_argument(self, *args, **kwargs):
        """ define new command line argument.

        Original/underlying args/kwargs of :class:`argparse.ArgumentParser` are used - please see the
        description/definition of :meth:`~argparse.ArgumentParser.add_argument`.

        This method has an alias named :meth:`add_arg`.
        """
        # ### THIS METHOD DEF GOT CODED HERE ONLY FOR SPHINX DOCUMENTATION BUILD PURPOSES ###
        # .. this method get never called because gets overwritten with self._arg_parser.add_argument in __init__().
        self._arg_parser.add_argument(*args, **kwargs)

    add_arg = add_argument      #: alias of method :meth:`.add_argument`

    def get_argument(self, name: str) -> Any:
        """ determine the command line parameter value.

        :param name:    Argument id of the parameter.
        :return:        Value of the parameter.

        This method has an alias named :meth:`get_arg`.
        """
        if not self._parsed_args:
            self._parse_args()
        return getattr(self._parsed_args, name)

    get_arg = get_argument      #: alias of method :meth:`.get_argument`

    def add_option(self, name, desc, value, short_opt=None, choices=None, multiple=False):
        """ defining and adding a new config option for this app.

        :param name:        string specifying the option id and short description of this new option.
                            The name value will also be available as long command line argument option (case-sens.).
        :param desc:        description and command line help string of this new option.
        :param value:       default value and the type of the option. This value will be used only if the config values
                            are not specified in any config file. The command line argument option value
                            will always overwrite this value (and any value in any config file).
        :param short_opt:   short option character. If not passed or passed as '' then the first character of the name
                            will be used. Please note that the short options 'D' and 'L' are already used internally
                            by :class:`ConsoleApp` (recommending using lower-case options for your application).
        :param choices:     list of valid option values (optional, default=allow all values).
        :param multiple:    True if option can be added multiple times to command line (optional, default=False).

        The value of a config option can be of any type and gets represented by an instance of the
        :class:`~ae.literal.Literal` class. Supported value types and literals are documented
        :attr:`here <ae.literal.Literal.value>`.

        This method has an alias named :meth:`add_opt`.
        """
        self._parsed_args = None        # request (re-)parsing of command line args
        if short_opt == '':
            short_opt = name[0]

        args = list()
        if short_opt and len(short_opt) == 1:
            args.append('-' + short_opt)
        args.append('--' + name)

        # determine config value for to use as default for command line arg
        option = Literal(literal_or_value=value, name=name)
        cfg_val = self._get_cfg_parser_val(name, default_value=value)
        option.value = cfg_val
        kwargs = dict(help=desc, default=cfg_val, type=option.convert_value, choices=choices, metavar=name)
        if multiple:
            kwargs['type'] = option.append_value
            if choices:
                kwargs['choices'] = None    # for multiple options this instance need to check the choices
                self.cfg_opt_choices[name] = choices

        self._arg_parser.add_argument(*args, **kwargs)

        self.cfg_options[name] = option

    add_opt = add_option    #: alias of method :meth:`.add_option`

    def get_option(self, name: str, default_value: Optional[Any] = None) -> Any:
        """ get the value of a config option specified by it's name (option id).

        The returned value has the same type as the value specified in the :meth:`add_option` call and
        gets taken either from the command line, the default section (:data:`MAIN_SECTION_DEF`) of any found
        config variable file (with file extension INI or CFG) or from the default values specified in your python code.

        Underneath you find the order of the value search - the first specified/found value will be returned:

        #. command line arguments option value
        #. :ref:`config files <config-files>` added in your app code via one of the methods :meth:`.add_cfg_file` or
           :meth:`add_cfg_files` (these files will be searched for the config option value in reversed order - so the
           last added :ref:`config file <config-files>` will be the first one where the config option will be searched)
        #. :ref:`config files <config-files>` added via :paramref:`~ConsoleApp.additional_cfg_files` argument of
           :meth:`ConsoleApp.__init__` (searched in the reversed order)
        #. <app_name>.INI file in the <cwd>
        #. <app_name>.CFG file in the <cwd>
        #. <app_name>.INI file in the <app_dir>
        #. <app_name>.CFG file in the <app_dir>
        #. .sys_env.cfg in the <cwd>
        #. .sys_env<sys_env_id>.cfg in the <cwd>
        #. .app_env.cfg in the <cwd>
        #. .sys_env.cfg in the parent folder of the <cwd>
        #. .sys_env<sys_env_id>.cfg in the parent folder of the <cwd>
        #. .app_env.cfg in the parent folder of the <cwd>
        #. .sys_env.cfg in the <app_dir>
        #. .sys_env<sys_env_id>.cfg in the <app_dir>
        #. .app_env.cfg in the <app_dir>
        #. .sys_env.cfg in the parent folder of the parent folder of the <cwd>
        #. .sys_env<sys_env_id>.cfg in the parent folder of the parent folder of the <cwd>
        #. .app_env.cfg in the parent folder of the parent folder of the <cwd>
        #. value argument passed into the add_opt() method call (defining the option)
        #. default_value argument passed into this method (only if :class:`~ConsoleApp.add_option` didn't get called)

        **Placeholders in the above search order lists are**:

        * *<cwd>* is the current working directory of your application (determined with :func:`os.getcwd`)
        * *<app_name>* is the base name without extension of your main python code file.
        * *<app_dir>* is the application directory (where your <app_name>.py or the exe file of your app is situated)
        * *<sys_env_id>* is specified as argument of :meth:`ConsoleApp.__init__`

        :param name:            id of the config option.
        :param default_value:   default value of the option (if not defined with :class:`~ConsoleApp.add_option`).

        :return:                first found value of the option identified by :paramref:`~ConsoleApp.get_option.name`.

        This method has an alias named :meth:`get_opt`.
        """
        if not self._parsed_args:
            self._parse_args()
        return self.cfg_options[name].value if name in self.cfg_options else default_value

    get_opt = get_option    #: alias of method :meth:`.get_option`

    def show_help(self):
        """ show help message on console output/stream.

        Original/underlying args/kwargs are used - please see description/definition of
        :meth:`~argparse.ArgumentParser.print_help` of :class:`~argparse.ArgumentParser`.
        """
        self._arg_parser.print_help(file=ori_std_out)

    def _parse_args(self):
        """ parse all command line args.

        This method get normally only called once and after all the options have been added with :meth:`add_option`.
        :meth:`add_option` will then set the determined config file value as the default value and then the
        following call of this method will overwrite it with command line argument value, if given.
        """
        self._parsed_args = self._arg_parser.parse_args()

        for name in self.cfg_options.keys():
            self.cfg_options[name].value = getattr(self._parsed_args, name)
            if name in self.cfg_opt_choices:
                for given_value in self.cfg_options[name].value:
                    if self._cfg_opt_val_stripper:
                        given_value = self._cfg_opt_val_stripper(given_value)
                    allowed_values = self.cfg_opt_choices[name]
                    if given_value not in allowed_values:
                        raise ArgumentError(None, "Wrong {} option value {}; allowed are {}"
                                            .format(name, given_value, allowed_values))

        is_main_app = main_app_instance() is self
        if is_main_app and not self.py_log_params:
            self._log_file_name = self.cfg_options['logFile'].value
            if self._log_file_name:
                self.log_file_check()

        # finished argument parsing - now print chosen option values to the console
        debug_level = self.cfg_options['debugLevel'].value
        if debug_level >= DEBUG_LEVEL_ENABLED:
            self.po("  ##  Debug Level(" + ", ".join([str(k) + "=" + v for k, v in DEBUG_LEVELS.items()]) + "):",
                    debug_level, logger=_logger)
            # print sys env - s.a. pyinstaller docs (http://pythonhosted.org/PyInstaller/runtime-information.html)
            if self.sys_env_id or not is_main_app:
                self.po(" ###  Initialized ConsoleApp instance for system env id", self.sys_env_id, logger=_logger)
            self.po("  ##  System Environment:", logger=_logger)
            self.po(sys_env_text(extra_sys_env_dict={'main cfg': self._main_cfg_fnam}), logger=_logger)

        self.startup_end = datetime.datetime.now()
        self.po(self.app_name, " V", self.app_version, "  Args  parsed", self.startup_end, logger=_logger)
        if not is_main_app and not self.sys_env_id:
            self.po("  **  Additional instance of ConsoleApp requested with empty system environment ID",
                    logger=_logger)
        self.po("####  Startup finished....  ####", logger=_logger)
        self.startup_end = datetime.datetime.now()

    def set_option(self, name: str, value: Any, cfg_fnam: Optional[str] = None, save_to_config: bool = True) -> str:
        """ set or change the value of a config option.

        :param name:            id of the config option to set.
        :param value:           value to assign to the option, identified by :paramref:`~set_option.name`.
        :param cfg_fnam:        config file name to save new option value. If not specified then the
                                default file name of :meth:`~ConsoleApp.set_variable` will be used.
        :param save_to_config:  pass False to prevent to save the new option value also to a config file.
                                The value of the config option will be changed in any case.
        :return:                ''/empty string on success else error message text.

        This method has an alias named :meth:`set_opt`.
        """
        self.cfg_options[name].value = value
        if name == 'debugLevel':
            self.debug_level = value
        return self.set_var(name, value, cfg_fnam) if save_to_config else ''

    set_opt = set_option    #: alias of method :meth:`.set_option`

    def add_cfg_file(self, cfg_file_name: str) -> bool:
        """ add :paramref:`~add_cfg_file.cfg_file_name` to the recognized :attr:`config files <ConsoleApp._cfg_files>`.

        :param cfg_file_name:   new config file name to add.
        :return:                True, if passed config file exists and was not in the list before, else False.
        """
        if cfg_file_name not in self._cfg_files and os.path.isfile(cfg_file_name):
            self._cfg_files.append(cfg_file_name)
            return True
        return False

    def add_cfg_files(self, additional_cfg_files: Iterable = ()) -> str:
        """ extend list of found config files (in :attr:`~ConsoleApp.config_files`).

        :param additional_cfg_files:    additional/user-defined config files.
        :return:                        ""/empty string on success else error message text.
        """
        cwd_path = os.getcwd()
        app_path = self._app_path
        app_name = self.app_name

        # prepare config env, first compile cfg/ini files - the last one overwrites previously loaded values
        cwd_path_fnam = os.path.join(cwd_path, app_name)
        self._main_cfg_fnam = cwd_path_fnam + INI_EXT  # default will be overwritten by load_cfg_files()
        sys_env_id = self.sys_env_id or 'TEST'
        for cfg_path in (os.path.join(cwd_path, '..', '..'), app_path, os.path.join(cwd_path, '..'), cwd_path, ):
            for cfg_file in ('.app_env.cfg', '.sys_env' + sys_env_id + '.cfg', '.sys_env.cfg', ):
                self.add_cfg_file(os.path.join(cfg_path, cfg_file))

        app_path_fnam = os.path.join(app_path, app_name)
        for cfg_file in (app_path_fnam + '.cfg', app_path_fnam + INI_EXT,
                         cwd_path_fnam + '.cfg', cwd_path_fnam + INI_EXT):
            self.add_cfg_file(cfg_file)

        err_msg = ""
        for cfg_fnam in additional_cfg_files:
            add_cfg_path_fnam = os.path.join(cwd_path, cfg_fnam)
            if not self.add_cfg_file(add_cfg_path_fnam):
                add_cfg_path_fnam = os.path.join(app_path, cfg_fnam)
                if not self.add_cfg_file(add_cfg_path_fnam):
                    err_msg = "Additional config file {} not found!".format(cfg_fnam)
        return err_msg

    def _get_cfg_parser_val(self, name: str, section: Optional[str] = None, default_value: Optional[Any] = None,
                            cfg_parser: Optional[ConfigParser] = None) -> Any:
        """ determine thread-safe the value of a config variable from the config file.

        :param name:            name/option_id of the config variable.
        :param section:         name of the config section (def= :data:`MAIN_SECTION_DEF` also if passed as None/'')
        :param default_value:   default value to return if config value is not specified in any config file.
        :param cfg_parser:      ConfigParser instance to use (def=self._cfg_parser).
        :return:                value of the config variable.
        """
        with config_lock:
            cfg_parser = cfg_parser or self._cfg_parser
            val = cfg_parser.get(section or MAIN_SECTION_DEF, name, fallback=default_value)
        return val

    def load_cfg_files(self):
        """ load and parse all config files.
        """
        with config_lock:
            for cfg_fnam in reversed(self._cfg_files):
                if cfg_fnam.endswith(INI_EXT) and os.path.isfile(cfg_fnam):
                    self._main_cfg_fnam = cfg_fnam
                    self._main_cfg_mod_time = os.path.getmtime(self._main_cfg_fnam)
                    break

            self._cfg_parser.optionxform = str      # or use 'lambda option: option' to have case sensitive var names
            self._cfg_parser.read(self._cfg_files, encoding='utf-8')

    def is_main_cfg_file_modified(self) -> bool:
        """ determine if main config file got modified.

        :return:    True if the content of the main config file got modified/changed.
        """
        return self._main_cfg_mod_time and os.path.getmtime(self._main_cfg_fnam) > self._main_cfg_mod_time

    def get_variable(self, name: str, section: Optional[str] = None, default_value: Optional[Any] = None,
                     cfg_parser: Optional[ConfigParser] = None, value_type: Optional[Type] = None) -> Any:
        """ get the value of a config variable.

        :param name:            name of the :ref:`config variable <config-variables>`
                                or id of :ref:`config option <config-options>`.
        :param section:         name of the :ref:`config section <config-sections>` (def= :data:`MAIN_SECTION_DEF`).
        :param default_value:   default value to return if config value is not specified in any config file.
        :param cfg_parser:      ConfigParser instance to use (def= :attr:`~ConsoleApp._cfg_parser`).
        :param value_type:      type of the config value.
        :return:                value of the config variable or of the config option (the latter only
                                if the passed string in :paramref:`~get_variable.name` is the id of a defined
                                config option and the :paramref:`~get_variable.section` is either empty or
                                equal to the value of :data:`MAIN_SECTION_DEF`.

        This method has an alias named :meth:`get_var`.
        """
        if name in self.cfg_options and section in (MAIN_SECTION_DEF, '', None):
            val = self.cfg_options[name].value
        else:
            s = Literal(literal_or_value=default_value, value_type=value_type, name=name)  # used for conversion/eval
            s.value = self._get_cfg_parser_val(name, section=section, default_value=s.value, cfg_parser=cfg_parser)
            val = s.value
        return val

    get_var = get_variable      #: alias of method :meth:`.get_variable`

    def set_variable(self, name: str, value: Any, cfg_fnam: Optional[str] = None, section: Optional[str] = None) -> str:
        """ set/change the value of a :ref:`config variable <config-variables>` and if exists the related config option.

        If the passed string in :paramref:`~set_variable.name` is the id of a defined
        :ref:`config option <config-options>` and :paramref:`~set_variable.section` is either empty or
        equal to the value of :data:`MAIN_SECTION_DEF` then the value of this
        config option will be changed too.

        :param name:            name/option_id of the config value to set.
        :param value:           value to assign to the config value, specified by the
                                :paramref:`~set_variable.name` argument.
        :param cfg_fnam:        file name (def= :attr:`~ConsoleApp._main_cfg_fnam`) to save the new option value to.
        :param section:         name of the config section (def= :data:`MAIN_SECTION_DEF`).
        :return:                ''/empty string on success else error message text.

        This method has an alias named :meth:`set_var`.
        """
        msg = "****  ConsoleApp.set_var({}, {}) ".format(name, value)
        if not cfg_fnam:
            cfg_fnam = self._main_cfg_fnam
        if not section:
            section = MAIN_SECTION_DEF

        if name in self.cfg_options and section in (MAIN_SECTION_DEF, '', None):
            self.cfg_options[name].value = value

        if not os.path.isfile(cfg_fnam):
            return msg + "INI/CFG file {} not found. Please set the ini/cfg variable {}/{} manually to the value " \
                .format(cfg_fnam, section, name, value)

        err_msg = ''
        with config_lock:
            try:
                cfg_parser = ConfigParser()     # not using self._cfg_parser for to put INI vars from other files
                cfg_parser.optionxform = str    # or use 'lambda option: option' to have case sensitive var names
                cfg_parser.read(cfg_fnam)
                if isinstance(value, (dict, list, tuple)):
                    str_val = "'''" + repr(value).replace('%', '%%') + "'''"
                elif type(value) is datetime.datetime:
                    str_val = value.strftime(DATE_TIME_ISO)
                elif type(value) is datetime.date:
                    str_val = value.strftime(DATE_ISO)
                else:
                    str_val = str(value)    # using str() here because repr() will put high-commas around string values
                cfg_parser.set(section, name, str_val)
                with open(cfg_fnam, 'w') as configfile:
                    cfg_parser.write(configfile)
            except Exception as ex:
                err_msg = msg + "exception: {}".format(ex)

        return err_msg

    set_var = set_variable  #: alias of method :meth:`.set_variable`

    def debug_out(self, *objects, minimum_debug_level: int = DEBUG_LEVEL_VERBOSE, **kwargs):
        """ special debug version of :func:`builtin print() function <print>`.

        This method will print-out the passed objects only if the :attr:`current debug level
        <ae.core.AppBase.debug_level>` of this app instance is higher than the value passed into the
        :paramref:`~debug_out.minimum_debug_level` argument. In this case the print-out will be
        delegated onto the :meth:`~ae.core.AppBase.print_out` method of the :class:`~ae.core.AppBase` class.

        :param objects:                 objects to be printed out.
        :param minimum_debug_level:     minimum debug level for to print the passed objects.
        :param kwargs:                  The :paramref:`~ae.core.AppBase.print_out.file` argument is documented
                                        at the :meth:`~ae.core.AppBase.print_out` method of the
                                        :class:`~ae.core.AppBase` class. All other supported kwargs of this method
                                        are documented at the :func:`print_out() function <ae.core.print_out>`
                                        of the :mod:`~ae.core` module.

        This method has an alias named :meth:`.dpo`.
        """
        if self.debug_level >= minimum_debug_level:
            self.po(*objects, **kwargs)

    dpo = debug_out         #: alias of method :meth:`.debug_out`
