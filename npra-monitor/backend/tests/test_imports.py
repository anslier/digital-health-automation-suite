from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import func, select

from app.db.models import ImportRun, Product, ProductObservation, SourceDocument
from app.importer.service import run_import
from app.importer.types import DocumentRef, DownloadedDocument


def _browser_factory():
    class Page:
        url = "https://npra.example/new-products"
    return object(), Page(), lambda: None


def test_repeat_run_is_idempotent_and_latest_dca_wins(temp_db, fixtures_dir, monkeypatch):
    _engine, Session = temp_db
    refs = [
        DocumentRef(404, "DCA404", "https://npra.example/2025/dca404.pdf", 2025),
        DocumentRef(424, "DCA424", "https://npra.example/2026/dca424.pdf", 2026),
    ]

    def discoverer(page, source_url=None, minimum_dca=404):
        return refs

    files = {
        404: fixtures_dir / "dca404-transcribed-sample.pdf",
        424: fixtures_dir / "dca424-transcribed-sample.pdf",
    }

    def downloader(context, ref, output_dir, retries=3, gap_seconds=0):
        path = files[ref.meeting_number]
        body = path.read_bytes()
        return DownloadedDocument(ref=ref, path=path, sha256=hashlib.sha256(body).hexdigest(), size=len(body))

    # Keep test output local and instant.
    from app.core import config as config_mod
    settings = config_mod.get_settings()
    monkeypatch.setattr(settings, "download_gap_seconds", 0.0)

    with Session() as db:
        run1 = ImportRun(trigger="TEST", status="QUEUED")
        db.add(run1); db.commit(); db.refresh(run1)
    summary1 = run_import(run1.id, session_factory=Session, browser_factory=_browser_factory, discoverer=discoverer, downloader=downloader)
    assert summary1["status"] == "SUCCESS"
    assert summary1["processed"] == 2

    with Session() as db:
        product_count_1 = db.scalar(select(func.count(Product.id)))
        obs_count_1 = db.scalar(select(func.count(ProductObservation.id)))
        run2 = ImportRun(trigger="TEST", status="QUEUED")
        db.add(run2); db.commit(); db.refresh(run2)
    summary2 = run_import(run2.id, session_factory=Session, browser_factory=_browser_factory, discoverer=discoverer, downloader=downloader)
    assert summary2["status"] == "SUCCESS"
    assert summary2["processed"] == 0
    assert summary2["skipped"] == 2

    with Session() as db:
        assert db.scalar(select(func.count(Product.id))) == product_count_1
        assert db.scalar(select(func.count(ProductObservation.id))) == obs_count_1
        assert db.scalar(select(func.count(SourceDocument.id))) == 2


def test_failed_document_is_visible_and_retryable(temp_db, fixtures_dir):
    _engine, Session = temp_db
    ref = DocumentRef(404, "DCA404", "https://npra.example/2025/fail.pdf", 2025)
    def discoverer(page, source_url=None, minimum_dca=404): return [ref]
    def downloader(context, ref, output_dir, retries=3, gap_seconds=0):
        path = fixtures_dir / "dca404-transcribed-sample.pdf"
        return DownloadedDocument(ref=ref, path=path, sha256="abc", size=path.stat().st_size)
    from app.importer.types import ParseResult, ParseError
    def bad_parser(path): return ParseResult(errors=[ParseError(page=1, row=None, message="No product table rows found")])
    with Session() as db:
        run = ImportRun(trigger="TEST", status="QUEUED")
        db.add(run); db.commit(); db.refresh(run)
    summary = run_import(run.id, session_factory=Session, browser_factory=_browser_factory, discoverer=discoverer, downloader=downloader, parser=bad_parser)
    assert summary["status"] == "FAILED"
    with Session() as db:
        doc = db.scalar(select(SourceDocument).where(SourceDocument.meeting_number == 404))
        assert doc.status == "FAILED"
        assert "No product table" in doc.parse_error


