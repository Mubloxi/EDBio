"""Application entry point."""

import sys
import os

# Allow running directly: python edbio/main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from edbio.config import APP_NAME, Settings
from edbio.journal import JournalMonitor, default_journal_dir
from edbio.database import Database
from edbio.species import SpeciesDB
from edbio.processor import JournalProcessor
from edbio.ui.main_window import MainWindow
from edbio.paths import user_data_dir, resource_path

DB_PATH = os.path.join(user_data_dir(), "edbio.db")

# Application icon, bundled with the package.
ICON_PATH = resource_path("resources/icon.png")
SVG_ICON_PATH = resource_path("resources/EDBio-icon.svg")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    settings = Settings()

    db = Database(DB_PATH)
    species_db = SpeciesDB()
    processor = JournalProcessor(db, species_db)

    monitor = JournalMonitor(default_journal_dir())
    monitor.start()

    window = MainWindow(processor, monitor, settings, ICON_PATH)
    window.show()

    try:
        sys.exit(app.exec())
    finally:
        monitor.stop()
        db.close()


if __name__ == "__main__":
    main()
