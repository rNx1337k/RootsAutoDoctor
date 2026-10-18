"""Testes de robustez: a comunicação tem de falhar de forma controlada (ProtocolError /
RequestRejected / NotSupported), nunca com IndexError, KeyError, TypeError, etc.

Correr:  python tests/test_robustness.py
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import vag_data
from rad.errors import NotSupported, ProtocolError, RequestRejected
from rad.kline import KLine, SIM_PORT
from rad.protocols import kw1281, kwp2000
from rad.session import ECUSession
from rad.simulator import SimSerial

EXPECTED = (ProtocolError, RequestRejected, NotSupported)


class FaultySerial(SimSerial):
    """Simulador com defeitos: ruído, bytes perdidos, ECU que deixa de responder."""

    def __init__(self, noise=0.0, drop=0.0, die_after=None, seed=0):
        super().__init__()
        self.rng = random.Random(seed)
        self.noise, self.drop = noise, drop
        self.die_after = die_after
        self.reads = 0

    def read(self, n=1):
        out = bytearray()
        while len(out) < n and self.rx:
            b = self.rx.popleft()
            self.reads += 1
            if self.die_after is not None and self.reads > self.die_after:
                self.rx.clear()
                break
            if self.rng.random() < self.drop:
                continue
            if self.rng.random() < self.noise:
                b ^= 1 << self.rng.randrange(8)
            out.append(b)
        return bytes(out)


def make(serial, echo="auto"):
    kl = KLine(SIM_PORT, echo=echo)
    kl.ser = serial
    return kl


def full_session(s, address):
    """Executa todas as funções; só são aceites erros 'controlados'."""
    calls = [lambda: s.read_faults(), lambda: s.read_group(1), lambda: s.read_group(250),
             lambda: s.keep_alive(), lambda: s.adaptation_read(1), lambda: s.basic_setting(1),
             lambda: s.output_test(), lambda: s.login(12233, 0), lambda: s.read_faults()]
    for c in calls:
        if not s.connected:
            break
        try:
            c()
        except EXPECTED:
            pass


def test_no_echo_cable():
    ser = SimSerial()
    ser.echo = False
    kl = make(ser)
    s = ECUSession(kl)
    info = s.connect(0x01)
    assert kl.echo is False
    assert info["coding"] == 2
    assert len(s.read_faults()) == 2
    s3 = ECUSession(kl)
    s.disconnect()
    assert s3.connect(0x03)["protocol"] == "KWP2000"


def test_forced_echo_settings():
    ser = SimSerial()
    kl = make(ser, echo="on")
    s = ECUSession(kl)
    s.connect(0x01)
    assert s.read_group(3)["fields"]
    # cabo sem eco mas configurado "com eco" → erro controlado, não crash
    ser2 = SimSerial()
    ser2.echo = False
    s2 = ECUSession(make(ser2, echo="on"))
    try:
        s2.connect(0x01)
        assert False, "devia falhar"
    except EXPECTED:
        pass


def test_noise_and_drops_never_crash():
    crashes = []
    for seed in range(120):
        ser = FaultySerial(noise=0.01, drop=0.01, seed=seed)
        s = ECUSession(make(ser))
        addr = (0x01, 0x03, 0x17)[seed % 3]
        try:
            s.connect(addr)
            full_session(s, addr)
        except EXPECTED:
            pass
        except Exception as e:
            crashes.append((seed, addr, repr(e)))
    assert not crashes, crashes[:5]


def test_ecu_dies_mid_session():
    for die in range(10, 400, 7):
        ser = FaultySerial(die_after=die)
        s = ECUSession(make(ser))
        try:
            s.connect(0x01)
            full_session(s, 0x01)
        except EXPECTED:
            pass
        assert ser.reads >= 0


def test_reconnect_after_failure():
    ser = FaultySerial(die_after=60)
    kl = make(ser)
    s = ECUSession(kl)
    try:
        s.connect(0x01)
        full_session(s, 0x01)
    except EXPECTED:
        pass
    assert not s.connected
    ser.die_after = None
    s2 = ECUSession(kl)
    assert s2.connect(0x01)["part"] == "038906019FN"


def test_long_live_session():
    kl = make(SimSerial())
    s = ECUSession(kl)
    s.connect(0x01)
    t = time.time()
    for i in range(1500):
        g = s.read_group((1, 3, 11)[i % 3])
        assert len(g["fields"]) == 4
        if i % 50 == 0:
            s.keep_alive()
    assert s.connected
    print(f"   1500 leituras de grupo em {time.time() - t:.1f}s")


def test_fuzz_parsers():
    rng = random.Random(1)
    for _ in range(20000):
        data = [rng.randrange(256) for _ in range(rng.randrange(0, 20))]
        vag_data.decode_triplets(data)
        if len(data) >= 2:
            vag_data.decode_fault((data[0] << 8) | data[1], data[-1])
        blocks = [kw1281.Block(1, rng.choice([0xF6, 0xFC, 0xE7]), data)]
        kw1281.parse_ident(blocks)
    for f in range(0, 256):
        for a in (0, 1, 127, 255):
            for b in (0, 1, 128, 255):
                r = vag_data.decode_value(f, a, b)
                assert isinstance(r["value"], str) and isinstance(r["unit"], str)


def test_kwp_ident_fuzz():
    rng = random.Random(2)

    class Fake(kwp2000.KWP2000):
        def __init__(self, payload):
            self.payload = payload
            self.log = lambda m: None

        def request(self, p, timeout=1.0):
            return self.payload

    for _ in range(3000):
        payload = [0x5A, 0x9B] + [rng.randrange(256) for _ in range(rng.randrange(0, 60))]
        info = Fake(payload).read_ident()
        assert set(info) >= {"part", "component", "coding", "wsc"}
    # leitura de avarias com contagem errada
    for n in range(0, 10):
        f = Fake([0x58, n] + [rng.randrange(256) for _ in range(rng.randrange(0, 12))])
        f.read_faults()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            t = time.time()
            fn()
            print(f"OK {name}  ({time.time() - t:.1f}s)")
