"""Property verification — the core flow.

Runs the risk engine server-side, persists property + risk_report + verification_log
(the audit trail), and returns the report.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..db import get_db
from ..models import Property, RiskReport, User, VerificationLog
from ..schemas import ReportOut, VerifyIn
from ..serialize import report_to_out
from ..services.assessment import run_assessment

router = APIRouter(prefix="/api", tags=["verify"])


@router.post("/verify", response_model=ReportOut)
def verify(payload: VerifyIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = run_assessment(db, payload.lat, payload.lng)

    prop = Property(
        latitude=payload.lat,
        longitude=payload.lng,
        description=payload.description,
        state=payload.state,
    )
    db.add(prop)
    db.flush()  # assign property_id

    report = RiskReport(
        reference="VR-PENDING",
        user_id=user.user_id,
        property_id=prop.property_id,
        score=result.score,
        risk_level=result.level,
        verdict=result.verdict,
        recommendation=result.recommendation,
        matched_zones=[m.to_dict() for m in result.matches],
    )
    db.add(report)
    db.flush()  # assign report_id
    report.reference = f"VR-{10200 + report.report_id}"

    db.add(VerificationLog(user_id=user.user_id, report_id=report.report_id, method=payload.method))
    db.commit()
    db.refresh(report)
    return report_to_out(report)
