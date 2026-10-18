"""Janela principal do Roots Auto Doctor."""
import datetime
import os

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QImage, QKeySequence, QPageSize, QShortcut, QTextDocument
from PySide6.QtWidgets import (
    QButtonGroup, QDockWidget, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QMainWindow,
    QMessageBox, QPlainTextEdit, QStackedWidget, QVBoxLayout, QWidget,
)

from .. import APP_NAME, VERSION, applog, history, report, vag_data
from ..kline import SIM_PORT
from ..worker import Worker
from .pages import (AutoScanPage, HistoryPage, HomePage, ModulePage, ModuleSelectPage,
                    OptionsPage, btn, lbl)
from .style import BLUE_SOFT, MUTED, OK, QSS, WARN
from .widgets import LogoLabel, PulseIndicator, Toast, asset_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}")
        self.setWindowIcon(QIcon(asset_path("icon.ico")))
        self.resize(1320, 860)
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(QSS)
        self.settings = QSettings("Roots", "RootsAutoDoctor")
        self.module_faults = None
        self.disk_log = applog.DiskLog()

        self.worker = Worker()
        self.worker.log.connect(self.append_log)
        self.worker.state.connect(self.on_state)
        self.worker.result.connect(self.on_result)
        self.worker.error.connect(self.on_error)
        self.worker.live.connect(self.on_live)
        self.worker.scan_progress.connect(self.on_scan_progress)

        root = QWidget()
        root.setObjectName("root")
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.setCentralWidget(root)

        # ---------------- barra lateral
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(236)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(14, 18, 14, 16)
        sv.setSpacing(6)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(LogoLabel(46))
        bt = QVBoxLayout()
        bt.setSpacing(0)
        bt.addWidget(lbl("Roots", "wordmark"))
        bt.addWidget(lbl("Auto Doctor", "wordmarkSub"))
        brand.addLayout(bt)
        brand.addStretch(1)
        sv.addLayout(brand)
        sv.addSpacing(22)

        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        self.nav_btns = {}
        for key, text in [("home", "Início"), ("modules", "Controladores"),
                          ("module", "Controlador ligado"), ("autoscan", "Auto-Scan"),
                          ("history", "Histórico"), ("options", "Opções")]:
            b = btn(text, "nav", lambda _=False, k=key: self.show_page(k))
            b.setCheckable(True)
            self.nav.addButton(b)
            self.nav_btns[key] = b
            sv.addWidget(b)
        self.nav_btns["module"].setEnabled(False)
        sv.addStretch(1)

        conn = QFrame()
        conn.setObjectName("card")
        cv = QVBoxLayout(conn)
        cv.setContentsMargins(12, 10, 12, 10)
        cv.setSpacing(4)
        self.conn_lbl = lbl("Sem ligação", "h2")
        self.conn_sub = lbl("", "muted")
        self.conn_sub.setWordWrap(True)
        self.pulse = PulseIndicator()
        cv.addWidget(self.conn_lbl)
        cv.addWidget(self.pulse)
        cv.addWidget(self.conn_sub)
        self.reconnect_btn = btn("Voltar a ligar", "primary", self._reconnect)
        self.reconnect_btn.hide()
        cv.addWidget(self.reconnect_btn)
        sv.addWidget(conn)
        self.last_address = None
        h.addWidget(side)

        # ---------------- páginas
        self.stack = QStackedWidget()
        h.addWidget(self.stack, 1)
        self.home = HomePage()
        self.select = ModuleSelectPage()
        self.module = ModulePage(self.worker)
        self.scan = AutoScanPage(self.worker)
        self.options = OptionsPage(self.settings)
        self.hist = HistoryPage()
        self.pages = {"home": self.home, "modules": self.select, "module": self.module,
                      "autoscan": self.scan, "history": self.hist, "options": self.options}
        for p in self.pages.values():
            self.stack.addWidget(p)

        self.home.go.connect(self._home_go)
        self.select.connect_req.connect(self.connect_module)
        self.scan.connect_req.connect(self.connect_module)
        self.scan.report_req.connect(lambda: self.export_report("scan"))
        self.module.report_req.connect(lambda: self.export_report("module"))
        self.hist.report_req.connect(self.export_session)
        self.options.saved.connect(self.apply_config)
        self.options.test_req.connect(lambda: self.worker.submit("test_interface"))

        # ---------------- registo
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(4000)
        dock = QDockWidget("Registo de comunicação", self)
        dock.setWidget(self.log)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self.resizeDocks([dock], [150], Qt.Vertical)
        self.log_dock = dock
        self.menuBar().hide()

        self.toast = Toast(root)
        self._shortcuts()
        self.statusBar().showMessage(f"{APP_NAME} v{VERSION}")
        self.set_conn_state("disconnected")
        self.worker.start()
        self.apply_config(self.options.config(), quiet=True)
        self.show_page("home")

    # ---------------------------------------------------------- navegação
    def show_page(self, key):
        if key != "module":
            self.module.stop_live()
        if key == "history":
            self.hist.refresh()
        self.stack.setCurrentWidget(self.pages[key])
        self.nav_btns[key].setChecked(True)

    def _shortcuts(self):
        def on_module(fn):
            def run():
                if self.stack.currentWidget() is self.module and self.nav_btns["module"].isEnabled():
                    fn()
            return run
        keys = [
            ("F5", on_module(lambda: self.worker.submit("read_faults"))),
            ("F6", on_module(self.module._toggle_mvb)),
            ("Ctrl+R", lambda: self.export_report("auto")),
            ("Ctrl+1", lambda: self.show_page("home")),
            ("Ctrl+2", lambda: self.show_page("modules")),
            ("Ctrl+3", lambda: self.show_page("autoscan")),
            ("Ctrl+4", lambda: self.show_page("history")),
            ("Ctrl+L", lambda: self.log_dock.setVisible(not self.log_dock.isVisible())),
        ]
        self._sc = []
        for seq, fn in keys:
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(fn)
            self._sc.append(sc)

    def _reconnect(self):
        if self.last_address is not None:
            self.reconnect_btn.hide()
            self.connect_module(self.last_address)

    def _home_go(self, key):
        if key == "sim":
            self.options.select_simulator()
            self.show_page("modules")
            self.toast.show_msg("Simulador activo: experimente 01 Motor, 03 ABS ou 17 Painel", "info")
            return
        if key == "report":
            self.export_report("auto")
            return
        self.show_page(key)

    # -------------------------------------------------------- configuração
    def apply_config(self, cfg, quiet=False):
        self.worker.submit("configure", cfg)
        port = cfg["port"]
        if not port:
            self.home.set_port("Escolha a porta do cabo em Opções")
            self.conn_sub.setText("Interface por configurar")
        else:
            txt = "Simulador" if port == SIM_PORT else port
            self.home.set_port(f"Interface pronta: {txt}", ok=True)
            self.conn_sub.setText(f"Interface: {txt}")
        if not quiet:
            self.toast.show_msg("Opções guardadas")

    def connect_module(self, address):
        if not self.options.config()["port"]:
            QMessageBox.information(self, APP_NAME, "Escolha primeiro a porta do cabo em Opções.")
            self.show_page("options")
            return
        self.module.stop_live()
        self.worker.submit("connect", address)

    # ------------------------------------------------------------ relatório
    def _report_items(self, source):
        if source == "auto":
            source = "scan" if self.scan.items else "module"
        if source == "scan":
            return self.scan.items
        if self.module.info is None:
            return []
        return [{"address": self.module.info["address"], "module": self.module.info["module"],
                 "status": "ok", "info": self.module.info, "faults": self.module.faults}]

    def export_report(self, source):
        items = self._report_items(source)
        if not items:
            QMessageBox.information(self, APP_NAME, "Ainda não há dados para o relatório.\n"
                                    "Faça um Auto-Scan ou ligue a um controlador e leia as avarias.")
            return
        vehicle = self.home.vehicle()
        if not vehicle.get("plate"):
            plate, ok = QInputDialog.getText(self, APP_NAME, "Matrícula do veículo (opcional):")
            if ok and plate.strip():
                self.home.vehicle_edits["plate"].setText(plate.strip().upper())
                vehicle = self.home.vehicle()
        notes, ok = QInputDialog.getMultiLineText(self, APP_NAME, "Observações para o cliente (opcional):")
        if not ok:
            return
        if self._write_report(items, vehicle, notes):
            kind = "autoscan" if items is self.scan.items else "modulo"
            try:
                history.save_session(kind, vehicle, items, notes)
            except Exception as e:
                self.append_log(f"Histórico: não foi possível guardar ({e})")

    def export_session(self, data):
        self._write_report(data.get("items", []), data.get("vehicle", {}), data.get("notes", ""))

    def _write_report(self, items, vehicle, notes):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        name = f"Diagnostico_{vehicle.get('plate') or 'veiculo'}_{stamp}.pdf".replace(" ", "")
        path, _flt = QFileDialog.getSaveFileName(
            self, "Guardar relatório", os.path.join(os.path.expanduser("~"), name),
            "PDF (*.pdf);;Página web (*.html)")
        if not path:
            return False
        workshop = self.options.workshop()
        try:
            if path.lower().endswith(".html"):
                html = report.build_html(workshop, vehicle, items,
                                         report.logo_data_uri(asset_path("logo.png")), notes)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(html)
            else:
                if not path.lower().endswith(".pdf"):
                    path += ".pdf"
                from PySide6.QtPrintSupport import QPrinter
                html = report.build_html(workshop, vehicle, items, "logo.png", notes)
                doc = QTextDocument()
                doc.addResource(QTextDocument.ImageResource, QUrl("logo.png"), QImage(asset_path("logo.png")))
                doc.setHtml(html)
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setPageSize(QPageSize(QPageSize.A4))
                printer.setOutputFileName(path)
                doc.print_(printer)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Não foi possível gravar o relatório:\n{e}")
            return False
        self.toast.show_msg("Relatório guardado")
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        return True

    # ------------------------------------------------------------ sinais
    def append_log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log.appendPlainText(f"[{ts}] {msg}")
        self.disk_log.write(f"[{ts}] {msg}")

    def set_conn_state(self, state, text=None, sub=None):
        labels = {"disconnected": "Sem ligação", "connecting": "A ligar…", "connected": "Ligado"}
        colors = {"disconnected": MUTED, "connecting": WARN, "connected": OK}
        self.conn_lbl.setText(text or labels[state])
        self.conn_lbl.setStyleSheet(f"color: {colors[state]};")
        self.pulse.set_mode({"disconnected": "off", "connecting": "connecting", "connected": "on"}[state])
        if sub is not None:
            self.conn_sub.setText(sub)

    def on_state(self, state, data):
        if state == "connecting":
            self.set_conn_state("connecting", f"A ligar a {data:02X}…", vag_data.module_name(data))
            self.statusBar().showMessage(f"A ligar ao controlador {data:02X} — {vag_data.module_name(data)}…")
        elif state == "connected":
            self.last_address = data["address"]
            self.reconnect_btn.hide()
            self.set_conn_state("connected", f"Ligado a {data['address']:02X}",
                                f"{data['module']}\n{data['protocol']} · {data['baud']} baud")
            self.module.set_info(data)
            self.nav_btns["module"].setEnabled(True)
            self.show_page("module")
            self.statusBar().showMessage(f"Ligado a {data['address']:02X} — {data['part']} {data['component']}")
        else:
            port = self.options.config()["port"]
            self.set_conn_state("disconnected", None,
                                f"Interface: {'Simulador' if port == SIM_PORT else port or '—'}")
            self.module.stop_live()
            self.nav_btns["module"].setEnabled(False)
            if self.stack.currentWidget() is self.module:
                self.show_page("modules")
            self.statusBar().showMessage(f"Ligação terminada: {data}" if data else "Controlador fechado")
            if data:
                self.toast.show_msg("Ligação ao controlador perdida", "bad")
                if self.last_address is not None:
                    self.reconnect_btn.setText(f"Voltar a ligar a {self.last_address:02X}")
                    self.reconnect_btn.show()
            else:
                self.reconnect_btn.hide()

    def on_result(self, cmd, data):
        if cmd in ("read_faults", "clear_faults"):
            self.module.show_faults(data)
            if cmd == "clear_faults":
                self.toast.show_msg("Memória de avarias apagada" if not data
                                    else f"Apagado — {len(data)} avaria(s) voltaram a aparecer",
                                    "ok" if not data else "warn")
            else:
                self.toast.show_msg("Sem avarias" if not data else f"{len(data)} avaria(s) encontrada(s)",
                                    "ok" if not data else "warn")
        elif cmd in ("adaptation_read", "adaptation_test", "adaptation_save"):
            self.module.show_adaptation(cmd, data)
            if cmd == "adaptation_save":
                self.toast.show_msg("Adaptação gravada")
        elif cmd == "recode":
            self.module.set_info(data)
            self.module.tabs.setCurrentIndex(5)
            self.toast.show_msg("Codificação aceite pelo controlador")
        elif cmd == "login":
            self.toast.show_msg("Login aceite")
        elif cmd == "output_test":
            self.module.show_output(data)
        elif cmd == "test_interface":
            (QMessageBox.information if data["ok"] else QMessageBox.warning)(self, APP_NAME, data["message"])
        elif cmd == "autoscan":
            self.scan.done(data["aborted"])
            self.select.mark_scan(self.scan.items)
            if self.scan.items:
                try:
                    history.save_session("autoscan", self.home.vehicle(), self.scan.items)
                except Exception as e:
                    self.append_log(f"Histórico: não foi possível guardar ({e})")
            self.toast.show_msg("Auto-Scan concluído" if not data["aborted"] else "Auto-Scan interrompido",
                                "ok" if not data["aborted"] else "warn")

    def on_error(self, cmd, msg):
        self.append_log(f"ERRO ({cmd}): {msg}")
        self.statusBar().showMessage(msg, 8000)
        if cmd == "autoscan":
            self.scan.done(True)
        if cmd in ("connect", "test_interface", "recode", "login", "adaptation_save", "clear_faults",
                   "autoscan"):
            QMessageBox.warning(self, APP_NAME, msg)
        else:
            self.toast.show_msg(msg, "bad")

    def on_live(self, data):
        self.module.on_live(data)

    def on_scan_progress(self, i, total, item):
        self.scan.on_progress(i, total, item)
        self.statusBar().showMessage(f"Auto-Scan {i}/{total}: {item['address']:02X} {item['module']}")

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if getattr(self, "toast", None) is not None and self.toast.isVisible():
            par = self.toast.parentWidget()
            self.toast.move(par.width() - self.toast.width() - 24, par.height() - self.toast.height() - 24)

    def closeEvent(self, ev):
        self.module.stop_live()
        self.worker.submit("disconnect")
        self.worker.stop()
        super().closeEvent(ev)
