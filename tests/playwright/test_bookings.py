"""End-to-end reservation flow: customer books → staff approves → calendar blocks the dates."""
import re
from datetime import date, timedelta

from playwright.sync_api import expect

from conftest import BASE_URL, STAFF, login, shot


def register_customer(page, unique):
    page.goto(f"{BASE_URL}/accounts/register/")
    page.fill("#id_username", f"cust{unique.lower()}")
    page.fill("#id_email", f"cust{unique.lower()}@example.com")
    page.fill("#id_first_name", "Asha")
    page.fill("#id_password1", "Cust!Strong-Pass-77")
    page.fill("#id_password2", "Cust!Strong-Pass-77")
    page.click("form[data-testid=register-form] button[type=submit]")
    expect(page).to_have_url(re.compile(r"/bookings/$"))


def test_customer_books_staff_approves_calendar_blocks(browser, unique):
    start = date.today() + timedelta(days=20)
    end = start + timedelta(days=2)
    cust_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    cust = cust_ctx.new_page()
    register_customer(cust, unique)
    # availability check for the dates
    cust.fill("#f-start", start.isoformat())
    cust.fill("#f-end", end.isoformat())
    cust.fill("#f-q", "Standing Desk")
    cust.click("form[data-testid=availability-form] button[type=submit]")
    card = cust.locator("[data-testid=catalogue-item][data-sku=FUR-002]")
    expect(card).to_be_visible()
    free_before = int(card.locator("[data-testid=available]").inner_text().split("/")[0])
    assert free_before >= 1
    expect(card).to_contain_text("₹")
    shot(cust, "customer-dashboard")
    card.locator("[data-testid=book-item]").click()
    expect(cust.locator("[data-testid=free-units]")).to_have_text(str(free_before))
    cust.fill("#id_quantity", str(free_before))
    cust.fill("#id_note", "Playwright event")
    shot(cust, "booking-form")
    cust.click("form[data-testid=booking-form] button[type=submit]")
    expect(cust.get_by_text("sent for approval")).to_be_visible()
    booking_id = cust.locator("[data-testid=booking-id]").inner_text().strip()
    assert re.match(r"^BK-\d{6}-[0-9A-F]{6}$", booking_id)
    expect(cust.locator("[data-testid=booking-status]")).to_contain_text("Pending")

    # A second customer cannot book more than remains once staff approve
    staff_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    staff = staff_ctx.new_page()
    login(staff, STAFF)
    expect(staff.locator("[data-testid=booking-widgets]")).to_be_visible()
    staff.goto(f"{BASE_URL}/bookings/manage/?q={booking_id}")
    expect(staff.locator("[data-testid=booking-table]")).to_contain_text(booking_id)
    shot(staff, "staff-booking-requests")
    staff.click(f"[data-testid=approve-{booking_id}]")
    expect(staff.get_by_text(f"Booking {booking_id} approved")).to_be_visible()

    # calendar shows the item on each booked day
    staff.goto(f"{BASE_URL}/bookings/calendar/?month={start:%Y-%m}")
    cell = staff.locator(f"td[data-date='{start.isoformat()}']")
    expect(cell).to_contain_text("Standing Desk")
    shot(staff, "staff-calendar")

    # dates are now blocked for customers
    cust.goto(f"{BASE_URL}/bookings/?start={start.isoformat()}&end={end.isoformat()}&q=Standing+Desk")
    card = cust.locator("[data-testid=catalogue-item][data-sku=FUR-002]")
    expect(card.locator("[data-testid=available]")).to_contain_text("0 /")
    expect(card).to_contain_text("Fully booked")
    cust.goto(f"{BASE_URL}/bookings/mine/")
    expect(cust.locator("[data-testid=my-bookings]")).to_contain_text("Approved")

    # customer cancels → units free again
    cust.locator("[data-testid=my-bookings] tr", has_text=booking_id).locator("button", has_text="Cancel").click()
    expect(cust.get_by_text(f"Booking {booking_id} cancelled")).to_be_visible()
    cust_ctx.close()
    staff_ctx.close()


def test_customer_cannot_open_staff_pages(page, unique):
    register_customer(page, unique)
    for path in ("/products/", "/transactions/", "/bookings/manage/", "/bookings/calendar/"):
        resp = page.goto(BASE_URL + path)
        assert resp.status == 403, path
    page.goto(f"{BASE_URL}/dashboard/")
    expect(page).to_have_url(re.compile(r"/bookings/$"))
