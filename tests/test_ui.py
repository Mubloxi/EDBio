"""Tests for user-facing empty states."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox

from edbio.audio import DEFAULT_SOUND
from edbio.credits import CreditCalculator
from edbio.database import Database
from edbio.journal import JournalMonitor
from edbio.processor import JournalProcessor
from edbio.species import SpeciesDB
from edbio.ui import bio_overlay
from edbio.ui.bio_overlay import BioOverlay
from edbio.ui.exobiology_tab import ExobiologyTab
from edbio.ui.main_window import MainWindow
from edbio.ui.sound_picker import FirstRunDialog, populate_sound_combo


class WindowSettings:
    def window_geometry(self):
        return None

    def window_state(self):
        return None

    def current_tab(self):
        return 0

    def always_on_top(self):
        return False

    def minimize_to_tray(self):
        return False

    def overlay_enabled(self):
        return False

    def sound_enabled(self):
        return True

    def selected_sound(self):
        return DEFAULT_SOUND

    def set_current_tab(self, index):
        pass

    def set_window_geometry(self, geometry):
        pass

    def set_window_state(self, state):
        pass


class EmptyProcessor:
    def __init__(self):
        self.planet = None
        self.credits = CreditCalculator()

    def current_planet(self):
        return self.planet

    def predictions_for_current_planet(self):
        return []

    def get_tracker(self, genus, species):
        return None

    def sample_trackers(self):
        return []


def test_exobiology_tab_explains_empty_species_table():
    app = QApplication.instance() or QApplication([])
    processor = EmptyProcessor()
    tab = ExobiologyTab(processor)

    tab.refresh()
    assert not tab.lbl_empty.isHidden()
    assert "Waiting for journal data" in tab.lbl_empty.text()

    processor.planet = {"signals": [], "genuses": []}
    tab.refresh()
    assert not tab.lbl_empty.isHidden()
    assert "No species predictions yet" in tab.lbl_empty.text()


def test_sound_picker_groups_and_selects_the_default():
    app = QApplication.instance() or QApplication([])
    combo = QComboBox()

    assert populate_sound_combo(combo, "random ass/notification.mp3")
    assert combo.currentData() == "random ass/notification.mp3"
    assert "French" in [combo.itemText(i) for i in range(combo.count())]

    previews = []
    dialog = FirstRunDialog(DEFAULT_SOUND, previews.append)
    dialog.preview_button.click()
    assert previews == [DEFAULT_SOUND]


def test_overlay_is_hidden_when_the_game_is_not_foreground(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(bio_overlay, "foreground_game_rect", lambda: (0, 0, 1920, 1080))
    overlay = BioOverlay(enabled=True)

    overlay.show_detection("Planet A", 3, ["Stratum"])
    assert overlay.isVisible()
    assert "Stratum" in overlay.detail.text()

    monkeypatch.setattr(bio_overlay, "foreground_game_rect", lambda: None)
    overlay._update_visibility()
    assert not overlay.isVisible()
    overlay.set_enabled(False)


def test_live_fss_bio_signal_plays_selected_sound_and_updates_overlay():
    app = QApplication.instance() or QApplication([])
    database = Database(":memory:")
    processor = JournalProcessor(database, SpeciesDB())
    window = MainWindow(processor, JournalMonitor(""), WindowSettings())
    played = []
    window._play_sound = played.append

    window._on_live_event({
        "event": "FSSBodySignals",
        "BodyName": "Planet A",
        "Signals": [
            {"Type_Localised": "Biological", "Count": 2},
            {"Type_Localised": "Geological", "Count": 4},
        ],
    })
    assert played == [DEFAULT_SOUND]
    assert "Planet A" in window.bio_overlay.detail.text()
    assert "2 biological signal(s)" in window.bio_overlay.detail.text()

    processor.signals["Planet A"] = {"biological_count": 2}
    window._on_live_event({
        "event": "SAASignalsFound",
        "BodyName": "Planet A",
        "Genuses": [{"Genus": "$Codex_Ent_Stratum_Genus_Name;"}],
    })
    assert "Detected genera: Stratum" in window.bio_overlay.detail.text()

    window.close()
    database.close()
