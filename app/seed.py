"""Idempotent database seeding.

Ports the 8 government zones from ``site/assets/js/zones.js`` into ``government_zone``,
creates map layers, the demo admin + buyer accounts, and a backdated verification
history so the dashboard, history and audit-log pages render with real data.

Run standalone:  ``python -m app.seed``
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .core.security import hash_password
from .db import SessionLocal, init_db
from .models import GovernmentZone, MapLayer, Property, RiskReport, User, VerificationLog
from .services.risk import assess_risk
from .services.zones_data import GOV_ZONES

# zone_type → layer name
_LAYER_FOR_TYPE = {
    "Government Acquisition": "Government Acquisitions",
    "Infrastructure Corridor": "Infrastructure Corridors",
    "Environmental / Protected": "Environmental & Protected",
    "Aviation Safety Zone": "Aviation & Institutional",
    "Government Institution": "Aviation & Institutional",
}

_LAYERS = [
    ("Government Acquisitions", "Lagos State Lands Bureau / NPA"),
    ("Infrastructure Corridors", "Federal Ministry of Works"),
    ("Environmental & Protected", "NESREA / River Basin Authorities"),
    ("Aviation & Institutional", "FAAN / University vesting"),
]

# (label, lat, lng, days_ago, description, state)
_HISTORY = [
    ("Lekki Phase 2 plot", 6.41000, 3.68000, 2, "Plot 24, Lekki Phase 2 layout", "Lagos"),
    ("UI endowment edge", 7.43400, 3.88900, 5, "Plot near UI second gate", "Oyo"),
    ("Bodija estate", 7.42900, 3.90800, 9, "Bodija GRA, 3-bed bungalow plot", "Oyo"),
    ("Lagos–Ibadan ROW", 6.64500, 3.38500, 14, "Land off the expressway service lane", "Ogun"),
    ("Magodo GRA", 6.61600, 3.37500, 20, "Magodo Phase 1 residential plot", "Lagos"),
]


def run(db: Session, *, force: bool = False) -> None:
    if not force and db.execute(select(User).limit(1)).first():
        return  # already seeded

    # --- layers ---
    layers: dict[str, MapLayer] = {}
    for name, source in _LAYERS:
        layer = MapLayer(name=name, source=source, visible=True)
        db.add(layer)
        layers[name] = layer
    db.flush()

    # --- zones (ported from zones.js) ---
    for z in GOV_ZONES:
        layer = layers.get(_LAYER_FOR_TYPE.get(z["zone_type"], "Government Acquisitions"))
        db.add(GovernmentZone(
            code=z["code"],
            layer_id=layer.layer_id if layer else None,
            name=z["name"],
            zone_type=z["zone_type"],
            authority=z["authority"],
            status=z["status"],
            severity=z["severity"],
            note=z["note"],
            legal=z["legal"],
            boundary=z["boundary"],
        ))

    # --- users ---
    admin = User(
        full_name=settings.seed_admin_name,
        email=settings.seed_admin_email,
        password_hash=hash_password(settings.seed_admin_password),
        role="admin",
    )
    buyer = User(
        full_name=settings.seed_buyer_name,
        email=settings.seed_buyer_email,
        password_hash=hash_password(settings.seed_buyer_password),
        role="buyer",
    )
    extra = [
        User(full_name="Aisha Bello", email="aisha.agent@landsecure.ng",
             password_hash=hash_password("agent1234"), role="agent"),
        User(full_name="Chidi Okeke", email="chidi.legal@landsecure.ng",
             password_hash=hash_password("legal1234"), role="legal"),
    ]
    db.add_all([admin, buyer, *extra])
    db.flush()

    # --- backdated history for the buyer ---
    now = dt.datetime.now(dt.timezone.utc)
    zones_for_engine = [
        {**z, "zone_id": None} for z in GOV_ZONES  # engine only needs boundary + metadata
    ]
    for label, lat, lng, days_ago, desc, state in _HISTORY:
        result = assess_risk(lat, lng, zones_for_engine)
        created = now - dt.timedelta(days=days_ago, hours=3)
        prop = Property(latitude=lat, longitude=lng, description=desc, state=state)
        db.add(prop)
        db.flush()
        report = RiskReport(
            reference="VR-PENDING",
            user_id=buyer.user_id,
            property_id=prop.property_id,
            score=result.score,
            risk_level=result.level,
            verdict=result.verdict,
            recommendation=result.recommendation,
            matched_zones=[m.to_dict() for m in result.matches],
            created_at=created,
        )
        db.add(report)
        db.flush()
        report.reference = f"VR-{10200 + report.report_id}"
        db.add(VerificationLog(
            user_id=buyer.user_id, report_id=report.report_id,
            method="coordinate", ts=created,
        ))

    db.commit()


if __name__ == "__main__":
    init_db()
    session = SessionLocal()
    try:
        run(session, force=False)
        n = session.execute(select(GovernmentZone)).scalars().all()
        print(f"Seed complete — {len(n)} zones, demo users ready.")
        print(f"  admin: {settings.seed_admin_email} / {settings.seed_admin_password}")
        print(f"  buyer: {settings.seed_buyer_email} / {settings.seed_buyer_password}")
    finally:
        session.close()
