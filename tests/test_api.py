"""API tests — auth flow, verify persistence, zones, role gating, stats."""
from __future__ import annotations

from .conftest import auth


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_then_login(client):
    payload = {"full_name": "Test Buyer", "email": "new.buyer@example.com", "password": "secret123"}
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["role"] == "buyer"
    assert body["access_token"]

    # duplicate email rejected
    assert client.post("/api/auth/register", json=payload).status_code == 409

    r = client.post("/api/auth/login", json={"email": payload["email"], "password": "secret123"})
    assert r.status_code == 200
    assert client.post("/api/auth/login",
                       json={"email": payload["email"], "password": "wrong"}).status_code == 401


def test_public_register_cannot_be_admin(client):
    r = client.post("/api/auth/register", json={
        "full_name": "Sneaky", "email": "sneaky@example.com", "password": "secret123", "role": "admin"})
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "buyer"


def test_me_requires_auth(client, buyer_token):
    assert client.get("/api/auth/me").status_code == 401
    r = client.get("/api/auth/me", headers=auth(buyer_token))
    assert r.status_code == 200
    assert r.json()["email"]


def test_verify_high_risk_lekki(client, buyer_token):
    r = client.post("/api/verify", headers=auth(buyer_token),
                    json={"lat": 6.41, "lng": 3.68, "description": "Plot 24", "state": "Lagos"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["score"] == 100
    assert body["risk_level"] == "high"
    assert body["reference"].startswith("VR-")
    assert len(body["matched_zones"]) >= 1
    assert body["matched_zones"][0]["relation"] == "within"

    # report retrievable + appears in history
    rid = body["report_id"]
    assert client.get(f"/api/reports/{rid}", headers=auth(buyer_token)).status_code == 200
    hist = client.get("/api/reports", headers=auth(buyer_token))
    assert any(item["report_id"] == rid for item in hist.json())


def test_verify_low_risk_clear(client, buyer_token):
    r = client.post("/api/verify", headers=auth(buyer_token), json={"lat": 9.05785, "lng": 7.49508})
    assert r.status_code == 200
    assert r.json()["risk_level"] == "low"


def test_verify_rejects_bad_coords(client, buyer_token):
    assert client.post("/api/verify", headers=auth(buyer_token),
                       json={"lat": 999, "lng": 3.68}).status_code == 422


def test_zones_public_and_geojson(client):
    r = client.get("/api/zones")
    assert r.status_code == 200
    assert len(r.json()) == 8  # the 8 seeded zones

    gj = client.get("/api/zones/geojson")
    assert gj.status_code == 200
    fc = gj.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 8
    assert fc["features"][0]["geometry"]["type"] == "Polygon"


def test_zone_crud_role_gating(client, buyer_token, admin_token):
    new_zone = {
        "name": "Test Acquisition Strip", "zone_type": "Government Acquisition",
        "authority": "Test Authority", "severity": "high",
        "boundary": [[6.50, 3.30], [6.51, 3.30], [6.51, 3.31], [6.50, 3.31]],
    }
    # buyer forbidden
    assert client.post("/api/zones", headers=auth(buyer_token), json=new_zone).status_code == 403
    # admin allowed
    r = client.post("/api/zones", headers=auth(admin_token), json=new_zone)
    assert r.status_code == 201, r.text
    zid = r.json()["zone_id"]
    assert r.json()["code"]

    # update + delete
    assert client.put(f"/api/zones/{zid}", headers=auth(admin_token),
                      json={"severity": "medium"}).json()["severity"] == "medium"
    assert client.delete(f"/api/zones/{zid}", headers=auth(admin_token)).status_code == 204


def test_zone_create_from_geojson(client, admin_token):
    geo = {
        "name": "GeoJSON Zone", "zone_type": "Environmental / Protected", "severity": "medium",
        "geometry": {"type": "Polygon", "coordinates": [[[3.30, 6.50], [3.30, 6.51], [3.31, 6.51], [3.31, 6.50], [3.30, 6.50]]]},
    }
    r = client.post("/api/zones", headers=auth(admin_token), json=geo)
    assert r.status_code == 201, r.text
    # boundary stored as [lat,lng], closing vertex stripped
    assert r.json()["boundary"][0] == [6.50, 3.30]


def test_admin_stats_and_logs(client, buyer_token, admin_token):
    assert client.get("/api/admin/stats", headers=auth(buyer_token)).status_code == 403
    stats = client.get("/api/admin/stats", headers=auth(admin_token))
    assert stats.status_code == 200
    body = stats.json()
    assert body["zones"] >= 8
    assert body["users"] >= 2

    logs = client.get("/api/logs", headers=auth(admin_token))
    assert logs.status_code == 200
    assert isinstance(logs.json(), list)
    csv = client.get("/api/logs/export.csv", headers=auth(admin_token))
    assert csv.status_code == 200
    assert "log_id" in csv.text


def test_pdf_download(client, buyer_token):
    rid = client.post("/api/verify", headers=auth(buyer_token),
                      json={"lat": 6.41, "lng": 3.68}).json()["report_id"]
    r = client.get(f"/api/reports/{rid}/pdf", headers=auth(buyer_token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
