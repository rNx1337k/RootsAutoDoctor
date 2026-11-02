"""Comparação da validação no carro com um Auto-Scan do VCDS (rad/vcds_log.py). Sem Qt e sem carro."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import validation, vag_data, vcds_log

AUTOSCAN = """VCDS Version: Release 12.12.0 (x64)
Data version: 20130524

Monday,02,November,2026,18:00:00:12345

Chassis Type: 8L - Audi A3/S3 (1997 > 2003)
Scan: 01 02 03 08 15 16 17 19 22 25 29 35 36 37 39 3F 46 47 55 56 57 5F 75 76 77

VIN: WAUZZZ8LZ1A000000   Mileage: 245000km/152237miles

01-Engine -- Status: Malfunction 0010
03-ABS Brakes -- Status: Malfunction 0010
17-Instruments -- Status: OK 0000

-------------------------------------------------------------------------------
Address 01: Engine        Labels: 038-906-019-ASZ.lbl
   Part No: 038 906 019 FN
   Component: 1,9l R4 EDC  G   0SG  8571
   Coding: 00002
   Shop #: WSC 12345
   VCID: 3B6D2E8D7E9C3F1A6B-8016

2 Faults Found:
00532 - Supply Voltage B+
            07-10 - Signal too Low - Intermittent
01247 - Solenoid for Charge Pressure Control (N75)
            30-00 - Open or Short to Plus
Readiness: N/A

-------------------------------------------------------------------------------
Address 03: ABS Brakes        Labels: 1C0-907-379-MK60-F.clb
   Part No SW: 1C0 907 379 K    HW: 1C0 907 379 K
   Component: ABS/ESP 20 IE CAN   0001
   Revision: 00H13001
   Coding: 0018719
   Shop #: WSC 12345 000 00000

1 Fault Found:
00283 - ABS Wheel Speed Sensor; Front Left (G47)
            35-00 - -
             Freeze Frame:
                    Fault Status: 00100011
                    Fault Priority: 2

-------------------------------------------------------------------------------
Address 17: Instruments        Labels: 1J0-920-xx5-17.lbl
   Part No: 1J0 920 926 C
   Component: KOMBI+WEGFAHRSP VDO V01
   Coding: 04211
   Shop #: WSC 00000

No fault code found.

