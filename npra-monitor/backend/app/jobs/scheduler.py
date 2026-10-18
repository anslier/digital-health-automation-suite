from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.db.models import ScheduleConfig
from app.jobs.dispatcher import enqueue_run

JOB_ID = "npra-monthly-import"


def build_trigger(config: ScheduleConfig):
    hour, minute = [int(x) for x in config.local_time.split(":", 1)]
    tz = ZoneInfo(config.timezone)
    cadence = config.cadence.upper()
    if cadence == "DAILY":
        return CronTrigger(hour=hour, minute=minute, timezone=tz)
    if cadence == "WEEKLY":
        return CronTrigger(day_of_week=config.weekday if config.weekday is not None else 0, hour=hour, minute=minute, timezone=tz)
    return CronTrigger(day=config.day_of_month, hour=hour, minute=minute, timezone=tz)


def apply_schedule(scheduler: BackgroundScheduler, config: ScheduleConfig, enqueue_callable) -> None:
    try:
        scheduler.remove_job(JOB_ID)
    except Exception:
        pass
    if not config.enabled:
        return
    scheduler.add_job(
        enqueue_callable,
        trigger=build_trigger(config),
        id=JOB_ID,
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )


def next_run_time(scheduler: BackgroundScheduler) -> datetime | None:
    job = scheduler.get_job(JOB_ID)
    return job.next_run_time if job else None
