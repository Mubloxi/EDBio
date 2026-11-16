"""Planets tab: scanned planets in the current system."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView,
)

from credits import format_credits

ED_ORANGE = "#ff9900"


class PlanetsTab(QWidget):
    def __init__(self, processor):
        super().__init__()
        self.processor = processor
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.lbl_info = QLabel("No planets scanned yet.")
        self.lbl_info.setStyleSheet("color: #cccccc;")
        layout.addWidget(self.lbl_info)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Planet", "Biological Signals", "Predicted Species", "Estimated Value", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_select)
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        self.btn_inspect = QPushButton("Inspect Selected Planet")
        self.btn_inspect.clicked.connect(self._inspect_selected)
        self.btn_inspect.setEnabled(False)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(self.btn_inspect)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_refresh)
        layout.addLayout(btn_row)

    def refresh(self):
        system = self.processor.current_system
        planets = self.processor.all_db_planets() if system else []
        self.lbl_info.setText(f"System: {system or '--'}  ({len(planets)} planet(s))")

        self.table.setRowCount(0)
        for planet in planets:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = planet.get("body_name") or "Unknown"
            signals = planet.get("signals") or []
            bio_count = sum(s.get("Count", 0) for s in signals
                            if s.get("Type_Localised") == "Biological")
            genuses = planet.get("genuses") or []
            pred_names = ", ".join(genuses) if genuses else "Unknown"
            est = planet.get("estimated_value") or 0
            status = planet.get("status") or "Scanned"

            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(bio_count)))
            self.table.setItem(row, 2, QTableWidgetItem(pred_names))
            self.table.setItem(row, 3, QTableWidgetItem(format_credits(est) if est else "--"))
            self.table.setItem(row, 4, QTableWidgetItem(status))
            self.table.item(row, 0).setData(Qt.UserRole, planet)

            if est and est >= 10000000:
                highlight = QColor(ED_ORANGE)
                for col in range(5):
                    self.table.item(row, col).setForeground(highlight)

    def _on_select(self):
        self.btn_inspect.setEnabled(self.table.currentRow() >= 0)

    def _inspect_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        planet = item.data(Qt.UserRole) if item else None
        if not planet:
            return
        body_name = planet.get("body_name")
        if body_name:
            self.processor.set_body(body_name)
            if self.processor.on_planet_updated:
                self.processor.on_planet_updated(planet)
            mw = self.window()
            if mw:
                mw.tabs.setCurrentIndex(0)
                mw.tab_exo.refresh()

    def export_csv(self, path):
        raise NotImplementedError("history export is on the History tab")
