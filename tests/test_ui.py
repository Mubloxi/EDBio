"""Tests for user-facing empty states."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QComboBox

from audio import DEFAULT_SOUND
from credits import CreditCalculator
from database import Database
from journal import JournalMonitor
from processor import JournalProcessor
from species import SpeciesDB
from ui import bio_overlay
from ui.bio_overlay import BioOverlay
from ui.exobiology_tab import ExobiologyTab
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.sound_picker import FirstRunDialog, populate_sound_combo


class WindowSettings:
    def __init__(self):
        self._theme = "classic"
        self._journal_dir = ""

    def journal_dir(self):
        return self._journal_dir

    def set_journal_dir(self, path):
        self._journal_dir = path

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

    def theme(self):
        return self._theme

    def set_theme(self, theme):
        self._theme = theme

    def sound_enabled(self):
        return True

    def notify_valuable(self):
        return True

    def selected_sound(self):
        return DEFAULT_SOUND

    def vista_search_radius(self):
        return 50

    def min_value_threshold(self):
        return 0

    def set_current_tab(self, index):
        pass

    def set_vista_search_radius(self, value):
        pass

    def set_always_on_top(self, value):
        pass

    def set_minimize_to_tray(self, value):
        pass

    def set_notify_valuable(self, value):
        pass

    def set_sound_enabled(self, value):
        pass

    def set_overlay_enabled(self, value):
        pass

    def set_selected_sound(self, value):
        pass

    def set_min_value_threshold(self, value):
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


def test_main_window_includes_database_management_tab():
    app = QApplication.instance() or QApplication([])
    database = Database(":memory:")
    processor = JournalProcessor(database, SpeciesDB())
    window = MainWindow(processor, JournalMonitor(""), WindowSettings())

    assert window.tabs.count() == 4
    assert window.tabs.tabText(3) == "Database"
    assert window.tab_database.bridge.database is database
    assert window.tab_database._theme == "classic"
    assert not window.tab_database._loaded

    window.close()
    database.close()


def test_oled_theme_is_persisted_and_uses_black_window_palette():
    app = QApplication.instance() or QApplication([])
    database = Database(":memory:")
    settings = WindowSettings()
    processor = JournalProcessor(database, SpeciesDB())
    window = MainWindow(processor, JournalMonitor(""), settings)

    window.act_oled_theme.setChecked(True)
    assert settings.theme() == "oled"
    assert window.tab_database._theme == "oled"
    assert window.palette().color(QPalette.Window).name() == "#000000"

    window.act_oled_theme.setChecked(False)
    assert settings.theme() == "classic"
    assert window.tab_database._theme == "classic"
    assert window.palette().color(QPalette.Window).name() != "#000000"
    window.close()
    database.close()


def test_replay_coalesces_ui_refreshes_until_indexing_finishes():
    app = QApplication.instance() or QApplication([])
    database = Database(":memory:")
    processor = JournalProcessor(database, SpeciesDB())
    window = MainWindow(processor, JournalMonitor(""), WindowSettings())
    refreshes = {"exo": 0, "planets": 0, "history": 0}
    window.tab_exo.refresh = lambda: refreshes.__setitem__(
        "exo", refreshes["exo"] + 1
    )
    window.tab_planets.refresh = lambda: refreshes.__setitem__(
        "planets", refreshes["planets"] + 1
    )
    window.tab_history.refresh = lambda: refreshes.__setitem__(
        "history", refreshes["history"] + 1
    )

    window._on_replay_started()
    window._on_status_changed({
        "commander": "CMDR",
        "system": "Sol",
        "body": "Sol 1",
        "station": None,
        "last_event_time": "12:00:00",
    })
    window._on_planet_updated({"body_name": "Sol 1"})
    window._on_sample_updated({})
    window._on_history_added({})

    assert refreshes == {"exo": 0, "planets": 0, "history": 0}

    window._on_indexing_finished()

    assert refreshes == {"exo": 1, "planets": 1, "history": 1}
    assert not window._is_replaying
    window.close()
    database.close()


def test_settings_dialog_saves_journal_folder_only_on_accept(monkeypatch):
    app = QApplication.instance() or QApplication([])
    settings = WindowSettings()
    dialog = SettingsDialog(settings)
    monkeypatch.setattr(
        "ui.settings_dialog.QFileDialog.getExistingDirectory",
        lambda *args: "C:\\Elite Journals",
    )

    dialog._choose_dir()
    assert settings.journal_dir() == ""
    dialog.accept()
    assert settings.journal_dir() == "C:\\Elite Journals"


def test_sound_picker_groups_and_selects_the_default():
    app = QApplication.instance() or QApplication([])
    combo = QComboBox()

    assert populate_sound_combo(combo, "random ass/notification.mp3")
    assert combo.currentData() == "random ass/notification.mp3"
    assert any(item.startswith("[French]") for item in
               [combo.itemText(i) for i in range(combo.count())])

    previews = []
    dialog = FirstRunDialog(DEFAULT_SOUND, previews.append)
    dialog.preview_button.click()
    assert previews == [DEFAULT_SOUND]


def test_settings_preview_is_enabled_and_calls_the_player(monkeypatch):
    app = QApplication.instance() or QApplication([])
    database = Database(":memory:")
    processor = JournalProcessor(database, SpeciesDB())
    window = MainWindow(processor, JournalMonitor(""), WindowSettings())
    played = []
    window._play_sound = played.append

    def preview_from_settings(dialog):
        assert dialog.btn_preview.isEnabled()
        dialog._preview_sound()
        return 0

    monkeypatch.setattr(SettingsDialog, "exec", preview_from_settings)
    window.open_settings()
    assert played == [DEFAULT_SOUND]

    window.close()
    database.close()


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
