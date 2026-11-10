"""Gravação e reprodução da comunicação com o carro.

Gravar: com uma gravação activa, cada byte enviado e recebido pela interface (cabo VAG, adaptador OBD) e cada
pedido à ponte J2534 fica num ficheiro .radrec, com o tempo, junto com os comandos que o programa executou e os
resultados que obteve. É o ficheiro a enviar ao suporte depois de um teste no carro.

Reproduzir: a porta "REPLAY:<ficheiro>" faz o programa falar com a gravação em vez de um carro. A gravação
devolve os bytes que o carro devolveu e confirma que o programa envia exactamente os mesmos bytes; qualquer
diferença fica registada (`divergences`). Os testes automáticos (tests/test_captures.py) reproduzem todas as
gravações de tests/captures/: cada teste feito num carro real passa a ser um teste permanente.

Formato (uma linha JSON por evento, legível num editor de texto):
  {"rad_capture": 1, "version": "1.11.0", "started": "...", "port": "...", "adapter": "kline", "simulated": false}
  {"t": 0.105, "c": "kline", "tx": "8A F1 ..."}           bytes enviados
  {"t": 0.131, "c": "kline", "rx": "55 01 8A"}            bytes recebidos
  {"t": 0.200, "c": "kline", "to": 3}                     3 leituras seguidas sem nada recebido
  {"t": 0.300, "c": "kline", "ev": "baud", "v": 10400}    controlo da porta: baud, flush, break, lines, init5
  {"t": 0.400, "c": "j2534", "call": "read", "kw": {...}, "res": {...}}
  {"t": 0.500, "note": "cmd", "cmd": "connect", "args": [1]}
  {"t": 0.900, "note": "result", "cmd": "connect", "data": {...}}
  {"t": 1.000, "note": "error", "cmd": "connect", "msg": "..."}
  {"t": 9.000, "end": true}
"""
import datetime
import json
import logging
import os
import threading
import time

from . import APP_NAME, VERSION

log = logging.getLogger(__name__)

FORMAT = 1
EXT = ".radrec"
REPLAY_PREFIX = "REPLAY:"
CONTROL = ("baud", "flush", "break", "lines", "init5")

_active = None
_active_lock = threading.Lock()
OPENED = []        # portas de reprodução abertas (rad/replay.py junta as divergências de todas)
_CURSORS = {}      # (ficheiro, canal) → onde a última porta fechada ficou: reabrir a porta continua a gravação


def reset_replay():
    """Esquece as portas de reprodução anteriores (início de uma nova reprodução)."""
    del OPENED[:]
    _CURSORS.clear()


def captures_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor", "gravacoes")
    os.makedirs(path, exist_ok=True)
    return path


def default_path(tag="sessao"):
    return os.path.join(captures_dir(), f"{tag}_{datetime.datetime.now():%Y%m%d_%H%M%S}{EXT}")


def recent(n=3):
    """As n gravações mais recentes (para o pacote de suporte)."""
    try:
        d = captures_dir()
        files = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(EXT)]
    except OSError:
        return []
    return sorted(files, key=os.path.getmtime)[-n:]


J2534_REPLAY_PREFIX = "J2534:" + REPLAY_PREFIX     # gravação feita com uma interface J2534


def is_replay_port(port):
    port = str(port or "")
    return port.startswith(REPLAY_PREFIX) or port.startswith(J2534_REPLAY_PREFIX)


def replay_port(path, transport=None):
    prefix = J2534_REPLAY_PREFIX if transport == "j2534" else REPLAY_PREFIX
    return prefix + os.path.abspath(path)


def replay_path(port):
    port = str(port)
    if port.startswith(J2534_REPLAY_PREFIX):
        return port[len(J2534_REPLAY_PREFIX):]
    if port.startswith("J2534:"):                  # J2534Link guarda a parte depois de "J2534:"
        port = port[len("J2534:"):]
    return port[len(REPLAY_PREFIX):]


def _hex(data):
    return " ".join(f"{b:02X}" for b in data)


def _unhex(text):
    return bytes.fromhex(text) if text else b""


def jsonable(obj, depth=0):
    """Converte um resultado do programa em algo que o json aceita (bytes → hex, tuplos → listas...)."""
    if depth > 8:
        return repr(obj)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (bytes, bytearray)):
        return _hex(obj)
    if isinstance(obj, dict):
        return {str(k): jsonable(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v, depth + 1) for v in obj]
    return repr(obj)


