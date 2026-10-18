"""Registos em disco: comunicação (um ficheiro por dia) e erros inesperados (crash.log).
Ficam em %APPDATA%\\RootsAutoDoctor\\registos — é isto que se envia para corrigir bugs."""
import datetime
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
