from __future__ import annotations

import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.db.bootstrap import bootstrap
from app.db.models import ScheduleConfig
from app.db.session import SessionLocal
from app.importer.service import run_import
from app.jobs.dispatcher import claim_next_run, enqueue_run, reconcile_stale_runs
from app.jobs.scheduler import apply_schedule


def main() -> None:
    settings = get_settings()
    bootstrap()
    scheduler = BackgroundScheduler()
    scheduler.start()
    last_revision = None

    def scheduled_enqueue():
        with SessionLocal() as db:
            enqueue_run(db, trigger="SCHEDULE")

    while True:
        try:
            with SessionLocal() as db:
                reconcile_stale_runs(db)
                config = db.get(ScheduleConfig, 1)
                if config and config.revision != last_revision:
                    apply_schedule(scheduler, config, scheduled_enqueue)
                    last_revision = config.revision
                run = claim_next_run(db)
            if run:
                try:
                    run_import(run.id)
                except Exception as exc:
                    with SessionLocal() as db:
                        saved = db.get(type(run), run.id)
                        if saved:
                            saved.status = "FAILED"
                            saved.error_message = str(exc)[:4000]
                            db.commit()
            time.sleep(settings.worker_poll_seconds)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(f"worker error: {exc}", flush=True)
            time.sleep(settings.worker_poll_seconds)
    scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
