"""Exceções comuns do Roots Auto Doctor."""


class ProtocolError(Exception):
    """Erro fatal de comunicação: a ligação ao controlador perdeu-se."""


class KLineError(ProtocolError):
    """Erro na camada física (porta série / linha K)."""


class InterfaceError(KLineError):
    """A própria interface falhou (porta fechada, cabo arrancado, ponte/driver bloqueado). Ao contrário de um
    controlador que não responde, não vale a pena continuar a tentar outros endereços."""


class KLineTimeout(KLineError):
    """O controlador não respondeu dentro do tempo."""


class ConnectError(ProtocolError):
    """Falhou o estabelecimento da ligação ao controlador."""


class NoResponse(ConnectError):
    """Nenhum controlador respondeu no endereço pedido."""


class RequestRejected(Exception):
    """O controlador recusou o pedido (NAK / resposta negativa). Não é fatal."""


class NotSupported(Exception):
    """Função não disponível para este protocolo/controlador. Não é fatal."""


class OperationUnconfirmed(RequestRejected):
    """O comando foi enviado ao controlador, mas não foi possível confirmar o resultado
    (ex.: apagar avarias e a releitura falhou). O estado real do controlador é desconhecido."""
