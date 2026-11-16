"""Local SQLite storage for planets, history, samples, and processed events."""

import os
import sqlite3
import json
import csv
from datetime import datetime, timezone


class Database:
    MANAGEMENT_TABLES = {
        "history": "date DESC, id DESC",
        "planets": "updated_at DESC, body_name",
        "samples": "updated_at DESC, species",
        "processed_events": "processed_at DESC, id",
    }

    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS processed_events (
                id         TEXT PRIMARY KEY,
                event_type TEXT,
                timestamp  TEXT,
                processed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS planets (
                system_address INTEGER,
                body_id        INTEGER,
                system_name    TEXT,
                body_name      TEXT,
                planet_class   TEXT,
                atmosphere     TEXT,
                atmosphere_type TEXT,
                temperature    REAL,
                gravity        REAL,
                volcanism      TEXT,
                radius         REAL,
                surface_gravity REAL,
                star_system    TEXT,
                star_type      TEXT,
                signals        TEXT,
                genuses        TEXT,
                estimated_value INTEGER,
                status         TEXT,
                updated_at     TEXT,
                PRIMARY KEY (system_address, body_id)
            );

            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT,
                system      TEXT,
                planet      TEXT,
                species     TEXT,
                samples     INTEGER,
                value       INTEGER,
                status      TEXT
            );

            CREATE TABLE IF NOT EXISTS samples (
                system_address INTEGER,
                body_id        INTEGER,
                genus          TEXT,
                species        TEXT,
                scan_count     INTEGER DEFAULT 0,
                reference_lat  REAL,
                reference_lon  REAL,
                planet_radius  REAL,
                distance_required REAL,
                status         TEXT,
                updated_at     TEXT,
                PRIMARY KEY (system_address, body_id, genus, species)
            );
            """
        )
        self.conn.commit()

    # --- processed event dedup ---

    def is_processed(self, event_id):
        cur = self.conn.execute(
            "SELECT 1 FROM processed_events WHERE id = ?", (event_id,)
        )
        return cur.fetchone() is not None

    def mark_processed(self, event_id, event_type, timestamp):
        self.conn.execute(
            "INSERT OR IGNORE INTO processed_events (id, event_type, timestamp, processed_at) "
            "VALUES (?, ?, ?, ?)",
            (event_id, event_type, timestamp, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    # --- planets ---

    def upsert_planet(self, planet):
        self.conn.execute(
            """
            INSERT INTO planets (
                system_address, body_id, system_name, body_name, planet_class,
                atmosphere, atmosphere_type, temperature, gravity, volcanism,
                radius, surface_gravity, star_system, star_type, signals,
                genuses, estimated_value, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(system_address, body_id) DO UPDATE SET
                system_name=excluded.system_name,
                body_name=excluded.body_name,
                planet_class=excluded.planet_class,
                atmosphere=excluded.atmosphere,
                atmosphere_type=excluded.atmosphere_type,
                temperature=excluded.temperature,
                gravity=excluded.gravity,
                volcanism=excluded.volcanism,
                radius=excluded.radius,
                surface_gravity=excluded.surface_gravity,
                star_system=excluded.star_system,
                star_type=excluded.star_type,
                signals=excluded.signals,
                genuses=excluded.genuses,
                estimated_value=excluded.estimated_value,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (
                planet.get("system_address"),
                planet.get("body_id"),
                planet.get("system_name"),
                planet.get("body_name"),
                planet.get("planet_class"),
                planet.get("atmosphere"),
                planet.get("atmosphere_type"),
                planet.get("temperature"),
                planet.get("gravity"),
                planet.get("volcanism"),
                planet.get("radius"),
                planet.get("surface_gravity"),
                planet.get("star_system"),
                planet.get("star_type"),
                json.dumps(planet.get("signals") or []),
                json.dumps(planet.get("genuses") or []),
                planet.get("estimated_value"),
                planet.get("status"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()

    def _deserialize_planet(self, row):
        d = dict(row)
        for key in ("signals", "genuses"):
            try:
                d[key] = json.loads(d[key]) if d[key] else []
            except (json.JSONDecodeError, TypeError):
                d[key] = []
        return d

    def get_planets(self, system_name=None):
        if system_name:
            cur = self.conn.execute(
                "SELECT * FROM planets WHERE system_name = ? ORDER BY body_name",
                (system_name,),
            )
        else:
            cur = self.conn.execute("SELECT * FROM planets ORDER BY system_name, body_name")
        return [self._deserialize_planet(row) for row in cur.fetchall()]

    def get_planet(self, system_address, body_id):
        cur = self.conn.execute(
            "SELECT * FROM planets WHERE system_address = ? AND body_id = ?",
            (system_address, body_id),
        )
        row = cur.fetchone()
        return self._deserialize_planet(row) if row else None

    def delete_planets_for_system(self, system_name):
        self.conn.execute(
            "DELETE FROM planets WHERE system_name = ?", (system_name,)
        )
        self.conn.commit()

    # --- history ---

    def add_history(self, record):
        self.conn.execute(
            """
            INSERT INTO history (date, system, planet, species, samples, value, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("date"),
                record.get("system"),
                record.get("planet"),
                record.get("species"),
                record.get("samples"),
                record.get("value"),
                record.get("status"),
            ),
        )
        self.conn.commit()

    def get_history(self, search=None):
        if search:
            like = f"%{search}%"
            cur = self.conn.execute(
                """
                SELECT * FROM history
                WHERE system LIKE ? OR planet LIKE ? OR species LIKE ?
                ORDER BY date DESC
                """,
                (like, like, like),
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM history ORDER BY date DESC"
            )
        return [dict(row) for row in cur.fetchall()]

    def clear_history(self):
        self.conn.execute("DELETE FROM history")
        self.conn.commit()

    # --- samples ---

    def upsert_sample(self, sample):
        self.conn.execute(
            """
            INSERT INTO samples (
                system_address, body_id, genus, species, scan_count,
                reference_lat, reference_lon, planet_radius,
                distance_required, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(system_address, body_id, genus, species) DO UPDATE SET
                scan_count=excluded.scan_count,
                reference_lat=excluded.reference_lat,
                reference_lon=excluded.reference_lon,
                planet_radius=excluded.planet_radius,
                distance_required=excluded.distance_required,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (
                sample.get("system_address"),
                sample.get("body_id"),
                sample.get("genus"),
                sample.get("species"),
                sample.get("scan_count"),
                sample.get("reference_lat"),
                sample.get("reference_lon"),
                sample.get("planet_radius"),
                sample.get("distance_required"),
                sample.get("status"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()

    def get_samples(self, system_address=None, body_id=None):
        if system_address is not None and body_id is not None:
            cur = self.conn.execute(
                "SELECT * FROM samples WHERE system_address = ? AND body_id = ?",
                (system_address, body_id),
            )
        else:
            cur = self.conn.execute("SELECT * FROM samples")
        return [dict(row) for row in cur.fetchall()]

    def management_snapshot(self, limit=100):
        tables = []
        for name, order_by in self.MANAGEMENT_TABLES.items():
            count = self.conn.execute(
                f"SELECT COUNT(*) FROM {name}"
            ).fetchone()[0]
            rows = self.conn.execute(
                f"SELECT * FROM {name} ORDER BY {order_by} LIMIT ?",
                (limit,),
            ).fetchall()
            tables.append({
                "name": name,
                "count": count,
                "rows": [dict(row) for row in rows],
            })

        try:
            size = os.path.getsize(self.path) if self.path != ":memory:" else None
        except OSError:
            size = None
        return {
            "path": os.path.abspath(self.path) if self.path != ":memory:" else self.path,
            "size_bytes": size,
            "tables": tables,
        }

    def backup_to(self, destination):
        source = os.path.abspath(self.path) if self.path != ":memory:" else None
        target = os.path.abspath(destination)
        if source and os.path.normcase(source) == os.path.normcase(target):
            raise ValueError("Choose a backup path different from the active database.")

        backup = sqlite3.connect(target)
        try:
            self.conn.backup(backup)
        finally:
            backup.close()

    def export_table_csv(self, table_name, destination):
        if table_name not in self.MANAGEMENT_TABLES:
            raise ValueError(f"Unsupported database table: {table_name}")

        cursor = self.conn.execute(f"SELECT * FROM {table_name}")
        with open(destination, "w", newline="", encoding="utf-8-sig") as output:
            writer = csv.writer(output)
            writer.writerow(column[0] for column in cursor.description)
            writer.writerows(cursor.fetchall())

    def integrity_check(self):
        return [
            row[0] for row in self.conn.execute("PRAGMA quick_check")
        ]

    def close(self):
        self.conn.close()
