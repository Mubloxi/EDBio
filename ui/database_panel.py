

import json

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from paths import resource_path
from ui.database_bridge import DatabaseBridge


class DatabasePanel(QWidget):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._loaded = False
        self._loading = False
        self._theme = "classic"
        self.view = QWebEngineView(self)
        self.view.loadFinished.connect(self._on_load_finished)
        self.bridge = DatabaseBridge(database, self)
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("databaseBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def load(self):
        if self._loaded or self._loading:
            return
        self._loading = True
        self.view.setUrl(QUrl.fromLocalFile(resource_path("web/index.html")))

    def set_theme(self, theme):
        if theme not in ("classic", "oled"):
            raise ValueError(f"Unsupported theme: {theme}")
        self._theme = theme
        if self._loaded:
            self._apply_theme()

    def _on_load_finished(self, succeeded):
        self._loading = False
        self._loaded = succeeded
        if succeeded:
            self._apply_theme()

    def _apply_theme(self):
        theme = json.dumps(self._theme)
        self.view.page().runJavaScript(
            f"document.documentElement.dataset.theme = {theme};"
        )
