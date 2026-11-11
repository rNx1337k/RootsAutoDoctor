"""Registos em disco: comunicação (um ficheiro por dia) e erros inesperados (crash.log).
Ficam em %APPDATA%\\RootsAutoDoctor\\registos — é isto que se envia para corrigir bugs."""
import datetime
import logging
import logging.handlers
import os
import platform
import re
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


def crash_log_path():
    """Caminho do crash.log (para mostrar ao utilizador). Nunca falha, mesmo sem acesso à pasta."""
    try:
        return os.path.join(log_dir(), "crash.log")
    except OSError:
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
        return os.path.join(base, "RootsAutoDoctor", "registos", "crash.log")


_fault_fh = None


def enable_fault_log(path=None):
    """Fechos nativos (driver do cabo, Qt, DLL J2534) não passam pelo sys.excepthook: o processo desaparece sem
    deixar nada. Com o faulthandler, o Python escreve no crash.log a pilha de todas as threads antes de morrer.
    Devolve o ficheiro aberto, ou None se não foi possível (nunca impede o programa de abrir)."""
    global _fault_fh
    import faulthandler
    if _fault_fh is not None and path is None:
        return _fault_fh
    try:
        fh = open(path or crash_log_path(), "a", encoding="utf-8")
        fh.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {APP_NAME} v{VERSION} a iniciar — se o "
                 f"programa fechar sozinho, a pilha das threads fica a seguir =====\n")
        fh.flush()
        faulthandler.enable(file=fh, all_threads=True)
    except Exception:
        return None
    if _fault_fh is not None and _fault_fh is not fh:
        try:
            _fault_fh.close()
        except Exception:
            pass
    _fault_fh = fh
    return fh


def write_crash(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        with open(crash_log_path(), "a", encoding="utf-8") as fh:
            fh.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {APP_NAME} v{VERSION}  "
                     f"Python {sys.version.split()[0]}  {platform.platform()} =====\n{text}")
    except Exception:
        pass
    return text


# Números de chassis (VIN: 17 caracteres, sem I, O e Q) e matrículas portuguesas (AA-00-AA, 00-AA-00, 00-00-AA,
# AA-00-00) saem dos ficheiros de texto do pacote de suporte: identificam o carro do cliente e não fazem falta para
# corrigir um erro. Os bytes em hexadecimal (separados por espaços) não são afectados.
_VIN = re.compile(r"(?<![A-Za-z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-Za-z0-9])")
_PLATE = re.compile(r"(?<![A-Za-z0-9-])(?:[A-Z]{2}-\d{2}-[A-Z]{2}|\d{2}-[A-Z]{2}-\d{2}|\d{2}-\d{2}-[A-Z]{2}|"
                    r"[A-Z]{2}-\d{2}-\d{2})(?![A-Za-z0-9-])")


def _is_vin(text):
    return any(c.isalpha() for c in text) and any(c.isdigit() for c in text)


def scrub(text):
    """Tira VIN e matrículas de um texto (para o pacote de suporte)."""
    text = _VIN.sub(lambda m: "[VIN]" if _is_vin(m.group(0)) else m.group(0), text)
    return _PLATE.sub("[MATRÍCULA]", text)


SAFE_SETTINGS = ("adapter", "port", "baud", "echo", "elm_protocol", "raw_log", "ui/language", "ui/scale",
                 "updates/gave_up", "updates/channel")

BUNDLE_README = """Pacote de suporte — {app} v{version}

sistema.txt          versão, Windows, portas, cabos detectados, definições de ligação e estado das actualizações
comunicacao_*.log    comunicação com o carro dos últimos dias
erros.log, crash.log erros do programa
instalacao.log       registo da última actualização (se houver)
gravacoes/           últimas gravações da comunicação e relatórios de validação

Não leva o histórico de diagnósticos, os dados da oficina, a licença nem o logótipo. Os números de chassis e as
matrículas foram tirados dos registos e dos relatórios. As gravações vão tal como foram feitas (para reproduzir o
problema byte a byte).
"""


