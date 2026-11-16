"""Embedded TypeScript database management surface."""

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from paths import resource_path
from ui.database_bridge import DatabaseBridge


class DatabasePanel(QWidget):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.view = QWebEngineView(self)
        self.bridge = DatabaseBridge(database, self)
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("databaseBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.view.setUrl(QUrl.fromLocalFile(resource_path("web/index.html")))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
