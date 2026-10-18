from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.importer.parser import parse_pdf, parse_rows


def test_transcribed_real_rows_parse_all_eight_fields(fixtures_dir: Path):
    expected = {row["meeting"]: row for row in json.loads((fixtures_dir / "real-sample-rows.json").read_text(encoding="utf-8"))}
    for meeting, row in expected.items():
        result = parse_pdf(fixtures_dir / f"{meeting.lower()}-transcribed-sample.pdf")
        assert result.errors == []
        assert len(result.records) == 1
        record = result.records[0]
        assert record.registration_no == row["registration_no"]
        assert record.product_name == row["product_name"]
        assert record.holder == row["holder"]
        assert record.manufacturer == row["manufacturer"]
        assert record.status == row["status"]
        assert record.category == row["category"]
        assert record.registration_date_raw == row["registration_date"]
        assert record.expiry_date_raw == row["expiry_date"]
        assert record.registration_date.isoformat() == "-".join(reversed(row["registration_date"].split("-")))


def test_rejects_non_pdf(tmp_path: Path):
    path = tmp_path / "bad.pdf"
    path.write_text("<html>error</html>")
    result = parse_pdf(path)
    assert not result.records
    assert "not a PDF" in result.errors[0].message


def test_same_registration_with_distinct_source_rows_is_preserved():
    rows = [
        ["No.", "No. Pendaftaran MAL", "Nama Produk", "Pemegang", "Pengilang", "Status", "Kategori", "Tarikh Daftar", "Tarikh Luput"],
        ["21", "MAL09082827T", "Bai Hu Tang Extract Powder", "LIFECARE ESSENTIAL SDN. BHD.", "SHENG CHANG PHARMACEUTICAL CO., LTD.", "COS - Approved", "NATURAL PRODUCT-TRADITIONAL(GENERAL)", "04-02-2025", "04-02-2030"],
        ["238", "MAL09082827T", "Bai Hu Tang Extract Powder", "LIFECARE ESSENTIAL SDN. BHD.", "SHENG CHANG PHARMACEUTICAL CO., LTD.", "RE-REGISTRATION (RENEWAL)", "NATURAL PRODUCT-TRADITIONAL(GENERAL)", "04-02-2025", "04-02-2030"],
    ]
    result = parse_rows(rows, 1)
    assert result.errors == []
    assert [r.registration_no for r in result.records] == ["MAL09082827T", "MAL09082827T"]
    assert [r.status for r in result.records] == ["COS - Approved", "RE-REGISTRATION (RENEWAL)"]

