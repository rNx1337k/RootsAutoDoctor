"""Gravações de valores de medição guardadas com o veículo e comparação automática com a visita anterior."""
import datetime
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import recordings

CSV = "Hora;G001.1 Rotação [/min]\n10:00:00.000;850\n10:00:01.000;900\n"


def _csv():
    path = os.path.join(tempfile.mkdtemp(), "gravacao.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write(CSV)
    return path


def test_vehicle_key_uses_plate_then_vin():
    assert recordings.vehicle_key({"plate": "12-ab-34"}) == "12AB34"
    assert recordings.vehicle_key({"plate": "", "vin": "wvwzzz1jz3w000001"}) == "WVWZZZ1JZ3W000001"
    assert recordings.vehicle_key({}) is None and recordings.vehicle_key(None) is None


def test_without_plate_or_vin_nothing_is_stored():
    d = tempfile.mkdtemp()
    assert recordings.store(_csv(), {"plate": ""}, 0x01, d) is None
    assert recordings.for_vehicle({"plate": ""}, directory=d) == []


def test_previous_finds_the_last_visit_of_the_same_controller():
    d = tempfile.mkdtemp()
    car = {"plate": "12-AB-34"}
    t = datetime.datetime(2026, 10, 1, 9, 0, 0)
    first = recordings.store(_csv(), car, 0x01, d, when=t)
    recordings.store(_csv(), car, 0x17, d, when=t + datetime.timedelta(days=5))        # outro controlador
    same_second = recordings.store(_csv(), {"plate": "12 ab 34"}, 0x01, d, when=t)     # não sobrepõe
    assert same_second != first and os.path.exists(first) and os.path.exists(same_second)
    now = recordings.store(_csv(), car, 0x01, d, when=t + datetime.timedelta(days=30))
    assert [os.path.basename(p) for p, _w, _a in recordings.for_vehicle(car, 0x01, d)][0] == \
        os.path.basename(now)
    prev = recordings.previous(car, 0x01, current=now, directory=d)
    assert prev is not None and prev[1] == t
    assert recordings.previous(car, 0x01, directory=d)[0] == now          # sem current: a mais recente
    oldest = recordings.for_vehicle(car, 0x01, d)[-1][0]
    assert recordings.previous(car, 0x01, current=oldest, directory=d) is None
    assert recordings.previous({"plate": "99-ZZ-99"}, 0x01, directory=d) is None


def test_measuring_csv_is_kept_with_the_car_and_compared_next_visit():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from tests.test_ui import _window, _wait
    from PySide6.QtWidgets import QFileDialog
    from rad.ui import logviewer
    app, w = _window()
    opened = []
    orig_save, orig_exec = QFileDialog.getSaveFileName, logviewer.LogViewerDialog.exec
    out_dir = tempfile.mkdtemp()
    names = iter(["visita1.csv", "visita2.csv"])
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (os.path.join(out_dir, next(names)), ""))
    logviewer.LogViewerDialog.exec = lambda self: opened.append(self)
    try:
        w.home.vehicle_edits["plate"].setText("RC-00-01")
        w.connect_module(0x01)
        assert _wait(app, lambda: w.module.info is not None)
        page = w.module
        fields = [{"value": "850", "unit": "/min", "formula": 1, "a": 200, "b": 21, "numeric": 850.0}] * 4
        for _visit in range(2):
            page._toggle_csv()
            for i in range(3):
                page.on_live({"mode": "read", "t": 1000 + i, "groups": {1: fields, 3: fields}})
            page._toggle_csv()
            page.stop_live()
        stored = recordings.for_vehicle({"plate": "RC-00-01"}, 0x01)
        assert len(stored) == 2 and page.last_stored == stored[0][0]
        page.open_logs()
        dlg = opened[-1]
        assert dlg.log is not None and dlg.log.title == "visita2.csv"
        assert dlg.other is not None and dlg.other_date == stored[1][1]
        assert "visita anterior" in dlg.files_lbl.text() or "previous visit" in dlg.files_lbl.text()
        assert os.path.normcase(dlg.start_dir) == os.path.normcase(recordings.vehicle_dir({"plate": "RC-00-01"}))
        # sem gravação nesta sessão do programa: abre a última guardada do carro, comparada com a anterior
        page.last_csv = page.last_stored = None
        page.open_logs()
        dlg = opened[-1]
        assert os.path.normcase(dlg.log.path) == os.path.normcase(stored[0][0]) and dlg.other is not None
        for d in opened:
            d.deleteLater()
        app.processEvents()
    finally:
        QFileDialog.getSaveFileName = orig_save
        logviewer.LogViewerDialog.exec = orig_exec
        w.close()
