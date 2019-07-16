import pytest
import os
import struct

from ae.architecture import executable_architecture


# @pytest.fixture(params=)
def create_executable(file_name='TEST.TXT', magic=b'MZ', magic_pe=b'PE', machine=0x8664):
    with open(file_name, 'wb') as file_handle:
        dos_hdr = struct.pack('2s58si', magic, "x"*58, 0)
        file_handle.write(dos_hdr)

        pe_hdr = struct.pack('2s2sH', magic_pe, "y"*2, machine)
        file_handle.write(pe_hdr)
    yield file_name
    os.remove(file_name)


def test_executable_architecture_invalid_file():
    with pytest.raises(FileNotFoundError):
        executable_architecture('NotExistingFile.exe')
