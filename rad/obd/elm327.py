"""Adaptador ELM327 (e compatíveis) — OBD-II/EOBD multimarca por porta série (USB, Bluetooth SPP).

Usa só os comandos AT documentados na folha de características pública do ELM327 (Elm Electronics). O ELM327
trata da camada física e do ISO-TP; este módulo envia pedidos em hexadecimal, lê as linhas até ao ">" e
devolve Response(ecu, dados) iguais às de qualquer outro link (ver link.py).

Os cabeçalhos ficam LIGADOS (ATH1) para se saber sempre que centralina respondeu. Em CAN, com os cabeçalhos
ligados, o ELM mostra as tramas tal como chegam (com o byte PCI do ISO-TP) e o programa remonta-as com o
isotp.Reassembler — não depende do formato "0: 1: 2:" que alguns clones implementam mal.

Separação de estados (o que cada passo prova):
  porta abriu                  → só que o Windows tem a porta (não que é um ELM327)
  o adaptador respondeu ao ATZ → é um ELM327/compatível e funciona
  0100 com resposta            → há comunicação com pelo menos uma centralina
Nenhum destes passos é dado como cumprido sem a resposta correspondente.

Clones: muitos clones dizem "v1.5" ou "v2.1" sem implementar todos os comandos. Comandos opcionais que
respondem "?" são registados e ignorados; os essenciais (E0, H1, SP) têm de responder "OK".
"""
import logging
import time

from ..errors import InterfaceError, KLineError, NoResponse, NotSupported, ProtocolError
from . import isotp
from .link import Response

log = logging.getLogger(__name__)

from ..kline import SIM_ELM_PORT as ELM_SIM_PORT  # noqa: E402  (uma só definição)
BAUDS = (38400, 9600, 115200, 57600, 230400)

PROTOCOLS = {
    "1": "SAE J1850 PWM (41,6 kbit/s)",
    "2": "SAE J1850 VPW (10,4 kbit/s)",
    "3": "ISO 9141-2 (linha K, init 5 baud)",
    "4": "ISO 14230-4 KWP2000 (linha K, init 5 baud)",
    "5": "ISO 14230-4 KWP2000 (linha K, init rápido)",
    "6": "ISO 15765-4 CAN (11 bits, 500 kbit/s)",
    "7": "ISO 15765-4 CAN (29 bits, 500 kbit/s)",
    "8": "ISO 15765-4 CAN (11 bits, 250 kbit/s)",
    "9": "ISO 15765-4 CAN (29 bits, 250 kbit/s)",
    "A": "SAE J1939 CAN (29 bits, 250 kbit/s)",
    "B": "CAN definido pelo utilizador 1",
    "C": "CAN definido pelo utilizador 2",
}
CAN_11 = {"6", "8"}
CAN_29 = {"7", "9"}
FUNCTIONAL_HEADER = {"1": "616AF1", "2": "686AF1", "3": "686AF1", "4": "C133F1", "5": "C133F1",
                     "6": "7DF", "8": "7DF", "7": "18DB33F1", "9": "18DB33F1"}

# Respostas de erro do ELM327 → (excepção, explicação para o utilizador)
ERRORS = {
    "UNABLE TO CONNECT": (NoResponse, "O adaptador não encontrou nenhum protocolo OBD-II: confirme que a ignição "
                                      "está ligada e que o veículo tem OBD-II/EOBD (gasolina ≥ 2001, gasóleo ≥ 2004 "
                                      "na UE). Centralinas VAG antigas só por KW1281 precisam de um cabo KKL."),
    "NO DATA": (NoResponse, "A centralina não respondeu a este pedido (NO DATA)."),
    "CAN ERROR": (NoResponse, "Erro no barramento CAN: sem actividade CAN na ficha, velocidade errada ou o "
                              "veículo não usa CAN neste protocolo."),
    "BUS ERROR": (NoResponse, "Erro no barramento (sinal inválido na ficha OBD): confirme o encaixe do cabo."),
    "BUS BUSY": (NoResponse, "Barramento ocupado: demasiada actividade ou interferência."),
    "FB ERROR": (NoResponse, "Erro de retorno do barramento (problema de cablagem ou do adaptador)."),
    "DATA ERROR": (ProtocolError, "Resposta com erro de dados (checksum/CRC inválido)."),
    "<DATA ERROR": (ProtocolError, "Resposta com erro de dados (checksum/CRC inválido)."),
    "BUFFER FULL": (ProtocolError, "O buffer do adaptador encheu: demasiados dados para a ligação série."),
    "STOPPED": (ProtocolError, "O adaptador interrompeu o pedido."),
    "LV RESET": (InterfaceError, "O adaptador reiniciou por tensão baixa na ficha OBD."),
    "ACT ALERT": (InterfaceError, "O adaptador entrou em poupança de energia por falta de actividade."),
    "?": (NotSupported, "O adaptador não reconheceu o comando."),
}


