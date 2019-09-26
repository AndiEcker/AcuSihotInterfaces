"""
ae package core constants, helper functions and base classes
============================================================

This module declares practical constants, base classes as well as tiny helper functions
making the code of your application (and other modules of this package) much cleaner.

Constants
---------

For to set the debug level of your application run-time you can use one of the constants
:data:`DEBUG_LEVEL_DISABLED`, :data:`DEBUG_LEVEL_ENABLED`, :data:`DEBUG_LEVEL_VERBOSE`
or :data:`DEBUG_LEVEL_TIMESTAMPED`. The debug level of your application can be either
hard-coded in your code or optionally also externally (using the :ref:`config-files`
or :ref:`config-options` of the module :mod:`ae.console`).

Short names for all debug level constants are provided by the dict :data:`DEBUG_LEVELS`.

For to use the :mod:`python logging module <logging>` in conjunction with this module
the constant :data:`LOGGING_LEVELS` is providing a mapping between the debug levels
and the python logging levels.

Standard ISO format strings for date and datetime values are provided by the constants
:data:`DATE_ISO` and :data:`DATE_TIME_ISO`.

The encoding of strings into byte-strings (for to output them to the console/stdout or
to file contents) can be tricky sometimes. For to not lose any logging output because
of invalid characters this module will automatically handle any :exc:`UnicodeEncodeError`
exception for you. Invalid characters will in case of this error be converted
to the default encoding (specified by :data:`DEF_ENCODING`) with the default error
handling method specified by :data:`DEF_ENCODE_ERRORS`.


Helper Functions
----------------

Although most of the helper functions provided by this module are tiny with only few lines
of code, they are a great help in making your application code more clear and readable.

For the dynamic execution of functions and code blocks the helper functions :func:`try_call`,
:func:`try_exec` and :func:`exec_with_return` are provided. And :func:`try_eval` is making
the evaluation of dynamic python expressions much easier. These functions are e.g. used
by the :class:`~ae.literal.Literal` class for the implementation of dynamically
determined literal values.

The functions :data:`module_name`, :func:`stack_frames` and :func:`stack_variable` are very
helpful for to inspect the call stack. With them you can easily access the stack frame
and read e.g. variable values of the callers of your functions/methods. The class
:class:`~ae.console.ConsoleApp` is using them e.g. for to determine the
:ref:`version <app-version>` and :ref:`title <app-title>` of your application.

Other helper functions for the inspection and debugging of your application are
:func:`full_stack_trace`, :func:`sys_env_dict` and :func:`sys_env_text`.

The :func:`parse_date` helper function is converting date and datetime string literals into the
built-in types :class:`datetime.datetime` and :class:`datetime.date`.

Two of the bigger helper functions are :func:`correct_email` and :func:`correct_phone`,
which are useful for to check if a string contains a valid email address or phone number. They
also allow you to automatically correct an email address or a phone number to a valid format.
More sophisticated helpers for the validation of email addresses, phone numbers and
post addresses are available in the :mod:`ae.validation` module.

For to encode unicode strings to other codecs the functions :func:`force_encoding` and
:func:`to_ascii` can be used. The :func:`print_out` function, which is fully compatible to pythons
:func:`print`, is using these encode helpers for to auto-correct invalid characters.

:func:`hide_dup_line_prefix` is very practical if you want to remove or hide redundant
line prefixes in your log files, to make them better readable.

Finally the :func:`round_traditional` get declared in this module fully compatible to
Python's :func:`round` function, to be used for traditional rounding of float values.


Application Base Class
----------------------

The base class :class:`AppBase` is providing sophisticated logging features with the help of the
function :func:`print_out` and their sub-class :class:`_PrintingReplicator`.

The first created instance of :class:`AppBase` in your application is representing the main app
and any further created instances are representing the sub-apps of your application.

Sub-apps are not tied to any fix use-case. They can be created for example for each sub-task or
application thread. You could also create a sub-app instance for each of your external systems,
like a database server or for to connect your application onto different test environments
or to your live/production system.

:class:`AppBase` ensures automatically for you the proper handling of any exceptions and run-time
errors: if any critical exception/error cannot be handled then the :meth:`~AppBase.shutdown`
will make sure that all sub-apps and threads get terminated and joined.
Additionally it will flush all print-out buffers for to include all the info
of the critical error (the last debug and error messages) into the
standard error/output and any active log files.


Application Class Hierarchy
...........................

For most use cases you will never need to instantiate from :class:`AppBase` directly - instead you will
instantiate one of the classes that are inherited from this base class.

The class :class:`~ae.console.ConsoleApp` e.g. inherits from :class:`AppBase` and is adding
configuration options and variables to it. So in your console application it is recommended to directly
use instances of :class:`~ae.console.ConsoleApp` instead of :class:`AppBase`.

For applications with an GUI use instead one of the classes :class:`~ae.kivy_app.KivyApp`,
:class:`~ae.enaml_app.EnamlApp` or :class:`~ae.dabo_app.DaboApp`. These app GUI classes
inherit all functionality from :class:`~ae.console.ConsoleApp` and :class:`AppBase`.


Application Logging
-------------------

Print-outs are an essential tool for the debugging and logging of your application at run-time. In python
the print-outs are done with the :func:`print` function or the python :mod:`logging` module. These
print-outs get per default send to the standard output and error streams of your OS and so displayed on
your system console/shell. The :func:`print_out` function and the :meth:`~AppBase.print_out` method of
this :mod:`.core` module are adding two more sophisticated ways for print-outs to the console/log-files.

Using :class:`AppBase` is making the logging much easier and also ensures that print-outs of any
imported library or package will be included within your log files. This is done by redirecting the
standard output and error streams to your log files with the help of the :class:`_PrintingReplicator`
class.

Head-less server applications like web servers are mostly not allowed to use the standard output streams.
For some these applications you could redirect the standard output and error streams to a log file by
using the OS redirection character (>)::

    python your_application.py >log_std_out.log 2>log_std_err.log

But because most web servers doesn't allow you to use this redirection, you can alternatively specify
the :paramref:`~AppBase.suppress_stdout` parameter as True in the instantiation of an :class:`AppBase`
instance. Additionally you can call the :meth:`~AppBase.init_logging` method for to activate a log file.
After that all print-outs of your application and libraries will only appear in your log file.

Also in complex applications, where huge print-outs to the console can get lost easily, you want to use
a log file instead. But even a single log file can get messy to read, especially for multi-threaded
server applications. For that :mod:`.core` is allowing you to create for each thread a separate
sub-application :class:`AppBase` instance with its own log file.


Enable Ae Log File
..................

.. _ae-log-file:

Ae Log Files are text files using by default the encoding of your OS console/shell. To activate the
redirection of your applications print-outs into a ae log file for a :class:`AppBase` instance you
simply specify the file name of the log file in the :meth:`~AppBase.init_logging` method call::

    app = AppBase()
    app.init_logging(log_file_name='my_log_file.log')


Enable Ae Logging Features
..........................

For multi-threaded applications you can include the thread-id of the printing thread automatically
into your log files. For that you have to pass a True value to the
:paramref:`~AppBase.multi_threading` argument. For to additionally also suppress any print-outs
to the standard output/error streams pass True to the :paramref:`~AppBase.suppress_stdout` argument::

    app = AppBase(multi_threading=True, suppress_stdout=True)
    app.init_logging(log_file_name='my_log_file.log')

The ae log files provided by this module are automatically rotating if the size of an log file
succeeds the value in MBytes defined in the :data:`LOG_FILE_MAX_SIZE`. For to adapt this value
to your needs you can specify the maximum log file size in MBytes with the argument
:paramref:`~AppBase.init_logging.log_file_size_max` in your call of :meth:`~AppBase.init_logging`::

    app.init_logging(log_file_name='my_log_file.log', log_file_size_max=9.)

By using the :class:`~ae.console.ConsoleApp` class instead of :class:`AppBase` you can
alternatively store the logging configuration of your application within a
:ref:`configuration variable <config-variables>` or a :ref:`configuration option <config-options>`.
The order of precedence for to find the appropriate logging configuration of each
app instance is documented :meth:`here <ae.console.ConsoleApp._init_logging>` .


Using Python Logging Module
...........................

If you prefer to use instead the python logging module for the print-outs of your application,
then pass a :mod:`python logging configuration dictionary <logging.config>` with the individual
configuration of your logging handlers, files and loggers to the
:paramref:`~AppBase.init_logging.py_logging_params` argument of the
:meth:`~AppBase.init_logging` method::

    app.init_logging(py_logging_params=my_py_logging_config_dict)

Passing the python logging configuration dictionary to one of the :class:`AppBase`
instances created by your application will automatically disable the ae log file of this
instance.


Application Debugging
---------------------

For to use the debug features of :mod:`~ae.core` you simple have to import the needed
:ref:`debug level constants <debug-level-constants>`.


"""
import ast
import copy
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
from typing import Any, AnyStr, Callable, Generator, Dict, Optional, TextIO, Tuple, Union

