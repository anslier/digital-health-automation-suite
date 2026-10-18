from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import Product, SourceDocument
from app.db.session import get_db

router = APIRouter(prefix="/records", tags=["records"], dependencies=[Depends(require_admin)])


@router.get("")
def list_records(
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    filters = []
    if q:
        needle = f"%{q}%"
        filters.append(or_(Product.registration_no.ilike(needle), Product.product_name.ilike(needle), Product.holder.ilike(needle), Product.manufacturer.ilike(needle)))
    if category:
        filters.append(Product.category == category)
    base = select(Product)
    count_stmt = select(func.count(Product.id))
    for f in filters:
        base = base.where(f)
        count_stmt = count_stmt.where(f)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(base.order_by(Product.registration_no).offset((page - 1) * page_size).limit(page_size)).all()
    source_ids = {p.current_source_document_id for p in rows}
    sources = {d.id: d for d in db.scalars(select(SourceDocument).where(SourceDocument.id.in_(source_ids))).all()} if source_ids else {}
    return {
        "items": [
            {
                "registration_no": p.registration_no,
                "product_name": p.product_name,
                "holder": p.holder,
                "manufacturer": p.manufacturer,
                "status": p.status,
                "category": p.category,
                "registration_date": p.registration_date_raw,
                "expiry_date": p.expiry_date_raw,
                "meeting": p.current_meeting_number,
                "source_url": sources[p.current_source_document_id].canonical_url if p.current_source_document_id in sources else None,
            }
            for p in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    return [x for x in db.scalars(select(Product.category).distinct().order_by(Product.category)).all() if x]
