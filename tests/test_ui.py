"""Tests for user-facing empty states."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from edbio.credits import CreditCalculator
from edbio.ui.exobiology_tab import ExobiologyTab


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

    app.quit()
