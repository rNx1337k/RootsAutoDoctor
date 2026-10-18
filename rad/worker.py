"""Thread de comunicação: toda a conversa com o carro acontece aqui, fora da UI.

A UI envia comandos com submit(); os resultados voltam por sinais Qt.
Quando não há comandos, a thread mantém a ligação viva (keep-alive) ou faz a
leitura contínua dos grupos de medição.
"""
import queue
import time
import traceback

from PySide6.QtCore import QThread, Signal

from .kline import KLine
from .j2534 import J2534Link, is_j2534_port
from .session import ECUSession
from .errors import ProtocolError, NoResponse, RequestRejected, NotSupported
from . import vag_data


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

    # ------------------------------------------------------------ API da UI
    def submit(self, cmd, *args):
        self.q.put((cmd, args))

    def set_live(self, mode, groups):
        self.live_groups = list(groups)
        self.live_mode = mode if groups else None

    def stop(self):
        self._running = False
        self.submit("_quit")
        self.wait(3000)

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
                self.busy.emit(True)
                try:
                    self._dispatch(cmd, args)
                finally:
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
        except Exception:
            pass
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
        self.kl.open()
        self.log.emit(f"Interface {c['port']} aberta")

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
            except Exception:
                pass
        self.session = None
        self.state.emit("disconnected", None)

    def _cmd_test_interface(self):
        self._ensure_port()
        ok = self.kl.echo_test()
        msg = ("Porta aberta e eco da linha K OK — o cabo está a comunicar com a ficha OBD."
               if ok else
               "A porta abriu, mas não houve eco na linha K.\n"
               "Ligue o cabo ao carro com a ignição ligada e volte a testar "
               "(sem 12 V na ficha o cabo KKL não ecoa).")
        self.result.emit("test_interface", {"ok": ok, "message": msg})

    def _cmd_autoscan(self, addresses):
        self.abort_scan = False
        self.live_mode = None
        if self.session:
            self._cmd_disconnect()
        self._ensure_port()
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
