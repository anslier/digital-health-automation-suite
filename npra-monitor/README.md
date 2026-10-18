# NPRA New Products Monitor

A Python automation that discovers NPRA New Products Approved PDFs from DCA404 (January 2025), downloads new documents, parses their product tables and stores the records in PostgreSQL. Repeated imports skip successful documents and prevent duplicate observations.

## Architecture

```text
CLI -> shared importer -> Playwright discovery/download -> pdfplumber -> PostgreSQL
Angular -> nginx -> FastAPI -> database queue -> worker -> shared importer
APScheduler -> database queue
```

The CLI and worker use the same importer. Source observations retain the PDF history; the current-products table gives one current record per registration number. The runtime uses no AI API.

## Setup and run

Requirements: Docker Desktop or Docker Engine with Compose v2 and Linux containers, a browser, and internet for building and live NPRA imports.

Open a terminal in the extracted `npra-monitor` folder, then run:

```bash
docker compose up -d --build
docker compose ps
```

Wait for the database, API and web health checks to pass and the worker to be running. Open **http://localhost:4201**.

Defaults work without an `.env` file; `.env.example` contains the settings if needed. Sign in with the prefilled admin account: **admin@npra.local / npra-demo-2026**. A new database has no product records until the first import. Its schedule starts disabled.

## CLI

Discover source links:

```bash
docker compose exec npra-api python -m app.cli discover
```

Download, parse and import:

```bash
docker compose exec npra-api python -m app.cli import
```

The first import can take several minutes. It prints document progress and a final summary; expect `SUCCESS` with `failed=0`. Run the import again to check that already processed documents are skipped without new duplicate records.

The eight stored fields are registration number, product name, holder, manufacturer, status, category, registration date and expiry date.

## Dashboard

Use Records to search, browse pages, open PDF source links and export CSVs. Import history shows CLI, UI and scheduled runs. Run import now queues the same importer for the worker. Finish a CLI import before starting a UI import.

In Schedule, enable checks, choose daily/weekly/monthly, set the time and timezone, then save. The worker must remain running for scheduled checks.

## Export

The dashboard's CSV and Manifest buttons download exports. To export through the CLI:

```bash
docker compose exec npra-api python -m app.cli export --output /data/records.csv
docker compose exec npra-api python -m app.cli manifest --output /data/source-manifest.csv
docker compose cp npra-api:/data/records.csv ./records.csv
docker compose cp npra-api:/data/source-manifest.csv ./source-manifest.csv
```

## Tests

With the app running:

```bash
docker compose -f compose.yaml -f compose.test.yaml run --rm --build npra-tests
```

## Stop

```bash
docker compose down
```

Database records and downloaded PDFs remain saved for the next start. For errors, check `docker compose logs --tail 100`.
