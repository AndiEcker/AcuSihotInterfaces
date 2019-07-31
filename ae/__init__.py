import os
import re
import sys
import inspect
import logging
import unicodedata


DEBUG_LEVEL_DISABLED = 0        # ERROR/CRITICAL
DEBUG_LEVEL_ENABLED = 1         # WARNING
DEBUG_LEVEL_VERBOSE = 2         # INFO/DEBUG
DEBUG_LEVEL_TIMESTAMPED = 3     # -"- plus timestamp in logging format

debug_levels = {0: 'disabled', 1: 'enabled', 2: 'verbose', 3: 'timestamped'}

logging_levels = {DEBUG_LEVEL_DISABLED: logging.ERROR, DEBUG_LEVEL_ENABLED: logging.WARNING,
                  DEBUG_LEVEL_VERBOSE: logging.INFO, DEBUG_LEVEL_TIMESTAMPED: logging.DEBUG}

# default date/time formats in config files/variables
DATE_TIME_ISO = '%Y-%m-%d %H:%M:%S.%f'
DATE_ISO = '%Y-%m-%d'

# core encoding that will always work independent from destination (console, file system, XMLParser, ...)
DEF_ENCODING = 'ascii'

# illegal unicode/XML characters
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


def force_encoding(text, encoding=DEF_ENCODING, errors='backslashreplace'):
    """ force the encoding of text (str or bytes) """
    if isinstance(text, str):
        text = text.encode(encoding=encoding, errors=errors)
    return text.decode(encoding=encoding)


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


def round_traditional(val, digits=0):
    """ needed because python round() is not working always, like e.g. round(0.075, 2) == 0.07 instead of 0.08
        taken from https://stackoverflow.com/questions/31818050/python-2-7-round-number-to-nearest-integer
    """
    return round(val + 10**(-len(str(val)) - 1), digits)


def sys_env_dict(file=__file__):
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


def sys_env_text(file=__file__, ind_ch=" ", ind_len=18, key_ch="=", key_len=12, extra_sys_env_dict=None):
    sed = sys_env_dict(file=file)
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
