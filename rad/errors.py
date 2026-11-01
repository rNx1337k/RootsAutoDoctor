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


# ------------------------------------------------------------------ mensagens para o cliente
# As camadas de comunicação descrevem os erros com o detalhe técnico (protocolo, bytes, ponte, driver…), que é o
# que interessa ao suporte e fica no registo. O cliente vê uma explicação de oficina: o que aconteceu e o que fazer.
import logging as _logging  # noqa: E402  (secção à parte, ver comentário acima)
import re as _re  # noqa: E402  (secção à parte, ver comentário acima)

_log = _logging.getLogger(__name__)

_TECHNICAL = _re.compile(
    r"KW1281|KWP|J2534|ELM\s?327|\bELM\b|\bISO\b|ISO[ -]?\d|\bSAE\b|\bCAN\b|\bUDS\b|ISO-TP|\bNRC\b|0x[0-9A-Fa-f]"
    r"|[Cc]hecksum|\bbytes?\b|\bblocos?\b|\bblocks?\b|[Pp]onte\b|[Bb]ridge\b|[Dd]river|D2XX|FTDI|WinUSB|Zadig"
    r"|pyftdi|pyusb|libusb|pip install|\bDLL\b|\.DLL|\.dll|[Tt]imeout|\bbaud\b|[Kk]eyword|PassThru|\b[Ee]co\b"
    r"|\b[Ee]cho\b|[Ll]inha K|K-line|\bKB2\b|\binit\b|\bPID\b|\bVID\b|S/N|runtime|\d+ bits|Errno|WinError|OSError"
    r"|Traceback|Serial|microcontrol|firmware|\bKKL\b|\bHEX\b|\bPCI\b|\bDID\b|First Frame|Single Frame|\bNAK\b"
    r"|complemento|[Cc]olisão|[Cc]ollision|\bkeep-alive\b|\bRT-USB\b|\bJ1850\b|\bJ1939\b|BUS INIT")


def is_technical(text):
    """True se o texto tem termos técnicos (protocolos, bytes, drivers…) que o cliente não precisa de ver."""
    return bool(text) and bool(_TECHNICAL.search(str(text)))


def client_text(msg, technical=None):
    """Devolve a mensagem própria para o cliente. Se já está em linguagem de oficina, fica igual; se tem detalhe
    técnico, é substituída por uma explicação simples (o original vai para o registo). No modo técnico
    (--tecnico) devolve sempre o original."""
    from . import technician_mode
    from .i18n import tr
    text = "" if msg is None else str(msg)
    if not text or not _TECHNICAL.search(text):
        return text
    if technician_mode() if technical is None else technical:
        return text
    _log.info("Mensagem técnica simplificada para o cliente: %s", text)
    low = text.lower()
    if any(k in low for k in ("eco", "echo", "linha k", "k-line", "bus init", "kkl", "microcontrol")):
        return tr("O cabo não está a comunicar com o carro. Confirme que está bem encaixado na ficha de "
                  "diagnóstico e que a ignição está ligada, e tente de novo.")
    if "outro programa" in low or "another program" in low:
        return tr("O cabo está a ser usado por outro programa. Feche os outros programas de diagnóstico e tente "
                  "de novo.")
    if any(k in low for k in ("ponte", "bridge", "driver", "dll", "d2xx", "ftdi", "winusb", "usb", "porta",
                              "port", "serial", "errno", "winerror", "oserror", "runtime", "bits", "libusb",
                              "pyftdi", "pyusb", "pip install", "elm")):
        return tr("O cabo deixou de responder ou não está disponível. Desligue o cabo do USB, volte a ligá-lo "
                  "e tente de novo. Se continuar, crie um Pacote de suporte em Opções e envie-o.")
    if any(k in low for k in ("não respond", "timeout", "sem resposta", "tempo esgotado", "did not answer",
                              "no response", "not respond")):
        return tr("O módulo não respondeu. Confirme que a ignição está ligada e tente de novo.")
    if any(k in low for k in ("recus", "nak", "nrc", "rejected", "refused")):
        return tr("O módulo recusou o pedido.")
    if any(k in low for k in ("não disponível", "ainda não", "não suportad", "not available", "not supported")):
        return tr("Esta função ainda não está disponível para este módulo.")
    return tr("Houve um erro na comunicação com o veículo. Tente de novo; se continuar, crie um Pacote de "
              "suporte em Opções e envie-o.")
