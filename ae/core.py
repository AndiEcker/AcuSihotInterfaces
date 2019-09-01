import inspect
import logging
import os
import re
import sys
import unicodedata
from typing import Dict, List, Tuple, Optional, AnyStr, Pattern

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

ILLEGAL_XML_CHARS: List[Tuple[int, int]] = [(0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F),
                                            (0x7F, 0x84), (0x86, 0x9F),
                                            (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF)]
""" illegal unicode/XML characters.

taken from https://stackoverflow.com/questions/1707890/fast-way-to-filter-illegal-xml-unicode-chars-in-python.
"""
if sys.maxunicode >= 0x10000:  # not narrow build of Python
    ILLEGAL_XML_CHARS.extend([(0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF),
                              (0x3FFFE, 0x3FFFF), (0x4FFFE, 0x4FFFF),
                              (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                              (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF),
                              (0x9FFFE, 0x9FFFF), (0xAFFFE, 0xAFFFF),
                              (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                              (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF),
                              (0xFFFFE, 0xFFFFF), (0x10FFFE, 0x10FFFF)])


def illegal_xml_sub() -> Pattern[str]:
    """ generate pre-compiled regular expression for to find illegal unicode/XML characters in a string.

    :return: re module compatible substitution expression for to detect illegal unicode chars.
    """
    return re.compile('[%s]' % u''.join(["%s-%s" % (chr(low), chr(high)) for (low, high) in ILLEGAL_XML_CHARS]))


def calling_module(called_module: Optional[str] = __name__, depth: int = 1) -> Optional[str]:
    """ determine/find the first stack frame that is *not* in the module specified by ``called_module``.

    :param called_module:   skipped module name; for normal usages pass here the module name from which this
                            function get called.
    :param depth:           the calling level from which on to search (def=1 which refers the next higher module).
                            Pass 2 or a even higher value if you want to get the module name from a higher level
                            in the call stack.
    :return:                The module name of a higher level within the call stack.
    """
    module = None
    try:
        while True:
            # noinspection PyProtectedMember
            module = sys._getframe(depth).f_globals.get('__name__', '__main__')
            if module != called_module:
                break
            depth += 1
    except (TypeError, AttributeError, ValueError):
        pass
    return module


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


def round_traditional(val: float, digits: int = 0) -> float:
    """ round numeric value traditional.

    Needed because python round() is working differently, e.g. round(0.075, 2) == 0.07 instead of 0.08
    taken from https://stackoverflow.com/questions/31818050/python-2-7-round-number-to-nearest-integer.

    :param val:     float value to be round.
    :param digits:  number of digits to be round (def=0 - rounds to an integer value).

    :return:        rounded value.
    """
    return round(val + 10**(-len(str(val)) - 1), digits)


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


def sys_env_text(file: str = __file__, ind_ch: str = " ", ind_len: int = 18, key_ch: str = " =", key_len: int = 12,
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
                     .format(ind="", ind_ch=ind_ch, ind_len=ind_len, key_ch=key_ch, key_len=key_len, key=k, val=v)
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
