# distance calculations for planets and species 

import math


def haversine_meters(lat1, lon1, lat2, lon2, radius_meters):
    """Great-circle distance between two points on a sphere, in meters.

    Returns None if any input is missing or the radius is unavailable.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    if radius_meters is None or radius_meters <= 0:
        return None

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_meters * c


def format_distance(meters):
    """Format a distance in meters for display. Returns 'Unknown' if None."""
    if meters is None:
        return "Unknown"
    if meters < 1000:
        return f"{meters:.0f}m"
    return f"{meters / 1000:.2f}km"
