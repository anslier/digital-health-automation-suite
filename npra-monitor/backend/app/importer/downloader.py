from __future__ import annotations

import hashlib
import time
from pathlib import Path

from app.importer.types import DocumentRef, DownloadedDocument


class DownloadError(RuntimeError):
    pass


def _safe_name(ref: DocumentRef) -> str:
    return f"{ref.meeting_label}.pdf"


def download_document(context, document: DocumentRef, output_dir: Path, retries: int = 3, gap_seconds: float = 1.0) -> DownloadedDocument:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / _safe_name(document)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = context.request.get(document.url, timeout=90_000, fail_on_status_code=False)
            if not response.ok:
                raise DownloadError(f"HTTP {response.status} for {document.url}")
            body = response.body()
            content_type = (response.headers.get("content-type") or "").lower()
            if not body.startswith(b"%PDF"):
                raise DownloadError(f"Response is not a PDF (content-type={content_type!r})")
            path.write_bytes(body)
            digest = hashlib.sha256(body).hexdigest()
            if gap_seconds:
                time.sleep(gap_seconds)
            return DownloadedDocument(ref=document, path=path, sha256=digest, size=len(body))
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
    raise DownloadError(str(last_error) if last_error else "download failed")
