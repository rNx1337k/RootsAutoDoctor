"""Contrato comum entre as interfaces (ELM327, ISO-TP sobre CAN…) e os serviços (OBD-II, UDS).

Um "link" é qualquer objecto com:

    request(payload: bytes, target=None, timeout=None) -> list[Response]
        Envia um pedido de diagnóstico (o 1.º byte é o serviço) e devolve as respostas de TODAS as
        centralinas que responderam, já remontadas (multi-trama). target=None → pedido funcional (todas as
        centralinas OBD); target="7E0" (CAN) → pedido físico a uma centralina.
        Sem nenhuma resposta → levanta NoResponse. Erro da interface → InterfaceError.
    protocol: str            nome do protocolo físico em uso (ex.: "ISO 15765-4 CAN 11 bits 500 kbit/s")
    is_can: bool
    simulated: bool          True quando a interface é um simulador (os dados não vêm de um veículo)
    describe() -> dict       informação da interface (para o relatório e o registo)

As respostas negativas (0x7F) NÃO levantam excepção aqui: chegam como Response com .negative = True,
porque num pedido funcional uma centralina pode recusar e outra aceitar. Os serviços decidem.
"""
from ..errors import RequestRejected

NRC = {
    0x10: "recusa geral",
    0x11: "serviço não suportado",
    0x12: "sub-função não suportada",
    0x13: "comprimento ou formato da mensagem incorrecto",
    0x14: "resposta demasiado longa",
    0x21: "ocupada — repetir o pedido",
    0x22: "condições incorrectas (ex.: motor a trabalhar, velocidade, tensão)",
    0x24: "sequência de pedidos incorrecta",
    0x25: "sem resposta de um componente da sub-rede",
    0x26: "uma falha impede a execução",
    0x31: "pedido fora do intervalo (identificador não suportado)",
    0x33: "acesso de segurança negado",
    0x35: "chave inválida",
    0x36: "número de tentativas excedido",
    0x37: "tempo de espera obrigatório ainda não passou",
    0x70: "transferência não aceite",
    0x72: "falha geral de programação",
    0x78: "pedido recebido — resposta pendente",
    0x7E: "sub-função não suportada nesta sessão",
    0x7F: "serviço não suportado nesta sessão",
    0x81: "rotação demasiado alta",
    0x82: "rotação demasiado baixa",
    0x83: "o motor está a trabalhar",
    0x84: "o motor não está a trabalhar",
    0x88: "velocidade do veículo demasiado alta",
    0x92: "tensão demasiado alta",
    0x93: "tensão demasiado baixa",
}


def nrc_text(code):
    return NRC.get(code, f"código 0x{code:02X}")


class NegativeResponse(RequestRejected):
    """A centralina recusou o pedido (resposta 7F <serviço> <NRC>)."""

    def __init__(self, ecu, service, nrc):
        self.ecu, self.service, self.nrc = ecu, service, nrc
        super().__init__(f"A centralina {ecu} recusou o pedido 0x{service:02X}: {nrc_text(nrc)} (NRC 0x{nrc:02X})")


class Response:
    __slots__ = ("ecu", "data")

    def __init__(self, ecu, data):
        self.ecu = ecu                # identificador de quem respondeu: "7E8" (CAN 11 bits), "18DAF110", "10"…
        self.data = bytes(data)       # resposta completa, a começar no byte de serviço (+0x40) ou 0x7F

    @property
    def negative(self):
        return len(self.data) >= 3 and self.data[0] == 0x7F

    @property
    def nrc(self):
        return self.data[2] if self.negative else None

    def __repr__(self):
        return f"Response({self.ecu}, {self.data.hex(' ').upper()})"

    def __eq__(self, other):
        return isinstance(other, Response) and (self.ecu, self.data) == (other.ecu, other.data)


def positive(responses, service):
    """Só as respostas positivas a `service` (SID + 0x40)."""
    return [r for r in responses if r.data and r.data[0] == service + 0x40]


def raise_if_all_negative(responses, service):
    """Se nenhuma centralina respondeu positivamente e pelo menos uma recusou, levanta a recusa."""
    if positive(responses, service):
        return
    for r in responses:
        if r.negative and r.data[1] == service:
            raise NegativeResponse(r.ecu, service, r.nrc)
