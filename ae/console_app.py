import sys
import os
import datetime

from builtins import chr  # works like unichr() also in Python 2

import inspect
import logging
import logging.config
import pprint
import re
import threading
import unicodedata
import weakref

from configparser import ConfigParser
from argparse import ArgumentParser, ArgumentError, HelpFormatter

from ae import (DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, DEBUG_LEVEL_TIMESTAMPED,
                debug_levels, logging_levels, DATE_TIME_ISO, DATE_ISO)
from ae.setting import Setting

INI_EXT = '.ini'

# default name of main config section
MAIN_SECTION_DEF = 'Settings'

# core encoding that will always work independent from destination (console, file system, XMLParser, ...)
DEF_ENCODING = 'ascii'

# illegal characters in XML
# .. taken from https://stackoverflow.com/questions/1707890/fast-way-to-filter-illegal-xml-unicode-chars-in-python
ILLEGAL_XML_CHARS = [(0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F),
                     (0x7F, 0x84), (0x86, 0x9F),
                     (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF)]
if sys.maxunicode >= 0x10000:  # not narrow build of Python
    ILLEGAL_XML_CHARS.extend([(0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF),
                              (0x3FFFE, 0x3FFFF), (0x4FFFE, 0x4FFFF),
                              (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                              (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF),
                              (0x9FFFE, 0x9FFFF), (0xAFFFE, 0xAFFFF),
                              (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                              (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF),
                              (0xFFFFE, 0xFFFFF), (0x10FFFE, 0x10FFFF)])
ILLEGAL_XML_SUB = re.compile(u'[%s]' % u''.join(["%s-%s" % (chr(low), chr(high)) for (low, high) in ILLEGAL_XML_CHARS]))

MAX_NUM_LOG_FILES = 99

# initialized in ConsoleApp.__init__() for to allow log file split/rotation and debugLevel access at this module level
ae_instances = weakref.WeakValueDictionary()   # type: weakref.WeakValueDictionary[str, ConsoleApp]

# global Locks for to prevent errors in log file rotation, config reloads and config reads
log_file_rotation_lock = threading.Lock()
config_lock = threading.Lock()
config_read_lock = threading.Lock()


def _get_debug_level():
    """ determining the debug level of the console app env instance of the currently running app.

    :return: current debug level.
    """
    main_instance = ae_instances.get('')
    if main_instance and 'debugLevel' in main_instance.config_options:
        return main_instance.config_options['debugLevel'].value
    return DEBUG_LEVEL_DISABLED


def round_traditional(val, digits=0):
    """ needed because python round() is not working always, like e.g. round(0.075, 2) == 0.07 instead of 0.08
        taken from https://stackoverflow.com/questions/31818050/python-2-7-round-number-to-nearest-integer
    """
    return round(val + 10**(-len(str(val)) - 1), digits)


def fix_encoding(text, encoding=DEF_ENCODING, try_counter=2, pex=None, context='ae.console_app.fix_encoding()'):
    """ used for to encode invalid char encodings in text that cannot be fixed with encoding="cp1252/utf-8/.. """
    ori_text = text
    if try_counter == 0:
        try_method = "replacing &#128 with €, &#1; with ¿1¿ and &#7; with ¿7¿ for Sihot XML"
        text = text.replace('&#1;', '¿1¿').replace('&#7;', '¿7¿').replace('&#128;', '€')
    elif try_counter == 1:
        try_method = "replacing &#NNN; with chr(NNN) for Sihot XML"
        text = re.compile("&#([0-9]+);").sub(lambda m: chr(int(m.group(0)[2:-1])), text)
    elif try_counter == 2:
        if not encoding:
            encoding = DEF_ENCODING
        try_method = "recode to backslash-replaced " + encoding + " encoding"
        text = text.encode(encoding, errors='backslashreplace').decode(encoding)
    elif try_counter == 3:
        try_method = "replacing invalid unicode code points with ¿_¿"
        text = ILLEGAL_XML_SUB.sub('¿_¿', text)
    elif try_counter == 4:
        try_method = "replacing &#NNN; and &#xNNN; with ¿?¿"
        text = re.compile("&#([0-9]+);|&#x([0-9a-fA-F]+);").sub('¿?¿', text)
    else:
        try_method = ""
        text = None

    if try_method and _get_debug_level() >= DEBUG_LEVEL_VERBOSE:
        # push/print ori_text and error message to console/log
        uprint(pprint.pformat(context + ": " + (str(pex) + '- ' if pex else '') + try_method +
                              ", " + DEF_ENCODING + " text:\n'" +
                              ori_text.encode(DEF_ENCODING, errors='backslashreplace').decode(DEF_ENCODING) + "'\n",
                              indent=12, width=120))

    return text


def full_stack_trace(ex):
    ret = "Exception {!r}. Traceback:\n".format(ex)

    tb = sys.exc_info()[2]
    for item in reversed(inspect.getouterframes(tb.tb_frame)[1:]):
        ret += 'File "{1}", line {2}, in {3}\n'.format(*item)
        if item[4]:
            for line in item[4]:
                ret += ' '*4 + line.lstrip()
    for item in inspect.getinnerframes(tb):
        ret += 'file "{1}", line {2}, in {3}\n'.format(*item)
        if item[4]:
            for line in item[4]:
                ret += ' '*4 + line.lstrip()
    return ret


def sys_env_dict():
    sed = dict()
    sed['python_ver'] = sys.version
    sed['argv'] = sys.argv
    sed['executable'] = sys.executable
    sed['cwd'] = os.getcwd()
    sed['__file__'] = __file__
    sed['frozen'] = getattr(sys, 'frozen', False)
    if getattr(sys, 'frozen', False):
        sed['bundle_dir'] = getattr(sys, '_MEIPASS', '*#ERR#*')
    return sed


def sys_env_text(ind_ch=" ", ind_len=18, key_ch="=", key_len=12, extra_sys_env_dict=None):
    sed = sys_env_dict()
    if extra_sys_env_dict:
        sed.update(extra_sys_env_dict)
    text = "\n".join(["{ind:{ind_ch}>{ind_len}}{key:{key_ch}<{key_len}}{val}"
                     .format(ind="", ind_ch=ind_ch, ind_len=ind_len, key_ch=key_ch, key_len=key_len, key=k, val=v)
                      for k, v in sed.items()])
    return text


def to_ascii(unicode_str):
    """
    converts unicode string into ascii representation (for fuzzy string comparision); copied from MiniQuark's answer in:
    https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string

    :param unicode_str:     string to convert
    :return:                converted string (replaced accents, diacritics, ... into normal ascii characters)
    """
    nfkd_form = unicodedata.normalize('NFKD', unicode_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


# save original stdout/stderr
ori_std_out = sys.stdout
ori_std_err = sys.stderr
app_std_out = ori_std_out
app_std_err = ori_std_err


class _DuplicateSysOut:
    def __init__(self, log_file, sys_out=ori_std_out):
        self.log_file = log_file
        self.sys_out = sys_out

    def write(self, message):
        if self.log_file and not self.log_file.closed:
            try:
                self.log_file.write(message)
            except UnicodeEncodeError:
                # log file has different encoding than console, so simply replace with backslash
                self.log_file.write(fix_encoding(message, encoding=self.log_file.encoding))
        if not self.sys_out.closed:
            self.sys_out.write(message)

    def __getattr__(self, attr):
        return getattr(self.sys_out, attr)


_logger = logging.getLogger(__name__)


def calling_module(called_module=__name__, depth=1):
    module = None
    try:
        # find the first stack frame that is *not* in this module
        while True:
            # noinspection PyProtectedMember
            module = sys._getframe(depth).f_globals.get('__name__', '__main__')
            if module != called_module:
                break
            depth += 1
    except (TypeError, AttributeError, ValueError):
        pass
    return module


def uprint(*print_objects, sep=" ", end="\n", file=None, flush=False, encode_errors_def='backslashreplace',
           debug_level=None, logger=None, cae_instance=None, **kwargs):
    processing = end == "\r"
    if not file:
        # app_std_out cannot be specified as file argument default because get initialized after import of this module
        # .. within ConsoleApp._open_log_file(). Use ori_std_out for animation prints (see tcp.py/TcpServer.run()).
        file = ori_std_out if processing else app_std_out
    enc = file.encoding

    if cae_instance is None:
        cae_instance = ae_instances.get('')
    if cae_instance is not None:
        if getattr(cae_instance, 'multi_threading', False):            # add thread ident
            print_objects = (" <{: >6}>".format(threading.get_ident()),) + print_objects
        if getattr(cae_instance, '_log_file_obj', False):
            # creating new log file and backup of current one if the current one has more than 20 MB in size
            cae_instance.log_file_check_rotation()

    # even with enc == 'UTF-8' and because of _DuplicateSysOut is also writing to file it raises the exception:
    # ..UnicodeEncodeError: 'charmap' codec can't encode character '\x9f' in position 191: character maps to <undefined>
    # if enc == 'UTF-8':
    #     print(*print_objects, sep=sep, end=end, file=file, flush=flush)
    # else:
    #     print(*map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), print_objects),
    #           sep=sep, end=end, file=file, flush=flush)
    if _get_debug_level() >= DEBUG_LEVEL_TIMESTAMPED:
        print_objects = (datetime.datetime.now().strftime(DATE_TIME_ISO),) + print_objects

    if kwargs:
        print_objects += ("\n   *  EXTRA KWARGS={}".format(kwargs), )

    use_logger = not processing and debug_level in logging_levels \
        and getattr(cae_instance, 'logging_conf_dict', False)
    if use_logger and logger is None:
        module = calling_module()
        logger = logging.getLogger(module) if module else _logger

    try_counter = 2     # skip try_counter 0 and 1 because it is very specific to the Sihot XML interface and XMLParser
    while True:
        try:
            print_strings = map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), print_objects)
            if use_logger or getattr(cae_instance, 'multi_threading', False):
                # prevent fluttered log file content by concatenating print_objects and adding end value
                # .. see https://stackoverflow.com/questions/3029816/how-do-i-get-a-thread-safe-print-in-python-2-6
                # .. and https://stackoverflow.com/questions/50551637/end-key-in-print-not-thread-safe
                print_one_str = sep.join(print_strings)
                sep = ""
                if end and not use_logger:
                    print_one_str += end
                    end = ""
                print_strings = (print_one_str, )

            if use_logger:
                logger.log(level=logging_levels[debug_level], msg=print_strings[0])
            else:
                print(*print_strings, sep=sep, end=end, file=file, flush=flush)

            break
        except UnicodeEncodeError:
            fixed_objects = list()
            for obj in print_objects:
                if isinstance(obj, str) or isinstance(obj, bytes):
                    obj = fix_encoding(obj, enc, try_counter)
                    if not obj:
                        raise
                fixed_objects.append(obj)
            print_objects = fixed_objects
        try_counter += 1


class ConsoleApp:
    def __init__(self, app_version, app_desc, debug_level_def=DEBUG_LEVEL_DISABLED,
                 config_eval_vars=None, additional_cfg_files=(), option_value_stripper=None,
                 multi_threading=False, suppress_stdout=False,
                 formatter_class=HelpFormatter, epilog="",
                 sys_env_id='', logging_config=None):
        """ encapsulating ConfigParser and ArgumentParser for python console applications
            :param app_version:             application version.
            :param app_desc:                application description.
            :param debug_level_def:         default debug level (DEBUG_LEVEL_DISABLED).
            :param config_eval_vars:        dict of additional application specific data values that are used in eval
                                            expressions (e.g. AcuSihotMonitor.ini).
            :param additional_cfg_files:    list of additional CFG/INI file names (opt. incl. abs/rel. path).
            :param option_value_stripper:   function for to strip option value for to check if is an allowed value.
            :param multi_threading:         pass True if instance is used in multi-threading app.
            :param suppress_stdout:         pass True (for wsgi apps) for to prevent any python print outputs to stdout.
            :param formatter_class:         alternative formatter class passed onto ArgumentParser instantiation.
            :param epilog:                  optional epilog text for command line arguments/options help text (passed
                                            onto ArgumentParser instantiation).
            :param sys_env_id:              system environment id used as file name suffix for to load all
                                            the system config variables in sys_env<suffix>.cfg (def='', pass e.g. 'LIVE'
                                            for to init second ConsoleApp instance with values from sys_envLIVE.cfg).
            :param logging_config:          dict with logging configuration default values - supported keys. If the key
                                            py_logging_config_dict is a non-empty dict then all other keys are ignored:
                                            py_logging_config_dict  config dict for python logging configuration.
                                            file_name_def           default log file name for internal logging (def='').
                                            file_size_max           max. size in MBytes of internal log file (def=20).
        """
        """
            :var  ae_instances          module dict var, referencing all instances of this class. The main/first-created
                                        instance has an empty string as the dict key.
            :ivar config_options        pre-/user-defined options (dict of Setting instances).
            :ivar _parsed_args          ArgumentParser.parse_args() return - used for to retrieve command line args and
                                        as flag to ensure that the command line arguments get re-parsed if add_option()
                                        get called after a first call to methods which are initiating the re-fetch of
                                        the args and INI/cfg vars (like e.g. get_option() or dprint()).
            :ivar _log_file_obj         file handle of currently opened log file (opened in self._parse_args()).
            :ivar _log_file_max_size    maximum size in MBytes of a log file.
            :ivar _log_file_name        path and file name of the log file.
            :ivar _log_file_index       index of the current rotation log file backup.
        """
        global ae_instances
        if ae_instances.get('') is None:
            ae_instances[''] = self
        self.sys_env_id = sys_env_id
        if sys_env_id not in ae_instances:
            ae_instances[sys_env_id] = self

        self._parsed_args = None
        self._nul_std_out = None
        self._shut_down = False
        self.multi_threading = multi_threading
        self.suppress_stdout = True     # block initially until app-config/-logging is fully initialized

        self.startup_beg = datetime.datetime.now()
        self.config_options = dict()
        self.config_choices = dict()

        self.config_eval_vars = config_eval_vars or dict()

        app_path_fnam_ext = sys.argv[0]
        app_fnam = os.path.basename(app_path_fnam_ext)
        self._app_path = os.path.dirname(app_path_fnam_ext)
        self._app_name = os.path.splitext(app_fnam)[0]
        self._app_version = app_version

        # prepare load of config files (done in config_load()) where last existing INI/CFG file is default config file
        # .. to write to and if there is no INI file at all then create on demand a <APP_NAME>.INI file in the cwd
        self._cfg_parser = None
        self._config_files = list()
        self._main_cfg_fnam = None
        self._main_cfg_mod_time = None                  # initially assume there is no main config file
        self.config_init(app_path_fnam_ext, additional_cfg_files)
        self._option_value_stripper = option_value_stripper
        self.config_load()

        if logging_config is None:
            logging_config = dict()
        self._log_file_obj = None
        self._log_file_max_size = logging_config.get('file_size_max', 20)
        self._log_file_name = ""    # will be initialized in self._parse_args() indirectly via logFile setting
        self._log_file_index = 0
        # check if app is using python logging module
        lcd = logging_config.get('py_logging_config_dict', self.get_config('py_logging_config_dict'))
        if lcd:
            # logging.basicConfig(level=logging.DEBUG, style='{')
            logging.config.dictConfig(lcd)     # configure logging module
        self.logging_conf_dict = ae_instances.get('').logging_conf_dict = lcd or dict()

        self.suppress_stdout = suppress_stdout
        if not self.suppress_stdout:    # no log file ready after defining all options (with add_option())
            self.uprint(self._app_name, " V", app_version, "  Startup", self.startup_beg, app_desc, logger=_logger)
            self.uprint("####  Initialization......  ####", logger=_logger)

        # prepare argument parser
        self._arg_parser = ArgumentParser(description=app_desc, formatter_class=formatter_class, epilog=epilog)
        self.add_option('debugLevel', "Display additional debugging info on console output", debug_level_def, 'D',
                        choices=debug_levels.keys())
        self.add_option('logFile', "Copy stdout and stderr into log file", logging_config.get('file_name_def', ''), 'L')

    def __del__(self):
        if ae_instances.get('') is self and not self._shut_down:
            self.shutdown()

    def add_option(self, name, desc, value, short_opt=None, choices=None, multiple=False):
        """
        defining and adding an new option for this app as INI/CFG var and as command line argument.

        :param name:        string specifying the name and short description of this new option.
                            The name value will also be available as long command line argument option (case-sens.).
        :param desc:        description string of this new option.
        :param value:       default value and the type of the option. The value will be used only if the config values
                            are not specified in any config file. The command line argument option value
                            will always overwrite this value (and any value in any config file).
        :param short_opt:   short option character. If not passed or passed as '' then the first character of the name
                            will be used. Please note that the short options 'D' and 'L' are used internally
                            (recommending using only lower-case options for your application).
        :param choices:     list of valid option values (optional, default=allow all values).
        :param multiple:    True if option can be added multiple times to command line (optional, default=False).

            For string expressions that need to evaluated for to determine their value you either can pass
            True for the evaluate parameter or you enclose the string expression with triple high commas.
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

    def add_parameter(self, *args, **kwargs):
        self._arg_parser.add_argument(*args, **kwargs)

    def show_help(self):
        self._arg_parser.print_help(file=app_std_out)

    def _parse_args(self):
        """ this should only get called once and only after all the options have been added with self.add_option().
            self.add_option() sets the determined config file value as the default value and then following call of
            .. _arg_parser.parse_args() overwrites it with command line argument value if given.
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

        if ae_instances.get('') is self and not self.logging_conf_dict:
            self._log_file_name = self.config_options['logFile'].value
            if self._log_file_name:
                try:                        # enable logging
                    self._close_log_file()
                    self._open_log_file()
                    self.uprint(" ###  Activated log file", self._log_file_name, logger=_logger)
                except Exception as ex:
                    self.uprint(" ***  ConsoleApp._parse_args(): exception while trying to enable logging:", ex,
                                logger=_logger)

        # finished argument parsing - now print chosen option values to the console
        _debug_level = self.config_options['debugLevel'].value
        if _debug_level >= DEBUG_LEVEL_ENABLED:
            self.uprint("  ##  Debug Level(" + ", ".join([str(k) + "=" + v for k, v in debug_levels.items()]) + "):",
                        _debug_level, logger=_logger)
            # print sys env - s.a. pyinstaller docs (http://pythonhosted.org/PyInstaller/runtime-information.html)
            if ae_instances.get('') is self:
                self.uprint("  ##  System Environment:", logger=_logger)
                self.uprint(sys_env_text(extra_sys_env_dict={'main cfg': self._main_cfg_fnam}), logger=_logger)
            else:
                self.uprint(" ###  Initialized additional ConsoleApp instance for system env id", self.sys_env_id,
                            logger=_logger)

        self.startup_end = datetime.datetime.now()
        self.uprint(self._app_name, " V", self._app_version, "  Args  parsed", self.startup_end, logger=_logger)
        if ae_instances.get('') is not self and not self.sys_env_id:
            self.uprint("  **  Additional instance of ConsoleApp requested with empty system environment ID",
                        logger=_logger)
        self.uprint("####  Startup finished....  ####", logger=_logger)

    def get_option(self, name, default_value=None):
        """ get the value of the option specified by it's name.

            The returned value has the same type as the value specified in the add_option() call and is the value from
            either (ordered by precedence - first specified/found value will be returned):
            - command line arguments option
            - default section of the INI/CFG file(s) that got specified in the additional_cfg_files parameter of this
              object instantiation (see __init__() method of this class).
            - default section of INI file in the current working directory (cwd)
            - default section of CFG file in the current working directory (cwd)
            - default section of INI file in the application directory (where the main py or exe file is placed)
            - default section of CFG file in the application directory (where the main py or exe file is placed)
            - default section of .console_app_env.cfg in the cwd
            - default section of .console_app_env.cfg in the application directory
            - value argument passed into the add_option() method call (defining the option)
            - default_value argument passed into this method (should actually not happen-add_option() didn't get called)
        """
        if not self._parsed_args:
            self._parse_args()
        return self.config_options[name].value if name in self.config_options else default_value

    def set_option(self, name, val, cfg_fnam=None, save_to_config=True):
        self.config_options[name].value = val
        return self.set_config(name, val, cfg_fnam) if save_to_config else ''

    def get_parameter(self, name):
        if not self._parsed_args:
            self._parse_args()
        return getattr(self._parsed_args, name)

    def config_file_add(self, fnam):
        if os.path.isfile(fnam):
            self._config_files.append(fnam)
            return True

    def config_init(self, app_path_fnam_ext, additional_cfg_files=()):
        cwd_path = os.getcwd()
        app_path = self._app_path

        # prepare config env, first compile cfg/ini files - the last one overwrites previously loaded values
        cwd_path_fnam = os.path.join(cwd_path, self._app_name)
        self._main_cfg_fnam = cwd_path_fnam + INI_EXT  # default will be overwritten by config_load()
        sys_env_id = self.sys_env_id or 'TEST'
        for cfg_path in (app_path, os.path.join(cwd_path, '..', ''), cwd_path, ):
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

    def _get_config_val(self, name, section=None, default_value=None, cfg_parser=None):
        global config_lock
        with config_lock:
            cfg_parser = cfg_parser or self._cfg_parser
            val = cfg_parser.get(section or MAIN_SECTION_DEF, name, fallback=default_value)
        return val

    def config_load(self):
        global config_lock
        for cfg_fnam in reversed(self._config_files):
            if cfg_fnam.endswith(INI_EXT) and os.path.isfile(cfg_fnam):
                self._main_cfg_fnam = cfg_fnam
                self._main_cfg_mod_time = os.path.getmtime(self._main_cfg_fnam)
                break

        with config_lock:
            self._cfg_parser = ConfigParser()
            self._cfg_parser.optionxform = str      # or use 'lambda option: option' to have case sensitive var names
            self._cfg_parser.read(self._config_files, encoding='utf-8')

    def config_main_file_modified(self):
        return self._main_cfg_mod_time and os.path.getmtime(self._main_cfg_fnam) > self._main_cfg_mod_time

    def get_config(self, name, section=None, default_value=None, cfg_parser=None, value_type=None):
        if name in self.config_options and section in (MAIN_SECTION_DEF, '', None):
            val = self.config_options[name].value
        else:
            s = Setting(name=name, value=default_value, value_type=value_type)  # used only for conversion/eval
            s.value = self._get_config_val(name, section=section, default_value=s.value, cfg_parser=cfg_parser)
            val = s.value
        return val

    def set_config(self, name, val, cfg_fnam=None, section=None):
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
                cfg_parser = ConfigParser()     # not using self._cfg_parser for to put INI vars from other files
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

    def dprint(self, *objects, sep=' ', end='\n', file=None, minimum_debug_level=DEBUG_LEVEL_VERBOSE, **kwargs):
        if self.get_option('debugLevel') >= minimum_debug_level:
            self.uprint(*objects, sep=sep, end=end, file=file, debug_level=minimum_debug_level, **kwargs)

    def uprint(self, *objects, sep=' ', end='\n', file=None, debug_level=DEBUG_LEVEL_DISABLED, **kwargs):
        if self.sys_env_id:
            objects = ('{' + self.sys_env_id + '}', ) + objects
        uprint(*objects, sep=sep, end=end, file=file, debug_level=debug_level, **kwargs)

    def app_name(self):
        return self._app_name

    def _append_eof_and_flush_file(self, stream_file, stream_name):
        try:
            try:
                # ALWAYS add \nEoF\n to the end
                # .. we cannot use uprint here because of recursions on log file rotation, so use built-in print()
                # .. self.uprint()
                # .. self.uprint('EoF')
                print()
                print('EoF')
            except Exception as ex:
                self.dprint("Ignorable {} end-of-file marker exception={}".format(stream_name, ex), logger=_logger)

            stream_file.flush()

        except Exception as ex:
            self.dprint("Ignorable {} flush exception={}".format(stream_name, ex), logger=_logger)

    def _open_log_file(self):
        global app_std_out, app_std_err
        self._log_file_obj = open(self._log_file_name, "w")
        if app_std_out == ori_std_out:      # first call/open-of-log-file?
            if self.suppress_stdout:
                std_out = self._nul_std_out = open(os.devnull, 'w')
            else:
                std_out = ori_std_out
            app_std_out = sys.stdout = _DuplicateSysOut(self._log_file_obj, sys_out=std_out)
            app_std_err = sys.stderr = _DuplicateSysOut(self._log_file_obj, sys_out=ori_std_err)
        else:
            app_std_out.log_file = self._log_file_obj
            app_std_err.log_file = self._log_file_obj

    def _rename_log_file(self):
        self._log_file_index = 0 if self._log_file_index >= MAX_NUM_LOG_FILES else self._log_file_index + 1
        index_width = len(str(MAX_NUM_LOG_FILES))
        file_path, file_ext = os.path.splitext(self._log_file_name)
        dfn = file_path + "-{:0>{index_width}}".format(self._log_file_index, index_width=index_width) + file_ext
        if os.path.exists(dfn):
            os.remove(dfn)
        if os.path.exists(self._log_file_name):     # prevent errors after unit test cleanup
            os.rename(self._log_file_name, dfn)

    def _close_log_file(self):
        global app_std_out, app_std_err
        if self._log_file_obj:
            self._append_eof_and_flush_file(self._log_file_obj, "log file")
            app_std_err.log_file = None     # prevent calls of _DuplicateSysOut.log_file.write() to prevent exception
            app_std_out.log_file = None
            sys.stderr = ori_std_err        # set back for to prevent stack overflow/recursion error with kivy logger:
            sys.stdout = ori_std_out        # .. "Fatal Python error: Cannot recover from stack overflow"
            self._log_file_obj.close()
            self._log_file_obj = None
        elif self.logging_conf_dict:
            logging.shutdown()

    def log_file_check_rotation(self):
        if self._log_file_obj is not None:
            if self.multi_threading:
                global log_file_rotation_lock
                log_file_rotation_lock.acquire()
            self._log_file_obj.seek(0, 2)  # due to non-posix-compliant Windows feature
            if self._log_file_obj.tell() >= self._log_file_max_size * 1024 * 1024:
                self._close_log_file()
                self._rename_log_file()
                self._open_log_file()
            if self.multi_threading:
                log_file_rotation_lock.release()

    def shutdown(self, exit_code=0, testing=False):
        if self.multi_threading:
            with config_lock:
                main_thread = threading.current_thread()
                for t in threading.enumerate():
                    if t is not main_thread:
                        self.uprint("  **  joining thread ident <{: >6}> name={}".format(t.ident, t.getName()),
                                    logger=_logger)
                        t.join(0.9 if testing else None)
        if exit_code:
            self.uprint("****  Non-zero exit code:", exit_code, logger=_logger)

        self.uprint("####  Shutdown............  ####", logger=_logger)

        self._close_log_file()
        if self._log_file_index:
            self._rename_log_file()

        if self._nul_std_out and not self._nul_std_out.closed:
            self._append_eof_and_flush_file(self._nul_std_out, "NUL stdout")
            self._nul_std_out.close()
            self._nul_std_out = None

        if ae_instances.get('') is self:
            self._shut_down = True
            if not testing:
                sys.exit(exit_code)