# ------------------------------------------------------------------ resumo estável dos resultados
def _faults(faults):
    return [[f.get("vag") or f.get("code"), f.get("status")] for f in faults or [] if isinstance(f, dict)]


def summarize(cmd, data):
    """Parte estável de um resultado (não depende do idioma nem da hora): é o que os testes comparam."""
    try:
        if cmd in ("connect", "connected") and isinstance(data, dict):
            return {k: data.get(k) for k in ("address", "protocol", "part", "component", "coding", "wsc")}
        if cmd in ("read_faults", "clear_faults"):
            return _faults(data)
        if cmd in ("read_group", "basic_setting") and isinstance(data, dict):
            return {"group": data.get("group"), "raw": jsonable(data.get("raw"))}
        if cmd in ("adaptation_read", "adaptation_test", "adaptation_save", "service_reset") and data:
            return {k: data.get(k) for k in ("channel", "value", "status")}
        if cmd == "recode" and isinstance(data, dict):
            return {"status": data.get("status"), "coding": (data.get("info") or {}).get("coding")}
        if cmd in ("autoscan", "clear_all") and isinstance(data, dict):
            items = data.get("items") or []
            return [{"address": i.get("address"), "status": i.get("status"), "faults": _faults(i.get("faults"))}
                    for i in items]
        if cmd == "obd_connect" and isinstance(data, dict):
            ecus = [[e.get("ecu"), e.get("pids")] for e in data.get("ecus") or [] if isinstance(e, dict)]
            return {"vin": data.get("vin"), "protocol": data.get("protocol"), "ecus": ecus}
        if cmd == "obd_dtcs" and isinstance(data, dict):
            return jsonable({k: sorted(d.get("code") for d in v if isinstance(d, dict))
                             for k, v in data.items() if isinstance(v, list)})
        if cmd == "validation" and isinstance(data, dict):
            return [[s.get("id"), s.get("result")] for s in data.get("steps") or []]
    except Exception:
        log.debug("Resumo do resultado %s falhou", cmd, exc_info=True)
    return None


# ------------------------------------------------------------------------------- gravação
class Recorder:
    """Escreve a gravação à medida que acontece (um corte de energia não perde o que já foi gravado)."""

    def __init__(self, path, meta=None):
        self.path = path
        self.meta = dict(meta or {})
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._fh = open(path, "w", encoding="utf-8")
        self._t0 = time.monotonic()
        self._lock = threading.Lock()
        self._pending = None              # último "to" (leituras vazias seguidas juntam-se num só evento)
        # Num carro, cada byte vai logo para o ficheiro: se o programa ou o PC forem abaixo a meio de uma ligação,
        # a gravação tem os últimos bytes — os que explicam o que correu mal. No simulador não é preciso.
        self._flush_always = not self.meta.get("simulated", False)
        self.events = 0
        self.closed = False
        head = {"rad_capture": FORMAT, "app": APP_NAME, "version": VERSION,
                "started": datetime.datetime.now().isoformat(timespec="seconds")}
        head.update(self.meta)
        self._write(head)

    def _now(self):
        return round(time.monotonic() - self._t0, 4)

    def _write(self, obj):
        self._fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def _flush_pending(self):
        if self._pending is not None:
            self._write(self._pending)
            self._pending = None

    def _emit(self, obj):
        with self._lock:
            if self.closed:
                return
            if "to" in obj:
                p = self._pending
                if p is not None and p.get("c") == obj.get("c"):
                    p["to"] += obj["to"]
                    return
                self._flush_pending()
                self._pending = obj
                return
            self._flush_pending()
            self._write(obj)
            self.events += 1
            if self._flush_always or "note" in obj or "call" in obj:
                self._fh.flush()

    # ---- bytes e controlo
    def tx(self, channel, data):
        if data:
            self._emit({"t": self._now(), "c": channel, "tx": _hex(data)})

    def rx(self, channel, data):
        if data:
            self._emit({"t": self._now(), "c": channel, "rx": _hex(data)})
        else:
            self._emit({"t": self._now(), "c": channel, "to": 1})

    def control(self, channel, kind, value=None, **extra):
        ev = {"t": self._now(), "c": channel, "ev": kind}
        if value is not None:
            ev["v"] = value
        ev.update(extra)
        self._emit(ev)

    def call(self, op, kw, res=None, error=None):
        ev = {"t": self._now(), "c": "j2534", "call": op, "kw": jsonable(kw)}
        if error is not None:
            ev["error"] = str(error)
        else:
            ev["res"] = jsonable(res)
        self._emit(ev)

    # ---- o que o programa fez
    def note(self, kind, **data):
        ev = {"t": self._now(), "note": kind}
        ev.update(jsonable(data))
        self._emit(ev)

    def close(self):
        with self._lock:
            if self.closed:
                return
            self._flush_pending()
            self._write({"t": self._now(), "end": True})
            self.closed = True
            try:
                self._fh.close()
            except OSError:
                pass


