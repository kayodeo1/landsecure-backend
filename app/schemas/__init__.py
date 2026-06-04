"""Pydantic v2 request/response schemas."""
from __future__ import annotations

import datetime as dt
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
Role = Literal["buyer", "agent", "legal", "admin"]
Severity = Literal["high", "medium", "low"]
RiskLevel = Literal["high", "medium", "low"]


# --- auth --------------------------------------------------------------------
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: str
    password: str = Field(min_length=6, max_length=128)
    role: Role = "buyer"

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    full_name: str
    email: str
    role: Role
    status: str
    created_at: dt.datetime


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshIn(BaseModel):
    refresh_token: str


# --- verify / reports --------------------------------------------------------
class VerifyIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    description: str | None = Field(default=None, max_length=500)
    state: str | None = Field(default=None, max_length=80)
    method: Literal["coordinate", "map_pin"] = "coordinate"


class MatchedZone(BaseModel):
    zone_id: int | None = None
    code: str | None = None
    name: str
    zone_type: str | None = None
    authority: str | None = None
    severity: str | None = None
    status: str | None = None
    note: str | None = None
    legal: str | None = None
    relation: str
    distance: int


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    report_id: int
    reference: str
    lat: float
    lng: float
    description: str | None = None
    state: str | None = None
    score: int
    risk_level: RiskLevel
    verdict: str | None = None
    recommendation: str | None = None
    color: str
    matched_zones: list[MatchedZone] = []
    created_at: dt.datetime


# --- zones -------------------------------------------------------------------
class ZoneBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    zone_type: str = Field(min_length=2, max_length=120)
    authority: str | None = None
    status: str | None = "Restricted"
    severity: Severity = "high"
    note: str | None = None
    legal: str | None = None
    layer_id: int | None = None


class ZoneIn(ZoneBase):
    """Accepts either a ``boundary`` ([[lat,lng],…]) or a GeoJSON ``geometry``
    (Polygon, coordinates in [lng,lat]); normalises to ``boundary``."""
    boundary: list[list[float]] | None = None
    geometry: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _normalise(self):
        if self.boundary is None and self.geometry is None:
            raise ValueError("Provide a polygon via 'boundary' or 'geometry'")
        if self.boundary is None and self.geometry is not None:
            self.boundary = _geojson_to_boundary(self.geometry)
        if not self.boundary or len(self.boundary) < 3:
            raise ValueError("A polygon needs at least 3 vertices")
        return self


class ZoneUpdate(BaseModel):
    name: str | None = None
    zone_type: str | None = None
    authority: str | None = None
    status: str | None = None
    severity: Severity | None = None
    note: str | None = None
    legal: str | None = None
    layer_id: int | None = None
    boundary: list[list[float]] | None = None
    geometry: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _normalise(self):
        if self.boundary is None and self.geometry is not None:
            self.boundary = _geojson_to_boundary(self.geometry)
        return self


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    zone_id: int
    code: str | None = None
    layer_id: int | None = None
    name: str
    zone_type: str
    authority: str | None = None
    status: str | None = None
    severity: str
    note: str | None = None
    legal: str | None = None
    boundary: list[list[float]]


def _geojson_to_boundary(geometry: dict[str, Any]) -> list[list[float]]:
    """GeoJSON Polygon ([lng,lat] rings) → [[lat,lng],…] outer ring."""
    if geometry.get("type") != "Polygon":
        raise ValueError("Only Polygon geometries are supported")
    coords = geometry.get("coordinates") or []
    if not coords:
        raise ValueError("Empty polygon coordinates")
    ring = coords[0]
    out = [[float(pt[1]), float(pt[0])] for pt in ring]
    # GeoJSON rings are closed (last==first); drop the duplicate closing vertex
    if len(out) > 1 and out[0] == out[-1]:
        out = out[:-1]
    return out


# --- layers ------------------------------------------------------------------
class LayerIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    source: str | None = None
    visible: bool = True


class LayerUpdate(BaseModel):
    name: str | None = None
    source: str | None = None
    visible: bool | None = None


class LayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    layer_id: int
    name: str
    source: str | None = None
    visible: bool
    zone_count: int = 0


# --- users (admin) -----------------------------------------------------------
class UserAdminUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    status: Literal["active", "suspended"] | None = None


# --- logs --------------------------------------------------------------------
class LogOut(BaseModel):
    log_id: int
    user_id: int | None = None
    user_name: str | None = None
    report_id: int | None = None
    reference: str | None = None
    method: str | None = None
    risk_level: str | None = None
    score: int | None = None
    coordinate: str | None = None
    ts: dt.datetime


# --- admin stats -------------------------------------------------------------
class StatsOut(BaseModel):
    users: int
    zones: int
    verifications: int
    high_risk_pct: float
    reports_high: int
    reports_medium: int
    reports_low: int
