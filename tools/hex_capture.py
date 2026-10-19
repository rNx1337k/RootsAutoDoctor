"""Análise de capturas USB (Wireshark + USBPcap) de interfaces com chip FTDI — ver docs/HEX_USB.md.

    .venv\\Scripts\\python.exe tools\\hex_capture.py captura_hex.pcapng
    .venv\\Scripts\\python.exe tools\\hex_capture.py captura_hex.pcapng --device 1.5 -o analise.txt

Lê o ficheiro (.pcapng ou .pcap, tipo de ligação USBPcap), fica só com o dispositivo FTDI, tira os 2 bytes de
estado que o chip põe no início de cada pacote de 64 bytes e mostra, por ordem e com o tempo:

  - os pedidos de controlo do FTDI: velocidade, DTR/RTS, BREAK, latência, purge;
  - os bytes PC → cabo e cabo → PC, agrupados nos pacotes 53/4D do microcontrolador dos clones HEX quando os
    houver (com o nome do comando, se for conhecido), ou em bruto (cabo KKL, modo directo).

No fim lista os opcodes vistos e quantas vezes, separando os que o Roots Auto Doctor já conhece dos que faltam.
Só usa a biblioteca padrão e nunca escreve nada no dispositivo.
"""
import argparse
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import hexmcu                                     # noqa: E402

LINKTYPE_USBPCAP = 249
FTDI_VID = 0x0403
FTDI_PACKET = 64                                           # tamanho de pacote bulk do FT232R (full speed)

URB_ISO, URB_INTERRUPT, URB_CONTROL, URB_BULK = 0, 1, 2, 3

# Opcodes do microcontrolador HEX (rad/hexmcu.py + engenharia inversa pública; "?" = por confirmar)
OPCODES = {
    0x02: "versão",
    0x03: "velocidade PC↔cabo (?)",
    0x08: "reset do cabo (?)",
    0x0B: "leitura de bloco interno (?)",
    0x0D: "modo de arranque",
    0x0E: "mudar modo de arranque",
    0x16: "GC (?)",
    0x17: "GCr (?)",
    0x18: "SCr (?)",
    0x19: "GC CAN (?)",
    0x82: "teste da linha K",
    0x84: "init 5 baud pelo cabo (?)",
    0x85: "turbo baud (?)",
    0x9A: "eco 10400 (?)",
    0xB3: "máscara CAN (?)",
    0xB4: "filtro CAN (?)",
    0xFD: "pronto",
    0xFE: "ACK",
    0xFF: "erro",
}
KNOWN = {hexmcu.OP_VERSION, hexmcu.OP_READ_BOOT, hexmcu.OP_SET_BOOT, hexmcu.OP_KLINE_TEST, hexmcu.OP_ACK}

# Pedidos de fabricante do FTDI (bmRequestType 0x40)
FTDI_RESET, FTDI_MODEM, FTDI_FLOW, FTDI_BAUD, FTDI_DATA, FTDI_LATENCY = 0x00, 0x01, 0x02, 0x03, 0x04, 0x09
FRACTION = {0: 0, 1: 0.5, 2: 0.25, 3: 0.125, 4: 0.375, 5: 0.625, 6: 0.75, 7: 0.875}


# ---------------------------------------------------------------- ficheiro
class CaptureError(Exception):
    pass


def read_packets(path):
    """[(tempo em s, bytes do pacote)] de um .pcapng ou .pcap com ligação USBPcap."""
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 24:
        raise CaptureError("Ficheiro demasiado pequeno para ser uma captura")
    if data[:4] == b"\x0a\x0d\x0d\x0a":
        return _read_pcapng(data)
    return _read_pcap(data)


