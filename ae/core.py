"""
ae package core constants, helper functions and base classes
============================================================

AppBase
-------

Enable Logging
..............


Enable Multi-Thread-Safety
..........................


"""
import datetime
import inspect
import logging
import logging.config
import os
import sys
import threading
import unicodedata
import weakref
from string import ascii_letters, digits
from typing import Any, AnyStr, Dict, Optional, TextIO, Generator

DEBUG_LEVEL_DISABLED: int = 0       #: lowest debug level - only display logging levels ERROR/CRITICAL.
DEBUG_LEVEL_ENABLED: int = 1        #: minimum debugging info - display logging levels WARNING or higher.
DEBUG_LEVEL_VERBOSE: int = 2        #: verbose debug info - display logging levels INFO/DEBUG or higher.
DEBUG_LEVEL_TIMESTAMPED: int = 3    #: highest/verbose debug info - including timestamps in the log output.
DEBUG_LEVELS: Dict[int, str] = {0: 'disabled', 1: 'enabled', 2: 'verbose', 3: 'timestamped'}    #: debug level names

LOGGING_LEVELS: Dict[int, int] = {DEBUG_LEVEL_DISABLED: logging.ERROR, DEBUG_LEVEL_ENABLED: logging.WARNING,
                                  DEBUG_LEVEL_VERBOSE: logging.INFO, DEBUG_LEVEL_TIMESTAMPED: logging.DEBUG}
""" association between ae debug levels and python logging levels.
"""

DATE_TIME_ISO: str = '%Y-%m-%d %H:%M:%S.%f'     #: ISO string format for datetime values in config files/variables
DATE_ISO: str = '%Y-%m-%d'                      #: ISO string format for date values in config files/variables

DEF_ENCODING: str = 'ascii'
""" core encoding that will always work independent from destination (console, file system, XMLParser, ...).
"""

INI_EXT: str = '.ini'                       #: INI file extension

MAIN_SECTION_DEF: str = 'aeOptions'         #: default name of main config section

MAX_NUM_LOG_FILES: int = 69                 #: maximum number of log files
LOG_FILE_MAX_SIZE: int = 20                 #: maximum size in MB of a rotating log file

log_file_rotation_lock = threading.Lock()   #: log file rotation lock

# The following line is throwing an error in the Sphinx docs make:
# app_instances: weakref.WeakValueDictionary[str, "AppBase"] = weakref.WeakValueDictionary() #: dict of app instances
app_instances = weakref.WeakValueDictionary()   # type: weakref.WeakValueDictionary[str, AppBase]
""" `app_instances` is holding the references for all :class:`AppBase` instances created at run time.

The first created :class:`AppBase` instance is called the main app instance and has an empty string as the dict key.
This weak dict gets automatically initialized in :func:`AppBase.__init__` for to allow log file split/rotation
and debugLevel access at application thread or module level.
"""


# save original stdout/stderr
ori_std_out = sys.stdout
ori_std_err = sys.stderr
app_std_out = ori_std_out
app_std_err = ori_std_err


def stack_frames(depth: int = 1) -> Generator:    # Generator[frame, None, None]
    """ generator diving deeper into the call stack from the level given in :paramref:`stack_frames.depth`.

    :param depth:           the calling level from which on to start (def=1 which refers the next deeper stack frame).
                            Pass 2 or a even higher value if you want to start with a deeper frame in the call stack.
    :return:                The stack frame of a deeper level within the call stack.
    """
    try:
        while True:
            # noinspection PyProtectedMember
            yield sys._getframe(depth)
            depth += 1
    except (TypeError, AttributeError, ValueError):
        pass


def stack_module(*skip_modules: str, depth: int = 1) -> Optional[str]:
    """ find the first module in the call stack that is *not* in :paramref:`stack_module.skip_modules`.

    :param skip_modules:    module names to skip (def=this ae.core module).
    :param depth:           the calling level from which on to search (def=1 which refers the next deeper frame).
                            Pass 2 or a even higher value if you want to get the module name from a deeper level
                            in the call stack.
    :return:                The module name of a deeper level within the call stack.
    """
    if not skip_modules:
        skip_modules = (__name__, )
    return stack_var('__name__', *skip_modules, depth=depth)


