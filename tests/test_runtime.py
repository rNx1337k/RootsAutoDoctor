"""Python portátil das pontes (runtime/): noutro PC não pode ser preciso instalar um Python de 32 bits."""
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import get_runtime  # noqa: E402
from rad import j2534  # noqa: E402


def _fake_runtime(bits):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, f"py{bits}"))
    open(os.path.join(d, f"py{bits}", "python.exe"), "wb").close()
    return d


def _no_py_launcher(fn):
    real = subprocess.run

    def blocked(cmd, *a, **k):
        if cmd and str(cmd[0]).lower() in ("py", "py.exe"):
            raise FileNotFoundError("sem lançador py")
        return real(cmd, *a, **k)
    subprocess.run = blocked
    try:
        return fn()
    finally:
        subprocess.run = real


def test_bundled_runtime_is_used_without_system_python():
    d = _fake_runtime(32)
    old_env, old_frozen = os.environ.get("RAD_RUNTIME_DIR"), j2534.is_frozen
    os.environ["RAD_RUNTIME_DIR"] = d
    try:
        exe = _no_py_launcher(lambda: j2534.find_python(32))
        assert exe == os.path.join(d, "py32", "python.exe")
        j2534.is_frozen = lambda: True                 # programa compilado: nunca o próprio .exe
        try:
            _no_py_launcher(lambda: j2534.find_python(64))
            assert False, "sem runtime/py64 devia falhar"
        except Exception as e:
            assert "py64" in str(e) and "instalar" in str(e)
    finally:
        j2534.is_frozen = old_frozen
        if old_env is None:
            os.environ.pop("RAD_RUNTIME_DIR", None)
        else:
            os.environ["RAD_RUNTIME_DIR"] = old_env


def test_source_mode_uses_own_python_for_same_bits():
    import struct
    mine = struct.calcsize("P") * 8
    assert os.path.samefile(j2534.find_python(mine), j2534._python_console(sys.executable))


def _zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("python.exe", b"MZ")
        z.writestr("python313._pth", "python313.zip\n.\n")
    return buf.getvalue()


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _with_download(data, fn):
    import urllib.request
    real = urllib.request.urlopen
    urllib.request.urlopen = lambda url, timeout=None: _Resp(data)
    try:
        return fn()
    finally:
        urllib.request.urlopen = real


def test_get_runtime_verifies_hash_and_installs():
    data = _zip_bytes()
    dest = tempfile.mkdtemp()
    old = dict(get_runtime.FILES)
    get_runtime.FILES["py32"] = ("win32", hashlib.sha256(data).hexdigest())
    try:
        folder = _with_download(data, lambda: get_runtime.install("py32", dest, log=lambda m: None))
        assert get_runtime.is_ready(folder)
        assert os.path.exists(os.path.join(folder, "python.exe"))
        # segunda vez não descarrega
        _with_download(b"", lambda: get_runtime.install("py32", dest, log=lambda m: None))
        # ficheiro adulterado: recusado e nada fica instalado
        get_runtime.FILES["py32"] = ("win32", "0" * 64)
        dest2 = tempfile.mkdtemp()
        try:
            _with_download(data, lambda: get_runtime.install("py32", dest2, log=lambda m: None))
            assert False, "hash errado devia ser recusado"
        except RuntimeError as e:
            assert "SHA-256" in str(e)
        assert not os.path.exists(os.path.join(dest2, "py32"))
    finally:
        get_runtime.FILES.clear()
        get_runtime.FILES.update(old)


def test_pinned_hashes_look_valid():
    for name, (arch, sha) in get_runtime.FILES.items():
        assert arch in ("win32", "amd64") and len(sha) == 64 and int(sha, 16) >= 0, name


def test_selftest_runs_both_bridges():
    from rad import selftest
    ok, lines = selftest.run()
    text = "\n".join(lines)
    assert ok, text
    assert "Ponte J2534 (simulador)" in text and "Ponte D2XX (simulador)" in text and "tudo OK" in text


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
