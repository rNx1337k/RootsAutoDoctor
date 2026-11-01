"""Secção "Valores de medição" do relatório: alertas da leitura e comparação com a visita anterior."""
import datetime
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import report

ITEMS = [{"address": 1, "module": "Motor", "status": "ok",
          "info": {"part": "038906019FN", "component": "1,9l R4 EDC", "coding": 2}, "faults": []}]

WITH_ALERT = {"address": 1, "module": "Motor", "groups": [1, 11], "checked": True,
              "alerts": [{"group": 11, "severity": "warn", "text": "Pressão do turbo 300 mbar abaixo da pretendida"}],
              "channels": [{"name": "G011.3 Pressão real", "unit": "mbar", "min": 990, "max": 1850, "avg": 1400,
                            "prev_avg": 1700}],
              "previous_date": "2026-10-01T09:00"}


def _html(meta, variant):
    return report.build_html({"name": "Oficina"}, {"plate": "AA-00-00"}, ITEMS, meta=meta, variant=variant)


def test_no_measuring_means_no_section():
    assert "Valores de medição" not in _html({}, "client")
    assert report.measuring_html(None) == ""


def test_client_report_shows_the_alerts_but_not_the_value_table():
    html = _html({"measuring": WITH_ALERT}, "client")
    assert "Valores de medição" in html and "grupos lidos: 001, 011" in html
    assert "300 mbar abaixo" in html
    assert "G011.3 Pressão real" not in html


def test_technical_report_compares_with_the_previous_visit():
    html = _html({"measuring": WITH_ALERT}, "technical")
    assert "G011.3 Pressão real" in html and "2026-10-01 09:00" in html
    assert "-300" in html                                   # 1400 agora, 1700 na visita anterior


def test_all_values_normal_or_no_rules():
    ok = dict(WITH_ALERT, alerts=[], channels=[], previous_date=None)
    assert "dentro do habitual" in _html({"measuring": ok}, "client")
    unknown = dict(ok, checked=False)
    html = _html({"measuring": unknown}, "client")
    assert "dentro do habitual" not in html and "Sem avaliação automática" in html


def test_module_page_summary_goes_into_the_report_and_history():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from tests.test_ui import _window, _wait
    from tests.test_live_alerts import f
    from PySide6.QtWidgets import QFileDialog
    from rad import recordings
    app, w = _window()
    orig_save = QFileDialog.getSaveFileName
    out = os.path.join(tempfile.mkdtemp(), "agora.csv")
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out, ""))
    try:
        car = {"plate": "RM-00-02"}
        w.home.vehicle_edits["plate"].setText(car["plate"])
        # gravação da visita anterior do mesmo carro
        old = os.path.join(tempfile.mkdtemp(), "antes.csv")
        with open(old, "w", encoding="utf-8") as fh:
            fh.write("Hora;G011.1 Rotação [/min];G011.2 Pressão pretendida [mbar];G011.3 Pressão real [mbar];"
                     "G011.4 Ciclo N75 [%]\n10:00:00.000;2900;2000;1950;70\n")
        recordings.store(old, car, 0x01, when=datetime.datetime(2026, 10, 1, 9, 0))
        w.connect_module(0x01)
        assert _wait(app, lambda: w.module.info is not None)
        page = w.module
        assert page.measuring_summary() is None             # ainda não leu valores
        page.groups[0].spin.setValue(11)
        page._toggle_mvb()
        page._toggle_csv()
        for i in range(12):
            page.on_live({"mode": "read", "t": 100 + i * 0.25, "groups": {11: f(2900, 2000, 1600, 75)}})
        page._toggle_csv()
        page.stop_live()
        m = page.measuring_summary()
        assert 11 in m["groups"] and m["checked"]
        assert [a["group"] for a in m["alerts"]] == [11]
        boost = next(c for c in m["channels"] if c["name"].startswith("G011.3"))
        assert boost["avg"] == 1600 and boost["prev_avg"] == 1950
        assert m["previous_date"] == "2026-10-01T09:00"
        import json
        json.dumps(m)                                       # vai para o histórico
        built = {}

        def fake_write(items, vehicle, notes, meta=None, date=None):
            built["meta"] = meta
            return vehicle, notes
        w._write_report = fake_write
        w.export_report("module")
        assert built["meta"]["measuring"]["alerts"][0]["group"] == 11
        # ao mudar de controlador, a medição do anterior não passa para o relatório do novo
        page.set_info(dict(page.info, address=0x17, module="Painel"))
        assert page.measuring_summary() is None
    finally:
        QFileDialog.getSaveFileName = orig_save
        w.close()
