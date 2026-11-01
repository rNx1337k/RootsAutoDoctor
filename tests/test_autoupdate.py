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


class _Key:
    """Chave de actualizações de teste enquanto dura o bloco with."""
    def __enter__(self):
        self.old = autoupdate.public_key
        autoupdate.public_key = lambda: PUBLIC

    def __exit__(self, *a):
        autoupdate.public_key = self.old


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
    assert any(a.startswith("/LOG=") and a.endswith(autoupdate.LOG_NAME) for a in calls[0][1])
    assert autoupdate.RELAUNCH_ARG not in calls[0][1]                     # ao fechar: não volta a abrir
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


def test_source_or_read_only_copy_never_installs_by_itself():
    assert not _with_key(lambda: autoupdate.can_self_update(installed=False))           # código-fonte
    folder = tempfile.mkdtemp()
    mode = autoupdate.update_mode
    assert _with_key(lambda: mode(installed=True, platform="win32")) == autoupdate.INSTALLER
    assert _with_key(lambda: mode(installed=False, frozen=True, folder=folder, platform="win32")) == autoupdate.PORTABLE
    assert _with_key(lambda: mode(installed=False, frozen=False, folder=folder, platform="win32")) is None
    assert _with_key(lambda: mode(installed=False, frozen=True, folder=os.path.join(folder, "nao_existe"),
                                  platform="win32")) is None                          # pasta só de leitura
    assert _with_key(lambda: mode(installed=True, platform="linux")) is None
    assert mode(installed=True, platform="win32") is None or autoupdate.public_key()  # sem chave: só avisa


def test_release_lists_installer_signature():
    rel = {"tag_name": "v9.0.0", "html_url": "h", "body": "",
           "assets": [{"name": "Setup_RootsAutoDoctor_9.0.0.exe", "browser_download_url": "https://dl/s.exe"},
                      {"name": "Setup_RootsAutoDoctor_9.0.0.exe.sig", "browser_download_url": "https://dl/s.sig"},
                      {"name": "RootsAutoDoctor_9.0.0_portatil.zip", "browser_download_url": "https://dl/p.zip"}]}

    def opener(req, timeout=None):
        return _Resp(json.dumps(rel).encode())
    r = updates.check("1.9.0", opener=opener)
    assert r["download"] == "https://dl/s.exe" and r["signature"] == "https://dl/s.sig"


def test_update_now_asks_the_installer_to_reopen_the_program():
    autoupdate.clear()
    sig = autoupdate.make_signature(SECRET, _setup_file(), "9.0.0")
    info, opener = _info(sig)
    _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
    calls = []
    assert _with_key(lambda: autoupdate.install_pending(launcher=lambda p, a, e: calls.append(a) or True,
                                                        folder=tempfile.mkdtemp(), relaunch=True))
    assert autoupdate.RELAUNCH_ARG in calls[0] and "/VERYSILENT" in calls[0]
    autoupdate.clear()


def test_installer_reopens_the_program_only_for_update_now():
    iss = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "installer",
                            "RootsAutoDoctor.iss"), encoding="utf-8").read()
    assert "Check: ShouldRelaunch" in iss and "{param:RELAUNCH|0}" in iss and "WizardSilent" in iss
    assert autoupdate.RELAUNCH_ARG == "/RELAUNCH=1"


# ------------------------------------------------------------------ resultado no arranque seguinte
def _launched(attempts=1, launched=True):
    autoupdate.clear()
    sig = autoupdate.make_signature(SECRET, _setup_file(), "9.0.0")
    info, opener = _info(sig)
    info["notes"] = "• Novidade"
    _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
    for _ in range(attempts):
        _with_key(lambda: autoupdate.install_pending(launcher=lambda *a: launched, folder=tempfile.mkdtemp()))


def test_successful_update_reports_the_new_version_with_its_notes():
    _launched()
    st = autoupdate.startup_status(current="9.0.0")
    assert st == {"result": "updated", "version": "9.0.0", "notes": "• Novidade"}
    assert autoupdate.pending() is None