def start(path, meta=None):
    """Começa uma gravação e torna-a a activa. Fecha a anterior, se houver."""
    global _active
    rec = Recorder(path, meta)
    with _active_lock:
        old, _active = _active, rec
    if old is not None:
        old.close()
    log.info("Gravação iniciada: %s", path)
    return rec


def stop():
    """Termina a gravação activa. Devolve o caminho do ficheiro (ou None)."""
    global _active
    with _active_lock:
        rec, _active = _active, None
    if rec is None:
        return None
    rec.close()
    log.info("Gravação terminada: %s (%d eventos)", rec.path, rec.events)
    return rec.path


def active():
    return _active


def note(kind, **data):
    rec = _active
    if rec is not None:
        try:
            rec.note(kind, **data)
        except Exception:
            log.warning("Gravação: não foi possível registar %s", kind, exc_info=True)


class RecordingSerial:
    """Envolve uma porta (serial.Serial, FTDI, D2XX, simulador) e grava o que passa por ela.
    Tudo o que não é leitura/escrita/controlo passa directamente para a porta original."""

    _OWN = ("_inner", "_channel")

    def __init__(self, inner, channel):
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_channel", channel)

    @property
    def inner(self):
        return self._inner

    def _rec(self):
        return _active

    def read(self, n=1):
        data = self._inner.read(n)
        rec = self._rec()
        if rec is not None:
            rec.rx(self._channel, data)
        return data

    def write(self, data):
        rec = self._rec()
        if rec is not None:
            rec.tx(self._channel, bytes(data))
        return self._inner.write(data)

    def reset_input_buffer(self):
        rec = self._rec()
        if rec is not None:
            rec.control(self._channel, "flush")
        return self._inner.reset_input_buffer()

    def capture_init(self, address, baud):
        """Chamado pelo KLine antes de um init a 5 baud feito por BREAK (marca o endereço na gravação)."""
        rec = self._rec()
        if rec is not None:
            rec.control(self._channel, "init5", address=address, baud=baud)

    def __getattr__(self, name):
        if name == "sim_five_baud":
            fn = getattr(self._inner, "sim_five_baud")      # AttributeError se a porta não for o simulador

            def sim_five_baud(address):
                rec = self._rec()
                if rec is not None:
                    rec.control(self._channel, "init5", address=address, baud=getattr(self._inner, "baudrate", None))
                return fn(address)
            return sim_five_baud
        return getattr(self._inner, name)

    def __setattr__(self, name, value):
        rec = self._rec()
        if rec is not None:
            if name == "baudrate":
                rec.control(self._channel, "baud", value)
            elif name == "break_condition":
                rec.control(self._channel, "break", bool(value))
            elif name in ("dtr", "rts"):
                rec.control(self._channel, "lines", [name, bool(value)])
        setattr(self._inner, name, value)


def wrap_serial(ser, channel):
    """Com uma gravação activa devolve a porta envolvida pela gravação; senão a própria porta."""
    if ser is None or _active is None or isinstance(ser, (RecordingSerial, ReplaySerial)):
        return ser
    return RecordingSerial(ser, channel)


def unwrap_serial(ser):
    return ser.inner if isinstance(ser, RecordingSerial) else ser


# ------------------------------------------------------------------------------- leitura
def load(path):
    """Devolve (cabeçalho, eventos). Linhas estragadas no fim (gravação interrompida) são ignoradas."""
    head, events = None, []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                log.warning("%s: linha %d ilegível (gravação interrompida?)", path, n + 1)
                continue
            if head is None:
                if obj.get("rad_capture") is None:
                    raise ValueError("não é uma gravação do Roots Auto Doctor")
                head = obj
                continue
            events.append(obj)
    if head is None:
        raise ValueError("ficheiro vazio")
    return head, events


