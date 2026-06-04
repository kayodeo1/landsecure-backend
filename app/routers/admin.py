"""Admin dashboard statistics."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.security import require_admin
from ..db import get_db
from ..models import GovernmentZone, RiskReport, User, VerificationLog
from ..schemas import StatsOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.execute(select(func.count(User.user_id))).scalar_one()
    zones = db.execute(select(func.count(GovernmentZone.zone_id))).scalar_one()
    verifications = db.execute(select(func.count(VerificationLog.log_id))).scalar_one()
    total_reports = db.execute(select(func.count(RiskReport.report_id))).scalar_one()

    def level_count(level: str) -> int:
        return db.execute(
            select(func.count(RiskReport.report_id)).where(RiskReport.risk_level == level)
        ).scalar_one()

    high = level_count("high")
    medium = level_count("medium")
    low = level_count("low")
    high_pct = round(100.0 * high / total_reports, 1) if total_reports else 0.0

    return StatsOut(
        users=users,
        zones=zones,
        verifications=verifications,
        high_risk_pct=high_pct,
        reports_high=high,
        reports_medium=medium,
        reports_low=low,
    )