def test_failed_update_is_reported_once_and_the_program_keeps_working():
    _launched()
    later = autoupdate.pending()["launched_at"] + autoupdate.SETTLE_SECONDS + 1
    assert autoupdate.startup_status(current="1.9.0", now=later - 60) is None   # pode estar ainda a instalar
    st = autoupdate.startup_status(current="1.9.0", now=later)
    assert st["result"] == "failed" and st["version"] == "9.0.0" and not st["gave_up"] and not st["denied"]
    assert autoupdate.startup_status(current="1.9.0", now=later) is None        # só avisa uma vez
    assert autoupdate.pending()                                                  # volta a tentar ao fechar
    autoupdate.clear()


def test_refused_authorisation_and_giving_up_keep_the_installation_log():
    _launched(launched=False)
    later = autoupdate.pending()["launched_at"] + autoupdate.SETTLE_SECONDS + 1
    assert autoupdate.startup_status(current="1.9.0", now=later)["denied"]
    _launched(attempts=autoupdate.MAX_ATTEMPTS)
    with open(autoupdate.log_path(), "w") as fh:
        fh.write("registo do instalador")
    later = autoupdate.pending()["launched_at"] + autoupdate.SETTLE_SECONDS + 1
    assert autoupdate.startup_status(current="1.9.0", now=later)["gave_up"]
    assert autoupdate.pending() is None and os.listdir(autoupdate.updates_dir()) == [autoupdate.LOG_NAME]
    autoupdate.clear()


# ------------------------------------------------------------------ versão portátil
def _portable_zip(files=None, top="Roots Auto Doctor"):
    import zipfile
    path = os.path.join(tempfile.mkdtemp(), "RootsAutoDoctor_9.0.0_portatil.zip")
    files = files if files is not None else {f"{top}/RootsAutoDoctor.exe": b"MZ novo", f"{top}/LEIA-ME.txt": b"x",
                                             f"{top}/runtime/py64/python.exe": b"MZ py"}
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return path


def _portable_info(zip_path):
    sig = autoupdate.make_signature(SECRET, zip_path, "9.0.0")
    with open(zip_path, "rb") as fh:
        data = fh.read()
    files = {"https://dl/p.zip": data, "https://dl/p.zip.sig": json.dumps(sig).encode()}
    info = {"version": "9.0.0", "download": "https://dl/setup.exe", "signature": "https://dl/setup.exe.sig",
            "portable": "https://dl/p.zip", "portable_signature": "https://dl/p.zip.sig"}
    return info, _opener(files)


def test_portable_copy_downloads_the_signed_zip_and_applies_it_after_closing():
    autoupdate.clear()
    info, opener = _portable_info(_portable_zip())
    assert autoupdate.downloadable(info, autoupdate.PORTABLE) and not autoupdate.downloadable({}, autoupdate.PORTABLE)
    st = _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0", mode=autoupdate.PORTABLE))
    assert st["mode"] == autoupdate.PORTABLE and st["path"].endswith("_portatil.zip")
    assert os.path.isfile(os.path.join(st["staging"], "RootsAutoDoctor.exe"))
    calls = []
    app = os.path.join(tempfile.mkdtemp(), "Pasta do programa")
    os.makedirs(app)
    assert _with_key(lambda: autoupdate.install_pending(launcher=lambda p, a, e: calls.append((p, a, e)) or True,
                                                        folder=app, relaunch=True, pid=4321))
    script = calls[0][0]
    assert script.endswith(autoupdate.SCRIPT) and calls[0][2] is False
    text = open(script, encoding="utf-8").read()
    assert 'set "PID=4321"' in text and f'set "APP={app}"' in text and f'set "NEW={st["staging"]}"' in text
    assert 'if not "1"=="1" goto end' in text and "robocopy" in text and ":rollback" in text
    assert 'if "0"=="1" (start "" explorer.exe' in text                       # sem administrador: abre directo
    assert open(script, "rb").read().count(b"\r\n") > 20                      # CRLF: o cmd lê linha a linha
    autoupdate.clear()