def stack_var(name: str, *skip_modules: str, depth: int = 1, locals_only: bool = False) -> Optional[Any]:
    """ determine variable value in calling stack/frames.

    :param name:            variable name.
    :param skip_modules:    module names to skip (def=this ae.core module).
    :param depth:           the calling level from which on to search (def=1 which refers the next deeper stack frame).
                            Pass 2 or a even higher value if you want to get the variable value from a deeper level
                            in the call stack.
    :param locals_only:     pass True to only check for local variables (ignoring globals).
    :return:                The variable value of a deeper level within the call stack.
    """
    val = None
    for frame in stack_frames(depth):
        global_vars = frame.f_globals
        variables = frame.f_locals if locals_only else global_vars
        if global_vars.get('__name__') not in skip_modules and name in variables:
            val = variables[name]
            break
    return val


def correct_email(email, changed=False, removed=None):
    """ check and correct email address from a user input (removing all comments)

    Special conversions that are not returned as changed/corrected are: the domain part of an email will be corrected
    to lowercase characters, additionally emails with all letters in uppercase will be converted into lowercase.

    Regular expressions are not working for all edge cases (see the answer to this SO question:
    https://stackoverflow.com/questions/201323/using-a-regular-expression-to-validate-an-email-address) because RFC822
    is very complex (even the reg expression recommended by RFC 5322 is not complete; there is also a
    more readable form given in the informational RFC 3696). Additionally a regular expression
    does not allow corrections. Therefore this function is using a procedural approach (using recommendations from
    RFC 822 and https://en.wikipedia.org/wiki/Email_address).

    :param email:       email address
    :param changed:     (optional) flag if email address got changed (before calling this function) - will be returned
                        unchanged if email did not get corrected.
    :param removed:     (optional) list declared by caller for to pass back all the removed characters including
                        the index in the format "<index>:<removed_character(s)>".
    :return:            tuple of (possibly corrected email address, flag if email got changed/corrected)
    """
    if email is None:
        return "", False

    if removed is None:
        removed = list()

    letters_or_digits = ascii_letters + digits
    in_local_part = True
    in_quoted_part = False
    in_comment = False
    all_upper_case = True
    local_part = ""
    domain_part = ""
    domain_beg_idx = -1
    domain_end_idx = len(email) - 1
    comment = ''
    last_ch = ''
    ch_before_comment = ''
    for idx, ch in enumerate(email):
        if ch.islower():
            all_upper_case = False
        next_ch = email[idx + 1] if idx + 1 < domain_end_idx else ''
        if in_comment:
            comment += ch
            if ch == ')':
                in_comment = False
                removed.append(comment)
                last_ch = ch_before_comment
            continue
        elif ch == '(' and not in_quoted_part \
                and (idx == 0 or email[idx:].find(')@') >= 0 if in_local_part
                     else idx == domain_beg_idx or email[idx:].find(')') == domain_end_idx - idx):
            comment = str(idx) + ':('
            ch_before_comment = last_ch
            in_comment = True
            changed = True
            continue
        elif ch == '"' \
                and (not in_local_part
                     or last_ch != '.' and idx and not in_quoted_part
                     or next_ch not in ('.', '@') and last_ch != '\\' and in_quoted_part):
            removed.append(str(idx) + ':' + ch)
            changed = True
            continue
        elif ch == '@' and in_local_part and not in_quoted_part:
            in_local_part = False
            domain_beg_idx = idx + 1
        elif ch in letters_or_digits:  # ch.isalnum():
            pass  # uppercase and lowercase Latin letters A to Z and a to z (isalnum() includes also umlauts)
        elif ord(ch) > 127 and in_local_part:
            pass    # international characters above U+007F
        elif ch == '.' and in_local_part and not in_quoted_part and last_ch != '.' and idx and next_ch != '@':
            pass    # if not the first or last unless quoted, and does not appear consecutively unless quoted
        elif ch in ('-', '.') and not in_local_part and (last_ch != '.' or ch == '-') \
                and idx not in (domain_beg_idx, domain_end_idx):
            pass    # if not duplicated dot and not the first or last character in domain part
        elif (ch in ' (),:;<>@[]' or ch in '\\"' and last_ch == '\\' or ch == '\\' and next_ch == '\\') \
                and in_quoted_part:
            pass    # in quoted part and in addition, a backslash or double-quote must be preceded by a backslash
        elif ch == '"' and in_local_part:
            in_quoted_part = not in_quoted_part
        elif (ch in "!#$%&'*+-/=?^_`{|}~" or ch == '.'
              and (last_ch and last_ch != '.' and next_ch != '@' or in_quoted_part)) \
                and in_local_part:
            pass    # special characters (in local part only and not at beg/end and no dup dot outside of quoted part)
        else:
            removed.append(str(idx) + ':' + ch)
            changed = True
            continue

        if in_local_part:
            local_part += ch
        else:
            domain_part += ch.lower()
        last_ch = ch

    if all_upper_case:
        local_part = local_part.lower()

    return local_part + domain_part, changed


