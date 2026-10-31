"""Actualizações automáticas: descarrega a versão nova em segundo plano e instala-a quando o programa fecha.

Fluxo (só na versão instalada e compilada, com chave de actualizações configurada):
  1. rad/updates.py diz que há uma versão nova no GitHub, com o instalador e a assinatura (.sig) anexados.
  2. download() descarrega os dois para %APPDATA%\\RootsAutoDoctor\\actualizacoes e verifica a assinatura:
     SHA-256 do instalador + versão, assinados com a chave privada do fornecedor (Ed25519). Um ficheiro trocado
     ou corrompido é apagado e nunca corre.
  3. Ao fechar o programa, install_pending() volta a verificar o ficheiro e corre o instalador em silêncio
     (/VERYSILENT). Se a pasta do programa não for gravável (instalação para todos os utilizadores), o Windows
     pede autorização de administrador uma vez.
  4. No arranque seguinte, after_start() vê que a versão mudou, limpa a pasta e devolve a versão nova (aviso).

A versão portátil e o código-fonte nunca se instalam sozinhos: só avisam (o resto do programa não muda).
Este módulo não usa Qt, para poder ser testado sem janela nem rede."""
import hashlib
import json
import logging
import os
import subprocess
import sys
import urllib.request

from . import APP_NAME, VERSION, ed25519
from .i18n import tr
from .updates import TIMEOUT, UpdateError, is_newer, parse_version

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3                     # instalações tentadas (ex.: autorização recusada) antes de desistir
SILENT_ARGS = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/CLOSEAPPLICATIONS"]
_STATE = "pendente.json"


# ------------------------------------------------------------------ chave e assinatura
def public_key():
    from .update_pubkey import UPDATE_PUBLIC_KEY
    return bytes.fromhex(UPDATE_PUBLIC_KEY) if UPDATE_PUBLIC_KEY else None


def signed_message(version, sha256_hex):
    """O que a assinatura cobre: a versão e o conteúdo exacto do instalador."""
    return f"RAD-UPDATE\n{version}\n{sha256_hex.lower()}\n".encode("ascii")


def make_signature(secret, path, version):
    """Assinatura (.sig, JSON) de um instalador. Usado pelo build (tools/finish_build.py sign)."""
    digest = file_sha256(path)
    sig = ed25519.sign(secret, signed_message(version, digest))
    return {"version": version, "file": os.path.basename(path), "sha256": digest, "signature": sig.hex()}


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_file(path, sig, version, public=None):
    """True só se o ficheiro for exactamente o instalador assinado para esta versão."""
    public = public if public is not None else public_key()
    if not public or not isinstance(sig, dict):
        return False
    try:
        if sig.get("version") != version:
            return False
        digest = file_sha256(path)
        if digest != str(sig.get("sha256", "")).lower():
            return False
        return ed25519.verify(public, signed_message(version, digest), bytes.fromhex(sig.get("signature", "")))
    except (OSError, ValueError):
        return False


# ------------------------------------------------------------------ onde e quando
def updates_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor", "actualizacoes")
    os.makedirs(path, exist_ok=True)
    return path


def app_dir():
    from .j2534 import app_root
    return app_root()


def is_installed(folder=None):
    """Versão instalada pelo instalador (tem o desinstalador do Inno Setup ao lado do .exe)."""
    from .j2534 import is_frozen
    folder = folder or app_dir()
    return is_frozen() and os.path.exists(os.path.join(folder, "unins000.exe"))


def can_self_update(installed=None):
    """True quando a versão nova pode ser instalada sozinha. Na versão portátil, no código-fonte ou sem chave de
    actualizações configurada, o programa só avisa."""
    installed = is_installed() if installed is None else installed
    return bool(installed and public_key() and sys.platform == "win32")


def _state_path():
    return os.path.join(updates_dir(), _STATE)


def pending():
    """{"version", "path", "sig", "attempts"} da actualização descarregada e por instalar, ou None."""
    try:
        with open(_state_path(), encoding="utf-8") as fh:
            st = json.load(fh)
        return st if isinstance(st, dict) and st.get("version") and st.get("path") else None
    except (OSError, ValueError):
        return None


def _save(state):
    tmp = _state_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    os.replace(tmp, _state_path())


def clear():
    """Apaga a actualização pendente e os ficheiros descarregados."""
    folder = updates_dir()
    for name in os.listdir(folder):
        try:
            os.remove(os.path.join(folder, name))
        except OSError:
            log.warning("Não foi possível apagar %s", name, exc_info=True)


