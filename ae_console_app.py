import sys
import os
import datetime
from builtins import chr  # works like unichr() also in Python 2
import re
import inspect
import pprint
import unicodedata
import threading

from configparser import ConfigParser
from argparse import ArgumentParser, ArgumentError

# supported debugging levels
DEBUG_LEVEL_DISABLED = 0
DEBUG_LEVEL_ENABLED = 1
DEBUG_LEVEL_VERBOSE = 2
DEBUG_LEVEL_TIMESTAMPED = 3
debug_levels = {0: 'disabled', 1: 'enabled', 2: 'verbose', 3: 'timestamped'}

# default name of main config section
MAIN_SECTION_DEF = 'Settings'

# default date/time formats in config files/variables
DATE_TIME_ISO = '%Y-%m-%d %H:%M:%S.%f'
DATE_ISO = '%Y-%m-%d'

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
_ca_instance = None

# global Locks for to prevent errors in log file rotation, config reloads and config reads
log_file_rotation_lock = threading.Lock()
config_lock = threading.Lock()
config_read_lock = threading.Lock()


def _get_debug_level():
    """ determining the debug level of the console app env instance of the currently running app.

    :return: current debug level.
    """
    if _ca_instance and 'debugLevel' in _ca_instance.config_options:
        return _ca_instance.config_options['debugLevel'].value
    return DEBUG_LEVEL_DISABLED


def round_traditional(val, digits=0):
    """ needed because python round() is not working always, like e.g. round(0.074, 2) == 0.07 instead of 0.08
        taken from https://stackoverflow.com/questions/31818050/python-2-7-round-number-to-nearest-integer
    """
    return round(val + 10**(-len(str(val)) - 1), digits)


def fix_encoding(text, encoding=DEF_ENCODING, try_counter=2, pex=None, context='ae_console_app.fix_encoding()'):
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
        try:        # first try to put ori_text in error message
            uprint(pprint.pformat(context + ": " + (str(pex) + '- ' if pex else '') + try_method +
                                  ", " + DEF_ENCODING + " text:\n'" +
                                  ori_text.encode(DEF_ENCODING, errors='backslashreplace').decode(DEF_ENCODING) + "'\n",
                                  indent=12, width=120))

        except UnicodeEncodeError:
            uprint(pprint.pformat(context + ": " + (str(pex) + '- ' if pex else '') + try_method, indent=12, width=120))
    return text


def full_stack_trace(ex):
    ret = "Exception {}. Traceback:\n".format(repr(ex))

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


