"""tools/hex_capture.py com capturas USBPcap sintéticas (.pcapng e .pcap), sem Wireshark."""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

import hex_capture                                          # noqa: E402
from rad import hexmcu                                      # noqa: E402

CABLE = (1, 5)
MOUSE = (1, 2)


def usbpcap(dev, ep, xfer, data=b"", completion=False, stage=None):
    hlen = 28 if stage is not None else 27
    hdr = struct.pack("<HQIHBHHBBI", hlen, 0, 0, 0, 1 if completion else 0, dev[0], dev[1], ep, xfer, len(data))
    if stage is not None:
        hdr += bytes([stage])
    return hdr + data


def setup(req, value, index=0):
    return usbpcap(CABLE, 0x00, hex_capture.URB_CONTROL, struct.pack("<BBHHH", 0x40, req, value, index, 0), stage=0)


def bulk_out(data):
    return usbpcap(CABLE, 0x02, hex_capture.URB_BULK, data)


def bulk_in(data, dev=CABLE):
    out = bytearray()
    for i in range(0, max(len(data), 1), 62):                # 2 bytes de estado por pacote de 64
        out += b"\x01\x60" + data[i:i + 62]
    return usbpcap(dev, 0x81, hex_capture.URB_BULK, bytes(out), completion=True)


def session():
    """Sessão parecida com a do cabo real: velocidade, DTR/RTS, versão, modo e um pedido desconhecido."""
    ver = hexmcu.frame(hexmcu.OP_VERSION)
    ver_ans = hexmcu.frame(hexmcu.OP_VERSION, bytes([1, 96, ord("F")]), marker=hexmcu.DEV)
    mode = hexmcu.frame(hexmcu.OP_READ_BOOT)
    mode_ans = hexmcu.frame(hexmcu.OP_READ_BOOT, b"\x02", marker=hexmcu.DEV)
    init = hexmcu.frame(0x84, bytes([0x01, 0x07, 0x03]))
    init_ans = hexmcu.frame(0x84, bytes([0x28, 0xA0, 0x01, 0x8A, 0x55, 0x00]), marker=hexmcu.DEV)
    return [
        (0.000, setup(hex_capture.FTDI_BAUD, 0x001A)),                   # 3 MHz / 26 = 115384 baud
        (0.001, setup(hex_capture.FTDI_MODEM, 0x0300)),                  # DTR off, RTS off
        (0.002, setup(hex_capture.FTDI_LATENCY, 1)),
        (0.010, bulk_out(ver)),
        (0.020, bulk_in(ver_ans[:3])),                                   # resposta partida em dois pacotes USB
        (0.021, bulk_in(ver_ans[3:])),
        (0.030, bulk_in(b"", dev=MOUSE)),                                # outro dispositivo, ignorado
        (0.040, bulk_out(mode)),
        (0.050, bulk_in(mode_ans)),
        (1.000, bulk_out(init)),
        (3.200, bulk_in(init_ans)),
        (3.300, setup(hex_capture.FTDI_DATA, 0x4008)),                   # 8 bits, BREAK on
    ]


def write_pcapng(packets):
    def block(btype, body):
        body += b"\x00" * (-len(body) % 4)
        n = len(body) + 12
        return struct.pack("<II", btype, n) + body + struct.pack("<I", n)
    out = block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))
    out += block(0x00000001, struct.pack("<HHI", hex_capture.LINKTYPE_USBPCAP, 0, 65535))
    for t, pkt in packets:
        ts = int(t * 1e6)
        out += block(0x00000006, struct.pack("<IIIII", 0, ts >> 32, ts & 0xFFFFFFFF, len(pkt), len(pkt)) + pkt)
    return _tmp(out, ".pcapng")


def write_pcap(packets):
    out = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, hex_capture.LINKTYPE_USBPCAP)
    for t, pkt in packets:
        out += struct.pack("<IIII", int(t), int((t % 1) * 1e6), len(pkt), len(pkt)) + pkt
    return _tmp(out, ".pcap")


