"""Helpers that turn ORM rows into API response shapes."""
from __future__ import annotations

from .models import RiskReport
from .schemas import ReportOut

LEVEL_COLOR = {"high": "#d6322e", "medium": "#d98a00", "low": "#0f7a4d"}


def report_to_out(r: RiskReport) -> ReportOut:
    prop = r.property
    return ReportOut(
        report_id=r.report_id,
        reference=r.reference,
        lat=prop.latitude if prop else 0.0,
        lng=prop.longitude if prop else 0.0,
        description=prop.description if prop else None,
        state=prop.state if prop else None,
        score=r.score,
        risk_level=r.risk_level,
        verdict=r.verdict,
        recommendation=r.recommendation,
        color=LEVEL_COLOR.get(r.risk_level, "#5d6b78"),
        matched_zones=r.matched_zones or [],
        created_at=r.created_at,
    )
