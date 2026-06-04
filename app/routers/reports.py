"""Risk reports — list, fetch, and PDF download."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..db import get_db
from ..models import RiskReport, User
from ..schemas import ReportOut
from ..serialize import report_to_out
from ..services.report_pdf import build_report_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(RiskReport).order_by(RiskReport.created_at.desc())
    if user.role != "admin":
        stmt = stmt.where(RiskReport.user_id == user.user_id)
    reports = db.execute(stmt).scalars().all()
    return [report_to_out(r) for r in reports]


def _get_owned(report_id: int, db: Session, user: User) -> RiskReport:
    report = db.get(RiskReport, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if user.role != "admin" and report.user_id != user.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your report")
    return report


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return report_to_out(_get_owned(report_id, db, user))


@router.get("/{report_id}/pdf")
def report_pdf(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = _get_owned(report_id, db, user)
    pdf = build_report_pdf(report)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="LandSecure_{report.reference}.pdf"'},
    )
