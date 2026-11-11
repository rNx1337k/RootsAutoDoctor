"""Impede o Windows de suspender o PC enquanto o programa fala com o carro.

Um portátil a bateria pode suspender a meio de um Auto-Scan ou de uma leitura de valores: o USB do cabo é cortado e
a centralina fica a meio da sessão. Enquanto houver comunicação, o programa pede ao Windows que não suspenda
(SetThreadExecutionState). O ecrã pode desligar-se na mesma: só a suspensão do sistema é impedida.

O pedido é por thread: tem de ser ligado e desligado sempre na mesma thread (a de comunicação)."""
import logging
import sys

log = logging.getLogger(__name__)

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _set_state(flags):
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.SetThreadExecutionState(flags))
    except Exception:
        log.warning("SetThreadExecutionState falhou", exc_info=True)
        return False


class KeepAwake:
    """Estado do pedido para a thread actual. set(True/False) só chama o Windows quando o estado muda."""

    def __init__(self, set_state=None):
        self._set_state = set_state or _set_state
        self.active = False

    def set(self, active):
        active = bool(active)
        if active == self.active:
            return
        flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if active else 0)
        if self._set_state(flags) or not active:
            self.active = active
            log.info("Suspensão do PC %s", "bloqueada (comunicação em curso)" if active else "permitida")
