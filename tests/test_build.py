"""Build de venda (tools/finish_build.py): a pasta compilada tem de levar tudo o que um PC limpo não tem
(runtime do Visual C++, plugin do Qt, pontes, Python portátil) e a versão portátil abre-se sem instalar nada.
Corre sem compilar nada: usa uma pasta compilada falsa."""
import json
import os
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import finish_build  # noqa: E402


def _fake_dist(skip=()):
    dist = tempfile.mkdtemp()
    files = list(finish_build.REQUIRED) + [os.path.join("PySide6", "qt-plugins", "platforms", "qwindows.dll")]
    files += finish_build.MSVC_RUNTIME[:3]
    for rel in files:
        if rel in skip:
            continue
        path = os.path.join(dist, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"x")
    return dist


def test_complete_dist_passes_check():
    assert finish_build.check(_fake_dist(), log=lambda m: None)


def test_missing_qt_plugin_or_bridge_fails_check():
    plugin = os.path.join("PySide6", "qt-plugins", "platforms", "qwindows.dll")
    assert not finish_build.check(_fake_dist(skip=[plugin]), log=lambda m: None)
    assert not finish_build.check(_fake_dist(skip=[os.path.join("runtime", "py32", "python.exe")]),
                                  log=lambda m: None)


def test_missing_msvc_runtime_is_copied_when_available():
    dist = _fake_dist(skip=["vcruntime140.dll"])
    src = tempfile.mkdtemp()
    with open(os.path.join(src, "vcruntime140.dll"), "wb") as fh:
        fh.write(b"dll")
    old = finish_build._msvc_sources
    finish_build._msvc_sources = lambda: [src]
    try:
        assert finish_build.check(dist, log=lambda m: None)
    finally:
        finish_build._msvc_sources = old
    assert os.path.exists(os.path.join(dist, "vcruntime140.dll"))


def test_portable_zip_has_one_folder_with_the_program_and_instructions():
    dist = _fake_dist()
    out = tempfile.mkdtemp()
    path = finish_build.portable(dist, "9.9.9", out_dir=out, log=lambda m: None)
    assert os.path.basename(path) == "RootsAutoDoctor_9.9.9_portatil.zip"
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        readme = z.read("Roots Auto Doctor/LEIA-ME.txt").decode("utf-8")
    assert "Roots Auto Doctor/RootsAutoDoctor.exe" in names
    assert all(n.startswith("Roots Auto Doctor/") for n in names)
    assert "9.9.9" in readme and "Executar mesmo assim" in readme and "Run anyway" in readme


def test_installer_signature_for_automatic_updates():
    from rad import autoupdate, ed25519
    secret = bytes(range(1, 33))
    setup = os.path.join(tempfile.mkdtemp(), "Setup_RootsAutoDoctor_9.9.9.exe")
    with open(setup, "wb") as fh:
        fh.write(b"MZ instalador")
    path = finish_build.sign(setup, "9.9.9", secret=secret, log=lambda m: None)
    assert path == setup + ".sig"
    with open(path, encoding="utf-8") as fh:
        sig = json.load(fh)
    assert autoupdate.verify_file(setup, sig, "9.9.9", ed25519.public_key(secret))
