"""Testes guiados contra o simulador (com o ciclo ralenti → aceleração)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import guided, simulator
from rad.kline import KLine, SIM_PORT
from rad.session import ECUSession


def collect(group, profile_changes=None, pull=False, n=40):
    old = dict(simulator.ENGINE)
    simulator.ENGINE.update(profile_changes or {})
    try:
        kl = KLine(SIM_PORT)
        kl.open()
        s = ECUSession(kl)
        s.connect(0x01)
        ecu = kl.ser.ecu
        samples = []
        for i in range(n):
            if pull:   # avança o relógio do simulador para dentro da aceleração
                ecu.t0 = time.monotonic() - (12.5 + 5.0 * i / n)
            samples.append(s.read_group(group)["fields"])
        s.disconnect()
        return samples, s.info
    finally:
        simulator.ENGINE.clear()
        simulator.ENGINE.update(old)


def test_available():
    _, info = collect(1, n=1)
    assert guided.available_for(info)
    assert not guided.available_for({**info, "address": 0x17})


def test_injectors_ok_and_bad():
    r = guided.InjectorBalance().analyze(collect(13)[0])
    assert r["ok"] is True, r
    r = guided.InjectorBalance().analyze(collect(13, {"injectors": [0.3, 3.1, -0.4, 0.2]})[0])
    assert r["ok"] is False and "2" in r["summary"], r


def test_boost():
    r = guided.BoostTest().analyze(collect(11, pull=True)[0])
    assert r["ok"] is True, r
    r = guided.BoostTest().analyze(collect(11, {"boost_loss": 400}, pull=True)[0])
    assert r["ok"] is False and "abaixo" in r["summary"], r
    r = guided.BoostTest().analyze(collect(11)[0])          # só ralenti
    assert r["ok"] is None


def test_maf():
    assert guided.MafTest().analyze(collect(3, pull=True)[0])["ok"] is True
    assert guided.MafTest().analyze(collect(3, {"maf_ratio": 0.7}, pull=True)[0])["ok"] is False


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
