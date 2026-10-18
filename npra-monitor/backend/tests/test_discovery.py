from app.importer.discovery import canonicalize_url, extract_document_refs_from_links


def test_filters_to_dca404_and_newer_and_sorts():
    links = [
        {"text": "DCA403", "href": "/2024/dca403.pdf"},
        {"text": "DCA424", "href": "https://www.npra.gov.my/2026/dca424.pdf#page=1"},
        {"text": " DCA 404 ", "href": "/2025/dca404.pdf"},
        {"text": "Approved Additional Indication DCA 424", "href": "/indication/dca424.html"},
        {"text": "DCA414", "href": "/2025/dca414.pdf"},
        {"text": "DCA414", "href": "/2025/dca414.pdf"},
    ]
    refs = extract_document_refs_from_links(links, "https://www.npra.gov.my/index.php/en/page")
    assert [r.meeting_number for r in refs] == [404, 414, 424]
    assert refs[0].year == 2025
    assert refs[-1].url == "https://www.npra.gov.my/2026/dca424.pdf"


def test_canonicalize_removes_fragment_not_query():
    assert canonicalize_url("HTTPS://NPRA.GOV.MY/a.pdf?x=1#page=2") == "https://npra.gov.my/a.pdf?x=1"
