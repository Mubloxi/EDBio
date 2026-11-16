"""Genetic sample tracking state machine.

ScanOrganic journal events arrive with ScanType: Log, Sample, or Analyse.
A species progresses: 0 samples (not seen) -> Logged (1) -> Sampled (2) ->
Analysed/Complete (3). Each sample needs a minimum genetic diversity distance
from the reference sample before the next one counts.
"""

from .distance import haversine_meters, format_distance

LOG = "Log"
SAMPLE = "Sample"
ANALYSE = "Analyse"

NOT_STARTED = "Not Started"
SAMPLING = "Sampling"
COMPLETE = "Complete"


class SampleTracker:
    def __init__(self, system_address, body_id, genus, species,
                 planet_radius=None, distance_required=None):
        self.system_address = system_address
        self.body_id = body_id
        self.genus = genus
        self.species = species
        self.planet_radius = planet_radius
        self.distance_required = distance_required or 500.0
        self.scan_count = 0
        self.reference_lat = None
        self.reference_lon = None
        self.current_lat = None
        self.current_lon = None
        self.status = NOT_STARTED
        self.last_scan_type = None
        self.distance_traveled = None
        self.remaining = None

    def update_position(self, lat, lon):
        self.current_lat = lat
        self.current_lon = lon
        self._recompute_distance()

    def set_reference(self, lat, lon):
        self.reference_lat = lat
        self.reference_lon = lon
        self._recompute_distance()

    def set_radius(self, radius):
        self.planet_radius = radius
        self._recompute_distance()

    def _recompute_distance(self):
        if self.reference_lat is None or self.reference_lon is None or \
           self.current_lat is None or self.current_lon is None or \
           self.planet_radius is None:
            self.distance_traveled = None
            self.remaining = None
            return
        from .distance import haversine_meters
        self.distance_traveled = haversine_meters(
            self.reference_lat, self.reference_lon,
            self.current_lat, self.current_lon, self.planet_radius)
        if self.distance_traveled is not None:
            self.remaining = max(0.0, self.distance_required - self.distance_traveled)

    def apply_event(self, scan_type, lat=None, lon=None):
        """Apply a ScanOrganic event. Returns True if scan count changed."""
        if scan_type == LOG:
            if self.scan_count == 0:
                self.scan_count = 1
                self.status = SAMPLING
                if lat is not None and lon is not None:
                    self.set_reference(lat, lon)
                self.last_scan_type = LOG
                return True
            # Already logged; nothing changes.
            return False
        elif scan_type == SAMPLE:
            if self.scan_count < 1:
                return False
            # A new sample counts only if we've moved far enough from reference.
            if self.scan_count == 1:
                if self.distance_traveled is not None and \
                   self.distance_traveled >= self.distance_required:
                    self.scan_count = 2
                    self.last_scan_type = SAMPLE
                    return True
                return False
            elif self.scan_count == 2:
                if self.distance_traveled is not None and \
                   self.distance_traveled >= self.distance_required:
                    self.scan_count = 3
                    self.status = COMPLETE
                    self.last_scan_type = ANALYSE
                    return True
                return False
            return False
        elif scan_type == ANALYSE:
            if self.scan_count >= 2:
                self.scan_count = 3
                self.status = COMPLETE
                self.last_scan_type = ANALYSE
                return True
            return False
        return False

    def progress_text(self):
        return f"{self.scan_count}/3"

    def distance_text(self):
        from .distance import format_distance
        return format_distance(self.distance_traveled)

    def remaining_text(self):
        from .distance import format_distance
        return format_distance(self.remaining)

    def required_text(self):
        from .distance import format_distance
        return format_distance(self.distance_required)

    def to_dict(self):
        return {
            "system_address": self.system_address,
            "body_id": self.body_id,
            "genus": self.genus,
            "species": self.species,
            "scan_count": self.scan_count,
            "status": self.status,
            "reference_lat": self.reference_lat,
            "reference_lon": self.reference_lon,
            "planet_radius": self.planet_radius,
            "distance_required": self.distance_required,
            "distance_traveled": self.distance_traveled,
            "remaining": self.remaining,
        }

    @classmethod
    def from_dict(cls, data):
        tracker = cls(
            data["system_address"], data["body_id"], data["genus"], data["species"],
            data.get("planet_radius"), data.get("distance_required"))
        tracker.scan_count = data.get("scan_count", 0)
        tracker.status = data.get("status", NOT_STARTED)
        tracker.reference_lat = data.get("reference_lat")
        tracker.reference_lon = data.get("reference_lon")
        tracker.current_lat = data.get("reference_lat")
        tracker.current_lon = data.get("reference_lon")
        tracker.distance_traveled = data.get("distance_traveled")
        tracker.remaining = data.get("remaining")
        return tracker
