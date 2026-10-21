import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rad import history, report


def test_history_roundtrip():
    d = tempfile.mkdtemp()
    items = [{"address": 1, "module": "Motor", "status": "ok",
              "info": {"part": "038906019FN", "component": "1,9l", "coding": 2, "wsc": 1},
              "faults": [{"vag": "00532", "pcode": "", "desc": "Tensão", "elab": "baixa",
                          "elab_code": 7, "intermittent": True}]}]
    sid = history.save_session("autoscan", {"plate": "12-AB-34", "client": "João"}, items, directory=d)
    lst = history.list_sessions(d)
    assert lst[0]["id"] == sid and lst[0]["faults"] == 1 and lst[0]["plate"] == "12-AB-34"
    data = history.load_session(sid, d)
    html = report.build_html({"name": "Oficina"}, data["vehicle"], data["items"])
    assert "00532" in html and "12-AB-34" in html
    history.delete_session(sid, d)
    assert history.list_sessions(d) == []


def test_same_second_ids_are_unique():
    d = tempfile.mkdtemp()
    a = history.save_session("modulo", {"plate": "AA"}, [], directory=d)
    b = history.save_session("modulo", {"plate": "AA"}, [], directory=d)
    assert a != b and len(history.list_sessions(d)) == 2


def test_imports_old_json_files():
    d = tempfile.mkdtemp()
    old = {"id": "20260101_100000_OLD", "date": "2026-01-01T10:00:00", "kind": "autoscan",
           "vehicle": {"plate": "OLD"}, "items": [{"status": "ok", "faults": [{}, {}]}], "notes": ""}
    with open(os.path.join(d, old["id"] + ".json"), "w", encoding="utf-8") as fh:
        json.dump(old, fh)
    with open(os.path.join(d, "estragado.json"), "w", encoding="utf-8") as fh:
        fh.write("{nao e json")
    lst = history.list_sessions(d)
    assert [s["id"] for s in lst] == [old["id"]] and lst[0]["faults"] == 2
    assert history.load_session(old["id"], d) == old
    assert os.path.exists(os.path.join(d, "importados", old["id"] + ".json"))
    assert os.path.exists(os.path.join(d, "importados", "com_erro", "estragado.json"))   # guardado, não se perde



def _item(addr, codes, status="ok"):
    from rad import vag_data
    return {"address": addr, "module": vag_data.module_name(addr), "status": status,
            "info": {"part": "P", "component": "C"}, "faults": [vag_data.decode_fault(c, 0) for c in codes]}


def test_compare_new_resolved_persisting():
    old = [_item(1, [532, 1247]), _item(3, []), _item(0x17, [771])]
    new = [_item(1, [1247, 522]), _item(3, [283]), _item(0x17, [], status="error")]
    d = history.compare(old, new)
    assert sorted((f["address"], f["vag"]) for f in d["new"]) == [(1, "00522"), (3, "00283")]
    assert [(f["address"], f["vag"]) for f in d["resolved"]] == [(1, "00532")]   # o 17 não foi lido agora
    assert [(f["address"], f["vag"]) for f in d["persisting"]] == [(1, "01247")]
    assert history.compare([], []) == {"new": [], "resolved": [], "persisting": []}


def test_previous_for_plate():
    d = tempfile.mkdtemp()
    a = history.save_session("autoscan", {"plate": "12-ab-34"}, [_item(1, [532])], directory=d)
    history.save_session("autoscan", {"plate": "99-ZZ-99"}, [], directory=d)
    b = history.save_session("autoscan", {"plate": "12 AB 34"}, [_item(1, [])], directory=d)
    prev = history.previous_for_plate("12AB34", before=b, directory=d)
    assert prev is not None and prev["id"] == a                       # ignora traços, espaços e maiúsculas
    assert history.previous_for_plate("12AB34", before=a, directory=d) is None
    assert history.previous_for_plate("12AB34", directory=d)["id"] == b
    assert history.previous_for_plate("", directory=d) is None


def test_report_includes_advice():
    items = [_item(1, [1247])]
    html = report.build_html({"name": "Oficina"}, {"plate": "AA"}, items)
    # as causas aparecem como sugestão do programa, não como certeza
    assert "Possíveis causas (sugestão do programa" in html and "N75" in html and "gravidade média" in html


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