DATE_TIME_ISO: str = '%Y-%m-%d %H:%M:%S.%f'     #: ISO string format for datetime values in config files/variables
DATE_ISO: str = '%Y-%m-%d'                      #: ISO string format for date values in config files/variables

DEF_ENCODE_ERRORS: str = 'backslashreplace'     #: default encode error handling for UnicodeEncodeErrors
DEF_ENCODING: str = 'ascii'
""" core encoding that will always work independent from destination (console, file system, XMLParser, ...)."""

DEBUG_LEVELS: Dict[int, str] = {0: 'disabled', 1: 'enabled', 2: 'verbose', 3: 'timestamped'}
""" numeric ids and names of all supported debug levels

.. _debug-level-constants:

"""
# DON'T RE-ORDER - using DEBUG_LEVELS doc-string as sphinx hyperlink label to the DEBUG_ constants underneath #
DEBUG_LEVEL_DISABLED: int = 0       #: lowest debug level - only display logging levels ERROR/CRITICAL.
DEBUG_LEVEL_ENABLED: int = 1        #: minimum debugging info - display logging levels WARNING or higher.
DEBUG_LEVEL_VERBOSE: int = 2        #: verbose debug info - display logging levels INFO/DEBUG or higher.
DEBUG_LEVEL_TIMESTAMPED: int = 3    #: highest/verbose debug info - including timestamps in the log output.

LOGGING_LEVELS: Dict[int, int] = {DEBUG_LEVEL_DISABLED: logging.ERROR, DEBUG_LEVEL_ENABLED: logging.WARNING,
                                  DEBUG_LEVEL_VERBOSE: logging.INFO, DEBUG_LEVEL_TIMESTAMPED: logging.DEBUG}
""" association between ae debug levels and python logging levels.
"""


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


