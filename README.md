# LandSecure API (backend)

FastAPI backend for **LandSecure — Property Risk Assessment Platform** (University
of Ibadan final-year project, Adiamo Sodiq · E046135). It runs server-side spatial
risk assessment, JWT auth with an audit trail, and ReportLab PDF reports.

The Next.js frontend lives in a separate repo: **landsecure-frontend**.

## Stack
FastAPI · SQLAlchemy 2 · Pydantic v2 · PyJWT + bcrypt · ReportLab. SQLite for
zero-config local dev; PostgreSQL in production (the risk engine is pure-Python,
so no PostGIS extension is required).

## Run locally
```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```
On first boot the API creates the schema and **seeds** 8 government zones + demo
accounts. Docs at <http://localhost:8000/docs>, health at `/api/health`.

| Role  | Email                 | Password    |
|-------|-----------------------|-------------|
| Buyer | `buyer@landsecure.ng` | `buyer1234` |
| Admin | `admin@landsecure.ng` | `admin1234` |

## Tests
```bash
./.venv/bin/python -m pytest      # 30 tests incl. the Table 4.1 risk regression
```

## Deploy to Render

This repo ships a **`render.yaml` Blueprint**. In the [Render](https://render.com)
dashboard: **New + → Blueprint → connect this repo**. Render then:

1. provisions a **free Postgres** database (`landsecure-db`),
2. builds the web service (`pip install -r requirements.txt`),
3. starts it with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
4. injects `DATABASE_URL` (auto-upgraded to the psycopg v3 driver in `config.py`)
   and a generated `JWT_SECRET`, and
5. health-checks `/api/health`.

### After the first frontend deploy
Set CORS so the browser app can call the API. In the service's **Environment**:

- `CORS_ORIGINS` → your exact Vercel URL, e.g. `https://landsecure-frontend.vercel.app`
- `CORS_ORIGIN_REGEX` → `https://.*\.vercel\.app` (default; also allows preview URLs)

### Environment variables
See [`.env.example`](.env.example). Key ones: `DATABASE_URL`, `JWT_SECRET`,
`CORS_ORIGINS`, `CORS_ORIGIN_REGEX`.

> **Free tier note:** the database is real and persists; the web instance sleeps
> after inactivity and cold-starts on the next request (first call may take ~30s).

---
© LandSecure — final-year project, University of Ibadan. *Verify Before You Buy.*
