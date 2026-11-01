"""Codificação, adaptação e acesso de segurança em KWP2000 (linha K), contra o controlador ABS simulado.

As sequências seguem as capturas de uma EDC16 publicadas pelo kw1281test (MIT). O que se verifica aqui é o lado do
programa: bytes enviados, interpretação das respostas e, sobretudo, que nada é dado como gravado sem o controlador
o confirmar."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad import simulator
from rad.errors import NotSupported, RequestRejected
from rad.kline import KLine, SIM_PORT
from rad.protocols import kwp2000
from rad.session import ECUSession

CODE = simulator.ABS["security_code"]


def _abs():
    kl = KLine(SIM_PORT, echo="auto")
    kl.open()
    s = ECUSession(kl)
    return s, s.connect(0x03)


def _raises(exc, fn, *args):
    try:
        fn(*args)
    except exc as e:
        return e
    raise AssertionError(f"{fn.__name__} devia ter falhado com {exc.__name__}")


def test_workshop_code_codec_matches_the_documented_example():
    raw = kwp2000.encode_wsc6(45678, 345, 987654)
    assert bytes(raw).hex(" ").upper() == "78 90 32 B2 B2 6E"
    assert kwp2000.decode_wsc6(raw) == (45678, 345, 987654)
    _raises(ValueError, kwp2000.encode_wsc6, 200000)


def test_identification_with_coding_and_workshop_code():
    s, info = _abs()
    assert info["protocol"] == "KWP2000" and info["part"] == "1C0907379K"
    assert info["component"] == "ABS/ESP 20 IE CAN" and info["coding"] == 18719 and info["wsc"] == 12345
    assert info["coding_digits"] == 7 and set(info["features"]) == {"basic", "adaptation", "coding", "login", "outputs"}
    s.disconnect()


def test_adaptation_needs_access_code_and_every_write_is_read_back():
    s, _ = _abs()
    e = _raises(RequestRejected, s.adaptation_read, 5)
    assert "Login" in str(e)
    e = _raises(RequestRejected, s.login, CODE + 1, 0)
    assert "recusou o código" in str(e)
    assert s.login(CODE, 0)["status"] == "ok"
    assert s.adaptation_read(5)["value"] == 120
    assert s.adaptation_test(5, 130)["status"] == "ok"
    r = s.adaptation_save(5, 130, 0)
    assert r["status"] == "ok" and r["value"] == 130 and r["previous"] == 120
    assert s.adaptation_read(5)["value"] == 130
    e = _raises(RequestRejected, s.adaptation_read, 99)
    assert "canal 99" in str(e)
    s.disconnect()


def test_coding_keeps_workshop_code_and_is_confirmed_by_reading_again():
    s, _ = _abs()
    sent = []
    proto = s.proto
    orig = proto.request

    def spy(payload, timeout=1.0):
        sent.append(list(payload))
        return orig(payload, timeout)
    proto.request = spy
    r = s.recode(18720, 99999)                      # o código de oficina pedido não é usado: fica o da centralina
    assert r["status"] == "ok" and r["previous"] == 18719 and r["info"]["coding"] == 18720
    write = next(p for p in sent if p[:2] == [0x3B, 0x9A])
    assert write[2:8] == simulator.ABS["wsc6"] and write[8:12] == list(b"0001")
    assert write[12:] == [0x03, 0x00, 0x49, 0x20]                    # 03 + 18720 em 3 bytes
    _raises(RequestRejected, s.recode, 10_000_000, 0)
    s.disconnect()


def test_coding_ignored_by_the_module_is_reported_as_rejected():
    s, _ = _abs()
    ecu = s.kl.ser.ecu
    real = ecu.handle

    def ignore_coding(p):
        if p[0] == 0x3B:
            return [0x7B, 0x9A]                     # diz que sim, mas não muda nada
        return real(p)
    ecu.handle = ignore_coding
    e = _raises(RequestRejected, s.recode, 18720, 0)
    assert "recusou a codificação" in str(e)
    s.disconnect()


def test_unknown_identification_layout_disables_writing():
    s, _ = _abs()
    ecu = s.kl.ser.ecu
    real = ecu.handle

    def old_layout(p):
        if p[0] == 0x1A:
            return [0x5A, 0x9B] + list(b"1C0907379K  0101") + [0x00, 0x05, 0x00, 0x00] + list(b"ABS 20 IE")
        return real(p)
    ecu.handle = old_layout
    info = s.proto.read_ident()
    assert info["coding"] is None and s.proto.features == ()
    _raises(NotSupported, s.recode, 18720, 0)
    s.disconnect()


def test_vag_over_can_writes_with_the_same_safeguards():
    from rad.vagcan import SIM_PORT as CAN_SIM
    from rad.vagcan.link import VagCanLink
    from rad.vagcan.simbus import PROFILES
    link = VagCanLink(CAN_SIM)
    link.open()
    s = ECUSession(link)
    info = s.connect(0x01)
    assert info["protocol"] == "KWP2000 (CAN TP2.0)" and info["coding"] == 72 and "coding" in info["features"]
    _raises(RequestRejected, s.adaptation_read, 4)                   # sem acesso de segurança
    assert s.login(PROFILES[0x01]["security_code"], 0)["status"] == "ok"
    assert s.adaptation_save(4, 3, 0)["value"] == 3
    r = s.recode(73, 0)
    assert r["status"] == "ok" and r["info"]["coding"] == 73
    assert s.basic_setting(1)["fields"]
    assert s.output_test()["code"] == PROFILES[0x01]["outputs"][0]
    s.keep_alive()
    s.disconnect()
    link.close()


def test_worker_logs_kwp2000_coding_in_the_change_journal():
    from rad import journal
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": SIM_PORT})
    res = []
    w.result.connect(lambda c, d: res.append((c, d)))
    w._dispatch("connect", (0x03,))
    w._dispatch("recode", (18721, 0))
    assert res[-1][0] == "recode" and res[-1][1]["status"] == "ok"
    changes = journal.list_changes(0x03, "1C0907379K")
    assert any(c["kind"] == "coding" and c["after"] == 18721 and c["before"] == 18719 for c in changes)
    w._dispatch("disconnect", ())


def _spy(s):
    sent = []
    orig = s.proto.request

    def spy(payload, timeout=1.0):
        sent.append(list(payload))
        return orig(payload, timeout)
    s.proto.request = spy
    return sent


def test_basic_setting_enters_once_polls_and_leaves_the_routine():
    s, _ = _abs()
    sent = _spy(s)
    assert s.basic_setting(1)["group"] == 1 and s.basic_setting(1)["fields"]
    assert sent[:3] == [[0x31, 0xB8, 0x00, 0x00], [0x31, 0xB8, 0x00, 0x01], [0x31, 0xBA, 0x00, 0x01]]
    assert sent[3] == [0x31, 0xBA, 0x00, 0x01]                       # a segunda leitura não volta a entrar
    r = s.basic_setting(1)
    assert len(r["raw"]) == 12                                        # o campo vazio do fim (0x25) foi tirado
    s.basic_setting(2)
    assert [0x32, 0xB8, 0x00, 0x01] in sent                           # mudar de grupo sai do anterior
    s.read_faults()
    assert sent[-2] == [0x32, 0xB8, 0x00, 0x02] and sent[-1][0] == 0x18   # outra função sai primeiro
    e = _raises(RequestRejected, s.basic_setting, 7)
    assert "007" in str(e)
    s.disconnect()


def test_output_test_steps_through_every_output_and_closes_at_the_end():
    s, _ = _abs()
    sent = _spy(s)
    codes = []
    while True:
        r = s.output_test()
        if r is None:
            break
        codes.append(r["code"])
    assert codes == simulator.ABS["outputs"]
    assert sent[-1] == [0x32, 0xB8, 0x01, 0x02]                       # fim da lista: rotina fechada
    assert sent.count([0x31, 0xB9, 0x01, 0x02]) == 2 * len(codes)    # activar + passar à seguinte
    s.output_test()                                                   # recomeça do início
    s.keep_alive()                                                    # durante o teste: lê a saída (31 BA)
    assert sent[-1] == [0x31, 0xBA, 0x01, 0x02]
    s.disconnect()
    assert [0x32, 0xB8, 0x01, 0x02] in sent[-3:]
