"""Estados da ligação (rad/connstate.py) — lógica pura, sem Qt nem hardware.

Confirma que cada acontecimento é classificado no estado certo e, sobretudo, que só uma centralina que
respondeu de facto conta como "ligada". Corre em qualquer computador, sem o cabo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import connstate as cs
from rad.errors import (ConnectError, InterfaceError, KLineError, KLineTimeout, NoResponse, ProtocolError,
                        RequestRejected)


def test_legacy_mapping_keeps_the_old_three_buckets():
    assert cs.legacy_bucket(cs.ECU_CONNECTED) == "connected"
    assert cs.legacy_bucket(cs.CONNECTING) == "connecting"
    for s in (cs.NO_DEVICE, cs.UNREACHABLE, cs.OPEN_NO_ECU, cs.ERROR):
        assert cs.legacy_bucket(s) == "disconnected"


def test_only_ecu_connected_counts_as_real_communication():
    assert cs.is_live(cs.ECU_CONNECTED)
    for s in (cs.NO_DEVICE, cs.UNREACHABLE, cs.OPEN_NO_ECU, cs.CONNECTING, cs.ERROR):
        assert not cs.is_live(s), s
    # abrir a interface NÃO é ligação à centralina
    assert cs.opened("COM5").state == cs.OPEN_NO_ECU and not cs.opened("COM5").live


def test_connected_needs_an_identified_ecu():
    st = cs.connected({"address": 0x01, "module": "Motor", "part": "038906019FN"})
    assert st.state == cs.ECU_CONNECTED and st.live
    assert "01" in st.message and st.data["part"] == "038906019FN"


def test_interface_failure_is_unreachable_and_fatal():
    st = cs.classify_error(InterfaceError("o cabo foi arrancado"))
    assert st.state == cs.UNREACHABLE and st.fatal and "arrancado" in st.message


def test_no_ecu_answer_keeps_the_interface_open():
    for e in (NoResponse("sem ignição"), KLineTimeout("timeout")):
        st = cs.classify_error(e)
        assert st.state == cs.OPEN_NO_ECU and not st.fatal


def test_open_failure_distinguishes_present_from_absent():
    assert cs.classify_error(KLineError("porta ocupada"), present=True).state == cs.UNREACHABLE
    assert cs.classify_error(KLineError("não existe"), present=False).state == cs.NO_DEVICE
    # sem saber se está presente, assume-se inacessível (não se inventa "não detectada")
    assert cs.classify_error(KLineError("x"), present=None).state == cs.UNREACHABLE


def test_connect_error_with_a_responsive_interface_is_open_no_ecu():
    assert cs.classify_error(ConnectError("protocolo desconhecido")).state == cs.OPEN_NO_ECU


def test_request_rejected_does_not_mean_disconnected():
    # uma recusa pontual (NAK) é um erro de operação, não uma perda de ligação à interface
    st = cs.classify_error(RequestRejected("o controlador recusou"))
    assert st.state == cs.ERROR and not st.fatal


def test_generic_protocol_error_is_error():
    assert cs.classify_error(ProtocolError("qualquer")).state == cs.ERROR


def test_bad_state_is_rejected():
    try:
        cs.LinkStatus("inventado")
    except ValueError:
        return
    assert False, "um estado desconhecido devia ser recusado"
