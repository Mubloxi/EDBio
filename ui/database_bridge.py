# Narrow WebChannel API for viewing and backing up the application database

import json
import os
import sqlite3

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QFileDialog


class DatabaseBridge(QObject):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database

    @Slot(result=str)
    def snapshot(self):
        try:
            data = self.database.management_snapshot()
        except sqlite3.Error as exc:
            return json.dumps({"error": f"Could not read the database: {exc}"})
        return json.dumps({"data": data})

    @Slot(result=str)
    def backup(self):
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Back Up EDBio Database",
            os.path.join(os.path.expanduser("~"), "EDBio-backup.sqlite3"),
            "SQLite database (*.sqlite3 *.db)",
        )
        if not destination:
            return json.dumps({"cancelled": True})

        try:
            self.database.backup_to(destination)
        except (OSError, sqlite3.Error, ValueError) as exc:
            return json.dumps({"error": f"Backup failed: {exc}"})
        return json.dumps({"saved_to": destination})

    @Slot(str, result=str)
    def export_table(self, table_name):
        if table_name not in self.database.MANAGEMENT_TABLES:
            return json.dumps({"error": "Choose a listed database table to export."})

        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Export Database Table",
            os.path.join(os.path.expanduser("~"), f"edbio-{table_name}.csv"),
            "CSV file (*.csv)",
        )
        if not destination:
            return json.dumps({"cancelled": True})

        try:
            self.database.export_table_csv(table_name, destination)
        except (OSError, sqlite3.Error, ValueError) as exc:
            return json.dumps({"error": f"Export failed: {exc}"})
        return json.dumps({"saved_to": destination})

    @Slot(result=str)
    def check_integrity(self):
        try:
            results = self.database.integrity_check()
        except sqlite3.Error as exc:
            return json.dumps({"error": f"Integrity check failed: {exc}"})
        return json.dumps({"integrity": results})
