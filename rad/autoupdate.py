"""Actualizações automáticas: descarrega a versão nova em segundo plano e instala-a quando o programa fecha.

Fluxo (só no programa compilado, com chave de actualizações configurada):
  1. rad/updates.py diz que há uma versão nova no GitHub, com o instalador, a versão portátil e as assinaturas
     (.sig) anexados.
  2. download() descarrega o ficheiro certo para esta cópia (o instalador na versão instalada, o zip na versão
     portátil) e a assinatura para %APPDATA%\\RootsAutoDoctor\\actualizacoes e verifica-a: SHA-256 do ficheiro +
     versão, assinados com a chave privada do fornecedor (Ed25519). Um ficheiro trocado ou corrompido é apagado e
     nunca corre.
  3. Instala-se sem o cliente fazer nada: logo que acaba de descarregar, se o cliente ainda não começou a trabalhar
     (a janela fecha, actualiza e volta a abrir); senão ao fechar o programa; e, se ficou por instalar, ao abrir o
     programa da vez seguinte, antes da janela (install_on_start). install_pending() volta a verificar o ficheiro e:
     - versão instalada: corre o instalador em silêncio (/VERYSILENT, com registo em instalacao.log). Se a pasta
       do programa não for gravável, o Windows pede autorização de administrador uma vez;
     - versão portátil: extrai o zip para uma pasta à parte e lança um script que espera que o programa feche,
       guarda uma cópia da versão actual, copia a nova por cima e, se a cópia falhar, repõe a anterior.
     Com "Actualizar agora" o programa volta a abrir no fim.
  4. No arranque seguinte, startup_status() diz se correu bem (a versão mudou: limpa a pasta) ou se a instalação
     não terminou (o programa continua na versão anterior e avisa uma vez; tenta outra vez ao fechar, até
     MAX_ATTEMPTS vezes).

As actualizações são sempre automáticas (não há opção para as desligar). Uma cópia portátil numa pasta só de
leitura também se actualiza: o Windows pede autorização de administrador. O código-fonte nunca se instala sozinho.
Este módulo não usa Qt, para poder ser testado sem janela nem rede."""
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

from . import APP_NAME, VERSION, ed25519
from .i18n import tr
from .updates import TIMEOUT, UpdateError, is_newer, parse_version

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3                     # instalações tentadas (ex.: autorização recusada) antes de desistir
SILENT_ARGS = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/CLOSEAPPLICATIONS"]
# Ao abrir o programa (o cliente está à espera): /SILENT mostra só a barra de progresso da instalação, sem perguntas.
VISIBLE_ARGS = ["/SILENT"] + SILENT_ARGS[1:]
_STATE = "pendente.json"
LOG_NAME = "instalacao.log"          # registo da última instalação (vai no pacote de suporte)
STAGING = "nova_versao"              # versão portátil: zip extraído, à espera de ser copiado
BACKUP = "versao_anterior"           # versão portátil: cópia da versão actual, para repor se a cópia falhar
SCRIPT = "aplicar_actualizacao.bat"
EXE_NAME = "RootsAutoDoctor.exe"
SETTLE_SECONDS = 180                 # depois de lançar a instalação, tempo em que ainda pode estar a decorrer
INSTALLER, PORTABLE = "installer", "portable"


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


def update_mode(installed=None, frozen=None, folder=None, platform=None):
    """Como se actualiza esta cópia: INSTALLER (versão instalada), PORTABLE (versão portátil numa pasta gravável)
    ou None (código-fonte, pasta só de leitura, sem chave de actualizações ou fora do Windows: só avisa)."""
    if (platform or sys.platform) != "win32" or not public_key():
        return None
    from .j2534 import is_frozen
    installed = is_installed() if installed is None else installed
    if installed:
        return INSTALLER
    frozen = is_frozen() if frozen is None else frozen
    if frozen and os.path.isdir(folder or app_dir()):     # pasta só de leitura: pede autorização ao Windows
        return PORTABLE
    return None


