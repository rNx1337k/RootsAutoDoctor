"""Detecção do cabo de diagnóstico ligado ao PC (Windows).

Lista os dispositivos USB-série presentes — mesmo sem driver instalado — e diz:
  - que chip tem (FTDI, CH340, PL2303, CP210x) e se já tem porta COM;
  - se é um clone HEX-USB (chip FTDI com PID próprio): precisa do driver WinUSB para ser usado
    por acesso USB directo (rad/ftdi_direct.py) — e só funciona se não tiver microcontrolador;
  - se é outra interface com firmware próprio (HEX-V2/HEX-NET genuínas, Autocom...), que não serve;
  - o Latency Timer dos cabos FTDI (1 ms recomendado).
"""
import importlib.util
import json
import logging
import re
import subprocess
import sys
from .i18n import tr

log = logging.getLogger(__name__)

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
    "Select-Object FriendlyName,InstanceId,Status,Class,Service,HardwareID | ConvertTo-Json -Compress"
)


# O PowerShell escreve para o tubo na página de código OEM (cp850 num Windows português) e o Python lia com a
# ANSI (cp1252): nomes como "Porta série USB" chegavam corrompidos. Força-se UTF-8 dos dois lados.
PS_UTF8 = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "


def _run_powershell(cmd):
    flags = 0x08000000 if sys.platform == "win32" else 0          # CREATE_NO_WINDOW
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_UTF8 + cmd],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                         creationflags=flags)
    return out.stdout


def list_usb_devices():
    """[{name, id, status, cls}] — vazio fora do Windows ou se o PowerShell falhar."""
    try:
        raw = _run_powershell(PS_QUERY).strip()
    except Exception:
        log.warning("Não foi possível listar os dispositivos USB (PowerShell)", exc_info=True)
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
             "status": d.get("Status") or "", "cls": d.get("Class") or "",
             "service": d.get("Service") or "", "hwid": _as_list(d.get("HardwareID"))} for d in data]


def _as_list(v):
    if v is None:
        return []
    return [v] if isinstance(v, str) else list(v)


def _bcd_device(hwids):
    """bcdDevice a partir do HardwareID ...&REV_0600 (identifica o chip FTDI)."""
    for h in hwids or ():
        m = re.search(r"REV_([0-9A-F]{4})", h.upper())
        if m:
            return int(m.group(1), 16)
    return None


def _usb_serial(instance_id):
    """N.º de série USB = último segmento do InstanceId (se tiver '&' foi o Windows que o inventou)."""
    last = instance_id.rsplit("\\", 1)[-1]
    return None if "&" in last else last


WINUSB_SERVICES = {"winusb", "libusbk", "libusb0"}


def _pyftdi_available():
    return importlib.util.find_spec("pyftdi") is not None and importlib.util.find_spec("usb") is not None


def _d2xx_finding(d, name, chip, serial, caveat):
    """Clone HEX-USB com o driver RT-USB da Ross-Tech: usa-se pelo RT-USB.DLL (D2XX, 32 bits)."""
    from .d2xx import PREFIX, find_dll
    from .j2534 import dll_bitness, find_python
    base = {"com": None, "driver_url": None}
    dll = find_dll()
    if not dll:
        return {**base, "level": "warn", "driver_url": "https://zadig.akeo.ie/",
                "title": tr("{name} — driver RT-USB sem RT-USB.DLL", name=name),
                "detail": (tr("O driver está instalado mas falta a biblioteca RT-USB.DLL. Reinstale o driver, ou "
                           "troque-o pelo WinUSB com o Zadig para usar o acesso USB directo. ") + caveat)}
    bits = dll_bitness(dll)
    try:
        find_python(bits)
    except Exception:
        return {**base, "level": "warn", "driver_url": None,
                "title": tr("{name} — driver RT-USB OK, falta o componente de {bits} bits do programa",
                            name=name, bits=bits),
                "detail": (tr("O {dll} é de {bits} bits e é carregado pelo componente de {bits} bits que vem com o "
                              "Roots Auto Doctor (pasta runtime/py{bits}), que não foi encontrado. Volte a instalar o "
                              "programa (ou, no código-fonte, execute o run.bat) e carregue outra vez em Detectar "
                              "cabo. ",
                              dll=dll, bits=bits) + caveat)}
    return {**base, "level": "ok", "com": PREFIX + (serial or ""),
            "title": tr("{name} pronta pelo driver RT-USB ({chip}, S/N {v})", name=name, chip=chip, v=serial or '—'),
            "detail": (tr("Usa a biblioteca D2XX do driver (o VCDS continua a funcionar). Faça o Diagnóstico da "
                       "ligação com o cabo no carro e a ignição ligada. ") + caveat)}


