from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class DocumentRef:
    meeting_number: int
    meeting_label: str
    url: str
    year: int | None = None


@dataclass(frozen=True)
class DownloadedDocument:
    ref: DocumentRef
    path: Path
    sha256: str
    size: int


@dataclass
class ProductRecord:
    registration_no: str
    product_name: str | None
    holder: str | None
    manufacturer: str | None
    status: str | None
    category: str | None
    registration_date_raw: str | None
    registration_date: date | None
    expiry_date_raw: str | None
    expiry_date: date | None
    source_page: int | None
    source_row: int | None = None


@dataclass
class ParseError:
    page: int | None
    row: int | None
    message: str


@dataclass
class ParseResult:
    records: list[ProductRecord] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