class AdapterNotResponding(InterfaceError):
    """A porta abriu, mas do outro lado não está um ELM327 a responder."""


def _open_serial(port, baud):
    if port == ELM_SIM_PORT:
        from .sim_elm import SimElm327Serial
        return SimElm327Serial()
    import serial
    return serial.Serial(port, baud, timeout=0.05, write_timeout=1.0)


class Elm327Link:
    is_can = False

    def __init__(self, port, log=None, raw_log=False, protocol="0", serial_factory=None,
                 timeout=4.0, search_timeout=20.0):
        self.port_name = port
        self.log = log or (lambda m: None)
        self.raw_log = raw_log
        self.protocol_setting = protocol          # "0" = automático; "1"…"9" = forçar
        self._factory = serial_factory or _open_serial
        self.timeout = timeout
        self.search_timeout = search_timeout
        self.ser = None
        self.baud = None
        self.version = None
        self.device = None
        self.voltage = None
        self.proto = None                          # número do protocolo ("6", …) depois de falar com o carro
        self.header = None
        self.cancelled = False
        self.warnings = []

    # ------------------------------------------------------------------ propriedades
    @property
    def is_open(self):
        return self.ser is not None

    @property
    def is_simulator(self):
        return self.port_name == ELM_SIM_PORT

    simulated = is_simulator

    @property
    def is_can(self):
        return self.proto in CAN_11 or self.proto in CAN_29

    @property
    def protocol(self):
        return PROTOCOLS.get(self.proto, "por determinar") if self.proto else "por determinar"

    def describe(self):
        return {"adapter": "ELM327", "port": self.port_name, "version": self.version, "device": self.device,
                "baud": self.baud, "protocol": self.protocol, "protocol_number": self.proto,
                "voltage": self.voltage, "simulated": self.is_simulator, "warnings": list(self.warnings)}

    # ------------------------------------------------------------------ série
    def _write(self, text):
        if self.raw_log:
            self.log(f"    › {text}")
        try:
            self.ser.write((text + "\r").encode("ascii"))
        except Exception as e:
            raise InterfaceError(f"Erro de escrita na porta {self.port_name}: {e}") from e

    def _read_until_prompt(self, timeout):
        """Lê até ao ">" do ELM327. Devolve o texto (sem o ">") ou None se o tempo acabar."""
        buf = bytearray()
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.cancelled:
                raise ProtocolError("Operação cancelada")
            try:
                chunk = self.ser.read(256)
            except Exception as e:
                raise InterfaceError(f"Erro de leitura na porta {self.port_name}: {e}") from e
            if chunk:
                buf += chunk
                if b">" in buf:
                    text = buf[:buf.rindex(b">")].replace(b"\x00", b"").decode("ascii", "replace")
                    if self.raw_log:
                        self.log("    ‹ " + " | ".join(l for l in text.replace("\n", "\r").split("\r") if l.strip()))
                    return text
        if buf and self.raw_log:
            self.log("    ‹ (sem prompt) " + buf.decode("ascii", "replace").strip())
        return None

    def _command(self, cmd, timeout=None):
        """Envia um comando e devolve as linhas da resposta (sem o eco). InterfaceError se o adaptador não
        devolver o prompt."""
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass
        self._write(cmd)
        text = self._read_until_prompt(timeout or self.timeout)
        if text is None:
            raise InterfaceError(f"O adaptador deixou de responder (sem resposta a {cmd!r} na porta {self.port_name})")
        lines = [l.strip() for l in text.replace("\n", "\r").split("\r")]
        return [l for l in lines if l and l.replace(" ", "").upper() != cmd.replace(" ", "").upper()]

    def _at(self, cmd, required=True):
        lines = self._command(cmd)
        if lines and lines[-1].upper() == "OK":
            return lines
        if lines and lines[-1] == "?":
            msg = f"O adaptador não suporta o comando {cmd}"
            if required:
                raise NotSupported(msg + " — não é um ELM327 compatível.")
            self.warnings.append(msg)
            self.log(f"ELM327: {msg} (ignorado)")
            return lines
        return lines

    # ------------------------------------------------------------------ abrir / identificar
    def open(self):
        """Abre a porta e identifica o adaptador. Não fala com o carro (isso é connect_vehicle)."""
        if self.ser is not None:
            return self.describe()
        tried = []
        last_err = None
        for baud in BAUDS:
            try:
                self.ser = self._factory(self.port_name, baud)
            except Exception as e:
                last_err = e
                if baud == BAUDS[0]:
                    raise KLineError(f"Não foi possível abrir a porta {self.port_name}: {e}") from e
                continue
            tried.append(baud)
            try:
                self.ser.baudrate = baud
            except Exception:
                pass
            self.baud = baud
            if self._probe():
                break
            self.ser.close()
            self.ser = None
            if self.is_simulator:
                break
        if self.ser is None:
            raise AdapterNotResponding(
                f"A porta {self.port_name} abriu, mas nenhum adaptador ELM327 respondeu "
                f"(velocidades tentadas: {', '.join(map(str, tried)) or '—'}). Confirme que é um ELM327, "
                "que o Bluetooth está emparelhado e que nenhum outro programa está a usar a porta."
                + (f" Detalhe: {last_err}" if last_err else ""))
        self._init_adapter()
        return self.describe()

    def _probe(self):
        """True se um ELM327 responder nesta velocidade."""
        try:
            self.ser.write(b"\r")
            self._read_until_prompt(0.4)
            self._write("ATI")
            text = self._read_until_prompt(1.0)
        except Exception:
            return False
        return bool(text) and "ELM" in text.upper()

    def _init_adapter(self):
        lines = self._command("ATZ", timeout=3.0)
        ident = next((l for l in lines if "ELM" in l.upper()), None)
        if ident is None:
            lines = self._command("ATI")
            ident = next((l for l in lines if "ELM" in l.upper()), None)
        if ident is None:
            raise AdapterNotResponding(f"O dispositivo na porta {self.port_name} não se identificou como ELM327.")
        self.version = ident.strip()
        self._at("ATE0")
        self._at("ATL0", required=False)
        self._at("ATS1", required=False)
        self._at("ATH1")
        self._at("ATAT1", required=False)
        try:
            dev = self._command("AT@1")
            self.device = dev[0] if dev and dev[0] != "?" else None
        except InterfaceError:
            raise
        except Exception:
            self.device = None
        self.voltage = self.read_voltage()
        self._at(f"ATSP{self.protocol_setting}")
        self.log(f"ELM327: {self.version} a {self.baud} baud"
                 + (f", tensão na ficha {self.voltage:.1f} V" if self.voltage is not None else ""))

    def read_voltage(self):
        """Tensão medida pelo adaptador no pino 16 da ficha OBD (V) ou None."""
        try:
            lines = self._command("ATRV")
        except InterfaceError:
            raise
        except Exception:
            return None
        for l in lines:
            t = l.upper().rstrip("V").strip()
            try:
                return float(t)
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------------ veículo
    def connect_vehicle(self):
        """Primeiro contacto com o veículo (0100, com procura automática do protocolo). Devolve as respostas.
        NoResponse se o carro não responder; InterfaceError se o adaptador falhar."""
        lines = self._command("0100", timeout=self.search_timeout)
        self._raise_errors(lines, "0100")
        dpn = self._command("ATDPN")
        num = (dpn[0] if dpn else "").strip().upper()
        if len(num) == 2 and num[0] == "A":          # "A6" = escolhido pela procura automática
            num = num[1]
        if num not in PROTOCOLS:
            raise ProtocolError(f"O adaptador indicou um protocolo desconhecido: {dpn!r}")
        self.proto = num
        self.header = None
        if num == "A":
            raise NotSupported("O veículo respondeu em SAE J1939 (pesados): não suportado nesta versão.")
        resp = self._parse(lines)
        if not resp:
            raise NoResponse("O adaptador indicou um protocolo, mas nenhuma centralina deu uma resposta válida.")
        self.log(f"ELM327: protocolo {self.protocol}")
        return resp

    def _raise_errors(self, lines, cmd):
        has_data = any(self._looks_like_data(l) for l in lines)
        for l in lines:
            key = l.upper().strip()
            if key.startswith("BUS INIT") and "ERROR" in key:
                raise NoResponse("A inicialização da linha K falhou (BUS INIT: ERROR): ignição desligada, "
                                 "centralina sem OBD-II na linha K, ou protocolo errado.")
            for k, (exc, text) in ERRORS.items():
                if key == k or (k != "?" and key.startswith(k)):
                    if exc is NoResponse and has_data:
                        continue                     # outra centralina respondeu
                    raise exc(f"{text} [{cmd}]")

    @staticmethod
    def _looks_like_data(line):
        t = line.replace(" ", "")
        return len(t) >= 4 and all(c in "0123456789ABCDEFabcdef" for c in t)

    def _set_header(self, target):
        want = target or FUNCTIONAL_HEADER.get(self.proto)
        if want and want != self.header:
            self._at(f"ATSH{want}")
            self.header = want

    def request(self, payload, target=None, timeout=None):
        if self.proto is None:
            raise ProtocolError("Ainda não há protocolo com o veículo (ligue primeiro)")
        if target is not None and not self.is_can:
            raise NotSupported("Pedidos dirigidos a uma centralina só estão disponíveis em CAN nesta versão")
        self._set_header(target)
        cmd = bytes(payload).hex().upper()
        for attempt in range(4):
            lines = self._command(cmd, timeout=timeout or self.timeout)
            self._raise_errors(lines, cmd)
            resp = self._parse(lines)
            pending = [r for r in resp if r.negative and r.nrc == 0x78]
            final = [r for r in resp if not (r.negative and r.nrc == 0x78)]
            if final or not pending:
                break
            self.log(f"ELM327: {pending[0].ecu} pediu para esperar (resposta pendente) — a repetir o pedido")
            time.sleep(0.2)
        if not final:
            raise NoResponse(f"Sem resposta válida ao pedido {cmd}")
        return final

    def _parse(self, lines):
        """Linhas de dados (cabeçalhos ligados) → [Response], remontando o ISO-TP em CAN."""
        out = []
        asm = {}
        for l in lines:
            if not self._looks_like_data(l):
                continue
            t = l.replace(" ", "").upper()
            try:
                if self.proto in CAN_11:
                    ecu, raw = t[:3], bytes.fromhex(t[3:])
                elif self.proto in CAN_29:
                    ecu, raw = t[:8], bytes.fromhex(t[8:])
                else:
                    b = bytes.fromhex(t)
                    hlen = 4 if (b[0] & 0x80 and (b[0] & 0x3F) == 0 and self.proto in ("4", "5")) else 3
                    if len(b) < hlen + 2:
                        continue
                    ecu, data, cs = f"{b[2]:02X}", b[hlen:-1], b[-1]
                    if self.proto in ("3", "4", "5") and (sum(b[:-1]) & 0xFF) != cs:
                        self.log(f"ELM327: checksum inválido ignorado: {l}")
                        continue
                    out.append(Response(ecu, data))
                    continue
            except ValueError:
                self.log(f"ELM327: linha ignorada (não é hexadecimal válido): {l}")
                continue
            if not raw:
                continue
            a = asm.setdefault(ecu, isotp.Reassembler())
            try:
                msg = a.feed(raw)
            except isotp.IsoTpError as e:
                self.log(f"ELM327: {ecu}: {e} ({l})")
                continue
            if msg is not None:
                out.append(Response(ecu, msg))
        for ecu, a in asm.items():
            if a.in_progress:
                self.log(f"ELM327: resposta multi-trama de {ecu} incompleta")
        return out

    # ------------------------------------------------------------------ fechar
    def close(self):
        if self.ser is not None:
            try:
                if self.proto is not None:
                    self._write("ATPC")              # fecha o protocolo (o adaptador deixa de manter a sessão)
                    self._read_until_prompt(0.5)
            except Exception:
                pass
            try:
                self.ser.close()
            except Exception:
                log.warning("%s: erro ao fechar a porta", self.port_name, exc_info=True)
        self.ser = None
        self.proto = None
        self.header = None

    def kill(self):
        """Fecho forçado (chamado de outra thread quando a comunicação fica bloqueada)."""
        self.cancelled = True
        try:
            if self.ser is not None:
                self.ser.close()
        except Exception:
            pass