def to_ascii(unicode_str):
    """
    converts unicode string into ascii representation (for fuzzy string comparision); copied from MiniQuark's answer in:
    https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string

    :param unicode_str:     string to convert
    :return:                converted string (replaced accents, diacritics, ... into normal ascii characters)
    """
    nfkd_form = unicodedata.normalize('NFKD', unicode_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


PLACEHOLDER_PREFIX = '<<<'
PLACEHOLDER_SUFFIX = '>>>'


def substitute_placeholders(expr, key_values, value_prefix=""):
    for key, val in key_values.items():
        # if not isinstance(val, str):
        #    val = str(val)
        expr = expr.replace(PLACEHOLDER_PREFIX + key + PLACEHOLDER_SUFFIX, value_prefix + val)
    return expr


def missing_requirements(obj, requirements, bool_check=False):
    """
    test if obj has the required attribute-/item-hierarchies
    :param obj:             object to inspect/test
    :param requirements:    list of requirement items, each item is a list specifying the path to retrieve the
                            required value. The items of the path list can be a of mix of attribute names and item keys.
    :param bool_check:      (opt, def=False) additionally check if an existing requirement has non-empty/True value.
    :return:                list of missing requirements.
    """
    missing = list()
    for req in requirements:
        val = obj
        for name_or_key in req:
            try:
                val = getattr(val, name_or_key)
            except (AttributeError, TypeError, IndexError, Exception):  # TypeError if name is not str
                try:
                    val = val[name_or_key]
                except (AttributeError, TypeError, IndexError, Exception):
                    missing.append(req)
                    break
        if bool_check and not val:
            missing.append(req)
    return missing


class Setting:
    def __init__(self, name='Unnamed', value=None, value_type=None):
        """ create new Setting instance

        :param name: optional name of the setting (only used for debugging/error-message).
        :param value: optional initial value or evaluable string expression.
        :param value_type: optional value type. cannot be changed later. will be determined latest in value getter.
        """
        super(Setting, self).__init__()
        self._name = name
        self._value = None
        self._type = value_type
        if value is not None:
            self.value = value

    @property
    def value(self):
        value = self._value
        try:
            if self._type != type(value):
                if isinstance(value, bytes):    # convert bytes to string?
                    value = str(value, encoding='utf-8')  # value.decode('utf-8', 'replace') -> shows warning in PyCharm
                if isinstance(value, str):
                    eval_expr = self._eval_str(value)
                    self._value = eval(eval_expr) if eval_expr else \
                        (bool(eval(value)) if self._type == bool else
                         (datetime.datetime.strptime(value, DATE_TIME_ISO)
                          if self._type == datetime.datetime and len(value) > 10 else
                          (datetime.datetime.strptime(value, DATE_ISO).date()
                           if self._type in (datetime.date, datetime.datetime) else
                           (self._type(value) if self._type else value))))
                elif self._type:
                    self._value = self._type(value)
            if not self._type and self._value is not None:      # the value type gets only once initialized
                self._type = type(self._value)
        except Exception as ex:
            uprint("Setting.value exception '{}' on evaluating the setting {} with value: '{}'"
                   .format(ex, self._name, value))
        return self._value

    @value.setter
    def value(self, value):
        if not self._type and not isinstance(value, str) and value is not None:
            self._type = type(value)
        self._value = value

    def append_value(self, value):
        self.value.append(value)
        return self.value

    def convert_value(self, value):
        self.value = value
        return self.value       # using self.value instead of value to call getter for evaluation/type-correction

    @staticmethod
    def _eval_str(str_val):
        """ check str_val if needs to be evaluated and return non-empty-and-stripped-eval-string if yes else '' """
        if (str_val.startswith("'''") and str_val.endswith("'''")) \
                or (str_val.startswith('"""') and str_val.endswith('"""')):
            ret = str_val[3:-3]
        elif (str_val.startswith("[") and str_val.endswith("]")) \
                or (str_val.startswith("{") and str_val.endswith("}")) \
                or (str_val.startswith("(") and str_val.endswith(")")) \
                or (str_val.startswith("'") and str_val.endswith("'")) \
                or (str_val.startswith('"') and str_val.endswith('"')):
            ret = str_val
        else:
            ret = ''
        return ret


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
                enc = self.log_file.encoding
                self.log_file.write(fix_encoding(message, encoding=enc))
        if not self.sys_out.closed:
            self.sys_out.write(message)

    def __getattr__(self, attr):
        return getattr(self.sys_out, attr)


def uprint(*print_objects, sep=" ", end="\n", file=None, flush=False, encode_errors_def='backslashreplace'):
    if not file:
        # app_std_out cannot be specified as file argument default because get initialized after import of this module
        # .. within ConsoleApp._open_log_file(). Use ori_std_out for animation prints (see ae_tcp.py/TcpServer.run()).
        file = ori_std_out if end == "\r" else app_std_out
    enc = file.encoding

    # creating new log file and backup of current one if the current one has more than 20 MB in size
    if _ca_instance is not None:
        _ca_instance.log_file_check_rotation()
        if _ca_instance.multi_threading:            # add thread ident
            print_objects = (" <{: >6}>".format(threading.get_ident()),) + print_objects

    # even with enc == 'UTF-8' and because of _DuplicateSysOut is also writing to file it raises the exception:
    # ..UnicodeEncodeError: 'charmap' codec can't encode character '\x9f' in position 191: character maps to <undefined>
    # if enc == 'UTF-8':
    #     print(*print_objects, sep=sep, end=end, file=file, flush=flush)
    # else:
    #     print(*map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), print_objects),
    #           sep=sep, end=end, file=file, flush=flush)
    if _get_debug_level() >= DEBUG_LEVEL_TIMESTAMPED:
        print_objects = (datetime.datetime.now().strftime(DATE_TIME_ISO),) + print_objects
    try_counter = 2     # skip try_counter 0 and 1 because it is very specific to the Sihot XML interface and XMLParser
    while True:
        try:
            print_strings = map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), print_objects)
            if getattr(_ca_instance, 'multi_threading', False):     # multi_threading not exists in ae_db unit tests
                # prevent fluttered log file content by concatenating print_objects and adding end value
                # .. see https://stackoverflow.com/questions/3029816/how-do-i-get-a-thread-safe-print-in-python-2-6
                # .. and https://stackoverflow.com/questions/50551637/end-key-in-print-not-thread-safe
                print_one_str = sep.join(print_strings)
                sep = ""
                if end:
                    print_one_str += end
                    end = ""
                print_strings = (print_one_str, )
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


