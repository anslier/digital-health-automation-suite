from __future__ import annotations

import csv
import json
from pathlib import Path

import typer
from sqlalchemy import select

from app.core.config import get_settings
from app.db.bootstrap import bootstrap
from app.db.models import ImportRun, Product, SourceDocument, utcnow
from app.db.session import SessionLocal
from app.importer.discovery import discover_documents
from app.importer.service import run_import
from app.jobs.locking import ImportAlreadyRunning

app = typer.Typer(help="NPRA new-product importer and export utility", no_args_is_help=True)


def _print_import_progress(event: str, data: dict) -> None:
    if event == "discovering":
        typer.echo("Discovering NPRA documents...")
        return

    if event == "discovered":
        count = data["count"]
        first = data.get("first")
        last = data.get("last")
        if first and last:
            typer.echo(f"Found {count} documents: {first} -> {last}")
        else:
            typer.echo(f"Found {count} documents")
        typer.echo()
        return

    index = data.get("index")
    total = data.get("total")
    meeting = data.get("meeting")
    prefix = f"[{index}/{total}] {meeting}" if index and total and meeting else meeting or ""

    if event == "document_skipped":
        typer.echo(f"{prefix} - skipped (already processed)")
    elif event == "document_downloading":
        typer.echo(prefix)
        typer.echo("  downloading...")
    elif event == "document_parsing":
        typer.echo("  parsing...")
    elif event == "document_success":
        typer.echo(f"  OK {data['records']} observations")
        typer.echo()
    elif event == "document_failed":
        typer.echo(f"  FAILED {data['error']}", err=True)
        typer.echo()
    elif event == "complete":
        typer.echo("Import complete")


@app.command("import")
def import_command():
    """Discover DCA404+ PDFs, download unknown documents, parse and persist them."""
    bootstrap()
    with SessionLocal() as db:
        run = ImportRun(trigger="CLI", status="QUEUED")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id

    try:
        summary = run_import(run_id, progress=_print_import_progress)
    except ImportAlreadyRunning as exc:
        with SessionLocal() as db:
            saved = db.get(ImportRun, run_id)
            if saved:
                saved.status = "FAILED"
                saved.error_message = str(exc)
                saved.finished_at = utcnow()
                db.commit()
        typer.echo(json.dumps({"run_id": run_id, "status": "FAILED", "error": str(exc)}, indent=2))
        raise typer.Exit(2)

    typer.echo()
    typer.echo(json.dumps(summary, indent=2, default=str))
    if summary["status"] == "FAILED":
        raise typer.Exit(1)


@app.command()
def discover():
    """Discover live DCA404+ PDF links without downloading files or mutating the database."""
    settings = get_settings()

    typer.echo("Discovering NPRA documents...")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.browser_headless)
        context = browser.new_context(accept_downloads=False)
        page = context.new_page()
        try:
            refs = discover_documents(page, source_url=settings.source_url, minimum_dca=404)
        finally:
            context.close()
            browser.close()

    if not refs:
        typer.echo("No DCA404+ documents found.", err=True)
        raise typer.Exit(1)

    typer.echo(f"Found {len(refs)} documents: {refs[0].meeting_label} -> {refs[-1].meeting_label}")
    for ref in refs:
        year = f" ({ref.year})" if ref.year else ""
        typer.echo(f"{ref.meeting_label}{year}  {ref.url}")


@app.command()
def export(output: Path = typer.Option(Path("records.csv"), "--output", "-o")):
    """Export the current product representation to CSV."""
    bootstrap()
    output.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db, output.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["registration_no", "product_name", "holder", "manufacturer", "status", "category", "registration_date", "expiry_date", "dca_meeting"])
        for p in db.scalars(select(Product).order_by(Product.registration_no)):
            writer.writerow([p.registration_no, p.product_name, p.holder, p.manufacturer, p.status, p.category, p.registration_date_raw, p.expiry_date_raw, p.current_meeting_number])
    typer.echo(str(output))


@app.command()
def manifest(output: Path = typer.Option(Path("source-manifest.csv"), "--output", "-o")):
    """Export source-document provenance/status."""
    bootstrap()
    output.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db, output.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["meeting", "url", "status", "sha256", "file_size", "processed_at", "error"])
        for d in db.scalars(select(SourceDocument).order_by(SourceDocument.meeting_number)):
            writer.writerow([d.meeting_label, d.canonical_url, d.status, d.sha256, d.file_size, d.processed_at, d.parse_error])
    typer.echo(str(output))


if __name__ == "__main__":
    app()
