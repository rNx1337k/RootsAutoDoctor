"""Thread de comunicação: toda a conversa com o carro acontece aqui, fora da UI.

A UI envia comandos com submit(); os resultados voltam por sinais Qt.
Quando não há comandos, a thread mantém a ligação viva (keep-alive) ou faz a
leitura contínua dos grupos de medição.
"""
import logging
import queue
import sys
import time
import traceback

from PySide6.QtCore import QThread, Signal

from .kline import KLine, is_simulated_port
from .j2534 import J2534Link, is_j2534_port
from .session import ECUSession
from .errors import (InterfaceError, NoResponse, NotSupported, OperationUnconfirmed, ProtocolError,
                     RequestRejected)
from . import connstate, hexmcu, vag_data

log = logging.getLogger(__name__)


class Worker(QThread):
    STOP_WAIT_MS = 5000                     # tempo para a thread terminar sozinha ao fechar o programa
    log = Signal(str)
    state = Signal(str, object)            # antigo (UI): "disconnected" | "connecting" | "connected"
    link_state = Signal(object)            # detalhado (connstate.LinkStatus): ver rad/connstate.py
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
        self.hex_info = None               # último probe do microcontrolador do clone HEX (por porta aberta)

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
        if self.wait(self.STOP_WAIT_MS):
            return
        # A thread está presa numa operação da interface (driver bloqueado, cabo arrancado a meio):
        # fechar a interface à força faz a operação falhar e a thread terminar.
        log.warning("A thread de comunicação não terminou em 5 s: a fechar a interface à força")
        self._force_close()
        if not self.wait(self.STOP_WAIT_MS):
            log.error("A thread de comunicação continua bloqueada; o programa vai fechar mesmo assim")

    def _force_close(self):
        """Chamado de outra thread: termina as pontes D2XX/J2534 e cancela leituras série pendentes."""
        kl = self.kl
        if kl is None:
            return
        for obj in (kl, getattr(kl, "ser", None)):
            if obj is None:
                continue
            for name in ("kill", "cancel_read", "cancel_write"):
                fn = getattr(obj, name, None)
                if callable(fn):
                    try:
                        fn()
                    except Exception:
                        log.warning("Fecho forçado: %s falhou", name, exc_info=True)

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
                if isinstance(e, InterfaceError):
                    self._drop_port()
            except Exception as e:
                self._quiet = False
                if isinstance(e, (RequestRejected, NotSupported)):
                    log.warning("Leitura contínua / keep-alive recusado: %s", e)
                else:
                    log.exception("Erro na leitura contínua / keep-alive")
                self.log.emit(f"Erro: {e}")
                # sem isto, um keep-alive recusado (resposta negativa) repetia-se em ciclo apertado
                last = time.monotonic()
            finally:
                self._quiet = False
        self._close_all()

    def _log(self, msg):
        if not self._quiet:
            self.log.emit(msg)

    def _emit_link(self, status):
        """Emite o estado detalhado (connstate.LinkStatus). O sinal antigo `state` continua a ser emitido
        à parte, com os valores que a interface actual espera; este é informação adicional e mais precisa."""
        self.link_state.emit(status)
        log.info("Estado da ligação: %s — %s", status.state, status.message)

    def _port_present(self):
        """True/False se a porta escolhida aparece na lista de interfaces do computador; None se não se
        conseguir saber. Serve para distinguir "interface não detectada" de "detectada mas inacessível"."""
        port = self.cfg.get("port") or ""
        if not port or is_simulated_port(port):
            return None
        try:
            from .kline import list_serial_ports
            return any(dev == port for dev, _desc in list_serial_ports())
        except Exception:
            log.warning("Não foi possível verificar a presença da interface", exc_info=True)
            return None

    def _lost(self, reason):
        self.live_mode = None
        self.log.emit(f"Ligação perdida: {reason}")
        self.session = None
        self.state.emit("disconnected", reason)
        self._emit_link(connstate.LinkStatus(connstate.OPEN_NO_ECU,
                                             f"Ligação à centralina perdida: {reason}"))

    def _drop_port(self):
        """A interface falhou: fecha-a para que o próximo comando a volte a abrir do zero
        (ex.: depois de voltar a ligar o cabo ao USB)."""
        self.session = None
        if self.kl is not None:
            try:
                self.kl.close()
            except Exception:
                log.warning("Erro ao fechar a interface que falhou", exc_info=True)
        self.kl = None
        self.hex_info = None
        self.log.emit("Interface fechada depois de um erro; será reaberta no próximo comando.")
        present = self._port_present()
        state = connstate.NO_DEVICE if present is False else connstate.UNREACHABLE
        self._emit_link(connstate.LinkStatus(state, connstate.LABELS[state], fatal=True))

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
        self.hex_info = None
        self.log.emit(f"Interface {c['port']} aberta")
        self._emit_link(connstate.opened(c["port"]))

    def _hex_check(self):
        """Clone HEX-USB+CAN sem eco: pergunta ao microcontrolador do cabo a versão, o modo de arranque e o
        estado da linha K. Devolve o resultado (também em self.hex_info)."""
        mcu = hexmcu.HexMcu(self.kl.ser, log=self._log)
        res = mcu.probe()
        res["kline"] = None
        self.log.emit("Cabo HEX: " + hexmcu.describe(res))
        if res["found"]:
            try:
                res["kline"] = hexmcu.kline_test(mcu)
            except Exception:
                log.warning("Teste da linha K pelo cabo HEX falhou", exc_info=True)
            if res["kline"] is not None:
                self.log.emit("Cabo HEX: linha K vista pelo cabo — " + hexmcu.describe_kline(res["kline"]))
        self.kl.set_baud(10400)
        self.kl.set_lines(*hexmcu.HEX_LINES)
        self.hex_info = res
        return res

    def _echo(self):
        """Teste de eco; se falhar, procura o DTR/RTS que liga o transceptor e guarda-o para esta porta.
        No clone HEX, se continuar sem eco, pergunta ao microcontrolador do cabo o que se passa."""
        if getattr(self.kl, "is_j2534", False):
            return self.kl.echo_test(), ""
        ok, note = self._echo_lines()
        if ok or not getattr(self.kl, "is_hex", False) or self.kl.is_simulator:
            return ok, note
        if self.hex_info is None:
            res = self._hex_check()
            if res.get("found") and res.get("mode") == hexmcu.MODE_DUMB:
                ok, note = self._echo_lines()
        return ok, note

    def _echo_lines(self):
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
            raise ProtocolError(no_echo_text(self.cfg.get("port", ""), self.hex_info))
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
            if self.session is not None and not self.session.connected:   # ex.: releitura falhou por perda de ligação
                self.session = None
                self.state.emit("disconnected", str(e))
                self._emit_link(connstate.classify_error(e))
        except ProtocolError as e:
            self.error.emit(cmd, str(e))
            drop = isinstance(e, InterfaceError)
            if cmd == "connect" or (self.session and not self.session.connected) or drop:
                if self.session is not None or cmd == "connect":
                    self.state.emit("disconnected", str(e))
                    if not drop:            # _drop_port() emite o seu próprio estado detalhado
                        self._emit_link(connstate.classify_error(e, self._port_present()))
                self.session = None
            if drop:
                self._drop_port()
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
        self._emit_link(connstate.connecting(address))
        self._preflight()
        s = ECUSession(self.kl, self._log, self.cfg["baud"])
        info = s.connect(address, retry=True)
        self.session = s
        self.log.emit(f"Ligado a {address:02X} — {info['part']} {info['component']}")
        self.state.emit("connected", info)
        self._emit_link(connstate.connected(info))

    def _cmd_disconnect(self):
        self.live_mode = None
        if self.session:
            try:
                self.session.disconnect()
            except Exception as e:
                log.info("Erro ao desligar a sessão: %s", e)
        self.session = None
        self.state.emit("disconnected", None)
        if self.kl is not None and self.kl.is_open:
            self._emit_link(connstate.LinkStatus(connstate.OPEN_NO_ECU,
                            "Controlador fechado. A interface continua aberta."))
        else:
            self._emit_link(connstate.LinkStatus(connstate.NO_DEVICE, "Sem ligação."))

    def _cmd_test_interface(self):
        self._ensure_port()
        ok, note = self._echo()
        msg = ("Porta aberta e eco da linha K OK — o cabo está a comunicar com a ficha OBD." + note
               if ok else "A porta abriu. " + no_echo_text(self.cfg.get("port", ""), self.hex_info))
        self.result.emit("test_interface", {"ok": ok, "message": msg})

    def _cmd_hex_mode(self, mode):
        """Lê ("read") ou repõe ("smart") o modo de arranque de origem do microcontrolador do clone HEX."""
        self.live_mode = None
        if self.session:
            self._cmd_disconnect()
        self._ensure_port()
        if not getattr(self.kl, "is_hex", False):
            raise ProtocolError("A porta escolhida não é um cabo HEX (D2XX:… ou FTDI:0403:FA2x:…)")
        mcu = hexmcu.HexMcu(self.kl.ser, log=self._log)
        try:
            res = mcu.probe()
            msg = hexmcu.describe(res)
            if res["found"] and mode == "smart":
                now = mcu.set_mode(hexmcu.MODE_SMART)
                mcu.reset(boot=1.0)
                msg += f"\n\nModo de arranque agora: {hexmcu.MODE_NAMES.get(now, now)}"
                res["mode"] = now
            ok = bool(res["found"])
        except hexmcu.HexMcuError as e:
            ok, msg = False, str(e)
        finally:
            self.kl.set_baud(10400)
            self.kl.set_lines(*hexmcu.HEX_LINES)
            self.hex_info = None
        self.result.emit("hex_mode", {"ok": ok, "message": msg})

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
            present = _usb_present(port)
            if present is not None:
                steps.append(("Cabo detectado no USB", present,
                              "O Windows vê a interface" if present else
                              "O Windows não vê a interface: ligue o cabo ao USB (ou troque de porta/cabo USB)"))
                if not present:
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
                except Exception as e:
                    log.warning("Teste de eco falhou", exc_info=True)
                    ok, note = False, ""
                    if self.hex_info is None and getattr(self.kl, "is_hex", False):
                        self.hex_info = {"found": False, "raw": [str(e)]}
                h = self.hex_info
                if h is not None:
                    steps.append(("Adaptador (microcontrolador do cabo HEX)", bool(h.get("found")),
                                  hexmcu.describe(h)))
                    if h.get("found") and h.get("kline") is not None:
                        steps.append(("Linha K vista pelo cabo", True, hexmcu.describe_kline(h["kline"])))
                    if h.get("found"):
                        if h.get("mode") == hexmcu.MODE_DUMB:
                            steps.append(("Modo do cabo", True, "KKL (linha K directa)"))
                        else:
                            steps.append(("Modo do cabo", False,
                                          "Modo inteligente: a linha K é controlada pelo microcontrolador do cabo "
                                          "e o protocolo dele para falar com as centralinas ainda não está "
                                          "implementado no Roots Auto Doctor"))
                why = ("O cabo vê a linha K do carro." + note) if ok else no_echo_text(port, h)
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
        scanned = 0
        interface_error = None
        for i, addr in enumerate(addresses):
            if self.abort_scan:
                break
            scanned += 1
            item = {"address": addr, "module": vag_data.module_name(addr)}
            try:
                s = ECUSession(self.kl, self._log, self.cfg["baud"])
                item["info"] = s.connect(addr)
                item["faults"] = s.read_faults()
                item["status"] = "ok"
                s.disconnect()
            except NoResponse:
                item["status"] = "absent"
            except InterfaceError as e:
                # a interface deixou de funcionar: não adianta tentar os endereços seguintes
                item["status"] = "error"
                item["error"] = str(e)
                interface_error = str(e)
            except Exception as e:
                item["status"] = "error"
                item["error"] = str(e)
            self.scan_progress.emit(i + 1, total, item)
            if interface_error:
                break
            if self.kl.is_simulator:
                time.sleep(0.02)
            else:
                # depois de um erro a ECU pode ficar à espera; deixá-la expirar antes do próximo init
                time.sleep(1.5 if item["status"] == "error" else 0.35)
        port = self.cfg.get("port", "")
        if interface_error:
            self._drop_port()
        self.result.emit("autoscan", {"aborted": self.abort_scan or bool(interface_error), "scanned": scanned,
                                      "total": total, "interface": port, "simulated": is_simulated_port(port),
                                      "interface_error": interface_error})

    def _cmd_clear_all(self, addresses):
        """Apaga as avarias em cada endereço e volta a ler o que ficou."""
        self.live_mode = None
        if self.session:
            self._cmd_disconnect()
        self._ensure_port()
        out = []
        interface_error = None
        for addr in addresses:
            item = {"address": addr}
            if interface_error:
                item.update(status="error", error="Não tentado: a interface deixou de responder")
                out.append(item)
                continue
            try:
                s = ECUSession(self.kl, self._log, self.cfg["baud"])
                s.connect(addr, retry=True)
                item["faults"] = s.clear_faults()
                item["status"] = "ok"
                s.disconnect()
            except OperationUnconfirmed as e:
                item["status"] = "unknown"           # o apagar foi enviado, mas não se sabe o que ficou
                item["error"] = str(e)
                if isinstance(e.__cause__, InterfaceError):
                    interface_error = str(e.__cause__)
            except InterfaceError as e:
                item["status"] = "error"
                item["error"] = str(e)
                interface_error = str(e)
            except Exception as e:
                item["status"] = "error"
                item["error"] = str(e)
            out.append(item)
            self.log.emit(f"Apagar avarias {addr:02X}: "
                          f"{'ficaram ' + str(len(item['faults'])) if item['status'] == 'ok' else item['error']}")
            if not interface_error:
                time.sleep(0.02 if self.kl.is_simulator else (1.5 if item["status"] != "ok" else 0.35))
        if interface_error:
            self._drop_port()
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


