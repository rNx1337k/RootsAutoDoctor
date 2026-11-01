"""Leitura e comparação das gravações de valores de medição do programa (CSV)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import logview

_APP = None

RAD_CSV = (
    "﻿Hora;G001.1 Rotação [/min];G001.2 Quantidade injectada [mg/H];G001.3 Temperatura [°C];G001.4;"
    "G011.1 Rotação [/min];G011.2 Pressão pedida [mbar];G011.3 Pressão real [mbar];G011.4 N75 [%]\n"
    "23:59:59.500;850;4.2;88.5;QUENTE;850;1010;990;34.0\n"
    "00:00:00.000;1900;12.1;89.1;QUENTE;1900;1900;1850;62.5\n"
    "00:00:01.000;2400;;89.4;QUENTE;2400;2100;1500;70\n"
)

AFTER_CSV = (
    "Hora;G001.1 Rotação [/min];G001.2 Quantidade injectada [mg/H];G011.3 Pressão real [mbar]\n"
    "10:00:00.000;860;4.0;980\n"
    "10:00:00.500;1950;11.8;1930\n"
    "10:00:01.000;2500;14.0;2150\n"
)


def _write(text, name="log.csv"):
    path = os.path.join(tempfile.mkdtemp(), name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


def test_numbers_accept_both_decimal_marks_and_reject_text():
    assert logview.to_number("1500") == 1500
    assert logview.to_number("1,5") == 1.5
    assert logview.to_number("-3.25 %") == -3.25
    assert logview.to_number("QUENTE") is None
    assert logview.to_number("1º mapa") is None
    assert logview.to_number("") is None


def test_reads_the_programs_own_csv_across_midnight():
    log = logview.parse(_write(RAD_CSV))
    names = [c.name for c in log.channels]
    assert names[0] == "G001.1 Rotação" and "G011.3 Pressão real" in names
    rpm = log.channels[0]
    assert rpm.unit == "/min" and rpm.group == 1 and rpm.field == 1
    assert rpm.times == [0.0, 0.5, 1.5]              # a hora passou da meia-noite sem voltar atrás
    assert rpm.stats() == (850, 2400, (850 + 1900 + 2400) / 3)
    iq = log.channel("G001.2 Quantidade injectada")
    assert iq.values[2] is None and iq.stats()[1] == 12.1     # célula vazia não entra nas contas
    assert log.channel("G001.4").stats() is None              # só texto (QUENTE)
    assert abs(log.duration() - 1.5) < 1e-9 and log.samples() == 3


def test_value_at_returns_the_nearest_sample():
    rpm = logview.parse(_write(RAD_CSV)).channels[0]
    assert rpm.value_at(0.4) == 1900
    assert rpm.value_at(99) == 2400


def test_compare_pairs_channels_by_group_and_field():
    before = logview.parse(_write(RAD_CSV))
    after = logview.parse(_write(AFTER_CSV, "depois.csv"))
    pairs = {a.name: (b.name, d) for a, b, d in logview.compare(before, after)}
    assert set(pairs) == {"G001.1 Rotação", "G001.2 Quantidade injectada", "G011.3 Pressão real"}
    expected = (980 + 1930 + 2150) / 3 - (990 + 1850 + 1500) / 3
    assert abs(pairs["G011.3 Pressão real"][1] - expected) < 1e-9


def test_unknown_or_empty_files_give_a_clear_error():
    for text in ("", "a;b;c\n1;2;3\n", "Hora;G001.1 X\n"):
        try:
            logview.parse(_write(text))
        except logview.LogError as e:
            assert str(e)
        else:
            raise AssertionError("devia ter falhado")
    try:
        logview.parse(os.path.join(tempfile.mkdtemp(), "nao_existe.csv"))
    except logview.LogError:
        pass
    else:
        raise AssertionError("devia ter falhado")


def test_viewer_window_shows_channels_comparison_and_cursor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    global _APP
    app = _APP = QApplication.instance() or QApplication([])     # vive até ao fim: sem ela o Qt cai ao sair
    from rad.ui.logviewer import LogViewerDialog, MAX_SERIES
    dlg = LogViewerDialog(None, _write(RAD_CSV))
    dlg.resize(1100, 680)
    dlg.show()
    app.processEvents()
    assert dlg.channel_list.count() == 8
    assert [c.name for c in dlg.selected()] == ["G001.1 Rotação", "G001.2 Quantidade injectada"]
    assert len(dlg.chart.series) == 2 and not dlg.uncompare_btn.isEnabled()
    text_only = dlg.channel_list.item(3)                       # G001.4: só QUENTE
    assert not text_only.flags() & Qt.ItemIsEnabled
    dlg.set_other(logview.parse(_write(AFTER_CSV, "depois.csv")))
    assert len(dlg.chart.series) == 4                          # cada canal com a sua linha tracejada
    assert [s[2] for s in dlg.chart.series] == [False, True, False, True]
    boost_row = next(r for r in range(dlg.table.rowCount()) if dlg.table.item(r, 0).text() == "G011.3 Pressão real")
    assert dlg.table.item(boost_row, 6).text().startswith("+")
    for i in range(dlg.channel_list.count()):                  # não passa do máximo de canais
        it = dlg.channel_list.item(i)
        if it.flags() & Qt.ItemIsEnabled:
            it.setCheckState(Qt.Checked)
    assert len(dlg.selected()) == MAX_SERIES
    assert str(MAX_SERIES) in dlg.cursor_lbl.text()
    dlg._show_cursor(0.5)
    assert "G001.1 Rotação: 1900 /min" in dlg.cursor_lbl.text()
    dlg.chart.repaint()
    dlg.set_other(None)
    assert all(not s[2] for s in dlg.chart.series)
    dlg.close()
    dlg.deleteLater()
    app.processEvents()
