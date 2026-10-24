"""Opções: interface, oficina e ferramentas de suporte."""
import datetime
import logging
import os
import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QScrollArea, QVBoxLayout, QWidget,
)

from ... import APP_NAME
from ...kline import list_serial_ports
from ...settings import ui_scale
from ..style import BAD, OK, WARN
from .common import lbl, btn, card, page_header

log = logging.getLogger(__name__)


class OptionsPage(QWidget):
    saved = Signal(dict)
    test_req = Signal()
    link_check_req = Signal()
    hex_mode_req = Signal(str)
    coverage_req = Signal()
    detect_done = Signal(object)          # resultado da procura do cabo (vem de uma thread à parte)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header("Opções", "Interface (cabo), comunicação e dados da oficina.", "Configuração"))

        c = card()
        f = QFormLayout(c)
        f.setContentsMargins(20, 18, 20, 18)
        f.setVerticalSpacing(12)
        self.adapter = QComboBox()
        for t, d in [("Cabo KKL / J2534 — diagnóstico VAG pela linha K (KW1281, KWP2000)", "kline"),
                     ("Adaptador ELM327 — OBD-II / EOBD multimarca (CAN e linha K)", "elm327")]:
            self.adapter.addItem(t, d)
        self.adapter.currentIndexChanged.connect(self._adapter_changed)
        f.addRow(lbl("Tipo de interface", "muted"), self.adapter)
        prow = QHBoxLayout()
        self.port = QComboBox()
        self.port.setMinimumWidth(240)
        prow.addWidget(self.port, 1)
        prow.addWidget(btn("Actualizar", None, self.refresh_ports))
        f.addRow(lbl("Porta do cabo", "muted"), prow)
        self.port.currentIndexChanged.connect(self._port_changed)
        self.elm_proto = QComboBox()
        for t, d in [("Automático (o adaptador procura)", "0"), ("ISO 15765-4 CAN 11 bits 500k", "6"),
                     ("ISO 15765-4 CAN 29 bits 500k", "7"), ("ISO 15765-4 CAN 11 bits 250k", "8"),
                     ("ISO 15765-4 CAN 29 bits 250k", "9"), ("ISO 14230-4 KWP rápido", "5"),
                     ("ISO 14230-4 KWP 5 baud", "4"), ("ISO 9141-2", "3"), ("SAE J1850 VPW", "2"),
                     ("SAE J1850 PWM", "1")]:
            self.elm_proto.addItem(t, d)
        self.elm_proto_lbl = lbl("Protocolo OBD", "muted")
        f.addRow(self.elm_proto_lbl, self.elm_proto)
        self.baud = QComboBox()
        for t, d in [("Automática", "auto"), ("10400", "10400"), ("9600", "9600"), ("4800", "4800")]:
            self.baud.addItem(t, d)
        f.addRow(lbl("Velocidade", "muted"), self.baud)
        self.echo = QComboBox()
        for t, d in [("Automático", "auto"), ("Com eco (KKL normal)", "on"), ("Sem eco", "off")]:
            self.echo.addItem(t, d)
        f.addRow(lbl("Eco da linha K", "muted"), self.echo)
        self.raw = QCheckBox("Registo detalhado: todos os blocos e bytes (para enviar quando houver problemas)")
        f.addRow(lbl("Debug", "muted"), self.raw)
        crow = QHBoxLayout()
        crow.setSpacing(8)
        self.detect_btn = btn("Detectar cabo", "primary", self._detect_cable)
        crow.addWidget(self.detect_btn)
        crow.addWidget(btn("Testar interface", None, self._test))
        crow.addWidget(btn("Diagnóstico da ligação", None, lambda: self.link_check_req.emit()))
        crow.addWidget(btn("Compatibilidade", None, lambda: self.coverage_req.emit()))
        crow.addStretch(1)
        f.addRow(lbl("Cabo", "muted"), crow)
        hrow = QHBoxLayout()
        hrow.setSpacing(8)
        hrow.addWidget(btn("Ler modo do cabo", None, lambda: self._hex("read")))
        hrow.addWidget(btn("Repor modo inteligente", None, lambda: self._hex("smart")))
        hrow.addStretch(1)
        self.hex_lbl = lbl("Cabo HEX", "muted")
        f.addRow(self.hex_lbl, hrow)
        self._form, self._hex_row = f, hrow
        v.addWidget(c)

        wc = card()
        wf = QFormLayout(wc)
        wf.setContentsMargins(20, 18, 20, 18)
        wf.setVerticalSpacing(10)
        wf.addRow(lbl("Dados da oficina", "h2"))
        wf.addRow(lbl("Aparecem no cabeçalho do relatório para o cliente.", "muted"))
        self.ws_edits = {}
        for key, name in [("name", "Nome da oficina"), ("address", "Morada"), ("phone", "Telefone"),
                          ("email", "Email"), ("nif", "NIF")]:
            e = QLineEdit()
            e.setPlaceholderText(name)
            self.ws_edits[key] = e
            wf.addRow(lbl(name, "muted"), e)
        lrow = QHBoxLayout()
        self.ws_logo_preview = QLabel()
        self.ws_logo_preview.setFixedSize(150, 60)
        self.ws_logo_preview.setAlignment(Qt.AlignCenter)
        self.ws_logo_preview.setStyleSheet("background: #0B1120; border: 1px dashed #3A4A72; border-radius: 8px; color: #7C8BAD;")
        lrow.addWidget(self.ws_logo_preview)
        lrow.addWidget(btn("Escolher imagem…", None, self._pick_logo))
        lrow.addWidget(btn("Remover", None, self._remove_logo))
        lrow.addStretch(1)
        wf.addRow(lbl("Logótipo da oficina", "muted"), lrow)
        wf.addRow(lbl("O logótipo aparece no relatório para o cliente e na barra lateral do programa.", "muted"))
        v.addWidget(wc)

        sc = card()
        sf = QFormLayout(sc)
        sf.setContentsMargins(20, 18, 20, 18)
        sf.setVerticalSpacing(10)
        sf.addRow(lbl("Ecrã", "h2"))
        self.scale = QComboBox()
        for t, d in [("Normal (100%)", "1"), ("Grande (115%)", "1.15"), ("Muito grande (130%)", "1.3"),
                     ("Oficina — ver ao longe (150%)", "1.5")]:
            self.scale.addItem(t, d)
        sf.addRow(lbl("Tamanho da interface", "muted"), self.scale)
        sf.addRow(lbl("Aumenta letras, botões e mostradores para se lerem a partir do carro. "
                      "Aplica-se quando o programa voltar a abrir.", "muted", wrap=True))
        v.addWidget(sc)
        row = QHBoxLayout()
        row.addWidget(btn("Guardar", "primary", self._save))
        row.addSpacing(12)
        row.addWidget(btn("Pacote de suporte", None, self._support_bundle))
        row.addWidget(btn("Abrir pasta de registos", None, self._open_logs))
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(lbl(
            "Cabos suportados: cabos KKL 'VAG-COM 409.1' e clones VCDS de linha K com chip FTDI ou CH340 "
            "(aparecem como porta COM normal). Para máxima velocidade em cabos FTDI: Gestor de dispositivos → "
            "Portas (COM) → Propriedades → Definições da porta → Avançadas → Latency Timer = 1 ms.\n\n"
            "Adaptadores ELM327 (USB ou Bluetooth) aparecem como porta COM: escolha \"Adaptador ELM327\" em Tipo de "
            "interface e use a página OBD-II para qualquer marca com OBD-II/EOBD. Os clones baratos nem sempre "
            "implementam todos os comandos; o programa indica o que o adaptador respondeu.\n\n"
            "Clones HEX-USB+CAN (chip FTDI VID 0403 PID FA24 com microcontrolador) aparecem como D2XX:… "
            "(driver RT-USB) ou FTDI:… (driver WinUSB). O Diagnóstico da ligação fala com o microcontrolador "
            "do cabo e mostra o estado real; a leitura de centralinas através dele ainda não está disponível. "
            "Interfaces HEX-V2 / HEX-NET genuínas usam firmware fechado da Ross-Tech e não são suportadas.",
            "muted", wrap=True))
        v.addStretch(1)
        self._detecting = False
        self.detect_done.connect(self._detect_finished)
        self.refresh_ports()
        self._load()

    def refresh_ports(self):
        cur = self.port.currentData() or self.settings.value("port", "")
        self.port.clear()
        for dev, desc in list_serial_ports():
            self.port.addItem(desc, dev)
        i = self.port.findData(cur)
        if i >= 0:
            self.port.setCurrentIndex(i)

    def _adapter_changed(self, *_):
        """Mostra só as opções que se aplicam à interface escolhida."""
        elm = self.adapter.currentData() == "elm327"
        form = getattr(self, "_form", None)
        if form is None:
            return
        form.setRowVisible(self.elm_proto, elm)
        for row in (self.baud, self.echo, self._hex_row):
            form.setRowVisible(row, not elm)

    def _port_changed(self, *_):
        from ...kline import is_elm_sim_port
        if is_elm_sim_port(self.port.currentData() or ""):
            i = self.adapter.findData("elm327")
            if i >= 0 and self.adapter.currentIndex() != i:
                self.adapter.setCurrentIndex(i)

    def _load(self):
        for combo, key, default in ((self.port, "port", ""), (self.baud, "baud", "auto"), (self.echo, "echo", "auto"),
                                    (self.adapter, "adapter", "kline"), (self.elm_proto, "elm_protocol", "0")):
            i = combo.findData(self.settings.value(key, default))
            if i >= 0:
                combo.setCurrentIndex(i)
        self.raw.setChecked(self.settings.value("raw_log", "false") == "true")
        self.scale.setCurrentIndex(max(0, self.scale.findData(ui_scale(self.settings))))
        self._adapter_changed()
        for k, e in self.ws_edits.items():
            e.setText(self.settings.value(f"workshop/{k}", "") or "")
        self._show_logo()

    @staticmethod
    def logo_file():
        from ...applog import log_dir
        return os.path.join(os.path.dirname(log_dir()), "oficina_logo.png")

    def workshop_logo(self):
        p = self.logo_file()
        return p if os.path.exists(p) else None

    def _show_logo(self):
        from PySide6.QtGui import QPixmap
        p = self.workshop_logo()
        if p:
            pm = QPixmap(p).scaled(140, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.ws_logo_preview.setPixmap(pm)
        else:
            self.ws_logo_preview.setPixmap(QPixmap())
            self.ws_logo_preview.setText("Sem logótipo")

    def _pick_logo(self):
        from PySide6.QtGui import QImage
        path, _ = QFileDialog.getOpenFileName(self, "Logótipo da oficina", os.path.expanduser("~"),
                                              "Imagens (*.png *.jpg *.jpeg *.bmp *.webp)")
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, APP_NAME, "Não foi possível abrir essa imagem.")
            return
        if img.width() > 800 or img.height() > 400:
            img = img.scaled(800, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if not img.save(self.logo_file(), "PNG"):
            QMessageBox.warning(self, APP_NAME, "Não foi possível guardar o logótipo.")
            return
        self._show_logo()
        self.saved.emit(self.config())

    def _remove_logo(self):
        try:
            os.remove(self.logo_file())
        except OSError:
            pass
        self._show_logo()
        self.saved.emit(self.config())
    def workshop(self):
        return {k: e.text().strip() for k, e in self.ws_edits.items()}

    def config(self):
        return {"port": self.port.currentData() or "", "baud": self.baud.currentData(),
                "echo": self.echo.currentData(), "raw_log": self.raw.isChecked(),
                "adapter": self.adapter.currentData() or "kline", "elm_protocol": self.elm_proto.currentData() or "0"}

    def _save(self):
        c = self.config()
        self.settings.setValue("port", c["port"])
        self.settings.setValue("baud", c["baud"])
        self.settings.setValue("echo", c["echo"])
        self.settings.setValue("raw_log", "true" if c["raw_log"] else "false")
        self.settings.setValue("adapter", c["adapter"])
        self.settings.setValue("elm_protocol", c["elm_protocol"])
        for k, val in self.workshop().items():
            self.settings.setValue(f"workshop/{k}", val)
        scale = self.scale.currentData() or "1"
        if scale != ui_scale(self.settings):
            self.settings.setValue("ui/scale", scale)
            QMessageBox.information(self, APP_NAME, "O novo tamanho da interface aplica-se quando voltar a abrir "
                                                    "o programa.")
        self.saved.emit(c)

    def _detect_cable(self):
        """Procura o cabo numa thread à parte: o PowerShell pode demorar vários segundos e a janela não
        deve ficar congelada entretanto."""
        if self._detecting:
            return
        self._detecting = True
        self.detect_btn.setEnabled(False)
        self.detect_btn.setText("A procurar…")
        threading.Thread(target=self._detect_worker, name="detectar-cabo", daemon=True).start()

    def _detect_worker(self):
        from ... import cable
        try:
            res = (cable.detect(), cable.j2534_devices())
        except Exception as e:
            log.warning("Detectar cabo falhou", exc_info=True)
            res = e
        try:
            self.detect_done.emit(res)
        except RuntimeError:              # a janela já foi fechada
            pass

    def _detect_finished(self, res):
        self._detecting = False
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText("Detectar cabo")
        if isinstance(res, Exception):
            QMessageBox.warning(self, APP_NAME, f"Não foi possível procurar o cabo:\n{res}")
            return
        findings, j2534 = res
        self.refresh_ports()
        colors = {"ok": OK, "warn": WARN, "bad": BAD}
        if not findings:
            html = ("<p><b>Nenhum cabo de diagnóstico encontrado.</b></p>"
                    "<p>Ligue o cabo à porta USB e volte a carregar em Detectar cabo. Se continuar sem aparecer:</p>"
                    "<ul><li>Experimente outra porta USB (de preferência directamente no PC, sem hub).</li>"
                    "<li>Abra o Gestor de Dispositivos e veja se aparece um dispositivo com ponto de exclamação "
                    "em <i>Outros dispositivos</i> — nesse caso falta o driver.</li></ul>")
        else:
            parts = []
            for f in findings:
                link = (f"<br><a href='{f['driver_url']}'>Página oficial do driver</a>"
                        if f.get("driver_url") else "")
                parts.append(f"<p><b style='color:{colors[f['level']]}'>{f['title']}</b><br>{f['detail']}{link}</p>")
            html = "".join(parts)
        if j2534:
            html += "<p><b>Interfaces J2534 (PassThru) instaladas:</b></p><ul>"
            for d in j2534:
                html += (f"<li><b>{d['name']}</b> — {d['vendor']} ({d['view']})<br>"
                         f"Protocolos: {', '.join(d['protocols']) or '—'}<br><small>{d['dll']}</small></li>")
            html += "</ul>"
        else:
            html += "<p>Nenhuma interface J2534 (PassThru) registada neste PC.</p>"
        ready = [f["com"] for f in findings if f.get("com")]
        if len(ready) == 1:
            i = self.port.findData(ready[0])
            if i >= 0:
                self.port.setCurrentIndex(i)
                self._save()
                html += f"<p>A porta <b>{ready[0]}</b> foi escolhida e guardada automaticamente.</p>"
        box = QMessageBox(self)
        box.setWindowTitle("Detectar cabo")
        box.setTextFormat(Qt.RichText)
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        box.setText(html)
        dm = box.addButton("Abrir Gestor de Dispositivos", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Ok)
        box.exec()
        if box.clickedButton() is dm:
            try:
                os.startfile("devmgmt.msc")      # abre sem pedir administrador (só leitura)
            except Exception:
                pass

    def _support_bundle(self):
        from ... import applog
        name = f"RootsAutoDoctor_suporte_{datetime.datetime.now():%Y%m%d_%H%M}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar pacote de suporte",
                                              os.path.join(os.path.expanduser("~"), "Desktop", name), "Zip (*.zip)")
        if not path:
            return
        try:
            applog.make_support_bundle(path)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Não foi possível criar o pacote:\n{e}")
            return
        QMessageBox.information(self, APP_NAME, f"Pacote de suporte guardado em:\n{path}\n\n"
                                                "Contém os registos de comunicação dos últimos dias e a lista de "
                                                "portas e cabos. Não contém dados de clientes.")

    def _open_logs(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from ... import applog
        QDesktopServices.openUrl(QUrl.fromLocalFile(applog.log_dir()))

    def _hex(self, mode):
        self._save()
        self.hex_mode_req.emit(mode)

    def _test(self):
        self._save()
        self.test_req.emit()

    def select_simulator(self, kind="kline"):
        """kind: "kline" (simulador VAG) ou "elm327" (simulador OBD-II)."""
        from ...kline import SIM_ELM_PORT, SIM_PORT
        i = self.port.findData(SIM_ELM_PORT if kind == "elm327" else SIM_PORT)
        if i >= 0:
            self.port.setCurrentIndex(i)
        j = self.adapter.findData(kind)
        if j >= 0:
            self.adapter.setCurrentIndex(j)
        self._save()


# ---------------------------------------------------------------- histórico
