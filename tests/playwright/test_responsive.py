import pytest
from playwright.sync_api import expect

from conftest import ADMIN, BASE_URL, login, shot

VIEWPORTS = {"desktop": (1440, 900), "tablet": (820, 1180), "mobile": (390, 844)}
PAGES = {"dashboard": "/dashboard/", "products": "/products/", "faq": "/faq/", "tickets": "/tickets/"}


@pytest.mark.parametrize("device", list(VIEWPORTS))
def test_layout_responsive(browser, device):
    if not ADMIN[1]:
        pytest.skip("E2E_ADMIN_PASSWORD not set")
    w, h = VIEWPORTS[device]
    context = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                                  is_mobile=device == "mobile", has_touch=device != "desktop")
    page = context.new_page()
    page.goto(f"{BASE_URL}/")
    shot(page, f"{device}-home", full_page=False)
    login(page, ADMIN)
    for name, path in PAGES.items():
        page.goto(BASE_URL + path)
        page.wait_for_load_state("networkidle")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 1, f"{name} overflows horizontally by {overflow}px on {device}"
        expect(page.locator("[data-testid=chat-launcher]")).to_be_visible()
        shot(page, f"{device}-{name}", full_page=False)
    if device != "desktop":
        page.goto(f"{BASE_URL}/dashboard/")
        sidebar = page.locator("#sidebar")
        page.click("[data-sidebar-toggle]")
        page.wait_for_timeout(350)
        expect(sidebar.locator("text=Products")).to_be_in_viewport()
        shot(page, f"{device}-menu-open", full_page=False)
        page.click("#sidebar >> text=Products")
        expect(page.locator("h1")).to_have_text("Products")
    else:
        page.goto(f"{BASE_URL}/dashboard/")
        page.click("[data-testid=chat-launcher]")
        expect(page.locator("[data-testid=chat-window]")).to_be_visible()
    context.close()
