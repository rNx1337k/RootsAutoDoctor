"""Licença por oficina, com ativação offline.

Cada PC tem um código (ID do PC) tirado do identificador do Windows. A oficina envia esse código, o
fornecedor gera uma chave com `tools/license_tool.py issue` e a oficina cola-a em Opções → Licença. A chave
é assinada (Ed25519) com a chave privada do fornecedor; o programa só tem a chave pública, por isso não é
possível fabricar uma licença a partir do programa. Não é precisa internet em nenhum passo.

Sem licença válida o programa funciona em modo demonstração: lê tudo (identificação, avarias, valores de
medição, OBD-II) e o simulador funciona sem limites, mas não escreve em controladores reais (codificação,
adaptação, ajustes básicos, apagar avarias, teste de saídas) e os relatórios saem marcados.

Nota: num programa em Python a verificação pode ser contornada por quem altere o código; a licença serve
para controlar a distribuição normal, não é uma protecção contra cópia determinada."""
import base64
import datetime
import hashlib
import json
import logging
import os
import platform
import uuid

from . import ed25519
from .i18n import tr

log = logging.getLogger(__name__)

PREFIX = "RAD1-"
FILE_NAME = "licenca.txt"
DIRECTORY = None             # pasta alternativa (testes); None = %APPDATA%\RootsAutoDoctor

# Comandos que escrevem no controlador ou no veículo: bloqueados em modo demonstração (fora do simulador).
WRITE_COMMANDS = frozenset({"recode", "adaptation_test", "adaptation_save", "service_reset", "clear_faults",
                            "clear_all", "obd_clear", "output_test", "basic_setting"})


def _public_key():
    from .license_pubkey import PUBLIC_KEY
    return bytes.fromhex(PUBLIC_KEY) if PUBLIC_KEY else None


def _b64e(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64d(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ------------------------------------------------------------------ ID do PC
def _windows_machine_guid():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                             winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0))
        try:
            return str(winreg.QueryValueEx(key, "MachineGuid")[0])
        finally:
            winreg.CloseKey(key)
    except Exception:
        return None


def format_machine_id(raw):
    """Código curto e legível ao telefone: 12 caracteres em 3 grupos (sem 0/O/1/I)."""
    digest = hashlib.sha256(("RootsAutoDoctor|" + raw).encode()).digest()
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    n = int.from_bytes(digest[:10], "big")
    chars = []
    for _ in range(12):
        n, r = divmod(n, len(alphabet))
        chars.append(alphabet[r])
    code = "".join(chars)
    return f"{code[:4]}-{code[4:8]}-{code[8:]}"


def machine_id():
    raw = _windows_machine_guid() or f"{platform.node()}|{uuid.getnode():012x}"
    return format_machine_id(raw)


def normalize_machine_id(text):
    t = "".join(c for c in (text or "").upper() if c.isalnum())
    return f"{t[:4]}-{t[4:8]}-{t[8:12]}" if len(t) == 12 else (text or "").strip().upper()


# ------------------------------------------------------------- chave de licença
def make_key(secret, workshop, machine, expires=None, edition="pro", issued=None):
    """Cria a chave de licença (usado pela ferramenta do fornecedor, nunca pelo programa)."""
    payload = {"v": 1, "workshop": workshop.strip(), "machine": normalize_machine_id(machine),
               "edition": edition, "issued": (issued or datetime.date.today()).isoformat(),
               "expires": expires.isoformat() if expires else None}
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return PREFIX + _b64e(data) + "." + _b64e(ed25519.sign(secret, data))


def check_key(text, machine=None, today=None, public=None):
    """Valida uma chave. Devolve {"valid", "reason", "workshop", "expires", "edition", "machine"}."""
    out = {"valid": False, "reason": "", "workshop": "", "expires": None, "edition": "", "machine": ""}
    public = public if public is not None else _public_key()
    text = "".join((text or "").split())
    if public is None:
        out["reason"] = tr("O licenciamento ainda não está configurado nesta versão.")
        return out
    if not text.startswith(PREFIX) or "." not in text:
        out["reason"] = tr("Isto não é uma chave de licença do Roots Auto Doctor.")
        return out
    try:
        body, sig = text[len(PREFIX):].split(".", 1)
        data, signature = _b64d(body), _b64d(sig)
    except Exception:
        out["reason"] = tr("A chave está incompleta ou foi mal copiada.")
        return out
    if not ed25519.verify(public, data, signature):
        out["reason"] = tr("A chave não é válida (assinatura errada ou chave alterada).")
        return out
    try:
        payload = json.loads(data.decode())
    except Exception:
        out["reason"] = tr("A chave não é válida.")
        return out
    out.update(workshop=payload.get("workshop", ""), edition=payload.get("edition", ""),
               machine=payload.get("machine", ""))
    if payload.get("expires"):
        out["expires"] = datetime.date.fromisoformat(payload["expires"])
    machine = machine or machine_id()
    if normalize_machine_id(payload.get("machine")) != normalize_machine_id(machine):
        out["reason"] = tr("Esta licença é de outro PC ({other}). O ID deste PC é {machine}.",
                           other=payload.get("machine"), machine=machine)
        return out
    today = today or datetime.date.today()
    if out["expires"] and today > out["expires"]:
        out["reason"] = tr("A licença expirou em {date}.", date=f"{out['expires']:%d/%m/%Y}")
        return out
    out["valid"] = True
    return out


# ----------------------------------------------------------------- ficheiro
def license_dir():
    if DIRECTORY:
        return DIRECTORY
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor")
    os.makedirs(path, exist_ok=True)
    return path


def _path():
    return os.path.join(license_dir(), FILE_NAME)


def stored_key():
    try:
        with open(_path(), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def install(text, machine=None):
    """Valida e guarda a chave. Devolve o resultado de check_key (só guarda se for válida)."""
    r = check_key(text, machine)
    if r["valid"]:
        with open(_path(), "w", encoding="utf-8") as fh:
            fh.write("".join(text.split()) + "\n")
    return r


def remove():
    try:
        os.remove(_path())
    except OSError:
        pass


def status(machine=None, today=None):
    """Estado actual: {"state": "unconfigured" | "licensed" | "demo", "licensed", "message", ...}.
    unconfigured = versão sem chave pública (desenvolvimento): tudo funciona."""
    if _public_key() is None:
        return {"state": "unconfigured", "licensed": True, "workshop": "", "expires": None,
                "message": tr("Licenciamento não configurado (versão de desenvolvimento).")}
    key = stored_key()
    if not key:
        return {"state": "demo", "licensed": False, "workshop": "", "expires": None,
                "message": tr("Modo demonstração: sem licença activada neste PC.")}
    r = check_key(key, machine, today)
    if not r["valid"]:
        return {"state": "demo", "licensed": False, "workshop": r["workshop"], "expires": r["expires"],
                "message": tr("Modo demonstração: {reason}", reason=r["reason"])}
    if r["expires"]:
        message = tr("Licenciado a {workshop}, válida até {date}.", workshop=r["workshop"],
                     date=f"{r['expires']:%d/%m/%Y}")
    else:
        message = tr("Licenciado a {workshop}, sem data de fim.", workshop=r["workshop"])
    return {"state": "licensed", "licensed": True, "workshop": r["workshop"], "expires": r["expires"],
            "message": message}


def demo_block_message():
    """Mensagem de recusa em modo demonstração (no idioma escolhido). A janela compara com esta função."""
    return tr("Modo demonstração: esta função escreve no veículo e precisa de uma licença. "
              "Active a licença em Opções → Licença (o simulador funciona sem limites).")
