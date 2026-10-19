"""Licenças: chaves válidas, de outro PC, expiradas e adulteradas."""
import base64
import datetime
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rad import ed25519, license

FAKE_SECRET = bytes(range(32))     # chave de teste, diferente da verdadeira


def test_machine_code_format():
    c = license.machine_code()
    assert len(c) == 19 and c.count("-") == 3


def test_foreign_signature_rejected():
    key = license.make_key(FAKE_SECRET, "AAAA-BBBB-CCCC-DDDD", "Pirata")
    assert license.check_key(key, machine="AAAA-BBBB-CCCC-DDDD")["status"] == "invalid"


def test_real_key_if_available():
    path = os.path.join(ROOT, "keys", "roots_private.key")
    if not os.path.exists(path):
        return                       # a chave privada só existe no PC do vendedor
    secret = base64.b64decode(open(path).read().strip())
    m = "AAAA-BBBB-CCCC-DDDD"
    k = license.make_key(secret, m, "Oficina", "2030-01-01")
    assert license.check_key(k, machine=m)["status"] == "valid"
    assert license.check_key(k, machine="0000-0000-0000-0000")["status"] == "other_pc"
    assert license.check_key(k, machine=m, today=datetime.date(2031, 1, 1))["status"] == "expired"
    p, s = k.split(".")
    tampered = license._b64e(license._b64d(p).replace(b"Oficina", b"Oficin4")) + "." + s
    assert license.check_key(tampered, machine=m)["status"] == "invalid"
    assert license.check_key("lixo", machine=m)["status"] == "invalid"
    assert license.check_key(" \n".join([k[:40], k[40:]]), machine=m)["status"] == "valid"


def test_clock_rollback_ignored():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "estado")
        d1, d0 = datetime.date(2027, 5, 1), datetime.date(2026, 1, 1)
        assert license._effective_today(d1, path) == d1
        assert license._effective_today(d0, path) == d1       # relógio atrasado: conta a última data vista
        assert license._effective_today(datetime.date(2027, 6, 1), path) == datetime.date(2027, 6, 1)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
