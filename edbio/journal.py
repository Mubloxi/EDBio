"""Elite Dangerous journal reader and real-time monitor.

Reads Journal.*.log files incrementally, handles rotation, partial lines,
duplicate events and malformed JSON. Runs in a background QThread so the UI
never blocks.
"""

import json
import os
import glob
import re
import threading
import time
from datetime import datetime, timezone

from PySide6.QtCore import QThread, Signal


# Journal events EDBio cares about.
RELEVANT_EVENTS = {
    "FileHeader", "LoadGame", "Location", "FSDJump", "Scan",
    "FSSBodySignals", "SAASignalsFound", "Touchdown", "Liftoff",
    "Disembark", "Embark", "ScanOrganic", "CodexEntry", "SellOrganicData",
}

JOURNAL_GLOB = "Journal.*.log"

# How often the monitor polls the active journal file (seconds).
POLL_INTERVAL = 1.0


def default_journal_dir():
    return os.path.join(
        os.environ.get("USERPROFILE", ""),
        "Saved Games", "Frontier Developments", "Elite Dangerous",
    )


def journal_files(journal_dir):
    """Return Journal log files sorted oldest -> newest."""
    if not journal_dir or not os.path.isdir(journal_dir):
        return []
    files = glob.glob(os.path.join(journal_dir, JOURNAL_GLOB))
    return sorted(files)


def current_journal_file(journal_dir):
    """The most recently written journal file, or None."""
    files = journal_files(journal_dir)
    return files[-1] if files else None


def parse_event_line(line):
    """Parse a single JSON journal line. Returns dict or None on failure."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None


class JournalReader:
    """Incremental reader for a single journal file with partial-line buffering."""

    def __init__(self, path):
        self.path = path
        self.position = 0
        self.buffer = ""
        self.inode = None
        self.mtime = None
        self.size = None
        self._refresh_stat()

    def _refresh_stat(self):
        try:
            st = os.stat(self.path)
            self.inode = st.st_ino
            self.mtime = st.st_mtime
            self.size = st.st_size
        except OSError:
            self.inode = None
            self.mtime = None
            self.size = 0

    def rotated(self):
        """True if the file was replaced (rotation)."""
        try:
            st = os.stat(self.path)
            if self.inode is not None and st.st_ino != self.inode:
                return True
        except OSError:
            return True
        return False

    def read_new_events(self):
        """Yield new complete events from the file since last read."""
        if not os.path.exists(self.path):
            return

        if self.rotated():
            # File was rotated: start from the beginning.
            self.position = 0
            self.buffer = ""
            self._refresh_stat()

        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self.position)
                data = f.read()
                self.position = f.tell()
        except OSError:
            return

        if not data:
            return

        self.buffer += data
        lines = self.buffer.split("\n")

        # The last element is a partial line unless the file ends with newline.
        # Keep it in the buffer until we get more data.
        self.buffer = lines.pop() if lines else ""

        for line in lines:
            event = parse_event_line(line)
            if event is not None:
                yield event


class JournalMonitor(QThread):
    """Background thread that watches the active journal and emits events."""

    event_received = Signal(dict)
    status_changed = Signal(dict)
    position_changed = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, journal_dir=None):
        super().__init__()
        self.journal_dir = journal_dir or default_journal_dir()
        self._running = False
        self._reader = None
        self._lock = threading.Lock()
        # Dedup memory: set of recent event signatures.
        self._seen = set()
        self._max_seen = 2000
        # Last known system / body for context.
        self.current_system = None
        self.current_body = None
        self.current_commander = None
        self.last_event_time = "--:--:--"
        self.game_running = False
        self.journal_connected = False

    def set_journal_dir(self, path):
        with self._lock:
            self.journal_dir = path
        self._reader = None

    def run(self):
        self._running = True
        while self._running:
            try:
                self._tick()
            except Exception as exc:  # keep the thread alive
                self.error_occurred.emit(str(exc))
            time.sleep(POLL_INTERVAL)

    def stop(self):
        self._running = False
        self.wait()

    def _tick(self):
        file_path = current_journal_file(self.journal_dir)
        connected = file_path is not None

        if connected and (self._reader is None or self._reader.path != file_path):
            self._reader = JournalReader(file_path)

        if self._reader is None:
            if connected != self.journal_connected:
                self.journal_connected = connected
                self._emit_status()
            return

        if not self.journal_connected:
            self.journal_connected = True
            self._emit_status()

        for event in self._reader.read_new_events():
            try:
                self._process_event(event)
            except Exception as exc:
                self.error_occurred.emit(str(exc))

        # Status.json gives live player/planet info.
        self._read_status()

    def _process_event(self, event):
        event_type = event.get("event")
        if event_type not in RELEVANT_EVENTS:
            return

        # Build a dedup signature.
        signature = self._signature(event)
        if signature and signature in self._seen:
            return
        if signature:
            self._seen.add(signature)
            if len(self._seen) > self._max_seen:
                # Drop oldest entries arbitrarily.
                self._seen = set(list(self._seen)[-self._max_seen // 2:])

        timestamp = event.get("timestamp", "")
        try:
            t = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            self.last_event_time = t.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            self.last_event_time = timestamp[11:19] if len(timestamp) >= 19 else "--:--:--"

        if event_type == "LoadGame":
            self.current_commander = event.get("Commander")
            self.current_system = event.get("StarSystem")
        elif event_type == "Location":
            self.current_system = event.get("StarSystem")
        elif event_type == "FSDJump":
            self.current_system = event.get("StarSystem")
            self.current_body = None
        elif event_type == "Scan":
            body_name = event.get("BodyName")
            if body_name:
                self.current_body = body_name

        self.game_running = True
        self._emit_status()
        self.event_received.emit(event)

    def _signature(self, event):
        """Dedup key: timestamp + event + identifying fields."""
        parts = [event.get("timestamp", ""), event.get("event", "")]
        for key in ("SystemAddress", "BodyID", "BodyName", "Genus", "Species", "ScanType"):
            if key in event:
                parts.append(str(event[key]))
        return "|".join(parts)

    def _read_status(self):
        path = os.path.join(self.journal_dir, "Status.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError, ValueError):
            return

        flags = data.get("Flags", {})
        self.game_running = flags.get("InMainGame", False) or \
                            flags.get("OnFoot", False) or \
                            flags.get("InSRV", False) or self.game_running

        lat = data.get("Latitude")
        lon = data.get("Longitude")
        radius = data.get("PlanetRadius")
        body = data.get("BodyName")
        if lat is not None or lon is not None or radius is not None or body:
            self.position_changed.emit({
                "lat": lat, "lon": lon, "radius": radius, "body": body,
            })

        self._emit_status()

    def _emit_status(self):
        self.status_changed.emit({
            "journal_connected": self.journal_connected,
            "game_running": self.game_running,
            "system": self.current_system,
            "commander": self.current_commander,
            "body": self.current_body,
            "last_event_time": self.last_event_time,
        })
