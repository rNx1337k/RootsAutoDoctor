"""Janela principal do Roots Auto Doctor."""
import datetime
import logging
import os

import threading

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import (QDesktopServices, QIcon, QImage, QKeySequence, QPageSize, QPixmap, QShortcut,
                           QTextDocument)
from PySide6.QtWidgets import (
    QButtonGroup, QDockWidget, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from .. import (APP_NAME, VERSION, applog, autoupdate, connstate, history, journal, licensing, report,
               technician_mode, vag_data)
from ..errors import client_text
from ..settings import app_settings
from ..kline import is_elm_sim_port, is_simulated_port, port_label
from ..worker import Worker
from .pages import (AutoScanPage, HistoryPage, HomePage, ModulePage, ModuleSelectPage,
                    ObdPage, OptionsPage, btn, lbl)
from .pages.common import FaultInfoDialog
from .palette import Command, CommandPalette
from .style import BAD, MUTED, OK, QSS, WARN, pill_style
from .widgets import LogoLabel, PulseIndicator, Toast, asset_path, nav_icon
from ..i18n import tr, tr_data

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    update_downloaded = Signal(object)        # resultado da descarga da versão nova (vem de uma thread à parte)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}")
        self.setWindowIcon(QIcon(asset_path("icon.ico")))
        self.resize(1320, 860)
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(QSS)
        self.settings = app_settings()
        self.module_faults = None
        self.disk_log = applog.DiskLog()

        self.worker = Worker()
        self.worker.log.connect(self.append_log)
        self.worker.state.connect(self.on_state)
        self.worker.result.connect(self.on_result)
        self.worker.error.connect(self.on_error)
        self.worker.live.connect(self.on_live)
        self.worker.scan_progress.connect(self.on_scan_progress)
        self.worker.link_state.connect(self.on_link_state)
        self._obd_conn = False

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
        sv.addSpacing(16)
        self.search_btn = btn(tr("  Procurar…"), "search", self.open_palette)
        self.search_btn.setIcon(nav_icon("search"))
        self.search_btn.setIconSize(QSize(18, 18))
        self.search_btn.setToolTip(tr("Procurar (Ctrl+K): páginas, controladores, acções e avarias"))
        sl = QHBoxLayout(self.search_btn)
        sl.setContentsMargins(0, 0, 10, 0)
        sl.addStretch(1)
        kb = lbl("Ctrl K", "kbd")
        kb.setAttribute(Qt.WA_TransparentForMouseEvents)
        sl.addWidget(kb)
        sv.addWidget(self.search_btn)
        sv.addSpacing(12)

        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        self.nav_btns = {}
        for key, text in [("home", tr("Início")), ("modules", tr("Controladores")),
                          ("module", tr("Controlador ligado")), ("autoscan", tr("Auto-Scan")),
                          ("obd", tr("OBD — todas as marcas")), ("history", tr("Histórico")),
                          ("options", tr("Opções"))]:
            b = btn(text, "nav", lambda _=False, k=key: self.show_page(k))
            b.setIcon(nav_icon(key))
            b.setIconSize(QSize(20, 20))
            b.setCheckable(True)
            self.nav.addButton(b)
            self.nav_btns[key] = b
            sv.addWidget(b)
        self.nav_btns["module"].setEnabled(False)
        sv.addStretch(1)
        self.ws_brand = lbl("", "muted")
        self.ws_brand.setAlignment(Qt.AlignCenter)
        self.ws_brand.setWordWrap(True)
        self.ws_brand.setMinimumHeight(10)
        sv.addWidget(self.ws_brand)
        sv.addSpacing(6)

        conn = QFrame()
        conn.setObjectName("card")
        cv = QVBoxLayout(conn)
        cv.setContentsMargins(12, 10, 12, 10)
        cv.setSpacing(4)
        self.conn_lbl = lbl(tr("Sem ligação"), "h2", wrap=True)
        self.conn_sub = lbl("", "muted")
        self.conn_sub.setWordWrap(True)
        self.pulse = PulseIndicator()
        # aviso permanente quando a porta escolhida é um simulador: os dados não vêm de nenhum carro
        self.sim_badge = lbl(tr("MODO DE SIMULAÇÃO"), "pill")
        self.sim_badge.setAlignment(Qt.AlignCenter)
        self.sim_badge.setStyleSheet(pill_style(WARN))
        self.sim_badge.setToolTip(tr("Está a usar o simulador: os valores e avarias são fictícios."))
        self.sim_badge.hide()
        cv.addWidget(self.sim_badge)
        self.demo_badge = QPushButton(tr("MODO DEMONSTRAÇÃO"))
        self.demo_badge.setObjectName("demoBadge")
        self.demo_badge.setStyleSheet(pill_style(BAD).replace("QLabel#pill", "QPushButton#demoBadge")
                                      + " QPushButton#demoBadge { border-radius: 10px; padding: 3px 10px; "
                                        "font-weight: 600; }")
        self.demo_badge.setCursor(Qt.PointingHandCursor)
        self.demo_badge.setToolTip(tr("Sem licença: lê tudo, mas não escreve em carros reais. Clique para activar."))
        self.demo_badge.clicked.connect(lambda: self.show_page("options"))
        self.demo_badge.hide()
        cv.addWidget(self.demo_badge)
        self.update_btn = btn(tr("Nova versão disponível"), "primary", self._open_update)
        self.update_btn.hide()
        cv.addWidget(self.update_btn)
        self.update_info = None
        cv.addWidget(self.conn_lbl)
        cv.addWidget(self.pulse)
        cv.addWidget(self.conn_sub)
        self.reconnect_btn = btn(tr("Voltar a ligar"), "primary", self._reconnect)
        self.reconnect_btn.hide()
        cv.addWidget(self.reconnect_btn)
        sv.addWidget(conn)
        ver = lbl(f"v{VERSION}", "muted")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color: #4A5880; font-size: 8.5pt;")
        sv.addSpacing(4)
        sv.addWidget(ver)
        self.last_address = None
        self.was_connected = False
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
        self.obd = ObdPage(self.worker)
        self.pages = {"home": self.home, "modules": self.select, "module": self.module,
                      "autoscan": self.scan, "obd": self.obd, "history": self.hist, "options": self.options}
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
        self.options.link_check_req.connect(self.run_link_check)
        self.options.hex_mode_req.connect(self.run_hex_mode)
        self.options.coverage_req.connect(self.show_coverage)          # botão só existe no modo técnico
        self.options.license_changed.connect(self.apply_license)
        self.options.update_found.connect(self.on_update_found)
        self.obd.report_req.connect(lambda: self.export_report("obd"))
        self.obd.vin_found.connect(self._vin_from_vehicle)

        # ---------------- registo de comunicação: só no modo técnico (--tecnico). Para o cliente fica apenas
        # no disco (pasta de registos / pacote de suporte).
        self.technical = technician_mode()
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(4000)
        dock = QDockWidget(tr("Registo de comunicação"), self)
        dock.setWidget(self.log)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.log_dock = dock
        if self.technical:
            self.addDockWidget(Qt.BottomDockWidgetArea, dock)
            self.resizeDocks([dock], [150], Qt.Vertical)
        # o registo técnico fica escondido por omissão; botão na barra de estado e Ctrl+L
        self.log_btn = btn(tr("Registo técnico"), None,
                           lambda: self.log_dock.setVisible(not self.log_dock.isVisible()))
        self.log_btn.setObjectName("statusBtn")
        self.log_btn.setCheckable(True)
        dock.visibilityChanged.connect(self.log_btn.setChecked)
        if self.technical:
            self.statusBar().addPermanentWidget(self.log_btn)
            dock.setVisible(self.settings.value("ui/log_visible", "false") == "true")
        else:
            self.log_btn.hide()
            dock.hide()
        self.menuBar().hide()

        self.toast = Toast(root)
        self.palette = CommandPalette(self, self._commands, self.show_fault)
        self._shortcuts()
        self.statusBar().showMessage(f"{APP_NAME} v{VERSION}")
        self.set_conn_state("disconnected")
        self.worker.start()
        self.apply_license()
        self.apply_config(self.options.config(), quiet=True)
        self.show_page("home")
        self._downloading = False
        self.update_downloaded.connect(self._update_downloaded)
        self._after_update()
        if self.options.auto_update_enabled() and not os.environ.get("RAD_NO_UPDATE_CHECK"):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(5000, self.options.check_updates)     # depois de a janela abrir

    # ---------------------------------------------------------- navegação
    def show_page(self, key):
        if key != "module":
            self.module.stop_live()
        if key != "obd":
            self.obd.stop_live()
        if key == "history":
            self.hist.refresh()
        if key == "home":
            self.home.refresh_stats()
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
            ("Ctrl+5", lambda: self.show_page("obd")),
            ("Ctrl+K", self.open_palette),
            ("Ctrl+P", self.open_palette),
        ]
        if self.technical:
            keys.append(("Ctrl+L", lambda: self.log_dock.setVisible(not self.log_dock.isVisible())))
        self._sc = []
        for seq, fn in keys:
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(fn)
            self._sc.append(sc)

    def apply_license(self):
        """Lê o estado da licença e passa-o à thread de comunicação (que bloqueia as escritas sem licença)."""
        try:
            self.license = licensing.status()
        except Exception as e:                     # nunca impedir o arranque por causa da licença
            log.warning("Estado da licença ilegível: %s", e)
            self.license = {"state": "demo", "licensed": False, "message": tr("Modo demonstração ({e}).", e=e)}
        self.worker.licensed = self.license["licensed"]
        self.demo_badge.setVisible(not self.license["licensed"])
        self.options.show_license(self.license)

    def _after_update(self):
        """Primeiro arranque depois de uma actualização automática: avisa e limpa a pasta de descargas."""
        try:
            version = autoupdate.after_start()
        except Exception:
            log.warning("Verificação pós-actualização falhou", exc_info=True)
            return
        if version:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.toast.show_msg(tr("Actualizado para a versão {version}",
                                                                   version=version)))

    def on_update_found(self, info):
        self.update_info = info
        if self.options.auto_update_enabled() and autoupdate.can_self_update() and info.get("signature"):
            self._download_update(info)
            return
        self.update_btn.setText(tr("Nova versão {version} disponível", version=info['version']))
        self.update_btn.setToolTip(tr("Abre a página da versão nova no navegador."))
        self.update_btn.show()
        self.toast.show_msg(tr("Está disponível a versão {version}", version=info['version']))

    def _download_update(self, info):
        """Descarrega a versão nova em segundo plano; instala-se quando o programa fechar."""
        if self._downloading:
            return
        self._downloading = True

        def run():
            try:
                res = autoupdate.download(info)
            except Exception as e:                      # UpdateError ou outro: nunca derrubar o programa
                log.warning("Actualização automática: %s", e)
                res = e
            try:
                self.update_downloaded.emit(res)
            except RuntimeError:                       # a janela já foi fechada
                pass
        threading.Thread(target=run, daemon=True, name="actualizacao").start()

    def _update_downloaded(self, res):
        self._downloading = False
        info = self.update_info or {}
        if isinstance(res, Exception):                 # falhou: fica o aviso normal, com a página de download
            self.update_btn.setText(tr("Nova versão {version} disponível", version=info.get('version', '?')))
            self.update_btn.setToolTip(tr("Abre a página da versão nova no navegador."))
            self.update_btn.show()
            return
        self.update_btn.setText(tr("Versão {version} pronta", version=res['version']))
        self.update_btn.setToolTip(tr("Instala-se sozinha quando fechar o programa."))
        self.update_btn.show()
        self.toast.show_msg(tr("Versão {version} descarregada: instala-se quando fechar o programa",
                               version=res['version']))

    def _open_update(self):
        if autoupdate.pending():
            QMessageBox.information(self, APP_NAME, tr("A versão nova já foi descarregada e verificada. Instala-se "
                                                       "sozinha quando fechar o programa; os diagnósticos, a "
                                                       "licença e as definições ficam guardados."))
            return
        info = self.update_info or {}
        notes = info.get("notes", "")
        text = (tr("Versão instalada: {VERSION}\nVersão nova: {v}\n\n", VERSION=VERSION, v=info.get('version', '?'))
                + (notes[:1200] + ("…" if len(notes) > 1200 else "") + "\n\n" if notes else "")
                + tr("Abrir a página para descarregar o instalador?"))
        if QMessageBox.question(self, APP_NAME, text) == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl(info.get("download") or info.get("url") or ""))

    def _reconnect(self):
        if self.last_address is not None:
            self.reconnect_btn.hide()
            self.connect_module(self.last_address)

    # ----------------------------------------------------- paleta de comandos
    def open_palette(self):
        self.palette.popup()

    def show_fault(self, fault, address=None):
        FaultInfoDialog(self, fault, address).exec()

    def _commands(self):
        c = [
            Command("Início", "Página inicial", lambda: self.show_page("home"), "home", "inicio pagina"),
            Command("Controladores", "Escolher um módulo para ligar", lambda: self.show_page("modules"), "modules",
                    "modulos seleccionar"),
            Command("Auto-Scan", "Ver o último Auto-Scan e o mapa do veículo", lambda: self.show_page("autoscan"),
                    "autoscan", "scan mapa"),
            Command("Iniciar Auto-Scan", "Ler todos os controladores agora", lambda: self._home_go("autoscan_start"),
                    "bolt", "scan comecar"),
            Command("OBD — todas as marcas", "Avarias, prontidão e dados de qualquer marca",
                    lambda: self.show_page("obd"), "obd", "obd eobd elm327 multimarca"),
            Command("Ligar por OBD", "Ligar ao veículo com o adaptador OBD", self._obd_connect, "obd",
                    "obd ligar elm"),
            Command("Abrir simulador OBD", "Experimentar o diagnóstico de todas as marcas sem carro",
                    lambda: self._home_go("sim_obd"), "sim", "demo obd elm simulador"),
            Command("Histórico", "Diagnósticos guardados", lambda: self.show_page("history"), "history",
                    "historico matricula"),
            Command("Opções", "Porta do cabo, oficina e suporte", lambda: self.show_page("options"), "options",
                    "definicoes porta cabo oficina"),
            Command("Relatório para o cliente", "PDF ou página web", lambda: self.export_report("auto"), "report",
                    "pdf imprimir"),
            Command("Abrir simulador", "Experimentar sem carro", lambda: self._home_go("sim"), "sim", "demo teste"),
            Command("Detectar cabo", "Encontrar o cabo ligado ao PC", self.options._detect_cable, "bolt",
                    "usb porta cabo"),
            Command("Diagnóstico da ligação", "Verificar o cabo e a ligação ao carro", self.run_link_check, "bolt",
                    "teste ligacao"),
        ]
        if self.technical:
            c.append(Command("Registo técnico", "Mostrar ou esconder (Ctrl+L)",
                             lambda: self.log_dock.setVisible(not self.log_dock.isVisible()), "log", "log debug"))
        if self.nav_btns["module"].isEnabled():
            c.insert(1, Command("Controlador ligado", self.module.title.text(), lambda: self.show_page("module"),
                                "module", "ligado"))
            c.insert(2, Command("Ler avarias", "Controlador ligado (F5)",
                                lambda: (self.show_page("module"), self.module._quick_faults()), "fault", "avarias"))
        for addr in sorted(vag_data.VAG_MODULES):
            name = vag_data.VAG_MODULES[addr]
            c.append(Command(tr("Ligar a {addr:02X} · {name}", addr=addr, name=tr_data(name)), "Controlador",
                             lambda a=addr: self.connect_module(a), "module", f"{addr:02x} ligar connect {name}"))
        return c

    def _home_go(self, key):
        if key == "palette":
            self.open_palette()
            return
        if key == "sim":
            self.options.select_simulator()
            self.show_page("modules")
            self.toast.show_msg(tr("Simulador activo: experimente 01 Motor, 03 ABS ou 17 Painel"), "info")
            return
        if key == "sim_obd":
            self.options.select_simulator("elm327")
            self.show_page("obd")
            self.toast.show_msg(tr("Simulador OBD activo — os dados são fictícios"), "info")
            return
        if key == "test_interface":
            self.options._test()
            return
        if key == "report":
            self.export_report("auto")
            return
        if key == "autoscan_start":
            if self._obd_sim_selected():
                self._explain_elm()
                return
            self.show_page("autoscan")
            if not self.options.config()["port"]:
                QMessageBox.information(self, APP_NAME, tr("Escolha primeiro a porta do cabo em Opções."))
                self.show_page("options")
                return
            if not self.scan.running:
                self.scan._toggle()
            return
        self.show_page(key)

    # -------------------------------------------------------- configuração
    def update_workshop_brand(self):
        """Mostra o logótipo (ou o nome) da oficina na barra lateral."""
        path = self.options.workshop_logo()
        name = self.options.workshop().get("name", "")
        if path:
            dpr = self.devicePixelRatioF() or 1.0
            pm = QPixmap(path)
            if not pm.isNull():
                pm = pm.scaled(int(200 * dpr), int(64 * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pm.setDevicePixelRatio(dpr)
                self.ws_brand.setPixmap(pm)
                self.ws_brand.setToolTip(name)
                return
        self.ws_brand.setPixmap(QPixmap())
        self.ws_brand.setText(name)

    def _elm_selected(self):
        c = self.options.config()
        return c.get("adapter") == "elm327" or is_elm_sim_port(c.get("port") or "")

    def _obd_sim_selected(self):
        """O simulador OBD só imita o diagnóstico de todas as marcas (não tem controladores VAG)."""
        return is_elm_sim_port(self.options.config().get("port") or "")

    def _explain_elm(self):
        QMessageBox.information(self, APP_NAME, tr(
            "O Simulador OBD só tem o diagnóstico de todas as marcas.\n\n"
            "Para experimentar os controladores e o Auto-Scan do Grupo VW, escolha em Opções o Simulador VAG "
            "ou o Simulador VAG por CAN."))
        self.show_page("obd")

    def _obd_connect(self):
        self.show_page("obd")
        self.obd._connect()

    def _vin_from_vehicle(self, vin):
        e = self.home.vehicle_edits["vin"]
        if not e.text().strip():
            e.setText(vin)
            self.toast.show_msg(tr("VIN lido do veículo: {vin}", vin=vin), "info")

    def show_coverage(self):
        """Matriz de compatibilidade (interfaces × protocolos, com o nível de prova): só no modo técnico."""
        from .pages.coverage import CoverageDialog
        CoverageDialog(self).exec()

    def apply_config(self, cfg, quiet=False):
        self.worker.submit("configure", cfg)
        self.update_workshop_brand()
        port = cfg["port"]
        sim = is_simulated_port(port)
        kind = tr("Adaptador OBD (todas as marcas)") if (cfg.get("adapter") == "elm327" or is_elm_sim_port(port)) \
            else tr("Cabo VAG")
        port_text = port_label(port) if port else tr("porta por escolher")
        self.home.set_interface(kind if sim else f"{kind} · {port_text}")
        self.obd.set_adapter_text(tr("Equipamento: {kind} · {port}", kind=kind, port=port_text))
        self.sim_badge.setVisible(sim)
        if not port:
            self.home.set_port(tr("Escolha a porta do cabo em Opções"))
            self.conn_sub.setText(tr("Cabo por configurar"))
        elif sim:
            self.home.set_port(tr("Modo de simulação — os dados não vêm de um carro"), ok=False)
            self.conn_sub.setText(tr("Simulador — sem carro"))
        else:
            # a porta está escolhida; só o Testar interface / Diagnóstico da ligação provam que comunica
            self.home.set_port(tr("Cabo escolhido: {port}", port=port_text), ok=True)
            self.conn_sub.setText(tr("Cabo: {port}", port=port_text))
        if not quiet:
            self.toast.show_msg(tr("Opções guardadas"))

    def connect_module(self, address):
        if self._obd_sim_selected():
            self._explain_elm()
            return
        if not self.options.config()["port"]:
            QMessageBox.information(self, APP_NAME, tr("Escolha primeiro a porta do cabo em Opções."))
            self.show_page("options")
            return
        if self.worker.is_busy or self.scan.running:
            self.toast.show_msg(tr("Aguarde — ainda a comunicar com o carro"), "warn")
            return
        self.module.stop_live()
        self.worker.submit("connect", address)

    def run_link_check(self):
        if self.worker.is_busy or self.scan.running:
            self.toast.show_msg(tr("Aguarde — ainda a comunicar com o carro"), "warn")
            return
        cfg = self.options.config()
        if not cfg["port"]:
            QMessageBox.information(self, APP_NAME, tr("Escolha primeiro a porta do cabo (ou use Detectar cabo)."))
            return
        if self._elm_selected():
            # com um ELM327, o diagnóstico da ligação é a própria ligação OBD-II, passo a passo
            self.options._save()
            self._obd_connect()
            return
        addr, ok = QInputDialog.getText(self, tr("Diagnóstico da ligação"),
                                        tr("Ligue o cabo ao carro com a ignição ligada.\n\n"
                                           "Módulo a testar (01 = motor, 17 = painel):"), text="01")
        if not ok:
            return
        try:
            a = int(addr.strip(), 16)
        except ValueError:
            QMessageBox.warning(self, APP_NAME, tr("Endereço inválido."))
            return
        self.options._save()
        self.toast.show_msg(tr("A verificar a ligação…"), "info")
        self.worker.submit("link_check", a)

    def run_hex_mode(self, mode):
        if self.worker.is_busy or self.scan.running:
            self.toast.show_msg(tr("Aguarde — ainda a comunicar com o carro"), "warn")
            return
        if mode == "smart" and QMessageBox.question(
                self, APP_NAME, tr("Vai repor o modo de arranque de origem (inteligente) do cabo. Continuar?")
        ) != QMessageBox.Yes:
            return
        self.toast.show_msg(tr("A falar com o cabo…"), "info")
        self.worker.submit("hex_mode", mode)

    def show_link_check(self, steps):
        for s in steps:
            self.append_log(f"{'OK' if s[1] else 'FALHOU'} — {s[0]}: {s[2]}")
        steps = [(s[0], s[1], client_text(s[2])) for s in steps]
        ok_all = steps and all(s[1] for s in steps)
        rows = "".join(f"<p><b style='color:{OK if s[1] else '#E8343A'}'>{'✔' if s[1] else '✖'}  {s[0]}</b>"
                       + (f"<br>{s[2]}" if s[2] else "") + "</p>" for s in steps)
        head = (tr("<p><b>Ligação OK — pode usar o programa no carro.</b></p>") if ok_all else
                tr("<p><b>A ligação falhou no passo assinalado.</b> Se não conseguir resolver, use "
                   "<i>Pacote de suporte</i> em Opções e envie o ficheiro.</p>"))
        box = QMessageBox(self)
        box.setWindowTitle(tr("Diagnóstico da ligação"))
        box.setTextFormat(Qt.RichText)
        box.setText(head + rows)
        box.exec()

    # ------------------------------------------------------------ relatório
    def _resolve_source(self, source):
        if source != "auto":
            return source
        if self.stack.currentWidget() is self.obd and self.obd.report_items():
            return "obd"
        return "scan" if self.scan.items else "module"

    def _report_items(self, source):
        source = self._resolve_source(source)
        if source == "obd":
            return self.obd.report_items()
        if source == "scan":
            return self.scan.items
        if self.module.info is None:
            return []
        return [{"address": self.module.info["address"], "module": self.module.info["module"],
                 "status": "ok", "info": self.module.info, "faults": self.module.faults}]

    def export_report(self, source):
        source = self._resolve_source(source)
        items = self._report_items(source)
        if not items:
            QMessageBox.information(self, APP_NAME, tr(
                "Ainda não há dados para o relatório.\n"
                "Faça um Auto-Scan ou ligue a um controlador e leia as avarias."))
            return
        vehicle = self.home.vehicle()
        if not vehicle.get("plate"):
            plate, ok = QInputDialog.getText(self, APP_NAME, tr("Matrícula do veículo (opcional):"))
            if ok and plate.strip():
                self.home.vehicle_edits["plate"].setText(plate.strip().upper())
                vehicle = self.home.vehicle()
        notes, ok = QInputDialog.getMultiLineText(self, APP_NAME, tr("Observações para o cliente (opcional):"))
        if not ok:
            return
        from_scan = source == "scan"
        from_obd = source == "obd"
        if from_scan:
            meta = dict(self.scan.meta)
        elif from_obd:
            oi = self.obd.info
            meta = {"interface": oi.get("interface", ""), "simulated": bool(oi.get("simulated")),
                    "protocol": oi.get("protocol"), "vin": oi.get("vin"), "kind": "obd"}
        else:
            info = self.module.info or {}
            meta = {"interface": info.get("interface", ""), "simulated": bool(info.get("simulated"))}
        if not from_obd:                  # o OBD-II só lê: não há escritas a mostrar
            try:
                meta["changes"] = journal.changes_for_visit(items, simulated=bool(meta.get("simulated")))
            except Exception as e:
                self.append_log(tr("Registo de alterações: não foi possível ler ({e})", e=e))
        if not self.license.get("licensed") and not meta.get("simulated"):
            meta["demo"] = True
        if not self._write_report(items, vehicle, notes, meta):
            return
        try:
            if from_scan and self.scan.session_id:
                # o Auto-Scan já ficou no histórico quando terminou: actualiza-o em vez de criar outro
                history.update_session(self.scan.session_id, vehicle, notes,
                                       meta={"changes": meta["changes"]} if meta.get("changes") else None)
            else:
                history.save_session("autoscan" if from_scan else ("obd" if from_obd else "modulo"), vehicle, items,
                                     notes, meta=meta)
        except Exception as e:
            self.append_log(tr("Histórico: não foi possível guardar ({e})", e=e))

    def export_session(self, data):
        self._write_report(data.get("items", []), data.get("vehicle", {}), data.get("notes", ""),
                           data.get("meta") or {}, data.get("date"))

    def _write_report(self, items, vehicle, notes, meta=None, date=None):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        name = f"Diagnostico_{vehicle.get('plate') or 'veiculo'}_{stamp}.pdf".replace(" ", "")
        path, _flt = QFileDialog.getSaveFileName(
            self, tr("Guardar relatório"), os.path.join(os.path.expanduser("~"), name),
            tr("PDF (*.pdf);;Página web (*.html)"))
        if not path:
            return False
        workshop = self.options.workshop()
        logo_path = self.options.workshop_logo() or asset_path("logo.png")
        logo_img = QImage(logo_path)
        if logo_img.isNull():
            logo_path, logo_img = asset_path("logo.png"), QImage(asset_path("logo.png"))
        lh = 64
        lw = max(1, min(220, round(logo_img.width() * lh / max(1, logo_img.height()))))
        logo_size = (lw, round(lw * logo_img.height() / max(1, logo_img.width())))
        try:
            if path.lower().endswith(".html"):
                html = report.build_html(workshop, vehicle, items,
                                         report.logo_data_uri(logo_path), notes, logo_size, meta, date)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(html)
            else:
                if not path.lower().endswith(".pdf"):
                    path += ".pdf"
                from PySide6.QtPrintSupport import QPrinter
                html = report.build_html(workshop, vehicle, items, "logo.png", notes, logo_size, meta, date)
                doc = QTextDocument()
                doc.addResource(QTextDocument.ImageResource, QUrl("logo.png"), logo_img)
                doc.setHtml(html)
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setPageSize(QPageSize(QPageSize.A4))
                printer.setOutputFileName(path)
                doc.print_(printer)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível gravar o relatório:\n{e}", e=e))
            return False
        self.toast.show_msg(tr("Relatório guardado"))
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        return True

    # ------------------------------------------------------------ sinais
    def append_log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        bar = self.log.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 4
        self.log.appendPlainText(f"[{ts}] {msg}")
        if at_end:
            bar.setValue(bar.maximum())
        self.disk_log.write(f"[{ts}] {msg}")

    def set_conn_state(self, state, text=None, sub=None):
        labels = {"disconnected": tr("Sem ligação"), "connecting": tr("A ligar…"), "connected": tr("Ligado")}
        colors = {"disconnected": MUTED, "connecting": WARN, "connected": OK}
        self.conn_lbl.setText(text or labels[state])
        self.conn_lbl.setStyleSheet(f"color: {colors[state]};")
        self.pulse.set_mode({"disconnected": "off", "connecting": "connecting", "connected": "on"}[state])
        if sub is not None:
            self.conn_sub.setText(sub)

    def on_state(self, state, data):
        if state == "connecting":
            self.was_connected = False
            self.set_conn_state("connecting", tr("A ligar a {data:02X}…", data=data), vag_data.module_name(data))
            self.statusBar().showMessage(tr("A ligar ao controlador {data:02X} — {v}…",
                                            data=data, v=vag_data.module_name(data)))
        elif state == "connected":
            self.was_connected = True
            self.last_address = data["address"]
            self.reconnect_btn.hide()
            sim = tr(" (simulação)") if data.get("simulated") else ""
            self.set_conn_state("connected", tr("Ligado a {address:02X}{sim}", address=data['address'], sim=sim),
                                data['module'])
            self.module.set_info(data)
            self.nav_btns["module"].setEnabled(True)
            self.show_page("module")
            self.statusBar().showMessage(tr("Ligado a {address:02X} — {part} {component}",
                                            address=data['address'], part=data['part'], component=data['component']))
        else:
            self.set_conn_state("disconnected", None, self._port_text())
            self.module.stop_live()
            self.nav_btns["module"].setEnabled(False)
            if self.stack.currentWidget() is self.module:
                self.show_page("modules")
            self.statusBar().showMessage(tr("Ligação terminada: {data}", data=client_text(data)) if data
                                         else tr("Controlador fechado"))
            lost = bool(data) and self.was_connected     # uma ligação que falhou à primeira não se "perdeu"
            self.was_connected = False
            if lost:
                self.toast.show_msg(tr("Ligação ao controlador perdida"), "bad")
                if self.last_address is not None:
                    self.reconnect_btn.setText(tr("Voltar a ligar a {last_address:02X}",
                                                  last_address=self.last_address))
                    self.reconnect_btn.show()
            else:
                self.reconnect_btn.hide()

    def on_result(self, cmd, data):
        if cmd.startswith("obd_"):
            return self._on_obd_result(cmd, data)
        if cmd in ("read_faults", "clear_faults"):
            self.module.show_faults(data)
            if cmd == "clear_faults":
                self.toast.show_msg(tr("Memória de avarias apagada") if not data
                                    else tr("Apagado — {v} avaria(s) voltaram a aparecer", v=len(data)),
                                    "ok" if not data else "warn")
            else:
                self.toast.show_msg(tr("Sem avarias") if not data else tr("{v} avaria(s) encontrada(s)", v=len(data)),
                                    "ok" if not data else "warn")
        elif cmd in ("adaptation_read", "adaptation_test", "adaptation_save", "service_reset"):
            self.module.show_adaptation(cmd, data)
            if cmd in ("adaptation_save", "service_reset"):
                self.module.refresh_changes()
                if data.get("status") == "ok":
                    self.toast.show_msg(tr("Revisão reposta — confirmado pelo painel") if cmd == "service_reset"
                                        else tr("Adaptação gravada — confirmada pelo controlador"))
                else:
                    QMessageBox.warning(self, APP_NAME, data.get("message", "Resultado desconhecido."))
        elif cmd == "recode":
            self.module.set_info(data["info"])
            self.module.tabs.setCurrentIndex(5)
            if data["status"] == "ok":
                self.toast.show_msg(data["message"])
            else:
                QMessageBox.warning(self, APP_NAME, data["message"])
        elif cmd == "login":
            QMessageBox.information(self, APP_NAME, data["message"])
        elif cmd == "clear_all":
            left, errs, unknown = self.scan.apply_clear_results(data)
            self.select.mark_scan(self.scan.items)
            if unknown:
                QMessageBox.warning(self, APP_NAME, tr("Em {unknown} controlador(es) o pedido de apagar foi enviado "
                                                       "mas não foi possível confirmar o resultado. Volte a fazer o "
                                                       "Auto-Scan para ver o estado real.",
                                                       unknown=unknown))
            self.toast.show_msg(tr("Avarias apagadas em todos os controladores") if not (left or errs or unknown)
                                else tr("Feito — {left} avaria(s) voltaram a aparecer", left=left)
                                + (tr(", {v} controlador(es) por confirmar",
                                      v=errs + unknown) if errs or unknown else ""),
                                "ok" if not (left or errs or unknown) else "warn")
        elif cmd == "link_check":
            self.show_link_check(data)
        elif cmd == "output_test":
            self.module.show_output(data)
        elif cmd in ("test_interface", "hex_mode"):
            self.append_log(data["message"])
            (QMessageBox.information if data["ok"] else QMessageBox.warning)(self, APP_NAME,
                                                                             client_text(data["message"]))
        elif cmd == "autoscan":
            self.scan.meta = {k: data.get(k) for k in ("aborted", "scanned", "total", "interface", "simulated")}
            self.scan.done(data["aborted"])
            self.select.mark_scan(self.scan.items)
            if self.scan.items:
                try:
                    vehicle = self.home.vehicle()
                    sid = history.save_session("autoscan", vehicle, self.scan.items, meta=self.scan.meta)
                    self.scan.session_id = sid
                    prev = history.previous_for_plate(vehicle.get("plate"), before=sid)
                    if prev is not None:
                        self.scan.show_compare(prev["date"], history.compare(prev.get("items", []), self.scan.items))
                except Exception as e:
                    self.append_log(tr("Histórico: não foi possível guardar ({e})", e=e))
            if data.get("interface_error"):
                log.warning("Auto-Scan parado pela interface: %s", data['interface_error'])
                QMessageBox.warning(self, APP_NAME, tr("O Auto-Scan parou porque o cabo deixou de responder "
                                                       "(desligado do USB ou bloqueado). Os controladores "
                                                       "já lidos ficaram guardados.\n\nDesligue o cabo do USB, "
                                                       "volte a ligá-lo e repita o Auto-Scan."))
            self.statusBar().showMessage(tr("Auto-Scan concluído") if not data["aborted"] else tr("Auto-Scan "
                                                                                                  "interrompido"))
            self.toast.show_msg(tr("Auto-Scan concluído") if not data["aborted"] else tr("Auto-Scan interrompido"),
                                "ok" if not data["aborted"] else "warn")

    def _on_obd_result(self, cmd, data):
        o = self.obd
        if cmd == "obd_connect":
            o.on_connected(data)
            self.statusBar().showMessage(tr("Ligado ao veículo por OBD"))
            self.toast.show_msg(tr("Ligado ao veículo por OBD")
                                + (tr(" (simulação)") if data.get("simulated") else ""))
        elif cmd == "obd_steps":
            o.show_steps(data)
        elif cmd == "obd_dtcs":
            o.on_dtcs(data)
            n = sum(len(data.get(k, [])) for k in ("stored", "pending", "permanent"))
            self.toast.show_msg(tr("Sem avarias") if not n else tr("{n} avaria(s) encontrada(s)",
                                                                   n=n), "ok" if not n else "warn")
        elif cmd == "obd_clear":
            o.on_clear(data)
            left = len(data["after"].get("stored", [])) + len(data["after"].get("pending", []))
            self.toast.show_msg(tr("Avarias apagadas — confirmado pela releitura") if not left else
                                tr("Pedido aceite, mas {left} avaria(s) continuam na memória",
                                   left=left), "ok" if not left else "warn")
        elif cmd == "obd_freeze":
            o.on_freeze(data)
        elif cmd == "obd_uds":
            o.on_uds(data)
        elif cmd == "obd_lost":
            o.on_lost(data)
            self.toast.show_msg(tr("Ligação ao veículo perdida"), "bad")
        elif cmd == "obd_disconnect":
            o.on_disconnected()

    def on_link_state(self, st):
        """Estado detalhado (connstate) — a fonte de verdade do centro de ligação e da barra lateral em OBD-II.
        Na barra lateral, as ligações VAG continuam a ser tratadas por on_state."""
        self.home.set_link(st)
        data = st.data if isinstance(st.data, dict) else None
        if st.state == connstate.ECU_CONNECTED and data and data.get("kind") == "obd":
            self._obd_conn = True
            self.set_conn_state("connected", tr("Ligado por OBD"),
                                tr("{v} centralina(s)", v=len(data.get('ecus', []))))
        elif st.state == connstate.CONNECTING and st.data is None:          # ligação OBD-II a começar
            self._obd_conn = True
            self.set_conn_state("connecting", tr("A ligar por OBD…"), "")
        elif self._obd_conn:
            self._obd_conn = False
            self.set_conn_state("disconnected", None, self._port_text())

    def _port_text(self):
        port = self.options.config()["port"]
        if not port:
            return tr("Cabo por configurar")
        return tr("Simulador — sem carro") if is_simulated_port(port) else tr("Cabo: {port}", port=port_label(port))

    def on_error(self, cmd, msg):
        self.append_log(tr("ERRO ({cmd}): {msg}", cmd=cmd, msg=msg))
        msg = client_text(msg)
        self.statusBar().showMessage(msg, 8000)
        if cmd.startswith("obd_"):
            self.obd.on_error(cmd, msg)
            if cmd in ("obd_connect", "obd_clear") or msg == licensing.demo_block_message():
                QMessageBox.warning(self, APP_NAME, msg)
            elif cmd != "obd_uds":
                self.toast.show_msg(msg, "bad")
            return
        if cmd == "autoscan":
            self.scan.done(True, msg)
        if cmd == "clear_all":
            self.scan.clear_all_btn.setEnabled(True)
        if cmd == "output_test":
            self.module._out_running = False          # o próximo início volta a pedir confirmação
        if msg == licensing.demo_block_message() or cmd in (
                "connect", "test_interface", "hex_mode", "recode", "login", "adaptation_save", "clear_faults",
                "autoscan", "service_reset", "adaptation_test"):
            QMessageBox.warning(self, APP_NAME, msg)
        else:
            self.toast.show_msg(msg, "bad")

    def on_live(self, data):
        if data.get("mode") == "obd":
            self.obd.on_live(data)
            return
        self.module.on_live(data)

    def on_scan_progress(self, i, total, item):
        self.scan.on_progress(i, total, item)
        self.statusBar().showMessage(tr("Auto-Scan {i}/{total}: {address:02X} {module}",
                                        i=i, total=total, address=item['address'], module=item['module']))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if getattr(self, "toast", None) is not None and self.toast.isVisible():
            par = self.toast.parentWidget()
            self.toast.move(par.width() - self.toast.width() - 24, par.height() - self.toast.height() - 24)

    def closeEvent(self, ev):
        if self.technical:
            self.settings.setValue("ui/log_visible", "true" if self.log_dock.isVisible() else "false")
        self.settings.setValue("ui/geometry", self.saveGeometry())
        self.module.stop_live()
        self.obd.stop_live()
        self.worker.submit("disconnect")
        self.worker.stop()
        if autoupdate.can_self_update():
            try:
                autoupdate.install_pending()           # corre o instalador em silêncio depois de fechar
            except Exception:
                log.exception("Não foi possível instalar a actualização ao fechar")
        super().closeEvent(ev)
