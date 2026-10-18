from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    DocumentStatus,
    ImportRun,
    ImportRunDocument,
    Product,
    ProductObservation,
    RunStatus,
    SourceDocument,
    utcnow,
)
from app.db.session import SessionLocal, engine
from app.importer.discovery import discover_documents
from app.importer.downloader import download_document
from app.importer.parser import parse_pdf
from app.importer.types import DocumentRef, DownloadedDocument, ParseResult, ProductRecord
from app.jobs.locking import import_lock


def _upsert_manifest(refs: list[DocumentRef], session_factory=SessionLocal) -> dict[str, int]:
    ids: dict[str, int] = {}
    with session_factory() as db:
        for ref in refs:
            doc = db.scalar(select(SourceDocument).where(SourceDocument.canonical_url == ref.url))
            if not doc:
                doc = SourceDocument(
                    meeting_number=ref.meeting_number,
                    meeting_label=ref.meeting_label,
                    source_year=ref.year,
                    canonical_url=ref.url,
                    status=DocumentStatus.DISCOVERED.value,
                )
                db.add(doc)
                db.flush()
            ids[ref.url] = doc.id
        db.commit()
    return ids


def _record_fields(record: ProductRecord) -> dict:
    return {
        "product_name": record.product_name,
        "holder": record.holder,
        "manufacturer": record.manufacturer,
        "status": record.status,
        "category": record.category,
        "registration_date_raw": record.registration_date_raw,
        "registration_date": record.registration_date,
        "expiry_date_raw": record.expiry_date_raw,
        "expiry_date": record.expiry_date,
    }


def _observation_key(record: ProductRecord) -> str:
    payload = [
        record.registration_no,
        record.product_name,
        record.holder,
        record.manufacturer,
        record.status,
        record.category,
        record.registration_date_raw,
        record.expiry_date_raw,
    ]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def persist_document(
    *,
    session_factory,
    document_id: int,
    downloaded: DownloadedDocument,
    parsed: ParseResult,
    run_id: str,
) -> int:
    unresolved = [e for e in parsed.errors if e.message.startswith("Missing") or e.message.startswith("No product")]
    if unresolved:
        raise ValueError("; ".join(e.message for e in unresolved[:5]))

    with session_factory() as db:
        doc = db.get(SourceDocument, document_id)
        if not doc:
            raise ValueError(f"source document {document_id} not found")

        try:
            count = 0
            for record in parsed.records:
                observation_key = _observation_key(record)
                existing_obs = db.scalar(
                    select(ProductObservation).where(
                        ProductObservation.source_document_id == doc.id,
                        ProductObservation.observation_key == observation_key,
                    )
                )
                if not existing_obs:
                    db.add(
                        ProductObservation(
                            source_document_id=doc.id,
                            registration_no=record.registration_no,
                            observation_key=observation_key,
                            source_page=record.source_page,
                            source_row=record.source_row,
                            **_record_fields(record),
                        )
                    )
                    count += 1

                product = db.scalar(select(Product).where(Product.registration_no == record.registration_no))
                if not product:
                    product = Product(
                        registration_no=record.registration_no,
                        current_meeting_number=doc.meeting_number,
                        current_source_document_id=doc.id,
                        **_record_fields(record),
                    )
                    db.add(product)
                    # SessionLocal disables autoflush; flush so another distinct
                    # observation for the same registration in this document finds
                    # the pending Product row instead of attempting a duplicate insert.
                    db.flush()
                elif doc.meeting_number >= product.current_meeting_number:
                    for key, value in _record_fields(record).items():
                        setattr(product, key, value)
                    product.current_meeting_number = doc.meeting_number
                    product.current_source_document_id = doc.id

            doc.local_path = str(downloaded.path)
            doc.sha256 = downloaded.sha256
            doc.file_size = downloaded.size
            doc.status = DocumentStatus.SUCCESS.value
            doc.parse_error = None
            doc.processed_at = utcnow()

            rd = db.scalar(
                select(ImportRunDocument).where(
                    ImportRunDocument.run_id == run_id,
                    ImportRunDocument.source_document_id == doc.id,
                )
            )
            if rd:
                rd.status = DocumentStatus.SUCCESS.value
                rd.records_count = count
                rd.error_message = None

            db.commit()
            return count
        except Exception:
            db.rollback()
            raise


def mark_document_failed(session_factory, document_id: int, run_id: str, message: str) -> None:
    with session_factory() as db:
        doc = db.get(SourceDocument, document_id)
        if doc:
            doc.status = DocumentStatus.FAILED.value
            doc.parse_error = message[:4000]

        rd = db.scalar(
            select(ImportRunDocument).where(
                ImportRunDocument.run_id == run_id,
                ImportRunDocument.source_document_id == document_id,
            )
        )
        if rd:
            rd.status = DocumentStatus.FAILED.value
            rd.error_message = message[:4000]

        db.commit()