def no_echo_text(port, hex_info=None):
    """Explicação para quando o byte enviado não volta da linha K."""
    if hex_info and hex_info.get("found"):
        kl = hex_info.get("kline")
        if hex_info.get("mode") != hexmcu.MODE_DUMB:
            return ("O cabo HEX responde pelo USB (" + hexmcu.describe(hex_info) + ")"
                    + (f"; linha K: {hexmcu.describe_kline(kl)}" if kl is not None else "")
                    + ". Em modo inteligente a linha K é controlada pelo microcontrolador do cabo, cujo protocolo "
                    "de comunicação com as centralinas ainda não está implementado no Roots Auto Doctor: este "
                    "cabo ainda não pode ler o carro.")
        return ("Sem eco na linha K. O cabo responde pelo USB e está em modo KKL, mas a linha K não devolve os "
                "bytes: confirme que o cabo está bem encaixado na ficha OBD e que a ignição está ligada "
                "(sem 12 V no pino 16 o transceptor da linha K não funciona).")
    if hex_info is not None and port.startswith(("FTDI:", "D2XX:")):
        return ("Sem eco na linha K e o microcontrolador do cabo não respondeu. Desligue e volte a ligar o "
                "cabo ao USB, feche outros programas que o possam estar a usar e repita com o cabo na ficha OBD "
                "e a ignição ligada. Detalhe: " + hexmcu.describe(hex_info))
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


def _usb_present(port):
    """True/False se o Windows vê a interface FTDI/D2XX desta porta; None quando não se aplica."""
    if not port.startswith(("FTDI:", "D2XX:")) or port.endswith("SIM00001"):
        return None
    if sys.platform != "win32":
        return None
    try:
        from .cable import list_usb_devices
        serial = port.rsplit(":", 1)[-1].upper()
        devs = list_usb_devices()
    except Exception:
        log.warning("Não foi possível verificar o USB", exc_info=True)
        return None
    return any(serial and d["id"].upper().endswith("\\" + serial) for d in devs)
