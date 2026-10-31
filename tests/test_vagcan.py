"""Diagnóstico VAG por CAN (TP2.0 + KWP2000): o canal abre, fecha e mantém-se como no protocolo real, as mensagens
longas são divididas e confirmadas (ACK), e a identificação, as avarias e os blocos de medição chegam iguais aos da
linha K. Sem carro: o lado dos controladores é o simulador (rad/vagcan/simbus.py); o adaptador ELM327/OBDLink em
modo CAN cru é imitado ao nível dos comandos AT."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad.errors import NoResponse, ProtocolError  # noqa: E402
from rad.vagcan import tp20  # noqa: E402
from rad.vagcan.elmcan import ElmCanBus, parse_frame  # noqa: E402
from rad.vagcan.kwp import VagCanKWP  # noqa: E402
from rad.vagcan.simbus import SimVagCanBus  # noqa: E402


def test_channel_setup_frames_follow_the_protocol():
    bus = SimVagCanBus()
    ch = tp20.Tp20Channel(bus, 0x01).open()
    assert bus.frames[0] == (0x200, bytes.fromhex("01C0001000 0301".replace(" ", "")))
    assert bus.frames[1] == (0x741, bytes.fromhex("A00F8AFF32FF"))
    assert (ch.tx_id, ch.rx_id) == (0x741, 0x300) and ch.block_size == 0x0F
    assert abs(ch.t3 - 0.010) < 1e-9 and abs(ch.t1 - 0.1) < 1e-9          # 0x4A = 10 × 1 ms, 0x8A = 10 × 10 ms


def test_ids_and_timings_are_decoded():
    assert tp20.decode_id(0x40, 0x07) == (0x740, True)
    assert tp20.decode_id(0x00, 0x10) == (0x000, False)
    assert tp20.encode_id(0x300) == bytes([0x00, 0x03])
    assert abs(tp20.timing_seconds(0x32) - 0.005) < 1e-9                  # 50 × 0,1 ms


def test_segmenting_long_messages_asks_ack_at_block_end_and_last_frame():
    payload = bytes(range(40))
    frames, seq = tp20.segment(payload, 0x0E, 3)
    ops = [f[0] for f in frames]
    assert ops[0] == 0x2E and ops[1] == 0x2F and ops[2] == 0x00       # 3.ª trama fecha o bloco → pede ACK
    assert ops[-1] & 0xF0 == 0x10                                      # a última pede sempre ACK
    assert frames[0][1:3] == b"\x00\x28"                               # comprimento na 1.ª trama
    assert seq == (0x0E + len(frames)) & 0x0F
    joined = b"".join(f[1:] for f in frames)[2:]
    assert joined == payload


def test_kwp_over_can_reads_ident_faults_and_live_data():
    bus = SimVagCanBus()
    p = VagCanKWP(bus, 0x01)
    ident = p.start()
    assert ident["part"] == "03G906021AB" and "EDC" in ident["component"]
    faults = p.read_faults()
    assert [f["code"] for f in faults] == [16785] and faults[0]["pcode"] == "P0401"
    fields = p.read_group(1)["fields"]
    assert fields[0]["unit"] == "/min" and 800 <= fields[0]["numeric"] <= 1000
    p.keep_alive()
    p.clear_faults()
    assert p.read_faults() == []
    p.end()
    assert bus.frames[-1][1] == bytes([tp20.OP_DISCONNECT]) and bus.channel is None


def test_absent_module_fails_fast_with_no_response():
    bus = SimVagCanBus()
    try:
        VagCanKWP(bus, 0x25).start()
        assert False, "um controlador ausente não pode abrir canal"
    except NoResponse as e:
        assert "25" in str(e)
    muted = SimVagCanBus(mute=[0x03])
    try:
        VagCanKWP(muted, 0x03).start()
        assert False
    except NoResponse:
        pass


def test_missing_ack_drops_the_channel():
    bus = SimVagCanBus(no_ack=[0x17])
    p = VagCanKWP(bus, 0x17)
    try:
        p.start()
        assert False, "sem ACK o canal tem de cair"
    except ProtocolError:
        pass
    assert not p.channel.is_open


def test_auto_scan_style_loop_over_all_addresses():
    bus = SimVagCanBus()
    found = []
    for addr in (0x01, 0x02, 0x03, 0x08, 0x15, 0x17, 0x19, 0x46):
        p = VagCanKWP(bus, addr)
        try:
            p.start()
        except NoResponse:
            continue
        found.append(addr)
        p.end()
    assert found == [0x01, 0x03, 0x08, 0x15, 0x17, 0x19]


# ------------------------------------------------------------------ adaptador ELM327 em modo CAN cru (imitação)
class FakeElmRawCan:
    """Imita a porta série de um ELM327 com os comandos que o ElmCanBus usa, ligado a um SimVagCanBus."""

    def __init__(self, bus):
        self.bus = bus
        self.header = 0x7DF
        self.filter = None
        self.out = bytearray()
        self.monitoring = False
        self.commands = []
        self.baudrate = 38400
        self.timeout = 0.05

    def reset_input_buffer(self):
        self.out.clear()

    def _frames(self):
        lines = []
        while self.bus.rx:
            arb, data = self.bus.rx.popleft()
            if self.filter is None or arb == self.filter:
                lines.append(f"{arb:03X} " + " ".join(f"{b:02X}" for b in data))
        return lines

    def write(self, data):
        text = data.decode("ascii").strip()
        if self.monitoring:                         # qualquer carácter pára o ATMA
            self.monitoring = False
            self.out += b"\r>"
            return len(data)
        if not text:
            self.out += b"\r>"
            return len(data)
        self.commands.append(text)
        up = text.upper()
        if up in ("ATZ", "ATI"):
            reply = ["ELM327 v1.5"]
        elif up == "ATRV":
            reply = ["12.4V"]
        elif up == "AT@1":
            reply = ["OBDII to RS232 Interpreter"]
        elif up.startswith("ATSH"):
            self.header, reply = int(up[4:], 16), ["OK"]
        elif up.startswith("ATCRA"):
            self.filter, reply = int(up[5:], 16), ["OK"]
        elif up == "ATMA":
            self.monitoring = True
            self.out += ("\r".join(self._frames()) + "\r").encode()
            return len(data)
        elif up.startswith("AT"):
            reply = ["OK"]
        else:
            self.bus.send(self.header, bytes.fromhex(up))
            reply = self._frames() or ["NO DATA"]
        self.out += ("\r".join(reply) + "\r\r>").encode()
        return len(data)

    def read(self, n=1):
        chunk, self.out = bytes(self.out[:n]), self.out[n:]
        return chunk

    def close(self):
        pass


def test_frame_lines_from_the_adapter_are_parsed():
    assert parse_frame("300 10 00 02 50 89") == (0x300, bytes.fromhex("1000025089"))
    assert parse_frame("300B1") == (0x300, b"\xb1")
    for junk in ("NO DATA", "OK", "?", "SEARCHING...", "", "ELM327 v1.5"):
        assert parse_frame(junk) is None


def test_kwp_over_can_through_an_elm327_in_raw_can_mode():
    sim = SimVagCanBus()
    fake = FakeElmRawCan(sim)
    bus = ElmCanBus("COM9", serial_factory=lambda port, baud: fake)
    bus.open()
    for cmd in ("ATSP6", "ATCAF0", "ATH1"):
        assert cmd in fake.commands, cmd
    p = VagCanKWP(bus, 0x01)
    assert p.start()["part"] == "03G906021AB"
    assert [f["code"] for f in p.read_faults()] == [16785]
    assert p.read_group(1)["fields"][0]["unit"] == "/min"           # resposta em várias tramas, com ACK
    p.end()
    assert "ATSH200" in fake.commands and "ATCRA201" in fake.commands and "ATCRA300" in fake.commands


# ------------------------------------------------------------------ na thread de comunicação (como no programa)
def _worker(port, adapter="kline"):
    import tempfile
    os.environ.setdefault("APPDATA", tempfile.mkdtemp())
    os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": port, "adapter": adapter})
    results, errors = [], []
    w.result.connect(lambda c, d: results.append((c, d)))
    w.error.connect(lambda c, m: errors.append((c, m)))
    progress = []
    w.scan_progress.connect(lambda i, n, it: progress.append(it))
    return w, results, errors, progress


def test_worker_connects_and_scans_vag_modules_over_can():
    from rad.vagcan import SIM_PORT
    w, results, errors, progress = _worker(SIM_PORT)
    states = []
    w.state.connect(lambda s, d: states.append((s, d)))
    w._dispatch("connect", (0x01,))
    assert not errors, errors
    info = [d for s, d in states if s == "connected"][0]
    assert info["part"] == "03G906021AB" and info["simulated"] and "CAN" in info["protocol"]
    w._dispatch("read_faults", ())
    assert [f["code"] for f in dict(results)["read_faults"]] == [16785]
    w._dispatch("disconnect", ())
    w._dispatch("autoscan", ([0x01, 0x02, 0x03, 0x17, 0x19],))
    assert not errors, errors
    assert [i["status"] for i in progress] == ["ok", "absent", "ok", "ok", "ok"]
    assert dict(results)["autoscan"]["simulated"]


def test_obd_simulator_explains_it_has_no_vag_modules():
    from rad.kline import SIM_ELM_PORT
    w, results, errors, progress = _worker(SIM_ELM_PORT, adapter="elm327")
    w._dispatch("connect", (0x01,))
    assert errors and "Simulador VAG por CAN" in errors[0][1]
