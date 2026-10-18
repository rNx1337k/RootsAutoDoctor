import os, sys, tempfile
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


if __name__ == "__main__":
    test_history_roundtrip()
    print("OK test_history_roundtrip")
