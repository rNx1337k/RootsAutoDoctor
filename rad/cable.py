"""Detecção do cabo de diagnóstico ligado ao PC (Windows).

Lista os dispositivos USB-série presentes — mesmo sem driver instalado — e diz:
  - que chip tem (FTDI, CH340, PL2303, CP210x) e se já tem porta COM;
  - se parece uma interface HEX da Ross-Tech (clone), que não funciona como cabo KKL;
  - o Latency Timer dos cabos FTDI (1 ms recomendado).
"""
import json
import re
import subprocess
import sys

KNOWN = {
    "0403": ("FTDI", {"6001": "FT232R", "6015": "FT231X", "6014": "FT232H", "6010": "FT2232"}),
    "1A86": ("CH340", {"7523": "CH340", "5523": "CH341", "55D4": "CH9102"}),
    "067B": ("Prolific", {"2303": "PL2303"}),
    "10C4": ("Silicon Labs", {"EA60": "CP210x"}),
}

DRIVERS = {
    "FTDI": "https://ftdichip.com/drivers/vcp-drivers/",
    "CH340": "https://www.wch-ic.com/downloads/CH341SER_EXE.html",
    "Prolific": "https://www.prolific.com.tw/US/ShowProduct.aspx?p_id=225&pcid=41",
    "Silicon Labs": "https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers",
}

PS_QUERY = (
    "Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^(USB|FTDIBUS)\\\\VID_' } | "
    "Select-Object FriendlyName,InstanceId,Status,Class | ConvertTo-Json -Compress"
)


def _run_powershell(cmd):
    flags = 0x08000000 if sys.platform == "win32" else 0          # CREATE_NO_WINDOW
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                         capture_output=True, text=True, timeout=20, creationflags=flags)
    return out.stdout


def list_usb_devices():
    """[{name, id, status, cls}] — vazio fora do Windows ou se o PowerShell falhar."""
    try:
        raw = _run_powershell(PS_QUERY).strip()
    except Exception:
        return []
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    if isinstance(data, dict):
        data = [data]
    return [{"name": d.get("FriendlyName") or "", "id": d.get("InstanceId") or "",
             "status": d.get("Status") or "", "cls": d.get("Class") or ""} for d in data]


def _vid_pid(instance_id):
    m = re.search(r"VID_([0-9A-F]{4})[&+]PID_([0-9A-F]{4})", instance_id.upper())
    return (m.group(1), m.group(2)) if m else (None, None)


def ftdi_latency():
    """{'COM5': 16, ...} lido do registo (só Windows)."""
    out = {}
    try:
        import winreg
        base = r"SYSTEM\CurrentControlSet\Enum\FTDIBUS"
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
        i = 0
        while True:
            try:
                dev = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            try:
                k = winreg.OpenKey(root, dev + r"\0000\Device Parameters")
                port, _ = winreg.QueryValueEx(k, "PortName")
                lat, _ = winreg.QueryValueEx(k, "LatencyTimer")
                out[str(port)] = int(lat)
            except OSError:
                continue
    except Exception:
        pass
    return out


def classify(devices, latency=None):
    """Transforma a lista de dispositivos em conclusões para o utilizador.

    Devolve [{"title", "detail", "level": ok|warn|bad, "com", "driver_url"}]."""
    latency = latency or {}
    findings = []
    seen = set()
    with_com = {_vid_pid(d["id"]) for d in devices if re.search(r"\(COM\d+\)", d["name"])}
    for d in devices:
        vid, pid = _vid_pid(d["id"])
        if not vid:
            continue
        name_l = d["name"].lower()
        com = None
        m = re.search(r"\((COM\d+)\)", d["name"])
        if m:
            com = m.group(1)
        hex_like = "ross-tech" in name_l or "hex-" in name_l or "hex v2" in name_l
        if vid not in KNOWN and not hex_like:
            continue
        key = (vid, pid, com)
        if key in seen:
            continue
        seen.add(key)
        vendor, models = KNOWN.get(vid, ("", {}))
        chip = models.get(pid, vendor)
        status_ok = d["status"].upper() == "OK"

        if hex_like or (vid == "0403" and pid not in models):
            findings.append({
                "level": "bad", "com": None, "driver_url": None,
                "title": f"Interface tipo VCDS HEX ({d['name'] or 'sem nome'})",
                "detail": ("Este cabo parece um clone de HEX-USB+CAN / HEX-V2: tem um microcontrolador com "
                           "firmware próprio da Ross-Tech entre o USB e o carro. Não funciona como cabo KKL "
                           "e não pode ser usado pelo Roots Auto Doctor, mesmo com drivers. "
                           "É preciso um cabo KKL 'VAG-COM 409.1' (FTDI ou CH340)."),
            })
            continue
        if com and status_ok:
            lat = latency.get(com)
            if vendor == "FTDI" and lat is not None and lat > 1:
                findings.append({
                    "level": "warn", "com": com, "driver_url": None,
                    "title": f"Cabo {chip} pronto em {com} — Latency Timer {lat} ms",
                    "detail": (f"Funciona, mas a leitura será lenta. Gestor de Dispositivos → Portas (COM e LPT) → "
                               f"{com} → Propriedades → Definições da porta → Avançadas → Latency Timer = 1."),
                })
            else:
                findings.append({
                    "level": "ok", "com": com, "driver_url": None,
                    "title": f"Cabo {chip} pronto em {com}",
                    "detail": f"Escolha {com} na porta do cabo e carregue em Testar interface com a ignição ligada.",
                })
        elif (vid, pid) in with_com:
            continue                     # entrada USB do mesmo cabo que já tem porta COM
        elif vendor == "FTDI" and status_ok and d["cls"].upper() == "USB":
            findings.append({
                "level": "warn", "com": None, "driver_url": DRIVERS["FTDI"],
                "title": "Cabo FTDI sem porta COM",
                "detail": ("O driver está instalado mas a porta COM está desligada. Gestor de Dispositivos → "
                           "Controladores USB → USB Serial Converter → Propriedades → Avançadas → marque "
                           "'Load VCP' → OK, e volte a ligar o cabo. Se não existir essa opção, instale o "
                           "driver VCP da FTDI."),
            })
        elif not status_ok:
            findings.append({
                "level": "warn", "com": None, "driver_url": DRIVERS.get(vendor),
                "title": f"Cabo {chip} sem driver",
                "detail": f"Instale o driver oficial ({vendor}) e volte a ligar o cabo.",
            })
    return findings


def detect():
    if sys.platform != "win32":
        return []
    return classify(list_usb_devices(), ftdi_latency())