def correct_phone(phone, changed=False, removed=None, keep_1st_hyphen=False):
    """ check and correct phone number from a user input (removing all invalid characters including spaces)

    :param phone:           phone number
    :param changed:         (optional) flag if phone got changed (before calling this function) - will be returned
                            unchanged if phone did not get corrected.
    :param removed:         (optional) list declared by caller for to pass back all the removed characters including
                            the index in the format "<index>:<removed_character(s)>".
    :param keep_1st_hyphen: (optional, def=False) pass True for to keep at least the first occurring hyphen character.
    :return:                tuple of (possibly corrected phone number, flag if phone got changed/corrected)
    """

    if phone is None:
        return "", False

    if removed is None:
        removed = list()

    corr_phone = ''
    got_hyphen = False
    for idx, ch in enumerate(phone):
        if ch.isdigit():
            corr_phone += ch
        elif keep_1st_hyphen and ch == '-' and not got_hyphen:
            got_hyphen = True
            corr_phone += ch
        else:
            if ch == '+' and not corr_phone and not phone[idx + 1:].startswith('00'):
                corr_phone = '00'
            removed.append(str(idx) + ':' + ch)
            changed = True

    return corr_phone, changed


def force_encoding(text: AnyStr, encoding: str = DEF_ENCODING, errors: str = 'backslashreplace') -> str:
    """ force/ensure the encoding of text (str or bytes) without any UnicodeDecodeError/UnicodeEncodeError.

    :param text:        text as str/byte.
    :param encoding:    encoding (def=DEF_ENCODING).
    :param errors:      encode error handling (def='backslashreplace').

    :return:            text as str (with all characters checked/converted/replaced for to be encode-able).
    """
    if isinstance(text, str):
        text = text.encode(encoding=encoding, errors=errors)
    return text.decode(encoding=encoding)


def full_stack_trace(ex: Exception) -> str:
    """ get full stack trace from an exception.

    :param ex:  exception instance.
    :return:    str with stack trace info.
    """
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


def round_traditional(num_value: float, num_digits: int = 0) -> float:
    """ round numeric value traditional.

    Needed because python round() is working differently, e.g. round(0.075, 2) == 0.07 instead of 0.08
    taken from https://stackoverflow.com/questions/31818050/python-2-7-round-number-to-nearest-integer.

    :param num_value:   float value to be round.
    :param num_digits:  number of digits to be round (def=0 - rounds to an integer value).

    :return:        rounded value.
    """
    return round(num_value + 10 ** (-len(str(num_value)) - 1), num_digits)


