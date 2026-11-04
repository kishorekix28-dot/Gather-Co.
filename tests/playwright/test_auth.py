import re

from playwright.sync_api import expect

from conftest import BASE_URL, STAFF, login, shot


def test_registration_login_logout(page, unique):
    page.goto(f"{BASE_URL}/accounts/register/")
    shot(page, "register")
    page.fill("#id_username", f"e2e{unique.lower()}")
    page.fill("#id_email", f"e2e{unique.lower()}@example.com")
    page.fill("#id_first_name", "Test")
    page.fill("#id_password1", "E2e!Strong-Pass-99")
    page.fill("#id_password2", "E2e!Strong-Pass-99")
    page.click("form[data-testid=register-form] button[type=submit]")
    expect(page).to_have_url(re.compile(r"/bookings/$"))
    expect(page.get_by_text("Your account has been created")).to_be_visible()
    page.click("button[aria-label='Account menu']")
    page.click("[data-testid=logout]")
    expect(page).to_have_url(re.compile(r"/accounts/login/$"))
    page.goto(f"{BASE_URL}/accounts/login/")
    page.fill("#id_username", f"e2e{unique.lower()}")
    page.fill("#id_password", "E2e!Strong-Pass-99")
    page.click("form[data-testid=login-form] button[type=submit]")
    expect(page).to_have_url(re.compile(r"/bookings/$"))
    expect(page.locator("h1")).to_contain_text("Hi,")


def test_invalid_credentials(page):
    page.goto(f"{BASE_URL}/accounts/login/")
    page.fill("#id_username", "admin")
    page.fill("#id_password", "definitely-wrong")
    page.click("form[data-testid=login-form] button[type=submit]")
    expect(page.locator("[data-testid=login-error]")).to_be_visible()
    shot(page, "login-invalid")


def test_restricted_pages_redirect_to_login(page):
    for path in ("/dashboard/", "/products/", "/transactions/", "/suppliers/", "/reports/", "/tickets/"):
        page.goto(BASE_URL + path)
        expect(page).to_have_url(re.compile(r"/accounts/login/\?next="))


def test_staff_forbidden_from_admin_pages(staff_page):
    resp = staff_page.goto(f"{BASE_URL}/suppliers/")
    assert resp.status == 403
    expect(staff_page.locator("[data-testid=error-code]")).to_have_text("403")
    expect(staff_page.locator("text=Suppliers").first).to_be_visible()