def _read_pcap(data):
    magic = data[:4]
    formats = {b"\xd4\xc3\xb2\xa1": ("<", 1e-6), b"\xa1\xb2\xc3\xd4": (">", 1e-6),
               b"\x4d\x3c\xb2\xa1": ("<", 1e-9), b"\xa1\xb2\x3c\x4d": (">", 1e-9)}
    if magic not in formats:
        raise CaptureError("Formato desconhecido: guarde a captura como .pcapng ou .pcap no Wireshark")
    e, unit = formats[magic]
    linktype = struct.unpack(e + "I", data[20:24])[0]
    if linktype != LINKTYPE_USBPCAP:
        raise CaptureError(f"A captura não é USBPcap (tipo de ligação {linktype})")
    out, pos = [], 24
    while pos + 16 <= len(data):
        sec, frac, incl, _orig = struct.unpack(e + "IIII", data[pos:pos + 16])
        pos += 16
        out.append((sec + frac * unit, data[pos:pos + incl]))
        pos += incl
    return out


def _read_pcapng(data):
    out, interfaces, pos, e = [], [], 0, "<"
    while pos + 12 <= len(data):
        btype = struct.unpack(e + "I", data[pos:pos + 4])[0]
        if btype == 0x0A0D0D0A:                               # Section Header: define a ordem dos bytes
            e = "<" if data[pos + 8:pos + 12] == b"\x4d\x3c\x2b\x1a" else ">"
            interfaces = []
        blen = struct.unpack(e + "I", data[pos + 4:pos + 8])[0]
        if blen < 12 or pos + blen > len(data):
            break
        body = data[pos + 8:pos + blen - 4]
        if btype == 0x00000001:                               # Interface Description
            linktype = struct.unpack(e + "H", body[:2])[0]
            interfaces.append({"linktype": linktype, "unit": _ts_unit(body[8:], e)})
        elif btype == 0x00000006:                             # Enhanced Packet
            iface, hi, lo, cap = struct.unpack(e + "IIII", body[:16])
            if iface < len(interfaces) and interfaces[iface]["linktype"] == LINKTYPE_USBPCAP:
                out.append((((hi << 32) | lo) * interfaces[iface]["unit"], body[20:20 + cap]))
        pos += blen
    if not interfaces:
        raise CaptureError("Ficheiro .pcapng sem interfaces")
    if all(i["linktype"] != LINKTYPE_USBPCAP for i in interfaces):
        raise CaptureError("A captura não tem nenhuma interface USBPcap")
    return out


def _ts_unit(opts, e):
    """Resolução do tempo (opção if_tsresol); por omissão microssegundos."""
    pos = 0
    while pos + 4 <= len(opts):
        code, length = struct.unpack(e + "HH", opts[pos:pos + 4])
        if code == 0:
            break
        if code == 9 and length >= 1:
            v = opts[pos + 4]
            return 2.0 ** -(v & 0x7F) if v & 0x80 else 10.0 ** -v
        pos += 4 + ((length + 3) & ~3)
    return 1e-6


# ---------------------------------------------------------------- USBPcap
def parse_usbpcap(pkt):
    """Cabeçalho USBPcap → dict, ou None se o pacote não for válido."""
    if len(pkt) < 27:
        return None
    hlen, _irp, status, _fn, info, bus, dev, ep, xfer, dlen = struct.unpack("<HQIHBHHBBI", pkt[:27])
    if hlen < 27 or hlen > len(pkt):
        return None
    r = {"bus": bus, "dev": dev, "ep": ep, "transfer": xfer, "status": status,
         "completion": bool(info & 1), "data": pkt[hlen:hlen + dlen], "stage": None}
    if xfer == URB_CONTROL and hlen >= 28:
        r["stage"] = pkt[27]                                   # 0 setup, 1 data, 2 status, 3 complete
    return r


def strip_ftdi_status(data):
    """Bulk IN do FTDI: cada pacote de 64 bytes começa com 2 bytes de estado da linha."""
    out = bytearray()
    for i in range(0, len(data), FTDI_PACKET):
        out += data[i + 2:i + FTDI_PACKET]
    return bytes(out)