def can_self_update(installed=None):
    """True quando a versão nova pode ser instalada sozinha (versão instalada ou portátil)."""
    return update_mode(installed) is not None


def assets_for(info, mode):
    """(ficheiro, assinatura) a descarregar para este modo, ou (None, None)."""
    if mode == PORTABLE:
        return info.get("portable"), info.get("portable_signature")
    if mode == INSTALLER:
        return info.get("download"), info.get("signature")
    return None, None


def downloadable(info, mode=None):
    """True se a release tem o ficheiro assinado de que esta cópia precisa para se actualizar sozinha."""
    mode = update_mode() if mode is None else mode
    url, sig = assets_for(info, mode)
    return bool(url and sig)


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


def log_path():
    return os.path.join(updates_dir(), LOG_NAME)


def clear(keep_log=False):
    """Apaga a actualização pendente e os ficheiros descarregados (e o registo da instalação, salvo keep_log)."""
    folder = updates_dir()
    for name in os.listdir(folder):
        if keep_log and name == LOG_NAME:
            continue
        path = os.path.join(folder, name)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
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


def download(info, opener=None, progress=None, current=VERSION, mode=INSTALLER):
    """Descarrega e verifica a versão nova (o instalador, ou o zip com mode=PORTABLE). Devolve o estado pendente
    ({"version", "path", "mode", "notes", ...}). Lança UpdateError se não houver ficheiro/assinatura ou se a
    assinatura não bater certo."""
    opener = opener or urllib.request.urlopen
    version = info.get("version", "")
    if not is_newer(version, current):
        raise UpdateError(tr("Já tem a versão mais recente ({VERSION}).", VERSION=current))
    url, sig_url = assets_for(info, mode)
    if not url or not sig_url:
        raise UpdateError(tr("A versão {version} não tem instalador assinado: actualize à mão.", version=version))
    st = pending()
    if (st and st["version"] == version and st.get("mode", INSTALLER) == mode and os.path.exists(st["path"])
            and verify_file(st["path"], st["sig"], version)):
        return st                                            # já descarregada numa sessão anterior
    clear()
    folder = updates_dir()
    name = (f"RootsAutoDoctor_{version}_portatil.zip" if mode == PORTABLE
            else f"Setup_RootsAutoDoctor_{version}.exe")
    try:
        sig = json.loads(_fetch(sig_url, opener).decode("utf-8"))
        path = os.path.join(folder, name)
        _fetch(url, opener, dest=path, progress=progress)
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
    st = {"version": version, "path": path, "sig": sig, "attempts": 0, "mode": mode,
          "notes": info.get("notes") or ""}
    if mode == PORTABLE:                                     # extrai já (em segundo plano), não ao fechar
        try:
            st["staging"] = extract_portable(path)
        except (UpdateError, OSError, zipfile.BadZipFile) as e:
            clear()
            if isinstance(e, UpdateError):
                raise
            raise UpdateError(tr("A versão portátil descarregada está danificada.")) from e
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
        params = subprocess.list2cmdline(args)             # caminhos com espaços (registo da instalação)
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", path, params, None, 0)
        return rc > 32                                       # ≤ 32 = erro (ex.: autorização recusada)
    flags = 0x00000008 | 0x00000200                          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([path] + args, creationflags=flags, close_fds=True)
    return True


def _launch_script(path, args, elevate):
    """Corre o script da versão portátil sem janela, fora deste processo. elevate: a pasta do programa não é
    gravável (ex.: dentro de "Programas"), o Windows pede autorização de administrador."""
    if elevate:
        import ctypes
        params = "/c " + subprocess.list2cmdline([path] + list(args))
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", params, None, 0)
        return rc > 32                                       # ≤ 32 = erro (ex.: autorização recusada)
    flags = 0x08000000 | 0x00000200                          # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(["cmd.exe", "/c", path] + args, creationflags=flags, close_fds=True)
    return True


RELAUNCH_ARG = "/RELAUNCH=1"          # o instalador volta a abrir o programa no fim (installer/RootsAutoDoctor.iss)


