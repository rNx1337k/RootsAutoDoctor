"""Thread de comunicação: toda a conversa com o carro acontece aqui, fora da UI.

A UI envia comandos com submit(); os resultados voltam por sinais Qt.
Quando não há comandos, a thread mantém a ligação viva (keep-alive) ou faz a
leitura contínua dos grupos de medição.
"""
import logging
import queue
import time
import traceback

from PySide6.QtCore import QThread, Signal

from .kline import KLine
from .j2534 import J2534Link, is_j2534_port
from .session import ECUSession
from .errors import ProtocolError, NoResponse, RequestRejected, NotSupported
from . import vag_data

log = logging.getLogger(__name__)


class Worker(QThread):
    log = Signal(str)
    state = Signal(str, object)            # "disconnected" | "connecting" | "connected"
    result = Signal(str, object)
    error = Signal(str, str)
    live = Signal(object)
    scan_progress = Signal(int, int, object)
    busy = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.q = queue.Queue()
        self.cfg = {"port": "", "baud": "auto", "echo": "auto", "raw_log": False}
        self.kl = None
        self.session = None
        self.live_mode = None              # None | "read" | "basic"
        self.live_groups = []
        self._quiet = False
        self.abort_scan = False
        self._running = True
        self._busy = False

    @property
    def is_busy(self):
        """A thread está a executar um comando ou tem comandos à espera (não conta a leitura contínua)."""
        return self._busy or not self.q.empty()

    # ------------------------------------------------------------ API da UI
    def submit(self, cmd, *args):
        self.q.put((cmd, args))

    def set_live(self, mode, groups):
        self.live_groups = list(groups)
        self.live_mode = mode if groups else None

    def stop(self):
        self._running = False
        self.abort_scan = True
        self.live_mode = None
        if self.kl is not None:
            self.kl.cancelled = True                 # interrompe um init a 5 baud em curso
        self.submit("_quit")
        # um init a 5 baud sem resposta pode demorar ~8 s; não destruir a thread a meio
        if not self.wait(12000):
            log.warning("A thread de comunicação não terminou a tempo")

    # ---------------------------------------------------------------- loop
    def run(self):
        last = time.monotonic()
        while self._running:
            try:
                cmd, args = self.q.get(timeout=0.03)
            except queue.Empty:
                cmd = None
            if cmd == "_quit":
                break
            if cmd:
                self._busy = True
                self.busy.emit(True)
                try:
                    if self._running:
                        self._dispatch(cmd, args)
                finally:
                    self._busy = False
                    self.busy.emit(False)
                last = time.monotonic()
                continue
            s = self.session
            if not (s and s.connected):
                continue
            # A leitura contínua e o keep-alive geram dezenas de blocos por segundo:
            # só vão para o registo com "Registo detalhado" ligado nas Opções.
            self._quiet = not self.cfg.get("raw_log")
            try:
                if self.live_mode and self.live_groups:
                    self._poll_live()
                    last = time.monotonic()
                elif time.monotonic() - last > s.keep_alive_interval:
                    s.keep_alive()
                    last = time.monotonic()
            except ProtocolError as e:
                self._quiet = False
                self._lost(str(e))
            except Exception as e:
                self._quiet = False
                log.exception("Erro na leitura contínua / keep-alive")
                self.log.emit(f"Erro: {e}")
            finally:
                self._quiet = False
        self._close_all()

    def _log(self, msg):
        if not self._quiet:
            self.log.emit(msg)

    def _lost(self, reason):
        self.live_mode = None
        self.log.emit(f"Ligação perdida: {reason}")
        self.session = None
        self.state.emit("disconnected", reason)

    def _close_all(self):
        try:
            if self.session:
                self.session.disconnect()
        except Exception as e:
            log.info("Erro ao desligar a sessão: %s", e)
        self.session = None
        if self.kl:
            self.kl.close()
        self.kl = None

    def _ensure_port(self):
        c = self.cfg
        if self.kl and self.kl.port_name == c["port"] and self.kl.echo_mode == c["echo"] and self.kl.is_open:
            self.kl.raw_log = c["raw_log"]
            return
        if self.kl:
            self.kl.close()
        if not c["port"]:
            raise ProtocolError("Escolha a porta do cabo nas Opções")
        if is_j2534_port(c["port"]):
            self.kl = J2534Link(c["port"], log=self._log, raw_log=c["raw_log"])
        else:
            self.kl = KLine(c["port"], echo=c["echo"], log=self._log, raw_log=c["raw_log"])
        saved = _saved_lines(c["port"])
        if saved and not getattr(self.kl, "is_j2534", False):
            self.kl.lines = saved
        self.kl.open()
        self.log.emit(f"Interface {c['port']} aberta")

    def _echo(self):
        """Teste de eco; se falhar, procura o DTR/RTS que liga o transceptor e guarda-o para esta porta."""
        if getattr(self.kl, "is_j2534", False):
            return self.kl.echo_test(), ""
        before = self.kl.lines
        combo = self.kl.find_lines()
        if combo is None:
            return False, ""
        note = ""
        if combo != before:
            _save_lines(self.cfg["port"], combo)
            note = f" (DTR {'on' if combo[0] else 'off'}, RTS {'on' if combo[1] else 'off'} — guardado)"
        return True, note

    def _preflight(self):
        """Antes de falar com o carro, confirma o eco da linha K (0,3 s; até 1,5 s se tiver de procurar o
        DTR/RTS). Sem isto, sem carro ou sem ignição cada endereço demora 3 s a falhar e o Auto-Scan
        ficava mais de um minuto parado a dizer só "não responde"."""
        if getattr(self.kl, "is_j2534", False) or self.cfg.get("echo") == "off":
            return
        ok, note = self._echo()
        if not ok:
            raise ProtocolError(no_echo_text(self.cfg.get("port", "")))
        if note:
            self.log.emit("Eco da linha K OK" + note)

    # ------------------------------------------------------------ comandos
    def _dispatch(self, cmd, args):
        try:
            handler = Worker.__dict__.get(f"_cmd_{cmd}")
            if handler:
                handler(self, *args)
            else:
                self._session_cmd(cmd, args)
        except (RequestRejected, NotSupported) as e:
            self.error.emit(cmd, str(e))
        except ProtocolError as e:
            self.error.emit(cmd, str(e))
            if cmd == "connect" or (self.session and not self.session.connected):
                self.session = None
                self.state.emit("disconnected", str(e))
        except Exception as e:
            log.exception("Erro interno no comando %s", cmd)
            self.log.emit(traceback.format_exc())
            self.error.emit(cmd, f"Erro interno: {e}")

    def _session_cmd(self, cmd, args):
        if not self.session or not self.session.connected:
            raise ProtocolError("Não há ligação ao controlador")
        res = getattr(self.session, cmd)(*args)
        self.result.emit(cmd, res)

    def _cmd_configure(self, cfg):
        changed = (cfg.get("port") != self.cfg.get("port") or cfg.get("echo") != self.cfg.get("echo"))
        self.cfg.update(cfg)
        if changed and self.kl:
            if self.session:
                self._cmd_disconnect()
            self.kl.close()
            self.kl = None
        if self.kl:
            self.kl.raw_log = self.cfg["raw_log"]

    def _cmd_connect(self, address):
        self.live_mode = None
        if self.session:
            self.session.disconnect()
            self.session = None
            time.sleep(0.3)
        self._ensure_port()
        self.state.emit("connecting", address)
        self._preflight()
        s = ECUSession(self.kl, self._log, self.cfg["baud"])
        info = s.connect(address, retry=True)
        self.session = s
        self.log.emit(f"Ligado a {address:02X} — {info['part']} {info['component']}")
        self.state.emit("connected", info)

    def _cmd_disconnect(self):
        self.live_mode = None
        if self.session:
            try:
                self.session.disconnect()
            except Exception as e:
                log.info("Erro ao desligar a sessão: %s", e)
        self.session = None
        self.state.emit("disconnected", None)

    def _cmd_test_interface(self):
        self._ensure_port()
        ok, note = self._echo()
        msg = ("Porta aberta e eco da linha K OK — o cabo está a comunicar com a ficha OBD." + note
               if ok else "A porta abriu. " + no_echo_text(self.cfg.get("port", "")))
        self.result.emit("test_interface", {"ok": ok, "message": msg})

    def _cmd_link_check(self, address):
        """Verifica a ligação passo a passo e devolve [(passo, ok, detalhe)]."""
        steps = []
        self.live_mode = None
        if self.session:
            self._cmd_disconnect()
        old_raw = self.cfg.get("raw_log")
        self.cfg["raw_log"] = True
        try:
            port = self.cfg.get("port")
            if not port:
                steps.append(("Porta do cabo", False, "Nenhuma porta escolhida. Use Detectar cabo."))
                return
            try:
                self._ensure_port()
                steps.append(("Abrir a interface", True, port))
            except Exception as e:
                steps.append(("Abrir a interface", False, f"{e}. Feche outros programas que usem o cabo "
                                                           "(VCDS, Delphi…) e confirme a porta."))
                return
            if not getattr(self.kl, "is_j2534", False):
                try:
                    ok, note = self._echo()
                except Exception:
                    log.warning("Teste de eco falhou", exc_info=True)
                    ok, note = False, ""
                why = ("O cabo vê a linha K do carro." + note) if ok else no_echo_text(port)
                steps.append(("Eco da linha K", ok, why))
                if not ok:
                    return
            try:
                s = ECUSession(self.kl, self._log, self.cfg["baud"])
                info = s.connect(address, retry=True)
                steps.append((f"Ligação ao controlador {address:02X}", True,
                              f"{info['protocol']} a {info['baud']} baud — {info['part']} {info['component']}"))
                try:
                    n = len(s.read_faults())
                    steps.append(("Leitura de avarias", True, f"{n} avaria(s)"))
                except Exception as e:
                    steps.append(("Leitura de avarias", False, str(e)))
                s.disconnect()
            except NoResponse as e:
                steps.append((f"Ligação ao controlador {address:02X}", False,
                              f"{e}. Confirme que a ignição está ligada; experimente outro endereço (ex.: 17)."))
            except Exception as e:
                steps.append((f"Ligação ao controlador {address:02X}", False,
                              f"{e}. Active o Registo detalhado e crie um pacote de suporte."))
        finally:
            self.cfg["raw_log"] = old_raw
            if self.kl:
                self.kl.raw_log = bool(old_raw)
            self.result.emit("link_check", steps)

    def _cmd_autoscan(self, addresses):
        self.abort_scan = False
        self.live_mode = None
        if self.session:
            self._cmd_disconnect()
        self._ensure_port()
        self._preflight()
        total = len(addresses)
        for i, addr in enumerate(addresses):
            if self.abort_scan:
                break
            item = {"address": addr, "module": vag_data.module_name(addr)}
            try:
                s = ECUSession(self.kl, self._log, self.cfg["baud"])
                item["info"] = s.connect(addr)
                item["faults"] = s.read_faults()
                item["status"] = "ok"
                s.disconnect()
            except NoResponse:
                item["status"] = "absent"
            except Exception as e:
                item["status"] = "error"
                item["error"] = str(e)
            self.scan_progress.emit(i + 1, total, item)
            if self.kl.is_simulator:
                time.sleep(0.02)
            else:
                # depois de um erro a ECU pode ficar à espera; deixá-la expirar antes do próximo init
                time.sleep(1.5 if item["status"] == "error" else 0.35)
        self.result.emit("autoscan", {"aborted": self.abort_scan})

    def _cmd_clear_all(self, addresses):
        """Apaga as avarias em cada endereço e volta a ler o que ficou."""
        self.live_mode = None
        if self.session:
            self._cmd_disconnect()
        self._ensure_port()
        out = []
        for addr in addresses:
            item = {"address": addr}
            try:
                s = ECUSession(self.kl, self._log, self.cfg["baud"])
                s.connect(addr, retry=True)
                item["faults"] = s.clear_faults()
                item["status"] = "ok"
                s.disconnect()
            except Exception as e:
                item["status"] = "error"
                item["error"] = str(e)
            out.append(item)
            self.log.emit(f"Apagar avarias {addr:02X}: "
                          f"{'ficaram ' + str(len(item['faults'])) if item['status'] == 'ok' else item['error']}")
            time.sleep(0.02 if self.kl.is_simulator else (1.5 if item["status"] == "error" else 0.35))
        self.result.emit("clear_all", out)

    # ------------------------------------------------------------ leitura viva
    def _poll_live(self):
        s = self.session
        mode = self.live_mode
        out = {"mode": mode, "groups": {}, "t": time.time()}
        for g in list(self.live_groups):
            try:
                r = s.read_group(g) if mode == "read" else s.basic_setting(g)
                out["groups"][g] = r["fields"]
            except (RequestRejected, NotSupported) as e:
                out["groups"][g] = str(e)
        self.live.emit(out)


