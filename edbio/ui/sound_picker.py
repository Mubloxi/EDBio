"""Reusable grouped sound selector and first-run audio prompt."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout,
)

from ..audio import available_sounds


def populate_sound_combo(combo, selected_path):
    sounds = available_sounds()
    model = QStandardItemModel(combo)
    current_category = None

    for sound in sounds:
        if sound["category"] != current_category:
            current_category = sound["category"]
            header = QStandardItem(current_category)
            header.setFlags(Qt.ItemIsEnabled)
            model.appendRow(header)

        item = QStandardItem(sound["name"])
        item.setData(sound["path"], Qt.UserRole)
        model.appendRow(item)

    combo.setModel(model)
    index = combo.findData(selected_path, Qt.UserRole)
    if index >= 0:
        combo.setCurrentIndex(index)
    elif sounds:
        combo.setCurrentIndex(1)
    return bool(sounds)


class FirstRunDialog(QDialog):
    def __init__(self, selected_path, preview_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to EDBio")
        self.setMinimumWidth(440)
        self.preview_callback = preview_callback

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Choose the sound EDBio plays when an FSS scan finds biological signals. "
            "Use Preview to hear your selection."
        ))

        self.sound_combo = QComboBox()
        has_sounds = populate_sound_combo(self.sound_combo, selected_path)
        layout.addWidget(self.sound_combo)

        self.message = QLabel(
            "The in-game overlay requires Elite Dangerous to run in Borderless or Windowed mode."
        )
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        if not has_sounds:
            self.message.setText("No bundled MP3 files were found. Reinstall EDBio to restore sound effects.")

        preview_row = QHBoxLayout()
        preview_row.addStretch()
        self.preview_button = QPushButton("Preview")
        self.preview_button.setEnabled(has_sounds)
        self.preview_button.clicked.connect(self._preview)
        preview_row.addWidget(self.preview_button)
        layout.addLayout(preview_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Start EDBio")
        buttons.button(QDialogButtonBox.Cancel).setText("Later")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_path(self):
        return self.sound_combo.currentData(Qt.UserRole)

    def _preview(self):
        path = self.selected_path()
        if path:
            self.preview_callback(path)
