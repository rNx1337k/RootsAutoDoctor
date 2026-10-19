import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rad import fault_advice, vag_data


def test_known_code_has_causes_and_checks():
    a = fault_advice.advice(vag_data.decode_fault(1247, 0x1E), 0x01)
    assert a["known"] and a["system"] == "Turbo" and a["severity"] == "media"
    assert any("N75" in c for c in a["causes"]) and a["checks"]
    assert any("Circuito aberto" in n for n in a["notes"])          # dica do tipo de avaria (30)


def test_intermittent_and_module_severity():
    f = vag_data.decode_fault(532, 0x87)                             # intermitente, sinal baixo
    a = fault_advice.advice(f, 0x01)
    assert a["severity"] == "media" and any("Intermitente" in n for n in a["notes"])
    assert fault_advice.advice(f, 0x03)["severity"] == "alta"         # a mesma avaria no ABS sobe de gravidade


def test_unknown_code_falls_back_to_module():
    f = {"vag": "09999", "pcode": "", "elab_code": 3, "intermittent": False}
    a = fault_advice.advice(f, 0x15)
    assert not a["known"] and a["severity"] == "alta" and a["system"] == "Airbags"
    assert a["notes"] and not a["causes"]
    assert fault_advice.advice({"vag": "x"}, None)["severity"] == "baixa"    # dados estragados não rebentam


def test_pcode_advice():
    f = vag_data.decode_fault(16384 + 299, 0)                        # P0299
    assert f["pcode"] == "P0299"
    assert fault_advice.advice(f)["system"] == "Turbo"


def test_lookup_code():
    assert fault_advice.lookup_code("00532")["code"] == 532
    assert fault_advice.lookup_code(" 532 ")["code"] == 532
    assert fault_advice.lookup_code("p0299")["code"] == 16683
    assert fault_advice.lookup_code("P1556")["code"] == 17408 + 556
    assert fault_advice.lookup_code("12345") is None                 # não é um código conhecido
    assert fault_advice.lookup_code("abc") is None and fault_advice.lookup_code("") is None


def test_search_codes():
    res = fault_advice.search_codes("turbo")
    assert res and all("turbo" in f["desc"].lower() for f in res)
    assert any(f["code"] == 1259 for f in fault_advice.search_codes("RELE bomba"))   # sem acentos nem maiúsculas
    assert any(f["code"] == 283 for f in fault_advice.search_codes("abs dianteiro"))
    assert fault_advice.search_codes("ab") == []                       # pesquisa demasiado curta


def test_worst_severity():
    items = [{"address": 1, "status": "ok", "faults": [vag_data.decode_fault(532, 0x07)]},
             {"address": 3, "status": "ok", "faults": [vag_data.decode_fault(283, 0x23)]},
             {"address": 0x15, "status": "error", "error": "x"}]
    assert fault_advice.worst_severity(items) == "alta"
    assert fault_advice.worst_severity(items[:1]) == "media"
    assert fault_advice.worst_severity([]) is None


def test_every_specific_entry_is_complete():
    for code, e in list(fault_advice.SPECIFIC.items()) + list(fault_advice.PCODE_ADVICE.items()):
        assert e["severity"] in fault_advice.SEVERITY_TEXT, code
        assert e["system"] and isinstance(e["causes"], list) and isinstance(e["checks"], list), code


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
