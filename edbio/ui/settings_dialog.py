"""Settings dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QCheckBox, QDoubleSpinBox, QFileDialog, QLabel, QDialogButtonBox, QGroupBox,
)


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.resize(460, 320)

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
            self.settings.set_journal_dir(path)

    def accept(self):
        self.settings.set_always_on_top(self.ck_ontop.isChecked())
        self.settings.set_minimize_to_tray(self.ck_tray.isChecked())
        self.settings.set_notify_valuable(self.ck_notify.isChecked())
        self.settings.set_min_value_threshold(self.spin_threshold.value())
        super().accept()