End --------------------------------------------------------------------------
"""


def _report():
    """O que a validação guarda, com as avarias tal como o simulador as devolve."""
    eng = [vag_data.decode_fault(532, 0x87), vag_data.decode_fault(1247, 0x1E)]
    abs_ = [vag_data.decode_fault(283, 0x23)]
    return {"steps": [], "modules": [
        {"address": 0x01, "module": "Motor", "part": "038906019FN", "protocol": "KW1281", "coding": 2,
         "faults_raw": validation.fault_rows(eng, "KW1281")},
        {"address": 0x17, "module": "Painel", "part": "1J0920926C", "protocol": "KW1281", "coding": 4211,
         "faults_raw": []},
        {"address": 0x03, "module": "ABS", "part": "1C0907379K", "protocol": "KWP2000", "coding": 18719,
         "faults_raw": validation.fault_rows(abs_, "KWP2000")},
        {"address": 0x15, "module": "Airbag"},                     # não respondeu: não entra na comparação
    ]}


def test_autoscan_text_is_parsed_without_vin_or_mileage():
    mods = vcds_log.parse(AUTOSCAN)
    assert sorted(mods) == [0x01, 0x03, 0x17]
    eng = mods[0x01]
    assert eng["part"] == "038 906 019 FN" and eng["coding"] == 2 and eng["name"] == "Engine"
    assert [(f["code"], f["status_text"], f["intermittent"]) for f in eng["faults"]] == \
        [(532, "07-10", True), (1247, "30-00", False)]
    assert mods[0x03]["part"] == "1C0 907 379 K" and mods[0x03]["coding"] == 18719
    assert mods[0x03]["faults"][0]["elab_code"] == 35            # a "Freeze Frame" não estraga o estado
    assert mods[0x17]["no_faults"] and not mods[0x17]["faults"]
    flat = repr(mods)
    assert "WAUZZZ" not in flat and "245000" not in flat


def test_comparison_finds_matches_and_the_kwp2000_status_difference():
    c = vcds_log.compare(_report(), vcds_log.parse(AUTOSCAN))
    by = {m["address"]: {r["item"]: r for r in m["rows"]} for m in c["modules"]}
    assert sorted(by) == [0x01, 0x03, 0x17]
    assert all(r["result"] == vcds_log.MATCH for r in by[0x01].values()), by[0x01]
    assert by[0x17]["Avarias"]["result"] == vcds_log.MATCH
    # 0x23 → o programa diz 35-00, o VCDS diz 35-00: igual
    assert by[0x03]["Avaria 00283"]["result"] == vcds_log.MATCH
    text, ok = vcds_log.verdict(c)
    assert ok and c["summary"][vcds_log.DIFF] == 0


def test_differences_and_missing_faults_are_reported():
    rep = _report()
    rep["modules"][0]["faults_raw"] = validation.fault_rows([vag_data.decode_fault(532, 0x07)], "KW1281")
    rep["modules"][0]["coding"] = 1
    c = vcds_log.compare(rep, vcds_log.parse(AUTOSCAN))
    eng = {r["item"]: r for r in c["modules"][0]["rows"]}
    assert eng["Codificação"]["result"] == vcds_log.DIFF
    assert eng["Avaria 00532"]["result"] == vcds_log.DIFF and "0x07" in eng["Avaria 00532"]["note"]
    assert eng["Avaria 01247"]["result"] == vcds_log.ONLY_VCDS
    text, ok = vcds_log.verdict(c)
    assert not ok and "3" in text


def test_new_vcds_status_format_is_left_for_a_manual_check():
    text = AUTOSCAN.replace("            35-00 - -", "            004 - No Signal/Communication - Intermittent")
    c = vcds_log.compare(_report(), vcds_log.parse(text))
    abs_rows = {r["item"]: r for r in next(m for m in c["modules"] if m["address"] == 0x03)["rows"]}
    row = abs_rows["Avaria 00283"]
    assert row["result"] == vcds_log.MANUAL and "004" in row["vcds"] and "0x23" in row["rad"]
    assert vcds_log.verdict(c)[1]


def test_vcds_lite_and_pcode_lines():
    text = """Address 01: Engine
Part No: 038906019FN
Component: 1,9l R4 EDC  G   0SG  8571
Coding: 00002
1 Fault Found:
16486 - Mass Air Flow Sensor (G70): Signal too Low
            P0102 - 35-10 - - - Intermittent
"""
    f = vcds_log.parse(text)[0x01]["faults"][0]
    assert f["code"] == 16486 and f["pcode"] == "P0102" and f["status_text"] == "35-10" and f["intermittent"]


def test_validation_report_gets_the_comparison_and_can_be_redone_from_the_saved_files():
    d = tempfile.mkdtemp()
    html_path = os.path.join(d, "validacao_20261102_180000.html")
    rep = dict(_report(), version="x", date="2026-11-02", interface="COM3", vehicle={"model": "A3"},
               report_path=html_path)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(validation.build_html(rep))
    validation.save_data(rep, html_path)
    vcds_path = os.path.join(d, "WAUZZZ8LZ1A000000-01234567-Autoscan.txt")
    with open(vcds_path, "wb") as fh:
        fh.write(AUTOSCAN.replace("\n", "\r\n").encode("cp1252"))
    again = validation.load_data(html_path)                   # outro dia, noutro PC
    c = validation.compare_with_vcds(again, vcds_path)
    assert vcds_log.verdict(c)[1]
    with open(html_path, encoding="utf-8") as fh:
        page = fh.read()
    assert "Comparação com o VCDS" in page and "Igual ao VCDS" in page
    assert "WAUZZZ" not in page and d not in page            # nem o chassis nem o caminho do PC
    assert validation.load_data(html_path)["vcds_compare"]["summary"][vcds_log.MATCH] >= 6
    try:
        validation.load_data(vcds_path)
        assert False
    except (OSError, ValueError):
        pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
