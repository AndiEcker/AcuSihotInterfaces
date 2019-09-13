import pytest
import os
import struct

from ae_osa.architecture import executable_architecture


def test_executable_architecture_invalid_file():
    with pytest.raises(FileNotFoundError):
        executable_architecture('NotExistingFile.exe')


@pytest.mark.parametrize(('prefix', 'machine', 'architecture'),
                         [
                             (bytes.fromhex('7f454c46'), None, 'elf'),
                             (bytes.fromhex('cafebabe'), None, 'java'),
                             (bytes.fromhex('feedface'), None, 'Mach-O'),
                             (b'#! /bin/sh', None, 'sh'),
                             (b'MZ', 0x014c, 'i386'),
                             (b'MZ', 0x0200, 'IA64'),
                             (b'MZ', 0x8664, 'x64'),
                             (b'MZ', 1, 'MS-unknown'),
                             (b'MZ', 0, 'MS-unknown'),
                             (b'', 0, None),
                         ])
def test_pseudo_executable(prefix, machine, architecture):
    file_name = 'TEST.EXECUTABLE'
    with open(file_name, 'wb') as file_handle:
        if prefix[:2] == b'MZ':
            prefix = struct.pack('2s58si', prefix, b"x"*58, 64)
        file_handle.write(prefix)

        if machine is not None:
            pe_hdr = struct.pack('2s2sH', b'PE', b"y"*2, machine)
            file_handle.write(pe_hdr)

    assert executable_architecture(file_name) == architecture
    os.remove(file_name)


@pytest.mark.parametrize(('file_name', 'architectures'),
                         [
                             ('/usr/bin/file', ('elf', )),
                             ('/usr/bin/grep', ('elf', )),
                             ('/usr/bin/which', ('sh', )),
                             ('c:\\windows\\explorer.exe', ('i386', 'IA64', 'x64')),
                             ('c:\\windows\\notepad.exe', ('i386', 'IA64', 'x64')),
                             ('c:\\windows\\regedit.exe', ('i386', 'IA64', 'x64')),
                             ('c:\\windows\\twain_32.dll', ('i386', 'IA64', 'x64')),
                         ])
def test_os_executables(file_name, architectures):
    exists = os.path.exists(file_name)
    print("{} OS executable {}".format("Checking architectures {} for".format(architectures) if exists else "SKIPPING",
                                       file_name))
    if exists:
        assert executable_architecture(file_name) in architectures
