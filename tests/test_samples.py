"""Tests for the genetic sample tracking state machine."""

from samples import SampleTracker, LOG, SAMPLE, ANALYSE, NOT_STARTED, SAMPLING, COMPLETE


def test_tracker_log_then_sample_distance_gated():
    t = SampleTracker(1, 1, "Stratum", "Stratum Tectonicas",
                      planet_radius=1000000, distance_required=500.0)
    assert t.status == NOT_STARTED
    assert t.scan_count == 0

    # Log the first sample with coordinates -> becomes reference.
    assert t.apply_event(LOG, lat=0.0, lon=0.0) is True
    assert t.scan_count == 1
    assert t.status == SAMPLING
    assert t.reference_lat == 0.0

    # Same coordinates again: no change.
    assert t.apply_event(LOG, lat=0.0, lon=0.0) is False
    assert t.scan_count == 1

    # Move 700m away from reference (radius 1e6m, ~0.04 deg lon at equator): sample counts.
    t.update_position(0.0, 0.04)
    assert t.apply_event(SAMPLE) is True
    assert t.scan_count == 2

    # Move further (~1.4km), analyse -> complete.
    t.update_position(0.0, 0.08)
    assert t.apply_event(ANALYSE) is True
    assert t.scan_count == 3
    assert t.status == COMPLETE


def test_sample_below_required_distance_not_counted():
    t = SampleTracker(1, 1, "Stratum", "Stratum Tectonicas",
                      planet_radius=1000000, distance_required=500.0)
    t.apply_event(LOG, lat=0.0, lon=0.0)
    # Only move 100m (~0.0057 deg), below 500m required.
    t.update_position(0.0, 0.0057)
    assert t.apply_event(SAMPLE) is False
    assert t.scan_count == 1


def test_missing_coordinates_unknown():
    t = SampleTracker(1, 1, "Stratum", "Stratum Tectonicas",
                      planet_radius=1000000, distance_required=500.0)
    t.apply_event(LOG)  # no coords
    assert t.distance_traveled is None
    assert t.remaining is None
    assert t.distance_text() == "Unknown"
    assert t.remaining_text() == "Unknown"


def test_missing_radius_unknown():
    t = SampleTracker(1, 1, "Stratum", "Stratum Tectonicas", planet_radius=None)
    t.apply_event(LOG, lat=0.0, lon=0.0)
    t.update_position(0.0, 0.01)
    assert t.distance_traveled is None
    assert t.remaining is None


def test_progress_text_and_status():
    t = SampleTracker(1, 1, "Stratum", "Stratum Tectonicas",
                      planet_radius=1000000, distance_required=500.0)
    assert t.progress_text() == "0/3"
    t.apply_event(LOG, lat=0.0, lon=0.0)
    assert t.progress_text() == "1/3"
    t.update_position(0.0, 0.04)  # ~700m, above 500m required
    t.apply_event(SAMPLE)
    assert t.progress_text() == "2/3"
