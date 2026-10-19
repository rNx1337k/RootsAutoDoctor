"""Microcontrolador dos clones HEX-USB+CAN (FTDI 0403:FA24 + ATmega162).

Estes clones não ligam o chip FTDI directamente à linha K: há um microcontrolador pelo meio que, no modo de
origem ("inteligente"), só aceita pacotes próprios. Por isso o teste de eco KKL falha sempre, mesmo no carro
com a ignição ligada. O firmware também tem um modo de arranque "dumb" (KKL), mas no firmware 1.96 'F'
testado não dá passagem directa para a linha K.

Formato dos pacotes (engenharia inversa pública do VCDS, github.com/guns96x/vcds-android), confirmado no
cabo real a 19/10/2026:

    PC → cabo:  53 <comprimento> <opcode> <dados...> <xor>
    cabo → PC:  4D <comprimento> <opcode> <dados...> <xor>

O comprimento conta o pacote inteiro; o xor é o XOR de todos os bytes anteriores.

    02 versão              53 04 02 55        → 4D 07 02 <maior> <menor> <tipo> xx   (ex.: 01 60 'F' = 1.96)
    0D modo de arranque    53 04 0D 5A        → 4D 05 0D <modo> xx     (00 = KKL, 02 = inteligente)
    0E mudar o modo        53 05 0E <modo> xx → 4D 04 FE B7            (FE = ACK; fica gravado no cabo)
    82 teste da linha K    53 04 82 D5        → 4D 06 82 <K1> <K2> xx

A mudança de modo só é enviada quando o cabo já respondeu a um pedido de modo com um pacote válido.

O DTR do FTDI está ligado ao RESET do microcontrolador (DTR activo = reset): por isso o cabo HEX trabalha
com DTR e RTS desligados (HEX_LINES).
"""
import logging
import time

log = logging.getLogger(__name__)

HOST, DEV = 0x53, 0x4D
OP_VERSION, OP_READ_BOOT, OP_SET_BOOT, OP_ACK = 0x02, 0x0D, 0x0E, 0xFE
OP_KLINE_TEST = 0x82                               # teste da linha K feito pelo próprio cabo
MODE_DUMB, MODE_SMART = 0x00, 0x02
MODE_NAMES = {MODE_DUMB: "KKL (dumb)", MODE_SMART: "inteligente"}
HEX_LINES = (False, False)                 # (DTR, RTS): microcontrolador fora de reset
PROBE_BAUDS = (9600, 115200, 19200, 38400, 57600)
TYPE_NAMES = {"C": "CAN, 1 linha K", "D": "CAN + 2 linhas K (HEX-USB+CAN)", "F": "Fast-HEX"}


def is_hex_port(port):
    """Portas que são um clone HEX (chip FTDI com PID da Ross-Tech, sem porta COM)."""
    if not port:
        return False
    if port.startswith("D2XX:"):
        return True
    if port.startswith("FTDI:"):
        parts = port.split(":")
        return len(parts) >= 3 and parts[2].upper().startswith("FA2")
    return False


def xor(data):
    x = 0
    for b in data:
        x ^= b
    return x


def frame(opcode, payload=b"", marker=HOST):
    body = bytes([marker, 4 + len(payload), opcode]) + bytes(payload)
    return body + bytes([xor(body)])


def parse(data, marker=DEV):
    """Procura um pacote válido em data. Devolve (opcode, payload) ou None."""
    data = bytes(data)
    for i, b in enumerate(data):
        if b != marker or i + 1 >= len(data):
            continue
        n = data[i + 1]
        if n < 4 or i + n > len(data):
            continue
        pkt = data[i:i + n]
        if xor(pkt[:-1]) == pkt[-1]:
            return pkt[2], bytes(pkt[3:-1])
    return None


class HexMcuError(Exception):
    pass