def script(events):
    """Os comandos que o programa executou, pela ordem: [(cmd, args), ...]."""
    return [(e["cmd"], tuple(e.get("args") or ())) for e in events if e.get("note") == "cmd"]


def results(events):
    """[(cmd, resumo)] dos resultados gravados, pela ordem (só os que têm resumo)."""
    out = []
    for e in events:
        if e.get("note") == "result" and e.get("summary") is not None:
            out.append((e["cmd"], e["summary"]))
    return out


def stats(head, events):
    """Resumo de uma gravação para mostrar ao técnico."""
    tx = sum(len(_unhex(e["tx"])) for e in events if "tx" in e)
    rx = sum(len(_unhex(e["rx"])) for e in events if "rx" in e)
    calls = sum(1 for e in events if "call" in e)
    cmds = [e["cmd"] for e in events if e.get("note") == "cmd"]
    errors = [e for e in events if e.get("note") == "error"]
    duration = events[-1]["t"] if events and "t" in events[-1] else 0
    return {"version": head.get("version"), "started": head.get("started"), "adapter": head.get("adapter"),
            "simulated": bool(head.get("simulated")), "bytes_tx": tx, "bytes_rx": rx, "j2534_calls": calls,
            "commands": cmds, "errors": len(errors), "duration": duration,
            "complete": bool(events and events[-1].get("end"))}


class ReplaySerial:
    """Porta que responde com uma gravação. Imita o serial.Serial o suficiente para o KLine e o ELM327.

    Regras: os eventos de controlo (velocidade, break, linhas...) são indicativos e saltam-se; uma leitura devolve
    os próximos bytes recebidos (ou nada, se a gravação diz que nesse ponto nada chegou ou que era a vez do
    programa enviar); uma escrita tem de ser igual aos próximos bytes enviados na gravação — senão fica uma
    divergência."""

    def __init__(self, events, channel="kline", path=""):
        self.path = path
        self.channel = channel
        self.ev = [e for e in events if e.get("c", channel) == channel and
                   ("tx" in e or "rx" in e or "to" in e or "ev" in e)]
        self.i = 0
        self._rx_off = 0
        self._to_left = None
        self.divergences = []
        self.baudrate = 10400
        self.timeout = 0.5
        self.write_timeout = 1.0
        self.break_condition = False
        self.dtr = True
        self.rts = False
        self.writes = 0

    @classmethod
    def open(cls, path, channel="kline"):
        _head, events = load(path)
        port = cls(events, channel, path)
        port.i = _CURSORS.get((path, channel), 0)
        OPENED.append(port)
        return port

    # ---- cursor
    def _skip_control(self):
        while self.i < len(self.ev) and "ev" in self.ev[self.i]:
            self.i += 1

    def _peek(self):
        self._skip_control()
        return self.ev[self.i] if self.i < len(self.ev) else None

    def _advance(self):
        self.i += 1
        self._rx_off = 0
        self._to_left = None

    def _diverge(self, what, **detail):
        if len(self.divergences) < 50:
            d = {"what": what, "event": self.i}
            d.update(detail)
            self.divergences.append(d)

    # ---- API série
    @property
    def in_waiting(self):
        e = self._peek()
        if e is not None and "rx" in e:
            return len(_unhex(e["rx"])) - self._rx_off
        return 0

    def read(self, n=1):
        e = self._peek()
        if e is None:
            return b""
        if "to" in e:
            if self._to_left is None:
                self._to_left = int(e["to"])
            self._to_left -= 1
            if self._to_left <= 0:
                self._advance()
            return b""
        if "rx" not in e:
            return b""                                   # era a vez do programa enviar: nada chega
        data = _unhex(e["rx"])
        out = data[self._rx_off:self._rx_off + n]
        self._rx_off += len(out)
        if self._rx_off >= len(data):
            self._advance()
        return out

    def write(self, data):
        data = bytes(data)
        self.writes += 1
        skipped = 0
        pos = 0
        while pos < len(data):
            e = self._peek()
            if e is None:
                self._diverge("escrita a mais", sent=_hex(data[pos:]))
                return len(data)
            if "tx" not in e:
                skipped += len(_unhex(e["rx"])) - self._rx_off if "rx" in e else 0
                self._advance()
                continue
            expected = _unhex(e["tx"])
            chunk = expected[self._rx_off:]
            take = min(len(chunk), len(data) - pos)
            if chunk[:take] != data[pos:pos + take]:
                self._diverge("bytes diferentes", expected=_hex(chunk[:take]), sent=_hex(data[pos:pos + take]))
            pos += take
            self._rx_off += take
            if self._rx_off >= len(expected):
                self._advance()
        if skipped:
            self._diverge("bytes recebidos não lidos", count=skipped)
        return len(data)

    def reset_input_buffer(self):
        j = self.i
        if j < len(self.ev) and self.ev[j].get("ev") == "flush":
            self._advance()

    def sim_five_baud(self, address):
        """O KLine usa este caminho (o do simulador) para não esperar 2 s de bits a 5 baud."""
        for j in range(self.i, len(self.ev)):
            e = self.ev[j]
            if e.get("ev") == "init5":
                if e.get("address") is not None and (e["address"] & 0x7F) != (address & 0x7F):
                    self._diverge("init noutro endereço", expected=e["address"], sent=address)
                self.i = j + 1
                self._rx_off = 0
                self._to_left = None
                return
            if "tx" in e:
                break                                    # bytes recebidos antes de um init são restos: ignoram-se
        self._diverge("init a 5 baud que não está na gravação", sent=address)

    def close(self):
        if self.path:
            _CURSORS[(self.path, self.channel)] = self.i if not self._rx_off else self.i + 1

    def cancel_read(self):
        pass

    @property
    def finished(self):
        return self._peek() is None

    def report(self):
        left_tx = sum(1 for e in self.ev[self.i:] if "tx" in e)
        return {"divergences": list(self.divergences), "events": len(self.ev), "used": self.i,
                "unsent": left_tx}


