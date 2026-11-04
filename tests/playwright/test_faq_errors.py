import re

from playwright.sync_api import expect

from conftest import BASE_URL, shot

REQUIRED = [400, 401, 403, 404, 405, 408, 429, 500]


def test_faq_page_loads_from_api(page):
    with page.expect_response(lambda r: r.url.endswith("/api/faqs/") and r.status == 200) as resp_info:
        page.goto(f"{BASE_URL}/faq/")
    api_items = resp_info.value.json()
    assert len(api_items) >= 10
    items = page.locator("[data-testid=faq-item]")
    expect(items).to_have_count(len(api_items))
    rendered = items.locator(".accordion-button").all_text_contents()
    for faq in api_items:
        assert any(faq["question"] in r for r in rendered)
    shot(page, "faq")


def test_faq_search_uses_api(page):
    page.goto(f"{BASE_URL}/faq/")
    with page.expect_response(re.compile(r".*/api/faqs/search/\?q=supplier")):
        page.fill("[data-testid=faq-search]", "supplier")
    expect(page.locator("[data-testid=faq-item]").first).to_contain_text("supplier")


def test_error_code_api(page):
    data = page.request.get(f"{BASE_URL}/api/errors/").json()
    codes = [e["code"] for e in data]
    assert all(c in codes for c in REQUIRED)
    detail = page.request.get(f"{BASE_URL}/api/errors/404/").json()
    assert detail["title"] == "Page Not Found" and detail["recommended_solution"]
    search = page.request.get(f"{BASE_URL}/api/errors/search/?q=unauthorized").json()
    assert [r["code"] for r in search["results"]] == [401]
    faq_detail = page.request.get(f"{BASE_URL}/api/faqs/1/")
    assert faq_detail.status == 200


def test_custom_404_with_ask_assistant(page):
    resp = page.goto(f"{BASE_URL}/no/such/page/")
    assert resp.status == 404
    expect(page.locator("[data-testid=error-code]")).to_have_text("404")
    expect(page.locator("[data-testid=return-home]")).to_be_visible()
    shot(page, "error-404")
    page.click("[data-testid=ask-assistant]")
    expect(page.locator("[data-testid=chat-window]")).to_be_visible()
    expect(page.locator("[data-testid=bot-message]").first).to_contain_text("Page Not Found", timeout=15000)
    page.click("[data-testid=return-home]") if page.locator("[data-testid=return-home]").is_visible() else None


def test_custom_500_with_ask_assistant(admin_page):
    page = admin_page
    resp = page.goto(f"{BASE_URL}/diagnostics/trigger-500/")
    assert resp.status == 500
    expect(page.locator("[data-testid=error-code]")).to_have_text("500")
    shot(page, "error-500")
    page.click("[data-testid=ask-assistant]")
    expect(page.locator("[data-testid=chat-window]")).to_be_visible()
    expect(page.locator("[data-testid=bot-message]").first).to_contain_text("Internal Server Error", timeout=15000)