def test_portable_copy_in_a_read_only_folder_asks_windows_for_permission():
    autoupdate.clear()
    info, opener = _portable_info(_portable_zip())
    _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0", mode=autoupdate.PORTABLE))
    app = os.path.join(tempfile.mkdtemp(), "Programas", "Roots Auto Doctor")
    os.makedirs(app)
    assert _with_key(lambda: autoupdate.update_mode(installed=False, frozen=True, folder=app,
                                                    platform="win32")) == autoupdate.PORTABLE
    calls, writable = [], autoupdate._writable
    autoupdate._writable = lambda folder: False
    try:
        assert not _with_key(lambda: autoupdate.install_pending(launcher=lambda p, a, e: calls.append(e) or False,
                                                                folder=app, relaunch=True, pid=4321))
    finally:
        autoupdate._writable = writable
    assert calls == [True]                                                    # pede autorização de administrador
    text = open(os.path.join(autoupdate.updates_dir(), autoupdate.SCRIPT), encoding="utf-8").read()
    assert 'if "1"=="1" (start "" explorer.exe' in text                       # reabre como o utilizador normal
    st = autoupdate.pending()
    assert st["attempts"] == 1 and st["launched"] is False                     # autorização recusada: avisa no arranque
    res = autoupdate.startup_status(current="1.9.0", now=st["launched_at"] + autoupdate.SETTLE_SECONDS + 1)
    assert res["result"] == "failed" and res["denied"]
    autoupdate.clear()


def test_update_left_uninstalled_is_installed_on_the_next_start_only_once():
    autoupdate.clear()
    path = _setup_file()
    info, opener = _info(autoupdate.make_signature(SECRET, path, "9.0.0"))
    _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
    assert autoupdate.ready_on_start(mode=autoupdate.PORTABLE) is None             # descarregada para outro modo
    assert _with_key(lambda: autoupdate.ready_on_start(mode=autoupdate.INSTALLER))["version"] == "9.0.0"
    calls = []
    folder = tempfile.mkdtemp()
    assert _with_key(lambda: autoupdate.install_on_start(launcher=lambda p, a, e: calls.append(a) or True,
                                                         folder=folder, mode=autoupdate.INSTALLER))
    args = calls[0]
    assert "/SILENT" in args and "/VERYSILENT" not in args and autoupdate.RELAUNCH_ARG in args   # barra de progresso
    # já foi tentada: se não terminou, o programa abre normalmente (tenta outra vez ao fechar), nunca em ciclo
    assert _with_key(lambda: autoupdate.ready_on_start(mode=autoupdate.INSTALLER)) is None
    assert not _with_key(lambda: autoupdate.install_on_start(launcher=lambda p, a, e: calls.append(a) or True,
                                                             folder=folder, mode=autoupdate.INSTALLER))
    assert len(calls) == 1
    autoupdate.clear()


def test_portable_zip_with_paths_outside_its_folder_is_refused():
    autoupdate.clear()
    for files in ({"Roots Auto Doctor/RootsAutoDoctor.exe": b"MZ", "../fora.txt": b"x"},
                  {"Outra/coisa.exe": b"MZ"}):
        info, opener = _portable_info(_portable_zip(files))
        try:
            _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0", mode=autoupdate.PORTABLE))
            assert False
        except updates.UpdateError as e:
            assert "danificada" in str(e)
        assert autoupdate.pending() is None


def _dead_pid():
    import subprocess
    p = subprocess.Popen(["cmd.exe", "/c", "exit"])
    p.wait()
    return p.pid


def _run_script(new, app):
    import subprocess
    folder = tempfile.mkdtemp()
    script = autoupdate.portable_script("9.0.0", _dead_pid(), app, new, folder=folder)
    subprocess.run(["cmd.exe", "/c", script], capture_output=True, timeout=180)
    with open(os.path.join(folder, autoupdate.LOG_NAME), encoding="utf-8", errors="replace") as fh:
        return fh.read(), folder


def test_portable_script_copies_the_new_version_and_restores_the_old_one_on_failure():
    if sys.platform != "win32":                       # o script corre no cmd do Windows (robocopy)
        return
    base = tempfile.mkdtemp()
    app, new = os.path.join(base, "Roots Auto Doctor"), os.path.join(base, "nova", "Roots Auto Doctor")
    for folder, version in ((app, "antiga"), (new, "nova")):
        os.makedirs(os.path.join(folder, "_internal"))
        with open(os.path.join(folder, "RootsAutoDoctor.exe"), "w") as fh:
            fh.write(version)
    with open(os.path.join(new, "_internal", "novo.dll"), "w") as fh:
        fh.write("x")
    log_text, folder = _run_script(new, app)
    assert "RESULTADO: ok" in log_text, log_text
    assert open(os.path.join(app, "RootsAutoDoctor.exe")).read() == "nova"
    assert os.path.exists(os.path.join(app, "_internal", "novo.dll"))
    assert not os.path.exists(new)
    # a cópia da versão anterior fica até a nova abrir bem (é o caminho de volta)
    assert open(os.path.join(folder, autoupdate.BACKUP, "RootsAutoDoctor.exe")).read() == "antiga"
    log_text, _ = _run_script(os.path.join(base, "nao_existe"), app)          # a cópia falha: repõe a anterior
    assert "RESULTADO: falhou" in log_text, log_text
    assert open(os.path.join(app, "RootsAutoDoctor.exe")).read() == "nova"


