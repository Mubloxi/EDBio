"""Main application window."""

import os

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QAction, QPalette, QColor, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QStatusBar, QSystemTrayIcon, QMenu, QMessageBox,
    QFileDialog, QFrame,
)

from .exobiology_tab import ExobiologyTab
from .planets_tab import PlanetsTab
from .history_tab import HistoryTab
from .settings_dialog import SettingsDialog
from .about_dialog import AboutDialog
from ..journal import default_journal_dir
from ..config import APP_NAME, VERSION


ED_ORANGE = "#ff9900"
ED_DARK = "#2b2b2b"
ED_PANEL = "#353535"


class MainWindow(QMainWindow):
    def __init__(self, processor, journal_monitor, settings, icon_path=None):
        super().__init__()
        self.processor = processor
        self.monitor = journal_monitor
        self.settings = settings

        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(900, 560)
        self.icon_path = icon_path
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.last_event_time = "--:--:--"
        self._apply_palette()
        self._build_ui()
        self._connect_signals()

        # Restore geometry / tab.
        geo = self.settings.window_geometry()
        if geo:
            self.restoreGeometry(geo)
        state = self.settings.window_state()
        if state:
            self.restoreState(state)
        tab = self.settings.current_tab()
        self.tabs.setCurrentIndex(max(0, min(tab, self.tabs.count() - 1)))

        # Tray icon.
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip(APP_NAME)
        if self.icon_path and os.path.exists(self.icon_path):
            self.tray.setIcon(QIcon(self.icon_path))
        tray_menu = QMenu(self)
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_normal)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close_app)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)

        self.last_event_time = "--:--:--"
        self._event_timer = QTimer(self)
        self._event_timer.timeout.connect(self._refresh_status_text)
        self._event_timer.start(1000)

    def _apply_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(ED_DARK))
        palette.setColor(QPalette.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.Base, QColor(ED_PANEL))
        palette.setColor(QPalette.AlternateBase, QColor("#3c3c3c"))
        palette.setColor(QPalette.Text, QColor("#ffffff"))
        palette.setColor(QPalette.Button, QColor("#4a4a4a"))
        palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.Highlight, QColor(ED_ORANGE))
        palette.setColor(QPalette.HighlightedText, QColor("#000000"))
        self.setPalette(palette)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header: EDBio | Commander | System | Planet
        header = QFrame()
        header.setStyleSheet(f"QFrame {{ background-color: {ED_PANEL}; border: 1px solid #444; }}")
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(8, 4, 8, 4)

        self.lbl_app = QLabel(f"<b>{APP_NAME}</b>")
        self.lbl_app.setStyleSheet(f"color: {ED_ORANGE};")
        self.lbl_cmdr = QLabel("Commander: --")
        self.lbl_system = QLabel("System: --")
        self.lbl_planet = QLabel("Planet: --")
        for lbl in (self.lbl_cmdr, self.lbl_system, self.lbl_planet):
            lbl.setStyleSheet("color: #cccccc;")

        hlayout.addWidget(self.lbl_app)
        hlayout.addStretch()
        hlayout.addWidget(self.lbl_cmdr)
        hlayout.addWidget(QLabel("|"))
        hlayout.addWidget(self.lbl_system)
        hlayout.addWidget(QLabel("|"))
        hlayout.addWidget(self.lbl_planet)
        layout.addWidget(header)

        # Tabs.
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)

        self.tab_exo = ExobiologyTab(self.processor)
        self.tab_planets = PlanetsTab(self.processor)
        self.tab_history = HistoryTab(self.processor)

        self.tabs.addTab(self.tab_exo, "Exobiology")
        self.tabs.addTab(self.tab_planets, "Planets")
        self.tabs.addTab(self.tab_history, "History")
        layout.addWidget(self.tabs, 1)

        # Status bar.
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_lbl = QLabel("Journal: --  |  Game: --  |  Last Event: --:--:--")
        self.status.addWidget(self.status_lbl)
        self._refresh_status_text()

        # Menu bar.
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        act_choose_dir = QAction("&Journal Directory...", self)
        act_choose_dir.triggered.connect(self.choose_journal_dir)
        act_refresh = QAction("&Refresh", self)
        act_refresh.triggered.connect(self.refresh)
        act_export = QAction("&Export History CSV...", self)
        act_export.triggered.connect(self.export_history)
        act_exit = QAction("E&xit", self)
        act_exit.triggered.connect(self.close_app)
        for act in (act_choose_dir, act_refresh, act_export, act_exit):
            file_menu.addAction(act)

        view_menu = menubar.addMenu("&View")
        self.act_ontop = QAction("Always on &Top", self)
        self.act_ontop.setCheckable(True)
        self.act_ontop.setChecked(self.settings.always_on_top())
        self.act_ontop.toggled.connect(self.toggle_ontop)
        self.act_tray = QAction("Minimize to System &Tray", self)
        self.act_tray.setCheckable(True)
        self.act_tray.setChecked(self.settings.minimize_to_tray())
        view_menu.addAction(self.act_ontop)
        view_menu.addAction(self.act_tray)

        tools_menu = menubar.addMenu("&Tools")
        act_settings = QAction("&Settings...", self)
        act_settings.triggered.connect(self.open_settings)
        tools_menu.addAction(act_settings)

        help_menu = menubar.addMenu("&Help")
        act_about = QAction("&About", self)
        act_about.triggered.connect(self.open_about)
        help_menu.addAction(act_about)

    def _connect_signals(self):
        self.monitor.event_received.connect(self.processor.handle_event)
        self.monitor.status_changed.connect(self._on_status_changed)
        self.monitor.position_changed.connect(self._on_position_changed)
        self.monitor.error_occurred.connect(self._on_error)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.processor.on_planet_updated = self._on_planet_updated
        self.processor.on_sample_updated = self._on_sample_updated
        self.processor.on_history_added = self._on_history_added

    # --- header updates ---

    def _on_status_changed(self, status):
        self.lbl_cmdr.setText(f"Commander: {status.get('commander') or '--'}")
        self.lbl_system.setText(f"System: {status.get('system') or '--'}")
        self.lbl_planet.setText(f"Planet: {status.get('body') or '--'}")
        self.current_system = status.get("system")
        self.current_body = status.get("body")
        self.last_event_time = status.get("last_event_time", "--:--:--")
        self.processor.set_system(status.get("system"))
        # A missing BodyName in Status.json must not wipe the body that the
        # journal just told us about (Scan / SAASignalsFound / Touchdown).
        if status.get("body"):
            self.processor.set_body(status.get("body"))

        self.tab_exo.refresh()
        self.tab_planets.refresh()
        self.tab_history.refresh()

        self._refresh_status_text()

    def _refresh_status_text(self):
        journal_txt = "Connected" if self.monitor.journal_connected else "Disconnected"
        game_txt = "Running" if self.monitor.game_running else "Stopped"
        self.status_lbl.setText(
            f"Journal: {journal_txt}  |  Game: {game_txt}  |  Last Event: {self.last_event_time}"
        )

    def _on_position_changed(self, position):
        lat = position.get("lat")
        lon = position.get("lon")
        radius = position.get("radius")
        body = position.get("body")
        if body:
            self.processor.set_body(body)
            self.lbl_planet.setText(f"Planet: {body}")
        if lat is not None or lon is not None:
            self.processor.set_position(lat, lon)
        if radius is not None:
            self.processor.set_planet_radius(radius)
        self.tab_exo.refresh()

    def _on_planet_updated(self, planet):
        self.lbl_planet.setText(f"Planet: {planet.get('body_name') or '--'}")
        self.tab_exo.refresh()
        self.tab_planets.refresh()

    def _on_sample_updated(self, sample):
        self.tab_exo.refresh()

    def _on_history_added(self, record):
        self.tab_history.refresh()

    def _on_error(self, message):
        # Keep errors in the status bar, don't spam popups.
        self.status.showMessage(message, 5000)

    def _on_tab_changed(self, index):
        self.settings.set_current_tab(index)

    # --- actions ---

    def choose_journal_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Elite Dangerous journal folder",
                                                self.settings.journal_dir())
        if path:
            self.settings.set_journal_dir(path)
            self.monitor.set_journal_dir(path)
            self.status.showMessage(f"Journal directory set to {path}", 5000)

    def refresh(self):
        self.status.showMessage("Refresh requested", 3000)
        self.tab_exo.refresh()
        self.tab_planets.refresh()
        self.tab_history.refresh()

    def export_history(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export History to CSV",
                                              "edbio_history.csv", "CSV Files (*.csv)")
        if path:
            self.tab_history.export_csv(path)

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.act_ontop.setChecked(self.settings.always_on_top())
            self.act_tray.setChecked(self.settings.minimize_to_tray())
            self.toggle_ontop(self.settings.always_on_top())

    def open_about(self):
        AboutDialog(self).exec()

    def toggle_ontop(self, checked):
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def show_normal(self):
        self.showNormal()
        self.activateWindow()

    def close_app(self):
        self.tray.hide()
        self.close()

    def closeEvent(self, event):
        self.settings.set_window_geometry(self.saveGeometry())
        self.settings.set_window_state(self.saveState())
        if self.settings.minimize_to_tray() and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.show()
            self.tray.showMessage(APP_NAME, "EDBio is running in the system tray.", 3000)
        else:
            self.monitor.stop()
            event.accept()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and self.isMinimized() and \
           self.settings.minimize_to_tray():
            self.hide()
            self.tray.show()