def run_import(
    run_id: str,
    session_factory=SessionLocal,
    source_url: str | None = None,
    *,
    browser_factory=None,
    discoverer: Callable | None = None,
    downloader: Callable | None = None,
    parser: Callable[[Path], ParseResult] | None = None,
    progress: Callable[[str, dict], None] | None = None,
) -> dict:
    settings = get_settings()
    source_url = source_url or settings.source_url
    discoverer = discoverer or discover_documents
    downloader = downloader or download_document
    parser = parser or parse_pdf

    def emit(event: str, **data) -> None:
        if progress:
            progress(event, data)

    with session_factory() as db:
        run = db.get(ImportRun, run_id)
        if not run:
            raise ValueError(f"import run {run_id} not found")
        run.status = RunStatus.RUNNING.value
        run.started_at = utcnow()
        run.heartbeat_at = utcnow()
        db.commit()

    counts = dict(discovered=0, skipped=0, downloaded=0, processed=0, failed=0, observations=0)

    with import_lock(engine, settings.import_lock_key):
        if browser_factory is None:
            from playwright.sync_api import sync_playwright

            p = sync_playwright().start()
            browser = p.chromium.launch(headless=settings.browser_headless)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            close_browser = lambda: (context.close(), browser.close(), p.stop())
        else:
            context, page, close_browser = browser_factory()

        try:
            emit("discovering")
            refs = discoverer(page, source_url=source_url, minimum_dca=404)
            if not refs:
                raise RuntimeError("NPRA discovery returned no DCA404+ PDFs")

            ids = _upsert_manifest(refs, session_factory=session_factory)
            counts["discovered"] = len(refs)
            emit(
                "discovered",
                count=len(refs),
                first=refs[0].meeting_label if refs else None,
                last=refs[-1].meeting_label if refs else None,
            )

            with session_factory() as db:
                run = db.get(ImportRun, run_id)
                run.discovered_count = len(refs)
                for ref in refs:
                    doc = db.get(SourceDocument, ids[ref.url])
                    existing = db.scalar(
                        select(ImportRunDocument).where(
                            ImportRunDocument.run_id == run_id,
                            ImportRunDocument.source_document_id == doc.id,
                        )
                    )
                    if not existing:
                        db.add(
                            ImportRunDocument(
                                run_id=run_id,
                                source_document_id=doc.id,
                                status="PENDING",
                            )
                        )
                db.commit()

            total = len(refs)
            for index, ref in enumerate(refs, start=1):
                document_id = ids[ref.url]

                with session_factory() as db:
                    doc = db.get(SourceDocument, document_id)
                    if doc.status == DocumentStatus.SUCCESS.value:
                        counts["skipped"] += 1
                        rd = db.scalar(
                            select(ImportRunDocument).where(
                                ImportRunDocument.run_id == run_id,
                                ImportRunDocument.source_document_id == document_id,
                            )
                        )
                        rd.status = "SKIPPED"
                        db.commit()

                        emit(
                            "document_skipped",
                            index=index,
                            total=total,
                            meeting=ref.meeting_label,
                        )
                        continue

                try:
                    emit(
                        "document_downloading",
                        index=index,
                        total=total,
                        meeting=ref.meeting_label,
                    )
                    downloaded = downloader(
                        context,
                        ref,
                        settings.downloads_dir,
                        retries=settings.download_retries,
                        gap_seconds=settings.download_gap_seconds,
                    )
                    counts["downloaded"] += 1

                    emit(
                        "document_parsing",
                        index=index,
                        total=total,
                        meeting=ref.meeting_label,
                    )
                    parsed = parser(downloaded.path)

                    count = persist_document(
                        session_factory=session_factory,
                        document_id=document_id,
                        downloaded=downloaded,
                        parsed=parsed,
                        run_id=run_id,
                    )
                    counts["processed"] += 1
                    counts["observations"] += count

                    emit(
                        "document_success",
                        index=index,
                        total=total,
                        meeting=ref.meeting_label,
                        records=count,
                    )
                except Exception as exc:
                    counts["failed"] += 1
                    mark_document_failed(session_factory, document_id, run_id, str(exc))
                    emit(
                        "document_failed",
                        index=index,
                        total=total,
                        meeting=ref.meeting_label,
                        error=str(exc),
                    )

                with session_factory() as db:
                    run = db.get(ImportRun, run_id)
                    run.heartbeat_at = utcnow()
                    run.skipped_count = counts["skipped"]
                    run.downloaded_count = counts["downloaded"]
                    run.processed_count = counts["processed"]
                    run.failed_count = counts["failed"]
                    run.observation_count = counts["observations"]
                    db.commit()
        finally:
            close_browser()

    with session_factory() as db:
        run = db.get(ImportRun, run_id)
        if counts["failed"] == 0:
            run.status = RunStatus.SUCCESS.value
        elif counts["processed"] > 0 or counts["skipped"] > 0:
            run.status = RunStatus.PARTIAL.value
        else:
            run.status = RunStatus.FAILED.value

        run.finished_at = utcnow()
        run.heartbeat_at = utcnow()
        run.discovered_count = counts["discovered"]
        run.skipped_count = counts["skipped"]
        run.downloaded_count = counts["downloaded"]
        run.processed_count = counts["processed"]
        run.failed_count = counts["failed"]
        run.observation_count = counts["observations"]
        db.commit()
        status = run.status

    summary = {**counts, "status": status, "run_id": run_id}
    emit("complete", **summary)
    return summary
