from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, text

from app.db.models import ImportRun, RunStatus, utcnow


def enqueue_run(db, trigger: str = "UI") -> ImportRun:
    # Serialize queue requests across API processes and the scheduler. This is
    # separate from the dedicated connection lock protecting actual imports.
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 742_404_425})
    active = db.scalar(select(ImportRun).where(
        ImportRun.status.in_([RunStatus.QUEUED.value, RunStatus.RUNNING.value])
    ).order_by(ImportRun.requested_at).limit(1))
    if active:
        db.commit()
        db.refresh(active)
        return active
    run = ImportRun(trigger=trigger, status=RunStatus.QUEUED.value)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def claim_next_run(db) -> ImportRun | None:
    # PostgreSQL SKIP LOCKED prevents two workers from claiming the same request.
    stmt = select(ImportRun).where(ImportRun.status == RunStatus.QUEUED.value).order_by(ImportRun.requested_at).limit(1)
    if db.bind and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    run = db.scalar(stmt)
    if run:
        run.status = RunStatus.RUNNING.value
        run.started_at = utcnow()
        run.heartbeat_at = utcnow()
        db.commit()
        db.refresh(run)
    return run


def reconcile_stale_runs(db, stale_minutes: int = 15) -> int:
    cutoff = utcnow() - timedelta(minutes=stale_minutes)
    stale = db.scalars(select(ImportRun).where(ImportRun.status == RunStatus.RUNNING.value, ImportRun.heartbeat_at < cutoff)).all()
    for run in stale:
        run.status = RunStatus.FAILED.value
        run.finished_at = utcnow()
        run.error_message = "Worker stopped while the import was running; safe to retry."
    db.commit()
    return len(stale)
