from __future__ import annotations

import os

import httpx


API_URL = os.getenv("NPRA_TEST_API_URL", "http://npra-api:8000").rstrip("/")
EMAIL = os.getenv("NPRA_ADMIN_EMAIL", "admin@npra.local")
PASSWORD = os.getenv("NPRA_ADMIN_PASSWORD", "npra-demo-2026")


def test_live_api_login_records_runs_and_schedule_are_reachable():
    """Non-destructive black-box check against the running Compose API."""
    with httpx.Client(base_url=API_URL, timeout=20.0) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        assert client.get("/api/records").status_code == 401
        bad_login = client.post("/api/auth/login", json={"email": EMAIL, "password": "incorrect-password"})
        assert bad_login.status_code == 401

        login = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert login.status_code == 200, login.text

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["email"].lower() == EMAIL.lower()

        records = client.get("/api/records", params={"page_size": 5})
        assert records.status_code == 200
        payload = records.json()
        assert {"items", "page", "page_size", "total"}.issubset(payload)
        assert isinstance(payload["items"], list)
        assert isinstance(payload["total"], int)

        runs = client.get("/api/runs")
        assert runs.status_code == 200
        assert isinstance(runs.json(), list)

        schedule = client.get("/api/schedule")
        assert schedule.status_code == 200
        schedule_payload = schedule.json()
        assert schedule_payload["cadence"] in {"DAILY", "WEEKLY", "MONTHLY"}
        assert "revision" in schedule_payload

        saved = client.put("/api/schedule", json={**schedule_payload, "enabled": False})
        assert saved.status_code == 200
        assert saved.json()["revision"] == schedule_payload["revision"] + 1
        assert client.get("/api/schedule").json()["enabled"] is False
        # Restore the prior configuration, retaining only the expected revision bump.
        assert client.put("/api/schedule", json=schedule_payload).status_code == 200
        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/auth/me").status_code == 401
