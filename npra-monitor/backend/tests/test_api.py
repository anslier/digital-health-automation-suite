from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.models import AdminUser, Base, Product, ScheduleConfig, SourceDocument
from app.db.session import build_engine
import app.db.session as session_module
import app.api.routes.auth as auth_route
import app.api.routes.records as records_route
import app.api.routes.runs as runs_route
import app.api.routes.schedule as schedule_route
import app.api.routes.exports as exports_route
from app.main import app


def test_auth_records_and_csv(tmp_path, monkeypatch):
    engine = build_engine(f"sqlite:///{tmp_path/'api.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    def override_db():
        db = Session()
        try: yield db
        finally: db.close()
    app.dependency_overrides[session_module.get_db] = override_db
    # Route modules captured the same callable object at declaration, so override is sufficient.
    with Session() as db:
        user = AdminUser(email="admin@npra.local", password_hash=hash_password("secret"))
        db.add(user)
        doc = SourceDocument(meeting_number=424, meeting_label="DCA424", source_year=2026, canonical_url="https://npra.example/dca424.pdf", status="SUCCESS")
        db.add(doc); db.flush()
        db.add(Product(registration_no="MAL11095004AZ", product_name="Desud Plus", holder="EUCOGEN", manufacturer="Lotus", status="COH APPROVE", category="PRESCRIPTION-FULL", registration_date_raw="08-10-2021", expiry_date_raw="08-10-2026", current_meeting_number=424, current_source_document_id=doc.id))
        db.add(ScheduleConfig(id=1, enabled=False, cadence="MONTHLY", local_time="09:00", day_of_month=8))
        db.commit()
    client = TestClient(app)
    login = client.post("/api/auth/login", json={"email":"admin@npra.local","password":"secret"})
    assert login.status_code == 200
    res = client.get("/api/records?q=Desud")
    assert res.status_code == 200
    assert res.json()["items"][0]["registration_no"] == "MAL11095004AZ"
    csv_res = client.get("/api/exports/records.csv")
    assert csv_res.status_code == 200
    assert "MAL11095004AZ" in csv_res.text
    schedule = client.put("/api/schedule", json={"enabled":True,"cadence":"WEEKLY","local_time":"08:30","weekday":1,"day_of_month":8,"timezone":"Asia/Kuala_Lumpur"})
    assert schedule.status_code == 200
    assert schedule.json()["revision"] == 2
    queued = client.post("/api/runs")
    assert queued.status_code == 202
    blocked = client.post("/api/runs", headers={"Origin":"https://evil.example"})
    assert blocked.status_code == 403
    app.dependency_overrides.clear()
