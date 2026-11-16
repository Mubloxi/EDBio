"""End-to-end test: real journal file -> monitor -> processor state."""

import os
import json
import tempfile
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from edbio.journal import JournalMonitor
from edbio.database import Database
from edbio.species import SpeciesDB
from edbio.processor import JournalProcessor


def _event(etype, **fields):
    evt = {"timestamp": "2023-05-01T12:00:00Z", "event": etype}
    evt.update(fields)
    return json.dumps(evt) + "\n"


def _pump(app, seconds):
    """Run the Qt event loop briefly so cross-thread slots execute."""
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.05)


def test_full_flow():
    app = QApplication.instance() or QApplication([])

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "Journal.230501-120000.part1.log")

    db = Database(":memory:")
    sdb = SpeciesDB()
    processor = JournalProcessor(db, sdb)
    updates = []

    processor.on_planet_updated = lambda p: updates.append(("planet", p.get("body_name")))
    processor.on_sample_updated = lambda s: updates.append(("sample", s["species"], s["scan_count"]))
    processor.on_history_added = lambda r: updates.append(("history", r["species"], r["status"]))

    monitor = JournalMonitor(tmp)
    monitor.event_received.connect(processor.handle_event)
    monitor.start()

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(_event("LoadGame", Commander="TestCmdr", StarSystem="Sol"))
            f.write(_event("Scan", ScanType="Detailed", BodyName="Sol 3",
                           SystemAddress=123, BodyID=3,
                           PlanetClass="High metal content body",
                           Atmosphere="Sulphur Dioxide atmosphere",
                           AtmosphereType="Sulphur Dioxide", SurfaceTemperature=140,
                           SurfaceGravity=1.0,
                           Volcanism="major silicate vapour geysers volcanism",
                           Radius=1000000.0))
            f.write(_event("SAASignalsFound", BodyName="Sol 3", SystemAddress=123, BodyID=3,
                           Signals=[{"Type": "$SAA_SignalType_Biological;",
                                     "Type_Localised": "Biological", "Count": 2}],
                           Genuses=[{"Genus": "$Codex_Ent_Stratum_Genus_Name;",
                                     "Genus_Localised": "Stratum"}]))

        _pump(app, 2.0)

        planet = processor.current_planet()
        assert planet is not None
        assert planet["body_name"] == "Sol 3"
        assert planet["estimated_value"] == 19010800  # Stratum Tectonicas

        with open(path, "a", encoding="utf-8") as f:
            f.write(_event("Touchdown", BodyName="Sol 3", Latitude=0.0, Longitude=0.0))
            f.write(_event("ScanOrganic", ScanType="Log",
                           Genus="$Codex_Ent_Stratum_Genus_Name;",
                           Genus_Localised="Stratum",
                           Species="$Codex_Ent_Stratum_07_Name;",
                           Species_Localised="Stratum Tectonicas",
                           SystemAddress=123, Body=3))

        _pump(app, 2.0)

        tracker = processor.get_tracker("Stratum", "Stratum Tectonicas")
        assert tracker is not None
        assert tracker.scan_count == 1
        assert tracker.reference_lat == 0.0

        tracker.update_position(0.0, 0.04)  # ~700m
        with open(path, "a", encoding="utf-8") as f:
            f.write(_event("ScanOrganic", ScanType="Sample",
                           Genus="$Codex_Ent_Stratum_Genus_Name;",
                           Species="$Codex_Ent_Stratum_07_Name;",
                           SystemAddress=123, Body=3))

        _pump(app, 2.0)
        assert tracker.scan_count == 2

        with open(path, "a", encoding="utf-8") as f:
            f.write(_event("ScanOrganic", ScanType="Analyse",
                           Genus="$Codex_Ent_Stratum_Genus_Name;",
                           Species="$Codex_Ent_Stratum_07_Name;",
                           SystemAddress=123, Body=3))

        _pump(app, 2.0)
        assert tracker.scan_count == 3
        assert tracker.status == "Complete"

        history = db.get_history()
        assert any(h["species"] == "Stratum Tectonicas" and h["status"] == "Complete"
                   for h in history)
        assert any(u[0] == "history" for u in updates)
    finally:
        monitor.stop()
