"""History tab: previously discovered and sampled species."""

import csv

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QHeaderView, QFileDialog, QMessageBox,
)

from ..credits import format_credits


class HistoryTab(QWidget):
    def __init__(self, processor):
        super().__init__()
        self.processor = processor
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Filter / search bar.
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search system, planet or species...")
        self.search.textChanged.connect(self.refresh)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._clear_search)
        self.btn_export = QPushButton("Export CSV...")
        self.btn_export.clicked.connect(self._export_dialog)
        bar.addWidget(QLabel("Filter:"))
        bar.addWidget(self.search, 1)
        bar.addWidget(self.btn_clear)
        bar.addStretch()
        bar.addWidget(self.btn_export)
        layout.addLayout(bar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Date", "System", "Planet", "Species", "Samples", "Value", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        self.lbl_total = QLabel("Total Estimated Value: 0 CR")
        self.lbl_total.setStyleSheet("color: #ff9900; font-weight: bold;")
        layout.addWidget(self.lbl_total)

    def refresh(self):
        term = self.search.text().strip()
        rows = self.processor.db.get_history(term if term else None)

        self.table.setRowCount(0)
        total = 0
        for record in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(record.get("date", "")[:16]))
            self.table.setItem(row, 1, QTableWidgetItem(record.get("system", "")))
            self.table.setItem(row, 2, QTableWidgetItem(record.get("planet", "")))
            self.table.setItem(row, 3, QTableWidgetItem(record.get("species", "")))
            self.table.setItem(row, 4, QTableWidgetItem(str(record.get("samples", 0))))
            value = record.get("value") or 0
            self.table.setItem(row, 5, QTableWidgetItem(format_credits(value) if value else "--"))
            self.table.setItem(row, 6, QTableWidgetItem(record.get("status", "")))
            if value:
                total += value

        self.lbl_total.setText(f"Total Estimated Value: {format_credits(total) if total else '0 CR'}")

    def _clear_search(self):
        self.search.clear()

    def _export_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export History to CSV",
                                              "edbio_history.csv", "CSV Files (*.csv)")
        if path:
            self.export_csv(path)

    def export_csv(self, path):
        term = self.search.text().strip()
        rows = self.processor.db.get_history(term if term else None)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "System", "Planet", "Species", "Samples", "Value", "Status"])
            for record in rows:
                writer.writerow([
                    record.get("date", ""),
                    record.get("system", ""),
                    record.get("planet", ""),
                    record.get("species", ""),
                    record.get("samples", 0),
                    record.get("value", 0),
                    record.get("status", ""),
                ])
