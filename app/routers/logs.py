"""Verification audit trail (admin only) — JSON list + CSV export."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import require_admin
from ..db import get_db
from ..models import User, VerificationLog
from ..schemas import LogOut

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _rows(db: Session) -> list[LogOut]:
    logs = db.execute(
        select(VerificationLog).order_by(VerificationLog.ts.desc())
    ).scalars().all()
    out: list[LogOut] = []
    for log in logs:
        report = log.report
        prop = report.property if report else None
        user = log.user if hasattr(log, "user") else None
        # log has no user relationship defined; fetch lazily
        if user is None and log.user_id is not None:
            user = db.get(User, log.user_id)
        out.append(
            LogOut(
                log_id=log.log_id,
                user_id=log.user_id,
                user_name=user.full_name if user else None,
                report_id=log.report_id,
                reference=report.reference if report else None,
                method=log.method,
                risk_level=report.risk_level if report else None,
                score=report.score if report else None,
                coordinate=(f"{prop.latitude:.5f}, {prop.longitude:.5f}" if prop else None),
                ts=log.ts,
            )
        )
    return out


@router.get("", response_model=list[LogOut])
def list_logs(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return _rows(db)


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["log_id", "timestamp", "user", "reference", "method", "risk_level", "score", "coordinate"])
    for r in _rows(db):
        writer.writerow([
            r.log_id, r.ts.isoformat(), r.user_name or "", r.reference or "",
            r.method or "", r.risk_level or "", r.score if r.score is not None else "",
            r.coordinate or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="landsecure_audit_log.csv"'},
    )
