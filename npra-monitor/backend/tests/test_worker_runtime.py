from __future__ import annotations

from types import SimpleNamespace

from app.db.models import ImportRun, RunStatus, ScheduleConfig, utcnow
from app.jobs.dispatcher import enqueue_run
import app.worker as worker


def test_worker_main_claims_queued_run_and_invokes_importer(temp_db, monkeypatch):
    """Exercise the real worker loop without touching NPRA or PostgreSQL.

    The worker uses the same claim path as production, but run_import is replaced
    with a deterministic fake so this test never opens a browser or downloads a PDF.
    """
    _engine, Session = temp_db

    with Session() as db:
        db.add(
            ScheduleConfig(
                id=1,
                enabled=False,
                cadence="MONTHLY",
                local_time="09:00",
                day_of_month=8,
                timezone="Asia/Kuala_Lumpur",
                revision=1,
            )
        )
        queued = enqueue_run(db, trigger="UI")
        run_id = queued.id

    calls: list[str] = []

    def fake_run_import(received_run_id: str):
        calls.append(received_run_id)
        with Session() as db:
            saved = db.get(ImportRun, received_run_id)
            # claim_next_run must have moved the request to RUNNING first.
            assert saved is not None
            assert saved.status == RunStatus.RUNNING.value
            saved.status = RunStatus.SUCCESS.value
            saved.finished_at = utcnow()
            saved.heartbeat_at = utcnow()
            db.commit()
        return {"run_id": received_run_id, "status": "SUCCESS"}

    sleep_calls = 0

    def stop_after_one_iteration(_seconds: float):
        nonlocal sleep_calls
        sleep_calls += 1
        raise KeyboardInterrupt

    monkeypatch.setattr(worker, "bootstrap", lambda: None)
    monkeypatch.setattr(worker, "SessionLocal", Session)
    monkeypatch.setattr(worker, "run_import", fake_run_import)
    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace(worker_poll_seconds=0))
    monkeypatch.setattr(worker.time, "sleep", stop_after_one_iteration)

    worker.main()

    assert sleep_calls == 1
    assert calls == [run_id]
    with Session() as db:
        saved = db.get(ImportRun, run_id)
        assert saved is not None
        assert saved.status == RunStatus.SUCCESS.value
        assert saved.started_at is not None
        assert saved.finished_at is not None
