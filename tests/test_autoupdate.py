"""Actualizações automáticas (rad/autoupdate.py): só se instala um instalador assinado pelo fornecedor para a
versão anunciada; um ficheiro trocado é apagado; a instalação acontece ao fechar e o arranque seguinte avisa.
Sem rede nem Windows: o GitHub e o lançamento do instalador são simulados."""
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["APPDATA"] = tempfile.mkdtemp()

from rad import autoupdate, ed25519, updates  # noqa: E402

SECRET = bytes(range(32))
PUBLIC = ed25519.public_key(SECRET)
INSTALLER = b"MZ" + os.urandom(4096)


def _setup_file(data=INSTALLER):
    path = os.path.join(tempfile.mkdtemp(), "Setup_RootsAutoDoctor_9.0.0.exe")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


class _Resp(io.BytesIO):
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _opener(files):
    def opener(req, timeout=None):
        return _Resp(files[req.full_url])
    return opener


def _with_key(fn):
    old = autoupdate.public_key
    autoupdate.public_key = lambda: PUBLIC
    try:
        return fn()
    finally:
        autoupdate.public_key = old


def _info(sig, data=INSTALLER):
    files = {"https://dl/setup.exe": data, "https://dl/setup.exe.sig": json.dumps(sig).encode()}
    info = {"version": "9.0.0", "download": "https://dl/setup.exe", "signature": "https://dl/setup.exe.sig"}
    return info, _opener(files)


def test_signature_covers_file_and_version():
    path = _setup_file()
    sig = autoupdate.make_signature(SECRET, path, "9.0.0")
    assert autoupdate.verify_file(path, sig, "9.0.0", PUBLIC)
    assert not autoupdate.verify_file(path, sig, "9.0.1", PUBLIC)                 # outra versão
    assert not autoupdate.verify_file(_setup_file(INSTALLER + b"x"), sig, "9.0.0", PUBLIC)   # ficheiro trocado
    other = ed25519.public_key(bytes(32))
    assert not autoupdate.verify_file(path, sig, "9.0.0", other)                  # assinado por outra chave
    assert not autoupdate.verify_file(path, sig, "9.0.0", b"")                    # sem chave configurada


def test_download_verifies_and_keeps_pending_update():
    autoupdate.clear()
    sig = autoupdate.make_signature(SECRET, _setup_file(), "9.0.0")
    info, opener = _info(sig)
    st = _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
    assert st["version"] == "9.0.0" and os.path.exists(st["path"])
    assert autoupdate.pending()["path"] == st["path"]


def test_tampered_download_is_deleted_and_never_pending():
    autoupdate.clear()
    sig = autoupdate.make_signature(SECRET, _setup_file(), "9.0.0")
    info, opener = _info(sig, data=INSTALLER + b"malware")
    try:
        _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
        assert False, "um instalador alterado devia ser recusado"
    except updates.UpdateError as e:
        assert "verificação de segurança" in str(e)
    assert autoupdate.pending() is None
    assert not [n for n in os.listdir(autoupdate.updates_dir()) if n.endswith(".exe")]


def test_release_without_signature_is_not_downloaded():
    try:
        autoupdate.download({"version": "9.0.0", "download": "https://dl/setup.exe", "signature": None},
                            opener=_opener({}), current="1.9.0")
        assert False
    except updates.UpdateError as e:
        assert "assinado" in str(e)


def test_install_on_close_runs_silent_installer_and_gives_up_after_three_tries():
    autoupdate.clear()
    sig = autoupdate.make_signature(SECRET, _setup_file(), "9.0.0")
    info, opener = _info(sig)
    _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
    calls = []

    def launcher(path, args, elevate):
        calls.append((path, args, elevate))
        return True
    folder = tempfile.mkdtemp()
    for _ in range(autoupdate.MAX_ATTEMPTS):
        assert _with_key(lambda: autoupdate.install_pending(launcher=launcher, folder=folder))
    assert len(calls) == autoupdate.MAX_ATTEMPTS
    assert "/VERYSILENT" in calls[0][1] and calls[0][2] is False          # pasta gravável: sem administrador
    assert not _with_key(lambda: autoupdate.install_pending(launcher=launcher, folder=folder))
    assert autoupdate.pending() is None                                    # desistiu e limpou


def test_installer_changed_after_download_is_not_run():
    autoupdate.clear()
    sig = autoupdate.make_signature(SECRET, _setup_file(), "9.0.0")
    info, opener = _info(sig)
    st = _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
    with open(st["path"], "ab") as fh:
        fh.write(b"alterado depois")
    ran = []
    folder = tempfile.mkdtemp()
    assert not _with_key(lambda: autoupdate.install_pending(launcher=lambda *a: ran.append(a), folder=folder))
    assert not ran and autoupdate.pending() is None


def test_first_start_after_update_reports_and_cleans():
    autoupdate.clear()
    sig = autoupdate.make_signature(SECRET, _setup_file(), "9.0.0")
    info, opener = _info(sig)
    _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
    assert autoupdate.after_start(current="1.9.0") is None and autoupdate.pending()   # ainda por instalar
    assert autoupdate.after_start(current="9.0.0") == "9.0.0"
    assert autoupdate.pending() is None and not os.listdir(autoupdate.updates_dir())


def test_portable_or_source_never_installs_by_itself():
    assert not _with_key(lambda: autoupdate.can_self_update(installed=False))


def test_release_lists_installer_signature():
    rel = {"tag_name": "v9.0.0", "html_url": "h", "body": "",
           "assets": [{"name": "Setup_RootsAutoDoctor_9.0.0.exe", "browser_download_url": "https://dl/s.exe"},
                      {"name": "Setup_RootsAutoDoctor_9.0.0.exe.sig", "browser_download_url": "https://dl/s.sig"},
                      {"name": "RootsAutoDoctor_9.0.0_portatil.zip", "browser_download_url": "https://dl/p.zip"}]}

    def opener(req, timeout=None):
        return _Resp(json.dumps(rel).encode())
    r = updates.check("1.9.0", opener=opener)
    assert r["download"] == "https://dl/s.exe" and r["signature"] == "https://dl/s.sig"
