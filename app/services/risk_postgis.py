"""Production spatial path — the PostGIS realisation of the risk engine.

This is the server-side spatial query from ``implementation_plan.md`` §5.1: the
point-in-polygon and proximity logic expressed as ``ST_Contains`` / ``ST_Distance``
over a GiST-indexed ``GEOMETRY(POLYGON, 4326)`` column. It is **functionally
equivalent** to the canonical pure-Python engine in ``risk.py`` and produces the
same verdicts; it is the path used when ``DATABASE_URL`` points at PostgreSQL+PostGIS
(and the ``boundary_geom`` column has been added by the spatial migration).

The SQLite dev path never calls this; ``assess_risk`` in ``risk.py`` is canonical.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .risk import (
    BASELINE_CLEAR_SCORE,
    HIGH_THRESHOLD,
    MEDIUM_THRESHOLD,
    PROXIMITY_BUFFER_M,
    SEVERITY_WEIGHT,
    RiskResult,
    ZoneMatch,
    _js_round,
)

_COLS = "zone_id, code, name, zone_type, authority, severity, status, note, legal"


def assess_risk_postgis(db: Session, lat: float, lng: float) -> RiskResult:
    pt = f"SRID=4326;POINT({lng} {lat})"

    contains = (
        db.execute(
            text(
                f"""
                SELECT {_COLS}
                FROM government_zone
                WHERE ST_Contains(boundary_geom, ST_GeomFromEWKT(:pt))
                """
            ),
            {"pt": pt},
        )
        .mappings()
        .all()
    )

    nearest = (
        db.execute(
            text(
                f"""
                SELECT {_COLS},
                       ST_Distance(boundary_geom::geography, ST_GeomFromEWKT(:pt)::geography) AS dist_m
                FROM government_zone
                ORDER BY boundary_geom <-> ST_GeomFromEWKT(:pt)
                LIMIT 1
                """
            ),
            {"pt": pt},
        )
        .mappings()
        .first()
    )

    if contains:
        max_w = max(SEVERITY_WEIGHT.get(z["severity"], 60) for z in contains)
        score = min(100, max_w + (len(contains) - 1) * 5)
        level = "high" if score >= HIGH_THRESHOLD else "medium"
        matches = [ZoneMatch(zone=dict(z), relation="within", distance=0) for z in contains]
    elif nearest is not None and nearest["dist_m"] <= PROXIMITY_BUFFER_M:
        base = SEVERITY_WEIGHT.get(nearest["severity"], 60)
        decay = 1 - (nearest["dist_m"] / PROXIMITY_BUFFER_M)
        score = _js_round(35 + base * 0.45 * decay)
        level = "medium" if score >= MEDIUM_THRESHOLD else "low"
        matches = [ZoneMatch(zone=dict(nearest), relation="near", distance=_js_round(nearest["dist_m"]))]
    else:
        score, level, matches = BASELINE_CLEAR_SCORE, "low", []

    nearest_summary = (
        {"name": nearest["name"], "distance": _js_round(nearest["dist_m"])} if nearest else None
    )
    return RiskResult(lat=lat, lng=lng, score=score, level=level, matches=matches, nearest=nearest_summary)
