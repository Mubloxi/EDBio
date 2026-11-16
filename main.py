"""Application entry point."""

import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from config import APP_NAME, Settings
from journal import JournalMonitor
from database import Database
from species import SpeciesDB
from processor import JournalProcessor
from ui.main_window import MainWindow
from paths import user_data_dir, resource_path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

DB_PATH = os.path.join(user_data_dir(), "edbio.db")

# Application icon. Your SVG is used directly for the window/taskbar icon;
# the ICO is embedded in the exe by PyInstaller via build_exe.py.
ICON_PATH = resource_path("resources/icon.png")
SVG_ICON_PATH = resource_path("resources/EDBio-icon.svg")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Use your SVG icon directly (PySide6 renders SVG natively).
    if os.path.exists(SVG_ICON_PATH):
        app.setWindowIcon(QIcon(SVG_ICON_PATH))
    elif os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    settings = Settings()

    db = Database(DB_PATH)
    species_db = SpeciesDB()
    processor = JournalProcessor(db, species_db)

    monitor = JournalMonitor(settings.journal_dir())

    window = MainWindow(processor, monitor, settings, ICON_PATH)
    window.show()
    window.prompt_first_run()
    # Start only after the window has connected its signals, otherwise the
    # initial journal replay can be emitted before anyone is listening.
    monitor.start()

    try:
        sys.exit(app.exec())
    finally:
        monitor.stop()
        db.close()


if __name__ == "__main__":
    main()
