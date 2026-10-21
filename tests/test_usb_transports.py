"""Transportes USB para o clone HEX-USB (chip FTDI, VID 0403 PID FA24), sem hardware.

- FtdiSerial (rad/ftdi_direct.py) com um chip FTDI falso que emula a linha K ao nível físico: o endereço do
  init a 5 baud é descodificado a partir dos tempos do sinal BREAK, como faria a centralina.
- D2xxSerial (rad/d2xx.py) com a ponte D2XX real (processo à parte) e o backend simulado.
- Classificação dos estados de driver do clone HEX-USB em rad/cable.py.

Nada disto prova que o cabo real funciona — ver docs/HEX_USB.md para os testes com hardware.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import cable, d2xx, ftdi_direct
from rad.errors import KLineError
from rad.kline import KLine
from rad.session import ECUSession
from rad.simulator import SimSerial


class FakeFtdi:
    """Imita pyftdi.ftdi.Ftdi ligado a uma linha K com as centralinas do simulador."""

    def __init__(self):
        self.sim = SimSerial()
        self.calls = []
        self.baud = None
        self.brk = False
        self.edges = []                    # (instante, break ligado?)
        self.pending = None                # endereço à espera de responder (depois do purge do KLine)
        self.unplugged = False

    def _io(self, name, *a):
        if self.unplugged:
            raise OSError("[Errno 19] No such device (it may have been disconnected)")
        self.calls.append((name,) + a)

    def set_line_property(self, bits, stop, parity):
        self._io("line", bits, stop, parity)

    def set_flowctrl(self, f):
        self._io("flow", f)

    def set_latency_timer(self, ms):
        self._io("latency", ms)

    def set_dtr(self, on):
        self._io("dtr", on)

    def set_rts(self, on):
        self._io("rts", on)

    def set_break(self, on):
        self._io("break", on)
        if on != self.brk:
            self.edges.append((time.perf_counter(), on))
        self.brk = on

    def set_baudrate(self, b):
        self._io("baud", b)
        self.baud = b
        if any(on for _, on in self.edges):
            self.pending = self._decode_5baud()
        self.edges = []
        return b

    def _decode_5baud(self):
        """Amostra a meio de cada bit de 200 ms: BREAK = 0, linha livre = 1 (start + 8 bits)."""
        t0 = next(t for t, on in self.edges if on)
        value = 0
        for n in range(1, 9):
            t = t0 + (n + 0.5) * 0.2
            state = False
            for te, on in self.edges:
                if te <= t:
                    state = on
            if not state:
                value |= 1 << (n - 1)
        return value & 0x7F

    def purge_buffers(self):
        self._io("purge")
        self.sim.rx.clear()

    def purge_rx_buffer(self):
        self._io("purge_rx")
        self.sim.rx.clear()

    def purge_tx_buffer(self):
        self._io("purge_tx")

    def read_data(self, n):
        self._io("read")
        if self.pending is not None:
            addr, self.pending = self.pending, None
            self.sim.baudrate = self.baud
            self.sim.sim_five_baud(addr)
        out = bytearray()
        while len(out) < n and self.sim.rx:
            out.append(self.sim.rx.popleft())
        return bytes(out)

    def write_data(self, data):
        self._io("write")
        return self.sim.write(data)

    def close(self):
        self.calls.append(("close",))


def _with_fake(fn):
    fake = FakeFtdi()
    old = ftdi_direct._open_ftdi
    ftdi_direct._open_ftdi = lambda vid, pid, serial: fake
    try:
        return fn(fake)
    finally:
        ftdi_direct._open_ftdi = old


PORT = "FTDI:0403:FA24:RT000001"


def test_port_names():
    assert ftdi_direct.parse_port(PORT) == (0x0403, 0xFA24, "RT000001")
    assert ftdi_direct.parse_port("FTDI:0403:FA24:") == (0x0403, 0xFA24, None)
    assert ftdi_direct.make_port(0x0403, 0xFA24, "RT000001") == PORT
    assert ftdi_direct.chip_name(0x0600) == "FT232R"
    try:
        ftdi_direct.parse_port("FTDI:lixo")
        assert False
    except KLineError:
        pass


def test_ftdi_serial_configures_chip():
    def run(fake):
        s = ftdi_direct.FtdiSerial(PORT, 10400)
        assert ("latency", 1) in fake.calls and ("line", 8, 1, "N") in fake.calls and ("flow", "") in fake.calls
        assert fake.baud == 10400 and fake.brk is False
        s.baudrate = 9600
        assert fake.baud == 9600 and s.baudrate == 9600
        s.break_condition = True
        assert fake.brk and s.break_condition
        s.dtr, s.rts = True, False
        assert ("dtr", True) in fake.calls and ("rts", False) in fake.calls
        s.close()
        assert ("close",) in fake.calls and not s.is_open
    _with_fake(run)


def test_ftdi_serial_read_timeout_and_unplug():
    def run(fake):
        s = ftdi_direct.FtdiSerial(PORT)
        s.timeout = 0.05
        t = time.perf_counter()
        assert s.read(1) == b""
        assert 0.04 <= time.perf_counter() - t < 0.5
        fake.sim.rx.extend([1, 2, 3])
        assert s.read(2) == b"\x01\x02" and s.read(5) == b"\x03"
        fake.unplugged = True
        for action in (lambda: s.read(1), lambda: s.write(b"\x00"), lambda: setattr(s, "break_condition", True)):
            try:
                action()
                assert False, "devia falhar com o cabo desligado"
            except KLineError as e:
                assert "desligado" in str(e)
    _with_fake(run)


def test_ftdi_open_errors_are_explained():
    old = ftdi_direct._open_ftdi
    try:
        def boom(*a):
            raise OSError("Operation not supported or unimplemented on this platform")
        ftdi_direct._open_ftdi = boom
        try:
            KLine(PORT).open()
            assert False
        except KLineError as e:
            assert "WinUSB" in str(e)
    finally:
        ftdi_direct._open_ftdi = old


def test_kline_over_ftdi_direct_kw1281():
    """Init a 5 baud por bit-banging do BREAK (tempos reais, ~2 s) + KW1281 completo pelo FtdiSerial."""
    def run(fake):
        kl = KLine(PORT, echo="auto")
        kl.open()
        try:
            s = ECUSession(kl)
            info = s.connect(0x01)
            assert info["protocol"] == "KW1281" and info["part"] == "038906019FN"
            assert kl.echo is True
            assert [f["vag"] for f in s.read_faults()] == ["00532", "01247"]
            assert len(s.read_group(1)["fields"]) == 4
            s.disconnect()
        finally:
            kl.close()
        assert ("close",) in fake.calls and fake.brk is False
    _with_fake(run)


def test_kline_over_ftdi_direct_absent_module():
    def run(fake):
        kl = KLine(PORT, echo="auto")
        kl.open()
        try:
            r = kl.five_baud_init(0x45, 10400)
            assert r["status"] == "none"
        finally:
            kl.close()
    _with_fake(run)


def test_line_search_finds_dtr_rts():
    """Clone cujo transceptor só liga com DTR desligado e RTS ligado: o eco só aparece nessa combinação."""
    class PickyFtdi(FakeFtdi):
        def __init__(self):
            super().__init__()
            self.dtr_on, self.rts_on = True, False
            self.sim.echo = False

        def set_dtr(self, on):
            self.dtr_on = on
            self.sim.echo = (not self.dtr_on) and self.rts_on

        def set_rts(self, on):
            self.rts_on = on
            self.sim.echo = (not self.dtr_on) and self.rts_on

    fake = PickyFtdi()
    old = ftdi_direct._open_ftdi
    ftdi_direct._open_ftdi = lambda vid, pid, serial: fake
    try:
        kl = KLine(PORT)
        kl.open()
        assert kl.echo_test() is False
        assert kl.find_lines() == (False, True) and kl.lines == (False, True)
        assert kl.echo_test() is True
        kl.close()

        fake = PickyFtdi()
        fake.set_dtr = fake.set_rts = lambda on: None          # nenhuma combinação dá eco
        kl = KLine(PORT)
        kl.open()
        assert kl.find_lines() is None and kl.lines == (False, False)     # clone HEX: DTR nunca activo
        kl.close()
    finally:
        ftdi_direct._open_ftdi = old


# ------------------------------------------------------------------ D2XX (ponte em processo à parte)
def test_d2xx_bridge_end_to_end():
    kl = KLine(d2xx.SIM_PORT, echo="auto")
    kl.open()
    try:
        assert kl.ser.info["pid"] == 0xFA24
        s = ECUSession(kl)
        info = s.connect(0x01)
        assert info["protocol"] == "KW1281"
        assert len(s.read_faults()) == 2
        s.disconnect()
        info = s.connect(0x03)
        assert info["protocol"] == "KWP2000"
        assert isinstance(s.read_faults(), list)
        s.disconnect()
        assert ECUSession(kl, baud="auto").connect(0x17)["baud"] == 9600
    finally:
        kl.close()
    assert not kl.is_open


def test_d2xx_bridge_dies_cleanly():
    s = d2xx.D2xxSimSerial()
    s.proc.kill()
    s.proc.wait()
    try:
        s.read(1)
        assert False
    except KLineError as e:
        assert "ponte D2XX" in str(e)
    s.close()


def test_d2xx_error_messages():
    assert "outro programa" in d2xx._explain("FT_OpenEx falhou (D2XX DEVICE_NOT_OPENED)", 3)
    assert "ligada" in d2xx._explain("FT_OpenEx falhou (D2XX DEVICE_NOT_FOUND)", 2)


def test_d2xx_native_path_only_for_32_bit():
    import struct
    from rad import d2xx_bridge
    p = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "RT-USB.DLL")
    if struct.calcsize("P") == 8:
        assert d2xx_bridge.native_path(p) == p


# ------------------------------------------------------------------ deteção
HEX_ID = "USB\\VID_0403&PID_FA24\\RT000001"
HWID = ["USB\\VID_0403&PID_FA24&REV_0600", "USB\\VID_0403&PID_FA24"]


def _hex(status, service, name="Ross-Tech HEX-USB"):
    return {"name": name, "id": HEX_ID, "status": status, "cls": "USB", "service": service, "hwid": HWID}


def test_hex_usb_without_driver():
    f = cable.classify([_hex("Error", "")])
    assert len(f) == 1 and f[0]["level"] == "warn" and f[0]["com"] is None
    assert "WinUSB" in f[0]["detail"] and "FT232R" in f[0]["title"] and "zadig" in f[0]["driver_url"]


def test_hex_usb_with_winusb():
    f = cable.classify([_hex("OK", "WinUSB", "Ross-Tech Direct USB Interface")])
    if cable._pyftdi_available():
        assert f[0]["level"] == "ok" and f[0]["com"] == "FTDI:0403:FA24:RT000001"
    else:
        assert f[0]["level"] == "warn" and "pyftdi" in f[0]["title"]


def test_hex_usb_with_rt_usb_driver():
    from rad import j2534
    old_dll, old_py = d2xx.find_dll, j2534.find_python
    try:
        d2xx.find_dll = lambda: None
        f = cable.classify([_hex("OK", "RT-USB")])
        assert f[0]["level"] == "warn" and "RT-USB.DLL" in f[0]["title"]

        d2xx.find_dll = lambda: sys.executable          # existe; o número de bits vem do cabeçalho PE

        def no_python(bits):
            raise RuntimeError("sem python")
        j2534.find_python = no_python
        f = cable.classify([_hex("OK", "RT-USB")])
        assert f[0]["level"] == "warn" and "componente de" in f[0]["title"] and "runtime/py" in f[0]["detail"]

        j2534.find_python = lambda bits: sys.executable
        f = cable.classify([_hex("OK", "RT-USB")])
        assert f[0]["level"] == "ok" and f[0]["com"] == "D2XX:RT000001"
    finally:
        d2xx.find_dll, j2534.find_python = old_dll, old_py


def test_other_firmware_interfaces_still_rejected():
    hexv2 = {"name": "Ross-Tech HEX-V2", "id": "USB\\VID_1234&PID_0001\\X", "status": "OK", "cls": "USB"}
    assert cable.classify([hexv2])[0]["level"] == "bad"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