def no_echo_text(port):
    """Explicação para quando o byte enviado não volta da linha K."""
    if port.startswith(("FTDI:", "D2XX:")):
        return ("Sem eco na linha K. Confirme que o cabo está ligado à ficha OBD e que a ignição está ligada "
                "(sem 12 V na ficha não há eco). Se já estiver, a interface abriu pelo USB mas os bytes não "
                "voltam da linha K: há um microcontrolador entre o chip FTDI e a ficha (clone 'inteligente') "
                "e esta interface não pode ser usada como cabo KKL — use um cabo KKL 409.1 ou uma interface J2534.")
    return ("Sem eco na linha K: o cabo não está ligado à ficha OBD, a ignição está desligada, ou não é um "
            "cabo KKL. Se o seu cabo não tiver eco, escolha \"Sem eco\" em Opções → Eco da linha K.")


def _saved_lines(port):
    """(DTR, RTS) que deu eco nesta porta da última vez, ou None."""
    try:
        from .settings import app_settings
        v = app_settings().value(f"lines/{port}")
        if v:
            dtr, rts = str(v).split(",")
            return (dtr == "1", rts == "1")
    except Exception:
        log.warning("Não foi possível ler o DTR/RTS guardado", exc_info=True)
    return None


def _save_lines(port, combo):
    try:
        from .settings import app_settings
        app_settings().setValue(f"lines/{port}", f"{int(combo[0])},{int(combo[1])}")
    except Exception:
        log.warning("Não foi possível guardar o DTR/RTS", exc_info=True)
