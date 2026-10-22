"""Estados da ligação, iguais para todas as interfaces (KKL, J2534, simulador).

A ideia é separar claramente *o que aconteceu de facto* do que se mostra na interface. Cada estado
corresponde a um acontecimento real e verificável, não a uma mudança visual:

  NO_DEVICE      — nenhuma interface foi encontrada no computador.
  UNREACHABLE    — a interface existe mas não se consegue abrir (ocupada por outro programa, driver em
                   falta, cabo arrancado, ponte bloqueada).
  OPEN_NO_ECU    — a interface abriu e comunica, mas nenhuma centralina respondeu (sem ignição, endereço
                   errado, cabo fora da ficha OBD). O cabo está bom; a centralina é que não atende.
  CONNECTING     — a estabelecer a ligação a uma centralina (transitório).
  ECU_CONNECTED  — uma centralina respondeu e identificou-se: há comunicação real confirmada.
  ERROR          — erro de comunicação durante uma operação já estabelecida.

A regra central: ECU_CONNECTED só é válido quando uma centralina devolveu a sua identificação. Detectar o
cabo no USB ou abrir a porta NÃO é ligação à centralina — fica em UNREACHABLE/OPEN_NO_ECU.

Este módulo é lógica pura (sem Qt nem hardware), para poder ser testado sem o cabo nem a interface gráfica.
O worker (rad/worker.py) usa-o para classificar os acontecimentos e emite o resultado para a interface.
"""

NO_DEVICE = "no_device"
UNREACHABLE = "unreachable"
OPEN_NO_ECU = "open_no_ecu"
CONNECTING = "connecting"
ECU_CONNECTED = "ecu_connected"
ERROR = "error"

ALL = (NO_DEVICE, UNREACHABLE, OPEN_NO_ECU, CONNECTING, ECU_CONNECTED, ERROR)

# Rótulo curto para a interface, em português.
LABELS = {
    NO_DEVICE: "Sem interface",
    UNREACHABLE: "Interface inacessível",
    OPEN_NO_ECU: "Interface aberta (sem centralina)",
    CONNECTING: "A ligar…",
    ECU_CONNECTED: "Ligado à centralina",
    ERROR: "Erro de comunicação",
}

# Só ECU_CONNECTED representa comunicação real com uma centralina.
LIVE = {ECU_CONNECTED}

# Ligação à versão antiga do sinal de estado (três valores), para a interface actual não precisar de mudar:
# disconnected | connecting | connected.
_LEGACY = {
    NO_DEVICE: "disconnected",
    UNREACHABLE: "disconnected",
    OPEN_NO_ECU: "disconnected",
    CONNECTING: "connecting",
    ECU_CONNECTED: "connected",
    ERROR: "disconnected",
}


def legacy_bucket(state):
    """O valor equivalente no sinal antigo (disconnected/connecting/connected)."""
    return _LEGACY[state]


def is_live(state):
    """True só quando há comunicação real confirmada com uma centralina."""
    return state in LIVE


class LinkStatus:
    """Um acontecimento de ligação: o estado, uma mensagem para o utilizador e se é fatal para a interface
    (fatal=True obriga a fechar e reabrir a interface — ex.: cabo arrancado)."""

    __slots__ = ("state", "message", "fatal", "data")

    def __init__(self, state, message="", fatal=False, data=None):
        if state not in ALL:
            raise ValueError(f"estado desconhecido: {state!r}")
        self.state = state
        self.message = message or LABELS[state]
        self.fatal = fatal
        self.data = data

    @property
    def label(self):
        return LABELS[self.state]

    @property
    def live(self):
        return is_live(self.state)

    @property
    def legacy(self):
        return legacy_bucket(self.state)

    def __repr__(self):
        return f"LinkStatus({self.state}, fatal={self.fatal})"

    def __eq__(self, other):
        return (isinstance(other, LinkStatus) and self.state == other.state
                and self.message == other.message and self.fatal == other.fatal)


def connected(info):
    """Centralina ligada e identificada (info = identificação devolvida pela centralina)."""
    addr = info.get("address")
    name = info.get("module", "")
    where = f"{addr:02X}" if isinstance(addr, int) else "?"
    return LinkStatus(ECU_CONNECTED, f"Ligado a {where} — {name}".strip(" —"), data=info)


def obd_connected(info):
    """Veículo ligado por OBD-II: pelo menos uma centralina respondeu ao pedido 01 00."""
    n = len(info.get("ecus", []))
    return LinkStatus(ECU_CONNECTED, f"Ligado por OBD-II — {info.get('protocol', '')} · {n} centralina(s)",
                      data=info)


def connecting(address):
    where = f"{address:02X}" if isinstance(address, int) else str(address)
    return LinkStatus(CONNECTING, f"A ligar ao controlador {where}…", data=address)


def opened(port):
    """A interface abriu, mas ainda não falou com nenhuma centralina."""
    return LinkStatus(OPEN_NO_ECU, f"Interface {port} aberta — ainda sem ligação a nenhuma centralina.",
                      data=port)


def classify_error(exc, present=None):
    """Classifica uma excepção da camada de comunicação num estado, sem a esconder.

    present: True/False se se sabe que a interface está (ou não) presente no computador; None = desconhecido.
    Distingue "não detectada" de "detectada mas inacessível" só quando essa informação existe — nunca se
    inventa a diferença.

    Devolve um LinkStatus. Importa aqui dentro para o módulo não depender de rad.errors ao ser importado
    noutros contextos (e para os testes poderem usar as mesmas classes)."""
    from .errors import (ConnectError, InterfaceError, KLineError, KLineTimeout, NoResponse, ProtocolError,
                         RequestRejected)
    msg = str(exc)
    # A interface em si falhou (porta fechou, cabo arrancado, ponte/driver bloqueado): fatal, há que reabrir.
    if isinstance(exc, InterfaceError):
        return LinkStatus(UNREACHABLE, msg, fatal=True)
    # Nenhuma centralina respondeu: a interface está boa, falta ignição/endereço/ficha OBD.
    if isinstance(exc, (NoResponse, KLineTimeout)):
        return LinkStatus(OPEN_NO_ECU, msg)
    # A porta não abriu (ocupada, sem driver, inexistente): detectada → inacessível; ausente → não detectada.
    if isinstance(exc, KLineError):
        if present is False:
            return LinkStatus(NO_DEVICE, msg, fatal=True)
        return LinkStatus(UNREACHABLE, msg, fatal=True)
    # Falhou o estabelecimento da ligação, mas a interface respondeu: fica aberta, sem centralina.
    if isinstance(exc, ConnectError):
        return LinkStatus(OPEN_NO_ECU, msg)
    # Recusa de um pedido pontual (NAK): não mexe no estado da ligação.
    if isinstance(exc, RequestRejected):
        return LinkStatus(ERROR, msg)
    if isinstance(exc, ProtocolError):
        return LinkStatus(ERROR, msg)
    return LinkStatus(ERROR, msg)
