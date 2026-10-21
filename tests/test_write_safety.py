"""Operações que escrevem no controlador: o programa só diz "aceite/gravado" quando o controlador devolve o
valor pedido. Recusas, respostas sem dados e releituras falhadas têm de aparecer como tal.
Corre sem Qt e sem carro (simulador com cenários de recusa)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import simulator
from rad.errors import KLineError, OperationUnconfirmed, RequestRejected
from rad.kline import KLine, SIM_PORT, SIM_D2XX_PORT, SIM_J2534_PORT, is_simulated_port
from rad.session import ECUSession


def _session(address=0x01, **profile):
    kl = KLine(SIM_PORT)
    kl.open()
    if profile:
        base = simulator.CLUSTER if address == 0x17 else simulator.ENGINE
        kl.ser.factories[address] = lambda: simulator.SimKW1281(dict(base, **profile))
    s = ECUSession(kl)
    s.connect(address)
    return kl, s


def test_rejected_coding_is_not_reported_as_accepted():
    kl, s = _session(coding_locked=True)
    try:
        s.recode(10002, 54321)
        assert False, "codificação recusada não pode ser dada como aceite"
    except RequestRejected as e:
        assert "recusou" in str(e) and "00002" in str(e)
    assert s.info["coding"] == 2                  # mostra o valor real que o controlador devolveu
    assert s.connected
    kl.close()


def test_adaptation_value_outside_limit_is_rejected():
    kl, s = _session(adapt_max={1: 150})
    assert s.adaptation_test(1, 140)["status"] == "ok"
    for fn in (lambda: s.adaptation_test(1, 200), lambda: s.adaptation_save(1, 200, 12345)):
        try:
            fn()
            assert False, "valor recusado não pode aparecer como gravado"
        except RequestRejected as e:
            assert "não aceitou" in str(e)
    assert s.adaptation_read(1)["value"] == 128   # nada mudou
    kl.close()


def test_adaptation_save_with_ack_only_is_unknown_not_success():
    kl, s = _session(adapt_save_ack_only=True)
    r = s.adaptation_save(1, 140, 12345)
    assert r["status"] == "unknown" and r["value"] is None and "desconhecido" in r["message"]
    kl.close()


def test_service_reset_does_not_save_when_test_is_refused():
    # o painel tem a revisão a 15 e recusa qualquer valor novo no canal 02
    kl, s = _session(0x17, adapt={2: 15, 9: 6, 30: 128}, adapt_max={2: -1})
    before = s.adaptation_read(2)["value"]
    assert before == 15
    try:
        s.service_reset(0)
        assert False
    except RequestRejected as e:
        assert "nada foi gravado" in str(e)
    assert s.adaptation_read(2)["value"] == before
    kl.close()


def test_service_reset_ok():
    kl, s = _session(0x17)
    assert s.service_reset(0)["status"] == "ok"
    assert s.adaptation_read(2)["value"] == 0
    kl.close()


def test_login_is_reported_as_sent_not_accepted():
    kl, s = _session()
    r = s.login(12233, 0)
    assert r["status"] == "sent" and "não indica" in r["message"]
    kl.close()


def test_clear_faults_with_failed_reread_is_unconfirmed():
    kl, s = _session()
    real = s.proto.read_faults
    s.proto.read_faults = lambda: (_ for _ in ()).throw(KLineError("cabo desligado"))
    try:
        s.clear_faults()
        assert False
    except OperationUnconfirmed as e:
        assert "não foi possível voltar a ler" in str(e)
    s.proto.read_faults = real
    kl.close()


def test_output_test_unexpected_answer_is_an_error_not_end():
    from rad.protocols import kw1281
    kl, s = _session()
    s.proto.request = lambda *a, **k: [kw1281.Block(1, kw1281.GROUP_RESPONSE, [1, 2, 3])]
    try:
        s.output_test()
        assert False
    except RequestRejected:
        pass
    kl.close()


def test_session_info_marks_simulated_interfaces():
    kl, s = _session()
    assert s.info["simulated"] is True and s.info["interface"] == SIM_PORT
    kl.close()
    assert all(is_simulated_port(p) for p in (SIM_PORT, SIM_D2XX_PORT, SIM_J2534_PORT))
    assert not any(is_simulated_port(p) for p in ("COM3", "D2XX:RT000001", "J2534:C:\\x.dll", "", None))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