def _add_text(z, path, arcname):
    """Junta um ficheiro de texto ao zip, sem VIN nem matrículas."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        z.writestr(arcname, scrub(fh.read()))


def _update_lines():
    try:
        from . import autoupdate
        mode = autoupdate.update_mode()
        st = autoupdate.pending() or {}
        lines = [f"  modo: {mode or 'só aviso'}"]
        bad = sorted(autoupdate.bad_versions())
        if bad:
            lines.append(f"  versões que não abriram (recusadas): {', '.join(bad)}")
        back = autoupdate.rollback_target()
        if back:
            lines.append(f"  caminho de volta: versão {back}")
        if st:
            lines.append(f"  pendente: {st.get('version')} ({st.get('mode', 'installer')}), "
                         f"tentativas {st.get('attempts', 0)}, lançada {st.get('launched')}")
        return lines
    except Exception as e:
        return [f"  erro: {e}"]


def make_support_bundle(dest, settings=None, license_state=None):
    """Cria um .zip com os registos dos últimos dias e informação do sistema, para enviar ao suporte.
    settings: as definições (QSettings ou dict); só vão as de SAFE_SETTINGS. license_state: "licensed", "demo"...
    Não inclui histórico de clientes, dados da oficina nem a chave da licença; tira VIN e matrículas dos registos e
    dos relatórios (as gravações vão inteiras: a reprodução precisa dos bytes exactos)."""
    import glob
    import zipfile
    from .kline import list_serial_ports
    info = [f"{APP_NAME} v{VERSION}", f"Python {sys.version}", f"Sistema: {platform.platform()}",
            f"Data: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"]
    if license_state:
        info.append(f"Licença: {license_state}")
    info += ["", "Portas:"]
    try:
        info += [f"  {dev}  —  {desc}" for dev, desc in list_serial_ports(technical=True)]
    except Exception as e:
        info.append(f"  erro: {e}")
    try:
        from . import cable
        info += ["", "Detecção de cabos:"]
        info += [f"  [{f['level']}] {f['title']}" for f in cable.detect()] or ["  nenhum cabo encontrado"]
        info += [f"  J2534: {d['name']} ({d['vendor']}) {d['dll']}" for d in cable.j2534_devices()]
    except Exception as e:
        info.append(f"  erro: {e}")
    if settings is not None:
        info += ["", "Definições:"]
        for key in SAFE_SETTINGS:
            try:
                value = settings.get(key) if isinstance(settings, dict) else settings.value(key)
            except Exception:
                value = None
            if value not in (None, ""):
                info.append(f"  {key} = {value}")
    info += ["", "Actualizações:"] + _update_lines()
    logs = sorted(glob.glob(os.path.join(log_dir(), "comunicacao_*.log")))[-3:]
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("LEIA-ME.txt", BUNDLE_README.format(app=APP_NAME, version=VERSION))
        z.writestr("sistema.txt", scrub("\n".join(info)))
        for p in logs + [os.path.join(log_dir(), n) for n in ("crash.log", "erros.log")]:
            if os.path.exists(p):
                _add_text(z, p, os.path.basename(p))
        try:
            from . import autoupdate
            if os.path.exists(autoupdate.log_path()):
                _add_text(z, autoupdate.log_path(), "instalacao.log")
        except Exception as e:
            z.writestr("instalacao_erro.txt", str(e))
        try:                                       # gravações da comunicação e relatórios de validação
            from . import capture
            for p in capture.recent(3):            # tal como foram gravadas: a reprodução compara byte a byte
                z.write(p, "gravacoes/" + os.path.basename(p))
                report = p[:-len(capture.EXT)] + ".html"
                if os.path.exists(report):
                    _add_text(z, report, "gravacoes/" + os.path.basename(report))
        except Exception as e:
            z.writestr("gravacoes/erro.txt", str(e))
    return dest
