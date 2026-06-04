"""Government zones — public read (list + GeoJSON) and admin CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.security import require_admin
from ..db import get_db
from ..models import GovernmentZone, User
from ..schemas import ZoneIn, ZoneOut, ZoneUpdate

router = APIRouter(prefix="/api/zones", tags=["zones"])

_SEVERITY_COLOR = {"high": "#d6322e", "medium": "#d98a00", "low": "#0f7a4d"}


@router.get("", response_model=list[ZoneOut])
def list_zones(db: Session = Depends(get_db)):
    return db.execute(select(GovernmentZone).order_by(GovernmentZone.zone_id)).scalars().all()


@router.get("/geojson")
def zones_geojson(db: Session = Depends(get_db)):
    """FeatureCollection for the Leaflet overlay. GeoJSON rings use [lng, lat]."""
    zones = db.execute(select(GovernmentZone).order_by(GovernmentZone.zone_id)).scalars().all()
    features = []
    for z in zones:
        ring = [[pt[1], pt[0]] for pt in z.boundary]  # [lat,lng] → [lng,lat]
        if ring and ring[0] != ring[-1]:
            ring.append(ring[0])  # close the ring
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "zone_id": z.zone_id,
                "code": z.code,
                "name": z.name,
                "zone_type": z.zone_type,
                "authority": z.authority,
                "status": z.status,
                "severity": z.severity,
                "note": z.note,
                "legal": z.legal,
                "color": _SEVERITY_COLOR.get(z.severity, "#5d6b78"),
            },
        })
    return {"type": "FeatureCollection", "features": features}


@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.get(GovernmentZone, zone_id)
    if not zone:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    return zone


def _next_code(db: Session) -> str:
    n = db.execute(select(func.count(GovernmentZone.zone_id))).scalar_one()
    return f"GZ-{n + 1:03d}"


@router.post("", response_model=ZoneOut, status_code=status.HTTP_201_CREATED)
def create_zone(payload: ZoneIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    zone = GovernmentZone(
        code=_next_code(db),
        layer_id=payload.layer_id,
        name=payload.name,
        zone_type=payload.zone_type,
        authority=payload.authority,
        status=payload.status,
        severity=payload.severity,
        note=payload.note,
        legal=payload.legal,
        boundary=payload.boundary,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.put("/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: int, payload: ZoneUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    zone = db.get(GovernmentZone, zone_id)
    if not zone:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    data = payload.model_dump(exclude_unset=True, exclude={"geometry"})
    for key, value in data.items():
        setattr(zone, key, value)
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(zone_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    zone = db.get(GovernmentZone, zone_id)
    if not zone:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    db.delete(zone)
    db.commit()
