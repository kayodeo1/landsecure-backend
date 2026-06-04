"""PDF report generation with ReportLab (pure-Python, no system libraries).

Renders a risk report — score, verdict, findings, legal basis and disclaimer —
styled to match the LandSecure palette used in the web report page.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..models import RiskReport

NAVY = colors.HexColor("#0d2438")
GREEN = colors.HexColor("#0f7a4d")
RED = colors.HexColor("#d6322e")
AMBER = colors.HexColor("#d98a00")
MUTED = colors.HexColor("#5d6b78")
LINE = colors.HexColor("#e3e8ee")

_LEVEL_COLOR = {"high": RED, "medium": AMBER, "low": GREEN}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("LSBrand", parent=ss["Title"], textColor=NAVY, fontSize=20, spaceAfter=2))
    ss.add(ParagraphStyle("LSSub", parent=ss["Normal"], textColor=MUTED, fontSize=9))
    ss.add(ParagraphStyle("LSH2", parent=ss["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=10, spaceAfter=6))
    ss.add(ParagraphStyle("LSBody", parent=ss["Normal"], fontSize=10, leading=15))
    ss.add(ParagraphStyle("LSMuted", parent=ss["Normal"], fontSize=9, textColor=MUTED, leading=13))
    ss.add(ParagraphStyle("LSScore", parent=ss["Title"], fontSize=40, alignment=TA_CENTER, textColor=NAVY))
    return ss


def build_report_pdf(report: RiskReport) -> bytes:
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"LandSecure Risk Report {report.reference}",
    )
    level = report.risk_level
    accent = _LEVEL_COLOR.get(level, MUTED)
    acc = "#" + accent.hexval()[2:]  # ReportLab font tags need '#rrggbb'
    prop = report.property
    lat = prop.latitude if prop else 0.0
    lng = prop.longitude if prop else 0.0

    flow = []
    flow.append(Paragraph("🛡 LandSecure", ss["LSBrand"]))
    flow.append(Paragraph("Property Risk Assessment Report", ss["LSSub"]))
    flow.append(Spacer(1, 6))
    flow.append(HRFlowable(width="100%", color=LINE, thickness=1))
    flow.append(Spacer(1, 10))

    # verdict band
    verdict_tbl = Table(
        [[
            Paragraph(f'<font size=34 color="{acc}"><b>{report.score}</b></font>'
                      '<br/><font size=8 color="#5d6b78">RISK SCORE / 100</font>', ss["LSBody"]),
            Paragraph(
                f'<font size=14 color="{acc}"><b>{report.verdict}</b></font><br/>'
                f'<font size=9 color="#5d6b78">Reference {report.reference} &nbsp;•&nbsp; '
                f'{report.created_at:%d %b %Y, %H:%M} UTC</font><br/>'
                f'<font size=9 color="#5d6b78">Coordinate: {lat:.5f}, {lng:.5f}</font>',
                ss["LSBody"],
            ),
        ]],
        colWidths=[40 * mm, None],
    )
    verdict_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 1, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f5f7fa")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    flow.append(verdict_tbl)
    flow.append(Spacer(1, 6))

    if prop and prop.description:
        flow.append(Paragraph(f"<b>Plot:</b> {prop.description}", ss["LSMuted"]))
    flow.append(Spacer(1, 8))

    # recommendation
    flow.append(Paragraph("Assessment summary", ss["LSH2"]))
    flow.append(Paragraph(report.recommendation or "", ss["LSBody"]))
    flow.append(Spacer(1, 8))

    # findings / legal table
    matches = report.matched_zones or []
    flow.append(Paragraph("Legal basis &amp; authority", ss["LSH2"]))
    if matches:
        data = [["Zone", "Type", "Authority", "Relation", "Legal reference"]]
        for m in matches:
            relation = "Within" if m.get("relation") == "within" else f"{m.get('distance', '')} m"
            data.append([
                Paragraph(f"<b>{m.get('name','')}</b>", ss["LSMuted"]),
                Paragraph(m.get("zone_type", ""), ss["LSMuted"]),
                Paragraph(m.get("authority", "") or "", ss["LSMuted"]),
                Paragraph(relation, ss["LSMuted"]),
                Paragraph(m.get("legal", "") or "", ss["LSMuted"]),
            ])
        tbl = Table(data, colWidths=[34 * mm, 26 * mm, 30 * mm, 16 * mm, None], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        flow.append(tbl)
    else:
        flow.append(Paragraph(
            "No government-acquired or restricted zone was detected at or within 500 m of "
            "this coordinate.", ss["LSBody"]))

    flow.append(Spacer(1, 14))
    flow.append(HRFlowable(width="100%", color=LINE, thickness=1))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        "<b>Disclaimer:</b> LandSecure provides an automated risk indication from mapped "
        "government data. It is not a substitute for a formal title search or a registered "
        "surveyor's report. Always confirm at the State Lands Registry before any payment.",
        ss["LSMuted"]))
    flow.append(Spacer(1, 4))
    flow.append(Paragraph(
        "© LandSecure — A final-year project, University of Ibadan. Verify Before You Buy.",
        ss["LSMuted"]))

    doc.build(flow)
    return buf.getvalue()
