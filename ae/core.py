"""
ae package core constants, helper functions and base classes
============================================================

AppBase
-------

Enable Logging
..............

.. _ae-log-file:


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
from io import StringIO
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

DEF_ENCODE_ERRORS = 'backslashreplace'      #: default encode error handling for UnicodeEncodeErrors
DEF_ENCODING: str = 'ascii'
""" core encoding that will always work independent from destination (console, file system, XMLParser, ...)."""

INI_EXT: str = '.ini'                       #: INI file extension

MAIN_SECTION_DEF: str = 'aeOptions'         #: default name of main config section

MAX_NUM_LOG_FILES: int = 69                 #: maximum number of log files
LOG_FILE_MAX_SIZE: int = 20                 #: maximum size in MB of a rotating log file

log_file_lock = threading.Lock()   #: log file rotation lock


ori_std_out = sys.stdout        #: original sys.stdout on app startup
ori_std_err = sys.stderr        #: original sys.stderr on app startup
app_std_out = ori_std_out       #: application std-out (may duplicated to :ref:`ae log file <ae-log-file>`
app_std_err = ori_std_err       #: application std-out (may duplicated to :ref:`ae log file <ae-log-file>`


# The following line is throwing an error in the Sphinx docs make:
# _app_instances: weakref.WeakValueDictionary[str, "AppBase"] = weakref.WeakValueDictionary()
_app_instances = weakref.WeakValueDictionary()   # type: weakref.WeakValueDictionary[str, AppBase]
""" dict that is weakly holding references to all :class:`AppBase` instances created at run time.

Gets automatically initialized in :meth:`AppBase.__init__` for to allow log file split/rotation
and debugLevel access at application thread or module level.

The first created :class:`AppBase` instance is called the main app instance. :data:`_main_app_inst_key`
stores the dict key of the main instance.
"""
_main_app_inst_key: str = ''    #: key in :data:`_app_instances` of main :class:`AppBase` instance


def _register_app_instance(app: 'AppBase'):
    """ register new :class:`AppBase` instance in :data:`_app_instances`.

    :param app:         :class:`AppBase` instance to register
    """
    global _main_app_inst_key
    msg = f"register_app_instance({app}) expects "
    assert app not in _app_instances.values(), msg + "new instance"

    key = app.app_name + app.sys_env_id
    assert key and key not in _app_instances, msg + f"non-empty, unique app key (app_name+sys_env_id=={key}"

    if not _main_app_inst_key:
        _main_app_inst_key = key
    _app_instances[key] = app


def main_app_instance() -> Optional['AppBase']:
    """ determine the main instance of the :class:`AppBase` in the current running application.

    :return:    main :class:`AppBase` instance or None (if app is not fully initialized yet).
    """
    return _app_instances.get(_main_app_inst_key)


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


def force_encoding(text: AnyStr, encoding: str = DEF_ENCODING, errors: str = DEF_ENCODE_ERRORS) -> str:
    """ force/ensure the encoding of text (str or bytes) without any UnicodeDecodeError/UnicodeEncodeError.

    :param text:        text as str/byte.
    :param encoding:    encoding (def=DEF_ENCODING).
    :param errors:      encode error handling (def=:data:`DEF_ENCODE_ERRORS`).

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


def stack_frames(depth: int = 1) -> Generator:  # Generator[frame, None, None]
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
        skip_modules = (__name__,)
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
    if not skip_modules:
        skip_modules = (__name__,)
    val = None
    for frame in stack_frames(depth):
        global_vars = frame.f_globals
        variables = frame.f_locals if locals_only else global_vars
        if global_vars.get('__name__') not in skip_modules and name in variables:
            val = variables[name]
            break
    return val


