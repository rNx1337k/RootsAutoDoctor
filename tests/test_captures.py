"""Gravação e reprodução da comunicação (rad/capture.py, rad/replay.py), sem carro.

1. Uma sessão gravada com o simulador reproduz-se sem diferenças (bytes enviados e resultados).
2. Se o programa passar a enviar outros bytes, ou a interpretar a resposta de outra forma, a reprodução falha.
3. Todas as gravações em tests/captures/ (testes feitos em carros reais e no simulador) continuam a passar.
"""
import glob
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad import capture, replay
from rad.kline import SIM_ELM_PORT, SIM_PORT, is_simulated_port, port_label

HERE = os.path.dirname(os.path.abspath(__file__))


def _record(port, commands, adapter="kline"):
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": port, "adapter": adapter})
    errors = []
    w.error.connect(lambda c, m: errors.append((c, m)))
    path = os.path.join(tempfile.mkdtemp(), "sessao" + capture.EXT)
    w._dispatch("capture_start", (path,))
    for cmd, args in commands:
        w._dispatch(cmd, args)
    w._dispatch("capture_stop", ())
    assert capture.active() is None
    return path, errors


VAG_SESSION = [("connect", (0x01,)), ("read_faults", ()), ("read_group", (1,)), ("disconnect", ()),
               ("connect", (0x03,)), ("read_faults", ()), ("disconnect", ()), ("autoscan", ([0x01, 0x03, 0x17],))]


def test_vag_session_records_and_replays_without_differences():
    path, errors = _record(SIM_PORT, VAG_SESSION)
    assert errors == []
    head, events = capture.load(path)
    st = capture.stats(head, events)
    assert st["complete"] and st["simulated"] and st["bytes_tx"] > 100 and st["bytes_rx"] > st["bytes_tx"]
    assert st["commands"] == [c for c, _ in VAG_SESSION]
    assert any(e.get("ev") == "init5" and e.get("address") == 0x01 for e in events)
    r = replay.run(path)
    assert r["ok"], r
    assert r["commands"] == len(VAG_SESSION) and r["results"] >= 6


def test_obd_session_records_and_replays_without_differences():
    path, errors = _record(SIM_ELM_PORT, [("obd_connect", ()), ("obd_dtcs", ()), ("obd_disconnect", ())],
                           adapter="elm327")
    assert errors == []
    r = replay.run(path)
    assert r["ok"], r
    assert r["results"] == 2


def _rewrite(path, fn):
    head, events = capture.load(path)
    events = fn(events)
    out = path.replace(capture.EXT, "_alterada" + capture.EXT)
    with open(out, "w", encoding="utf-8") as fh:
        for obj in [head] + events:
            fh.write(json.dumps(obj) + "\n")
    return out


def test_replay_fails_when_the_program_sends_different_bytes():
    path, _ = _record(SIM_PORT, [("connect", (0x01,)), ("read_faults", ())])

    def change_request(events):
        # o primeiro byte enviado para pedir as avarias passa a ser outro: o programa actual já não "bate certo"
        start = next(i for i, e in enumerate(events) if e.get("note") == "cmd" and e["cmd"] == "read_faults")
        first_tx = next(e for e in events[start:] if "tx" in e)
        first_tx["tx"] = "29"
        return events
    r = replay.run(_rewrite(path, change_request))
    assert not r["ok"]
    assert any(d["what"] == "bytes diferentes" for d in r["divergences"])


def test_replay_fails_when_the_result_is_interpreted_differently():
    path, _ = _record(SIM_PORT, [("connect", (0x01,)), ("read_faults", ())])

    def change_expected(events):
        for e in events:
            if e.get("note") == "result" and e.get("cmd") == "read_faults":
                e["summary"][0][1] ^= 0x80              # intermitente ↔ permanente
        return events
    r = replay.run(_rewrite(path, change_expected))
    assert not r["ok"] and r["mismatches"] and r["mismatches"][0]["cmd"] == "read_faults"


def test_interrupted_recording_still_loads_and_replay_port_is_never_a_real_car():
    path, _ = _record(SIM_PORT, [("connect", (0x01,))])
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    with open(path, "w", encoding="utf-8") as fh:            # corte de energia a meio da última linha
        fh.writelines(lines[:-1])
        fh.write(lines[-1][:5])
    head, events = capture.load(path)
    assert head["rad_capture"] == capture.FORMAT and not capture.stats(head, events)["complete"]
    port = capture.replay_port(path)
    assert is_simulated_port(port) and port_label(port) != port


def test_validation_runs_all_steps_saves_a_report_and_replays():
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": SIM_PORT})
    out, steps = {}, []
    w.result.connect(lambda c, d: out.__setitem__(c, d))
    w.validation_step.connect(steps.append)
    w._dispatch("validation", ({"clear": True, "vehicle": {"plate": "AA-00-AA", "model": "Audi A3 1.9 TDI"}},))
    rep = out["validation"]
    assert [s["result"] for s in rep["steps"]] == ["ok"] * 10 and len(steps) == 10
    abs_mod = next(m for m in rep["modules"] if m["address"] == 0x03)
    assert abs_mod["protocol"] == "KWP2000" and abs_mod["faults_raw"][0]["status_hex"] == "23"
    with open(rep["report_path"], encoding="utf-8") as fh:
        page = fh.read()
    assert "0x23" in page and "Audi A3 1.9 TDI" in page and "KWP2000" in page
    assert "AA-00-AA" not in page                     # vai para o suporte: sem dados do cliente
    assert capture.active() is None and os.path.exists(rep["capture"])
    r = replay.run(rep["capture"])
    assert r["ok"], r


def test_validation_without_cable_stops_at_the_first_step():
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": SIM_PORT})
    out = {}
    w.result.connect(lambda c, d: out.__setitem__(c, d))
    w._ensure_port()
    w.kl.ser.echo = False                             # sem eco: cabo fora do carro ou ignição desligada
    w._dispatch("validation", ({},))
    rep = out["validation"]
    assert rep["steps"][0]["id"] == "interface" and rep["steps"][0]["result"] == "fail"
    assert [s["result"] for s in rep["steps"][1:]] == ["skip"] * 3


def test_every_saved_capture_still_replays():
    files = sorted(glob.glob(os.path.join(HERE, "captures", "*" + capture.EXT)))
    assert files, "tests/captures está vazio"
    for path in files:
        r = replay.run(path)
        assert r["ok"], f"{os.path.basename(path)}: {r}"
