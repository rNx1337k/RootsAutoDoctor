"""Registo de alterações: cada codificação/adaptação gravada guarda o valor anterior, para se poder voltar ao
original. Escritas recusadas não ficam registadas (não mudaram nada). Corre sem Qt e sem carro."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import journal, simulator
from rad.errors import RequestRejected
from rad.kline import KLine, SIM_PORT
from rad.session import ECUSession

ENGINE = {"address": 0x01, "module": "Electrónica do motor", "part": "038906019FN", "component": "1,9l R4 EDC"}


def _session(address=0x01, **profile):
    kl = KLine(SIM_PORT)
    kl.open()
    if profile:
        base = simulator.CLUSTER if address == 0x17 else simulator.ENGINE
        kl.ser.factories[address] = lambda: simulator.SimKW1281(dict(base, **profile))
    s = ECUSession(kl)
    s.connect(address)
    return kl, s


def test_record_and_list_newest_first():
    d = tempfile.mkdtemp()
    a = journal.record("coding", ENGINE, requested=4102, before=2, after=4102, directory=d)
    b = journal.record("adaptation", ENGINE, requested=140, before=128, after=140, channel=1, directory=d)
    rows = journal.list_changes(directory=d)
    assert [r["id"] for r in rows] == [b, a]
    assert rows[1]["part"] == "038906019FN" and rows[1]["before"] == 2 and rows[1]["after"] == 4102
    assert rows[0]["channel"] == 1 and rows[0]["status"] == "ok" and rows[0]["simulated"] == 0


def test_list_filters_by_controller():
    d = tempfile.mkdtemp()
    journal.record("coding", ENGINE, requested=1, before=2, after=1, directory=d)
    journal.record("coding", dict(ENGINE, address=0x17, part="1J0920826C"), requested=1, before=2, after=1,
                   directory=d)
    journal.record("coding", ENGINE, requested=3, before=1, after=3, simulated=True, directory=d)
    assert len(journal.list_changes(address=0x01, part="038906019FN", directory=d)) == 2
    assert len(journal.list_changes(address=0x01, part="038906019FN", simulated=False, directory=d)) == 1
    assert len(journal.list_changes(address=0x17, directory=d)) == 1


def test_original_value_is_the_value_before_the_first_change():
    d = tempfile.mkdtemp()
    journal.record("coding", ENGINE, requested=4102, before=2, after=4102, directory=d)
    journal.record("coding", ENGINE, requested=4103, before=4102, after=4103, directory=d)
    journal.record("adaptation", ENGINE, requested=140, before=None, after=140, channel=1, directory=d)
    journal.record("adaptation", ENGINE, requested=150, before=140, after=150, channel=1, directory=d)
    assert journal.original_value(0x01, "038906019FN", "coding", directory=d) == 2
    # o primeiro registo do canal 1 não tinha valor anterior conhecido: usa o primeiro que tem
    assert journal.original_value(0x01, "038906019FN", "adaptation", channel=1, directory=d) == 140
    assert journal.original_value(0x01, "038906019FN", "adaptation", channel=2, directory=d) is None
    assert journal.original_value(0x01, "038906019FN", "coding", simulated=True, directory=d) is None


def test_invalid_kind_or_status_is_refused():
    d = tempfile.mkdtemp()
    for kw in ({"kind": "flash"}, {"kind": "coding", "status": "rejected"}):
        try:
            journal.record(info=ENGINE, requested=1, directory=d, **kw)
            assert False, f"{kw} não pode ser registado"
        except ValueError:
            pass
    assert journal.list_changes(directory=d) == []


def test_describe():
    assert journal.describe({"kind": "coding", "channel": None, "before": 2, "after": 4102, "requested": 4102,
                             "status": "ok"}) == "Codificação: 00002 → 04102"
    assert journal.describe({"kind": "adaptation", "channel": 1, "before": None, "after": None, "requested": 140,
                             "status": "unknown"}) == "Adaptação canal 01: ? → 140 (por confirmar)"


def test_session_recode_returns_previous_coding():
    kl, s = _session()
    before = s.info["coding"]
    r = s.recode(4102, 12345)
    assert r["status"] == "ok" and r["previous"] == before
    kl.close()


def test_session_adaptation_save_returns_previous_value():
    kl, s = _session()
    before = s.adaptation_read(1)["value"]
    r = s.adaptation_save(1, 140, 12345)
    assert r["status"] == "ok" and r["previous"] == before and r["value"] == 140
    kl.close()


def test_session_adaptation_unknown_result_still_has_previous():
    kl, s = _session(adapt_save_ack_only=True)
    r = s.adaptation_save(1, 140, 12345)
    assert r["status"] == "unknown" and r["previous"] == 128
    kl.close()


def test_channel_zero_has_no_previous_value():
    kl, s = _session()
    r = s.adaptation_save(0, 0, 12345)
    assert r["previous"] is None
    kl.close()


def test_rejected_write_raises_so_nothing_is_recorded():
    kl, s = _session(coding_locked=True)
    try:
        s.recode(10002, 54321)
        assert False
    except RequestRejected:
        pass
    kl.close()


def test_service_reset_records_the_mileage_counter_before_the_test():
    kl, s = _session(0x17, adapt={2: 15, 9: 6, 30: 128})
    r = s.service_reset(0)
    assert r["status"] == "ok" and r["previous"] == 15 and r["value"] == 0
    kl.close()
