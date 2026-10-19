"""Clone HEX-USB+CAN com microcontrolador (rad/hexmcu.py), sem hardware.

FakeHexSerial imita o FT232R + ATmega162: em modo inteligente responde aos pacotes 53/4D a 9600 baud e
engole tudo o resto (por isso não há eco KKL); em modo KKL passa os bytes para a linha K do simulador.
O DTR activo segura o microcontrolador em reset. Os formatos dos pacotes vêm da engenharia inversa
pública e ainda não foram vistos num cabo real — estes testes só garantem que o programa os usa bem.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import hexmcu                                      # noqa: E402
from rad.kline import KLine                                 # noqa: E402
from rad.simulator import SimSerial                         # noqa: E402


class FakeHexSerial:
    def __init__(self, mode=hexmcu.MODE_SMART, mcu_baud=9600, answers=True):
        self.sim = SimSerial()
        self.boot_mode = mode               # guardado na EEPROM do microcontrolador
        self.mode = mode                    # modo em que está a correr (muda ao reiniciar)
        self.mcu_baud = mcu_baud
        self.answers = answers
        self.baudrate = 10400
        self.timeout = 0.5
        self._dtr = False
        self.rts = False
        self.out = bytearray()
        self.writes = []
        self.break_condition = False

    # DTR activo = RESET do microcontrolador
    @property
    def dtr(self):
        return self._dtr

    @dtr.setter
    def dtr(self, on):
        if self._dtr and not on:
            self.mode = self.boot_mode      # arrancou outra vez
        self._dtr = bool(on)

    def reset_input_buffer(self):
        self.out.clear()
        self.sim.reset_input_buffer()

    def write(self, data):
        data = bytes(data)
        self.writes.append(data)
        if self._dtr:
            return len(data)
        if self.mode == hexmcu.MODE_DUMB and self.baudrate != self.mcu_baud:
            self.sim.baudrate = self.baudrate
            return self.sim.write(data)
        if self.baudrate != self.mcu_baud or not self.answers:
            return len(data)
        ans = hexmcu.parse(data, marker=hexmcu.HOST)
        if not ans:
            return len(data)
        op, payload = ans
        if op == hexmcu.OP_VERSION:
            self.out += hexmcu.frame(op, bytes([1, 96, ord("D")]), marker=hexmcu.DEV)
        elif op == hexmcu.OP_READ_BOOT:
            self.out += hexmcu.frame(op, bytes([self.boot_mode]), marker=hexmcu.DEV)
        elif op == hexmcu.OP_KLINE_TEST:
            self.out += hexmcu.frame(op, bytes([1, 1]), marker=hexmcu.DEV)
        elif op == hexmcu.OP_SET_BOOT:
            self.boot_mode = payload[0]
            self.out += hexmcu.frame(hexmcu.OP_ACK, marker=hexmcu.DEV)
        return len(data)

    def sim_five_baud(self, address):
        """Init a 5 baud: só chega à linha K em modo KKL (em modo inteligente o micro engole o BREAK)."""
        if self.mode == hexmcu.MODE_DUMB and not self._dtr:
            self.sim.baudrate = self.baudrate
            self.sim.sim_five_baud(address)

    def read(self, n=1):
        if self.mode == hexmcu.MODE_DUMB and not self._dtr and self.baudrate != self.mcu_baud:
            self.sim.timeout = self.timeout
            return self.sim.read(n)
        d, self.out = bytes(self.out[:n]), self.out[n:]
        return d


def test_frames():
    assert hexmcu.frame(hexmcu.OP_SET_BOOT, b"\x00") == bytes.fromhex("53050E0058")
    assert hexmcu.frame(hexmcu.OP_SET_BOOT, b"\x02") == bytes.fromhex("53050E025A")
    assert hexmcu.frame(hexmcu.OP_READ_BOOT) == bytes.fromhex("53040D5A")
    assert hexmcu.frame(hexmcu.OP_VERSION) == bytes.fromhex("53040255")
    assert hexmcu.parse(bytes.fromhex("00FF4D04FEB7")) == (0xFE, b"")
    assert hexmcu.parse(bytes.fromhex("4D04FEB8")) is None            # xor errado
    assert hexmcu.parse(bytes.fromhex("4D050D00")) is None            # incompleto


def test_hex_ports():
    assert hexmcu.is_hex_port("D2XX:RT000001")
    assert hexmcu.is_hex_port("FTDI:0403:FA24:RT000001")
    assert not hexmcu.is_hex_port("FTDI:0403:6001:A1")
    assert not hexmcu.is_hex_port("COM5") and not hexmcu.is_hex_port("")


def test_probe_finds_mcu_read_only():
    ser = FakeHexSerial(mcu_baud=115200)
    res = hexmcu.HexMcu(ser).probe()
    assert res["found"] and res["baud"] == 115200 and res["version"] == "1.96"
    assert res["mode"] == hexmcu.MODE_SMART and "inteligente" in hexmcu.describe(res)
    assert not any(w[2] == hexmcu.OP_SET_BOOT for w in ser.writes if len(w) > 2)   # só leitura
    assert ser.dtr is False


def test_probe_without_mcu():
    res = hexmcu.HexMcu(FakeHexSerial(answers=False)).probe()
    assert not res["found"] and "não respondeu" in hexmcu.describe(res)


def test_switch_to_kkl_then_kw1281_works():
    """Modo inteligente: sem eco. Depois de SetBoot(0) e reiniciar: eco e KW1281 completos."""
    ser = FakeHexSerial()
    kl = KLine("D2XX:RT000001", echo="auto")
    kl.ser = ser
    kl.set_lines(*kl.lines)
    assert kl.lines == hexmcu.HEX_LINES
    assert kl.echo_test() is False
    mcu = hexmcu.HexMcu(ser)
    assert mcu.probe()["mode"] == hexmcu.MODE_SMART
    assert mcu.set_mode(hexmcu.MODE_DUMB) == hexmcu.MODE_DUMB
    mcu.reset(boot=0)
    kl.set_baud(10400)
    assert kl.echo_test() is True
    from rad.session import ECUSession
    s = ECUSession(kl)
    info = s.connect(0x01)
    assert info["protocol"] == "KW1281" and info["part"] == "038906019FN"
    s.disconnect()
    # e volta ao original (hipótese: o micro continua a ouvir pacotes à velocidade dele)
    ser.baudrate = mcu.baud
    assert mcu.set_mode(hexmcu.MODE_SMART) == hexmcu.MODE_SMART


def test_set_mode_refused_without_valid_answer():
    ser = FakeHexSerial(answers=False)
    try:
        hexmcu.HexMcu(ser).set_mode(hexmcu.MODE_DUMB)
        assert False
    except hexmcu.HexMcuError as e:
        assert "não é seguro" in str(e)
    assert not ser.writes or all(w[2:3] != b"\x0e" for w in ser.writes)


# ------------------------------------------------------------------ Worker (Diagnóstico da ligação, Auto-Scan)
def _hex_worker(fake):
    import tempfile
    os.environ.setdefault("APPDATA", tempfile.mkdtemp())
    os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))
    from rad import worker as worker_mod
    from rad.worker import Worker
    worker_mod._usb_present = lambda port: None      # o cabo falso não está no USB do Windows
    w = Worker()
    w.cfg.update({"port": "D2XX:RT000001", "echo": "auto"})
    ev = {"error": [], "result": [], "progress": []}
    w.error.connect(lambda c, m: ev["error"].append((c, m)))
    w.result.connect(lambda c, d: ev["result"].append((c, d)))
    w.scan_progress.connect(lambda i, n, it: ev["progress"].append(it))
    kl = KLine("D2XX:RT000001", echo="auto")
    kl.ser = fake
    kl.set_lines(*kl.lines)
    w.kl = kl
    return w, ev


def test_link_check_separates_adapter_and_ecu_steps():
    """Modo inteligente, sem mudança automática: o diagnóstico distingue adaptador, linha K e modo, e pára
    antes de tentar a centralina."""
    w, ev = _hex_worker(FakeHexSerial())
    w._dispatch("link_check", (0x01,))
    steps = ev["result"][-1][1]
    names = [s[0] for s in steps]
    assert names == ["Abrir a interface", "Adaptador (microcontrolador do cabo HEX)", "Linha K vista pelo cabo",
                     "Modo do cabo", "Eco da linha K"], names
    assert [s[1] for s in steps] == [True, True, True, False, False]
    assert "K1=1, K2=1" in steps[2][2] and "ainda não está implementado" in steps[3][2]


def test_smart_mode_autoscan_explains_limit():
    w, ev = _hex_worker(FakeHexSerial())
    w._dispatch("autoscan", ([0x01],))
    assert ev["error"] and "ainda não está implementado" in ev["error"][0][1]
    assert ev["progress"] == []


def test_autoscan_reads_ecus_through_kkl_mode_cable():
    """Cabo já em modo KKL com passagem directa para a linha K (simulado): o Auto-Scan lê as centralinas."""
    w, ev = _hex_worker(FakeHexSerial(mode=hexmcu.MODE_DUMB))
    w._dispatch("autoscan", ([0x01, 0x03],))
    assert not ev["error"], ev["error"]
    assert [i["status"] for i in ev["progress"]] == ["ok", "ok"]


def test_hex_cable_without_mcu_answer_is_explained():
    w, ev = _hex_worker(FakeHexSerial(answers=False))
    w._dispatch("autoscan", ([0x01],))
    assert ev["error"] and "microcontrolador do cabo não respondeu" in ev["error"][0][1]
    assert ev["progress"] == []


def test_hex_mode_command_restores_smart():
    fake = FakeHexSerial(mode=hexmcu.MODE_DUMB)
    w, ev = _hex_worker(fake)
    w._dispatch("hex_mode", ("smart",))
    assert ev["result"][-1][1]["ok"] and fake.boot_mode == hexmcu.MODE_SMART
