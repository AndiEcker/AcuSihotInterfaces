"""
unicode helper constants and functions
======================================

"""
from functools import lru_cache
from typing import List, Tuple, Pattern
import re
import sys


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


@lru_cache(maxsize=1)
def illegal_xml_sub() -> Pattern[str]:
    """ generate pre-compiled regular expression to find illegal unicode/XML characters in a string.

    :return: re module compatible substitution expression to detect illegal unicode chars.
    """
    return re.compile('[%s]' % u''.join(["%s-%s" % (chr(low), chr(high)) for (low, high) in ILLEGAL_XML_CHARS]))
