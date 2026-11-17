"""Tests for SQLite persistence: history, samples, planets, dedup."""

from database import Database


def test_history_persistence():
    db = Database(":memory:")
    db.add_history({
        "date": "2023-05-01T12:00:00Z",
        "system": "Sol",
        "planet": "Earth",
        "species": "Stratum Tectonicas",
        "samples": 3,
        "value": 19010800,
        "status": "Complete",
    })
    rows = db.get_history()
    assert len(rows) == 1
    assert rows[0]["species"] == "Stratum Tectonicas"
    assert rows[0]["system"] == "Sol"


def test_history_search():
    db = Database(":memory:")
    db.add_history({"date": "2023-05-01T12:00:00Z", "system": "Sol", "planet": "Earth",
                    "species": "Stratum Tectonicas", "samples": 3, "value": 100, "status": "Complete"})
    db.add_history({"date": "2023-05-02T12:00:00Z", "system": "Alpha Centauri", "planet": "Mars",
                    "species": "Bacterium Cerbrus", "samples": 1, "value": 200, "status": "Predicted"})
    results = db.get_history("Stratum")
    assert len(results) == 1
    results = db.get_history("Centauri")
    assert len(results) == 1
    results = db.get_history("Nonexistent")
    assert len(results) == 0


def test_sample_persistence():
    db = Database(":memory:")
    db.upsert_sample({
        "system_address": 1, "body_id": 2, "genus": "Stratum", "species": "Stratum Tectonicas",
        "scan_count": 2, "reference_lat": 0.0, "reference_lon": 0.0,
        "planet_radius": 1000000.0, "distance_required": 500.0, "status": "Sampling",
    })
    rows = db.get_samples(1, 2)
    assert len(rows) == 1
    assert rows[0]["scan_count"] == 2
    assert rows[0]["status"] == "Sampling"


def test_planet_persistence():
    db = Database(":memory:")
    db.upsert_planet({
        "system_address": 1, "body_id": 2, "system_name": "Sol", "body_name": "Earth",
        "planet_class": "Earthlike body", "estimated_value": 50000000, "status": "Scanned",
    })
    planet = db.get_planet(1, 2)
    assert planet is not None
    assert planet["body_name"] == "Earth"
    assert planet["estimated_value"] == 50000000


def test_processor_can_restore_selected_planet_from_database():
    from processor import JournalProcessor
    from species import SpeciesDB

    db = Database(":memory:")
    db.upsert_planet({
        "system_address": 1,
        "body_id": 2,
        "system_name": "Sol",
        "body_name": "Sol 3",
        "signals": [{"Type_Localised": "Biological", "Count": 2}],
        "genuses": ["Stratum"],
        "radius": 1000000,
    })
    processor = JournalProcessor(db, SpeciesDB())
    processor.set_system("Sol", 1)
    processor.set_body("Sol 3")

    planet = processor.current_planet()
    assert planet["body_name"] == "Sol 3"
    assert processor.body_genuses["Sol 3"] == ["Stratum"]
    assert processor.signals["Sol 3"]["biological_count"] == 2
    db.close()


def test_processed_event_dedup():
    db = Database(":memory:")
    assert db.is_processed("evt1") is False
    assert db.mark_processed("evt1", "Scan", "2023-05-01T12:00:00Z") is True
    assert db.is_processed("evt1") is True
    # mark_processed is idempotent
    assert db.mark_processed("evt1", "Scan", "2023-05-01T12:00:00Z") is False
