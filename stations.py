# spansh station search for nearest Vista genocide service

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

from config import VERSION, VISTA_SEARCH_RADII


SPANSH_STATION_SEARCH_URL = "https://spansh.co.uk/api/stations/search"


def search_nearest_vista_station(system_name, radius):
    """Return the nearest listed Vista Genomics station around a system."""
    if not system_name or not system_name.strip():
        raise ValueError("A current system is required to search for stations.")
    if radius not in VISTA_SEARCH_RADII:
        raise ValueError(f"Unsupported search radius: {radius}")

    payload = {
        "filters": {
            "distance": {"min": 0, "max": radius},
            "services": [{"name": {"value": ["Vista Genomics"]}}],
        },
        "sort": [{"distance": {"direction": "asc"}}],
        "size": 1,
        "page": 0,
        "reference_system": system_name.strip(),
    }
    request = Request(
        SPANSH_STATION_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"EDBio/{VERSION}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Spansh station search failed (HTTP {exc.code}).") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Spansh: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise RuntimeError(f"Spansh station search failed: {exc}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("Spansh returned an invalid station-search response.") from exc

    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise RuntimeError("Spansh returned an unexpected station-search response.")
    results = data.get("results", [])
    for station in results:
        if not isinstance(station, dict):
            continue
        services = station.get("services") or []
        if not any(
            (service.get("name") if isinstance(service, dict) else service)
            == "Vista Genomics"
            for service in services
        ):
            continue
        try:
            distance = float(station.get("distance") or 0)
        except (TypeError, ValueError):
            continue
        arrival_distance = station.get("distance_to_arrival")
        try:
            arrival_distance = (
                float(arrival_distance) if arrival_distance is not None else None
            )
        except (TypeError, ValueError):
            arrival_distance = None
        return {
            "station": station.get("name") or "Unknown station",
            "system": station.get("system_name") or system_name.strip(),
            "distance": distance,
            "distance_to_arrival": arrival_distance,
            "updated_at": station.get("updated_at"),
            "source": "Spansh",
            "radius": radius,
        }
    return None


class StationSearchThread(QThread):
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, system_name, radius, parent=None):
        super().__init__(parent)
        self.system_name = system_name
        self.radius = radius

    def run(self):
        try:
            result = search_nearest_vista_station(self.system_name, self.radius)
        except (ValueError, RuntimeError) as exc:
            self.failed.emit(str(exc))
        else:
            self.result_ready.emit(result)
