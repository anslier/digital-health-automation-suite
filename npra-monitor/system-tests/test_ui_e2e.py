from __future__ import annotations

import json
import os

from playwright.sync_api import Route, Request, sync_playwright


WEB_URL = os.getenv("NPRA_TEST_WEB_URL", "http://npra-web").rstrip("/")
EMAIL = os.getenv("NPRA_ADMIN_EMAIL", "admin@npra.local")
PASSWORD = os.getenv("NPRA_ADMIN_PASSWORD", "npra-demo-2026")


def _api_route(route: Route, request: Request) -> None:
    """Keep the browser test non-destructive.

    The app is loaded through the Compose service name (`npra-web`), while the
    production origin guard intentionally allows localhost:4201. Rewriting only
    the Origin header lets this isolated Docker test exercise the same nginx/API
    path without weakening production security.

    POST /api/runs is fulfilled locally so clicking Run import now validates the
    UI behaviour but does not start a real NPRA scrape. Worker behaviour is
    covered separately by test_worker_runtime.py and the optional -LiveWorker
    PowerShell smoke test.
    """
    if request.method == "POST" and request.url.rstrip("/").endswith("/api/runs"):
        route.fulfill(
            status=202,
            content_type="application/json",
            body=json.dumps(
                {
                    "id": "e2e-fake-run",
                    "trigger": "UI",
                    "status": "QUEUED",
                    "requested_at": "2026-10-05T00:00:00",
                    "started_at": None,
                    "finished_at": None,
                    "heartbeat_at": None,
                    "discovered_count": 0,
                    "skipped_count": 0,
                    "downloaded_count": 0,
                    "processed_count": 0,
                    "failed_count": 0,
                    "observation_count": 0,
                    "error_message": None,
                }
            ),
        )
        return

    headers = dict(request.headers)
    headers["origin"] = "http://localhost:4201"
    route.continue_(headers=headers)


def test_dashboard_login_navigation_and_run_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.route("**/api/**", _api_route)

        try:
            page.goto(WEB_URL, wait_until="networkidle", timeout=30_000)
            page.get_by_role("heading", name="Sign in").wait_for()

            page.get_by_label("Email").fill("wrong@example.test")
            page.get_by_label("Password").fill("wrong-password")
            page.get_by_role("button", name="Use demo admin").click()
            assert page.get_by_label("Email").input_value() == "admin@npra.local"
            assert page.get_by_label("Password").input_value() == "npra-demo-2026"

            page.get_by_label("Email").fill(EMAIL)
            page.get_by_label("Password").fill(PASSWORD)
            page.get_by_role("button", name="Sign in").click()

            page.get_by_role("heading", name="Product records").wait_for(timeout=20_000)
            page.get_by_role("button", name="Records", exact=False).wait_for()

            page.get_by_role("button", name="Import history").click()
            page.get_by_role("heading", name="Import history").wait_for()

            page.get_by_role("button", name="Schedule").click()
            page.get_by_role("heading", name="Automatic monitor").wait_for()
            page.get_by_role("button", name="Save schedule").wait_for()

            # Persist the existing disabled config; no timed import is enabled.
            page.get_by_role("button", name="Save schedule").click()
            page.get_by_role("button", name="Save schedule").wait_for(state="visible")

            # Return to a stable page, then verify the main CTA's UI flow. The
            # POST itself is intercepted above, so this creates no real import.
            page.get_by_role("button", name="Records", exact=False).click()
            page.get_by_role("button", name="Run import now").click()
            page.get_by_role("heading", name="Import history").wait_for(timeout=20_000)

            page.get_by_role("button", name="Sign out").click()
            page.get_by_role("heading", name="Sign in").wait_for()
        finally:
            context.close()
            browser.close()
