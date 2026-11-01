"""Alertas durante a leitura dos valores de medição."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import live_alerts

TDI = "038906019FN"
ME7 = "06A906032HN"


def f(*vals):
    return [{"value": str(v), "unit": "", "formula": 1, "a": 0, "b": 0, "numeric": v} for v in vals]


def run(monitor, samples, dt=0.25):
    """Envia as leituras com dt segundos entre elas; devolve todos os alertas novos."""
    new = []
    for i, groups in enumerate(samples):
        new += monitor.feed(i * dt, groups)
    return new


def test_only_engines_with_known_groups_get_rules():
    assert live_alerts.Monitor(TDI).groups() == [1, 3, 11, 13]
    assert live_alerts.Monitor(ME7).groups() == [1, 4, 115]
    assert live_alerts.Monitor("1J0920926C").groups() == []
    assert live_alerts.Monitor("").feed(0, {11: f(3000, 2000, 1000, 80)}) == []


def test_low_boost_needs_load_and_must_last():
    m = live_alerts.Monitor(TDI)
    assert run(m, [{11: f(900, 1010, 700, 30)}] * 20) == []            # ao ralenti não conta
    m = live_alerts.Monitor(TDI)
    assert run(m, [{11: f(2800, 2000, 1700, 70)}] * 4) == []           # só 0,75 s: ainda não
    new = run(m, [{11: f(2800, 2000, 1700, 70)}] * 8)
    assert [a.key for a in new] == ["boost_low"]
    assert "300 mbar" in new[0].text and new[0].severity == "warn"
    assert len(m.alerts()) == 1
    m.feed(10, {11: f(2800, 2000, 1950, 70)})                            # recuperou: o alerta sai
    assert m.alerts() == []


def test_a_single_spike_never_raises_an_alert():
    m = live_alerts.Monitor(TDI)
    samples = [{11: f(2800, 2000, 1980, 70)}, {11: f(2800, 2000, 1500, 70)}] * 20
    assert run(m, samples) == []


def test_overboost_and_overheat_are_serious():
    m = live_alerts.Monitor(TDI)
    new = run(m, [{11: f(3000, 2000, 2400, 90), 1: f(2000, 20, 1.5, 114)}] * 12)
    assert {a.key for a in new} == {"boost_high", "overheat"}
    assert all(a.severity == "bad" for a in new)
    assert m.alerts()[0].severity == "bad"


def test_maf_and_injectors():
    m = live_alerts.Monitor(TDI)
    new = run(m, [{3: f(2600, 800, 600, 0), 13: f(0.4, -2.6, 0.6, 2.3)}] * 16)
    texts = {a.key: a.text for a in new}
    assert "75 %" in texts["maf_low"]
    assert "2, 4" in texts["injectors"]


def test_alerts_of_a_group_no_longer_read_go_away():
    m = live_alerts.Monitor(TDI)
    run(m, [{11: f(2800, 2000, 1700, 70)}] * 12)
    assert m.alerts()
    m.feed(5, {1: f(900, 4, 1.5, 90)})
    assert m.alerts() == []


def test_petrol_voltage_and_text_fields_are_ignored_safely():
    m = live_alerts.Monitor(ME7)
    new = run(m, [{4: f(800, 11.0, 90, 30)}] * 16)
    assert [a.key for a in new] == ["voltage"] and "11.0 V" in new[0].text
    m.feed(10, {4: "Erro de leitura", 1: [{"value": "QUENTE", "unit": "", "numeric": None}]})
    assert m.alerts() == []


def test_measuring_tab_shows_alerts_from_the_simulator():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from tests.test_ui import _window, _wait
    from rad import simulator
    app, w = _window()
    old = dict(simulator.ENGINE)
    try:
        w.connect_module(0x01)
        assert _wait(app, lambda: w.module.info is not None)
        page = w.module
        assert not page.alerts_lbl.isVisible()
        page.tabs.setCurrentIndex(2)
        page.groups[0].spin.setValue(11)
        page._toggle_mvb()
        assert page.monitor is not None and page.monitor.groups() == [1, 3, 11, 13]
        # leituras como as do carro, com o turbo a falhar em carga
        for i in range(12):
            page.on_live({"mode": "read", "t": 100 + i * 0.25, "groups": {11: f(2900, 2000, 1600, 75)}})
        assert page.alerts_lbl.isVisible() and "011" in page.alerts_lbl.text()
        page.stop_live()
        assert page.monitor is None and not page.alerts_lbl.isVisible()
    finally:
        simulator.ENGINE.clear()
        simulator.ENGINE.update(old)
        w.close()