def test_higher_meeting_wins_even_if_older_document_processed_later(temp_db, fixtures_dir):
    _engine, Session = temp_db
    from datetime import date
    from sqlalchemy import func
    from app.db.models import ImportRunDocument
    from app.importer.service import persist_document
    from app.importer.types import ParseResult, ProductRecord

    with Session() as db:
        d404 = SourceDocument(meeting_number=404, meeting_label="DCA404", source_year=2025, canonical_url="https://npra.example/dca404.pdf", status="DISCOVERED")
        d424 = SourceDocument(meeting_number=424, meeting_label="DCA424", source_year=2026, canonical_url="https://npra.example/dca424.pdf", status="DISCOVERED")
        run = ImportRun(trigger="TEST", status="RUNNING")
        db.add_all([d404, d424, run]); db.flush()
        db.add_all([
            ImportRunDocument(run_id=run.id, source_document_id=d404.id, status="PENDING"),
            ImportRunDocument(run_id=run.id, source_document_id=d424.id, status="PENDING"),
        ])
        db.commit()
        ids=(d404.id,d424.id,run.id)

    def rec(name, page):
        return ProductRecord(
            registration_no="MAL-SAME-001",
            product_name=name,
            holder="Holder",
            manufacturer="Maker",
            status="COH APPROVE",
            category="PRESCRIPTION-FULL",
            registration_date_raw="01-01-2025",
            registration_date=date(2025,1,1),
            expiry_date_raw="01-01-2030",
            expiry_date=date(2030,1,1),
            source_page=page,
        )

    path = fixtures_dir / "dca424-transcribed-sample.pdf"
    newer_ref = DocumentRef(424,"DCA424","https://npra.example/dca424.pdf",2026)
    older_ref = DocumentRef(404,"DCA404","https://npra.example/dca404.pdf",2025)
    newer = DownloadedDocument(newer_ref,path,"new",path.stat().st_size)
    older = DownloadedDocument(older_ref,path,"old",path.stat().st_size)

    persist_document(session_factory=Session, document_id=ids[1], downloaded=newer, parsed=ParseResult(records=[rec("newer value",1)]), run_id=ids[2])
    persist_document(session_factory=Session, document_id=ids[0], downloaded=older, parsed=ParseResult(records=[rec("older value",1)]), run_id=ids[2])

    with Session() as db:
        product=db.scalar(select(Product).where(Product.registration_no=="MAL-SAME-001"))
        assert product.product_name == "newer value"
        assert product.current_meeting_number == 424
        assert db.scalar(select(func.count(ProductObservation.id))) == 2


def test_same_registration_can_have_multiple_distinct_observations_in_one_document(temp_db, fixtures_dir):
    _engine, Session = temp_db
    from datetime import date
    from app.db.models import ImportRunDocument
    from app.importer.service import persist_document
    from app.importer.types import ParseResult, ProductRecord, DocumentRef, DownloadedDocument

    with Session() as db:
        doc = SourceDocument(meeting_number=405, meeting_label="DCA405", source_year=2025, canonical_url="https://npra.example/dca405.pdf", status="DISCOVERED")
        run = ImportRun(trigger="TEST", status="RUNNING")
        db.add_all([doc, run]); db.flush()
        db.add(ImportRunDocument(run_id=run.id, source_document_id=doc.id, status="PENDING"))
        db.commit(); ids=(doc.id, run.id)

    def rec(status, page, row):
        return ProductRecord(
            registration_no="MAL09082827T",
            product_name="Bai Hu Tang Extract Powder",
            holder="LIFECARE ESSENTIAL SDN. BHD.",
            manufacturer="SHENG CHANG PHARMACEUTICAL CO., LTD.",
            status=status,
            category="NATURAL PRODUCT-TRADITIONAL(GENERAL)",
            registration_date_raw="04-02-2025",
            registration_date=date(2025,2,4),
            expiry_date_raw="04-02-2030",
            expiry_date=date(2030,2,4),
            source_page=page,
            source_row=row,
        )

    path = fixtures_dir / "dca404-transcribed-sample.pdf"
    ref = DocumentRef(405, "DCA405", "https://npra.example/dca405.pdf", 2025)
    downloaded = DownloadedDocument(ref, path, "sha", path.stat().st_size)
    parsed = ParseResult(records=[
        rec("COS - Approved", 2, 21),
        rec("RE-REGISTRATION (RENEWAL)", 15, 238),
    ])

    count = persist_document(session_factory=Session, document_id=ids[0], downloaded=downloaded, parsed=parsed, run_id=ids[1])
    assert count == 2
    with Session() as db:
        observations = list(db.scalars(select(ProductObservation).where(ProductObservation.registration_no == "MAL09082827T")))
        assert len(observations) == 2
        assert {o.status for o in observations} == {"COS - Approved", "RE-REGISTRATION (RENEWAL)"}
        product = db.scalar(select(Product).where(Product.registration_no == "MAL09082827T"))
        assert product.status == "RE-REGISTRATION (RENEWAL)"
