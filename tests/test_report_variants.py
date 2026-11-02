"""Relatório em duas versões: para o cliente (linguagem simples) e técnico (pormenores de comunicação)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())

from rad import report, vag_data

ITEMS = [
    {"address": 0x01, "module": "Motor", "status": "ok",
     "info": {"part": "038906019FN", "component": "1,9l R4 EDC", "coding": 2, "coding_digits": 5, "wsc": 12345,
              "protocol": "KW1281", "baud": 10400, "interface": "COM3", "simulated": False},
     "faults": [vag_data.decode_fault(1247, 0x1E)]},
    {"address": 0x03, "module": "ABS", "status": "ok",
     "info": {"part": "1C0907379K", "component": "ABS/ESP 20 IE CAN", "coding": 18719, "coding_digits": 7,
              "wsc": 12345, "protocol": "KWP2000", "baud": 10400, "interface": "COM3", "simulated": False},
     "faults": [vag_data.decode_fault(283, 0x23)]},
    {"address": 0x15, "module": "Airbag", "status": "error", "error": "Timeout KWP2000 no init"},
]
META = {"interface": "COM3", "simulated": False}


def test_client_report_has_no_communication_details():
    page = report.build_html({"name": "Oficina"}, {"plate": "AA-00-AA"}, ITEMS, meta=META)
    assert "Relatório de diagnóstico" in page and "Relatório técnico" not in page
    for word in ("KW1281", "KWP2000", "baud", "estado 0x", "COM3", "Timeout"):
        assert word not in page, word
    assert "Codificação 00002" in page and "Codificação 0018719" in page     # 5 algarismos no KW1281, 7 no KWP2000


def test_technical_report_shows_protocol_raw_status_and_interface():
    page = report.build_html({"name": "Oficina"}, {"plate": "AA-00-AA"}, ITEMS, meta=META, variant="technical")
    assert "Relatório técnico" in page
    for text in ("KW1281", "KWP2000", "10400 baud", "Código de oficina 12345", "estado 0x1E", "estado 0x23",
                 "tipo 35", "Interface: COM3", "Timeout KWP2000 no init"):
        assert text in page, text


def test_coding_format_follows_the_protocol():
    assert report.format_coding({"coding": 2}) == "00002"
    assert report.format_coding({"coding": 18719, "coding_digits": 7}) == "0018719"
    assert report.format_coding({}) == "—"
