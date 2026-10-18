"""Diagnóstico da ligação e pacote de suporte (sem Qt: chama o worker directamente)."""
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["APPDATA"] = tempfile.mkdtemp()

from rad import applog


def test_support_bundle():
    applog.DiskLog().write("[00:00:00] teste")
    p = os.path.join(tempfile.mkdtemp(), "suporte.zip")
    applog.make_support_bundle(p)
    names = zipfile.ZipFile(p).namelist()
    assert "sistema.txt" in names and any(n.startswith("comunicacao_") for n in names)
    assert not any("licenca" in n or "historico" in n for n in names)


if __name__ == "__main__":
    test_support_bundle()
    print("OK test_support_bundle")
