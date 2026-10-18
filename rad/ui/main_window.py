"""Janela principal do Roots Auto Doctor."""
import datetime

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QButtonGroup, QDockWidget, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPlainTextEdit, QStackedWidget, QVBoxLayout, QWidget,
)

from .. import APP_NAME, VERSION, vag_data
from ..kline import SIM_PORT
from ..worker import Worker
from .pages import (AutoScanPage, HomePage, ModulePage, ModuleSelectPage, OptionsPage,
                    btn, lbl)
from .style import ACCENT, BAD, OK, QSS, WARN


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1280, 820)
        self.setStyleSheet(QSS)
        self.settings = QSettings("Roots", "RootsAutoDoctor")

        self.worker = Worker()
        self.worker.log.connect(self.append_log)
        self.worker.state.connect(self.on_state)
        self.worker.result.connect(self.on_result)
        self.worker.error.connect(self.on_error)
        self.worker.live.connect(self.on_live)
        self.worker.scan_progress.connect(self.on_scan_progress)
        self.worker.busy.connect(self.on_busy)

        root = QWidget()
        root.setObjectName("root")
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.setCentralWidget(root)

        # ---------------- barra lateral
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(230)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(14, 20, 14, 16)
        sv.setSpacing(6)
        sv.addWidget(lbl("ROOTS", "brand"))
        sv.addWidget(lbl("AUTO  DOCTOR", "brandSub"))
        sv.addSpacing(22)
        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        self.nav_btns = {}
        for key, text in [("home", "🏠   Início"), ("modules", "🔌   Controladores"),
                          ("module", "🧩   Módulo ligado"), ("autoscan", "🔍   Auto-Scan"),
                          ("options", "⚙️   Opções")]:
            b = btn(text, "nav", lambda _=False, k=key: self.show_page(k))
            b.setCheckable(True)
            self.nav.addButton(b)
            self.nav_btns[key] = b
            sv.addWidget(b)
        self.nav_btns["module"].setEnabled(False)
        sv.addStretch(1)
        self.conn_pill = lbl("●  Desligado", "pill")
        sv.addWidget(self.conn_pill)
        self.port_lbl = lbl("", "muted")
        self.port_lbl.setWordWrap(True)
        sv.addWidget(self.port_lbl)
        h.addWidget(side)

        # ---------------- páginas
        self.stack = QStackedWidget()
        h.addWidget(self.stack, 1)
        self.home = HomePage()
        self.select = ModuleSelectPage()
        self.module = ModulePage(self.worker)
        self.scan = AutoScanPage(self.worker)
        self.options = OptionsPage(self.settings)
        self.pages = {"home": self.home, "modules": self.select, "module": self.module,
                      "autoscan": self.scan, "options": self.options}
        for p in self.pages.values():
            self.stack.addWidget(p)

        self.home.go.connect(self._home_go)
        self.select.connect_req.connect(self.connect_module)
        self.options.saved.connect(self.apply_config)
        self.options.test_req.connect(lambda: self.worker.submit("test_interface"))

        # ---------------- log
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(4000)
        dock = QDockWidget("Registo de comunicação", self)
        dock.setWidget(self.log)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self.log_dock = dock
        self.resizeDocks([dock], [170], Qt.Vertical)

        self.statusBar().showMessage("Pronto")
        self.set_conn_state("disconnected")
        self.worker.start()
        self.apply_config(self.options.config(), quiet=True)
        self.show_page("home")

    # ---------------------------------------------------------- navegação
    def show_page(self, key):
        if key != "module":
            self.module.stop_live()
        self.stack.setCurrentWidget(self.pages[key])
        self.nav_btns[key].setChecked(True)

    def _home_go(self, key):
        if key == "sim":
            self.options.select_simulator()
            self.show_page("modules")
            self.append_log("Modo simulador: experimente os endereços 01 (motor), 03 (ABS) e 17 (painel).")
            return
        self.show_page(key)

    # -------------------------------------------------------- configuração
    def apply_config(self, cfg, quiet=False):
        self.worker.submit("configure", cfg)
        port = cfg["port"] or "—"
        txt = "Simulador" if port == SIM_PORT else port
        self.port_lbl.setText(f"Interface: {txt}")
        self.home.set_port(f"Interface: {txt}   ·   velocidade {cfg['baud']}   ·   eco {cfg['echo']}")
        if not quiet:
            self.statusBar().showMessage("Opções guardadas", 3000)

    def connect_module(self, address):
        if not self.options.config()["port"]:
            QMessageBox.information(self, APP_NAME, "Escolha primeiro a porta do cabo nas Opções.")
            self.show_page("options")
            return
        self.module.stop_live()
        self.worker.submit("connect", address)

    # ------------------------------------------------------------ sinais
    def append_log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log.appendPlainText(f"[{ts}] {msg}")

    def set_conn_state(self, state, text=None):
        colors = {"disconnected": "#3a4250", "connecting": WARN, "connected": OK}
        labels = {"disconnected": "●  Desligado", "connecting": "●  A ligar…", "connected": "●  Ligado"}
        c = colors[state]
        self.conn_pill.setText(text or labels[state])
        fg = "#0d0f13" if state != "disconnected" else "#c4c9d2"
        self.conn_pill.setStyleSheet(f"background: {c}; color: {fg}; border-radius: 10px; padding: 6px 10px; font-weight: 700;")

    def on_state(self, state, data):
        if state == "connecting":
            self.set_conn_state("connecting", f"●  A ligar a {data:02X}…")
            self.statusBar().showMessage(f"A ligar ao controlador {data:02X} — {vag_data.module_name(data)}…")
        elif state == "connected":
            self.set_conn_state("connected", f"●  Ligado: {data['address']:02X}")
            self.module.set_info(data)
            self.nav_btns["module"].setEnabled(True)
            self.show_page("module")
            self.statusBar().showMessage(f"Ligado a {data['address']:02X} ({data['protocol']} @ {data['baud']})")
        else:
            self.set_conn_state("disconnected")
            self.module.stop_live()
            self.nav_btns["module"].setEnabled(False)
            if self.stack.currentWidget() is self.module:
                self.show_page("modules")
            if data:
                self.statusBar().showMessage(f"Desligado: {data}")
            else:
                self.statusBar().showMessage("Controlador fechado")

    def on_busy(self, busy):
        if busy:
            self.statusBar().showMessage("A comunicar…")

    def on_result(self, cmd, data):
        if cmd in ("read_faults", "clear_faults"):
            self.module.show_faults(data)
            self.statusBar().showMessage("Avarias lidas" if cmd == "read_faults" else "Memória de avarias apagada", 4000)
        elif cmd in ("adaptation_read", "adaptation_test", "adaptation_save"):
            self.module.show_adaptation(cmd, data)
        elif cmd == "recode":
            self.module.set_info(data)
            self.module.tabs.setCurrentIndex(5)
            QMessageBox.information(self, APP_NAME, "Codificação aceite pelo controlador.")
        elif cmd == "login":
            QMessageBox.information(self, APP_NAME, "Login aceite.")
        elif cmd == "output_test":
            self.module.show_output(data)
        elif cmd == "test_interface":
            (QMessageBox.information if data["ok"] else QMessageBox.warning)(self, APP_NAME, data["message"])
        elif cmd == "autoscan":
            self.scan.done(data["aborted"])
            self.statusBar().showMessage("Auto-Scan terminado", 5000)
        else:
            self.statusBar().showMessage(f"{cmd}: OK", 3000)

    def on_error(self, cmd, msg):
        self.append_log(f"ERRO ({cmd}): {msg}")
        self.statusBar().showMessage(msg, 8000)
        if cmd == "autoscan":
            self.scan.done(True)
        if cmd in ("connect", "test_interface", "recode", "login", "adaptation_save", "clear_faults",
                   "autoscan", "adaptation_read", "adaptation_test", "output_test"):
            QMessageBox.warning(self, APP_NAME, msg)

    def on_live(self, data):
        self.module.on_live(data)

    def on_scan_progress(self, i, total, item):
        self.scan.on_progress(i, total, item)
        self.statusBar().showMessage(f"Auto-Scan {i}/{total}: {item['address']:02X} {item['module']}")

    def closeEvent(self, ev):
        self.module.stop_live()
        self.worker.submit("disconnect")
        self.worker.stop()
        super().closeEvent(ev)
