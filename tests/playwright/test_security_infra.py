import re

from playwright.sync_api import expect

from conftest import BASE_URL


def test_health_endpoint(page):
    resp = page.request.get(f"{BASE_URL}/health/")
    assert resp.status == 200
    data = resp.json()
    assert data["application"] == "Inventory Management System"
    assert data["database"] == "connected"
    assert data["status"] in ("healthy", "degraded")
    assert "mongodb" in data


def test_csrf_protection(page):
    resp = page.request.post(f"{BASE_URL}/assistant/chat/", data={"message": "hi"})
    assert resp.status == 403
    resp = page.request.post(f"{BASE_URL}/accounts/login/", form={"username": "admin", "password": "x"})
    assert resp.status == 403


def test_api_permissions(page):
    assert page.request.get(f"{BASE_URL}/api/products/").status in (401, 403)
    assert page.request.post(f"{BASE_URL}/api/faqs/", data={"question": "x"}).status in (401, 403)


def test_no_secrets_in_frontend(page):
    page.goto(f"{BASE_URL}/")
    html = page.content()
    scripts = [page.request.get(BASE_URL + src).text() if src.startswith("/") else ""
               for src in page.locator("script[src]").evaluate_all("els => els.map(e => e.getAttribute('src'))")]
    for blob in [html, *scripts]:
        for marker in ("mongodb://", "mongodb+srv://", "AI_API_KEY", "SECRET_KEY", "postgresql://"):
            assert marker not in blob


def test_session_cookie_httponly(admin_page):
    cookies = {c["name"]: c for c in admin_page.context.cookies()}
    assert cookies["sessionid"]["httpOnly"] is True
    assert cookies["csrftoken"]["httpOnly"] is True
    if BASE_URL.startswith("https://"):
        assert cookies["sessionid"]["secure"] is True


def test_external_api_fallback_does_not_break_reports(admin_page):
    admin_page.goto(f"{BASE_URL}/reports/")
    card = admin_page.locator("[data-testid=currency-card]")
    expect(card).to_be_visible()
    expect(card).to_contain_text(re.compile(r"Live|Fallback rates"))
    expect(admin_page.locator("[data-testid=report-table]")).to_be_visible()
