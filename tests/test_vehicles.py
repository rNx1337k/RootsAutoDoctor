"""Registo de veículos e clientes (rad/vehicles.py): cada carro fica uma vez, encontra-se pela matrícula, pelo VIN
ou pelo cliente, e os diagnósticos guardados mantêm-no actualizado."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import history, vehicles

VIN = "WAUZZZ8L71A123456"


def test_one_vehicle_per_car_and_data_is_completed_not_erased():
    d = tempfile.mkdtemp()
    assert vehicles.remember({"plate": "12-ab-34", "client": "João Silva", "model": "Audi A3 1.9 TDI"}, d)
    vehicles.remember({"plate": "12 AB 34", "vin": VIN.lower(), "km": "250000"}, d)    # mesma matrícula, outra escrita
    rows = vehicles.search("", directory=d)
    assert len(rows) == 1
    v = rows[0]
    assert v["plate"] == "12 AB 34" and v["vin"] == VIN and v["client"] == "João Silva" and v["km"] == "250000"
    assert v["visits"] == 2
    assert vehicles.lookup(vin=VIN, directory=d)["client"] == "João Silva"
    assert vehicles.lookup(plate="12AB34", directory=d)["vin"] == VIN
    assert vehicles.lookup(plate="99-ZZ-99", directory=d) is None
    assert vehicles.remember({"client": "sem matrícula"}, d) is None
    assert vehicles.plates(d) == ["12 AB 34"]


def test_search_by_vin_plate_or_client():
    d = tempfile.mkdtemp()
    vehicles.remember({"plate": "AA-11-BB", "vin": VIN, "client": "Oficina Roots"}, d)
    vehicles.remember({"plate": "CC-22-DD", "client": "Maria"}, d)
    assert [v["plate"] for v in vehicles.search("123456", directory=d)] == ["AA-11-BB"]       # fim do VIN
    assert [v["plate"] for v in vehicles.search("cc22", directory=d)] == ["CC-22-DD"]         # sem traços
    assert [v["plate"] for v in vehicles.search("maria", directory=d)] == ["CC-22-DD"]
    assert vehicles.search("não existe", directory=d) == []


def test_saved_diagnostics_keep_the_register_up_to_date():
    d = tempfile.mkdtemp()
    sid = history.save_session("autoscan", {"plate": "AA-00-01"}, [], directory=d)
    history.update_session(sid, vehicle={"plate": "AA-00-01", "client": "Ana", "vin": VIN}, directory=d)
    v = vehicles.lookup(plate="AA0001", directory=d)
    assert v["client"] == "Ana" and v["vin"] == VIN and v["visits"] == 1          # o relatório não é outra visita
    history.save_session("modulo", {"plate": "AA-00-01"}, [], directory=d)
    assert vehicles.lookup(vin=VIN, directory=d)["visits"] == 2


def test_existing_history_is_imported_the_first_time():
    d = tempfile.mkdtemp()
    import sqlite3
    db = history._open(d)
    db.close()
    for plate, client in (("OLD-1", "Rui"), ("OLD-1", ""), ("OLD-2", "Sara")):
        db = sqlite3.connect(os.path.join(d, "historico.db"))
        db.row_factory = sqlite3.Row
        with db:
            history._insert(db, {"id": f"{plate}{client}", "date": "2025-01-01T10:00:00", "kind": "autoscan",
                                 "vehicle": {"plate": plate, "client": client}, "items": []})
        db.close()
    rows = {v["plate"]: v for v in vehicles.search("", directory=d)}
    assert set(rows) == {"OLD-1", "OLD-2"} and rows["OLD-1"]["client"] == "Rui" and rows["OLD-1"]["visits"] == 2
