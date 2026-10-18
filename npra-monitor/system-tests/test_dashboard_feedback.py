import json
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

from test_ui_e2e import WEB_URL


def test_paging_save_confirmation_and_live_import_feedback():
    state = {"posts": 0, "polls": 0, "schedule": {
        "enabled": False, "cadence": "DAILY", "local_time": "13:55",
        "weekday": None, "day_of_month": 8, "timezone": "Asia/Kuala_Lumpur",
        "revision": 8, "next_run_at": None}}

    def route_api(route):
        request = route.request
        url = urlparse(request.url)
        data = {}
        if url.path == "/api/auth/me":
            data = {"email": "admin@npra.local"}
        elif url.path == "/api/records":
            params = parse_qs(url.query)
            page = int(params.get("page", [1])[0])
            size = int(params.get("page_size", [50])[0])
            total = 1 if params.get("q") else 103
            start = (page - 1) * size
            data = {"items": [{"registration_no": f"MAL{i:05}", "product_name": f"Product {i}",
                    "meeting": 424} for i in range(start + 1, min(start + size, total) + 1)],
                    "page": page, "page_size": size, "total": total}
        elif url.path == "/api/schedule":
            if request.method == "PUT":
                state["schedule"] = {**json.loads(request.post_data), "revision": 9}
            data = state["schedule"]
        elif url.path == "/api/runs":
            run = {"id": "feedback-test", "trigger": "UI", "status": "QUEUED",
                   "requested_at": "2026-10-05T05:35:47", "started_at": None, "finished_at": None,
                   "discovered_count": 0, "skipped_count": 0, "processed_count": 0,
                   "failed_count": 0, "observation_count": 0}
            if request.method == "POST":
                state["posts"] += 1
                data = run
            elif state["posts"]:
                state["polls"] += 1
                run["status"] = "SUCCESS" if state["polls"] >= 3 else "QUEUED"
                data = [run]
            else:
                data = []
        route.fulfill(status=202 if request.method == "POST" else 200,
                      content_type="application/json", body=json.dumps(data))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route("**/api/**", route_api)
        try:
            page.goto(WEB_URL)
            expect(page.get_by_text("Showing 1–50 of 103 records", exact=True).first).to_be_visible()
            page.get_by_role("button", name="Next page", exact=True).first.click()
            expect(page.get_by_text("Showing 51–100 of 103 records", exact=True).first).to_be_visible()
            page.get_by_role("button", name="Last page", exact=True).first.click()
            expect(page.get_by_text("Showing 101–103 of 103 records", exact=True).first).to_be_visible()
            expect(page.get_by_role("button", name="Next page", exact=True).first).to_be_disabled()
            page.get_by_placeholder("Search product, MAL number, holder…").fill("Product 1")
            page.get_by_role("button", name="Search", exact=True).click()
            expect(page.get_by_text("Showing 1–1 of 1 records", exact=True).first).to_be_visible()
            page.get_by_role("button", name="Schedule", exact=True).click()
            page.get_by_role("button", name="Save schedule", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="Schedule saved")).to_be_visible()
            expect(page.get_by_text("Automatic checks are disabled", exact=True)).to_be_visible()
            page.get_by_role("button", name="Run import now", exact=True).click()
            expect(page.get_by_role("button", name="Import queued…", exact=True)).to_be_disabled()
            expect(page.get_by_text("Import queued", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Run import now", exact=True)).to_be_enabled(timeout=15000)
            assert state["posts"] == 1
            expect(page.get_by_text("Import completed successfully", exact=True)).to_be_visible()
            page.set_viewport_size({"width": 390, "height": 844})
            page.get_by_role("button", name="Records", exact=False).click()
            expect(page.get_by_text("Showing 1–1 of 1 records", exact=True).first).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            page.get_by_role("button", name="Schedule", exact=True).click()
            expect(page.get_by_role("button", name="Save schedule", exact=True)).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        finally:
            browser.close()
