"""Licenças do Roots Auto Doctor.

Cada PC tem um código (derivado do MachineGuid do Windows). O vendedor gera com
tools/keygen.py uma chave assinada (Ed25519) para esse código; o programa só precisa
da chave pública para a validar, por isso não é possível gerar chaves a partir do programa.

Sem licença válida o programa funciona em modo de avaliação: todas as funções
disponíveis, mas os relatórios levam a marca "Versão de avaliação".
"""
import base64
import datetime
import hashlib
import json
import os
import uuid

from . import ed25519

PUBLIC_KEY = base64.b64decode("L7pY4GG7XOjMq5Bz4ugTxkUTtlFP/2AoyU1Kf/Z87TY=")


def _b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _raw_machine_id():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                           winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0))
        val, _ = winreg.QueryValueEx(k, "MachineGuid")
        return str(val)
    except Exception:
        pass
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(path) as fh:
                return fh.read().strip()
        except OSError:
            continue
    return f"mac-{uuid.getnode():012x}"


def machine_code():
    """Código do PC, para o cliente enviar ao vendedor: XXXX-XXXX-XXXX-XXXX."""
    h = hashlib.sha256(("roots-auto-doctor|" + _raw_machine_id()).encode()).hexdigest().upper()[:16]
    return "-".join(h[i:i + 4] for i in range(0, 16, 4))


def make_key(secret, machine, holder, expires=""):
    """Gera uma chave (usado só pelo tools/keygen.py)."""
    payload = json.dumps({"m": machine.upper(), "n": holder, "e": expires}, separators=(",", ":"),
                         ensure_ascii=False).encode()
    return _b64e(payload) + "." + _b64e(ed25519.sign(secret, payload))


def check_key(key, machine=None, today=None):
    """Devolve {"status": "valid"|"invalid"|"other_pc"|"expired", "holder", "expires"}."""
    machine = machine or machine_code()
    today = today or datetime.date.today()
    key = "".join((key or "").split())
    try:
        p, s = key.split(".")
        payload, sig = _b64d(p), _b64d(s)
        if not ed25519.verify(PUBLIC_KEY, payload, sig):
            return {"status": "invalid"}
        data = json.loads(payload.decode())
    except Exception:
        return {"status": "invalid"}
    info = {"holder": data.get("n", ""), "expires": data.get("e", "")}
    if data.get("m") != machine:
        return {"status": "other_pc", **info}
    if info["expires"]:
        try:
            if datetime.date.fromisoformat(info["expires"]) < today:
                return {"status": "expired", **info}
        except ValueError:
            return {"status": "invalid"}
    return {"status": "valid", **info}


def _license_file():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "licenca.key")


def _effective_today(today=None, path=None):
    """Data usada para a validade: a mais recente entre hoje e a última data em que o programa
    correu, para que atrasar o relógio do PC não prolongue uma licença com prazo."""
    today = today or datetime.date.today()
    path = path or os.path.join(os.path.dirname(_license_file()), "licenca.estado")
    try:
        with open(path, encoding="utf-8") as fh:
            last = datetime.date.fromisoformat(fh.read().strip())
    except (OSError, ValueError):
        last = today
    eff = max(today, last)
    if eff != last or not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(eff.isoformat())
        except OSError:
            pass
    return eff


def load():
    try:
        with open(_license_file(), encoding="utf-8") as fh:
            key = fh.read().strip()
    except OSError:
        return {"status": "missing"}
    return check_key(key, today=_effective_today())


def activate(key):
    r = check_key(key, today=_effective_today())
    if r["status"] == "valid":
        with open(_license_file(), "w", encoding="utf-8") as fh:
            fh.write("".join(key.split()))
    return r


STATUS_TEXT = {
    "valid": "Licença activa",
    "missing": "Versão de avaliação",
    "invalid": "Chave inválida",
    "other_pc": "Esta chave é de outro computador",
    "expired": "Licença expirada",
}
