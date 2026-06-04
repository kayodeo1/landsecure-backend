"""FastAPI application entrypoint — wires CORS, routers and startup seeding."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import SessionLocal, init_db
from .routers import admin, auth, layers, logs, reports, users, verify, zones


@asynccontextmanager
async def lifespan(app: FastAPI):
    # dev convenience: ensure schema exists and demo data is seeded.
    init_db()
    from . import seed

    db = SessionLocal()
    try:
        seed.run(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Server-side property risk-assessment API for LandSecure (FastAPI + PostGIS-ready).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, verify.router, reports.router, zones.router, layers.router,
          users.router, logs.router, admin.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "service": settings.app_name, "engine": "postgis" if settings.is_postgres else "python"}


@app.get("/", tags=["meta"])
def root():
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
    }
