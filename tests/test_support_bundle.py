"""Pacote de suporte (Opções → Suporte): leva o que é preciso para corrigir um problema e nada que identifique o
cliente ou a oficina."""
import json
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())

from rad import applog, autoupdate, capture  # noqa: E402

VIN = "WVWZZZ1JZ3W386752"


def test_scrub_removes_chassis_numbers_and_plates_but_not_bytes_codes_or_dates():
    text = (f"VIN {VIN} matrícula AA-00-AA e 12-AB-34 · 2026-11-01 14:55:00 · 1A 9B 03 · 35-10 · 1C0907379K "
            "· 0123456789ABCDEF0123")
    out = applog.scrub(text)
    assert VIN not in out and "[VIN]" in out and out.count("[MATRÍCULA]") == 2
    for keep in ("2026-11-01 14:55:00", "1A 9B 03", "35-10", "1C0907379K", "0123456789ABCDEF0123"):
        assert keep in out


def test_bundle_has_logs_install_log_and_recordings_without_customer_or_workshop_data():
    with open(os.path.join(applog.log_dir(), "comunicacao_20261101.log"), "w", encoding="utf-8") as fh:
        fh.write(f"OBD VIN: {VIN} cliente AA-00-AA\n")
    with open(autoupdate.log_path(), "w", encoding="utf-8") as fh:
        fh.write("Instalação: ok\n")
    rec = os.path.join(capture.captures_dir(), "teste" + capture.EXT)
    with open(rec, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"rad_capture": capture.FORMAT}) + "\n")
    settings = {"port": "COM3", "adapter": "kline", "workshop/name": "Oficina Secreta", "ui/language": "pt"}
    path = os.path.join(tempfile.mkdtemp(), "suporte.zip")
    applog.make_support_bundle(path, settings=settings, license_state="licensed")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        texts = {n: z.read(n).decode("utf-8", "replace") for n in names}
    assert {"LEIA-ME.txt", "sistema.txt", "comunicacao_20261101.log", "instalacao.log"} <= set(names)
    assert "gravacoes/teste" + capture.EXT in names
    assert VIN not in texts["comunicacao_20261101.log"] and "AA-00-AA" not in texts["comunicacao_20261101.log"]
    sysinfo = texts["sistema.txt"]
    assert "port = COM3" in sysinfo and "Licença: licensed" in sysinfo and "Actualizações:" in sysinfo
    assert "Oficina Secreta" not in "".join(texts.values())
    autoupdate.clear()
    os.remove(rec)
