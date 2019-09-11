"""
console application environment
===============================

Basic Usage
-----------

First create an instance of the class :class:`ConsoleApp` in your main application module, specifying
at least the version string and the title of your application::

    from ae.console_app import ConsoleApp

    cae = ConsoleApp('0.1.2dev', "My Application Title")

Then define the command line arguments and the configuration options of your application with the methods
:meth:`~ConsoleApp.add_argument` and :meth:`~ConsoleApp.add_option` of your just created
:class:`ConsoleApp` instance::

    cae.add_argument('argument_name_or_id', help="Help text for this command line argument")
    cae.add_option('option_name_or_id', "help text for this command line option", "default_value")
    ...

After all arguments and options are defined your application can gather their values with the methods
:meth:`~ConsoleApp.get_argument` and :meth:`~ConsoleApp.get_option` of your :class:`ConsoleApp` instance.



Configuration Options
---------------------

The value of a configuration option (defined with :meth:`~ConsoleApp.add_option`) can be either set
directly on the command line like so (by adding the option name or id with two leading hyphen characters,
followed by an equal character and the option value)::

    $ my_application --option_id=option_value

If a command line option is not specified on the command line then :class:`ConsoleApp` is searching if an
option default value got specified either in a configuration file or in the call of :meth:`ConsoleApp.add_option`.
The order of this default value search is documented :meth:`here <ConsoleApp.get_option>`.

For to query the resulting value of an option, simply call the :meth:`ConsoleApp.get_option`::

    option_value = cae.get_option('option_id')

For to read the default values of a configuration option directly from the configuration files use the
:meth:`ConsoleApp.get_config` method. This value can also be set/changed directly from within your application by
calling the :meth:`ConsoleApp.set_config` method (which will store the new default value into your
main configuration file).


Pre-defined Configuration Options
.................................

For a more verbose output you can specify on the command line or in one of your configuration files
the `ConsoleApp.debugLevel` option (or as short option -D) with a value of 2 (for verbose) or 3 (verbose and
with timestamp). The supported option values are documented :data:`here <ae.core.DEBUG_LEVELS>`.

The value of the second pre-defined option :data:`ConsoleApp.logFile` specifies the log file name.


Enable Logging
--------------


Enable Multi-Thread-Safety
--------------------------

"""
import sys
import os
import datetime

import threading
from typing import Any, AnyStr, Callable, Dict, Iterable, Optional, TextIO, Type, Sequence
import weakref

from configparser import ConfigParser
from argparse import ArgumentParser, ArgumentError, HelpFormatter, Namespace

import logging
import logging.config

from ae.core import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, DEBUG_LEVEL_TIMESTAMPED, \
    DEBUG_LEVELS, LOGGING_LEVELS, DATE_TIME_ISO, DATE_ISO, calling_module, force_encoding, sys_env_text, to_ascii
from ae.setting import Setting

INI_EXT: str = '.ini'                       #: INI file extension

MAIN_SECTION_DEF: str = 'aeOptions'         #: default name of main config section

MAX_NUM_LOG_FILES: int = 69                 #: maximum number of log files

# global Locks for to prevent errors in log file rotation, config reloads and config reads
log_file_rotation_lock = threading.Lock()
config_lock = threading.Lock()
config_read_lock = threading.Lock()


# The following line is throwing an error in the Sphinx docs make:
# app_instances: weakref.WeakValueDictionary[str, "ConsoleApp"] = weakref.WeakValueDictionary() #: dict of app instances
app_instances = weakref.WeakValueDictionary()   # type: weakref.WeakValueDictionary[str, ConsoleApp]
""" `app_instances` is holding the references for all :class:`ConsoleApp` instances created at run time.

The first created :class:`ConsoleApp` instance is called the main app instance and has an empty string as the dict key.
This weak dict gets automatically initialized in :func:`ConsoleApp.__init__` for to allow log file split/rotation
and debugLevel access at module level.
"""


def main_app_instance() -> Optional["ConsoleApp"]:
    """ determine the main instance of the :class:`ConsoleApp` in the current running application.

    :return:    main :class:`~ae.console_app.ConsoleApp` instance or None (if app is not fully initialized yet).
    """
    return app_instances.get('')


def _get_debug_level() -> int:
    """ determining the debug level of the main :class:`ConsoleApp` instance of the currently running app.

    :return: current debug level.
    """
    main_instance = main_app_instance()
    if main_instance and 'debugLevel' in main_instance.config_options:
        return main_instance.config_options['debugLevel'].value
    return DEBUG_LEVEL_DISABLED


# save original stdout/stderr
ori_std_out = sys.stdout
ori_std_err = sys.stderr
app_std_out = ori_std_out
app_std_err = ori_std_err