def to_ascii(unicode_str: str) -> str:
    """ converts unicode string into ascii representation.

    Useful for fuzzy string comparision; copied from MiniQuark's answer
    in: https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string

    :param unicode_str:     string to convert.
    :return:                converted string (replaced accents, diacritics, ... into normal ascii characters).
    """
    nfkd_form = unicodedata.normalize('NFKD', unicode_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


class AppPrintingReplicator:
    """ replace standard output/error stream for to replicate prints to all active logging streams (log files/buffers).
    """
    def __init__(self, sys_out_obj: TextIO = ori_std_out) -> None:
        """ initialise a new T-stream-object

        :param sys_out_obj:     standard output/error stream to be replicated (def=sys.stdout)
        """
        self.sys_out_obj = sys_out_obj

    def write(self, message: AnyStr) -> None:
        """ write string to logs and standard output streams.

        Automatically suppressing UnicodeEncodeErrors if console/shell or log file has different encoding
        by forcing re-encoding with DEF_ENCODE_ERRORS.

        :param message:     string to output.
        """
        streams = list()
        for app in _app_instances.values():
            if app.log_buf_stream and not app.log_buf_stream.closed:
                streams.append(app.log_buf_stream)
            elif app.log_file_stream and not app.log_file_stream.closed:
                streams.append(app.log_file_stream)
        if not self.sys_out_obj.closed:
            streams.append(self.sys_out_obj)

        for stream in streams:
            try:
                stream.write(message)
            except UnicodeEncodeError:
                stream.write(force_encoding(message, encoding=stream.encoding))

    def __getattr__(self, attr: str) -> Any:
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
              encode_errors_def: str = DEF_ENCODE_ERRORS, logger: Optional['logging.Logger'] = None,
              app_instance: Optional['AppBase'] = None, **kwargs) -> None:
    """ universal/unbreakable print function - replacement for the python print() built-in.

    This function is silently handling and auto-correcting string encode errors for output streams which are
    not supporting unicode. Any instance of :class:`AppBase` is providing this function as a method with the
    :func:`same name <AppBase.print_out>`). It is recommended to call/use the instance method instead of this function.

    :param objects:             tuple of objects to be printed.
    :param sep:                 separator character between each printed object/string (def=" ").
    :param end:                 finalizing character added to the end of this print (def="\\\\n").
                                Pass \\\\r for to suppress the print-out into :ref:`ae log file <ae-log-file>`
                                or python logger
                                - useful for console/shell processing animation (see :meth:`ae.tcp.TcpServer.run`).
    :param file:                output stream object to be printed to (def=None which will use standard output streams).
    :param flush:               flush stream after printing (def=False).
    :param encode_errors_def:   default error handling for to encode (def=:data:`DEF_ENCODE_ERRORS`).
    :param logger:              used logger for to output `objects` (def=None).
    :param app_instance:        used app environment of the passed :class:`AppBase` or :class:`~console_app.ConsoleApp`
                                instance (def=None -> use the main app instance).
    :param kwargs:              catch unsupported kwargs for debugging (all items will be printed to the output stream).

    This function has an alias named :meth:`.po`.
    """
    processing = end == "\r"
    enc = (file or ori_std_out if processing else app_std_out).encoding
    if processing:
        file = ori_std_out

    if app_instance is None:
        app_instance = main_app_instance()
    debug_level = app_instance.debug_level if app_instance else DEBUG_LEVEL_VERBOSE

    use_py_logger = False
    if app_instance and not processing:
        use_py_logger = getattr(app_instance, 'py_log_params', False) and debug_level in LOGGING_LEVELS
        if use_py_logger and logger is None:
            logger_late_init()
            module = stack_module()
            logger = logging.getLogger(module) if module else _logger
        if getattr(app_instance, 'log_file_stream', False):
            # creating new log file and backup of current one if the current has more than LOG_FILE_MAX_SIZE MB in size
            app_instance.log_file_check()

    if getattr(app_instance, 'multi_threading', False):            # add thread ident
        objects = (" <{: >6}>".format(threading.get_ident()),) + objects
    if debug_level >= DEBUG_LEVEL_TIMESTAMPED:
        objects = (datetime.datetime.now().strftime(DATE_TIME_ISO),) + objects
    if kwargs:
        objects += ("\n   *  EXTRA KWARGS={}".format(kwargs),)

    retries = 2
    while retries:
        try:
            print_strings = map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), objects)
            if use_py_logger or getattr(app_instance, 'multi_threading', False):
                # concatenating objects also prevents fluttered log file content in multi-threading apps
                # .. see https://stackoverflow.com/questions/3029816/how-do-i-get-a-thread-safe-print-in-python-2-6
                # .. and https://stackoverflow.com/questions/50551637/end-key-in-print-not-thread-safe
                print_one_str = sep.join(print_strings)
                sep = ""
                if end and not use_py_logger:
                    print_one_str += end
                    end = ""
                print_strings = (print_one_str,)

            if use_py_logger:
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

    * :attr:`_app_args`             value of sys.args at instantiation of this class.
    * :attr:`app_name`              basename (without the file name extension) of the executable.
    * :attr:`_app_path`             file path of executable.
    * :attr:`app_title`             application title/description.
    * :attr:`app_version`           application version (set via the :paramref:`AppBase.__init__.app_version` arg).
    * :attr:`debug_level`           debug level of this instance.
    * :attr:`log_buf_stream`        log file buffer stream.
    * :attr:`_log_file_index`       index of the current rotation log file backup.
    * :attr:`_log_file_max_size`    maximum size in MBytes of a log file.
    * :attr:`_log_file_name`        path and file name of the log file.
    * :attr:`log_file_stream`       log file stream (opened in :meth:~AppBase._open_log_file`, could be closed).
    * :attr:`py_log_params`         python logging config dict.
    * :attr:`multi_threading`       set to True if your application uses threads.
    * :attr:`_nul_std_out`          null stream used for to prevent printouts on stdout of the console/shell.
    * :attr:`_shut_down`            flag set to True if application shutdown was already processed.
    * :attr:`startup_beg`           datetime of begin of app instantiation/startup.
    * :attr:`startup_end`           datetime of end of app instantiation/startup.
    * :attr:`suppress_stdout`       flag set to True if application does not print to stdout/console.
    * :attr:`sys_env_id`            system environment id of this instance.
    """
    def __init__(self, app_title: str = '', app_name: str = '', app_version: str = '', sys_env_id: str = '',
                 debug_level: int = DEBUG_LEVEL_DISABLED, multi_threading: bool = False, suppress_stdout: bool = False):
        """ initialize a new :class:`AppBase` instance.

        :param app_title:               application instance title/description (def=value of main module docstring).
        :param app_name:                application instance name (def=main module file's base name).
        :param app_version:             application version (def=value of global __version__ in call stack).
        :param sys_env_id:              system environment id used as file name suffix for to load all
                                        the system config variables in sys_env<suffix>.cfg (def='', pass e.g. 'LIVE'
                                        for to init second :class:`AppBase` instance with values from sys_envLIVE.cfg).
        :param debug_level:             default debug level (def=DEBUG_LEVEL_DISABLED).
        :param multi_threading:         pass True if instance is used in multi-threading app.
        :param suppress_stdout:         pass True (for wsgi apps) for to prevent any python print outputs to stdout.
       """
        self.startup_beg: datetime.datetime = datetime.datetime.now()   #: begin of app startup datetime

        self._app_args = sys.argv                               #: initial sys.args value
        path_fnam_ext = self._app_args[0]
        app_fnam = os.path.basename(path_fnam_ext)
        self._app_path: str = os.path.dirname(path_fnam_ext)    #: path to folder of your main app code file

        if not app_title:
            app_title = stack_var('__doc__')
        if not app_name:
            app_name = os.path.splitext(app_fnam)[0]
        if not app_version:
            app_version = stack_var('__version__')

        self.app_title: str = app_title                         #: app title/description
        self.app_name: str = app_name                           #: app name
        self.app_version: str = app_version                     #: version of your app
        self.sys_env_id: str = sys_env_id                       #: system environment id of this instance
        self.debug_level: int = debug_level                     #: app default debug level
        self.multi_threading: bool = multi_threading            #: True if app uses multiple threads
        self.suppress_stdout: bool = suppress_stdout            #: flag to suppress prints to stdout

        self._nul_std_out: Optional[TextIO] = None              #: logging null stream
        self._shut_down: bool = False                           #: True if app got shut down already
        self.py_log_params: Dict[str, Any] = dict()             #: dict of config parameters for py logging
        self.startup_end: Optional[datetime.datetime] = None    #: end of app startup datetime

        self._log_file_max_size: int = LOG_FILE_MAX_SIZE        #: maximum log file size in MBytes (rotating log files)
        self._log_file_index: int = 0                           #: log file index (for rotating logs)
        self._log_file_name: str = ""                           #: log file name
        self.log_buf_stream: Optional[StringIO] = None          #: log file buffer stream instance
        self.log_file_stream: Optional[TextIO] = None           #: log file stream instance

        _register_app_instance(self)

    def init_logging(self, py_logging_params: Optional[Dict[str, Any]] = None, file_name_def: Optional[str] = "",
                     file_size_max: Optional[float] = LOG_FILE_MAX_SIZE, disable_buffering: Optional[bool] = False):
        """ prepare logging: most values will be initialized in self._parse_args() indirectly via logFile config option

        :param py_logging_params:       config dict for python logging configuration.
                                        If this dict is not empty then python logging is configured with the
                                        given options in this dict and all the other kwargs are ignored.
        :param file_name_def:           default log file name for ae logging (def='' - ae logging disabled).
        :param file_size_max:           max. size in MB of ae log file (def=LOG_FILE_MAX_SIZE).
        :param disable_buffering:       pass True to disable ae log buffering at app startup.
        """
        if py_logging_params:                     # init python logging - app is using python logging module
            logger_late_init()
            # logging.basicConfig(level=logging.DEBUG, style='{')
            logging.config.dictConfig(py_logging_params)     # configure py logging module
            main_instance = main_app_instance()
            if not main_instance.py_log_params:
                main_instance.py_log_params = py_logging_params
            self.py_log_params = py_logging_params
        else:                       # init ae logging
            self._log_file_name = file_name_def
            self._log_file_max_size = file_size_max
            if not disable_buffering:
                self.log_buf_stream = StringIO(initial_value="####  Log Buffer\n")

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
        with log_file_lock:
            try:  # enable logging
                self._close_log_file()
                self._open_log_file()
                self.po(" ###  Activated log file", self._log_file_name, logger=_logger)
            except Exception as ex:
                self.po(" ***  AppBase._parse_args(): exception while enabling logging:", ex, logger=_logger)

    def log_file_check(self):
        """ check and possibly correct log file status.

        For already opened log files check if the ae log file is big enough and if yes then do a file rotation.
        If log file is not opened but log file name got already set, then check if log startup buffer is active
        and if yes then pass log buffer content to log file and then close the log buffer.
        """
        with log_file_lock:
            if self.log_file_stream is not None:
                self.log_file_stream.seek(0, 2)  # due to non-posix-compliant Windows feature
                if self.log_file_stream.tell() >= self._log_file_max_size * 1024 * 1024:
                    self._close_log_file()
                    self._rename_log_file()
                    self._open_log_file()
            elif self.log_buf_stream and self._log_file_name:
                buf = self.log_buf_stream.getvalue()
                self.log_buf_stream.close()
                self._open_log_file()
                if self.log_file_stream:
                    self.log_buf_stream.write(buf)

    def _open_log_file(self):
        """ open the ae log file.
        """
        global app_std_out, app_std_err
        self.log_file_stream = open(self._log_file_name, "w", errors=DEF_ENCODE_ERRORS)
        if app_std_out == ori_std_out:      # first call/open-of-log-file?
            if self.suppress_stdout:
                std_out = self._nul_std_out = open(os.devnull, 'w')
            else:
                std_out = ori_std_out
            app_std_out = sys.stdout = AppPrintingReplicator(sys_out_obj=std_out)
            app_std_err = sys.stderr = AppPrintingReplicator(sys_out_obj=ori_std_err)
        else:
            app_std_out.log_file_stream = self.log_file_stream
            app_std_err.log_file_stream = self.log_file_stream

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
        if self.log_file_stream:
            stream = self.log_file_stream
            self._append_eof_and_flush_file(stream, "log file")
            self.log_file_stream = None     # prevent exception/calls of AppPrintingReplicator.log_file_stream.write()
            sys.stderr = ori_std_err        # set back for to prevent stack overflow/recursion with kivy logger
            sys.stdout = ori_std_out        # .. "Fatal Python error: Cannot recover from stack overflow"
            stream.close()
        elif self.py_log_params:
            logging.shutdown()

        if full_reset:
            app_std_err = ori_std_err  # set back for allow full reset of log for unit tests
            app_std_out = ori_std_out

    # noinspection PyIncorrectDocstring
    def print_out(self, *objects, **kwargs):
        """ special version of builtin print() function.

        This method has the same args as :func:`in the print_out() function of this module <.print_out>`.

        This method has an alias named :meth:`.po`
        """
        if self.sys_env_id:
            objects = ('{' + self.sys_env_id + '}', ) + objects
        po(*objects, **kwargs)

    po = print_out          #: alias of method :meth:`.print_out`

    def shutdown(self, exit_code: Optional[int] = 0, timeout: Optional[float] = None):
        """ shutdown app environment

        :param exit_code:   application OS exit code (def=0). Pass None for to not call sys.exit(exit_code).
        :param timeout:     timeout float value in seconds for thread joining (def=None - block/no-timeout).
                            Pass None for to block shutdown until all other threads have joined/finished.
        """
        self.po("####  Shutdown............  ", exit_code, timeout, logger=_logger)
        with log_file_lock:
            if self.multi_threading:
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
