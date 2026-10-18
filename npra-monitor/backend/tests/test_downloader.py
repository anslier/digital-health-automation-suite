from __future__ import annotations

from pathlib import Path

import pytest

from app.importer.downloader import DownloadError, download_document
from app.importer.types import DocumentRef


class Response:
    def __init__(self, body: bytes, status: int = 200, content_type: str = "application/pdf"):
        self._body = body
        self.status = status
        self.ok = 200 <= status < 300
        self.headers = {"content-type": content_type}
    def body(self):
        return self._body


class Request:
    def __init__(self, response): self.response=response
    def get(self, *args, **kwargs): return self.response


class Context:
    def __init__(self, response): self.request=Request(response)


def test_download_accepts_pdf_and_hashes(tmp_path: Path):
    ref=DocumentRef(424,"DCA424","https://npra.example/dca424.pdf",2026)
    result=download_document(Context(Response(b"%PDF-1.7\nfixture")),ref,tmp_path,retries=1,gap_seconds=0)
    assert result.path.read_bytes().startswith(b"%PDF")
    assert len(result.sha256)==64


def test_download_rejects_html_error_page(tmp_path: Path):
    ref=DocumentRef(424,"DCA424","https://npra.example/dca424.pdf",2026)
    with pytest.raises(DownloadError, match="not a PDF"):
        download_document(Context(Response(b"<html>maintenance</html>",content_type="text/html")),ref,tmp_path,retries=1,gap_seconds=0)
