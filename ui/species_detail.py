"""Detail dialog for a species."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QDialogButtonBox, QGroupBox,
    QHBoxLayout, QPushButton,
)

from samples import NOT_STARTED, SAMPLING, COMPLETE


ED_ORANGE = "#ff9900"


class SpeciesDetailDialog(QDialog):
    def __init__(self, species, status, value_txt, tracker, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Species Detail: {species}")
        self.resize(420, 300)

        layout = QVBoxLayout(self)

        info = QGroupBox("Species Information")
        form = QFormLayout(info)
        form.addRow("Species:", QLabel(species))
        form.addRow("Status:", QLabel(status))
        form.addRow("Estimated Payout:", QLabel(value_txt or "Unknown"))
        layout.addWidget(info)

        if tracker:
            samp = QGroupBox("Genetic Sampling")
            sform = QFormLayout(samp)
            sform.addRow("Progress:", QLabel(tracker.progress_text()))
            sform.addRow("Distance Required:", QLabel(tracker.required_text()))
            sform.addRow("Distance Traveled:", QLabel(tracker.distance_text()))
            sform.addRow("Remaining:", QLabel(tracker.remaining_text()))
            sform.addRow("Collection Status:", QLabel(tracker.status))
            layout.addWidget(samp)

        # Environmental note.
        notes = QGroupBox("Notes")
        nform = QFormLayout(notes)
        note = QLabel("Estimated payout is the base Vista Genomics value for a "
                      "full genetic sample set. Actual earnings depend on first "
                      "footfall and whether the data has already been sold.")
        note.setWordWrap(True)
        nform.addRow(note)
        layout.addWidget(notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