INI_EXT = '.ini'


class ConsoleApp:
    def __init__(self, app_version, app_desc, debug_level_def=DEBUG_LEVEL_DISABLED,
                 log_file_def='', config_eval_vars=None, additional_cfg_files=None, log_max_size=20,
                 multi_threading=False, suppress_stdout=False):
        """ encapsulating ConfigParser and ArgumentParser for python console applications
            :param app_version          application version.
            :param app_desc             application description.
            :param debug_level_def      default debug level (DEBUG_LEVEL_DISABLED).
            :param log_file_def         default log file name.
            :param config_eval_vars     dict of additional application specific data values that are used in eval
                                        expressions (e.g. AcuSihotMonitor.ini).
            :param additional_cfg_files list of additional CFG/INI file names (opt. incl. abs/rel. path).
            :param log_max_size         maximum size in MBytes of a log file.
            :param multi_threading      pass True if instance is used in multi-threading app.
            :param suppress_stdout      pass True (for wsgi apps) for to prevent any python print outputs to stdout.
        """
        """
            :ivar _parsed_args          ArgumentParser.parse_args() return - used for to retrieve command line args and
                                        as flag to ensure that the command line arguments get re-parsed if add_option()
                                        get called after a first call to methods which are initiating the re-fetch of
                                        the args and INI/cfg vars (like e.g. get_option() or dprint()).
            :ivar _log_file_obj         file handle of currently opened log file (opened in self._parse_args()).
            :ivar _log_max_size         maximum size in MBytes of a log file.
            :ivar _log_file_name        path and file name of the log file.
            :ivar _log_file_index       index of the current rotation log file backup.
            :ivar config_options        module variable with pre-/user-defined options (dict of Setting instances).
            :var  _ca_instance          module variable referencing this (singleton) instance.
        """
        global _ca_instance
        _ca_instance = self

        self._parsed_args = None
        self._log_file_obj = None       # has to be initialized before _ca_instance, else uprint() will throw exception
        self._log_max_size = log_max_size
        self._log_file_name = ""
        self._log_file_index = 0
        self.multi_threading = multi_threading
        self.suppress_stdout = suppress_stdout

        self.startup_beg = datetime.datetime.now()
        self.config_options = dict()
        self.config_choices = dict()

        self.config_eval_vars = config_eval_vars or dict()

        cwd_path = os.getcwd()
        app_path_fnam_ext = sys.argv[0]
        app_fnam = os.path.basename(app_path_fnam_ext)
        app_path = os.path.dirname(app_path_fnam_ext)

        self._app_name = os.path.splitext(app_fnam)[0]
        self._app_version = app_version

        if not self.suppress_stdout:    # no log file ready after defining all options (with add_option())
            uprint(self._app_name, " V", app_version, "  Startup", self.startup_beg, app_desc)
            uprint("####  Initialization......  ####")

        # prepare config parser, first compile list of cfg/ini files - the last one overwrites previously loaded values
        cwd_path_fnam = os.path.join(cwd_path, self._app_name)
        app_path_fnam = os.path.splitext(app_path_fnam_ext)[0]
        config_files = [os.path.join(app_path, '.console_app_env.cfg'), os.path.join(cwd_path, '.console_app_env.cfg'),
                        os.path.join(app_path, '.sys_env.cfg'), os.path.join(cwd_path, '.sys_env.cfg'),
                        app_path_fnam + '.cfg', app_path_fnam + INI_EXT,
                        cwd_path_fnam + '.cfg', cwd_path_fnam + INI_EXT,
                        ]
        if additional_cfg_files:
            for cfg_fnam in additional_cfg_files:
                add_cfg_path_fnam = os.path.join(cwd_path, cfg_fnam)
                if os.path.isfile(add_cfg_path_fnam):
                    config_files.append(add_cfg_path_fnam)
                else:
                    add_cfg_path_fnam = os.path.join(app_path, cfg_fnam)
                    if os.path.isfile(add_cfg_path_fnam):
                        config_files.append(add_cfg_path_fnam)
                    elif os.path.isfile(cfg_fnam):
                        config_files.append(cfg_fnam)
                    else:
                        # this is an error, no need to: file=app_std_err if self.suppress_stdout else app_std_out
                        uprint("****  Additional config file {} not found!".format(cfg_fnam))
        # prepare load of config files (done in load_config()) where last existing INI/CFG file is default config file
        # .. to write to and if there is no INI file at all then create on demand a <APP_NAME>.INI file in the cwd
        self._cfg_parser = None
        self._config_files = config_files
        self._main_cfg_fnam = cwd_path_fnam + INI_EXT   # default will be overwritten by load_config()
        self._main_cfg_mod_time = None                  # initially assume there is no main config file
        self.load_config()

        # prepare argument parser
        self._arg_parser = ArgumentParser(description=app_desc)
        self.add_option('debugLevel', "Display additional debugging info on console output", debug_level_def, 'D',
                        choices=debug_levels.keys())
        self.add_option('logFile', "Copy stdout and stderr into log file", log_file_def, 'L')

    def add_option(self, name, desc, value, short_opt=None, choices=None, multiple=False):
        """ defining and adding an new option for this app as INI/CFG var and as command line argument.

            The name and desc arguments are strings that are specifying the name and short description of the option
            of the console app. The name value will also be available as long command line argument option (case-sens.).

            The value argument is specifying the default value and the type of the option. It will be used only
            if the config values are not specified in any config file. The command line argument option value
            will always overwrite this value (and any value in any config file).

            If the short option character get not passed into short_opt then the first character of the name
            is used. The short options 'D' and 'L' are used internally (recommending using only lower-case options).

            For string expressions that need to evaluated for to determine their value you either can pass
            True for the evaluate parameter or you enclose the string expression with triple high commas.
        """
        self._parsed_args = None        # request (re-)parsing of command line args
        if not short_opt:
            short_opt = name[0]

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
        self._arg_parser.add_argument('-' + short_opt, '--' + name, **kwargs)
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
                    allowed_values = self.config_choices[name]
                    if given_value not in allowed_values:
                        raise ArgumentError(None, "Wrong {} option value {}; allowed are {}"
                                            .format(name, given_value, allowed_values))

        self._log_file_name = self.config_options['logFile'].value
        if self._log_file_name:  # enable logging
            try:
                self._close_log_file()
                self._open_log_file()
                uprint('Log file:', self._log_file_name)
            except Exception as ex:
                uprint("****  ConsoleApp._parse_args(): enable logging exception=", ex)

        # finished argument parsing - now print chosen option values to the console
        _debug_level = self.config_options['debugLevel'].value
        if _debug_level >= DEBUG_LEVEL_ENABLED:
            uprint("Debug Level(" + ", ".join([str(k) + "=" + v for k, v in debug_levels.items()]) + "):", _debug_level)
            # print sys env - s.a. pyinstaller docs (http://pythonhosted.org/PyInstaller/runtime-information.html)
            uprint("System Environment:")
            uprint(" "*18, "python ver=", str(sys.version))
            uprint(" "*18, "argv      =", str(sys.argv))
            uprint(" "*18, "executable=", sys.executable)
            uprint(" "*18, "cwd       =", os.getcwd())
            uprint(" "*18, "__file__  =", __file__)
            uprint(" "*18, "frozen    =", getattr(sys, 'frozen', False))
            if getattr(sys, 'frozen', False):
                uprint(" "*18, "bundle-dir=", getattr(sys, '_MEIPASS', '*#ERR#*'))
            uprint(" " * 18, "main-cfg  =", self._main_cfg_fnam)

        self.startup_end = datetime.datetime.now()
        uprint(self._app_name, " V", self._app_version, "  Args  parsed", self.startup_end)
        uprint("####  Startup finished....  ####")

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

    def _get_config_val(self, name, section=None, default_value=None, cfg_parser=None):
        global config_lock
        with config_lock:
            cfg_parser = cfg_parser or self._cfg_parser
            val = cfg_parser.get(section or MAIN_SECTION_DEF, name, fallback=default_value)
        return val

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
        if not cfg_fnam:
            cfg_fnam = self._main_cfg_fnam
        if not section:
            section = MAIN_SECTION_DEF

        if name in self.config_options and section in (MAIN_SECTION_DEF, '', None):
            self.config_options[name].value = val

        if not os.path.isfile(cfg_fnam):
            return "****  INI/CFG file " + str(cfg_fnam) + " not found. Please set the ini/cfg variable " \
                   + section + "/" + str(name) + " manually to the value " + str(val)

        err_msg = ''
        with config_lock:
            try:
                cfg_parser = ConfigParser()     # not using self._cfg_parser for to put INI vars from other files
                cfg_parser.optionxform = str    # or use 'lambda option: option' to have case sensitive var names
                cfg_parser.read(cfg_fnam)
                if isinstance(val, dict) or isinstance(val, list) or isinstance(val, tuple):
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
                err_msg = "****  ConsoleApp.set_option(" + str(name) + ", " + str(val) + ") exception: " + str(ex)

        return err_msg

    def config_main_file_modified(self):
        return self._main_cfg_mod_time and os.path.getmtime(self._main_cfg_fnam) > self._main_cfg_mod_time

    def load_config(self):
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

    def dprint(self, *objects, sep=' ', end='\n', file=None, minimum_debug_level=DEBUG_LEVEL_ENABLED):
        if self.get_option('debugLevel') >= minimum_debug_level:
            uprint(*objects, sep=sep, end=end, file=file)

    def app_name(self):
        return self._app_name

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
        os.rename(self._log_file_name, dfn)

    def _close_log_file(self):
        global app_std_out, app_std_err
        if self._log_file_obj:
            app_std_out.log_file = None
            app_std_err.log_file = None
            self._log_file_obj.close()
            self._log_file_obj = None

    def log_file_check_rotation(self):
        if self._log_file_obj is not None:
            if self.multi_threading:
                global log_file_rotation_lock
                log_file_rotation_lock.acquire()
            self._log_file_obj.seek(0, 2)  # due to non-posix-compliant Windows feature
            if self._log_file_obj.tell() >= self._log_max_size * 1024 * 1024:
                self._close_log_file()
                self._rename_log_file()
                self._open_log_file()
            if self.multi_threading:
                log_file_rotation_lock.release()

    def shutdown(self, exit_code=0):
        if self.multi_threading:
            with config_lock:
                main_thread = threading.current_thread()
                for t in threading.enumerate():
                    if t is not main_thread:
                        uprint("  **  joining thread ident <{: >6}> name={}".format(t.ident, t.getName()))
                        t.join()
        if exit_code:
            uprint("****  Non-zero exit code:", exit_code)

        uprint('####  Shutdown............  ####')

        if self._log_file_obj:
            app_std_err.log_file = None     # prevent calls of _DuplicateSysOut.log_file.write() to prevent exception
            app_std_out.log_file = None
            sys.stdout = ori_std_out        # set back for to prevent stack overflow/recursion error with kivy logger:
            sys.stderr = ori_std_err        # .. "Fatal Python error: Cannot recover from stack overflow"
            self._close_log_file()
            if self._log_file_index:
                self._rename_log_file()

        if self._nul_std_out and not self._nul_std_out.closed:
            self._nul_std_out.close()

        sys.exit(exit_code)