def sys_env_dict(file: str = __file__) -> dict:
    """ returns dict with python system run-time environment values.

    :param file:    optional file name (def=__file__/ae.core.py).
    :return:        python system run-time environment values like python_ver, argv, cwd, executable, __file__, frozen
                    and bundle_dir.
    """
    sed = dict()
    sed['python_ver'] = sys.version
    sed['argv'] = sys.argv
    sed['executable'] = sys.executable
    sed['cwd'] = os.getcwd()
    sed['__file__'] = file
    sed['frozen'] = getattr(sys, 'frozen', False)
    if getattr(sys, 'frozen', False):
        sed['bundle_dir'] = getattr(sys, '_MEIPASS', '*#ERR#*')
    return sed


def sys_env_text(file: str = __file__, ind_ch: str = " ", ind_len: int = 18, key_ch: str = "=", key_len: int = 12,
                 extra_sys_env_dict: Optional[Dict[str, str]] = None) -> str:
    """ compile formatted text block with system environment info.

    :param file:                main module file name (def=__file__).
    :param ind_ch:              indent character (def=" ").
    :param ind_len:             indent depths (def=18 characters).
    :param key_ch:              key-value separator character (def=" =").
    :param key_len:             key-name maximum length (def=12 characters).
    :param extra_sys_env_dict:  dict with additional system info items.
    :return:                    text block with system environment info.
    """
    sed = sys_env_dict(file=file)
    if extra_sys_env_dict:
        sed.update(extra_sys_env_dict)
    text = "\n".join(["{ind:{ind_ch}>{ind_len}}{key:{key_ch}<{key_len}}{val}"
                     .format(ind="", ind_ch=ind_ch, ind_len=ind_len, key=k, key_ch=key_ch, key_len=key_len, val=v)
                      for k, v in sed.items()])
    return text


