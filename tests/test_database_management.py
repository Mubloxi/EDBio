import json
import csv
import sqlite3

from database import Database
from ui.database_bridge import DatabaseBridge


def test_management_snapshot_reports_counts_and_recent_rows():
    database = Database(":memory:")
    database.add_history({
        "date": "2026-01-02T00:00:00Z",
        "system": "Sol",
        "planet": "Mars",
        "species": "Stratum",
        "samples": 3,
        "value": 100,
        "status": "Complete",
    })

    snapshot = database.management_snapshot()
    history = next(table for table in snapshot["tables"] if table["name"] == "history")
    assert snapshot["path"] == ":memory:"
    assert history["count"] == 1
    assert history["rows"][0]["system"] == "Sol"
    assert database.integrity_check() == ["ok"]


def test_bridge_backup_creates_openable_database(tmp_path, monkeypatch):
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "backup.sqlite3"
    database = Database(str(source))
    database.add_history({
        "date": "2026-01-02T00:00:00Z",
        "system": "Sol",
        "planet": "Mars",
        "species": "Stratum",
        "samples": 3,
        "value": 100,
        "status": "Complete",
    })
    monkeypatch.setattr(
        "ui.database_bridge.QFileDialog.getSaveFileName",
        lambda *args: (str(destination), "SQLite database (*.sqlite3 *.db)"),
    )

    result = json.loads(DatabaseBridge(database).backup())
    assert result["saved_to"] == str(destination)

    with sqlite3.connect(destination) as backup:
        count = backup.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    assert count == 1


def test_backup_rejects_the_active_database_path(tmp_path):
    path = tmp_path / "active.sqlite3"
    database = Database(str(path))
    try:
        database.backup_to(str(path))
    except ValueError as exc:
        assert "different from the active database" in str(exc)
    else:
        raise AssertionError("Backing up over the active database must be rejected")


def test_table_export_is_csv_and_rejects_unlisted_tables(tmp_path):
    database = Database(":memory:")
    database.add_history({
        "date": "2026-01-02T00:00:00Z",
        "system": "Sol",
        "planet": "Mars",
        "species": "Stratum, rare",
        "samples": 3,
        "value": 100,
        "status": "Complete",
    })
    destination = tmp_path / "history.csv"

    database.export_table_csv("history", str(destination))

    with destination.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert rows[0]["species"] == "Stratum, rare"

    try:
        database.export_table_csv("history; DROP TABLE history", str(destination))
    except ValueError as exc:
        assert "Unsupported database table" in str(exc)
    else:
        raise AssertionError("Only listed tables may be exported")