class _DuplicateSysOut:
    """ private helper class used by :class:`ConsoleApp` for to duplicate the standard output stream to an log file.
    """
    def __init__(self, log_file_obj: TextIO, sys_out_obj: TextIO = ori_std_out) -> None:
        """ initialise a new T-stream-object

        :param log_file_obj:    log file stream.
        :param sys_out_obj:     standard output stream (def=sys.stdout)
        """
        self.log_file_obj = log_file_obj
        self.sys_out_obj = sys_out_obj

    def write(self, message: AnyStr) -> None:
        """ write string to log and standard output streams.

        :param message:     string to output.
        """
        if self.log_file_obj and not self.log_file_obj.closed:
            try:
                self.log_file_obj.write(message)
            except UnicodeEncodeError:
                # log file has different encoding than console, so simply replace with backslash
                self.log_file_obj.write(force_encoding(message, encoding=self.log_file_obj.encoding))
        if not self.sys_out_obj.closed:
            self.sys_out_obj.write(message)

    def __getattr__(self, attr: str) -> object:
        """ get attribute value from standard output stream.

        :param attr:    name of the attribute to retrieve/return.
        :return:        value of the attribute.
        """
        return getattr(self.sys_out_obj, attr)


_logger = None       #: python logger for this module gets lazy/late initialized and only if requested by caller


def logger_late_init():
    """ check if logging modules got initialized already and if not then do it now. """
    global _logger
    if not _logger:
        _logger = logging.getLogger(__name__)


def uprint(*objects, sep: str = " ", end: str = "\n", file: Optional[TextIO] = None, flush: bool = False,
           encode_errors_def: str = 'backslashreplace', debug_level: Optional[int] = None,
           logger: Optional['logging.Logger'] = None, cae_instance: Optional['ConsoleApp'] = None,
           **kwargs) -> None:
    """ universal/unbreakable print function - replacement for the python print() built-in.

    This method is silently handling and auto-correcting string encode errors for output streams which are
    not supporting unicode. Any instance of :class:`ConsoleApp` is providing this function as a method with the
    :func:`same name <ConsoleApp.uprint>`). It is recommended to call/use the instance method instead of this function.

    :param objects:             tuple of objects to be printed.
    :param sep:                 separator character between each printed object/string (def=" ").
    :param end:                 finalizing character added to the end of this print (def="\\\\n").
    :param file:                output stream object to be printed to (def=None which will use standard output streams).
    :param flush:               flush stream after printing (def=False).
    :param encode_errors_def:   default error handling for to encode (def='backslashreplace').
    :param debug_level:         current debug level (def=None).
    :param logger:              used logger for to output `objects` (def=None).
    :param cae_instance:        used instance of :class:`ConsoleApp` (def=None which trying to use the main instance).
    :param kwargs:              additional kwargs dict (items will be printed to the output stream).
    """
    processing = end == "\r"
    if not file:
        # app_std_out cannot be specified as file argument default because get initialized after import of this module
        # .. within ConsoleApp._open_log_file(). Use ori_std_out for animation prints (see tcp.py/TcpServer.run()).
        file = ori_std_out if processing else app_std_out
    enc = file.encoding

    if cae_instance is None:
        cae_instance = main_app_instance()
    if cae_instance is not None:
        if getattr(cae_instance, 'multi_threading', False):            # add thread ident
            objects = (" <{: >6}>".format(threading.get_ident()),) + objects
        if getattr(cae_instance, '_log_file_obj', False):
            # creating new log file and backup of current one if the current one has more than 20 MB in size
            cae_instance.log_file_check_rotation()

    # even with enc == 'UTF-8' and because of _DuplicateSysOut is also writing to file it raises the exception:
    # ..UnicodeEncodeError: 'charmap' codec can't encode character '\x9f' in position 191: character maps to <undefined>
    # if enc == 'UTF-8':
    #     print(*objects, sep=sep, end=end, file=file, flush=flush)
    # else:
    #     print(*map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), objects),
    #           sep=sep, end=end, file=file, flush=flush)
    if _get_debug_level() >= DEBUG_LEVEL_TIMESTAMPED:
        objects = (datetime.datetime.now().strftime(DATE_TIME_ISO),) + objects

    if kwargs:
        objects += ("\n   *  EXTRA KWARGS={}".format(kwargs),)

    use_logger = not processing and debug_level in LOGGING_LEVELS \
        and getattr(cae_instance, 'logging_conf_dict', False)
    if use_logger and logger is None:
        logger_late_init()
        module = calling_module()
        logger = logging.getLogger(module) if module else _logger

    retries = 2
    while retries:
        try:
            print_strings = map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), objects)
            if use_logger or getattr(cae_instance, 'multi_threading', False):
                # prevent fluttered log file content by concatenating objects and adding end value
                # .. see https://stackoverflow.com/questions/3029816/how-do-i-get-a-thread-safe-print-in-python-2-6
                # .. and https://stackoverflow.com/questions/50551637/end-key-in-print-not-thread-safe
                print_one_str = sep.join(print_strings)
                sep = ""
                if end and not use_logger:
                    print_one_str += end
                    end = ""
                print_strings = (print_one_str,)

            if use_logger:
                logger.log(level=LOGGING_LEVELS[debug_level], msg=print_strings[0])
            else:
                print(*print_strings, sep=sep, end=end, file=file, flush=flush)
            break
        except UnicodeEncodeError:
            fixed_objects = list()
            for obj in objects:
                if not isinstance(obj, str) and not isinstance(obj, bytes):
                    obj = str(obj)
                if retries == 2:
                    obj = force_encoding(obj, encoding=enc)
                else:
                    obj = to_ascii(obj)
                fixed_objects.append(obj)
            objects = fixed_objects
            retries -= 1


