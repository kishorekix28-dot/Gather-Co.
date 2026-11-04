import re
from pathlib import Path

from playwright.sync_api import expect

from conftest import BASE_URL, shot

FIXTURE_IMAGE = Path(__file__).resolve().parents[2] / "static" / "images" / "sample-product.png"


def create_product(page, sku, qty="10", min_level="5", name=None):
    page.goto(f"{BASE_URL}/products/new/")
    page.fill("#id_name", name or f"E2E Product {sku}")
    page.fill("#id_sku", sku)
    page.select_option("#id_category", index=1)
    page.fill("#id_price", "49.99")
    page.fill("#id_cost", "20.00")
    page.fill("#id_opening_stock", qty)
    page.fill("#id_min_stock_level", min_level)
    page.fill("#id_description", "Created by Playwright")
    if FIXTURE_IMAGE.exists():
        page.set_input_files("#id_image", str(FIXTURE_IMAGE))
    page.click("form[data-testid=product-form] button[type=submit]")
    expect(page.locator("h1")).to_contain_text(name or f"E2E Product {sku}")


def test_add_edit_delete_product(admin_page, unique):
    page = admin_page
    sku = f"E2E-{unique}"
    create_product(page, sku)
    expect(page.locator("[data-testid=product-quantity]")).to_have_text("10")
    shot(page, "product-detail")
    # duplicate SKU is rejected
    page.goto(f"{BASE_URL}/products/new/")
    page.fill("#id_name", "Duplicate")
    page.fill("#id_sku", sku.lower())
    page.fill("#id_price", "1")
    page.fill("#id_cost", "1")
    page.click("form[data-testid=product-form] button[type=submit]")
    expect(page.get_by_text("already exists")).to_be_visible()
    # edit
    page.goto(f"{BASE_URL}/products/?sku={sku}")
    page.click(f"text=E2E Product {sku}")
    page.click("[data-testid=edit-product]")
    page.fill("#id_name", f"Edited {sku}")
    page.fill("#id_price", "59.00")
    page.click("form[data-testid=product-form] button[type=submit]")
    expect(page.locator("h1")).to_have_text(f"Edited {sku}")
    expect(page.get_by_text("₹59.00")).to_be_visible()
    # delete
    page.click("[data-testid=delete-product]")
    page.click("[data-testid=confirm-delete]")
    expect(page).to_have_url(re.compile(r"/products/$"))
    page.goto(f"{BASE_URL}/products/?sku={sku}")
    expect(page.locator("[data-testid=empty-state]")).to_be_visible()


def test_stock_in_out_negative_and_alerts(admin_page, unique):
    page = admin_page
    sku = f"STK-{unique}"
    create_product(page, sku, qty="8", min_level="5")
    pid = page.url.rstrip("/").split("/")[-1]
    # stock in
    page.goto(f"{BASE_URL}/transactions/new/?product={pid}&type=IN")
    page.fill("#id_quantity", "4")
    page.fill("#id_reference", "PO-E2E")
    page.click("form[data-testid=movement-form] button[type=submit]")
    expect(page.get_by_text(f"Stock In recorded for {sku}: 8 → 12")).to_be_visible()
    # negative prevented
    page.goto(f"{BASE_URL}/transactions/new/?product={pid}&type=OUT")
    page.fill("#id_quantity", "50")
    page.click("form[data-testid=movement-form] button[type=submit]")
    expect(page.get_by_text("Insufficient stock")).to_be_visible()
    shot(page, "negative-stock-prevented")
    # stock out to low level -> low-stock alert
    page.fill("#id_quantity", "9")
    page.click("form[data-testid=movement-form] button[type=submit]")
    expect(page.get_by_text("Low stock alert")).to_be_visible()
    # stock out to zero -> out-of-stock alert
    page.goto(f"{BASE_URL}/transactions/new/?product={pid}&type=OUT")
    page.fill("#id_quantity", "3")
    page.click("form[data-testid=movement-form] button[type=submit]")
    expect(page.get_by_text("Out of stock alert")).to_be_visible()
    shot(page, "transactions")
    page.goto(f"{BASE_URL}/products/{pid}/")
    expect(page.locator("[data-testid=product-quantity]")).to_have_text("0")
    expect(page.get_by_text("Out of stock").first).to_be_visible()


