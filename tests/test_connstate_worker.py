"""Transições de estado reais na thread de comunicação, contra o SIMULADOR.

Precisa do PySide6 (importa rad.worker) — corre no PC com o programa instalado, não no ambiente de
auditoria. Mesmo assim NÃO precisa de carro nem de cabo: usa a porta SIMULADOR. Confirma que o estado
ECU_CONNECTED só aparece quando uma centralina responde de facto, e que abrir/fechar a interface fica em
OPEN_NO_ECU — nunca "ligado" só por a porta estar aberta."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad import connstate as cs
from rad.kline import SIM_PORT


def _worker():
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": SIM_PORT})
    links = []
    w.link_state.connect(lambda st: links.append(st))
    return w, links


def test_connecting_then_ecu_connected_on_a_real_answer():
    w, links = _worker()
    w._dispatch("connect", (0x01,))                 # motor: o simulador responde
    states = [s.state for s in links]
    assert cs.OPEN_NO_ECU in states                  # a interface abriu primeiro
    assert cs.CONNECTING in states
    assert states[-1] == cs.ECU_CONNECTED            # só no fim, com a centralina a responder
    assert links[-1].live and links[-1].data["address"] == 0x01
    w._close_all()


def test_no_ecu_answer_stays_open_no_ecu_not_connected():
    w, links = _worker()
    w._dispatch("connect", (0x7F,))                 # endereço sem centralina no simulador
    states = [s.state for s in links]
    assert cs.ECU_CONNECTED not in states            # nunca se apresenta como ligado
    assert states[-1] == cs.OPEN_NO_ECU
    assert not any(s.live for s in links)
    assert w.session is None
    w._close_all()


def test_disconnect_returns_to_open_no_ecu_while_interface_stays_open():
    w, links = _worker()
    w._dispatch("connect", (0x01,))
    assert links[-1].state == cs.ECU_CONNECTED
    w._dispatch("disconnect", ())
    assert links[-1].state == cs.OPEN_NO_ECU         # fechou o controlador, a interface continua aberta
    assert not links[-1].live
    w._close_all()


def test_legacy_state_signal_still_matches():
    # a interface antiga continua a receber disconnected/connecting/connected
    w = None
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": SIM_PORT})
    legacy, links = [], []
    w.state.connect(lambda s, d: legacy.append(s))
    w.link_state.connect(lambda st: links.append(st))
    w._dispatch("connect", (0x01,))
    assert legacy[-1] == "connected" == cs.legacy_bucket(links[-1].state)
    w._close_all()
