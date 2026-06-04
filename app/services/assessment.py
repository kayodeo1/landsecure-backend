"""DB-backed assessment façade.

Loads zones from the database and dispatches to the canonical pure-Python engine
(``risk.py``). Keeping this here lets ``risk.py`` stay free of any DB import and be
unit-tested in isolation against the report's labelled coordinates.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import GovernmentZone
from .risk import RiskResult, assess_risk


def load_engine_zones(db: Session) -> list[dict]:
    rows = db.execute(select(GovernmentZone)).scalars().all()
    return [
        {
            "zone_id": z.zone_id,
            "code": z.code,
            "name": z.name,
            "zone_type": z.zone_type,
            "authority": z.authority,
            "status": z.status,
            "severity": z.severity,
            "note": z.note,
            "legal": z.legal,
            "boundary": z.boundary,
        }
        for z in rows
    ]


def run_assessment(db: Session, lat: float, lng: float) -> RiskResult:
    return assess_risk(lat, lng, load_engine_zones(db))