class Progress:
    def __init__(self, debug_level,  # default next message built only if >= DEBUG_LEVEL_VERBOSE
                 start_counter=0, total_count=0,  # pass either start_counter or total_counter (never both)
                 start_msg="", next_msg="",  # message templates/masks for start, processing and end
                 end_msg="Finished processing of {total_count} having {err_counter} failures:{err_msg}",
                 err_msg="{err_counter} failures on processing of {total_count} items, current={run_counter}:{err_msg}",
                 nothing_to_do_msg=''):
        if not next_msg and debug_level >= DEBUG_LEVEL_VERBOSE:
            next_msg = "Processing '{processed_id}': " + \
                       ("left" if start_counter > 0 and total_count == 0 else "item") + \
                       " {run_counter} of {total_count}. {err_counter} errors={err_msg}"

        def _complete_msg_prefix(msg, pch='#'):
            return (pch in msg and msg) or msg and " " + pch * 3 + "  " + msg or ""

        self._next_msg = _complete_msg_prefix(next_msg)
        self._end_msg = _complete_msg_prefix(end_msg)
        self._err_msg = _complete_msg_prefix(err_msg, '*')

        self._err_counter = 0
        self._run_counter = start_counter + 1  # def=decrementing run_counter
        self._total_count = start_counter
        self._delta = -1
        if total_count > 0:  # incrementing run_counter
            self._run_counter = 0
            self._total_count = total_count
            self._delta = 1
        elif start_counter <= 0:
            if nothing_to_do_msg:
                uprint(_complete_msg_prefix(nothing_to_do_msg))
            return  # RETURN -- empty set - nothing to process

        if start_msg:
            uprint(_complete_msg_prefix(start_msg).format(run_counter=self._run_counter + self._delta,
                                                          total_count=self._total_count))

    def next(self, processed_id='', error_msg='', next_msg=''):
        self._run_counter += self._delta
        if error_msg:
            self._err_counter += 1

        if error_msg and self._err_msg:
            uprint(self._err_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                        err_counter=self._err_counter, err_msg=error_msg, processed_id=processed_id))

        if not next_msg:
            next_msg = self._next_msg
        if next_msg:
            # using uprint with end parameter instead of leading \r will NOT GET DISPLAYED within PyCharm,
            # .. also not with flush - see http://stackoverflow.com/questions/34751441/
            # when-writing-carriage-return-to-a-pycharm-console-the-whole-line-is-deleted
            # .. uprint('   ', pend, end='\r', flush=True)
            next_msg = '\r' + next_msg
            uprint(next_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                   err_counter=self._err_counter, err_msg=error_msg, processed_id=processed_id))

    def finished(self, error_msg=''):
        if error_msg and self._err_msg:
            uprint(self._err_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                        err_counter=self._err_counter, err_msg=error_msg))
        uprint(self.get_end_message(error_msg=error_msg))

    def get_end_message(self, error_msg=''):
        return self._end_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                    err_counter=self._err_counter, err_msg=error_msg)


