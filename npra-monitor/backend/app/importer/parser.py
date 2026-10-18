from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pdfplumber

from app.importer.types import ParseError, ParseResult, ProductRecord

HEADER_ALIASES = {
    "registration_no": ("nopendaftaranmal", "nopendaftaran", "registrationno", "registrationnumber"),
    "product_name": ("namaproduk", "productname"),
    "holder": ("pemegang", "holder"),
    "manufacturer": ("pengilang", "manufacturer"),
    "status": ("status",),
    "category": ("kategori", "category"),
    "registration_date_raw": ("tarikhdaftar", "registerdate", "registrationdate"),
    "expiry_date_raw": ("tarikhluput", "expirydate", "expirationdate"),
}


def clean_cell(value) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).replace("\x00", " ").replace("\u00ad", " ")).strip()
    return text


def _header_key(value: str | None) -> str:
    value = clean_cell(value) or ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _find_columns(header: list[str | None]) -> dict[str, int]:
    normalized = [_header_key(x) for x in header]
    found: dict[str, int] = {}
    for field, aliases in HEADER_ALIASES.items():
        for idx, text in enumerate(normalized):
            if any(alias == text or alias in text for alias in aliases):
                found[field] = idx
                break
    return found


def _parse_date(raw: str | None):
    if not raw or raw.strip() in {"-", "–", "—", "N/A", "NA"}:
        return None
    value = raw.strip().replace(".", "-")
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def _value(row: list, columns: dict[str, int], field: str) -> str | None:
    idx = columns[field]
    return clean_cell(row[idx] if idx < len(row) else None)


def _looks_like_registration(value: str | None) -> bool:
    if not value:
        return False
    return bool(re.match(r"^MAL[0-9A-Z-]+$", value.replace(" ", ""), re.I))


def parse_rows(rows: list[list], page_number: int) -> ParseResult:
    result = ParseResult()
    if not rows:
        return result
    header_index = -1
    columns: dict[str, int] = {}
    for i, row in enumerate(rows[:6]):
        maybe = _find_columns(row)
        if len(maybe) >= 7 and "registration_no" in maybe:
            header_index = i
            columns = maybe
            break
    if header_index < 0:
        return result
    missing_columns = [k for k in HEADER_ALIASES if k not in columns]
    if missing_columns:
        result.errors.append(ParseError(page=page_number, row=None, message=f"Missing table columns: {', '.join(missing_columns)}"))
        return result

    for row_index, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        reg = _value(row, columns, "registration_no")
        if not reg:
            # Continuation rows are normally already folded by pdfplumber into a cell.
            # Ignore truly empty/footer rows rather than fabricating a registration number.
            continue
        reg = reg.replace(" ", "")
        if not _looks_like_registration(reg):
            continue
        values = {field: _value(row, columns, field) for field in HEADER_ALIASES}
        values["registration_no"] = reg
        # A blank/dash source cell is allowed and preserved; a missing column is an error above.
        result.records.append(
            ProductRecord(
                registration_no=values["registration_no"],
                product_name=values["product_name"],
                holder=values["holder"],
                manufacturer=values["manufacturer"],
                status=values["status"],
                category=values["category"],
                registration_date_raw=values["registration_date_raw"],
                registration_date=_parse_date(values["registration_date_raw"]),
                expiry_date_raw=values["expiry_date_raw"],
                expiry_date=_parse_date(values["expiry_date_raw"]),
                source_page=page_number,
                source_row=row_index,
            )
        )
    return result


def _candidate_tables(page):
    settings = [
        {"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 4, "join_tolerance": 4, "intersection_tolerance": 5},
        {"vertical_strategy": "lines", "horizontal_strategy": "text", "snap_tolerance": 4, "join_tolerance": 4},
        {},
    ]
    seen = set()
    for config in settings:
        try:
            for table in page.extract_tables(config) or []:
                signature = repr(table[:2])
                if signature not in seen:
                    seen.add(signature)
                    yield table
        except Exception:
            continue


def parse_pdf(path: Path) -> ParseResult:
    if path.read_bytes()[:4] != b"%PDF":
        return ParseResult(errors=[ParseError(page=None, row=None, message="Input is not a PDF")])
    result = ParseResult()
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            best = ParseResult()
            for table in _candidate_tables(page):
                parsed = parse_rows(table, page_no)
                if len(parsed.records) > len(best.records):
                    best = parsed
                elif not best.records and parsed.errors:
                    best.errors.extend(parsed.errors)
            result.records.extend(best.records)
            result.errors.extend(best.errors)
    # The same registration can legitimately appear more than once in one DCA PDF
    # (for example once under COS approval and again under re-registration/renewal).
    # Preserve distinct source rows and collapse only exact duplicate content that can
    # arise from PDF extraction artifacts. Source position is intentionally excluded
    # from the equality key so a repeated identical row across a page boundary is
    # stored once, while differing statuses/fields remain separate observations.
    deduped: dict[tuple, ProductRecord] = {}
    for record in result.records:
        key = (
            record.registration_no,
            record.product_name,
            record.holder,
            record.manufacturer,
            record.status,
            record.category,
            record.registration_date_raw,
            record.expiry_date_raw,
        )
        deduped.setdefault(key, record)
    result.records = list(deduped.values())
    if not result.records and not result.errors:
        result.errors.append(ParseError(page=None, row=None, message="No product table rows found"))
    return result
