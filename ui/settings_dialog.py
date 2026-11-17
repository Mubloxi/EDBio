"""Settings dialog."""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QLabel,
    QDialogButtonBox, QGroupBox, QMessageBox,
)

from audio import import_custom_sound
from ui.sound_picker import populate_sound_combo


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None, preview_callback=None):
        super().__init__(parent)
        self.settings = settings
        self.preview_callback = preview_callback
        self.setWindowTitle("Settings")
        self.resize(480, 470)

        layout = QVBoxLayout(self)

        journal = QGroupBox("Journal Directory")
        jform = QFormLayout(journal)
        self.journal_edit = QLabel(self.settings.journal_dir())
        self.journal_edit.setStyleSheet("color: #cccccc;")
        btn_choose = QPushButton("Choose...")
        btn_choose.clicked.connect(self._choose_dir)
        jrow = QHBoxLayout()
        jrow.addWidget(self.journal_edit, 1)
        jrow.addWidget(btn_choose)
        jform.addRow("Folder:", jrow)
        layout.addWidget(journal)

        behavior = QGroupBox("Behavior")
        bform = QFormLayout(behavior)
        self.ck_ontop = QCheckBox("Always on top")
        self.ck_ontop.setChecked(self.settings.always_on_top())
        self.ck_tray = QCheckBox("Minimize to system tray")
        self.ck_tray.setChecked(self.settings.minimize_to_tray())
        self.ck_notify = QCheckBox("Notify on valuable planets")
        self.ck_notify.setChecked(self.settings.notify_valuable())
        bform.addRow(self.ck_ontop)
        bform.addRow(self.ck_tray)
        bform.addRow(self.ck_notify)
        layout.addWidget(behavior)

        alerts = QGroupBox("Biological-signal alerts")
        aform = QFormLayout(alerts)
        self.ck_sound = QCheckBox("Play sound when FSS finds biological signals")
        self.ck_sound.setChecked(self.settings.sound_enabled())
        self.sound_combo = QComboBox()
        has_sounds = populate_sound_combo(self.sound_combo, self.settings.selected_sound())
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setEnabled(has_sounds and preview_callback is not None)
        self.btn_preview.clicked.connect(self._preview_sound)
        self.btn_add_sound = QPushButton("Add custom sound...")
        self.btn_add_sound.clicked.connect(self._add_custom_sound)
        sound_row = QHBoxLayout()
        sound_row.addWidget(self.sound_combo, 1)
        sound_row.addWidget(self.btn_preview)
        aform.addRow(self.ck_sound)
        aform.addRow("Sound:", sound_row)
        aform.addRow(self.btn_add_sound)
        self.lbl_sound_status = QLabel()
        self.lbl_sound_status.setWordWrap(True)
        aform.addRow(self.lbl_sound_status)
        self.ck_overlay = QCheckBox("Show the bio overlay in Elite Dangerous")
        self.ck_overlay.setChecked(self.settings.overlay_enabled())
        aform.addRow(self.ck_overlay)
        self.combo_vista_radius = QComboBox()
        for radius in (25, 50, 100, 250, 500, 1000):
            self.combo_vista_radius.addItem(f"{radius} ly", radius)
        current_radius = self.combo_vista_radius.findData(
            self.settings.vista_search_radius()
        )
        self.combo_vista_radius.setCurrentIndex(max(0, current_radius))
        aform.addRow("Station search radius:", self.combo_vista_radius)
        overlay_note = QLabel(
            "The overlay appears only while the game is active. Set the game to "
            "Borderless or Windowed mode."
        )
        overlay_note.setWordWrap(True)
        aform.addRow(overlay_note)
        layout.addWidget(alerts)

        threshold = QGroupBox("Valuable Planet Threshold")
        tform = QFormLayout(threshold)
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0, 1000000000)
        self.spin_threshold.setDecimals(0)
        self.spin_threshold.setValue(self.settings.min_value_threshold())
        self.spin_threshold.setSuffix(" CR")
        tform.addRow("Highlight planets worth at least:", self.spin_threshold)
        layout.addWidget(threshold)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select journal folder",
                                                self.settings.journal_dir())
        if path:
            self.journal_edit.setText(path)

    def _preview_sound(self):
        path = self.sound_combo.currentData()
        if path and self.preview_callback:
            if self.preview_callback(path) is False:
                self.lbl_sound_status.setText("Could not start preview. Check the file and audio output.")
            else:
                self.lbl_sound_status.setText("Playing sound preview...")

    def _add_custom_sound(self):
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Add a custom sound",
            "",
            "Audio files (*.mp3 *.wav *.ogg);;All files (*.*)",
        )
        if not source:
            return
        try:
            selected = import_custom_sound(source)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Could not add sound", str(exc))
            return

        populate_sound_combo(self.sound_combo, selected)
        self.lbl_sound_status.setText(f"Added custom sound: {os.path.basename(source)}")
        self.btn_preview.setEnabled(self.preview_callback is not None)

    def set_preview_error(self, message):
        self.lbl_sound_status.setText(f"Sound preview failed: {message}")

    def accept(self):
        self.settings.set_journal_dir(self.journal_edit.text())
        self.settings.set_always_on_top(self.ck_ontop.isChecked())
        self.settings.set_minimize_to_tray(self.ck_tray.isChecked())
        self.settings.set_notify_valuable(self.ck_notify.isChecked())
        self.settings.set_sound_enabled(self.ck_sound.isChecked())
        self.settings.set_overlay_enabled(self.ck_overlay.isChecked())
        self.settings.set_vista_search_radius(self.combo_vista_radius.currentData())
        selected_sound = self.sound_combo.currentData()
        if selected_sound:
            self.settings.set_selected_sound(selected_sound)
        self.settings.set_min_value_threshold(self.spin_threshold.value())
        super().accept()
