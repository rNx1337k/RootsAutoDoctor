"""Registos em disco: comunicação (um ficheiro por dia) e erros inesperados (crash.log).
Ficam em %APPDATA%\\RootsAutoDoctor\\registos — é isto que se envia para corrigir bugs."""
import datetime
import logging
import logging.handlers
import os
import platform
import sys
import traceback

from . import APP_NAME, VERSION


def log_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor", "registos")
    os.makedirs(path, exist_ok=True)
    return path


def setup_logging():
    """Erros apanhados pelo programa (que não chegam a ser crash) vão para erros.log, com o traceback.
    Sem isto, uma falha engolida no carro aparece só como "não liga"."""
    logger = logging.getLogger("rad")
    if logger.handlers:
        return logger
    try:
        h = logging.handlers.RotatingFileHandler(os.path.join(log_dir(), "erros.log"), maxBytes=1_000_000,
                                                 backupCount=2, encoding="utf-8")
    except OSError:
        return logger
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    logger.info("%s v%s a iniciar", APP_NAME, VERSION)
    return logger


class DiskLog:
    def __init__(self):
        self.fh = None
        self.day = None

    def write(self, line):
        try:
            today = datetime.date.today()
            if self.fh is None or today != self.day:
                if self.fh:
                    self.fh.close()
                self.day = today
                self.fh = open(os.path.join(log_dir(), f"comunicacao_{today:%Y%m%d}.log"), "a",
                               encoding="utf-8")
                self.fh.write(f"\n===== {APP_NAME} v{VERSION} — {datetime.datetime.now():%H:%M:%S} =====\n")
            self.fh.write(line + "\n")
            self.fh.flush()
        except Exception:
            pass


def write_crash(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        with open(os.path.join(log_dir(), "crash.log"), "a", encoding="utf-8") as fh:
            fh.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {APP_NAME} v{VERSION}  "
                     f"Python {sys.version.split()[0]}  {platform.platform()} =====\n{text}")
    except Exception:
        pass
    return text


def make_support_bundle(dest):
    """Cria um .zip com os registos dos últimos dias e informação do sistema, para enviar ao suporte.
    Não inclui licenças, histórico de clientes nem dados da oficina."""
    import glob
    import zipfile
    from .kline import list_serial_ports
    info = [f"{APP_NAME} v{VERSION}", f"Python {sys.version}", f"Sistema: {platform.platform()}",
            f"Data: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}", "", "Portas:"]
    try:
        info += [f"  {dev}  —  {desc}" for dev, desc in list_serial_ports()]
    except Exception as e:
        info.append(f"  erro: {e}")
    try:
        from . import cable
        info += ["", "Detecção de cabos:"]
        info += [f"  [{f['level']}] {f['title']}" for f in cable.detect()] or ["  nenhum cabo encontrado"]
        info += [f"  J2534: {d['name']} ({d['vendor']}) {d['dll']}" for d in cable.j2534_devices()]
    except Exception as e:
        info.append(f"  erro: {e}")
    logs = sorted(glob.glob(os.path.join(log_dir(), "comunicacao_*.log")))[-3:]
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("sistema.txt", "\n".join(info))
        for p in logs + [os.path.join(log_dir(), n) for n in ("crash.log", "erros.log")]:
            if os.path.exists(p):
                z.write(p, os.path.basename(p))
    return dest
