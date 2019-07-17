import pytest
import os
import struct

from ae.architecture import executable_architecture


def test_executable_architecture_invalid_file():
    with pytest.raises(FileNotFoundError):
        executable_architecture('NotExistingFile.exe')


@pytest.mark.parametrize(('machine', 'architecture'),
                         [
                             (0x014c, 'i386'),
                             (0x0200, 'IA64'),
                             (0x8664, 'x64'),
                             (0, 'unknown'),
                         ])
def test_pseudo_executable(machine, architecture):
    file_name = 'TEST._D_L_L'
    with open(file_name, 'wb') as file_handle:
        dos_hdr = struct.pack('2s58si', b'MZ', b"x"*58, 64)
        file_handle.write(dos_hdr)

        pe_hdr = struct.pack('2s2sH', b'PE', b"y"*2, machine)
        file_handle.write(pe_hdr)
    assert executable_architecture(file_name) == architecture
    os.remove(file_name)


@pytest.mark.parametrize(('file_name', 'architectures'),
                         [
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