def _clean_rollback():
    import shutil
    autoupdate.clear()
    shutil.rmtree(autoupdate.rollback_dir(), ignore_errors=True)


def test_new_version_that_does_not_open_goes_back_to_the_previous_installer():
    _clean_rollback()
    folder = tempfile.mkdtemp()
    old_setup = _setup_file(b"instalador 1.9.0")
    old_sig = autoupdate.make_signature(SECRET, old_setup, "1.9.0")
    path = _setup_file()
    info, opener = _info(autoupdate.make_signature(SECRET, path, "9.0.0"))
    with _Key():
        # 1.9.0 actualiza-se para 9.0.0 (e o instalador da 1.9.0 tinha ficado guardado da actualização anterior)
        autoupdate._keep_installer(old_setup, old_sig, "1.9.0")
        autoupdate.download(info, opener=opener, current="1.9.0")
        autoupdate._prepare_rollback("9.0.0", autoupdate.INSTALLER, current="1.9.0")
        st = autoupdate.pending()
        assert autoupdate.startup_status(current="9.0.0")["result"] == "updated"
        for v in ("9.0.0", "1.9.0"):                                  # o novo e o caminho de volta
            assert os.path.exists(autoupdate._installer_path(v))
        assert st and autoupdate.rollback_target() == "1.9.0"
        # a 9.0.0 não chega a abrir duas vezes seguidas: à terceira volta à 1.9.0
        mode = autoupdate.INSTALLER
        assert autoupdate.begin_start("9.0.0", mode) is None
        assert autoupdate.begin_start("9.0.0", mode) is None
        assert autoupdate.begin_start("9.0.0", mode) == "rollback"
        calls = []
        assert autoupdate.rollback(launcher=lambda p, a, e: calls.append((p, a)) or True, folder=folder,
                                   current="9.0.0")
        assert calls[0][0] == autoupdate._installer_path("1.9.0")
        assert autoupdate.RELAUNCH_ARG in calls[0][1] and "/SILENT" in calls[0][1]
        assert "9.0.0" in autoupdate.bad_versions() and not autoupdate.can_roll_back("9.0.0", mode)
        assert not autoupdate.rollback(launcher=lambda p, a, e: True, folder=folder, current="9.0.0")   # só uma vez
        # a 1.9.0 abre: avisa uma vez e limpa; a 9.0.0 nunca mais se instala sozinha
        assert autoupdate.begin_start("1.9.0", mode) is None
        assert autoupdate.rollback_notice("1.9.0") == {"bad": "9.0.0", "version": "1.9.0"}
        assert autoupdate.rollback_notice("1.9.0") is None
        autoupdate.mark_started_ok("1.9.0")
        assert not os.path.exists(os.path.join(autoupdate.rollback_dir(), autoupdate.ROLLBACK))
        assert os.path.exists(autoupdate._installer_path("1.9.0"))
        assert not os.path.exists(autoupdate._installer_path("9.0.0"))
    _clean_rollback()


def test_a_version_that_opens_keeps_only_its_installer_and_is_never_rolled_back():
    _clean_rollback()
    with _Key():
        autoupdate._prepare_rollback("9.0.0", autoupdate.INSTALLER, current="1.9.0")
        assert autoupdate.begin_start("9.0.0", autoupdate.INSTALLER) is None
        autoupdate.mark_started_ok("9.0.0")                       # a janela abriu (ou fechou normalmente)
        for _ in range(4):
            assert autoupdate.begin_start("9.0.0", autoupdate.INSTALLER) is None
        assert not autoupdate.can_roll_back("9.0.0", autoupdate.INSTALLER)
        # uma versão instalada à mão (sem actualização automática) nunca volta atrás
        _clean_rollback()
        for _ in range(4):
            assert autoupdate.begin_start("9.0.0", autoupdate.INSTALLER) is None
    _clean_rollback()