def ftdi_baud(value, index):
    """Velocidade a partir do divisor do FT232R/FT232BM (wValue, wIndex)."""
    div = value & 0x3FFF
    frac = FRACTION[((value >> 14) & 3) | ((index & 1) << 2)]
    if div == 0 and frac == 0:
        return 3000000
    if div == 1 and frac == 0:
        return 2000000
    return round(3000000 / (div + frac))


def describe_control(setup):
    """Texto para um pedido de controlo do FTDI (pacote SETUP de 8 bytes), ou None se não for do FTDI."""
    if len(setup) < 8:
        return None
    rtype, req, value, index, _length = struct.unpack("<BBHHH", setup[:8])
    if rtype != 0x40:
        return None
    if req == FTDI_RESET:
        return {0: "FTDI reset", 1: "FTDI purge RX", 2: "FTDI purge TX"}.get(value, f"FTDI reset {value}")
    if req == FTDI_MODEM:
        parts = []
        if value & 0x0100:
            parts.append("DTR " + ("on" if value & 1 else "off"))
        if value & 0x0200:
            parts.append("RTS " + ("on" if value & 2 else "off"))
        return "FTDI " + (", ".join(parts) or f"modem {value:#06x}")
    if req == FTDI_FLOW:
        return f"FTDI controlo de fluxo {index >> 8:#04x}"
    if req == FTDI_BAUD:
        return f"FTDI velocidade {ftdi_baud(value, index)} baud"
    if req == FTDI_DATA:
        brk = " BREAK on" if value & 0x4000 else " BREAK off"
        return f"FTDI {value & 0xFF} bits, paridade {(value >> 8) & 7}, stop {(value >> 11) & 3}{brk}"
    if req == FTDI_LATENCY:
        return f"FTDI latência {value & 0xFF} ms"
    return f"FTDI pedido {req:#04x} valor {value:#06x} índice {index:#06x}"


# ---------------------------------------------------------------- análise
def find_devices(records):
    """{(bus, dev): pontuação}: pedidos de controlo do FTDI e pacotes 53/4D contam a favor."""
    score = Counter()
    for _t, r in records:
        key = (r["bus"], r["dev"])
        if r["transfer"] == URB_CONTROL and r["stage"] == 0 and describe_control(r["data"]):
            score[key] += 1
        elif r["transfer"] == URB_BULK and r["data"]:
            data = r["data"] if not r["ep"] & 0x80 else strip_ftdi_status(r["data"])
            if hexmcu.parse(data, marker=hexmcu.HOST) or hexmcu.parse(data, marker=hexmcu.DEV):
                score[key] += 5
    return score


def events(records, device):
    """Eventos do dispositivo por ordem: (tempo, "ctl" | "out" | "in", texto ou bytes)."""
    out = []
    for t, r in records:
        if (r["bus"], r["dev"]) != device:
            continue
        if r["transfer"] == URB_CONTROL and r["stage"] == 0 and not r["completion"]:
            txt = describe_control(r["data"])
            if txt:
                out.append((t, "ctl", txt))
        elif r["transfer"] == URB_BULK:
            if r["ep"] & 0x80 and r["completion"]:
                data = strip_ftdi_status(r["data"])
                if data:
                    out.append((t, "in", data))
            elif not r["ep"] & 0x80 and not r["completion"] and r["data"]:
                out.append((t, "out", bytes(r["data"])))
    return out


def split_frames(buf, marker):
    """Separa os pacotes 53/4D de um fluxo de bytes. Devolve (pacotes, bytes soltos, resto incompleto)."""
    frames, loose, i = [], bytearray(), 0
    while i < len(buf):
        if buf[i] == marker and i + 1 < len(buf):
            n = buf[i + 1]
            if n >= 4:
                if i + n > len(buf):
                    break                                       # pacote ainda incompleto
                pkt = bytes(buf[i:i + n])
                if hexmcu.xor(pkt[:-1]) == pkt[-1]:
                    frames.append(pkt)
                    i += n
                    continue
        elif buf[i] == marker:
            break
        loose.append(buf[i])
        i += 1
    return frames, bytes(loose), bytes(buf[i:])


