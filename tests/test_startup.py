"""Arranque do programa noutro PC: uma falha antes de a janela abrir tem de ficar registada e ser mostrada.

Os testes correm o main.py num processo à parte com o PySide6 "bloqueado" (sys.modules['PySide6'] = None),
que é o que acontece num PC onde o Qt não carrega. Não abrem janelas nem falam com hardware."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BLOCK_QT = "import sys; sys.modules['PySide6'] = None; sys.path.insert(0, {root!r}); "


def _run(code, appdata):
    env = dict(os.environ, APPDATA=appdata, RAD_SETTINGS_INI=os.path.join(appdata, "s.ini"),
               QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-c", BLOCK_QT.format(root=ROOT) + code], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


def test_main_module_imports_without_qt():
    # importar o main.py não pode depender do Qt: só assim o registo de erros fica activo antes
    out = _run("import main; print('importado')", tempfile.mkdtemp())
    assert out.returncode == 0 and "importado" in out.stdout, out.stderr


def test_startup_failure_is_logged_and_shown():
    appdata = tempfile.mkdtemp()
    code = ("import main; shown = []; main.show_fatal_error = shown.append; sys.argv = ['main.py']; "
            "rc = main.main(); print('rc=%d' % rc); print('MSG=' + shown[0].replace(chr(10), ' | '))")
    out = _run(code, appdata)
    assert out.returncode == 0, out.stderr
    assert "rc=2" in out.stdout, out.stdout
    assert "Não foi possível iniciar" in out.stdout and "crash.log" in out.stdout, out.stdout
    crash = os.path.join(appdata, "RootsAutoDoctor", "registos", "crash.log")
    assert os.path.exists(crash)
    with open(crash, encoding="utf-8") as fh:
        text = fh.read()
    assert "PySide6" in text and "Traceback" in text


def test_selftest_does_not_need_qt():
    # o auto-teste da instalação corre sem Qt (verifica as pontes e o Python portátil)
    appdata = tempfile.mkdtemp()
    report = os.path.join(appdata, "autoteste.txt")
    out = _run(f"import main; sys.argv = ['main.py', '--selftest', {report!r}]; main.main()", appdata)
    assert os.path.exists(report), out.stderr
    with open(report, encoding="utf-8") as fh:
        text = fh.read()
    assert "auto-teste" in text and "OK    Ponte J2534 (simulador)" in text, text


def test_ui_scale_setting_is_applied_at_startup_only_when_valid():
    import tempfile
    from rad import settings
    ini = os.path.join(tempfile.mkdtemp(), "s.ini")
    old = os.environ.get("RAD_SETTINGS_INI")
    os.environ["RAD_SETTINGS_INI"] = ini
    try:
        env = {}
        assert settings.apply_ui_scale(env) is None and "QT_SCALE_FACTOR" not in env      # normal: nada muda
        s = settings.app_settings()
        s.setValue("ui/scale", "1.3")
        s.sync()
        assert settings.apply_ui_scale(env) == "1.3" and env["QT_SCALE_FACTOR"] == "1.3"
        env = {"QT_SCALE_FACTOR": "2"}
        assert settings.apply_ui_scale(env) is None and env["QT_SCALE_FACTOR"] == "2"   # do utilizador: fica
        s.setValue("ui/scale", "9")
        s.sync()
        env = {}
        assert settings.ui_scale() == "1" and settings.apply_ui_scale(env) is None      # valor inválido
    finally:
        if old is None:
            os.environ.pop("RAD_SETTINGS_INI", None)
        else:
            os.environ["RAD_SETTINGS_INI"] = old
