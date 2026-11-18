# Processes journal events into application state: planets, predictions, samples. totaly wasnt autto complete ;)

import hashlib
import json
import re
from datetime import datetime, timezone

from species import (
    SpeciesDB, PREDICTED, GENUS_CONFIRMED, SPECIES_CONFIRMED,
    SAMPLING, COMPLETE, UNKNOWN,
)
from samples import SampleTracker, LOG, SAMPLE, ANALYSE, NOT_STARTED
from distance import haversine_meters
from credits import CreditCalculator


class JournalProcessor:
    def __init__(self, database, species_db):
        self.db = database
        self.species = species_db
        self.credits = CreditCalculator()

        # Current state.
        self.current_system = None
        self.current_body = None
        self.current_commander = None
        self.current_station = None
        self.system_address = None

        # Body data keyed by body name within current system.
        self.bodies = {}
        # Biological signals per body: body_name -> list of signal dicts.
        self.signals = {}
        # Genuses detected per body (from SAASignalsFound).
        self.body_genuses = {}
        # Active sample trackers keyed by (genus, species).
        self.trackers = {}
        # Planet radius for current body (from Status.json / Scan).
        self.planet_radius = None
        self.current_lat = None
        self.current_lon = None
        self._replaying = False
        self._event_is_new = True

        # Callbacks for UI to register.
        self.on_planet_updated = None
        self.on_sample_updated = None
        self.on_history_added = None

    # --- position updates from Status.json / Touchdown ---

    def set_position(self, lat, lon):
        self.current_lat = lat
        self.current_lon = lon
        for tracker in self.trackers.values():
            tracker.update_position(lat, lon)

    def set_planet_radius(self, radius):
        self.planet_radius = radius
        for tracker in self.trackers.values():
            tracker.set_radius(radius)

    # --- context set by journal ---

    def set_system(self, system_name, system_address=None):
        if system_name != self.current_system:
            self.current_system = system_name
            self.system_address = system_address
            self._clear_planet_state()
            # Persist planets for the old system are already in the DB.

    def set_body(self, body_name):
        self.current_body = body_name

    def _clear_planet_state(self):
        self.current_body = None
        self.bodies = {}
        self.signals = {}
        self.body_genuses = {}
        self.trackers = {}
        self.planet_radius = None
        self.current_lat = None
        self.current_lon = None

    # --- event handling ---

    def begin_replay(self):
        self._replaying = True
        self.current_system = None
        self.current_commander = None
        self.current_station = None
        self.system_address = None
        self.current_lat = None
        self.current_lon = None
        self._clear_planet_state()

    def end_replay(self):
        self._replaying = False

    def handle_event(self, event):
        event_id = hashlib.sha256(
            json.dumps(
                event, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        self._event_is_new = not self.db.is_processed(event_id)

        etype = event.get("event")

        if etype == "LoadGame":
            self.current_commander = event.get("Commander")
            self.current_system = event.get("StarSystem")
            self.system_address = event.get("SystemAddress")
            self.current_station = None
            self._clear_planet_state()
        elif etype == "Location":
            self.set_system(event.get("StarSystem"), event.get("SystemAddress"))
            self.current_body = event.get("Body")
        elif etype == "FSDJump":
            self.current_system = event.get("StarSystem")
            self.system_address = event.get("SystemAddress")
            self.current_station = None
            self._clear_planet_state()
        elif etype == "Docked":
            self.current_system = event.get("StarSystem") or self.current_system
            self.current_station = event.get("StationName")
        elif etype == "Undocked":
            self.current_station = None
        elif etype == "Scan":
            self._handle_scan(event)
        elif etype == "FSSBodySignals":
            self._handle_fss_signals(event)
        elif etype == "SAASignalsFound":
            self._handle_saa_signals(event)
        elif etype == "Touchdown":
            self._handle_touchdown(event)
        elif etype == "Liftoff":
            self.current_body = None
        elif etype == "ScanOrganic":
            self._handle_scan_organic(event)
        elif etype == "CodexEntry":
            self._handle_codex_entry(event)

        if self._event_is_new:
            self.db.mark_processed(event_id, etype, event.get("timestamp", ""))
        return self._event_is_new

    def _handle_scan(self, event):
        body_name = event.get("BodyName")
        if not body_name:
            return
        self.set_body(body_name)

        known_signals = self.signals.get(body_name, {}).get("all_signals", [])
        genuse_names = self.body_genuses.get(body_name, [])
        body = {
            "system_address": event.get("SystemAddress"),
            "body_id": event.get("BodyID"),
            "system_name": self.current_system,
            "body_name": body_name,
            "planet_class": event.get("PlanetClass"),
            "atmosphere": event.get("Atmosphere", ""),
            "atmosphere_type": event.get("AtmosphereType", ""),
            "temperature": event.get("SurfaceTemperature"),
            "gravity": event.get("SurfaceGravity"),
            "volcanism": event.get("Volcanism", ""),
            "radius": event.get("Radius"),
            "surface_gravity": event.get("SurfaceGravity"),
            "star_type": event.get("StarType"),
            "signals": known_signals,
            "genuses": genuse_names,
            "estimated_value": 0,
            "status": "Scanned",
        }
        self.bodies[body_name] = body
        self.planet_radius = event.get("Radius")

        # Persist to database.
        self.db.upsert_planet(body)

        # Estimate value based on predicted species.
        genuses = self.body_genuses.get(body_name, [])
        predictions = self.species.predict_all(body, genuses)
        est = self._estimate_planet_value(predictions)
        body["estimated_value"] = est
        body["genuses"] = genuses
        self.db.upsert_planet(body)

        if self.on_planet_updated:
            self.on_planet_updated(body)

    def _handle_fss_signals(self, event):
        body_name = event.get("BodyName")
        if not body_name:
            return
        self.set_body(body_name)
        signals = event.get("Signals", [])
        bio_signals = [s for s in signals if s.get("Type_Localised") == "Biological" or
                       s.get("Type") == "$SAA_SignalType_Biological;"]
        count = sum(s.get("Count", 0) for s in bio_signals)
        self.signals[body_name] = {
            "biological_count": count,
            "all_signals": signals,
        }
        if body_name in self.bodies:
            self.bodies[body_name]["signals"] = signals
            self.db.upsert_planet(self.bodies[body_name])

    def _handle_saa_signals(self, event):
        body_name = event.get("BodyName")
        if not body_name:
            return
        self.set_body(body_name)
        signals = event.get("Signals", [])
        genuses = event.get("Genuses", [])
        genuse_names = []
        for g in genuses:
            name = self.species.normalize_genus(g.get("Genus"))
            if name:
                genuse_names.append(name)
        self.body_genuses[body_name] = genuse_names
        self.signals[body_name] = {
            "biological_count": sum(s.get("Count", 0) for s in signals
                                    if s.get("Type_Localised") == "Biological"),
            "all_signals": signals,
        }
        if body_name in self.bodies:
            self.bodies[body_name]["genuses"] = genuse_names
            self.bodies[body_name]["signals"] = signals
            predictions = self.species.predict_all(self.bodies[body_name], genuse_names)
            self.bodies[body_name]["estimated_value"] = self._estimate_planet_value(predictions)
            self.db.upsert_planet(self.bodies[body_name])

    def _handle_touchdown(self, event):
        body_name = event.get("BodyName")
        if body_name:
            self.set_body(body_name)
        lat = event.get("Latitude")
        lon = event.get("Longitude")
        if lat is not None and lon is not None:
            self.set_position(lat, lon)
        self.current_body = body_name

    def _handle_scan_organic(self, event):
        genus_codex = event.get("Genus", "")
        species_codex = event.get("Species", "")
        species_localised = event.get("Species_Localised") or ""
        genus, species_name = self.species.resolve_species(genus_codex, species_codex)
        if species_localised:
            species_name = species_localised
        scan_type = event.get("ScanType")
        system_address = event.get("SystemAddress")
        body_id = event.get("Body")

        if not genus or not species_name:
            return

        key = (genus, species_name)
        tracker = self.trackers.get(key)
        if tracker is None and not self._replaying:
            # Try loading from DB.
            row = self._load_tracker(system_address, body_id, genus, species_name)
            if row:
                tracker = SampleTracker.from_dict(row)
        if tracker is None:
            tracker = SampleTracker(system_address, body_id, genus, species_name,
                                    self.planet_radius)
            # Start the tracker from the current known position, if any.
            if self.current_lat is not None and self.current_lon is not None:
                tracker.update_position(self.current_lat, self.current_lon)
            self.trackers[key] = tracker

        changed = tracker.apply_event(scan_type, self.current_lat, self.current_lon)
        if changed and self._event_is_new:
            self.db.upsert_sample(tracker.to_dict())
        if changed and self.on_sample_updated:
            self.on_sample_updated(tracker.to_dict())

        # If a species was fully analysed, record it in history.
        if tracker.status == COMPLETE and changed and self._event_is_new:
            value = self.species.species_price(species_name) or 0
            self._add_history(
                system=self.current_system or "Unknown",
                planet=self.current_body or "Unknown",
                species=species_name,
                samples=tracker.scan_count,
                value=value,
                status=COMPLETE,
            )

    def _handle_codex_entry(self, event):
        # CodexEntry records a discovery. We can use it to mark a species
        # as genus/species confirmed.
        body_name = event.get("BodyName") or self.current_body
        entry_name = event.get("Name", "")
        # CodexEntry names are codex strings; we keep it simple and record history.
        if entry_name and self._event_is_new:
            self._add_history(
                system=self.current_system or "Unknown",
                planet=body_name or "Unknown",
                species=entry_name,
                samples=0,
                value=0,
                status=SPECIES_CONFIRMED,
            )

    # --- helpers ---

    def _load_tracker(self, system_address, body_id, genus, species):
        rows = self.db.get_samples(system_address, body_id)
        for row in rows:
            if row["genus"] == genus and row["species"] == species:
                return row
        return None

    def _estimate_planet_value(self, predictions):
        total = 0
        for p in predictions:
            val = p.get("base_value")
            if val:
                total += val
        return total

    def _add_history(self, system, planet, species, samples, value, status):
        record = {
            "date": datetime.now(timezone.utc).isoformat(),
            "system": system,
            "planet": planet,
            "species": species,
            "samples": samples,
            "value": value,
            "status": status,
        }
        self.db.add_history(record)
        if self.on_history_added:
            self.on_history_added(record)

    # --- queries used by the UI ---

    def current_planet(self):
        if self.current_body and self.current_body in self.bodies:
            return self.bodies[self.current_body]
        if self.current_body and self.current_system:
            for planet in self.db.get_planets(self.current_system):
                if planet.get("body_name") == self.current_body:
                    self.bodies[self.current_body] = planet
                    self.body_genuses[self.current_body] = planet.get("genuses") or []
                    self.signals[self.current_body] = {
                        "all_signals": planet.get("signals") or [],
                        "biological_count": sum(
                            signal.get("Count", 0)
                            for signal in planet.get("signals") or []
                            if signal.get("Type_Localised") == "Biological"
                        ),
                    }
                    self.planet_radius = planet.get("radius")
                    return planet
        return None

    def planets_in_system(self):
        return list(self.bodies.values())

    def all_db_planets(self):
        return self.db.get_planets(self.current_system)

    def predictions_for_current_planet(self):
        planet = self.current_planet()
        if not planet:
            return []
        genuses = self.body_genuses.get(self.current_body, [])
        return self.species.predict_all(planet, genuses)

    def sample_trackers(self):
        return list(self.trackers.values())

    def get_tracker(self, genus, species):
        return self.trackers.get((genus, species))
