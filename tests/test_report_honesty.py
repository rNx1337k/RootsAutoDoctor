"""Relatório e histórico: nunca dar o veículo como "sem problemas" com leituras parciais, e nunca confundir
dados do simulador com dados de um carro. Corre sem Qt."""
import json
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import history, report, vag_data
from rad.ui_score import health_score


def _ok(addr, codes=(), simulated=None):
    info = {"part": "1J0", "component": "X"}
    if simulated is not None:
        info.update(simulated=simulated, interface="SIMULADOR" if simulated else "COM3")
    return {"address": addr, "module": vag_data.module_name(addr), "status": "ok", "info": info,
            "faults": [vag_data.decode_fault(c, 0x23) for c in codes]}


def _err(addr):
    return {"address": addr, "module": vag_data.module_name(addr), "status": "error", "error": "timeout"}


def test_nothing_read_is_not_a_healthy_vehicle():
    items = [_err(1), _err(3)]
    assert health_score(items) is None
    html = report.build_html({}, {}, items)
    assert "não é possível avaliar" in html
    assert "Nenhuma avaria registada" not in html


def test_unreachable_modules_and_abort_are_stated():
    items = [_ok(1), _err(3)]
    html = report.build_html({}, {}, items, meta={"aborted": True, "scanned": 5, "total": 20})
    assert "Nenhuma avaria registada nos 1 controlador(es) lido(s)" in html
    assert "1 controlador(es) não comunicaram" in html
    assert "interrompido (5 de 20 endereços verificados)" in html
    assert "leitura parcial" in html
    color, _lines = report.verdict_lines(items, {"aborted": True})
    assert color != report.OK


def test_clean_full_scan_is_ok():
    color, lines = report.verdict_lines([_ok(1), _ok(3)], {"aborted": False})
    assert color == report.OK and lines == ["Nenhuma avaria registada nos 2 controlador(es) lido(s)."]


def test_simulated_data_is_marked_in_report():
    html = report.build_html({}, {"plate": "AA"}, [_ok(1, [532], simulated=True)])
    assert "DADOS SIMULADOS" in html
    real = report.build_html({}, {"plate": "AA"}, [_ok(1, [532], simulated=False)])
    assert "DADOS SIMULADOS" not in real and "Interface: COM3" in real


def test_report_uses_session_date_and_marks_suggestions():
    html = report.build_html({}, {}, [_ok(1, [532])], date="2026-03-04T10:20:30")
    assert "04/03/2026 10:20" in html
    assert "sugestão do programa" in html


def test_history_marks_simulation_and_keeps_unknown_for_old_sessions():
    d = tempfile.mkdtemp()
    sim = history.save_session("autoscan", {"plate": "AA"}, [_ok(1, simulated=True)], directory=d,
                               meta={"simulated": True, "interface": "SIMULADOR"})
    real = history.save_session("autoscan", {"plate": "BB"}, [_ok(1, simulated=False)], directory=d)
    old = history.save_session("autoscan", {"plate": "CC"}, [_ok(1)], directory=d)
    flags = {s["id"]: s["simulated"] for s in history.list_sessions(d)}
    assert flags[sim] == 1 and flags[real] == 0 and flags[old] is None
    assert history.load_session(sim, d)["meta"]["interface"] == "SIMULADOR"


def test_migration_adds_column_without_losing_sessions():
    d = tempfile.mkdtemp()
    db = sqlite3.connect(os.path.join(d, "historico.db"))         # base de dados de uma versão anterior
    db.executescript("""CREATE TABLE sessions (id TEXT PRIMARY KEY, date TEXT NOT NULL, kind TEXT NOT NULL,
        plate TEXT NOT NULL DEFAULT '', client TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
        modules INTEGER NOT NULL DEFAULT 0, faults INTEGER NOT NULL DEFAULT 0, data TEXT NOT NULL);""")
    data = {"id": "old1", "date": "2026-10-01T10:00:00", "kind": "autoscan", "vehicle": {"plate": "ZZ"},
            "items": [_ok(1, [532])]}
    db.execute("INSERT INTO sessions VALUES ('old1','2026-10-01T10:00:00','autoscan','ZZ','','',1,1,?)",
               (json.dumps(data),))
    db.commit()
    db.close()
    rows = history.list_sessions(d)
    assert [r["id"] for r in rows] == ["old1"] and rows[0]["simulated"] is None
    assert history.load_session("old1", d)["items"][0]["faults"][0]["vag"] == "00532"
    history.save_session("modulo", {"plate": "ZZ"}, [], directory=d)
    assert len(history.list_sessions(d)) == 2


def test_update_session_instead_of_duplicate():
    d = tempfile.mkdtemp()
    sid = history.save_session("autoscan", {"plate": ""}, [_ok(1)], directory=d)
    history.update_session(sid, {"plate": "12-AB-34", "client": "Ana"}, "Trocar sensor", directory=d)
    rows = history.list_sessions(d)
    assert len(rows) == 1 and rows[0]["plate"] == "12-AB-34" and rows[0]["client"] == "Ana"
    assert history.load_session(sid, d)["notes"] == "Trocar sensor"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
