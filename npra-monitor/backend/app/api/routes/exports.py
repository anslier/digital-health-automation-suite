from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import Product, SourceDocument
from app.db.session import get_db

router = APIRouter(prefix="/exports", tags=["exports"], dependencies=[Depends(require_admin)])


@router.get("/records.csv")
def records_csv(db: Session = Depends(get_db)):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["registration_no", "product_name", "holder", "manufacturer", "status", "category", "registration_date", "expiry_date", "dca_meeting", "source_url"])
    products = db.scalars(select(Product).order_by(Product.registration_no)).all()
    source_ids = {p.current_source_document_id for p in products}
    sources = {d.id: d for d in db.scalars(select(SourceDocument).where(SourceDocument.id.in_(source_ids))).all()} if source_ids else {}
    for p in products:
        writer.writerow([
            p.registration_no, p.product_name, p.holder, p.manufacturer, p.status, p.category,
            p.registration_date_raw, p.expiry_date_raw, p.current_meeting_number,
            sources[p.current_source_document_id].canonical_url if p.current_source_document_id in sources else "",
        ])
    payload = "\ufeff" + buffer.getvalue()
    return StreamingResponse(iter([payload.encode("utf-8")]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=npra-records.csv"})


@router.get("/manifest.csv")
def manifest_csv(db: Session = Depends(get_db)):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["meeting", "source_url", "status", "sha256", "file_size", "processed_at", "error"])
    for d in db.scalars(select(SourceDocument).order_by(SourceDocument.meeting_number)):
        writer.writerow([d.meeting_label, d.canonical_url, d.status, d.sha256, d.file_size, d.processed_at, d.parse_error])
    payload = "\ufeff" + buffer.getvalue()
    return StreamingResponse(iter([payload.encode("utf-8")]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=source-manifest.csv"})