def test_staff_records_stock(staff_page):
    page = staff_page
    page.goto(f"{BASE_URL}/transactions/new/")
    options = page.locator("#id_transaction_type option").all_text_contents()
    assert "Adjustment" not in options and "Stock In" in options
    page.select_option("#id_product", index=1)
    page.select_option("#id_transaction_type", "IN")
    page.fill("#id_quantity", "2")
    page.click("form[data-testid=movement-form] button[type=submit]")
    expect(page.get_by_text("Stock In recorded")).to_be_visible()


def test_search_filter_sort_paginate(admin_page):
    page = admin_page
    page.goto(f"{BASE_URL}/products/")
    shot(page, "products")
    page.fill("form[data-testid=product-filters] input[name=q]", "keyboard")
    page.click("form[data-testid=product-filters] button[type=submit]")
    rows = page.locator("[data-testid=product-table] tbody tr")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Mechanical Keyboard")
    page.goto(f"{BASE_URL}/products/?sku=NET")
    expect(page.locator("[data-testid=product-table] tbody tr").first).to_contain_text("NET-")
    page.goto(f"{BASE_URL}/products/")
    page.select_option("select[name=stock]", "out")
    page.wait_for_url(re.compile(r"stock=out"))
    for status in page.locator("[data-testid=product-table] tbody tr td:nth-child(7)").all_text_contents():
        assert "Out of stock" in status
    page.goto(f"{BASE_URL}/products/?stock=low")
    for status in page.locator("[data-testid=product-table] tbody tr td:nth-child(7)").all_text_contents():
        assert "Low stock" in status
    page.goto(f"{BASE_URL}/products/?sort=-price")
    prices = [float(p.strip().lstrip("₹").replace(",", "")) for p in
              page.locator("[data-testid=product-table] tbody tr td:nth-child(4)").all_text_contents()]
    assert prices == sorted(prices, reverse=True)
    page.goto(f"{BASE_URL}/products/?sort=quantity")
    qtys = [int(q) for q in page.locator("[data-testid=product-table] tbody tr td:nth-child(6)").all_text_contents()]
    assert qtys == sorted(qtys)
    expect(page.locator(".pagination")).to_be_visible()
    page.click(".pagination a[aria-label=Next]")
    expect(page).to_have_url(re.compile(r"page=2"))


def test_dashboard_reports_and_csv(admin_page):
    page = admin_page
    page.goto(f"{BASE_URL}/dashboard/")
    expect(page.locator("[data-testid=stat-cards] .stat-card")).to_have_count(6)
    expect(page.locator("#monthlyChart")).to_be_visible()
    shot(page, "dashboard")
    page.goto(f"{BASE_URL}/reports/")
    expect(page.locator("[data-testid=currency-card]")).to_be_visible()
    shot(page, "reports")
    with page.expect_download() as dl:
        page.click("[data-testid=export-csv]")
    assert dl.value.suggested_filename.startswith("inventory-report-")
    content = Path(dl.value.path()).read_text()
    assert content.splitlines()[0].startswith("SKU,Name,Category")


def test_categories_and_suppliers(admin_page, unique):
    page = admin_page
    page.goto(f"{BASE_URL}/categories/")
    page.fill("main input[name=q]", "furn")
    page.keyboard.press("Enter")
    expect(page.locator("[data-testid=category-table] tbody tr")).to_have_count(1)
    shot(page, "categories")
    page.goto(f"{BASE_URL}/suppliers/new/")
    page.fill("#id_name", f"E2E Supplier {unique}")
    page.fill("#id_email", "e2e@supplier.example")
    page.fill("#id_phone", "+91 98765 43210")
    page.click("main button[type=submit]")
    expect(page.locator("h1")).to_have_text(f"E2E Supplier {unique}")
    page.goto(f"{BASE_URL}/suppliers/")
    shot(page, "suppliers")
