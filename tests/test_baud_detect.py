"""Escolha da velocidade da linha K: o byte que chega quando a velocidade está errada diz qual é a certa, e um
sync que parece bom a 10400 baud vindo de um controlador a 9600 (e vice-versa) não deixa a ligação falhar.
Corre sem Qt e sem carro (porta falsa)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import session as session_mod
from rad.errors import ConnectError, InterfaceError, KLineTimeout, NoResponse
from rad.kline import KLine, SIM_PORT, rank_bauds, uart_reads
from rad.session import AUTO_BAUDS, ECUSession


def test_uart_model_reads_the_sync_byte_at_the_right_speed():
    for baud in AUTO_BAUDS:
        assert uart_reads(0x55, baud, baud) == {0x55}
    assert 0x00 in uart_reads(0x55, 1200, 10400)          # controlador lento: só se vê o bit de início
    assert 0xF8 in uart_reads(0x55, 2400, 10400)
    assert 0x66 in uart_reads(0x55, 4800, 10400)
    assert uart_reads(0x55, 9600, 10400) - {0x55}          # 9600 a 10400: quase sempre lixo


def test_rank_puts_the_speed_the_byte_points_to_first_and_never_drops_any():
    rest = [9600, 4800, 2400, 1200]
    assert rank_bauds(0x00, 10400, rest)[0] == 1200
    assert rank_bauds(0xF8, 10400, rest)[0] == 2400
    assert rank_bauds(0x66, 10400, rest)[0] == 4800
    assert rank_bauds(0xB5, 10400, rest)[0] == 9600
    for b in (0x00, 0x13, 0x2A, 0xF8, None):
        assert sorted(rank_bauds(b, 10400, rest)) == sorted(rest)
    assert rank_bauds(0x13, 10400, rest) == rest           # byte que não diz nada: ordem original


class FakeLink:
    """Porta falsa: cada init devolve o que o "controlador" a `ecu_baud` responderia à velocidade pedida."""
    is_simulator = True
    cancelled = False
    echo = True
    port_name = "COM9"

    def __init__(self, ecu_baud, fake_sync_at=None):
        self.ecu_baud = ecu_baud
        self.fake_sync_at = fake_sync_at        # velocidade errada em que o sync parece bom
        self.tried = []

    def five_baud_init(self, address, baud):
        self.tried.append(baud)
        if baud == self.ecu_baud or baud == self.fake_sync_at:
            return {"status": "ok", "kb1": 0x01, "kb2": 0x8A, "keyword": 1281, "address_byte": address}
        reads = sorted(uart_reads(0x55, self.ecu_baud, baud) - {0x55})
        return {"status": "garbage", "byte": reads[0]} if reads else {"status": "none"}


class FakeKW1281:
    name = "KW1281"
    features = ()
    coding_digits = 5
    fail_with = KLineTimeout

    def __init__(self, kl, address, log=None):
        self.kl = kl

    def start(self):
        if self.kl.tried[-1] != self.kl.ecu_baud:
            raise self.fail_with("Bloco incompleto (timeout)")
        return {"part": "1J0920926C", "component": "KOMBI", "extra": "", "coding": 4211, "wsc": 0, "raw": []}


def _with_fake_kw1281(fn, fail_with=KLineTimeout):
    real = session_mod.KW1281
    FakeKW1281.fail_with = fail_with
    session_mod.KW1281 = FakeKW1281
    try:
        return fn()
    finally:
        session_mod.KW1281 = real


def test_slow_module_is_reached_on_the_second_attempt():
    for ecu_baud in (4800, 2400, 1200):
        link = FakeLink(ecu_baud)
        info = _with_fake_kw1281(lambda: ECUSession(link).connect(0x15))
        assert info["baud"] == ecu_baud and link.tried == [10400, ecu_baud], (ecu_baud, link.tried)


def test_sync_that_looks_right_at_the_neighbour_speed_does_not_lose_the_module():
    link = FakeLink(9600, fake_sync_at=10400)
    logs = []
    info = _with_fake_kw1281(lambda: ECUSession(link, logs.append).connect(0x17))
    assert info["baud"] == 9600 and link.tried == [10400, 9600]
    assert any("não arrancou a 10400" in m for m in logs)


def test_neighbour_retry_keeps_the_real_error_if_nothing_else_works():
    link = FakeLink(9600, fake_sync_at=10400)
    link.ecu_baud = 4800                                  # nem 10400 nem 9600 arrancam
    link.five_baud_init = lambda a, b, _f=link.five_baud_init: (
        {"status": "none"} if b == 9600 else _f(a, b))
    try:
        _with_fake_kw1281(lambda: ECUSession(link).connect(0x17))
        assert False, "devia falhar"
    except NoResponse:
        assert False, "o erro útil é o do arranque, não 'não responde'"
    except KLineTimeout:
        pass


def test_interface_failure_and_fixed_speed_are_not_retried_at_another_speed():
    link = FakeLink(9600, fake_sync_at=10400)
    try:
        _with_fake_kw1281(lambda: ECUSession(link).connect(0x17), fail_with=InterfaceError)
        assert False
    except InterfaceError:
        assert link.tried == [10400]
    link = FakeLink(9600, fake_sync_at=10400)
    try:
        _with_fake_kw1281(lambda: ECUSession(link, baud="10400").connect(0x17))
        assert False
    except KLineTimeout:
        assert link.tried == [10400]


def test_no_speed_answers_still_says_sync_failed():
    link = FakeLink(9600)
    link.five_baud_init = lambda a, b: (link.tried.append(b), {"status": "garbage", "byte": 0x13})[1]
    try:
        ECUSession(link).connect(0x17)
        assert False
    except NoResponse:
        assert False
    except ConnectError:
        assert link.tried == list(AUTO_BAUDS)


def test_simulated_cluster_at_9600_is_found_straight_away():
    kl = KLine(SIM_PORT)
    kl.open()
    logs = []
    info = ECUSession(kl, logs.append).connect(0x17)
    assert info["baud"] == 9600
    assert any("o byte indica 9600 baud" in m for m in logs)
    kl.close()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