class HexMcu:
    """Conversa com o microcontrolador por cima de um objecto tipo serial.Serial
    (D2xxSerial, FtdiSerial ou pyserial)."""

    def __init__(self, ser, log=None):
        self.ser = ser
        self.log = log or (lambda m: None)
        self.baud = None
        self.raw = []                       # [(baud, bytes)] — tudo o que veio, para o pacote de suporte

    # ------------------------------------------------------------ baixo nível
    def _lines(self, dtr, rts):
        for attr, val in (("dtr", dtr), ("rts", rts)):
            try:
                setattr(self.ser, attr, val)
            except Exception:
                log.warning("hexmcu: não foi possível definir %s", attr.upper(), exc_info=True)

    def reset(self, pulse=0.05, boot=0.4):
        """Reinicia o microcontrolador com um impulso no DTR e deixa-o arrancar."""
        self._lines(True, False)
        time.sleep(pulse)
        self._lines(*HEX_LINES)
        time.sleep(boot)

    def _purge(self):
        try:
            self.ser.reset_input_buffer()
        except Exception:
            log.warning("hexmcu: purge falhou", exc_info=True)

    def _collect(self, timeout):
        """Lê tudo o que chegar até haver um pacote completo ou passar o timeout."""
        got = bytearray()
        end = time.perf_counter() + timeout
        while time.perf_counter() < end:
            self.ser.timeout = max(0.005, min(0.05, end - time.perf_counter()))
            d = self.ser.read(1)
            if d:
                got += d
                if parse(got):
                    break
        return bytes(got)

    def transact(self, opcode, payload=b"", timeout=0.4):
        req = frame(opcode, payload)
        self._purge()
        self.ser.write(req)
        raw = self._collect(timeout)
        self.raw.append((self.baud, req, raw))
        self.log(f"    HEX › {req.hex(' ').upper()}   ‹ {raw.hex(' ').upper() or '(nada)'}")
        return parse(raw), raw

    # ------------------------------------------------------------ comandos
    def probe(self, bauds=PROBE_BAUDS, do_reset=True):
        """Procura o microcontrolador. Só leitura (versão + modo de arranque).

        Devolve {"found": bool, "baud", "version", "type", "mode", "mode_name", "raw": [...]}."""
        out = {"found": False, "baud": None, "version": None, "type": None, "mode": None,
               "mode_name": None, "raw": []}
        self._lines(*HEX_LINES)
        if do_reset:
            self.reset()
        for baud in bauds:
            try:
                self.ser.baudrate = baud
            except Exception as e:
                out["raw"].append(f"{baud}: velocidade recusada ({e})")
                continue
            self.baud = baud
            time.sleep(0.02)
            ans, raw = self.transact(OP_VERSION)
            out["raw"].append(f"{baud}: {raw.hex(' ').upper() or '—'}")
            if not ans:
                continue
            out["found"], out["baud"] = True, baud
            op, data = ans
            if op == OP_VERSION and len(data) >= 2:
                out["version"] = f"{data[0]}.{data[1]:02d}"
                if len(data) >= 3:
                    t = chr(data[2]) if 32 <= data[2] < 127 else f"0x{data[2]:02X}"
                    out["type"] = TYPE_NAMES.get(t, t)
            break
        if not out["found"]:
            return out
        mode = self.read_mode()
        out["mode"] = mode
        out["mode_name"] = MODE_NAMES.get(mode, None if mode is None else f"0x{mode:02X}")
        return out

    def read_mode(self):
        ans, _raw = self.transact(OP_READ_BOOT)
        if ans and ans[0] == OP_READ_BOOT and ans[1]:
            return ans[1][0]
        return None

    def set_mode(self, mode):
        """Muda o modo de arranque (o mesmo que a opção "Boot in Intelligent Mode" do VCDS).

        Só avança se o cabo responder a ReadBoot com um pacote válido. Devolve o modo lido depois."""
        before = self.read_mode()
        if before is None:
            raise HexMcuError("O cabo não respondeu ao pedido de modo (ReadBoot): não é seguro enviar a mudança")
        if before == mode:
            return mode
        ans, raw = self.transact(OP_SET_BOOT, bytes([mode]), timeout=1.0)
        if not ans or ans[0] != OP_ACK:
            raise HexMcuError(f"O cabo não confirmou a mudança de modo (resposta: {raw.hex(' ').upper() or 'nada'})")
        after = self.read_mode()
        if after != mode:
            raise HexMcuError(f"O cabo confirmou, mas o modo lido a seguir é "
                              f"{'—' if after is None else hex(after)}")
        return after


def kline_test(mcu):
    """HC::KLineTest (0x82): o cabo diz se vê tensão nas linhas K1/K2 (ignição). Só leitura.
    Devolve (k1, k2) ou None."""
    ans, _raw = mcu.transact(OP_KLINE_TEST, timeout=0.8)
    if ans and ans[0] == OP_KLINE_TEST and len(ans[1]) >= 2:
        return ans[1][0], ans[1][1]
    return None


def describe_kline(kt):
    """Valores em bruto do HC::KLineTest. O VCDS mostra três textos diferentes para 0/1/2; qual é qual ainda
    não está confirmado, por isso mostram-se os números."""
    return f"K1={kt[0]}, K2={kt[1]} (valores em bruto do cabo)"


def describe(res):
    """Texto curto para a UI a partir do resultado de probe()."""
    if not res.get("found"):
        return ("O microcontrolador do cabo HEX não respondeu (a " + ", ".join(str(b) for b in PROBE_BAUDS)
                + " baud). Respostas: " + "; ".join(res.get("raw", [])))
    txt = f"Microcontrolador do cabo encontrado a {res['baud']} baud"
    if res.get("version"):
        txt += f", firmware {res['version']}"
    if res.get("type"):
        txt += f" ({res['type']})"
    if res.get("mode_name"):
        txt += f"; modo de arranque: {res['mode_name']}"
    return txt