# ------------------------------------------------------------------ versão portátil
def _portable_top(zip_path):
    """Pasta de topo do zip portátil que tem o programa. Recusa zips com caminhos para fora da pasta."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
    except (OSError, zipfile.BadZipFile) as e:
        raise UpdateError(tr("A versão portátil descarregada está danificada.")) from e
    for n in names:
        parts = n.replace("\\", "/").split("/")
        if n.startswith(("/", "\\")) or ":" in n or ".." in parts:
            raise UpdateError(tr("A versão portátil descarregada está danificada."))
    tops = {n.split("/", 1)[0] for n in names if n.lower().endswith("/" + EXE_NAME.lower()) and n.count("/") == 1}
    if len(tops) != 1:
        raise UpdateError(tr("A versão portátil descarregada está danificada."))
    return tops.pop()


def extract_portable(zip_path, dest=None):
    """Extrai o zip verificado para a pasta de espera e devolve a pasta com o programa novo."""
    top = _portable_top(zip_path)
    dest = dest or os.path.join(updates_dir(), STAGING)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest)
    new = os.path.join(dest, top)
    if not os.path.isfile(os.path.join(new, EXE_NAME)):
        raise UpdateError(tr("A versão portátil descarregada está danificada."))
    return new


SCRIPT_TEMPLATE = r"""@echo off
chcp 65001 >nul
REM Roots Auto Doctor: aplica a versao portatil {version} depois de o programa fechar.
set "PID={pid}"
set "APP={app}"
set "NEW={new}"
set "OLD={old}"
set "LOG={log}"
set /a N=0
echo %DATE% %TIME% a espera que o programa feche (processo %PID%)>>"%LOG%"
:wait
tasklist /FI "PID eq %PID%" /NH 2>nul | find " %PID% " >nul
if errorlevel 1 goto closed
set /a N+=1
if %N% GEQ 120 goto busy
ping -n 2 127.0.0.1 >nul
goto wait
:closed
if exist "%OLD%" rd /s /q "%OLD%"
echo %DATE% %TIME% a guardar a versao actual>>"%LOG%"
robocopy "%APP%" "%OLD%" /E /R:2 /W:1 /NP /NFL /NDL /NJH >>"%LOG%"
if errorlevel 8 goto nobackup
echo %DATE% %TIME% a copiar a versao {version}>>"%LOG%"
robocopy "%NEW%" "%APP%" /E /R:5 /W:2 /NP /NFL /NDL /NJH >>"%LOG%"
if errorlevel 8 goto rollback
echo %DATE% %TIME% RESULTADO: ok>>"%LOG%"
REM a copia da versao anterior fica ate a versao nova abrir bem (para voltar atras se nao abrir)
rd /s /q "%NEW%"
goto done
:rollback
echo %DATE% %TIME% a copia falhou: a repor a versao anterior>>"%LOG%"
robocopy "%OLD%" "%APP%" /E /R:5 /W:2 /NP /NFL /NDL /NJH >>"%LOG%"
echo %DATE% %TIME% RESULTADO: falhou (versao anterior reposta)>>"%LOG%"
goto done
:nobackup
echo %DATE% %TIME% RESULTADO: falhou (nao foi possivel guardar a versao actual; nada foi alterado)>>"%LOG%"
goto done
:busy
echo %DATE% %TIME% RESULTADO: falhou (o programa nao fechou)>>"%LOG%"
:done
if not "{relaunch}"=="1" goto end
REM com autorizacao de administrador, o explorer abre o programa como o utilizador normal
if "{elevated}"=="1" (start "" explorer.exe "%APP%\{exe}") else (start "" "%APP%\{exe}")
:end
"""


def portable_script(version, pid, app, new, folder=None, relaunch=False, elevated=False, backup=None):
    """Escreve o script que aplica a versão portátil e devolve o caminho. backup: onde fica a cópia da versão
    actual (por omissão na pasta do script)."""
    folder = folder or updates_dir()
    text = SCRIPT_TEMPLATE.format(version=version, pid=int(pid), app=os.path.abspath(app),
                                  new=os.path.abspath(new), old=backup or os.path.join(folder, BACKUP),
                                  log=os.path.join(folder, LOG_NAME), relaunch="1" if relaunch else "0",
                                  elevated="1" if elevated else "0", exe=EXE_NAME)
    path = os.path.join(folder, SCRIPT)
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text)
    return path


def install_pending(launcher=None, folder=None, relaunch=False, pid=None, visible=False):
    """Chamado ao fechar o programa. Instala a versão descarregada, se houver e se ainda for válida.
    relaunch=True: o programa volta a abrir já actualizado. visible=True: o instalador mostra a barra de progresso
    (o cliente está à espera que o programa abra). Devolve True se a instalação foi lançada."""
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
    st["launched_at"] = time.time()
    st["from"] = VERSION
    st["launched"] = False
    _save(st)
    folder = folder or app_dir()
    try:
        if os.path.exists(log_path()):
            os.remove(log_path())
    except OSError:
        pass
    try:
        if st.get("mode") == PORTABLE:
            new = st.get("staging")
            if not new or not os.path.isfile(os.path.join(new, EXE_NAME)):
                new = extract_portable(st["path"])
            elevate = not _writable(folder)
            _prepare_rollback(version, PORTABLE)
            script = portable_script(version, pid or os.getpid(), folder, new, relaunch=relaunch, elevated=elevate,
                                     backup=os.path.join(rollback_dir(), BACKUP))
            ok = (launcher or _launch_script)(script, [], elevate)
        else:
            elevate = not _writable(folder)
            _prepare_rollback(version, INSTALLER)
            args = (list(VISIBLE_ARGS if visible else SILENT_ARGS) + [f"/LOG={log_path()}"]
                    + ([RELAUNCH_ARG] if relaunch else []))
            ok = (launcher or _launch)(st["path"], args, elevate)
    except Exception:
        log.exception("Não foi possível lançar a instalação da versão %s", version)
        return False
    st["launched"] = bool(ok)
    _save(st)
    log.info("Instalação da versão %s lançada (%s, administrador: %s, tentativa %d)", version,
             st.get("mode", INSTALLER), elevate, st["attempts"])
    return bool(ok)


def forget_withdrawn(latest_version):
    """A versão descarregada deixou de estar publicada (retirada pelo fornecedor, ou era uma versão de teste e o
    canal mudou): apaga-a em vez de a instalar. True se apagou."""
    st = pending()
    if st and parse_version(latest_version) and is_newer(st.get("version", ""), latest_version):
        log.warning("A versão %s descarregada já não está publicada (a mais recente é %s): apagada",
                    st.get("version"), latest_version)
        clear(keep_log=True)
        return True
    return False


def ready_on_start(mode=None):
    """A versão nova já descarregada que se instala logo ao abrir o programa (antes da janela), ou None.
    Só na primeira tentativa: se uma instalação anterior não terminou, o programa abre normalmente e volta a tentar
    ao fechar (assim o cliente nunca fica preso num programa que fecha sempre ao abrir)."""
    mode = update_mode() if mode is None else mode
    st = pending()
    if not mode or not st or st.get("attempts", 0) or st.get("mode", INSTALLER) != mode:
        return None
    if not is_newer(st.get("version", "")) or st.get("version") in bad_versions():
        return None
    return st


def install_on_start(launcher=None, folder=None, pid=None, mode=None):
    """Instala já a versão descarregada (ver ready_on_start) e volta a abrir o programa no fim. True se lançou:
    nesse caso o programa deve sair logo."""
    if not ready_on_start(mode):
        return False
    log.info("Versão descarregada encontrada ao abrir: a instalar antes de abrir a janela")
    return install_pending(launcher, folder, relaunch=True, pid=pid, visible=True)


def startup_status(current=VERSION, now=None):
    """No arranque, o resultado da última actualização (ou None se não há nada a dizer):
      {"result": "updated", "version", "notes"}           correu bem: a pasta de descargas é limpa
      {"result": "failed", "version", "denied", "gave_up"}  a instalação não terminou; o programa continua na
                                                           versão actual. gave_up: desistiu (limpa, fica o registo)
    Cada falha é dita uma só vez. Logo a seguir a lançar a instalação (SETTLE_SECONDS) não diz nada: pode estar
    ainda a decorrer."""
    st = pending()
    if not st:
        return None
    version = st.get("version", "")
    if parse_version(version) == parse_version(current):
        if st.get("mode", INSTALLER) == INSTALLER:     # guarda-o: é o caminho de volta se a próxima falhar
            previous = (_read(ROLLBACK) or {}).get("previous")
            _keep_installer(st.get("path"), st.get("sig"), version, keep=[previous] if previous else [])
        clear()
        return {"result": "updated", "version": version, "notes": st.get("notes") or ""}
    if not is_newer(version, current):
        clear()
        return None
    attempts = st.get("attempts", 0)
    now = time.time() if now is None else now
    if not attempts or st.get("reported") == attempts or now - st.get("launched_at", 0) < SETTLE_SECONDS:
        return None
    gave_up = attempts >= MAX_ATTEMPTS
    res = {"result": "failed", "version": version, "denied": not st.get("launched", True), "gave_up": gave_up}
    log.warning("A actualização para %s não terminou (tentativa %d%s)", version, attempts,
                ", desistiu" if gave_up else "")
    if gave_up:
        clear(keep_log=True)
    else:
        st["reported"] = attempts
        _save(st)
    return res


def after_start(current=VERSION):
    """A versão nova se a última actualização correu bem, senão None (ver startup_status)."""
    st = startup_status(current)
    return st["version"] if st and st["result"] == "updated" else None


# ------------------------------------------------------------------ voltar à versão anterior
# Se uma versão nova, instalada por uma actualização automática, não chega a abrir neste PC, o programa volta
# sozinho à versão que estava antes e não volta a instalar essa versão (a seguinte instala-se normalmente).
#   begin_start()        no main.py, antes da janela: conta os arranques desta versão que não chegaram ao fim
#   mark_started_ok()    a janela abriu e o programa está a funcionar (HEALTHY_SECONDS) ou fechou normalmente
#   rollback()           repõe a versão anterior: na versão instalada corre o instalador dessa versão (guardado da
#                        actualização anterior ou descarregado do GitHub, sempre com a assinatura verificada); na
#                        portátil copia de volta a cópia que o script guardou antes de actualizar.
HEALTH = "arranque.json"
ROLLBACK = "reposicao.json"
BAD = "versoes_recusadas.json"
NOTICE = "aviso_reposicao.json"
ROLLBACK_SCRIPT = "repor_versao_anterior.bat"
FAILED_STARTS = 2                    # arranques seguidos sem abrir a janela antes de voltar à versão anterior
HEALTHY_SECONDS = 20                 # janela aberta há este tempo: a versão funciona neste PC


def rollback_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor", "reposicao")
    os.makedirs(path, exist_ok=True)
    return path


def _read(name, default=None):
    try:
        with open(os.path.join(rollback_dir(), name), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write(name, obj):
    path = os.path.join(rollback_dir(), name)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(obj, fh)
    os.replace(path + ".tmp", path)


def _remove(name):
    path = os.path.join(rollback_dir(), name)
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
    except OSError:
        log.warning("Não foi possível apagar %s", path, exc_info=True)


def bad_versions():
    """Versões que não abriram neste PC: nunca mais se instalam sozinhas."""
    return set(_read(BAD, []) or [])


def _installer_path(version):
    return os.path.join(rollback_dir(), f"Setup_RootsAutoDoctor_{version}.exe")


def _keep_installer(path, sig, version, keep=()):
    """Guarda o instalador da versão que ficou instalada (e a assinatura) e apaga os outros, salvo os de keep."""
    try:
        if path and os.path.exists(path) and verify_file(path, sig, version):
            shutil.copyfile(path, _installer_path(version))
            _write(os.path.basename(_installer_path(version)) + ".sig", sig)
        _prune_installers({version, *keep})
    except OSError:
        log.warning("Não foi possível guardar o instalador da versão %s", version, exc_info=True)


def _prune_installers(keep):
    names = {os.path.basename(_installer_path(v)) for v in keep}
    for name in os.listdir(rollback_dir()):
        if name.startswith("Setup_RootsAutoDoctor_") and name.replace(".sig", "") not in names:
            _remove(name)


def _kept_installer(version):
    """(caminho, assinatura) do instalador guardado de uma versão, se ainda estiver bom."""
    path = _installer_path(version)
    sig = _read(os.path.basename(path) + ".sig")
    if os.path.exists(path) and verify_file(path, sig, version):
        return path, sig
    return None, None


def _prepare_rollback(version, mode, current=VERSION):
    """Antes de instalar: lembra de onde vem, para poder voltar se a versão nova não abrir."""
    try:
        _write(ROLLBACK, {"version": version, "previous": current, "mode": mode})
    except OSError:
        log.warning("Não foi possível guardar o caminho de volta", exc_info=True)


def begin_start(current=VERSION, mode=None):
    """No arranque, antes da janela. Devolve "rollback" quando esta versão veio de uma actualização automática e os
    últimos FAILED_STARTS arranques não chegaram a abrir a janela."""
    try:
        h = _read(HEALTH, {}) or {}
        if h.get("version") != current:
            h = {"version": current, "failed": 0}
        elif h.get("open"):                              # o arranque anterior não chegou ao fim
            h["failed"] = h.get("failed", 0) + 1
        h["open"] = True
        _write(HEALTH, h)
        rb = _read(ROLLBACK) or {}
        if (rb.get("version") == current and not rb.get("rolled_back") and h["failed"] >= FAILED_STARTS
                and (mode or update_mode())):
            log.error("A versão %s não abriu %d vezes seguidas: a voltar à %s", current, h["failed"],
                      rb.get("previous"))
            return "rollback"
    except OSError:
        log.warning("Contagem de arranques falhou", exc_info=True)
    return None


def can_roll_back(current=VERSION, mode=None):
    """True se esta versão veio de uma actualização automática e ainda há caminho de volta."""
    rb = _read(ROLLBACK) or {}
    return bool(rb.get("version") == current and not rb.get("rolled_back") and rb.get("previous")
                and (mode or update_mode()))


def rollback_target():
    """A versão para onde se volta, se a actual não abrir (ou None)."""
    return (_read(ROLLBACK) or {}).get("previous")


def mark_started_ok(current=VERSION):
    """A versão abriu e funciona: esquece a contagem e apaga o que só servia para voltar atrás (fica o instalador
    desta versão, para a próxima actualização)."""
    try:
        _write(HEALTH, {"version": current, "failed": 0, "open": False})
        rb = _read(ROLLBACK) or {}
        if rb and (rb.get("version") == current or rb.get("rolled_back")):
            _remove(BACKUP)
            _prune_installers({current})
            _remove(ROLLBACK)
    except OSError:
        log.warning("Não foi possível marcar o arranque como bom", exc_info=True)


def _previous_installer(version, opener=None):
    """Instalador da versão anterior: o guardado, ou descarregado da release dessa versão (assinatura verificada)."""
    path, sig = _kept_installer(version)
    if path:
        return path
    from .updates import release_for
    info = release_for(version, opener)
    if not info or not info.get("download") or not info.get("signature"):
        return None
    opener = opener or urllib.request.urlopen
    path = _installer_path(version)
    try:
        sig = json.loads(_fetch(info["signature"], opener).decode("utf-8"))
        _fetch(info["download"], opener, dest=path)
    except (OSError, ValueError):
        log.warning("Não foi possível descarregar o instalador da versão %s", version, exc_info=True)
        return None
    if not verify_file(path, sig, version):
        _remove(os.path.basename(path))
        log.error("Instalador da versão %s recusado: a assinatura não corresponde", version)
        return None
    _write(os.path.basename(path) + ".sig", sig)
    return path


ROLLBACK_TEMPLATE = r"""@echo off
chcp 65001 >nul
REM Roots Auto Doctor: volta a versao {previous} porque a {version} nao abriu neste computador.
set "PID={pid}"
set "APP={app}"
set "OLD={old}"
set "LOG={log}"
set /a N=0
echo %DATE% %TIME% a voltar a versao {previous} (processo %PID%)>>"%LOG%"
:wait
tasklist /FI "PID eq %PID%" /NH 2>nul | find " %PID% " >nul
if errorlevel 1 goto closed
set /a N+=1
if %N% GEQ 120 goto busy
ping -n 2 127.0.0.1 >nul
goto wait
:closed
robocopy "%OLD%" "%APP%" /E /R:5 /W:2 /NP /NFL /NDL /NJH >>"%LOG%"
if errorlevel 8 (echo %DATE% %TIME% RESULTADO: falhou>>"%LOG%") else (echo %DATE% %TIME% RESULTADO: ok>>"%LOG%")
goto done
:busy
echo %DATE% %TIME% RESULTADO: falhou (o programa nao fechou)>>"%LOG%"
:done
if "{elevated}"=="1" (start "" explorer.exe "%APP%\{exe}") else (start "" "%APP%\{exe}")
"""


def rollback(launcher=None, folder=None, pid=None, opener=None, current=VERSION):
    """Volta à versão anterior (ver begin_start) e abre-a no fim. Esta versão fica recusada neste PC.
    True se a reposição foi lançada (o programa deve sair já)."""
    rb = _read(ROLLBACK) or {}
    if rb.get("version") != current or rb.get("rolled_back") or not rb.get("previous"):
        return False
    previous, mode = rb["previous"], rb.get("mode", INSTALLER)
    folder = folder or app_dir()
    _write(BAD, sorted(bad_versions() | {current}))
    clear()                                              # o que estiver descarregado desta versão já não serve
    elevate = not _writable(folder)
    try:
        if mode == PORTABLE:
            old = os.path.join(rollback_dir(), BACKUP)
            if not os.path.isfile(os.path.join(old, EXE_NAME)):
                log.error("Sem a cópia da versão %s: não é possível voltar atrás", previous)
                return False
            script = os.path.join(updates_dir(), ROLLBACK_SCRIPT)
            with open(script, "w", encoding="utf-8", newline="\r\n") as fh:
                fh.write(ROLLBACK_TEMPLATE.format(previous=previous, version=current, pid=int(pid or os.getpid()),
                                                  app=os.path.abspath(folder), old=old,
                                                  log=os.path.join(updates_dir(), LOG_NAME),
                                                  elevated="1" if elevate else "0", exe=EXE_NAME))
            ok = (launcher or _launch_script)(script, [], elevate)
        else:
            path = _previous_installer(previous, opener)
            if not path:
                log.error("Sem o instalador da versão %s: não é possível voltar atrás", previous)
                return False
            args = VISIBLE_ARGS + [f"/LOG={log_path()}", RELAUNCH_ARG]
            ok = (launcher or _launch)(path, args, elevate)
    except Exception:
        log.exception("Não foi possível voltar à versão %s", previous)
        return False
    if ok:
        _write(ROLLBACK, dict(rb, rolled_back=True))
        _write(NOTICE, {"bad": current, "version": previous})
    return bool(ok)


def rollback_notice(current=VERSION):
    """{"bad", "version"} uma vez, no primeiro arranque depois de voltar à versão anterior; senão None."""
    notice = _read(NOTICE)
    if not notice:
        return None
    if notice.get("version") != current:                 # a reposição ainda não terminou (ou falhou)
        return None
    _remove(NOTICE)
    return notice