def _tmp(data, suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return path


def test_ftdi_baud_divisors():
    assert hex_capture.ftdi_baud(0x001A, 0) == 115385
    assert hex_capture.ftdi_baud(0x4138, 0) == 9600          # 312.5
    assert hex_capture.ftdi_baud(0x0120, 0) == 10417         # 288 (10400 com o divisor mais próximo)
    assert hex_capture.ftdi_baud(0, 0) == 3000000


def test_control_requests():
    def txt(req, value, index=0):
        return hex_capture.describe_control(struct.pack("<BBHHH", 0x40, req, value, index, 0))
    assert txt(hex_capture.FTDI_MODEM, 0x0301) == "FTDI DTR on, RTS off"
    assert txt(hex_capture.FTDI_DATA, 0x4008).endswith("BREAK on")
    assert txt(hex_capture.FTDI_RESET, 1) == "FTDI purge RX"
    assert hex_capture.describe_control(struct.pack("<BBHHH", 0x80, 6, 0x100, 0, 18)) is None   # pedido padrão


def test_split_frames_keeps_incomplete_tail():
    ack = hexmcu.frame(hexmcu.OP_ACK, marker=hexmcu.DEV)
    frames, loose, rest = hex_capture.split_frames(b"\x00" + ack + ack[:2], hexmcu.DEV)
    assert frames == [ack] and loose == b"\x00" and rest == ack[:2]


def test_pcapng_session_is_decoded():
    path = write_pcapng(session())
    try:
        lines, ops = hex_capture.analyse(path)
    finally:
        os.remove(path)
    text = "\n".join(lines)
    assert lines[0].startswith("Dispositivo 1.5")
    assert "FTDI velocidade 115385 baud" in text and "DTR off, RTS off" in text and "BREAK on" in text
    assert "4D 07 02 01 60 46 6F" in text                    # resposta juntada a partir de dois pacotes USB
    assert ops[("out", 0x84)] == 1 and ops[("in", 0x84)] == 1 and ops[("in", 0x02)] == 1
    summ = "\n".join(hex_capture.summary(ops))
    assert "84  init 5 baud pelo cabo" in summ and "POR IMPLEMENTAR" in summ
    assert "02  versão" in summ and "conhecido" in summ


def test_pcap_and_explicit_device():
    path = write_pcap(session())
    try:
        lines, ops = hex_capture.analyse(path, device=CABLE)
        assert sum(ops.values()) == 6
        lines, ops = hex_capture.analyse(path, device=MOUSE)
        assert not ops
    finally:
        os.remove(path)


def test_raw_kline_bytes_without_frames():
    path = write_pcapng([(0.0, setup(hex_capture.FTDI_BAUD, 0x0120)), (0.1, bulk_out(b"\x55")),
                         (0.2, bulk_in(b"\x55"))])
    try:
        lines, ops = hex_capture.analyse(path)
    finally:
        os.remove(path)
    assert not ops and any("55   (bytes sem pacote)" in line for line in lines)
    assert "modo directo" in hex_capture.summary(ops)[0]


def test_bad_files():
    for data in (b"lixo" * 10, b""):
        path = _tmp(data, ".pcapng")
        try:
            hex_capture.analyse(path)
            assert False
        except hex_capture.CaptureError:
            pass
        finally:
            os.remove(path)


def test_command_line_writes_report():
    path = write_pcapng(session())
    out = path + ".txt"
    try:
        assert hex_capture.main([path, "-o", out]) == 0
        with open(out, encoding="utf-8") as fh:
            assert "POR IMPLEMENTAR" in fh.read()
        try:
            hex_capture.main([path, "--device", "x"])
            assert False, "devia recusar --device inválido"
        except SystemExit as e:
            assert e.code != 0
    finally:
        os.remove(path)
        if os.path.exists(out):
            os.remove(out)