def _hex_usb_finding(d, vid, pid):
    """Clone HEX-USB com chip FTDI: diz o que falta para o usar por acesso USB directo."""
    from .ftdi_direct import chip_name, make_port
    chip = chip_name(_bcd_device(d.get("hwid")))
    serial = _usb_serial(d["id"])
    service = (d.get("service") or "").lower()
    name = d["name"] or "Ross-Tech HEX-USB"
    caveat = (tr("Estes clones (HEX-USB+CAN) têm um microcontrolador entre o chip FTDI e a ficha OBD: o "
              "Diagnóstico da ligação fala com ele, confirma que responde e põe-no em modo KKL para chegar à "
              "linha K. Faça-o com o cabo no carro e a ignição ligada."))
    base = {"com": None, "driver_url": None}
    if d["status"].upper() != "OK" or not service:
        return {**base, "level": "warn", "driver_url": "https://zadig.akeo.ie/",
                "title": tr("{name} — chip {chip}, VID {vid} PID {pid}, sem driver",
                            name=name, chip=chip, vid=vid, pid=pid),
                "detail": (tr("Esta interface não tem porta COM. Para o Roots Auto Doctor a usar por acesso USB "
                              "directo, instale o driver WinUSB com o Zadig: Options → List All Devices → escolha "
                              "'{name}' → WinUSB → Install Driver. Depois carregue de novo em Detectar cabo. (O VCDS "
                              "deixa de reconhecer esta interface enquanto tiver o WinUSB.) ",
                              name=name) + caveat)}
    if service == "rt-usb":
        return _d2xx_finding(d, name, chip, serial, caveat)
    if service not in WINUSB_SERVICES:
        return {**base, "level": "warn", "driver_url": "https://zadig.akeo.ie/",
                "title": tr("{name} — usa o driver '{v}'", name=name, v=d.get('service')),
                "detail": (tr("Este driver é o do programa do fabricante e o Roots Auto Doctor não o usa. Para "
                           "acesso USB directo substitua-o pelo WinUSB com o Zadig (pode voltar ao driver "
                           "anterior no Gestor de Dispositivos → Controlador → Reverter). ") + caveat)}
    if not _pyftdi_available():
        return {**base, "level": "warn",
                "title": tr("{name} — driver WinUSB OK, falta o pyftdi", name=name),
                "detail": tr("Instale as dependências: .venv\\Scripts\\python.exe -m pip install -r requirements.txt")}
    port = make_port(int(vid, 16), int(pid, 16), serial)
    return {**base, "level": "ok", "com": port,
            "title": tr("{name} pronta por USB directo ({chip}, S/N {v})", name=name, chip=chip, v=serial or '—'),
            "detail": (tr("Faça o Diagnóstico da ligação com o cabo no carro e a ignição ligada para confirmar "
                       "que chega à linha K. ") + caveat)}


def _vid_pid(instance_id):
    m = re.search(r"VID_([0-9A-F]{4})[&+]PID_([0-9A-F]{4})", instance_id.upper())
    return (m.group(1), m.group(2)) if m else (None, None)


