"""Application entry point."""

import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from .config import APP_NAME, Settings
from .journal import JournalMonitor, default_journal_dir
from .database import Database
from .species import SpeciesDB
from .processor import JournalProcessor
from .ui.main_window import MainWindow
from .paths import user_data_dir, resource_path

DB_PATH = os.path.join(user_data_dir(), "edbio.db")

# Application icon, bundled with the package.
ICON_PATH = resource_path("resources/icon.png")


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
