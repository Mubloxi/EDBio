"""Tests for biological species prediction."""

from edbio.species import SpeciesDB, PREDICTED
from edbio.processor import JournalProcessor
from edbio.database import Database


def _planet(**overrides):
    base = {
        "planet_class": "High metal content body",
        "atmosphere": "Sulphur Dioxide atmosphere",
        "atmosphere_type": "Sulphur Dioxide",
        "temperature": 140,
        "gravity": 1.0,
        "volcanism": "major silicate vapour geysers volcanism",
        "radius": 1000000,
    }
    base.update(overrides)
    return base


def test_predict_stratum_tectonicas():
    db = Database(":memory:")
    sdb = SpeciesDB()
    proc = JournalProcessor(db, sdb)
    planet = _planet()
    preds = proc.predictions_for_current_planet() if False else sdb.predict_all(planet, ["Stratum"])
    names = [p["species"] for p in preds]
    assert "Stratum Tectonicas" in names
    for p in preds:
        assert p["status"] == PREDICTED
    db.close()


def test_predict_unknown_when_no_genus():
    db = Database(":memory:")
    sdb = SpeciesDB()
    planet = _planet()
    preds = sdb.predict_all(planet, [])
    assert preds == []
    db.close()


def test_species_price_verified():
    db = Database(":memory:")
    sdb = SpeciesDB()
    assert sdb.species_price("Stratum Tectonicas") == 19010800
    assert sdb.species_price("Fonticulua Fluctus") == 20000000
    assert sdb.species_price("Bacterium Cerbrus") == 1689800
    assert sdb.species_price("Nonexistent Species") is None
    db.close()


def test_prediction_never_confirmed():
    db = Database(":memory:")
    sdb = SpeciesDB()
    planet = _planet()
    preds = sdb.predict_all(planet, ["Stratum"])
    for p in preds:
        assert p["status"] != "Species Confirmed"
        assert p["status"] != "Complete"
    db.close()


def test_normalize_genus():
    db = Database(":memory:")
    sdb = SpeciesDB()
    assert sdb.normalize_genus("$Codex_Ent_Stratum_Genus_Name;") == "Stratum"
    assert sdb.normalize_genus("$Codex_Ent_Bacterial_Genus_Name;") == "Bacterium"
    assert sdb.normalize_genus("$Codex_Ent_Fonticulus_Genus_Name;") == "Fonticulua"
    db.close()