# ------------------------------------------------------------------ descarga
def _fetch(url, opener, dest=None, progress=None):
    req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME.replace(' ', '')}/{VERSION}"})
    with opener(req, timeout=max(TIMEOUT, 30)) as resp:
        if dest is None:
            return resp.read(1 << 20)                       # a assinatura é pequena
        total = int(getattr(resp, "headers", {}).get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as fh:
            for block in iter(lambda: resp.read(1 << 16), b""):
                fh.write(block)
                done += len(block)
                if progress:
                    progress(done, total)
    return None


def download(info, opener=None, progress=None, current=VERSION):
    """Descarrega e verifica a versão nova. Devolve o estado pendente ({"version", "path", ...}).
    Lança UpdateError se não houver instalador/assinatura ou se a assinatura não bater certo."""
    opener = opener or urllib.request.urlopen
    version = info.get("version", "")
    if not is_newer(version, current):
        raise UpdateError(tr("Já tem a versão mais recente ({VERSION}).", VERSION=current))
    if not info.get("download") or not info.get("signature"):
        raise UpdateError(tr("A versão {version} não tem instalador assinado: actualize à mão.", version=version))
    st = pending()
    if st and st["version"] == version and os.path.exists(st["path"]) and verify_file(st["path"], st["sig"], version):
        return st                                            # já descarregada numa sessão anterior
    clear()
    folder = updates_dir()
    try:
        sig = json.loads(_fetch(info["signature"], opener).decode("utf-8"))
        path = os.path.join(folder, f"Setup_RootsAutoDoctor_{version}.exe")
        _fetch(info["download"], opener, dest=path, progress=progress)
    except UpdateError:
        raise
    except (OSError, ValueError) as e:
        clear()
        raise UpdateError(tr("Não foi possível descarregar a versão {version}.", version=version)) from e
    if not verify_file(path, sig, version):
        clear()
        log.error("Actualização %s recusada: a assinatura não corresponde ao ficheiro descarregado", version)
        raise UpdateError(tr("A versão {version} descarregada não passou na verificação de segurança e foi "
                             "apagada.", version=version))
    st = {"version": version, "path": path, "sig": sig, "attempts": 0}
    _save(st)
    log.info("Actualização %s descarregada e verificada: %s", version, path)
    return st


# ------------------------------------------------------------------ instalação
def _writable(folder):
    probe = os.path.join(folder, f".rad_escrita_{os.getpid()}")
    try:
        with open(probe, "w") as fh:
            fh.write("x")
        os.remove(probe)
        return True
    except OSError:
        return False


def _launch(path, args, elevate):
    """Corre o instalador fora deste processo (continua depois de o programa fechar)."""
    if elevate:
        import ctypes
        params = " ".join(args)
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", path, params, None, 0)
        return rc > 32                                       # ≤ 32 = erro (ex.: autorização recusada)
    flags = 0x00000008 | 0x00000200                          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([path] + args, creationflags=flags, close_fds=True)
    return True


def install_pending(launcher=None, folder=None):
    """Chamado ao fechar o programa. Instala a versão descarregada, se houver e se ainda for válida.
    Devolve True se o instalador foi lançado."""
    st = pending()
    if not st:
        return False
    version = st["version"]
    if not is_newer(version) or st.get("attempts", 0) >= MAX_ATTEMPTS:
        clear()
        return False
    if not os.path.exists(st["path"]) or not verify_file(st["path"], st.get("sig"), version):
        log.error("Actualização %s pendente inválida no fecho: apagada", version)
        clear()
        return False
    st["attempts"] = st.get("attempts", 0) + 1
    _save(st)
    folder = folder or app_dir()
    elevate = not _writable(folder)
    try:
        ok = (launcher or _launch)(st["path"], list(SILENT_ARGS), elevate)
    except Exception:
        log.exception("Não foi possível lançar o instalador da versão %s", version)
        return False
    log.info("Instalador da versão %s lançado (administrador: %s, tentativa %d)", version, elevate, st["attempts"])
    return bool(ok)


def after_start(current=VERSION):
    """No arranque: se a versão pendente já é a que está a correr, a actualização correu bem — limpa e devolve
    a versão (para avisar o utilizador). Se for antiga, limpa. Caso contrário None."""
    st = pending()
    if not st:
        return None
    version = st.get("version", "")
    if parse_version(version) == parse_version(current):
        clear()
        return version
    if not is_newer(version, current):
        clear()
    return None