def exec_with_return(code_block, glo_vars: Optional[dict] = None, loc_vars: Optional[dict] = None):
    """ execute python code block and return the resulting value of its last code line.

    Inspired by this SO answer
    https://stackoverflow.com/questions/33409207/how-to-return-value-from-exec-in-function/52361938#52361938.

    :param code_block:      python code block to execute.
    :param glo_vars:        optional globals() available in the code execution.
    :param loc_vars:        optional locals() available in the code execution.
    :return:                value of the expression at the last code line or None if last code line is no expression.
    """
    def convert_expr(expr):
        expr.lineno = 0
        expr.col_offset = 0
        result = ast.Expression(expr.value, lineno=0, col_offset=0)

        return result

    if glo_vars is None:
        glo_vars = globals()
    if loc_vars is None:
        loc_vars = locals()

    code_ast = ast.parse(code_block)

    init_ast = copy.deepcopy(code_ast)
    init_ast.body = code_ast.body[:-1]

    last_ast = copy.deepcopy(code_ast)
    last_ast.body = code_ast.body[-1:]

    exec(compile(init_ast, "<ast>", "exec"), glo_vars, loc_vars)
    last_line = last_ast.body[0]
    if type(last_line) != ast.Expr:
        exec(compile(last_ast, "<ast>", "exec"), glo_vars, loc_vars)
    else:
        return eval(compile(convert_expr(last_line), "<ast>", "eval"), glo_vars, loc_vars)


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


def hide_dup_line_prefix(last_line: str, current_line: str) -> str:
    """ replace duplicate characters at the begin of two strings with spaces.

    :param last_line:       last line string (e.g. the last line of text/log file).
    :param current_line:    current line string.
    :return:                current line string but duplicate characters at the begin are replaced by space characters.
    """
    idx = 0
    min_len = min(len(last_line), len(current_line))
    while idx < min_len and last_line[idx] == current_line[idx]:
        idx += 1
    return " " * idx + current_line[idx:]


def module_name(*skip_modules: str, depth: int = 1) -> Optional[str]:
    """ find the first module in the call stack that is *not* in :paramref:`module_name.skip_modules`.

    :param skip_modules:    module names to skip (def=this ae.core module).
    :param depth:           the calling level from which on to search (def=1 which refers the next deeper frame).
                            Pass 2 or a even higher value if you want to get the module name from a deeper level
                            in the call stack.
    :return:                The module name of the call stack level specified in the :paramref:`~module_name.depth`
                            argument.
    """
    if not skip_modules:
        skip_modules = (__name__,)
    return stack_var('__name__', *skip_modules, depth=depth)


def parse_date(literal: str, *additional_formats: str, replace: Optional[Dict[str, Any]] = None,
               ret_date: Optional[bool] = False,
               dt_seps: Tuple[str, ...] = ('T', ' '), ti_sep: str = ':', ms_sep: str = '.', tz_sep: str = '+',
               ) -> Optional[Union[datetime.date, datetime.datetime]]:
    """ parse a date literal string, returning the represented date/datetime or None if date literal is invalid.

    :param literal:             date literal string in the format of :data:`DATE_ISO`, :data:`DATE_TIME_ISO` or in
                                one of the additional formats passed into the
                                :paramref:`parse_date.additional_formats` arguments tuple.
    :param additional_formats:  additional date literal format string masks (supported mask characters are documented
                                at the `format` argument of the python method :meth:`~datetime.datetime.strptime`).
    :param replace:             dict of replace keyword arguments for :meth:`datetime.datetime.replace` call.
                                Pass e.g. dict(microsecond=0, tzinfo=None) for to set the microseconds of the
                                resulting date to zero and for to remove the timezone info.
    :param ret_date:            request return value type: True=datetime.date, False=datetime.datetime (def)
                                or None=determine type from literal (short date if dt_seps are not in literal).
    :param dt_seps:             tuple of supported separator characters between the date and time literal parts.
    :param ti_sep:              separator character of the time parts (hours/minutes/seconds) in literal.
    :param ms_sep:              microseconds separator character.
    :param tz_sep:              time-zone separator character.
    :return:                    represented date/datetime or None if date literal is invalid.

    This function can not only fully replace the python method :meth:`~datetime.datetime.strptime`. On top
    it supports multiple date formats which are much more flexible used/interpreted.
    """
    lp_tz_sep = literal.rfind(tz_sep)
    lp_ms_sep = literal.rfind(ms_sep)
    lp_dt_sep = max((literal.find(_) for _ in dt_seps))
    if ret_date and lp_dt_sep != -1:
        literal = literal[:lp_dt_sep]       # cut time part if exists caller requested return of short date
        l_dt_sep = None
        l_time_sep_cnt = 0
    else:
        l_dt_sep = literal[lp_dt_sep] if lp_dt_sep != -1 else None
        l_time_sep_cnt = literal.count(ti_sep)
        if not (0 <= l_time_sep_cnt <= 2):
            return None

    if l_dt_sep:
        additional_formats += (DATE_TIME_ISO,)
    additional_formats += (DATE_ISO,)

    for mask in additional_formats:
        mp_dt_sep = max((mask.find(_) for _ in dt_seps))
        m_time_sep_cnt = mask.count(ti_sep)
        if lp_tz_sep == -1 and mask[-3] == tz_sep:
            mask = mask[:-3]                    # no timezone specified in literal, then remove '+%z' from mask
        if lp_ms_sep == -1 and mask.rfind(ms_sep) != -1:
            mask = mask[:mask.rfind(ms_sep)]    # no microseconds specified in literal, then remove '.%f' from mask
        if 1 <= l_time_sep_cnt < m_time_sep_cnt:
            mask = mask[:mask.rfind(ti_sep)]    # no seconds specified in literal, then remove ':%S' from mask
        if mp_dt_sep != -1:
            if l_dt_sep:
                m_dt_sep = mask[mp_dt_sep]
                if l_dt_sep != m_dt_sep:        # if literal uses different date-time-sep
                    mask = mask.replace(m_dt_sep, l_dt_sep)     # .. then replace in mask
            else:
                mask = mask[:mp_dt_sep]         # if no date-time-sep in literal, then remove time part from mask

        ret_val = try_call(datetime.datetime.strptime, literal, mask, ignored_exceptions=(ValueError, ))
        if ret_val is not None:
            if replace:
                ret_val = ret_val.replace(**replace)
            if ret_date or ret_date is None and l_dt_sep is None:
                ret_val = ret_val.date()
            return ret_val