def to_ascii(unicode_str: str) -> str:
    """ converts unicode string into ascii representation.

    Useful for fuzzy string comparision; copied from MiniQuark's answer
    in: https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string

    :param unicode_str:     string to convert.
    :return:                converted string (replaced accents, diacritics, ... into normal ascii characters).
    """
    nfkd_form = unicodedata.normalize('NFKD', unicode_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


def main_app_instance() -> Optional["AppBase"]:
    """ determine the main instance of the :class:`AppBase` in the current running application.

    :return:    main :class:`AppBase` instance or None (if app is not fully initialized yet).
    """
    return app_instances.get('')


def _get_debug_level() -> int:
    """ determining the debug level of the main :class:`AppBase` instance of the currently running app.

    :return: current debug level.
    """
    main_instance = main_app_instance()
    if main_instance:
        return main_instance.debug_level
    return DEBUG_LEVEL_DISABLED


class _DuplicateSysOut:
    """ private helper class used by :class:`AppBase` for to duplicate the standard output stream to an log file.
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
                # log file has different encoding than console/shell, so simply replace with backslash
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


def print_out(*objects, sep: str = " ", end: str = "\n", file: Optional[TextIO] = None, flush: bool = False,
              encode_errors_def: str = 'backslashreplace', debug_level: Optional[int] = None,
              logger: Optional['logging.Logger'] = None, app_instance: Optional['AppBase'] = None,
              **kwargs) -> None:
    """ universal/unbreakable print function - replacement for the python print() built-in.

    This function is silently handling and auto-correcting string encode errors for output streams which are
    not supporting unicode. Any instance of :class:`AppBase` is providing this function as a method with the
    :func:`same name <AppBase.print_out>`). It is recommended to call/use the instance method instead of this function.

    :param objects:             tuple of objects to be printed.
    :param sep:                 separator character between each printed object/string (def=" ").
    :param end:                 finalizing character added to the end of this print (def="\\\\n").
    :param file:                output stream object to be printed to (def=None which will use standard output streams).
    :param flush:               flush stream after printing (def=False).
    :param encode_errors_def:   default error handling for to encode (def='backslashreplace').
    :param debug_level:         current debug level (def=None).
    :param logger:              used logger for to output `objects` (def=None).
    :param app_instance:        used instance of :class:`AppBase` or :class:`~console_app.ConsoleApp`
                                (def=None -> use the main app instance).
    :param kwargs:              additional kwargs dict (items will be printed to the output stream).

    This function has an alias named :meth:`.po`.
    """
    processing = end == "\r"
    if not file:
        # app_std_out cannot be specified as file argument default because get initialized after import of this module
        # .. within AppBase._open_log_file(). Use ori_std_out for animation prints (see tcp.py/TcpServer.run()).
        file = ori_std_out if processing else app_std_out
    enc = file.encoding

    if app_instance is None:
        app_instance = main_app_instance()
    if app_instance is not None:
        if getattr(app_instance, 'multi_threading', False):            # add thread ident
            objects = (" <{: >6}>".format(threading.get_ident()),) + objects
        if getattr(app_instance, '_log_file_obj', False):
            # creating new log file and backup of current one if the current has more than LOG_FILE_MAX_SIZE MB in size
            app_instance.log_file_check_rotation()

    # even with enc == 'UTF-8' and because of _DuplicateSysOut is also writing to file it raises the exception:
    # ..UnicodeEncodeError: 'charmap' codec can't encode character '\x9f' in position 191: character maps to <undefined>
    # if enc == 'UTF-8':
    #     print(*objects, sep=sep, end=end, file=file, flush=flush)
    # else:
    #     print(*map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), objects),
    #           sep=sep, end=end, file=f   ile, flush=flush)
    if _get_debug_level() >= DEBUG_LEVEL_TIMESTAMPED:
        objects = (datetime.datetime.now().strftime(DATE_TIME_ISO),) + objects

    if kwargs:
        objects += ("\n   *  EXTRA KWARGS={}".format(kwargs),)

    use_logger = not processing and debug_level in LOGGING_LEVELS \
        and getattr(app_instance, 'logging_params', False)
    if use_logger and logger is None:
        logger_late_init()
        module = stack_module()
        logger = logging.getLogger(module) if module else _logger

    retries = 2
    while retries:
        try:
            print_strings = map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), objects)
            if use_logger or getattr(app_instance, 'multi_threading', False):
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


po = print_out              #: alias of function :func:`.print_out`


class AppBase:
    """ provides easy logging and debugging for your application.

    Most applications only need a single instance of this class; apps with threads could create separate instances
    for each thread.

    Instance Attributes (ordered alphabetically - ignoring underscore characters):

    * :attr:`app_name`              basename (without the file name extension) of the executable.
    * :attr:`_app_path`             file path of executable.
    * :attr:`app_title`             application title/description.
    * :attr:`app_version`           application version (set via the :paramref:`AppBase.__init__.app_version` arg).
    * :attr:`_log_file_index`       index of the current rotation log file backup.
    * :attr:`_log_file_max_size`    maximum size in MBytes of a log file.
    * :attr:`_log_file_name`        path and file name of the log file.
    * :attr:`_log_file_obj`         file handle of currently opened log file (opened in :meth:~AppBase._open_log_file`).
    * :attr:`logging_params`        python logging config dict.
    * :attr:`multi_threading`       set to True if your application uses threads.
    * :attr:`_nul_std_out`          null stream used for to prevent printouts on stdout of the console/shell.
    * :attr:`_shut_down`            flag set to True if application shutdown was already processed.
    * :attr:`startup_beg`           datetime of begin of app instantiation/startup.
    * :attr:`startup_end`           datetime of end of app instantiation/startup.
    * :attr:`suppress_stdout`       flag set to True if application does not print to stdout/console.
    * :attr:`sys_env_id`            system environment id of this instance.
    """
    def __init__(self, app_title: str = '', app_version: str = '',
                 debug_level_def: int = DEBUG_LEVEL_DISABLED, multi_threading: bool = False, sys_env_id: str = ''):
        """ initialize a new :class:`AppBase` instance.

        :param app_title:               application title/description (def=value of main module docstring).
        :param app_version:             application version (def=value of global __version__ in call stack).
        :param debug_level_def:         default debug level (def=DEBUG_LEVEL_DISABLED).
        :param multi_threading:         pass True if instance is used in multi-threading app.
        :param sys_env_id:              system environment id used as file name suffix for to load all
                                        the system config variables in sys_env<suffix>.cfg (def='', pass e.g. 'LIVE'
                                        for to init second :class:`AppBase` instance with values from sys_envLIVE.cfg).
        """
        self.startup_beg: datetime.datetime = datetime.datetime.now()       #: begin of app startup datetime

        if not app_title:
            app_title = stack_var('__doc__', 'ae.core')
        if not app_version:
            app_version = stack_var('__version__')

        self.app_title: str = app_title                                     #: app title/description
        self.app_version: str = app_version                                 #: version of your app
        self.debug_level: int = debug_level_def                             #: app debug level
        self.multi_threading: bool = multi_threading                        #: True if app uses multiple threads
        self.sys_env_id: str = sys_env_id                                   #: system environment id of this instance

        self._nul_std_out: Optional[TextIO] = None                          #: logging null stream
        self._shut_down: bool = False                                       #: True if app got shut down already

        # init later in :meth:`~AppBase.init_logging` - block initially until app-config/-logging is fully initialized
        self.suppress_stdout: bool = True                                   #: flag to suppress prints to stdout
        self.logging_params: Dict[str, Any] = dict()                        #: dict of config parameters for py logging
        self.startup_end: Optional[datetime.datetime] = None                #: end of app startup datetime

        if not sys.argv:    # prevent unit tests to fail on empty sys.argv
            sys.argv.append(os.path.join(os.getcwd(), 'TesT.exe'))

        app_path_fnam_ext = sys.argv[0]
        app_fnam = os.path.basename(app_path_fnam_ext)
        self.app_name: str = os.path.splitext(app_fnam)[0]                  #: main app code file's base name (w/o ext)
        self._app_path: str = os.path.dirname(app_path_fnam_ext)            #: path to folder of your main app code file

        main_instance = main_app_instance()
        if main_instance is None:
            app_instances[''] = self
        if sys_env_id not in app_instances:
            app_instances[sys_env_id] = self

        self._log_file_max_size: int = LOG_FILE_MAX_SIZE                    #: maximum log file size (rotating logs)
        self._log_file_obj: Optional[TextIO] = None                         #: log file stream instance
        self._log_file_index: int = 0                                       #: log file index (for rotating logs)
        self._log_file_name: str = ""                                       #: log file name

    def init_logging(self, logging_params: Optional[Dict[str, Any]] = None, suppress_stdout: bool = False):
        """ prepare logging: most values will be initialized in self._parse_args() indirectly via logFile config option

        :param logging_params:          dict with logging configuration values - supported dict keys are:

                                        * `py_logging_params`: config dict for python logging configuration.
                                          If this inner dict is not empty then python logging is configured with the
                                          given options and all the other keys for ae logging underneath
                                          are ignored.
                                        * `file_name_def`: default log file name for ae logging (def='').
                                        * `file_size_max`: max. size in MB of ae log file (def=LOG_FILE_MAX_SIZE).
        :param suppress_stdout:         pass True (for wsgi apps) for to prevent any python print outputs to stdout.
        :return:
        """
        if logging_params:
            params = logging_params.get('py_logging_params')
            if params:                     # init python logging - app is using python logging module
                logger_late_init()
                # logging.basicConfig(level=logging.DEBUG, style='{')
                logging.config.dictConfig(params)     # configure logging module
                main_instance = main_app_instance()
                if not main_instance.logging_params:
                    main_instance.logging_params = params
                self.logging_params = params
            else:                       # init ae logging
                self._log_file_max_size = logging_params.get('file_size_max', LOG_FILE_MAX_SIZE)
                #: maximum log file size in MBytes (for rotating log files)

        self.suppress_stdout = suppress_stdout
        self.startup_end = datetime.datetime.now()

    def _append_eof_and_flush_file(self, stream_file: TextIO, stream_name: str):
        """ add special end-of-file marker and flush the internal buffers to the file stream.

        :param stream_file:     file stream.
        :param stream_name:     name of the file stream.
        """
        try:
            try:
                # ALWAYS add \nEoF\n to the end
                # .. we cannot use print_out() here because of recursions on log file rotation, so use built-in print()
                # .. self.print_out()
                # .. self.print_out('EoF')
                print(file=stream_file)
                print('EoF', file=stream_file)
            except Exception as ex:
                self.po("Ignorable {} end-of-file marker exception={}".format(stream_name, ex), logger=_logger)

            stream_file.flush()

        except Exception as ex:
            self.po("Ignorable {} flush exception={}".format(stream_name, ex), logger=_logger)

    def activate_ae_logging(self):
        """ activate ae logging (not using the python logging module).
        """
        try:  # enable logging
            self._close_log_file()
            self._open_log_file()
            self.po(" ###  Activated log file", self._log_file_name, logger=_logger)
        except Exception as ex:
            self.po(" ***  AppBase._parse_args(): exception while enabling logging:", ex, logger=_logger)

    def _open_log_file(self):
        """ open the ae log file.
        """
        global app_std_out, app_std_err
        self._log_file_obj = open(self._log_file_name, "w")
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
        """ rename the log file (on rotating of the ae log file).
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
        """ close the ae log file.

        :param full_reset:  pass True to reset the standard output streams (stdout/stderr) to the defaults.
        """
        global app_std_out, app_std_err
        if self._log_file_obj:
            self._append_eof_and_flush_file(self._log_file_obj, "log file")
            app_std_err.log_file_obj = None     # prevent exception/calls of _DuplicateSysOut.log_file_obj.write()
            app_std_out.log_file_obj = None
            sys.stderr = ori_std_err  # set back for to prevent stack overflow/recursion with kivy logger
            sys.stdout = ori_std_out  # .. "Fatal Python error: Cannot recover from stack overflow"
            self._log_file_obj.close()
            self._log_file_obj = None
        elif self.logging_params:
            logging.shutdown()

        if full_reset:
            app_std_err = ori_std_err  # set back for allow full reset of log for unit tests
            app_std_out = ori_std_out

    def log_file_check_rotation(self):
        """ check if the ae log file is big enough and if yes then do a file rotation.
        """
        if self._log_file_obj is not None:
            if self.multi_threading:
                log_file_rotation_lock.acquire()
            self._log_file_obj.seek(0, 2)  # due to non-posix-compliant Windows feature
            if self._log_file_obj.tell() >= self._log_file_max_size * 1024 * 1024:
                self._close_log_file()
                self._rename_log_file()
                self._open_log_file()
            if self.multi_threading:
                log_file_rotation_lock.release()

    # noinspection PyIncorrectDocstring
    # .. not noinspection PyMissingOrEmptyDocstring
    def print_out(self, *objects, sep: str = ' ', end: str = '\n', file: Optional[TextIO] = None,
                  debug_level: int = DEBUG_LEVEL_DISABLED, **kwargs):
        """ special version of builtin print() function.

        This method has the same args as :func:`in the print_out() function of this module <ae.core.print_out>`.

        This method has an alias named :meth:`.po`
        """
        if self.sys_env_id:
            objects = ('{' + self.sys_env_id + '}', ) + objects
        po(*objects, sep=sep, end=end, file=file, debug_level=debug_level, **kwargs)

    po = print_out          #: alias of method :meth:`.print_out`

    def shutdown(self, exit_code: Optional[int] = 0, timeout: Optional[float] = None):
        """ shutdown app environment

        :param exit_code:   application OS exit code (def=0). Pass None for to not call sys.exit(exit_code).
        :param timeout:     timeout float value in seconds for thread joining (def=None - block/no-timeout).
                            Pass None for to block shutdown until all other threads have joined/finished.
        """
        self.po("####  Shutdown............  ", exit_code, timeout, logger=_logger)
        if self.multi_threading:
            with log_file_rotation_lock:
                main_thread = threading.current_thread()
                for t in threading.enumerate():
                    if t is not main_thread:
                        self.po("  **  joining thread ident <{: >6}> name={}".format(t.ident, t.getName()),
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
