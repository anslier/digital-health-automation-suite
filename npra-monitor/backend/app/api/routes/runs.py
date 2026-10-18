from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import ImportRun, ImportRunDocument, SourceDocument
from app.db.session import get_db
from app.jobs.dispatcher import enqueue_run

router = APIRouter(prefix="/runs", tags=["runs"], dependencies=[Depends(require_admin)])


def run_dict(run: ImportRun):
    return {
        "id": run.id,
        "trigger": run.trigger,
        "status": run.status,
        "requested_at": run.requested_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "heartbeat_at": run.heartbeat_at,
        "discovered_count": run.discovered_count,
        "skipped_count": run.skipped_count,
        "downloaded_count": run.downloaded_count,
        "processed_count": run.processed_count,
        "failed_count": run.failed_count,
        "observation_count": run.observation_count,
        "error_message": run.error_message,
    }


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_run(db: Session = Depends(get_db)):
    return run_dict(enqueue_run(db, trigger="UI"))


@router.get("")
def list_runs(db: Session = Depends(get_db)):
    runs = db.scalars(select(ImportRun).order_by(ImportRun.requested_at.desc()).limit(100)).all()
    return [run_dict(x) for x in runs]


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(ImportRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    docs = db.execute(
        select(ImportRunDocument, SourceDocument)
        .join(SourceDocument, SourceDocument.id == ImportRunDocument.source_document_id)
        .where(ImportRunDocument.run_id == run_id)
        .order_by(SourceDocument.meeting_number)
    ).all()
    out = run_dict(run)
    out["documents"] = [
        {
            "meeting": d.meeting_label,
            "url": d.canonical_url,
            "status": rd.status,
            "records_count": rd.records_count,
            "error_message": rd.error_message,
        }
        for rd, d in docs
    ]
    return out


@router.post("/{run_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_run(run_id: str, db: Session = Depends(get_db)):
    if not db.get(ImportRun, run_id):
        raise HTTPException(404, "Run not found")
    return run_dict(enqueue_run(db, trigger=f"RETRY:{run_id[:8]}"))
