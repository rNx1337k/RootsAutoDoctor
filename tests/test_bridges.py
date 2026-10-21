"""Pontes J2534 / D2XX: erros do driver e respostas inválidas têm de chegar ao programa como erros da
interface (não como "o controlador não respondeu" nem como "erro interno"). Sem hardware."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import d2xx, j2534, j2534_bridge
from rad.errors import KLineError


class _FakePassThru:
    """DLL J2534 falsa: devolve o código de erro pedido em PassThruReadMsgs."""

    def __init__(self, ret, count=0):
        self.ret, self.count = ret, count

    def PassThruReadMsgs(self, channel, msg, n, timeout):
        n._obj.value = self.count
        return self.ret

    def PassThruGetLastError(self, buf):
        return 0


def test_j2534_driver_error_is_not_a_timeout():
    be = j2534_bridge.PassThruBackend()
    be.dll = _FakePassThru(ret=0x08)                       # ERR_DEVICE_NOT_CONNECTED, sem mensagens
    try:
        be.read(100)
        assert False, "erro do driver não pode ser tratado como 'sem resposta'"
    except RuntimeError as e:
        assert "erro J2534 8" in str(e)
    for code in (j2534_bridge.ERR_BUFFER_EMPTY, j2534_bridge.ERR_TIMEOUT):
        be.dll = _FakePassThru(ret=code)
        assert be.read(100) is None                        # silêncio normal do controlador


def _garbage_bridge(name):
    from rad.bridge import BridgeProcess
    code = "import sys; sys.stdin.readline(); print('PassThru driver v1.0 loaded'); sys.stdout.flush(); sys.stdin.read()"
    return BridgeProcess([sys.executable, "-c", code], name)


def test_invalid_bridge_line_is_an_interface_error():
    link = j2534.J2534Link("J2534:" + j2534.SIM_DLL)
    link.proc = _garbage_bridge("J2534")                 # driver a escrever no stdout
    try:
        link._call("read", timeout_ms=10)
        assert False
    except KLineError as e:
        assert "Resposta inválida da ponte J2534" in str(e)
    assert link.proc is None                             # ponte fechada: a conversa ficou dessincronizada

    s = d2xx.D2xxSerial.__new__(d2xx.D2xxSerial)
    s.port, s.proc = d2xx.SIM_PORT, _garbage_bridge("D2XX")
    try:
        s._call("purge")
        assert False
    except KLineError as e:
        assert "Resposta inválida da ponte D2XX" in str(e)
    assert s.proc is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
