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


def test_codesign_is_skipped_without_a_certificate_and_fails_loudly_with_one():
    msgs = []
    assert finish_build.codesign("x.exe", environ={}, log=msgs.append) is None and "SmartScreen" in msgs[0]
    env = {"RAD_CODESIGN_PFX": r"C:\certs\roots.pfx", "RAD_CODESIGN_PASSWORD": "segredo",
           "RAD_SIGNTOOL": __file__}                    # um ficheiro que existe faz de signtool
    cmd = finish_build.codesign_command("dist\\Setup.exe", env, "signtool.exe")
    assert cmd[:4] == ["signtool.exe", "sign", "/fd", "SHA256"] and cmd[-1] == "dist\\Setup.exe"
    assert ["/f", r"C:\certs\roots.pfx", "/p", "segredo"] == cmd[cmd.index("/f"):cmd.index("/f") + 4]
    assert "/sha1" in finish_build.codesign_command("a.exe", {"RAD_CODESIGN_THUMBPRINT": "AB12"}, "s")

    class Res:
        returncode, stdout, stderr = 1, "", "SignTool Error: no certificates"
    try:
        finish_build.codesign("a.exe", environ=env, run=lambda *a, **k: Res(), log=msgs.append)
        raise AssertionError("devia falhar")
    except RuntimeError as e:
        assert "no certificates" in str(e)
    Res.returncode = 0
    assert finish_build.codesign("a.exe", environ=env, run=lambda *a, **k: Res(), log=msgs.append) is True


def test_clean_pc_test_before_publishing_passes_fails_or_says_it_was_not_done():
    zip_path = finish_build.portable(_fake_dist(), "9.9.9", out_dir=tempfile.mkdtemp(), log=lambda m: None)
    msgs = []
    assert finish_build.clean_pc_test(zip_path, log=msgs.append, exe="", launch=lambda c: None) is None
    assert "Sandbox" in msgs[0] and "não foi feito" in msgs[0]                # sem Windows Sandbox: avisa

    def sandbox_writes(result):
        def launch(cmd):
            with open(cmd[1], encoding="utf-8") as fh:
                wsb = fh.read()
            assert "RootsAutoDoctor.exe" in wsb and "--selftest" in wsb and "Roots Auto Doctor</HostFolder>" in wsb
            folder = os.path.join(finish_build.ROOT, "build", "pc_limpo_release", "resultado")
            with open(os.path.join(folder, "autoteste.txt"), "w", encoding="utf-8") as fh:
                fh.write("...\nRESULTADO: " + result + "\n")
        return launch
    closed = []
    run = dict(exe="WindowsSandbox.exe", poll=0.01, log=lambda m: None, close=lambda: closed.append(1))
    assert finish_build.clean_pc_test(zip_path, launch=sandbox_writes("tudo OK"), **run) is True
    assert finish_build.clean_pc_test(zip_path, launch=sandbox_writes("há falhas"), **run) is False
    assert finish_build.clean_pc_test(zip_path, launch=lambda c: None, timeout=0.05, **run) is False
    assert len(closed) == 3                                   # o Sandbox é sempre fechado