class ConsoleApp:
    """ provides easy console arguments and options, configuration options, logging and debugging for your application.

    Most applications only need a single instance of this class. Each instance is encapsulating a ConfigParser and
    a ArgumentParser instance. So only apps with threads and different sets of configuration options for each
    thread have to create a separate instance of this class.

    Instance Attributes (ordered alphabetically - ignoring underscore characters):

    * :attr:`_app_name`             basename (without the file name extension) of the executable.
    * :attr:`_app_path`             file path of executable.
    * :attr:`_app_version`          application version (set via the :paramref:`ConsoleApp.__init__.app_version` arg).
    * :attr:`_arg_parser`           internal ArgumentParser instance.
    * :attr:`config_choices`        valid choices for pre-/user-defined options.
    * :attr:`config_eval_vars`      additional values used for the evaluation of special formatted config option values
      (set via the :paramref:`~.__init__.config_eval_vars` argument of the method :meth:`ConsoleApp.__init__`).
    * :attr:`_config_files`         iterable of config file names that are getting loaded and parsed (specify
      additional configuration/INI files via :paramref:`.__init__.additional_cfg_files`).
    * :attr:`config_options`        pre-/user-defined options (dict of Setting instances defined via
      :meth:`~ConsoleApp.add_option`).
    * :attr:`_config_parser`        internal instance of used ConfigParser.
    * :attr:`_log_file_index`       index of the current rotation log file backup.
    * :attr:`_log_file_max_size`    maximum size in MBytes of a log file.
    * :attr:`_log_file_name`        path and file name of the log file.
    * :attr:`_log_file_obj`         file handle of currently opened log file (opened in :meth:~ConsoleApp._parse_args`).
    * :attr:`logging_conf_dict`     python logging config dict.
    * :attr:`_main_cfg_fnam`        main config file name.
    * :attr:`_main_cfg_mod_time`    last modification datetime of main config file.
    * :attr:`multi_threading`       set to True if your application uses threads.
    * :attr:`_nul_std_out`          null stream used for to prevent printouts on stdout of the console/shell.
    * :attr:`_option_value_stripper` callable to strip option values.
    * :attr:`_parsed_args`          ArgumentParser.parse_args() return.
    * :attr:`_shut_down`            flag set to True if application shutdown was already processed.
    * :attr:`startup_beg`           datetime of app instantiation/startup.
    * :attr:`suppress_stdout`       flag set to True if application does not print to stdout/console.
    * :attr:`sys_env_id`            system environment id of this instance.
    """
    def __init__(self, app_version: str, app_desc: str, debug_level_def: int = DEBUG_LEVEL_DISABLED,
                 config_eval_vars: Optional[dict] = None, additional_cfg_files: Iterable = (),
                 option_value_stripper: Optional[Callable] = None, multi_threading: bool = False,
                 suppress_stdout: bool = False, formatter_class: Optional[Type[HelpFormatter]] = None, epilog: str = "",
                 sys_env_id: str = '', logging_config: Optional[Dict[str, Any]] = None):
        """ initialize a new :class:`ConsoleApp` instance.

        :param app_version:             application version.
        :param app_desc:                application description.
        :param debug_level_def:         default debug level (DEBUG_LEVEL_DISABLED).
        :param config_eval_vars:        dict of additional application specific data values that are used in eval
                                        expressions (e.g. AcuSihotMonitor.ini).
        :param additional_cfg_files:    iterable of additional CFG/INI file names (opt. incl. abs/rel. path).
        :param option_value_stripper:   callable/function for to strip/reformat Setting option value for validation.
        :param multi_threading:         pass True if instance is used in multi-threading app.
        :param suppress_stdout:         pass True (for wsgi apps) for to prevent any python print outputs to stdout.
        :param formatter_class:         alternative formatter class passed onto ArgumentParser instantiation.
        :param epilog:                  optional epilog text for command line arguments/options help text (passed
                                        onto ArgumentParser instantiation).
        :param sys_env_id:              system environment id used as file name suffix for to load all
                                        the system config variables in sys_env<suffix>.cfg (def='', pass e.g. 'LIVE'
                                        for to init second ConsoleApp instance with values from sys_envLIVE.cfg).
        :param logging_config:          dict with logging configuration values - supported dict keys are:

                                        * `py_logging_config_dict`: config dict for python logging configuration.
                                          If this inner dict is not empty then python logging is configured with the
                                          given options and all the other keys underneath are ignored.
                                        * `file_name_def`: default log file name for internal logging (def='').
                                        * `file_size_max`: max. size in MBytes of internal log file (def=20).
        """
        global app_instances
        main_instance = main_app_instance()
        if main_instance is None:
            app_instances[''] = main_instance = self
        self.sys_env_id: str = sys_env_id                                   #: system environment id of this instance
        if sys_env_id not in app_instances:
            app_instances[sys_env_id] = self

        self._parsed_args: Optional[Namespace] = None
        """ used for to retrieve command line args and also as a flag for to ensure that the command line arguments
        get re-parsed if :meth:`~ConsoleApp.add_option` get called after a first call to methods which are initiating
        the re-fetch of the args and INI/cfg vars (like e.g. :meth:`~ConsoleApp.get_option` or
        :meth:`ConsoleApp.dprint`). """

        self._nul_std_out: Optional[TextIO] = None                          #: logging null stream
        self._shut_down: bool = False                                       #: True if app got shut down
        self.multi_threading: bool = multi_threading                        #: True if app uses multiple threads
        self.suppress_stdout: bool = True     # block initially until app-config/-logging is fully initialized

        self.startup_beg: datetime.datetime = datetime.datetime.now()       #: app startup datetime
        self.config_options: Dict[str, Setting] = dict()                    #: all configuration options
        self.config_choices: Dict[str, Sequence] = dict()                   #: all valid configuration option choices

        self.config_eval_vars: dict = config_eval_vars or dict()            #: additional application specific data

        if not sys.argv:    # prevent unit tests to fail on sys.argv == list()
            sys.argv.append(os.path.join(os.getcwd(), 'TesT.exe'))
        app_path_fnam_ext = sys.argv[0]
        app_fnam = os.path.basename(app_path_fnam_ext)
        self._app_path: str = os.path.dirname(app_path_fnam_ext)            #: path to folder of your main app code file
        self._app_name: str = os.path.splitext(app_fnam)[0]                 #: main app code file's base name (w/o ext)
        self._app_version: str = app_version                                #: version of your app

        # prepare config files, including determine default config file (last existing INI/CFG file) for
        # .. to write to and if there is no INI file at all then create on demand a <APP_NAME>.INI file in the cwd
        self._config_parser: Optional[ConfigParser] = None                  #: ConfigParser instance
        self._config_files: list = list()                                   #: list of all found INI/CFG files
        self._main_cfg_fnam: Optional[str] = None                           #: main config file name
        self._main_cfg_mod_time: Optional[int] = None                       #: main config file modification datetime
        self.config_init(app_path_fnam_ext, additional_cfg_files)
        self._option_value_stripper: Optional[Callable] = option_value_stripper     #: callable to strip option values
        self.config_load()

        # prepare logging: most values will be initialized in self._parse_args() indirectly via logFile setting
        if logging_config is None:
            logging_config = dict()
        self._log_file_obj: Optional[TextIO] = None                         #: log file stream instance
        self._log_file_max_size: int = logging_config.get('file_size_max', 20)  #: maximum log file size (rotating logs)
        self._log_file_name: str = ""                                       #: log file name
        self._log_file_index: int = 0                                       #: log file index (for rotating logs)
        # check if app is using python logging module
        lcd = logging_config.get('py_logging_config_dict', self.get_config('py_logging_config_dict'))
        if lcd:
            logger_late_init()
            # logging.basicConfig(level=logging.DEBUG, style='{')
            logging.config.dictConfig(lcd)     # configure logging module
        else:
            lcd = dict()
        self.logging_conf_dict = lcd                                        #: python logging config dict
        if not main_instance.logging_conf_dict:
            main_instance.logging_conf_dict = lcd

        self.suppress_stdout: bool = suppress_stdout                        #: flag to suppress prints to stdout
        if not self.suppress_stdout:    # no log file ready after defining all options (with add_option())
            self.uprint(self._app_name, " V", app_version, "  Startup", self.startup_beg, app_desc, logger=_logger)
            self.uprint("####  Initialization......  ####", logger=_logger)

        # prepare argument parser
        formatter_class = formatter_class or HelpFormatter
        self._arg_parser = ArgumentParser(
            description=app_desc, epilog=epilog, formatter_class=formatter_class)   #: ArgumentParser instance
        self.add_argument = self._arg_parser.add_argument       #: redirect this method to our ArgumentParser instance

        # create pre-defined config options
        self.add_option('debugLevel', "Verbosity of debug messages send to console and log files", debug_level_def, 'D',
                        choices=DEBUG_LEVELS.keys())
        self.add_option('logFile', "Log file path", logging_config.get('file_name_def', ''), 'L')

    def __del__(self):
        """ deallocate this instance and call :func:`ConsoleApp.shutdown` if it is the main app instance.
        """
        if main_app_instance() is self and not self._shut_down:
            self.shutdown()

    def add_argument(self, *args, **kwargs):
        """ define new command line argument.

        Original/underlying args/kwargs of :class:`argparse.ArgumentParser` are used - please see the
        description/definition of :meth:`~argparse.ArgumentParser.add_argument`.
        """
        # THIS METHOD DEF IS USED ONLY FOR DOCUMENTATION BUILD ###
        # .. this method get never called because gets overwritten with self._arg_parser.add_argument in __init__().
        self._arg_parser.add_argument(*args, **kwargs)

    def add_option(self, name, desc, value, short_opt=None, choices=None, multiple=False):
        """ defining and adding a new configuration option for this app.

        The value of a configuration option can be of any type and is internally represented by an instance of the
        :class:`~ae.setting.Setting` class. Supported value types and literals are documented
        :attr:`here <ae.setting.Setting.value>`.

        :param name:        string specifying the option id and short description of this new option.
                            The name value will also be available as long command line argument option (case-sens.).
        :param desc:        description and command line help string of this new option.
        :param value:       default value and the type of the option. This value will be used only if the config values
                            are not specified in any config file. The command line argument option value
                            will always overwrite this value (and any value in any config file).
        :param short_opt:   short option character. If not passed or passed as '' then the first character of the name
                            will be used. Please note that the short options 'D' and 'L' are used internally
                            (recommending using only lower-case options for your application).
        :param choices:     list of valid option values (optional, default=allow all values).
        :param multiple:    True if option can be added multiple times to command line (optional, default=False).
        """
        self._parsed_args = None        # request (re-)parsing of command line args
        if short_opt == '':
            short_opt = name[0]

        args = list()
        if short_opt and len(short_opt) == 1:
            args.append('-' + short_opt)
        args.append('--' + name)

        # determine config value for to use as default for command line arg
        setting = Setting(name=name, value=value)
        cfg_val = self._get_config_val(name, default_value=value)
        setting.value = cfg_val
        kwargs = dict(help=desc, default=cfg_val, type=setting.convert_value, choices=choices, metavar=name)
        if multiple:
            kwargs['type'] = setting.append_value
            if choices:
                kwargs['choices'] = None    # for multiple options this instance need to check the choices
                self.config_choices[name] = choices

        self._arg_parser.add_argument(*args, **kwargs)

        self.config_options[name] = setting

    def show_help(self):
        """ show help message on console output/stream.

        Original/underlying args/kwargs are used - please see description/definition of
        :meth:`~argparse.ArgumentParser.print_help` of :class:`~argparse.ArgumentParser`.
        """
        self._arg_parser.print_help(file=app_std_out)

    def _parse_args(self):
        """ parse all command line args.

        This method get normally only called once and after all the options have been added with :meth:`add_option`.
        :meth:`add_option` will then set the determined config file value as the default value and then the
        following call of this method will overwrite it with command line argument value, if given.
        """
        self._parsed_args = self._arg_parser.parse_args()

        for name in self.config_options.keys():
            self.config_options[name].value = getattr(self._parsed_args, name)
            if name in self.config_choices:
                for given_value in self.config_options[name].value:
                    if self._option_value_stripper:
                        given_value = self._option_value_stripper(given_value)
                    allowed_values = self.config_choices[name]
                    if given_value not in allowed_values:
                        raise ArgumentError(None, "Wrong {} option value {}; allowed are {}"
                                            .format(name, given_value, allowed_values))

        if main_app_instance() is self and not self.logging_conf_dict:
            self.activate_internal_logging(self.config_options['logFile'].value)

        # finished argument parsing - now print chosen option values to the console
        _debug_level = self.config_options['debugLevel'].value
        if _debug_level >= DEBUG_LEVEL_ENABLED:
            self.uprint("  ##  Debug Level(" + ", ".join([str(k) + "=" + v for k, v in DEBUG_LEVELS.items()]) + "):",
                        _debug_level, logger=_logger)
            # print sys env - s.a. pyinstaller docs (http://pythonhosted.org/PyInstaller/runtime-information.html)
            if self.sys_env_id or main_app_instance() is not self:
                self.uprint(" ###  Initialized ConsoleApp instance for system env id", self.sys_env_id, logger=_logger)
            self.uprint("  ##  System Environment:", logger=_logger)
            self.uprint(sys_env_text(extra_sys_env_dict={'main cfg': self._main_cfg_fnam}), logger=_logger)

        self.startup_end = datetime.datetime.now()
        self.uprint(self._app_name, " V", self._app_version, "  Args  parsed", self.startup_end, logger=_logger)
        if main_app_instance() is not self and not self.sys_env_id:
            self.uprint("  **  Additional instance of ConsoleApp requested with empty system environment ID",
                        logger=_logger)
        self.uprint("####  Startup finished....  ####", logger=_logger)

    def get_argument(self, name: str) -> Any:
        """ determine the command line parameter value.

        :param name:    Argument id of the parameter.
        :return:        Value of the parameter.
        """
        if not self._parsed_args:
            self._parse_args()
        return getattr(self._parsed_args, name)

    def get_option(self, name: str, default_value: Optional[Any] = None) -> Any:
        """ get the value of a configuration option specified by it's name (option id).

        The returned value has the same type as the value specified in the :meth:`add_option` call and
        gets taken either from the command line, the default section (:data:`MAIN_SECTION_DEF`) of any found
        config setting file (with file extension INI or CFG) or from the default values specified in your python code.

        Underneath you find the order of the value search - the first specified/found value will be returned:

        #. command line arguments option value
        #. INI/CFG file(s) added in your app code via one of the methods :meth:`~.config_file_add` or
          :meth:`config_init`. which will be searched for the configuration option value in reversed order - so
          the last added config file will be the first one where the configuration option will be searched.
        #. INI/CFG file(s) added via :paramref:`~ConsoleApp.additional_cfg_files` argument of
           :meth:`ConsoleApp.__init__` searched in the reversed order of the list.
        #. <app_name>.INI file in the <cwd>
        #. <app_name>.CFG file in the <cwd>
        #. <app_name>.INI file in the <app_dir>
        #. <app_name>.CFG file in the <app_dir>
        #. .sys_env.cfg in the <cwd>
        #. .sys_env<sys_env_id>.cfg in the <cwd>
        #. .console_app_env.cfg in the <cwd>
        #. .sys_env.cfg in the parent folder of the <cwd>
        #. .sys_env<sys_env_id>.cfg in the parent folder of the <cwd>
        #. .console_app_env.cfg in the parent folder of the <cwd>
        #. .sys_env.cfg in the <app_dir>
        #. .sys_env<sys_env_id>.cfg in the <app_dir>
        #. .console_app_env.cfg in the <app_dir>
        #. .sys_env.cfg in the parent folder of the parent folder of the <cwd>
        #. .sys_env<sys_env_id>.cfg in the parent folder of the parent folder of the <cwd>
        #. .console_app_env.cfg in the parent folder of the parent folder of the <cwd>
        #. value argument passed into the add_option() method call (defining the option)
        #. default_value argument passed into this method (only if :class:`~ConsoleApp.add_option` didn't get called)

        Placeholders in the above search order lists are:

        * <cwd> is the current working directory of your application (determined with :func:`os.getcwd`)
        * <app_name> is the base name without extension of your main python code file.
        * <app_dir> is the application directory (where your <app_name>.py or the exe file of your app is situated)
        * <sys_env_id> is specified as argument of :meth:`ConsoleApp.__init__`

        :param name:            id of the option/setting.
        :param default_value:   default value of the option (if not defined with :class:`~ConsoleApp.add_option`).

        :return:                first found value of the option identified by :paramref:`~ConsoleApp.get_option.name`.
        """
        if not self._parsed_args:
            self._parse_args()
        return self.config_options[name].value if name in self.config_options else default_value

    def set_option(self, name: str, val: Any, cfg_fnam: Optional[str] = None, save_to_config: bool = True) -> str:
        """ set or change the value of a configuration option.

        :param name:            id of the configuration option to set.
        :param val:             value to assign to the option, identified by :paramref:`~.set_option.name`.
        :param cfg_fnam:        config file name to save new option value. If not specified then the
                                default file name of :meth:`~ConsoleApp.set_config` will be used.
        :param save_to_config:  pass False to prevent to save the new option value also to a config file.
                                The value of the configuration option will be changed in any case.
        :return:                ''/empty string on success else error message text.
        """
        self.config_options[name].value = val
        return self.set_config(name, val, cfg_fnam) if save_to_config else ''

    def config_file_add(self, fnam: str) -> bool:
        """ add config file name to internal list of processed config files.

        :param fnam:    new config file name to add.
        :return:        True, if passed config file exists and was not in the list before, else False.
        """
        if fnam not in self._config_files and os.path.isfile(fnam):
            self._config_files.append(fnam)
            return True
        return False

    def config_init(self, app_path_fnam_ext: str, additional_cfg_files: Iterable = ()) -> str:
        """ extend list of found config files (in :attr:`~ConsoleApp.config_files`).

        :param app_path_fnam_ext:       file path of executable (normally taken from sys.argv[0].
        :param additional_cfg_files:    additional/user-defined config files.
        :return:                        ""/empty string on success else error message text.
        """
        cwd_path = os.getcwd()
        app_path = self._app_path

        # prepare config env, first compile cfg/ini files - the last one overwrites previously loaded values
        cwd_path_fnam = os.path.join(cwd_path, self._app_name)
        self._main_cfg_fnam = cwd_path_fnam + INI_EXT  # default will be overwritten by config_load()
        sys_env_id = self.sys_env_id or 'TEST'
        for cfg_path in (os.path.join(cwd_path, '..', '..'), app_path, os.path.join(cwd_path, '..'), cwd_path, ):
            for cfg_file in ('.console_app_env.cfg', '.sys_env' + sys_env_id + '.cfg', '.sys_env.cfg', ):
                self.config_file_add(os.path.join(cfg_path, cfg_file))

        app_path_fnam = os.path.splitext(app_path_fnam_ext)[0]
        for cfg_file in (app_path_fnam + '.cfg', app_path_fnam + INI_EXT,
                         cwd_path_fnam + '.cfg', cwd_path_fnam + INI_EXT):
            self.config_file_add(cfg_file)

        err_msg = ""
        for cfg_fnam in additional_cfg_files:
            add_cfg_path_fnam = os.path.join(cwd_path, cfg_fnam)
            if not self.config_file_add(add_cfg_path_fnam):
                add_cfg_path_fnam = os.path.join(app_path, cfg_fnam)
                if not self.config_file_add(add_cfg_path_fnam):
                    err_msg = "Additional config file {} not found!".format(cfg_fnam)
        return err_msg

    def _get_config_val(self, name: str, section: Optional[str] = None, default_value: Optional[Any] = None,
                        cfg_parser: Optional[ConfigParser] = None) -> Any:
        """ determine thread-safe the value of a config setting from the config file.

        :param name:            name/option_id of the config setting.
        :param section:         name of the config section (def= :paramRef:`MAIN_SECTION_DEF` also if passed as None/'')
        :param default_value:   default value to return if config value is not specified in any config file.
        :param cfg_parser:      ConfigParser instance to use (def=self._config_parser).
        :return:                value of the config setting.
        """
        global config_lock
        with config_lock:
            cfg_parser = cfg_parser or self._config_parser
            val = cfg_parser.get(section or MAIN_SECTION_DEF, name, fallback=default_value)
        return val

    def config_load(self):
        """ load and parse all config files.
        """
        global config_lock
        for cfg_fnam in reversed(self._config_files):
            if cfg_fnam.endswith(INI_EXT) and os.path.isfile(cfg_fnam):
                self._main_cfg_fnam = cfg_fnam
                self._main_cfg_mod_time = os.path.getmtime(self._main_cfg_fnam)
                break

        with config_lock:
            self._config_parser = ConfigParser()
            self._config_parser.optionxform = str      # or use 'lambda option: option' to have case sensitive var names
            self._config_parser.read(self._config_files, encoding='utf-8')

    def config_main_file_modified(self) -> bool:
        """ determine if main config file got modified.

        :return:    True if the content of the main config file got modified/changed.
        """
        return self._main_cfg_mod_time and os.path.getmtime(self._main_cfg_fnam) > self._main_cfg_mod_time

    def get_config(self, name: str, section: Optional[str] = None, default_value: Optional[Any] = None,
                   cfg_parser: Optional[ConfigParser] = None, value_type: Optional[Type] = None) -> Any:
        """ get the value of a config setting.

        :param name:            name of the config setting or id of configuration option.
        :param section:         name of the config section (def= :data:`MAIN_SECTION_DEF`).
        :param default_value:   default value to return if config value is not specified in any config file.
        :param cfg_parser:      ConfigParser instance to use (def= :attr:`~ConsoleApp._config_parser`).
        :param value_type:      type of the config value.
        :return:                value of the config setting or of the configuration option (the latter only
                                if the passed string in :paramref:`~.get_config.name` is the id of a defined
                                configuration option and the :paramref:`.section` is either empty or
                                equal to the value of :data:`MAIN_SECTION_DEF`.
        """
        if name in self.config_options and section in (MAIN_SECTION_DEF, '', None):
            val = self.config_options[name].value
        else:
            s = Setting(name=name, value=default_value, value_type=value_type)  # used only for conversion/eval
            s.value = self._get_config_val(name, section=section, default_value=s.value, cfg_parser=cfg_parser)
            val = s.value
        return val

    def set_config(self, name: str, val: Any, cfg_fnam: Optional[str] = None, section: Optional[str] = None) -> str:
        """ set or change the value of a config setting and if exists the related configuration option.

        If the passed string in :paramref:`~.set_config.name` is the id of a defined
        configuration option and :paramref:`~.set_config.section` is either empty or
        equal to the value of :data:`MAIN_SECTION_DEF` then the value of this
        configuration option will be changed too.

        :param name:            name/option_id of the config value to set.
        :param val:             value to assign to the config value, specified by the
                                :paramref:`.set_config.name` argument.
        :param cfg_fnam:        file name (def= :attr:`~ConsoleApp._main_cfg_fnam`) to save the new option value to.
        :param section:         name of the config section (def= :data:`MAIN_SECTION_DEF`).
        :return:                ''/empty string on success else error message text.
        """
        global config_lock
        msg = "****  ConsoleApp.set_config({}, {}) ".format(name, val)
        if not cfg_fnam:
            cfg_fnam = self._main_cfg_fnam
        if not section:
            section = MAIN_SECTION_DEF

        if name in self.config_options and section in (MAIN_SECTION_DEF, '', None):
            self.config_options[name].value = val

        if not os.path.isfile(cfg_fnam):
            return msg + "INI/CFG file {} not found. Please set the ini/cfg variable {}/{} manually to the value " \
                .format(cfg_fnam, section, name, val)

        err_msg = ''
        with config_lock:
            try:
                cfg_parser = ConfigParser()     # not using self._config_parser for to put INI vars from other files
                cfg_parser.optionxform = str    # or use 'lambda option: option' to have case sensitive var names
                cfg_parser.read(cfg_fnam)
                if isinstance(val, (dict, list, tuple)):
                    str_val = "'''" + repr(val).replace('%', '%%') + "'''"
                elif type(val) is datetime.datetime:
                    str_val = val.strftime(DATE_TIME_ISO)
                elif type(val) is datetime.date:
                    str_val = val.strftime(DATE_ISO)
                else:
                    str_val = str(val)       # using str() here because repr() will put high-commas around string values
                cfg_parser.set(section, name, str_val)
                with open(cfg_fnam, 'w') as configfile:
                    cfg_parser.write(configfile)
            except Exception as ex:
                err_msg = msg + "exception: {}".format(ex)

        return err_msg

    # noinspection PyIncorrectDocstring
    def dprint(self, *objects, sep: str = ' ', end: str = '\n', file: Optional[TextIO] = None,
               minimum_debug_level: int = DEBUG_LEVEL_VERBOSE, **kwargs):
        """ special debug version of builtin print() function.

        This method will print out only if the current debug level is higher than minimum_debug_level. All other
        args of this method are documented :func:`in the uprint() function of this module <.uprint>`.

        :param minimum_debug_level:     minimum debug level for to print the passed objects.
        """
        if self.get_option('debugLevel') >= minimum_debug_level:
            self.uprint(*objects, sep=sep, end=end, file=file, debug_level=minimum_debug_level, **kwargs)

    def uprint(self, *objects, sep: str = ' ', end: str = '\n', file: Optional[TextIO] = None,
               debug_level: int = DEBUG_LEVEL_DISABLED, **kwargs):
        """ special version of builtin print() function.

        This method has the same args as :func:`in the uprint() function of this module <ae.console_app.uprint>`.
        """
        if self.sys_env_id:
            objects = ('{' + self.sys_env_id + '}', ) + objects
        uprint(*objects, sep=sep, end=end, file=file, debug_level=debug_level, **kwargs)

    def app_name(self) -> str:
        """ determine the name of the application.

        :return:    application name.
        """
        return self._app_name

    def _append_eof_and_flush_file(self, stream_file: TextIO, stream_name: str):
        """ add special end-of-file marker and flush the internal buffers to the file stream.

        :param stream_file:     file stream.
        :param stream_name:     name of the file stream.
        """
        try:
            try:
                # ALWAYS add \nEoF\n to the end
                # .. we cannot use uprint here because of recursions on log file rotation, so use built-in print()
                # .. self.uprint()
                # .. self.uprint('EoF')
                print(file=stream_file)
                print('EoF', file=stream_file)
            except Exception as ex:
                self.dprint("Ignorable {} end-of-file marker exception={}".format(stream_name, ex), logger=_logger)

            stream_file.flush()

        except Exception as ex:
            self.dprint("Ignorable {} flush exception={}".format(stream_name, ex), logger=_logger)

    def activate_internal_logging(self, log_file: str):
        """ activate internal logging (not using the python logging module).

        :param log_file:    file name of the log file to use.
        """
        if log_file:
            try:  # enable logging
                self._close_log_file()
                self._open_log_file(log_file)
                self.uprint(" ###  Activated log file", log_file, logger=_logger)
                self._log_file_name = log_file
            except Exception as ex:
                self.uprint(" ***  ConsoleApp._parse_args(): exception while enabling logging:", ex, logger=_logger)

    def _open_log_file(self, log_file: str):
        """ open the internal log file.

        :param log_file:    file name of the log file.
        """
        global app_std_out, app_std_err
        self._log_file_obj = open(log_file, "w")
        if app_std_out == ori_std_out:      # first call/open-of-log-file?
            if self.suppress_stdout:
                std_out = self._nul_std_out = open(os.devnull, 'w')
            else:
                std_out = ori_std_out
            app_std_out = sys.stdout = _DuplicateSysOut(self._log_file_obj, sys_out_obj=std_out)
            app_std_err = sys.stderr = _DuplicateSysOut(self._log_file_obj, sys_out_obj=ori_std_err)
        else:
            app_std_out.log_file_obj = self._log_file_obj
            app_std_err.log_file_obj = self._log_file_obj

    def _rename_log_file(self):
        """ rename the log file (on rotating of the internal log file).
        """
        self._log_file_index = 0 if self._log_file_index >= MAX_NUM_LOG_FILES else self._log_file_index + 1
        index_width = len(str(MAX_NUM_LOG_FILES))
        file_path, file_ext = os.path.splitext(self._log_file_name)
        dfn = file_path + "-{:0>{index_width}}".format(self._log_file_index, index_width=index_width) + file_ext
        if os.path.exists(dfn):
            os.remove(dfn)
        if os.path.exists(self._log_file_name):     # prevent errors after unit test cleanup
            os.rename(self._log_file_name, dfn)

    def _close_log_file(self, full_reset: bool = False):
        """ close the internal log file.

        :param full_reset:  pass True to reset the standard output streams (stdout/stderr) to the defaults.
        """
        global app_std_out, app_std_err

        if self._log_file_obj:
            self._append_eof_and_flush_file(self._log_file_obj, "log file")
            app_std_err.log_file_obj = None     # prevent exception/calls of _DuplicateSysOut.log_file_obj.write()
            app_std_out.log_file_obj = None
            sys.stderr = ori_std_err            # set back for to prevent stack overflow/recursion with kivy logger
            sys.stdout = ori_std_out            # .. "Fatal Python error: Cannot recover from stack overflow"
            self._log_file_obj.close()
            self._log_file_obj = None
        elif self.logging_conf_dict:
            logging.shutdown()

        if full_reset:
            app_std_err = ori_std_err   # set back for allow full reset of log for unit tests
            app_std_out = ori_std_out

    def log_file_check_rotation(self):
        """ check if the internal log file is big enough and if yes then do a file rotation.
        """
        if self._log_file_obj is not None:
            if self.multi_threading:
                global log_file_rotation_lock
                log_file_rotation_lock.acquire()
            self._log_file_obj.seek(0, 2)  # due to non-posix-compliant Windows feature
            if self._log_file_obj.tell() >= self._log_file_max_size * 1024 * 1024:
                self._close_log_file()
                self._rename_log_file()
                self._open_log_file(self._log_file_name)
            if self.multi_threading:
                log_file_rotation_lock.release()

    def shutdown(self, exit_code: Optional[int] = 0, timeout: Optional[float] = None):
        """ shutdown console app environment

        :param exit_code:   application OS exit code (def=0). Pass None for to not call sys.exit(exit_code).
        :param timeout:     timeout float value in seconds for thread joining (def=None - block/no-timeout).
                            Pass None for to block shutdown until all other threads have joined/finished.
        """
        self.uprint("####  Shutdown............  ", exit_code, timeout, logger=_logger)
        if self.multi_threading:
            with config_lock:
                main_thread = threading.current_thread()
                for t in threading.enumerate():
                    if t is not main_thread:
                        self.uprint("  **  joining thread ident <{: >6}> name={}".format(t.ident, t.getName()),
                                    logger=_logger)
                        t.join(timeout)

        self._close_log_file()
        if self._log_file_index:
            self._rename_log_file()

        if self._nul_std_out and not self._nul_std_out.closed:
            self._append_eof_and_flush_file(self._nul_std_out, "NUL stdout")
            self._nul_std_out.close()
            self._nul_std_out = None

        if main_app_instance() is self:
            self._shut_down = True
            if exit_code is not None:
                sys.exit(exit_code)
