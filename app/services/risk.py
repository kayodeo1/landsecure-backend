"""LandSecure risk engine — server-side port of the documented algorithm.

This implements the pseudocode from the report (§3.10, Table 3.3) and
``implementation_plan.md`` §5.1 exactly:

    if point is inside one or more zones:
        score = max(severity_weight) + 5 * (extra_zones)
    elif nearest zone within 500 m:
        score = round(35 + 0.45 * severity_weight(nearest) * decay)   # decay = 1 - d/500
    else:
        score = 6                                                     # clear baseline

    level = HIGH if score >= 75 else MEDIUM if score >= 60 else LOW

The point-in-polygon (ray casting) and edge-sampled haversine distance mirror
``site/assets/js/risk.js`` so verdicts match the mockup. On a PostGIS deployment
the same contract is served by ``risk_postgis.py`` using ``ST_Contains`` /
``ST_Distance``; this pure-Python implementation is the canonical, dependency-free
reference (and what the SQLite dev path uses).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

SEVERITY_WEIGHT: dict[str, int] = {"high": 100, "medium": 70, "low": 40}
PROXIMITY_BUFFER_M: float = 500.0       # within this distance of a zone = elevated risk
BASELINE_CLEAR_SCORE: int = 6           # report Table 3.3 "Baseline (clear)"
HIGH_THRESHOLD: int = 75
MEDIUM_THRESHOLD: int = 60
EARTH_RADIUS_M: float = 6_371_000.0


# --- geometry helpers (verbatim port of risk.js) -----------------------------
def point_in_polygon(lat: float, lng: float, poly: list[list[float]]) -> bool:
    """Ray-casting test. ``poly`` is a ring of ``[lat, lng]`` pairs."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        yi, xi = poly[i][0], poly[i][1]
        yj, xj = poly[j][0], poly[j][1]
        intersect = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / (yj - yi) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres."""
    to_r = math.pi / 180.0
    d_lat = (lat2 - lat1) * to_r
    d_lng = (lng2 - lng1) * to_r
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1 * to_r) * math.cos(lat2 * to_r) * math.sin(d_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def distance_to_polygon(lat: float, lng: float, poly: list[list[float]]) -> float:
    """Approx minimum distance (m) from a point to a polygon perimeter.

    Samples each edge at 0.1 steps, mirroring ``risk.js`` so distances (and thus
    proximity-band scores) match the mockup.
    """
    minimum = math.inf
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        t = 0.0
        while t <= 1.0:
            plat = a[0] + (b[0] - a[0]) * t
            plng = a[1] + (b[1] - a[1]) * t
            d = haversine(lat, lng, plat, plng)
            if d < minimum:
                minimum = d
            t += 0.1
    return minimum


def _js_round(x: float) -> int:
    """Round half-up, matching JavaScript's ``Math.round``."""
    return math.floor(x + 0.5)


# --- result model ------------------------------------------------------------
@dataclass
class ZoneMatch:
    zone: dict
    relation: str       # "within" | "near"
    distance: int       # metres (0 when within)

    def to_dict(self) -> dict:
        z = self.zone
        return {
            "zone_id": z.get("zone_id"),
            "code": z.get("code"),
            "name": z.get("name"),
            "zone_type": z.get("zone_type"),
            "authority": z.get("authority"),
            "severity": z.get("severity"),
            "status": z.get("status"),
            "note": z.get("note"),
            "legal": z.get("legal"),
            "relation": self.relation,
            "distance": self.distance,
        }


@dataclass
class RiskResult:
    lat: float
    lng: float
    score: int
    level: str                       # high | medium | low
    matches: list[ZoneMatch] = field(default_factory=list)
    nearest: dict | None = None      # {name, distance}

    @property
    def verdict(self) -> str:
        return {
            "high": "High Risk — Do Not Proceed",
            "medium": "Medium Risk — Caution Advised",
            "low": "Low Risk — Likely Safe",
        }[self.level]

    @property
    def recommendation(self) -> str:
        return {
            "high": (
                "This coordinate falls within a government-acquired or legally restricted "
                "zone. Purchasing or developing here carries a high risk of revocation, legal "
                "dispute or demolition. Do not proceed without a verified Certificate of "
                "Occupancy and confirmation from the relevant authority."
            ),
            "medium": (
                "This coordinate is close to, or within a partially-controlled, restricted "
                "area. Obtain a survey plan, confirm the title at the State Lands Registry, "
                "and seek written clearance from the listed authority before proceeding."
            ),
            "low": (
                "No government-acquired or restricted zone was detected at or near this "
                "coordinate. Standard due diligence (title search and survey verification at "
                "the Lands Registry) is still recommended before purchase."
            ),
        }[self.level]

    @property
    def color(self) -> str:
        return {"high": "#d6322e", "medium": "#d98a00", "low": "#0f7a4d"}[self.level]

    def to_dict(self) -> dict:
        return {
            "lat": self.lat,
            "lng": self.lng,
            "score": self.score,
            "level": self.level,
            "verdict": self.verdict,
            "recommendation": self.recommendation,
            "color": self.color,
            "matches": [m.to_dict() for m in self.matches],
            "nearest": self.nearest,
        }


# --- the assessment ----------------------------------------------------------
def assess_risk(lat: float, lng: float, zones: list[dict]) -> RiskResult:
    """Run the risk assessment for a coordinate against a list of zone dicts.

    Each zone dict needs at least ``severity`` and ``boundary`` (``[[lat,lng],…]``)
    plus the descriptive fields used in the report snapshot.
    """
    matches: list[ZoneMatch] = []
    nearest: dict | None = None
    nearest_dist = math.inf

    for z in zones:
        poly = z["boundary"]
        if point_in_polygon(lat, lng, poly):
            matches.append(ZoneMatch(zone=z, relation="within", distance=0))
        else:
            d = distance_to_polygon(lat, lng, poly)
            if d < nearest_dist:
                nearest_dist = d
                nearest = z

    if matches:
        max_w = max(SEVERITY_WEIGHT.get(m.zone["severity"], 60) for m in matches)
        score = min(100, max_w + (len(matches) - 1) * 5)
        level = "high" if score >= HIGH_THRESHOLD else "medium"
    elif nearest is not None and nearest_dist <= PROXIMITY_BUFFER_M:
        base = SEVERITY_WEIGHT.get(nearest["severity"], 60)
        decay = 1 - (nearest_dist / PROXIMITY_BUFFER_M)   # 1 near edge → 0 at buffer
        score = _js_round(35 + base * 0.45 * decay)
        level = "medium" if score >= MEDIUM_THRESHOLD else "low"
        matches.append(ZoneMatch(zone=nearest, relation="near", distance=_js_round(nearest_dist)))
    else:
        score = BASELINE_CLEAR_SCORE
        level = "low"

    nearest_summary = (
        {"name": nearest["name"], "distance": _js_round(nearest_dist)}
        if nearest is not None and math.isfinite(nearest_dist)
        else None
    )
    return RiskResult(lat=lat, lng=lng, score=score, level=level, matches=matches, nearest=nearest_summary)
