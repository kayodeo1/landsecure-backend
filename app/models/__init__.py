"""SQLAlchemy 2.0 models — the six entities of the report ERD (Figure 3.7).

Geometry note: ``GovernmentZone.boundary`` holds the polygon as a JSON ring of
``[lat, lng]`` pairs (identical to the mockup's ``zones.js``). This is portable
across SQLite and PostgreSQL. On a PostGIS deployment a real
``GEOMETRY(POLYGON, 4326)`` column is added by migration and kept in sync; the
spatial queries in ``services/risk_postgis.py`` then use it directly.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class MapLayer(Base):
    __tablename__ = "map_layer"

    layer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200))
    visible: Mapped[bool] = mapped_column(Boolean, default=True)

    zones: Mapped[list["GovernmentZone"]] = relationship(back_populates="layer")


class User(Base):
    __tablename__ = "users"  # "user" is reserved in Postgres → table users

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="buyer", nullable=False)  # buyer|agent|legal|admin
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|suspended
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reports: Mapped[list["RiskReport"]] = relationship(back_populates="user")


class GovernmentZone(Base):
    __tablename__ = "government_zone"

    zone_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String(20), index=True)  # e.g. GZ-001
    layer_id: Mapped[int | None] = mapped_column(ForeignKey("map_layer.layer_id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(120), nullable=False)
    authority: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(40))      # Restricted|Caution|Cleared
    severity: Mapped[str] = mapped_column(String(10), nullable=False)  # high|medium|low
    note: Mapped[str | None] = mapped_column(Text)
    legal: Mapped[str | None] = mapped_column(Text)
    # portable polygon: list of [lat, lng] pairs
    boundary: Mapped[list] = mapped_column(JSON, nullable=False)

    layer: Mapped[MapLayer | None] = relationship(back_populates="zones")


class Property(Base):
    __tablename__ = "property"

    property_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(String(80))

    reports: Mapped[list["RiskReport"]] = relationship(back_populates="property")


class RiskReport(Base):
    __tablename__ = "risk_report"

    report_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), index=True)  # VR-10241
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    property_id: Mapped[int | None] = mapped_column(ForeignKey("property.property_id"))
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)  # high|medium|low
    verdict: Mapped[str | None] = mapped_column(String(80))
    recommendation: Mapped[str | None] = mapped_column(Text)
    matched_zones: Mapped[list] = mapped_column(JSON, default=list)  # snapshot
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User | None] = relationship(back_populates="reports")
    property: Mapped[Property | None] = relationship(back_populates="reports")
    logs: Mapped[list["VerificationLog"]] = relationship(back_populates="report")


class VerificationLog(Base):
    __tablename__ = "verification_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    report_id: Mapped[int | None] = mapped_column(ForeignKey("risk_report.report_id"))
    method: Mapped[str | None] = mapped_column(String(20))  # coordinate|map_pin
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    report: Mapped[RiskReport | None] = relationship(back_populates="logs")


__all__ = [
    "MapLayer",
    "User",
    "GovernmentZone",
    "Property",
    "RiskReport",
    "VerificationLog",
]
