"""Exobiology tab: active planet, species table, sample tracking."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QSpinBox, QDoubleSpinBox,
)

from ..species import PREDICTED, GENUS_CONFIRMED, SPECIES_CONFIRMED, SAMPLING, COMPLETE, UNKNOWN
from ..credits import format_credits
from .species_detail import SpeciesDetailDialog


ED_ORANGE = "#ff9900"


class ExobiologyTab(QWidget):
    def __init__(self, processor):
        super().__init__()
        self.processor = processor
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Species table.
        self.lbl_empty = QLabel()
        self.lbl_empty.setWordWrap(True)
        self.lbl_empty.setStyleSheet("color: #cccccc; padding: 6px;")
        layout.addWidget(self.lbl_empty)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Species", "Status", "Value", "Samples", "Distance", "Remaining"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_detail)
        layout.addWidget(self.table, 1)

        # Buttons row.
        btn_row = QHBoxLayout()
        self.btn_detail = QPushButton("Show Detail")
        self.btn_detail.clicked.connect(self._open_detail)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(self.btn_detail)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_refresh)
        layout.addLayout(btn_row)

        # Info group.
        info = QGroupBox("Planet Information")
        info.setFlat(True)
        form = QFormLayout(info)

        self.lbl_signals = QLabel("Biological Signals: --")
        self.lbl_planet_value = QLabel("Estimated Planet Value: --")
        self.lbl_completed = QLabel("Completed Species: 0")
        self.lbl_progress = QLabel("Sample Progress: --")
        self.lbl_coords = QLabel("Last Sample Coordinates: --")

        for lbl in (self.lbl_signals, self.lbl_planet_value, self.lbl_completed,
                    self.lbl_progress, self.lbl_coords):
            lbl.setStyleSheet("color: #cccccc;")

        form.addRow(self.lbl_signals)
        form.addRow(self.lbl_planet_value)
        form.addRow(self.lbl_completed)
        form.addRow(self.lbl_progress)
        form.addRow(self.lbl_coords)
        layout.addWidget(info)

        # Total value at the bottom.
        self.lbl_total = QLabel("Estimated Total: 0 CR")
        self.lbl_total.setStyleSheet(f"color: {ED_ORANGE}; font-weight: bold;")
        layout.addWidget(self.lbl_total)

    def refresh(self):
        planet = self.processor.current_planet()
        self.table.setRowCount(0)

        total = 0
        completed = 0

        if planet:
            signals = planet.get("signals") or []
            bio_count = sum(s.get("Count", 0) for s in signals
                            if s.get("Type_Localised") == "Biological")
            self.lbl_signals.setText(f"Biological Signals: {bio_count}")

            genuses = planet.get("genuses") or []
            predictions = self.processor.predictions_for_current_planet()

            for pred in predictions:
                row = self.table.rowCount()
                self.table.insertRow(row)

                species = pred["species"]
                status = pred["status"]
                value = pred.get("base_value")
                if value:
                    total += value

                self.table.setItem(row, 0, QTableWidgetItem(species))
                self.table.setItem(row, 1, QTableWidgetItem(status))
                self.table.setItem(row, 2, QTableWidgetItem(format_credits(value) if value else UNKNOWN))

                # Sample progress.
                tracker = self.processor.get_tracker(pred["genus_localised"], species)
                if tracker:
                    samples_txt = tracker.progress_text()
                    dist_txt = tracker.distance_text()
                    rem_txt = tracker.remaining_text()
                    if tracker.status == COMPLETE:
                        completed += 1
                else:
                    samples_txt = "0/3"
                    dist_txt = UNKNOWN
                    rem_txt = UNKNOWN

                self.table.setItem(row, 3, QTableWidgetItem(samples_txt))
                self.table.setItem(row, 4, QTableWidgetItem(dist_txt))
                self.table.setItem(row, 5, QTableWidgetItem(rem_txt))

            self.lbl_completed.setText(f"Completed Species: {completed}")
            planet_value = self.processor.credits.planet_value(
                [p.get("base_value") for p in predictions if p.get("status") == COMPLETE])
            # If nothing completed yet, show sum of predicted as potential.
            self.lbl_planet_value.setText(
                f"Estimated Planet Value: {format_credits(total) if total else UNKNOWN}")
            self.lbl_total.setText(f"Estimated Total: {format_credits(total) if total else '0 CR'}")

            # Coordinates from the most recent tracker with a reference.
            coords = "Unknown"
            for tr in self.processor.sample_trackers():
                if tr.reference_lat is not None and tr.reference_lon is not None:
                    coords = f"{tr.reference_lat:.4f}, {tr.reference_lon:.4f}"
                    break
            self.lbl_coords.setText(f"Last Sample Coordinates: {coords}")
        else:
            self.lbl_signals.setText("Biological Signals: --")
            self.lbl_planet_value.setText("Estimated Planet Value: --")
            self.lbl_completed.setText("Completed Species: 0")
            self.lbl_progress.setText("Sample Progress: --")
            self.lbl_coords.setText("Last Sample Coordinates: --")
            self.lbl_total.setText("Estimated Total: 0 CR")

        if self.table.rowCount():
            self.lbl_empty.hide()
        else:
            if planet:
                self.lbl_empty.setText(
                    "No species predictions yet. Check for biological signals "
                    "or wait for the journal to report them."
                )
            else:
                self.lbl_empty.setText(
                    "Waiting for journal data. Scan a planet to see exobiology "
                    "information here."
                )
            self.lbl_empty.show()

    def _open_detail(self):
        row = self.table.currentRow()
        if row < 0:
            return
        species = self.table.item(row, 0).text()
        status = self.table.item(row, 1).text()
        value_txt = self.table.item(row, 2).text()
        tracker = None
        for tr in self.processor.sample_trackers():
            if tr.species == species:
                tracker = tr
                break
        dlg = SpeciesDetailDialog(species, status, value_txt, tracker, self)
        dlg.exec()
