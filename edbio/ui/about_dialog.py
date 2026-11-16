"""About dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox,
)

from ..config import APP_NAME, VERSION


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.resize(420, 260)

        layout = QVBoxLayout(self)

        title = QLabel(f"<b>{APP_NAME}</b> v{VERSION}")
        title.setStyleSheet("color: #ff9900; font-size: 16px;")
        layout.addWidget(title)

        text = (
            "A small exobiology tool for Elite Dangerous. Reads the game journal "
            "to track biological samples, predict possible species, and show "
            "estimated Vista Genomics payouts.\n\n"
            "Built with Python, PySide6 and SQLite.\n\n"
            "EDBio is not affiliated with Frontier Developments.\n\n"
            "Third-party data and libraries are credited in README.md and LICENSE."
        )
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #cccccc;")
        layout.addWidget(lbl)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
