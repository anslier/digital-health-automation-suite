from datetime import datetime

from sqlalchemy import func, select

from app.db.models import ImportRun, ScheduleConfig
from app.jobs.dispatcher import enqueue_run
from app.api.routes.schedule import serialize


def test_repeated_queue_requests_reuse_pending_and_running_import(temp_db):
    _, Session = temp_db
    with Session() as db:
        first = enqueue_run(db, trigger="UI")
        assert enqueue_run(db, trigger="UI").id == first.id
        first.status = "RUNNING"
        db.commit()
        assert enqueue_run(db, trigger="SCHEDULE").id == first.id
        assert db.scalar(select(func.count(ImportRun.id))) == 1
        first.status = "SUCCESS"
        db.commit()
        assert enqueue_run(db, trigger="UI").id != first.id


def test_saved_schedule_exposes_next_time_and_disabled_has_none():
    config = ScheduleConfig(enabled=True, cadence="DAILY", local_time="13:55",
                            timezone="Asia/Kuala_Lumpur", revision=8,
                            day_of_month=8, weekday=None)
    data = serialize(config)
    next_time = datetime.fromisoformat(data["next_run_at"])
    assert next_time.hour == 13 and next_time.minute == 55
    assert next_time.utcoffset().total_seconds() == 8 * 3600
    config.enabled = False
    assert serialize(config)["next_run_at"] is None