def frame_text(pkt):
    op = pkt[2]
    name = OPCODES.get(op, "desconhecido")
    return f"{pkt.hex(' ').upper():<40} {op:02X} {name}"


def analyse(path, device=None):
    """Devolve (linhas de texto, Counter de opcodes {(direcção, opcode): n})."""
    records = []
    for t, pkt in read_packets(path):
        r = parse_usbpcap(pkt)
        if r is not None:
            records.append((t, r))
    if not records:
        raise CaptureError("A captura não tem pacotes USB")
    scores = find_devices(records)
    if device is None:
        if not scores:
            raise CaptureError("Não foi encontrado nenhum dispositivo FTDI na captura. Confirme que gravou a "
                               "interface USBPcap onde o cabo está ligado")
        device = scores.most_common(1)[0][0]
    t0 = records[0][0]
    lines = [f"Dispositivo {device[0]}.{device[1]}"
             + (f" (outros candidatos: {', '.join(f'{b}.{d}' for (b, d) in scores if (b, d) != device)})"
                if len(scores) > 1 else ""), ""]
    ops = Counter()
    buffers = {"out": bytearray(), "in": bytearray()}
    for t, kind, payload in events(records, device):
        stamp = f"{t - t0:10.3f}"
        if kind == "ctl":
            lines.append(f"{stamp}  ----        {payload}")
            continue
        arrow = "PC → cabo" if kind == "out" else "cabo → PC"
        marker = hexmcu.HOST if kind == "out" else hexmcu.DEV
        buffers[kind] += payload
        frames, loose, rest = split_frames(buffers[kind], marker)
        buffers[kind] = bytearray(rest)
        for pkt in frames:
            ops[(kind, pkt[2])] += 1
            lines.append(f"{stamp}  {arrow}  {frame_text(pkt)}")
        if loose:
            lines.append(f"{stamp}  {arrow}  {loose.hex(' ').upper()}   (bytes sem pacote)")
    for kind, rest in buffers.items():
        if rest:
            lines.append(f"{'fim':>10}  {'PC → cabo' if kind == 'out' else 'cabo → PC'}  "
                         f"{bytes(rest).hex(' ').upper()}   (incompleto)")
    return lines, ops


def summary(ops):
    if not ops:
        return ["Nenhum pacote 53/4D: o cabo esteve em modo directo (KKL) ou não é um clone HEX."]
    out = ["Opcodes vistos (direcção, opcode, nome, vezes):"]
    for (kind, op), n in sorted(ops.items(), key=lambda x: (x[0][1], x[0][0])):
        tag = "conhecido" if op in KNOWN else "POR IMPLEMENTAR"
        out.append(f"  {'PC → cabo' if kind == 'out' else 'cabo → PC'}  {op:02X}  "
                   f"{OPCODES.get(op, 'desconhecido'):<30} {n:5}  {tag}")
    return out


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("captura", help="ficheiro .pcapng ou .pcap gravado com USBPcap")
    ap.add_argument("--device", help="dispositivo bus.endereço (por omissão: o FTDI encontrado)")
    ap.add_argument("-o", "--output", help="guardar a análise neste ficheiro de texto")
    args = ap.parse_args(argv)
    device = None
    if args.device:
        try:
            bus, dev = (int(x) for x in args.device.split("."))
            device = (bus, dev)
        except ValueError:
            ap.error("--device tem de ser bus.endereço, ex.: 1.5")
    try:
        lines, ops = analyse(args.captura, device)
    except (OSError, CaptureError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    text = "\n".join(lines + [""] + summary(ops)) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Análise guardada em {args.output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