def round_traditional(num_value: float, num_digits: int = 0) -> float:
    """ round numeric value traditional.

    Needed because python round() is working differently, e.g. round(0.075, 2) == 0.07 instead of 0.08
    inspired by https://stackoverflow.com/questions/31818050/python-2-7-round-number-to-nearest-integer.

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
    """ generator diving deeper into the call stack from the level given in :paramref:`~stack_frames.depth`.

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


def stack_variable(name: str, *skip_modules: str, depth: int = 1, locals_only: bool = False) -> Optional[Any]:
    """ determine variable value in calling stack/frames.

    :param name:            variable name.
    :param skip_modules:    module names to skip (def=this ae.core module).
    :param depth:           the calling level from which on to search (def=1 which refers the next deeper stack frame).
                            Pass 2 or a even higher value if you want to get the variable value from a deeper level
                            in the call stack.
    :param locals_only:     pass True to only check for local variables (ignoring globals).
    :return:                The variable value of a deeper level within the call stack.

    This function has an alias named :func:`.stack_var`.
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


stack_var = stack_variable          #: alias of function :func:`.stack_variable`


def to_ascii(unicode_str: str) -> str:
    """ converts unicode string into ascii representation.

    Useful for fuzzy string comparision; inspired by MiniQuark's answer
    in: https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string

    :param unicode_str:     string to convert.
    :return:                converted string (replaced accents, diacritics, ... into normal ascii characters).
    """
    nfkd_form = unicodedata.normalize('NFKD', unicode_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


def try_call(func: Callable, *args, ignored_exceptions: Optional[tuple] = (), **kwargs) -> Any:
    """ call function ignoring specified exceptions and return function return value.

    :param func:                function to be called.
    :param args:                function arguments tuple.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param kwargs:              function keyword arguments dict.
    :return:                    function return value or None if a ignored exception got thrown.
    """
    ret = None
    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
        ret = func(*args, **kwargs)
    except ignored_exceptions:
        pass
    return ret


def try_eval(expr: str, ignored_exceptions: Optional[tuple] = (),
             glo_vars: Optional[dict] = None, loc_vars: Optional[dict] = None) -> Any:
    """ evaluate expression string ignoring specified exceptions and return evaluated value.

    :param expr:                expression to evaluate.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the expression evaluation.
    :param loc_vars:            optional locals() available in the expression evaluation.
    :return:                    function return value or None if a ignored exception got thrown.
    """
    ret = None

    if glo_vars is None:
        glo_vars = globals()
    if loc_vars is None:
        loc_vars = locals()

    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
        ret = eval(expr, glo_vars, loc_vars)
    except ignored_exceptions:
        pass
    return ret


def try_exec(code_block: str, ignored_exceptions: Optional[tuple] = (),
             glo_vars: Optional[dict] = None, loc_vars: Optional[dict] = None) -> Any:
    """ execute python code block string ignoring specified exceptions and return value of last code line in block.

    :param code_block:          python code block to be executed.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the code execution.
    :param loc_vars:            optional locals() available in the code execution.
    :return:                    function return value or None if a ignored exception got thrown.
    """
    ret = None

    if glo_vars is None:
        glo_vars = globals()
    if loc_vars is None:
        loc_vars = locals()

    try:
        ret = exec_with_return(code_block, glo_vars=glo_vars, loc_vars=loc_vars)
    except ignored_exceptions:
        pass
    return ret


MAX_NUM_LOG_FILES: int = 69                         #: maximum number of :ref:`ae log files <ae-log-file>`
LOG_FILE_MAX_SIZE: int = 15                         #: max. size in MB of rotating :ref:`ae log files <ae-log-file>`
LOG_FILE_IDX_WIDTH: int = len(str(MAX_NUM_LOG_FILES)) + 3
""" width of rotating log file index within log file name; adding +3 to ensure index range up to factor 10^3. """

ori_std_out: TextIO = sys.stdout                    #: original sys.stdout on app startup
ori_std_err: TextIO = sys.stderr                    #: original sys.stderr on app startup

log_file_lock: threading.RLock = threading.RLock()  #: log file rotation multi-threading lock


_logger = None       #: python logger for this module gets lazy/late initialized and only if requested by caller


def logger_late_init():
    """ check if logging modules got initialized already and if not then do it now. """
    global _logger
    if not _logger:
        _logger = logging.getLogger(__name__)


_multi_threading_activated: bool = False            #: flag if threading is used in your application


def activate_multi_threading():
    """ activate multi-threading for all app instances (normally done at main app startup). """
    global _multi_threading_activated
    _multi_threading_activated = True


def _deactivate_multi_threading():
    """ disable multi threading (needed for to reset app environment in unit testing). """
    global _multi_threading_activated
    _multi_threading_activated = False


def print_out(*objects, sep: str = " ", end: str = "\n", file: Optional[TextIO] = None, flush: bool = False,
              encode_errors_def: str = DEF_ENCODE_ERRORS, logger: Optional['logging.Logger'] = None,
              app: Optional['AppBase'] = None, **kwargs) -> None:
    """ universal/unbreakable print function - replacement for the :func:`built-in python function print() <print>`.

    :param objects:             tuple of objects to be printed.
    :param sep:                 separator character between each printed object/string (def=" ").
    :param end:                 finalizing character added to the end of this print-out (def="\\\\n").
                                Pass \\\\r for to suppress the print-out into :ref:`ae log file <ae-log-file>`
                                or to any activated python logger
                                - useful for console/shell processing animation (see :meth:`ae.tcp.TcpServer.run`).
    :param file:                output stream object to be printed to (def=None which will use standard output streams).
                                If given then the redirection to all active log files and python logging loggers
                                will be disabled (even if the :paramref:`~print_out.logger` argument is specified).
    :param flush:               flush stream after printing (def=False).
    :param encode_errors_def:   default error handling for to encode (def=:data:`DEF_ENCODE_ERRORS`).
    :param logger:              used logger for to output `objects` (def=None). Ignored if the
                                :paramref:`print_out.file` argument gets specified/passed.
    :param app:                 the app instance from where this print-out got initiated.
    :param kwargs:              catch unsupported kwargs for debugging (all items will be printed to the output stream).

    This function is silently handling and auto-correcting string encode errors for output streams which are
    not supporting unicode. Any instance of :class:`AppBase` is providing this function as a method with the
    :func:`same name <AppBase.print_out>`). It is recommended to call/use the instance method instead of this function.

    In multi-threaded applications this function prevents dismembered/fluttered print-outs from different threads.

    This function has an alias named :func:`.po`.
    """
    processing = end == "\r"
    enc = (file or ori_std_out if processing else sys.stdout).encoding
    use_py_logger = False

    main_app = main_app_instance()
    if main_app:
        main_app.log_file_check()       # check if late init of logging system is needed
    if app:
        app.log_file_check()            # check suppress_stdout/log file status and rotation
    else:
        app = main_app

    if processing:
        file = ori_std_out
    elif logger is not None and file is None and (app.py_log_params and main_app != app or main_app.py_log_params):
        use_py_logger = True
        logger_late_init()

    if kwargs:
        objects += ("\n   *  EXTRA KWARGS={}".format(kwargs),)

    retries = 2
    while retries:
        try:
            print_strings = map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), objects)
            if use_py_logger or _multi_threading_activated:
                # concatenating objects also prevents fluttered log file content in multi-threading apps
                # .. see https://stackoverflow.com/questions/3029816/how-do-i-get-a-thread-safe-print-in-python-2-6
                # .. and https://stackoverflow.com/questions/50551637/end-key-in-print-not-thread-safe
                print_one_str = sep.join(print_strings)
                sep = ""
                if end and (not use_py_logger or end != '\n'):
                    print_one_str += end
                    end = ""
                print_strings = (print_one_str,)

            if use_py_logger:
                debug_level = app.debug_level if app else DEBUG_LEVEL_VERBOSE
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


APP_KEY_SEP: str = '@'      #: separator character used in :attr:`~AppBase.app_key` of :class:`AppBase` instance

# Had to use type comment because the following line is throwing an error in the Sphinx docs make:
# _app_instances: weakref.WeakValueDictionary[str, "AppBase"] = weakref.WeakValueDictionary()
_app_instances = weakref.WeakValueDictionary()   # type: weakref.WeakValueDictionary[str, AppBase]
""" dict that is weakly holding references to all :class:`AppBase` instances created at run time.

