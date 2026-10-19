"""Opções: interface, oficina, licença e ferramentas de suporte."""
import datetime
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QScrollArea, QVBoxLayout, QWidget,
)

from ... import APP_NAME
from ...kline import list_serial_ports
from ..style import BAD, OK, WARN
from .common import lbl, btn, card, page_header


class OptionsPage(QWidget):
    saved = Signal(dict)
    test_req = Signal()
    license_changed = Signal(dict)
    link_check_req = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header("Opções", "Licença, interface (cabo), comunicação e dados da oficina."))

        from ... import license as lic
        self.lic = lic
        lc = card()
        lv = QVBoxLayout(lc)
        lv.setContentsMargins(20, 18, 20, 18)
        lv.setSpacing(8)
        lh = QHBoxLayout()
        lh.addWidget(lbl("Licença", "h2"))
        lh.addStretch(1)
        self.lic_status = lbl("", "h2")
        lh.addWidget(self.lic_status)
        lv.addLayout(lh)
        mrow = QHBoxLayout()
        mrow.addWidget(lbl("Código deste PC", "muted"))
        self.machine_lbl = lbl(lic.machine_code(), "h2")
        self.machine_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        mrow.addWidget(self.machine_lbl)
        mrow.addWidget(btn("Copiar", None, lambda: QGuiApplication.clipboard().setText(self.machine_lbl.text())))
        mrow.addStretch(1)
        lv.addLayout(mrow)
        krow = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Cole aqui a chave de licença que recebeu")
        krow.addWidget(self.key_edit, 1)
        krow.addWidget(btn("Activar", "primary", self._activate))
        lv.addLayout(krow)
        lv.addWidget(lbl("Para comprar uma licença envie o código deste PC. Sem licença o programa funciona "
                         "em modo de avaliação: todas as funções disponíveis, relatórios com a marca "
                         "\"Versão de avaliação\".", "muted", wrap=True))
        v.addWidget(lc)
        c = card()
        f = QFormLayout(c)
        f.setContentsMargins(20, 18, 20, 18)
        f.setVerticalSpacing(12)
        prow = QHBoxLayout()
        self.port = QComboBox()
        self.port.setMinimumWidth(380)
        prow.addWidget(self.port, 1)
        prow.addWidget(btn("Actualizar", None, self.refresh_ports))
        f.addRow(lbl("Porta do cabo", "muted"), prow)
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
        row = QHBoxLayout()
        row.addWidget(btn("Guardar", "primary", self._save))
        row.addWidget(btn("Detectar cabo", "primary", self._detect_cable))
        row.addWidget(btn("Testar interface", None, self._test))
        row.addWidget(btn("Diagnóstico da ligação", None, lambda: self.link_check_req.emit()))
        row.addWidget(btn("Pacote de suporte", None, self._support_bundle))
        row.addWidget(btn("Abrir pasta de registos", None, self._open_logs))
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(lbl(
            "Cabos suportados: cabos KKL 'VAG-COM 409.1' e clones VCDS de linha K com chip FTDI ou CH340 "
            "(aparecem como porta COM normal). Para máxima velocidade em cabos FTDI: Gestor de dispositivos → "
            "Portas (COM) → Propriedades → Definições da porta → Avançadas → Latency Timer = 1 ms.\n\n"
            "Cabos HEX-USB+CAN / HEX-V2 (originais ou clones) usam firmware fechado da Ross-Tech e só "
            "funcionam com o VCDS — não aparecem como porta COM e não podem ser usados por outro programa.",
            "muted", wrap=True))
        v.addStretch(1)
        self.refresh_ports()
        self._load()

    def show_license(self, info):
        text = self.lic.STATUS_TEXT.get(info["status"], "")
        if info["status"] == "valid":
            exp = f" até {info['expires']}" if info.get("expires") else " (vitalícia)"
            text = f"{text}{exp} — {info.get('holder', '')}"
        self.lic_status.setText(text)
        self.lic_status.setStyleSheet(f"color: {OK if info['status'] == 'valid' else WARN};")

    def _activate(self):
        key = self.key_edit.text().strip()
        if not key:
            return
        r = self.lic.activate(key)
        if r["status"] == "valid":
            self.key_edit.clear()
            QMessageBox.information(self, APP_NAME, f"Licença activada para {r.get('holder', '')}. Obrigado!")
            self.license_changed.emit(r)
        else:
            QMessageBox.warning(self, APP_NAME, self.lic.STATUS_TEXT.get(r["status"], "Chave inválida") + ".")
        self.show_license(r if r["status"] == "valid" else self.lic.load())

    def refresh_ports(self):
        cur = self.port.currentData() or self.settings.value("port", "")
        self.port.clear()
        for dev, desc in list_serial_ports():
            self.port.addItem(desc, dev)
        i = self.port.findData(cur)
        if i >= 0:
            self.port.setCurrentIndex(i)

    def _load(self):
        for combo, key, default in ((self.port, "port", ""), (self.baud, "baud", "auto"), (self.echo, "echo", "auto")):
            i = combo.findData(self.settings.value(key, default))
            if i >= 0:
                combo.setCurrentIndex(i)
        self.raw.setChecked(self.settings.value("raw_log", "false") == "true")
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
                "echo": self.echo.currentData(), "raw_log": self.raw.isChecked()}

    def _save(self):
        c = self.config()
        self.settings.setValue("port", c["port"])
        self.settings.setValue("baud", c["baud"])
        self.settings.setValue("echo", c["echo"])
        self.settings.setValue("raw_log", "true" if c["raw_log"] else "false")
        for k, val in self.workshop().items():
            self.settings.setValue(f"workshop/{k}", val)
        self.saved.emit(c)

    def _detect_cable(self):
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QApplication
        from ... import cable
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            findings = cable.detect()
        finally:
            QApplication.restoreOverrideCursor()
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
        j2534 = cable.j2534_devices()
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
                                                "portas e cabos. Não contém licenças nem dados de clientes.")

    def _open_logs(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from ... import applog
        QDesktopServices.openUrl(QUrl.fromLocalFile(applog.log_dir()))

    def _test(self):
        self._save()
        self.test_req.emit()

    def select_simulator(self):
        from ...kline import SIM_PORT
        i = self.port.findData(SIM_PORT)
        if i >= 0:
            self.port.setCurrentIndex(i)
        self._save()


# ---------------------------------------------------------------- histórico
