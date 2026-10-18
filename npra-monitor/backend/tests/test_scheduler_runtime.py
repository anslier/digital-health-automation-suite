from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.db.models import ImportRun, RunStatus, ScheduleConfig
from app.jobs.dispatcher import enqueue_run
from app.jobs.scheduler import JOB_ID, apply_schedule


def test_scheduler_job_callback_enqueues_schedule_run(temp_db):
    """Verify the scheduler callback creates the same durable DB queue request
    that the production worker consumes, without waiting for wall-clock time.
    """
    _engine, Session = temp_db

    config = ScheduleConfig(
        id=1,
        enabled=True,
        cadence="MONTHLY",
        local_time="09:00",
        day_of_month=8,
        timezone="Asia/Kuala_Lumpur",
        revision=1,
    )

    def scheduled_enqueue():
        with Session() as db:
            enqueue_run(db, trigger="SCHEDULE")

    scheduler = BackgroundScheduler()
    scheduler.start(paused=True)
    try:
        apply_schedule(scheduler, config, scheduled_enqueue)
        job = scheduler.get_job(JOB_ID)
        assert job is not None

        # Invoke the exact registered callback directly. This tests scheduler
        # wiring without making the test wait until the next real cron minute.
        job.func()

        with Session() as db:
            runs = db.scalars(select(ImportRun)).all()
            assert len(runs) == 1
            assert runs[0].trigger == "SCHEDULE"
            assert runs[0].status == RunStatus.QUEUED.value
    finally:
        scheduler.shutdown(wait=False)