class ReplayBridge:
    """Substitui a ponte J2534 por uma gravação: cada pedido devolve a resposta gravada para o mesmo pedido."""

    def __init__(self, events, path=""):
        self.path = path
        self.calls = [e for e in events if "call" in e]
        self.i = 0
        self.divergences = []

    @classmethod
    def open(cls, path):
        _head, events = load(path)
        bridge = cls(events, path)
        bridge.i = _CURSORS.get((path, "j2534"), 0)
        OPENED.append(bridge)
        return bridge

    READS = ("read", "can_read")

    @staticmethod
    def _empty(op):
        return {"ok": True, "data": None} if op == "read" else {"ok": True, "frame": None}

    @staticmethod
    def _got_data(e):
        res = e.get("res") or {}
        return bool(res.get("data") or res.get("frame"))

    def call(self, req, timeout=None):
        """As leituras seguem a gravação (o número de leituras vazias pode variar com o tempo de resposta do PC):
        uma leitura a mais devolve "nada"; um pedido que chega antes das leituras gravadas salta as que vieram
        vazias (e regista as que traziam dados, que o programa já não leu)."""
        op = req.get("op")
        if op in self.READS:
            if self.i < len(self.calls) and self.calls[self.i]["call"] == op:
                e = self.calls[self.i]
                self.i += 1
                return dict(e.get("res") or self._empty(op))
            return self._empty(op)
        while self.i < len(self.calls) and self.calls[self.i]["call"] in self.READS:
            if self._got_data(self.calls[self.i]):
                self.divergences.append({"what": "dados recebidos não lidos", "event": self.i})
            self.i += 1
        while self.i < len(self.calls):
            e = self.calls[self.i]
            self.i += 1
            if e["call"] != op:
                self.divergences.append({"what": "pedido diferente", "expected": e["call"], "sent": op})
                continue
            if op == "can_write" and (e.get("kw", {}).get("id") != req.get("id")
                                      or e.get("kw", {}).get("data") != req.get("data")):
                self.divergences.append({"what": "bytes diferentes", "expected": e.get("kw"),
                                         "sent": {"id": req.get("id"), "data": req.get("data")}})
            if op == "write" and e.get("kw", {}).get("data") != req.get("data"):
                self.divergences.append({"what": "bytes diferentes", "expected": e["kw"].get("data"),
                                         "sent": req.get("data")})
            if "error" in e:
                return {"ok": False, "error": e["error"]}
            return dict(e.get("res") or {"ok": True})
        self.divergences.append({"what": "pedido a mais", "sent": op})
        return {"ok": True}

    def close(self):
        if self.path:
            _CURSORS[(self.path, "j2534")] = self.i

    def kill(self):
        self.close()

    def report(self):
        return {"divergences": list(self.divergences), "events": len(self.calls), "used": self.i,
                "unsent": sum(1 for e in self.calls[self.i:] if e["call"] in ("write", "can_write"))}
