# EDBio

A small exobiology tool for Elite Dangerous. Reads the game journal to track
biological samples, predict possible species, and show estimated Vista Genomics
payouts. No login, no account, no companion application required.

## Features

- Reads Elite Dangerous journal files in real time (incremental, handles rotation)
- Detects the current commander, system, and planet from the journal
- Lists biological signals and predicted species for the active planet
- Tracks genetic sample progress using ScanOrganic events (Log / Sample / Analyse)
- Calculates surface distance from the reference sample using great-circle math
- Shows estimated Vista Genomics payouts per species and per planet
- First footfall multiplier shown as an estimate, never guaranteed
- History tab with search, filtering, and CSV export (stored in SQLite)
- Always-on-top, minimize to system tray, remembers window size and position
- Manual journal directory selection
- Settings dialog and About dialog

## Download

Pre-built Windows releases are available on the GitHub Releases page for this
repository. There is no installer; download EDBio.exe and run it.

## How To Use

1. Download EDBio.exe and run it. Python does not need to be installed.
2. Start Elite Dangerous and load into a game.
3. EDBio detects the journal directory automatically
   (%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous\).
   If it doesn't, use File > Journal Directory to pick it manually.
4. Fly to a planet, scan it, and use the Surface Area Scanner. Biological
   signals, predicted species, and sample tracking appear in the Exobiology tab.
5. Land and collect genetic samples. Sample progress, distance required, and
   distance remaining update as you move.
6. Use the History tab to review past discoveries and export to CSV.

The application opens normally even when Elite Dangerous is closed, showing
saved data from previous sessions.

## Requirements

- Windows 10 or Windows 11
- Elite Dangerous with Odyssey (for journal-based tracking)
- No Python installation required for the pre-built executable

## Building From Source

```bash
# Clone the repository
git clone <repository-url>
cd EDBio

# Create a virtual environment (optional but recommended)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run from source
python edbio/main.py

# Build the standalone Windows executable
python build_exe.py
```

The resulting executable is in dist\EDBio.exe.

## Known Issues

- Species prediction relies on community-documented environmental requirements.
  Some species have incomplete requirement data and are shown with whatever is
  known; missing requirements do not prevent a prediction but reduce confidence.
- First footfall bonuses are estimates. The game determines actual first
  footfall eligibility, which EDBio cannot verify from the journal.
- Genetic distance tracking requires the player to be on the planet surface
  with latitude and longitude available (Touchdown event). Without coordinates,
  distance is shown as Unknown.

## Credits

- PySide6 (Qt for Python) - LGPL
- Pillow - HPND
- PyInstaller - GPL (build tool only, not distributed with the app)
- pytest - MIT

Biological reference data and Vista Genomics prices are compiled from public
Elite Dangerous community documentation (ED-DSN, Canonn, Elite Dangerous Wiki).
Species names, planetary data, and Elite Dangerous content are the property of
Frontier Developments plc.

This project does not incorporate code from EDMC BioScan (GPL) or EDEXO
(PolyForm Noncommercial / CC BY-NC-SA), both of which carry incompatible
licenses for this project.

## Disclaimer

EDBio is not affiliated with Frontier Developments, the developers of Elite
Dangerous. Elite Dangerous is a trademark of Frontier Developments plc.