Gets automatically initialized in :meth:`AppBase.__init__` for to allow log file split/rotation
and debugLevel access at application thread or module level.

The first created :class:`AppBase` instance is called the main app instance. :data:`_main_app_inst_key`
stores the dict key of the main instance.
"""
_main_app_inst_key: str = ''    #: key in :data:`_app_instances` of main :class:`AppBase` instance

app_inst_lock: threading.RLock = threading.RLock()  #: app instantiation multi-threading lock


def main_app_instance() -> Optional['AppBase']:
    """ determine the main instance of the :class:`AppBase` in the current running application.

    :return:    main/first-instantiated :class:`AppBase` instance or None (if app is not fully initialized yet).
    """
    with app_inst_lock:
        return _app_instances.get(_main_app_inst_key)


def _register_app_instance(app: 'AppBase'):
    """ register new :class:`AppBase` instance in :data:`_app_instances`.

    :param app:         :class:`AppBase` instance to register
    """
    with app_inst_lock:
        global _app_instances, _main_app_inst_key
        msg = f"register_app_instance({app}) expects "
        assert app not in _app_instances.values(), msg + "new instance - this app got already registered"

        key = app.app_key
        assert key and key not in _app_instances, \
            msg + f"non-empty, unique app key (app_name+sys_env_id=={key} keys={list(_app_instances.keys())})"

        cnt = len(_app_instances)
        if _main_app_inst_key:
            assert cnt > 0, f"No app instances registered but main app key is set to {_main_app_inst_key}"
        else:
            assert cnt == 0, f"{cnt} sub-apps {list(_app_instances.keys())} found after main app remove"
            _main_app_inst_key = key
        _app_instances[key] = app


def _unregister_app_instance(app_key: str) -> 'AppBase':
    """ unregister/remove :class:`AppBase` instance from within :data:`_app_instances`.

    :param app_key:     app key of the instance to remove.
    :return:            removed :class:`AppBase` instance.
    """
    with app_inst_lock:
        global _app_instances, _main_app_inst_key
        app = _app_instances.pop(app_key, None)
        cnt = len(_app_instances)
        if app_key == _main_app_inst_key:
            _main_app_inst_key = ''
            assert cnt == 0, f"{cnt} sub-apps {list(_app_instances.keys())} found after main app {app_key}{app} remove"
        else:
            assert cnt > 0, f"Unregistered last app {app_key} but was not the main app {_main_app_inst_key}"
        return app


def _shut_down_sub_app_instances(timeout: Optional[float] = None):
    """ shut down all sub-app instances.

    :param timeout:     timeout float value in seconds used for the sub-app shutdowns and for the acquisition of the
                        threading locks of :data:`the ae log file <log_file_lock>` and the :data:`app instances
                        <app_inst_lock>`.
    """
    blocked = app_inst_lock.acquire(**(dict(blocking=False) if timeout is None else dict(timeout=timeout)))
    main_app = main_app_instance()
    for app in list(_app_instances.values()):   # list is needed because weak ref dict get changed in loop
        if app is not main_app:
            app.shutdown(timeout=timeout)
    if blocked:
        app_inst_lock.release()


class _PrintingReplicator:
    """ replacement of standard/error stream for to replicate print-outs to all active logging streams (log files/bufs).
    """
    def __init__(self, sys_out_obj: TextIO = ori_std_out) -> None:
        """ initialise a new T-stream-object

        :param sys_out_obj:     standard output/error stream to be replicated (def=sys.stdout)
        """
        self.sys_out_obj = sys_out_obj

    def write(self, message: AnyStr) -> None:
        """ write string to ae logging and standard output streams.

        Automatically suppressing UnicodeEncodeErrors if console/shell or log file has different encoding
        by forcing re-encoding with DEF_ENCODE_ERRORS.

        :param message:     string to output.
        """
        app_streams = list()
        with log_file_lock, app_inst_lock:
            for app in list(_app_instances.values()):
                # noinspection PyProtectedMember
                if app._log_buf_stream and not app._log_buf_stream.closed:
                    # noinspection PyProtectedMember
                    app_streams.append((app, app._log_buf_stream))
                elif app._log_file_stream and not app._log_file_stream.closed:
                    app.log_file_check()  # check log file rotation (if yes then switch to new app._log_file_stream)
                    # noinspection PyProtectedMember
                    app_streams.append((app, app._log_file_stream))
            if not self.sys_out_obj.closed:
                app_streams.append((main_app_instance(), self.sys_out_obj))

        log_lines = message.split('\n')
        for app, stream in app_streams:
            line_prefix = '\n' + (app.log_line_prefix() if app else '')
            app_msg = line_prefix.join(log_lines)
            try:
                stream.write(app_msg)
            except UnicodeEncodeError:
                stream.write(force_encoding(app_msg, encoding=stream.encoding))

    def __getattr__(self, attr: str) -> Any:
        """ get attribute value from standard output stream.

        :param attr:    name of the attribute to retrieve/return.
        :return:        value of the attribute.
        """
        return getattr(self.sys_out_obj, attr)


_app_threads = weakref.WeakValueDictionary()   # type: weakref.WeakValueDictionary[int, threading.Thread]
""" weak dict for to keep the references of all application threads. Added for to prevent
the joining of unit testing threads in the test teardown (resetting app environment). """


def _register_app_thread():
    """ add new app thread to _app_threads if not already added. """
    global _app_threads
    tid = threading.get_ident()
    if tid not in _app_threads:
        _app_threads[tid] = threading.current_thread()


def _join_app_threads(timeout: Optional[float] = None):
    """ join/finish all app threads and finally deactivate multi-threading.

    :param timeout:     timeout float value in seconds for thread joining (def=None - block/no-timeout).
    """
    global _app_threads
    main_thread = threading.current_thread()
    for t in list(_app_threads.values()):     # threading.enumerate() also includes PyCharm/pytest threads
        if t is not main_thread:
            po("  **  joining thread ident <{: >6}> name={}".format(t.ident, t.getName()), logger=_logger)
            t.join(timeout)
            _app_threads.pop(t.ident)
    _deactivate_multi_threading()


class AppBase:
    """ provides easy logging and debugging for your application.

    Most applications only need a single instance of this class; apps with threads could create separate instances
    for each thread.

    Instance Attributes (ordered alphabetically - ignoring underscore characters):

    * :attr:`_app_args`             value of sys.args at instantiation of this class.
    * :attr:`app_key`               id/key of this application instance.
    * :attr:`app_name`              basename (without the file name extension) of the executable.
    * :attr:`_app_path`             file path of executable.
    * :attr:`app_title`             application title/description.
    * :attr:`app_version`           application version (set via the :paramref:`AppBase.app_version` argument).
    * :attr:`debug_level`           debug level of this instance.
    * :attr:`_last_log_line_prefix` last ae log file line prefix that got print-out to the log of this app instance.
    * :attr:`_log_buf_stream`       ae log file buffer stream.
    * :attr:`_log_file_index`       index of the current rotation ae log file backup.
    * :attr:`_log_file_name`        path and file name of the ae log file.
    * :attr:`_log_file_size_max`    maximum size in MBytes of a ae log file.
    * :attr:`_log_file_stream`      ae log file TextIO output stream.
    * :attr:`py_log_params`         python logging config dictionary.
    * :attr:`_nul_std_out`          null stream used for to prevent print-outs to :attr:`standard output <sys.stdout>`.
    * :attr:`_shut_down`            flag set to True if this application instance got already shutdown.
    * :attr:`startup_beg`           datetime of begin of the instantiation/startup of this app instance.
    * :attr:`startup_end`           datetime of end of the instantiation/startup of this application instance.
    * :attr:`suppress_stdout`       flag set to True if this application does not print to stdout/console.
    * :attr:`sys_env_id`            system environment id of this application instance.
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
        :param debug_level:             default debug level (def=:data:`DEBUG_LEVEL_DISABLED`).
        :param multi_threading:         pass True if instance is used in multi-threading app.
        :param suppress_stdout:         pass True (for wsgi apps) for to prevent any python print outputs to stdout.
       """
        self.startup_beg: datetime.datetime = \
            datetime.datetime.now()                             #: begin of app startup datetime

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

        self.app_title: str = app_title                         #: title/description of this app instance
        self.app_name: str = app_name                           #: name of this app instance
        self.app_version: str = app_version                     #: version of your app instance
        self.sys_env_id: str = sys_env_id                       #: system environment id of this instance
        self.debug_level: int = debug_level                     #: debug level of this app instance
        if multi_threading:
            activate_multi_threading()
        self.suppress_stdout: bool = suppress_stdout            #: flag to suppress prints to stdout

        with log_file_lock:
            self._last_log_line_prefix: str = ""                #: prefix of the last printed log line
            self._log_buf_stream: Optional[StringIO] = None     #: log file buffer stream instance
            self._log_file_stream: Optional[TextIO] = None      #: log file stream instance
            self._log_file_index: int = 0                       #: log file index (for rotating logs)
            self._log_file_size_max: int = LOG_FILE_MAX_SIZE    #: maximum log file size in MBytes (rotating log files)
            self._log_file_name: str = ""                       #: log file name
            self._nul_std_out: Optional[TextIO] = None          #: logging null stream
            self.py_log_params: Dict[str, Any] = dict()         #: dict of config parameters for py logging

        self._shut_down: bool = False                           #: True if this app instance got shut down already
        self.startup_end: Optional[datetime.datetime] = None    #: end datetime of the application startup

        _register_app_thread()
        _register_app_instance(self)

    def __del__(self):
        """ deallocate this app instance by calling :func:`AppBase.shutdown`.
        """
        self.shutdown(exit_code=None)

    @property
    def app_key(self):
        return self.app_name + APP_KEY_SEP + self.sys_env_id

    def init_logging(self, py_logging_params: Optional[Dict[str, Any]] = None, log_file_name: str = "",
                     log_file_size_max: float = LOG_FILE_MAX_SIZE, disable_buffering: bool = False):
        """ prepare logging: most values will be initialized in self._parse_args() indirectly via logFile config option

        :param py_logging_params:       config dict for python logging configuration.
                                        If this dict is not empty then python logging is configured with the
                                        given options in this dict and all the other kwargs are ignored.
        :param log_file_name:           default log file name for ae logging (def='' - ae logging disabled).
        :param log_file_size_max:       max. size in MB of ae log file (def=LOG_FILE_MAX_SIZE).
        :param disable_buffering:       pass True to disable ae log buffering at app startup.
        """
        with log_file_lock:
            if py_logging_params:                   # init python logging - app is using python logging module
                logger_late_init()
                # logging.basicConfig(level=logging.DEBUG, style='{')
                logging.config.dictConfig(py_logging_params)     # re-configure py logging module
                self.py_log_params = py_logging_params
            else:                                   # (re-)init ae logging
                if self._log_file_stream:
                    self._close_log_file()
                    self._std_out_err_redirection(False)
                self._log_file_name = log_file_name
                self._log_file_size_max = log_file_size_max
                if not disable_buffering:
                    self._log_buf_stream = StringIO(initial_value="####  Log Buffer\n")

    def log_line_prefix(self) -> str:
        """ compile prefix of log print-out line for this :class:`AppBase` instance.

        The line prefix consists of (depending on the individual values of either a module variable or of an
        attribute this app instance):

        * :data:`_multi_threading_activated`: if True then the thread ident gets printed surrounded with
          angle brackets (< and >), right aligned and space padded to minimal 6 characters.
        * :attr:`sys_env_id`: if not empty then printed surrounded with curly brackets ({ and }), left aligned
          and space padded to minimal 4 characters.
        * :attr:`debug_level`: if greater or equal to :data:`DEBUG_LEVEL_TIMESTAMPED` then the system time
          (determined with :meth:`~datetime.datetime.now`) gets printed in the format specified by the
          :data:`DATE_TIME_ISO` constant.

        This method is using the instance attribute :attr:`_last_log_line_prefix` for to keep a copy of
        the last printed log line prefix for to prevent the printout of duplicate characters in consecutive
        log lines.

        :return: log file line prefix string including one space as separator character at the end.
        """
        parts = list()
        if _multi_threading_activated:
            parts.append(f"<{threading.get_ident(): >6}>")
        if self.app_key[-1] != APP_KEY_SEP:
            parts.append(f"{{{self.app_key: <6}}}")
        if self.debug_level >= DEBUG_LEVEL_TIMESTAMPED:
            parts.append(datetime.datetime.now().strftime(DATE_TIME_ISO))
        elif self.debug_level >= DEBUG_LEVEL_ENABLED:
            parts.append(f"[{DEBUG_LEVELS[self.debug_level][0]}]")

        prefix = "".join(parts)
        with log_file_lock:
            last_pre = self._last_log_line_prefix
            self._last_log_line_prefix = prefix

        return hide_dup_line_prefix(last_pre, prefix) + " "

    def log_file_check(self):
        """ check and possibly correct log file status.

        For already opened log files check if the ae log file is big enough and if yes then do a file rotation.
        If log file is not opened but log file name got already set, then check if log startup buffer is active
        and if yes then create log file, pass log buffer content to log file and close the log buffer.
        """
        with log_file_lock:
            if self._log_file_stream is not None:
                self._log_file_stream.seek(0, 2)  # due to non-posix-compliant Windows feature
                if self._log_file_stream.tell() >= self._log_file_size_max * 1024 * 1024:
                    self._close_log_file()
                    self._rename_log_file()
                    self._open_log_file()
            elif self._log_file_name:
                self._open_log_file()
                self._std_out_err_redirection(True)
                self._flush_and_close_log_buf()
            elif self.suppress_stdout and not self._nul_std_out:
                sys.stdout = self._nul_std_out = open(os.devnull, 'w')

    def print_out(self, *objects, file: Optional[TextIO] = None, **kwargs):
        """ app-instance-specific print-outs.

        :param objects:     objects to be printed out.
        :param file:        output stream object to be printed to (def=None). Passing None on a main app instance
                            will print the objects to the standard output and any active log files, but on a sub-app
                            instance with an active log file the print-out will get redirected exclusively/only
                            to log file of this sub-app instance.
        :param kwargs:      All the other supported kwargs of this method are documented
                            :func:`at the print_out() function of this module <print_out>`.

        This method has an alias named :meth:`.po`
        """
        if file is None and main_app_instance() is not self:
            with log_file_lock:
                stream = self._log_buf_stream or self._log_file_stream
            if stream:
                kwargs['file'] = stream
        if 'app' not in kwargs:
            kwargs['app'] = self
        print_out(*objects, **kwargs)

    po = print_out          #: alias of method :meth:`.print_out`

    def shutdown(self, exit_code: Optional[int] = 0, timeout: Optional[float] = None):
        """ shutdown this app instance and if it is the main app instance then also any created sub-app-instances.

        :param exit_code:   set application OS exit code - ignored if this is NOT the main app instance (def=0).
                            Pass None for to prevent call of sys.exit(exit_code).
        :param timeout:     timeout float value in seconds used for the thread termination/joining, for the
                            sub-app shutdowns and for the acquisition of the
                            threading locks of :data:`the ae log file <log_file_lock>` and the :data:`app instances
                            <app_inst_lock>`.
        """
        if self._shut_down:
            return

        if exit_code is not None:
            self.po("####  Shutdown............  ", exit_code, timeout, logger=_logger)

        is_main_instance = main_app_instance() is self
        if is_main_instance:
            _shut_down_sub_app_instances(timeout=timeout)
            if _multi_threading_activated:
                _join_app_threads(timeout=timeout)

        blocked = (False if is_main_instance and exit_code is not None  # prevent deadlock on app error exit/shutdown
                   else log_file_lock.acquire(**(dict(blocking=False) if timeout is None else dict(timeout=timeout))))

        self._flush_and_close_log_buf()
        self._close_log_file()
        if self._log_file_index:
            self._rename_log_file()

        if self._nul_std_out:
            if not self._nul_std_out.closed:
                self._append_eof_and_flush_file(self._nul_std_out, "NUL stdout")
                self._nul_std_out.close()
            self._nul_std_out = None

        if self.py_log_params:
            logging.shutdown()

        self._std_out_err_redirection(False)

        if blocked:
            log_file_lock.release()

        _unregister_app_instance(self.app_key)
        self._shut_down = True
        if is_main_instance and exit_code is not None:
            sys.exit(exit_code)

    def _std_out_err_redirection(self, redirect: bool):
        """ enable/disable the redirection of the standard output/error TextIO streams if needed.

        :param redirect:    pass True to enable or False to disable the redirection.
        """
        global ori_std_out, ori_std_err
        if redirect:
            if not isinstance(sys.stdout, _PrintingReplicator):  # sys.stdout==ori_std_out not works with pytest/capsys
                if not self.suppress_stdout:
                    std_out = ori_std_out
                elif self._nul_std_out and not self._nul_std_out.closed:
                    std_out = self._nul_std_out
                else:
                    std_out = self._nul_std_out = open(os.devnull, 'w')
                sys.stdout = _PrintingReplicator(sys_out_obj=std_out)
                sys.stderr = _PrintingReplicator(sys_out_obj=ori_std_err)
        else:
            if main_app_instance() is self:
                sys.stderr = ori_std_err
                sys.stdout = ori_std_out

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

    def _flush_and_close_log_buf(self):
        """ flush and close ae log buffer and pass content to log stream if opened.
        """
        if self._log_buf_stream:
            if self._log_file_stream:
                buf = self._log_buf_stream.getvalue() + "\n####  End Of Startup Log Buffer"
                self._log_file_stream.write(buf)
            self._log_buf_stream.close()
            self._log_buf_stream = None

    def _open_log_file(self):
        """ open the ae log file and ensure that standard output/error streams get redirected.
        """
        self._log_file_stream = open(self._log_file_name, "w", errors=DEF_ENCODE_ERRORS)

    def _close_log_file(self):
        """ close the ae log file.
        """
        if self._log_file_stream:
            stream = self._log_file_stream
            self._append_eof_and_flush_file(stream, "ae log file")
            self._log_file_stream = None
            stream.close()

    def _rename_log_file(self):
        """ rename rotating log file while keeping first/startup log and log file count below :data:`MAX_NUM_LOG_FILE`.
        """
        file_path, file_ext = os.path.splitext(self._log_file_name)
        dfn = file_path + "-{:0>{index_width}}".format(self._log_file_index, index_width=LOG_FILE_IDX_WIDTH) + file_ext
        if os.path.exists(dfn):
            os.remove(dfn)                              # remove old log file from previous app run
        if os.path.exists(self._log_file_name):         # prevent errors after log file error or unit test cleanup
            os.rename(self._log_file_name, dfn)

        self._log_file_index += 1
        if self._log_file_index > MAX_NUM_LOG_FILES:    # use > instead of >= for to always keep first/startup log file
            first_idx = self._log_file_index - MAX_NUM_LOG_FILES
            dfn = file_path + "-{:0>{index_width}}".format(first_idx, index_width=LOG_FILE_IDX_WIDTH) + file_ext
            if os.path.exists(dfn):
                os.remove(dfn)
