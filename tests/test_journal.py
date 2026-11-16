"""Tests for the journal reader: parsing, rotation, incremental reading, dedup."""

import os
import json
import tempfile
import time

import pytest

from edbio.journal import JournalReader, journal_files, current_journal_file, parse_event_line
from edbio.processor import JournalProcessor


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _event(event_type, **fields):
    evt = {"timestamp": "2023-05-01T12:00:00Z", "event": event_type}
    evt.update(fields)
    return json.dumps(evt)


def test_parse_event_line_valid():
    line = '{"timestamp":"2023-05-01T12:00:00Z","event":"LoadGame","Commander":"Cmdr"}'
    evt = parse_event_line(line)
    assert evt["event"] == "LoadGame"
    assert evt["Commander"] == "Cmdr"


def test_parse_event_line_malformed():
    assert parse_event_line("{not json") is None
    assert parse_event_line("") is None
    assert parse_event_line("   ") is None


def test_incremental_reading():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "Journal.230501-120000.part1.log")
    _write(path, _event("FileHeader") + "\n" + _event("LoadGame", Commander="A") + "\n")

    reader = JournalReader(path)
    events = list(reader.read_new_events())
    assert len(events) == 2
    assert events[0]["event"] == "FileHeader"
    assert events[1]["event"] == "LoadGame"
    assert reader.position > 0


def test_incremental_reading_continues():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "Journal.230501-120000.part1.log")
    _write(path, _event("FileHeader") + "\n")

    reader = JournalReader(path)
    events = list(reader.read_new_events())
    assert len(events) == 1
    pos = reader.position

    # Append more data and read again.
    with open(path, "a", encoding="utf-8") as f:
        f.write(_event("Location", StarSystem="Sol") + "\n")
    events = list(reader.read_new_events())
    assert len(events) == 1
    assert events[0]["event"] == "Location"
    assert reader.position > pos


def test_partial_line_buffering():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "Journal.230501-120000.part1.log")
    _write(path, _event("FileHeader") + "\n")

    reader = JournalReader(path)
    events = list(reader.read_new_events())
    assert len(events) == 1

    # Write a partial line (no trailing newline).
    with open(path, "a", encoding="utf-8") as f:
        f.write(_event("LoadGame", Commander="B"))

    events = list(reader.read_new_events())
    assert events == []  # partial line not yielded yet

    # Complete the line.
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + _event("FSDJump", StarSystem="Sol") + "\n")
    events = list(reader.read_new_events())
    assert len(events) == 2
    assert events[0]["event"] == "LoadGame"
    assert events[1]["event"] == "FSDJump"


def test_journal_rotation():
    tmp = tempfile.mkdtemp()
    path1 = os.path.join(tmp, "Journal.230501-120000.part1.log")
    path2 = os.path.join(tmp, "Journal.230501-120050.part2.log")
    _write(path1, _event("FileHeader") + "\n")

    reader = JournalReader(path1)
    events = list(reader.read_new_events())
    assert len(events) == 1

    # Simulate rotation: replace file1 content with a brand new file2.
    os.remove(path1)
    _write(path2, _event("LoadGame", Commander="C") + "\n")

    # Point reader at the new file.
    reader.path = path2
    reader.position = 0
    reader.buffer = ""
    reader._refresh_stat()
    events = list(reader.read_new_events())
    assert len(events) == 1
    assert events[0]["event"] == "LoadGame"


def test_duplicate_event_prevention():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "Journal.230501-120000.part1.log")
    line = _event("ScanOrganic", ScanType="Log", Genus="$Codex_Ent_Stratum_Genus_Name;",
                  Species="$Codex_Ent_Stratum_07_Name;", SystemAddress=1, Body=2) + "\n"
    _write(path, line + line)  # duplicate line

    reader = JournalReader(path)
    events = list(reader.read_new_events())
    assert len(events) == 2  # reader yields both lines

    from edbio.species import SpeciesDB
    from edbio.database import Database
    db = Database(":memory:")
    sdb = SpeciesDB()
    proc = JournalProcessor(db, sdb)
    evt1 = json.loads(line)
    evt2 = json.loads(line)
    proc.handle_event(evt1)
    proc.handle_event(evt2)
    trackers = proc.sample_trackers()
    assert len(trackers) == 1
    assert trackers[0].scan_count == 1
    db.close()


def test_multiple_commanders():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "Journal.230501-120000.part1.log")
    _write(path, _event("LoadGame", Commander="Alpha") + "\n" +
             _event("LoadGame", Commander="Beta") + "\n")

    reader = JournalReader(path)
    events = list(reader.read_new_events())
    assert events[0]["Commander"] == "Alpha"
    assert events[1]["Commander"] == "Beta"


def test_journal_files_sorted():
    tmp = tempfile.mkdtemp()
    first = os.path.join(tmp, "Journal.230501-120000.part1.log")
    second = os.path.join(tmp, "Journal.230501-120050.part2.log")
    _write(first, "")
    _write(second, "")
    # Journals are ordered by last write time, not filename: some game builds
    # emit names like Journal.261011193104.01.log that sort incorrectly.
    os.utime(first, (1000000000, 1000000000))
    os.utime(second, (1000000100, 1000000100))
    files = journal_files(tmp)
    assert len(files) == 2
    assert files[0].endswith("part1.log")
    assert files[1].endswith("part2.log")


def test_current_journal_ignores_bad_filenames():
    tmp = tempfile.mkdtemp()
    real = os.path.join(tmp, "Journal.2026-11-15T172402.01.log")
    odd = os.path.join(tmp, "Journal.261011193104.01.log")
    _write(real, _event("Location", StarSystem="Matet") + "\n")
    _write(odd, _event("Location", StarSystem="Old") + "\n")
    # The odd-named file is older even though its name sorts last.
    os.utime(odd, (1000000000, 1000000000))
    os.utime(real, (1000000100, 1000000100))
    assert current_journal_file(tmp) == real


def test_status_flags_integer_does_not_crash():
    from edbio.journal import JournalMonitor

    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "Status.json"), "w", encoding="utf-8") as f:
        json.dump({"timestamp": "2026-11-15T17:57:37Z", "event": "Status", "Flags": 0}, f)

    monitor = JournalMonitor(tmp)
    # Must not raise AttributeError: 'int' object has no attribute 'get'.
    monitor._read_status()
    assert monitor.game_running is True
