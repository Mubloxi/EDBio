import json

import pytest

from stations import search_nearest_vista_station


class FakeResponse:
    def __init__(self, data):
        self.data = json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.data


def test_spansh_finds_nearest_vista_station(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return FakeResponse({
            "results": [{
                "name": "Vista Station",
                "system_name": "Sol",
                "distance": 0.0,
                "distance_to_arrival": 125,
                "updated_at": "2026-11-16T12:00:00Z",
                "services": [{"name": "Vista Genomics"}],
            }]
        })

    monkeypatch.setattr("stations.urlopen", fake_urlopen)
    result = search_nearest_vista_station("Sol", 50)

    assert result["station"] == "Vista Station"
    assert result["system"] == "Sol"
    assert result["source"] == "Spansh"
    assert seen["timeout"] == 10
    payload = json.loads(seen["request"].data)
    assert payload["reference_system"] == "Sol"
    assert payload["filters"]["distance"] == {"min": 0, "max": 50}
    assert payload["filters"]["services"][0]["name"]["value"] == ["Vista Genomics"]


def test_spansh_result_must_include_vista_genomics(monkeypatch):
    monkeypatch.setattr(
        "stations.urlopen",
        lambda *args, **kwargs: FakeResponse({
            "results": [{
                "name": "Other Station",
                "services": [{"name": "Universal Cartographics"}],
            }]
        }),
    )
    assert search_nearest_vista_station("Sol", 25) is None


@pytest.mark.parametrize("system,radius", [("", 25), ("Sol", 24), ("Sol", 5000)])
def test_station_search_rejects_invalid_query(system, radius):
    with pytest.raises(ValueError):
        search_nearest_vista_station(system, radius)
