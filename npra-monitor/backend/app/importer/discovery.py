from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from app.importer.types import DocumentRef

_DCA_RE = re.compile(r"\bDCA\s*[-–—]?\s*(\d{3})\b", re.I)


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))


def extract_document_refs_from_links(links: list[dict], base_url: str, minimum_dca: int = 404) -> list[DocumentRef]:
    refs: dict[str, DocumentRef] = {}
    for link in links:
        text = " ".join(str(link.get(k, "")) for k in ("text", "title", "ariaLabel")).strip()
        match = _DCA_RE.search(text)
        if not match:
            continue
        meeting = int(match.group(1))
        if meeting < minimum_dca:
            continue
        href = str(link.get("href") or "").strip()
        if not href:
            continue
        absolute = canonicalize_url(urljoin(base_url, href))
        # NPRA links for this page are direct PDFs. Keep only PDFs to avoid confusing
        # the similarly named Additional Indications page.
        if ".pdf" not in absolute.lower():
            continue
        year_match = re.search(r"/(20\d{2})/", absolute)
        year = int(year_match.group(1)) if year_match else None
        ref = DocumentRef(meeting_number=meeting, meeting_label=f"DCA{meeting}", url=absolute, year=year)
        refs.setdefault(absolute, ref)
    return sorted(refs.values(), key=lambda r: r.meeting_number)


def discover_documents(page, source_url: str | None = None, minimum_dca: int = 404) -> list[DocumentRef]:
    if source_url:
        page.goto(source_url, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_selector("a", timeout=30_000)
    links = page.locator("a").evaluate_all(
        "els => els.map(a => ({text: (a.textContent || '').trim(), title: a.title || '', ariaLabel: a.getAttribute('aria-label') || '', href: a.href || ''}))"
    )
    return extract_document_refs_from_links(links, page.url, minimum_dca=minimum_dca)
