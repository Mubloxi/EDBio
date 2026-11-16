"""Application configuration and persistent settings."""

import os
from PySide6.QtCore import QSettings

APP_NAME = "EDBio"
ORGANIZATION = "EDBio"
VERSION = "1.0.0"

DEFAULT_JOURNAL_DIR = os.path.join(
    os.environ.get("USERPROFILE", ""),
    "Saved Games",
    "Frontier Developments",
    "Elite Dangerous",
)

# Minimum distance (meters) required between genetic samples, per species.
# The journal gives us the required distance via the sampling sequence; these
# are fallbacks when the game doesn't report it.
DEFAULT_SAMPLE_DISTANCE = 500.0

# Vista Genomics first discovery (first footfall) payout multiplier.
FIRST_FOOTFALL_MULTIPLIER = 4


class Settings:
    """Wrapper around QSettings for EDBio preferences."""

    def __init__(self):
        self.settings = QSettings(ORGANIZATION, APP_NAME)

    def get(self, key, default=None):
        return self.settings.value(key, default)

    def set(self, key, value):
        self.settings.setValue(key, value)

    # --- convenience accessors ---

    def journal_dir(self):
        value = self.get("journal_dir", DEFAULT_JOURNAL_DIR)
        return value or DEFAULT_JOURNAL_DIR

    def set_journal_dir(self, path):
        self.set("journal_dir", path)

    def always_on_top(self):
        return bool(self.get("always_on_top", False))

    def set_always_on_top(self, value):
        self.set("always_on_top", bool(value))

    def minimize_to_tray(self):
        return bool(self.get("minimize_to_tray", True))

    def set_minimize_to_tray(self, value):
        self.set("minimize_to_tray", bool(value))

    def window_geometry(self):
        return self.get("window_geometry", None)

    def set_window_geometry(self, geometry):
        self.set("window_geometry", geometry)

    def window_state(self):
        return self.get("window_state", None)

    def set_window_state(self, state):
        self.set("window_state", state)

    def current_tab(self):
        return int(self.get("current_tab", 0))

    def set_current_tab(self, index):
        self.set("current_tab", int(index))

    def min_value_threshold(self):
        return float(self.get("min_value_threshold", 0))

    def set_min_value_threshold(self, value):
        self.set("min_value_threshold", float(value))

    def notify_valuable(self):
        return bool(self.get("notify_valuable", True))

    def set_notify_valuable(self, value):
        self.set("notify_valuable", bool(value))

    def last_commander(self):
        return self.get("last_commander", "")

    def set_last_commander(self, name):
        self.set("last_commander", name)
