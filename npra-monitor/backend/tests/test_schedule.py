from __future__ import annotations

import pytest

pytest.importorskip("apscheduler")
from apscheduler.schedulers.background import BackgroundScheduler

from app.db.models import ScheduleConfig
from app.jobs.scheduler import JOB_ID, apply_schedule


def test_disabled_schedule_has_no_job_and_weekly_has_one():
    scheduler = BackgroundScheduler()
    scheduler.start(paused=True)
    try:
        disabled = ScheduleConfig(
            id=1,
            enabled=False,
            cadence="MONTHLY",
            local_time="09:00",
            day_of_month=8,
            timezone="Asia/Kuala_Lumpur",
        )
        apply_schedule(scheduler, disabled, lambda: None)
        assert scheduler.get_job(JOB_ID) is None

        enabled = ScheduleConfig(
            id=1,
            enabled=True,
            cadence="WEEKLY",
            local_time="08:30",
            weekday=1,
            day_of_month=8,
            timezone="Asia/Kuala_Lumpur",
        )
        apply_schedule(scheduler, enabled, lambda: None)
        assert scheduler.get_job(JOB_ID) is not None
    finally:
        scheduler.shutdown(wait=False)