def test_rollback_downloads_the_previous_installer_when_it_was_not_kept():
    _clean_rollback()
    old_setup = _setup_file(b"instalador 1.9.0")
    sig = autoupdate.make_signature(SECRET, old_setup, "1.9.0")
    rel = {"tag_name": "v1.9.0", "html_url": "h", "body": "",
           "assets": [{"name": "Setup_RootsAutoDoctor_1.9.0.exe", "browser_download_url": "https://dl/old.exe"},
                      {"name": "Setup_RootsAutoDoctor_1.9.0.exe.sig", "browser_download_url": "https://dl/old.sig"}]}
    with open(old_setup, "rb") as fh:
        data = fh.read()
    files = {updates.API + "/releases/tags/v1.9.0": json.dumps(rel).encode(), "https://dl/old.exe": data,
             "https://dl/old.sig": json.dumps(sig).encode()}
    with _Key():
        autoupdate._prepare_rollback("9.0.0", autoupdate.INSTALLER, current="1.9.0")
        calls = []
        assert autoupdate.rollback(launcher=lambda p, a, e: calls.append(p) or True, folder=tempfile.mkdtemp(),
                                   opener=_opener(files), current="9.0.0")
        assert calls == [autoupdate._installer_path("1.9.0")]
        # instalador trocado no GitHub: recusado, nada corre
        _clean_rollback()
        autoupdate._prepare_rollback("9.0.0", autoupdate.INSTALLER, current="1.9.0")
        files["https://dl/old.exe"] = b"outro ficheiro"
        assert not autoupdate.rollback(launcher=lambda p, a, e: calls.append(p) or True, folder=tempfile.mkdtemp(),
                                       opener=_opener(files), current="9.0.0")
        assert len(calls) == 1
    _clean_rollback()


def test_portable_copy_goes_back_to_the_copy_kept_before_updating():
    _clean_rollback()
    with _Key():
        autoupdate._prepare_rollback("9.0.0", autoupdate.PORTABLE, current="1.9.0")
        app = tempfile.mkdtemp()
        calls = []
        assert not autoupdate.rollback(launcher=lambda p, a, e: calls.append(p) or True, folder=app,
                                       current="9.0.0")                # sem cópia guardada: não faz nada
        _clean_rollback()
        autoupdate._prepare_rollback("9.0.0", autoupdate.PORTABLE, current="1.9.0")
        old = os.path.join(autoupdate.rollback_dir(), autoupdate.BACKUP)
        os.makedirs(old)
        with open(os.path.join(old, "RootsAutoDoctor.exe"), "w") as fh:
            fh.write("1.9.0")
        assert autoupdate.rollback(launcher=lambda p, a, e: calls.append(p) or True, folder=app, pid=4321,
                                   current="9.0.0")
        text = open(calls[-1], encoding="utf-8").read()
        assert f'set "OLD={old}"' in text and f'set "APP={app}"' in text and 'set "PID=4321"' in text
        assert open(calls[-1], "rb").read().count(b"\r\n") > 10
        autoupdate.mark_started_ok("1.9.0")                          # voltou e abriu: a cópia já não faz falta
        assert not os.path.exists(old)
    _clean_rollback()


def test_downloaded_version_that_was_withdrawn_is_forgotten_not_installed():
    autoupdate.clear()
    path = _setup_file()
    info, opener = _info(autoupdate.make_signature(SECRET, path, "9.0.0"))
    _with_key(lambda: autoupdate.download(info, opener=opener, current="1.9.0"))
    assert not autoupdate.forget_withdrawn("9.0.0") and autoupdate.pending()     # continua publicada
    assert not autoupdate.forget_withdrawn("lixo") and autoupdate.pending()
    assert autoupdate.forget_withdrawn("8.0.0") and autoupdate.pending() is None  # retirada: a publicada é a 8.0.0
    assert not _with_key(lambda: autoupdate.install_pending(launcher=lambda p, a, e: True,
                                                            folder=tempfile.mkdtemp()))