class NamedLocks:
    """
    allow to create named lock(s) within the same app (migrate from https://stackoverflow.com/users/355230/martineau
    answer in stackoverflow on the question https://stackoverflow.com/questions/37624289/value-based-thread-lock.

    Currently the sys_lock feature is not implemented. Use either ae_lockfile or the github extension portalocker (see
    https://github.com/WoLpH/portalocker) or the encapsulating extension ilock (https://github.com/symonsoft/ilock).
    More on system wide named locking: https://stackoverflow.com/questions/6931342/system-wide-mutex-in-python-on-linux.
    """
    locks_change_lock = threading.Lock()
    active_locks = {}
    active_lock_counters = {}

    def __init__(self, *lock_names, sys_lock=False):
        self._lock_names = lock_names
        self._sys_lock = sys_lock
        _ca_instance.dprint("NamedLocks.__init__", lock_names, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        assert not sys_lock, "sys_lock is currently not implemented"

    def __enter__(self):
        _ca_instance.dprint("NamedLocks.__enter__", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        for lock_name in self._lock_names:
            _ca_instance.dprint("NamedLocks.__enter__ b4 acquire ", lock_name, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            self.acquire(lock_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        _ca_instance.dprint("NamedLocks __exit__", exc_type, exc_val, exc_tb, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        for lock_name in self._lock_names:
            _ca_instance.dprint("NamedLocks.__exit__ b4 release ", lock_name, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            self.release(lock_name)

    def acquire(self, lock_name, *args, **kwargs):
        _ca_instance.dprint("NamedLocks.acquire", lock_name, 'START', minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        with self.locks_change_lock:
            if lock_name in self.active_locks:
                self.active_lock_counters[lock_name] += 1
            else:
                self.active_locks[lock_name] = threading.Lock()
                self.active_lock_counters[lock_name] = 1

        lock_acquired = self.active_locks[lock_name].acquire(*args, **kwargs)
        _ca_instance.dprint("NamedLocks.acquire", lock_name, 'END', minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        return lock_acquired

    def release(self, lock_name, *args, **kwargs):
        _ca_instance.dprint("NamedLocks.release", lock_name, 'START', minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        with self.locks_change_lock:
            if self.active_lock_counters[lock_name] == 1:
                del self.active_lock_counters[lock_name]
                lock = self.active_locks.pop(lock_name)
            else:
                self.active_lock_counters[lock_name] -= 1
                lock = self.active_locks[lock_name]

        lock.release(*args, **kwargs)
        _ca_instance.dprint("NamedLocks.release", lock_name, 'END', minimum_debug_level=DEBUG_LEVEL_VERBOSE)
