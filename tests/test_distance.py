"""Tests for great-circle distance calculations."""

from edbio.distance import haversine_meters, format_distance


def test_haversine_same_point():
    d = haversine_meters(0.0, 0.0, 0.0, 0.0, 1000000.0)
    assert d == 0.0


def test_haversine_known_distance():
    # Equator, 1 degree of longitude on radius 1e6 m = pi/180 * 1e6 m.
    d = haversine_meters(0.0, 0.0, 0.0, 1.0, 1000000.0)
    expected = (3.1415926535 / 180.0) * 1000000.0
    assert abs(d - expected) < 1.0


def test_haversine_missing_inputs():
    assert haversine_meters(None, 0.0, 0.0, 0.0, 1000000.0) is None
    assert haversine_meters(0.0, 0.0, None, 0.0, 1000000.0) is None
    assert haversine_meters(0.0, 0.0, 0.0, 0.0, None) is None
    assert haversine_meters(0.0, 0.0, 0.0, 0.0, 0.0) is None


def test_format_distance():
    assert format_distance(None) == "Unknown"
    assert format_distance(430) == "430m"
    assert format_distance(1500) == "1.50km"
