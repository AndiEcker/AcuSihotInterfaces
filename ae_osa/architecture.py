"""
operating system architecture helper functions
==============================================
"""
import os
import sys
from typing import Optional


def executable_architecture(executable_file: str) -> Optional[str]:
    """ function determining the type of executable architecture of any file (linux binary, shell script, DLL/EXE)

    On linux systems the file command could be used for that (unfortunately not available in MS Windows).
    Inspired by <https://github.com/tgandor/meats/blob/master/missing/arch_of.py>_ and
    <https://stackoverflow.com/questions/14799966/detect-an-executable-file-in-java?lq=1>_.

    :param executable_file:     file name (optionally with file path) to investigate.
    :return:                    possible return values:

                                * 'elf' for linux applications (executable binaries)
                                * 'java' for java class applications
                                * 'Mach-O' for Macintosh OSX applications
                                * 'sh' for linux shell scripts
                                * 'i386' for 32 bit, 'IA64' or 'x64' for 64 bit MS Windows applications
                                * 'MS-unknown' for MS Windows application (machine architecture is unknown)
                                * None if passed file is not recognized as executable (or cannot be opened)
    """
    ret = None
    with open(executable_file, 'rb') as file_handle:
        prefix = file_handle.read(64)
        if prefix[:4] == bytes.fromhex('7f454c46'):
            ret = 'elf'         # linux
        elif prefix[:4] == bytes.fromhex('cafebabe'):
            ret = 'java'
        elif prefix[:4] == bytes.fromhex('feedface'):
            ret = 'Mach-O'      # Mac OSX
        elif prefix[:10] == b'#! /bin/sh':
            ret = 'sh'
        elif prefix[:2] == b'MZ':
            offset = int.from_bytes(prefix[-4:], byteorder=sys.byteorder)
            file_handle.seek(offset, os.SEEK_SET)
            pe_hdr = file_handle.read(6)
            if pe_hdr[:2] == b'PE':
                machine = int.from_bytes(pe_hdr[4:], byteorder=sys.byteorder)
                if machine == 0x014c:
                    ret = 'i386'
                elif machine == 0x0200:
                    ret = 'IA64'
                elif machine == 0x8664:
                    ret = 'x64'
                else:
                    ret = 'MS-unknown'
    return ret