def ftdi_latency():
    """{'COM5': 16, ...} lido do registo (só Windows)."""
    out = {}
    try:
        import winreg
        base = r"SYSTEM\CurrentControlSet\Enum\FTDIBUS"
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
        except FileNotFoundError:
            return out                     # nunca foi instalado nenhum cabo FTDI com driver VCP
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
        log.warning("Não foi possível ler o Latency Timer FTDI", exc_info=True)
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

        if vid == "0403" and (pid == "FA24" or hex_like) and "autocom" not in name_l and "delphi" not in name_l:
            findings.append(_hex_usb_finding(d, vid, pid))
            continue
        if hex_like or "autocom" in name_l or "delphi" in name_l or (vid == "0403" and pid not in models):
            if "autocom" in name_l or "delphi" in name_l:
                kind, who = "Autocom / Delphi", "da Autocom/Delphi"
            elif hex_like:
                kind, who = "VCDS HEX", "da Ross-Tech"
            else:
                kind, who = "com firmware próprio", "do fabricante"
            findings.append({
                "level": "bad", "com": None, "driver_url": None,
                "title": tr("Interface {kind} ({v})", kind=kind, v=d['name'] or 'sem nome'),
                "detail": (tr("Esta interface tem um microcontrolador com firmware {who} entre o USB e o carro, e só "
                              "fala com o programa desse fabricante. Não funciona como cabo KKL e não pode ser usada "
                              "pelo Roots Auto Doctor, mesmo com drivers. É preciso um cabo KKL 'VAG-COM 409.1' (FTDI "
                              "ou CH340); para módulos KWP2000 também serve uma interface J2534.",
                              who=who)),
            })
            continue
        if com and status_ok:
            lat = latency.get(com)
            if vendor == "FTDI" and lat is not None and lat > 1:
                findings.append({
                    "level": "warn", "com": com, "driver_url": None,
                    "title": tr("Cabo {chip} pronto em {com} — Latency Timer {lat} ms", chip=chip, com=com, lat=lat),
                    "detail": (tr("Funciona, mas a leitura será lenta. Gestor de Dispositivos → Portas (COM e LPT) → "
                                  "{com} → Propriedades → Definições da porta → Avançadas → Latency Timer = 1.",
                                  com=com)),
                })
            else:
                findings.append({
                    "level": "ok", "com": com, "driver_url": None,
                    "title": tr("Cabo {chip} pronto em {com}", chip=chip, com=com),
                    "detail": tr("Escolha {com} na porta do cabo e carregue em Testar interface com a ignição ligada.",
                                 com=com),
                })
        elif (vid, pid) in with_com:
            continue                     # entrada USB do mesmo cabo que já tem porta COM
        elif vendor == "FTDI" and status_ok and d["cls"].upper() == "USB":
            findings.append({
                "level": "warn", "com": None, "driver_url": DRIVERS["FTDI"],
                "title": tr("Cabo FTDI sem porta COM"),
                "detail": (tr("O driver está instalado mas a porta COM está desligada. Gestor de Dispositivos → "
                           "Controladores USB → USB Serial Converter → Propriedades → Avançadas → marque "
                           "'Load VCP' → OK, e volte a ligar o cabo. Se não existir essa opção, instale o "
                           "driver VCP da FTDI.")),
            })
        elif not status_ok:
            findings.append({
                "level": "warn", "com": None, "driver_url": DRIVERS.get(vendor),
                "title": tr("Cabo {chip} sem driver", chip=chip),
                "detail": tr("Instale o driver oficial ({vendor}) e volte a ligar o cabo.", vendor=vendor),
            })
    return findings


def detect():
    if sys.platform != "win32":
        return []
    return classify(list_usb_devices(), ftdi_latency())


def j2534_devices():
    """Interfaces J2534 (PassThru 04.04) registadas no Windows: [{name, vendor, dll, protocols}]."""
    out = []
    try:
        import winreg
    except ImportError:
        return out
    for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\PassThruSupport.04.04", 0,
                                  winreg.KEY_READ | view)
        except OSError:
            continue
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            try:
                k = winreg.OpenKey(root, sub)
                vals = {}
                j = 0
                while True:
                    try:
                        n, v, _t = winreg.EnumValue(k, j)
                    except OSError:
                        break
                    vals[n] = v
                    j += 1
            except OSError:
                continue
            protos = [p for p in ("ISO9141", "ISO14230", "CAN", "ISO15765", "J1850VPW", "J1850PWM")
                      if vals.get(p) == 1]
            dev = {"name": vals.get("Name", sub), "vendor": vals.get("Vendor", ""),
                   "dll": vals.get("FunctionLibrary", ""), "protocols": protos,
                   "view": "32-bit" if view == winreg.KEY_WOW64_32KEY else "64-bit"}
            if all(dev["dll"] != o["dll"] for o in out):
                out.append(dev)
    return out
