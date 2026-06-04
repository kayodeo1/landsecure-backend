"""Map layers — public read, admin CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.security import require_admin
from ..db import get_db
from ..models import GovernmentZone, MapLayer, User
from ..schemas import LayerIn, LayerOut, LayerUpdate

router = APIRouter(prefix="/api/layers", tags=["layers"])


def _to_out(db: Session, layer: MapLayer) -> LayerOut:
    count = db.execute(
        select(func.count(GovernmentZone.zone_id)).where(GovernmentZone.layer_id == layer.layer_id)
    ).scalar_one()
    return LayerOut(
        layer_id=layer.layer_id,
        name=layer.name,
        source=layer.source,
        visible=layer.visible,
        zone_count=count,
    )


@router.get("", response_model=list[LayerOut])
def list_layers(db: Session = Depends(get_db)):
    layers = db.execute(select(MapLayer).order_by(MapLayer.layer_id)).scalars().all()
    return [_to_out(db, layer) for layer in layers]


@router.post("", response_model=LayerOut, status_code=status.HTTP_201_CREATED)
def create_layer(payload: LayerIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    layer = MapLayer(name=payload.name, source=payload.source, visible=payload.visible)
    db.add(layer)
    db.commit()
    db.refresh(layer)
    return _to_out(db, layer)


@router.put("/{layer_id}", response_model=LayerOut)
def update_layer(layer_id: int, payload: LayerUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    layer = db.get(MapLayer, layer_id)
    if not layer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Layer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(layer, key, value)
    db.commit()
    db.refresh(layer)
    return _to_out(db, layer)


@router.delete("/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_layer(layer_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    layer = db.get(MapLayer, layer_id)
    if not layer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Layer not found")
    db.delete(layer)
    db.commit()
