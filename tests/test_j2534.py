"""J2534: ponte num processo à parte + KWP2000 sobre PassThru, com a interface simulada."""
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import j2534
from rad.errors import ConnectError, NoResponse
from rad.session import ECUSession

SIM = "J2534:SIMULADOR-J2534"


def test_kwp2000_over_bridge():
    link = j2534.J2534Link(SIM)
    link.open()
    try:
        s = ECUSession(link)
        info = s.connect(0x03)
        assert info["protocol"] == "KWP2000 (J2534)" and info["part"] == "1C0907379K"
        assert [f["vag"] for f in s.read_faults()] == ["00283"]
        assert s.read_group(1)["fields"][0]["unit"] == "km/h"
        s.keep_alive()
        assert s.clear_faults() == []
        s.disconnect()
    finally:
        link.close()
    assert link.proc is None


def test_kw1281_refused_and_absent_module():
    link = j2534.J2534Link(SIM)
    link.open()
    try:
        try:
            ECUSession(link).connect(0x01)
            assert False
        except ConnectError as e:
            assert "KW1281" in str(e)
        try:
            ECUSession(link).connect(0x45)
            assert False
        except NoResponse:
            pass
    finally:
        link.close()


def test_dll_bitness():
    d = tempfile.mkdtemp()
    for machine, bits in ((0x14C, 32), (0x8664, 64)):
        p = os.path.join(d, f"x{bits}.dll")
        with open(p, "wb") as fh:
            data = bytearray(0x200)
            data[0:2] = b"MZ"
            struct.pack_into("<I", data, 0x3C, 0x80)
            data[0x80:0x84] = b"PE\0\0"
            struct.pack_into("<H", data, 0x84, machine)
            fh.write(data)
        assert j2534.dll_bitness(p) == bits
    assert j2534.dll_bitness(os.path.join(d, "nada.dll")) is None


def test_missing_dll():
    link = j2534.J2534Link("J2534:C:\\nao\\existe.dll")
    try:
        link.open()
        assert False
    except Exception as e:
        assert "não encontrado" in str(e)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
