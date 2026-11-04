import os
import re

import pytest
from playwright.sync_api import expect

from conftest import BASE_URL, shot

PUBLIC_PAGES = ["/", "/faq/", "/accounts/login/", "/accounts/register/", "/this-page-does-not-exist/"]
PRIVATE_PAGES = ["/dashboard/", "/products/", "/categories/", "/transactions/", "/transactions/new/", "/suppliers/",
                 "/reports/", "/faq/", "/tickets/", "/tickets/new/", "/accounts/profile/", "/assistant/knowledge-base/"]


def ask(page, question):
    if not page.locator("[data-testid=chat-window]").is_visible():
        page.click("[data-testid=chat-launcher]")
    before = page.locator("[data-testid=bot-message]").count()
    page.fill("[data-testid=chat-input]", question)
    page.click("[data-testid=chat-send]")
    msg = page.locator("[data-testid=bot-message]").nth(before)
    expect(msg).to_be_visible(timeout=15000)
    return msg


def test_widget_on_every_public_page(page):
    for path in PUBLIC_PAGES:
        page.goto(BASE_URL + path)
        launcher = page.locator("[data-testid=chat-launcher]")
        expect(launcher).to_be_visible()
        launcher.click()
        expect(page.locator("[data-testid=chat-window]")).to_be_visible()
        page.click("#chatClose")
        expect(page.locator("[data-testid=chat-window]")).to_be_hidden()


def test_widget_on_every_private_page(admin_page):
    for path in PRIVATE_PAGES:
        admin_page.goto(BASE_URL + path)
        expect(admin_page.locator("[data-testid=chat-launcher]")).to_be_visible()


def test_faq_and_error_answers_from_database(page):
    page.goto(f"{BASE_URL}/")
    msg = ask(page, "How do I add a product?")
    expect(msg).to_contain_text("Add product")
    assert msg.get_attribute("data-source") == "faq"
    msg = ask(page, "How do I update stock?")
    assert msg.get_attribute("data-source") == "faq"
    msg = ask(page, "Why is my product not appearing?")
    assert msg.get_attribute("data-source") == "help_docs"
    errors = page.request.get(f"{BASE_URL}/api/errors/").json()
    for err in errors:
        msg = ask(page, f"What does error {err['code']} mean?")
        assert msg.get_attribute("data-source") == "error_database"
        expect(msg).to_contain_text(err["title"])
    shot(page, "assistant-answers", full_page=False)


def test_unknown_question_creates_ticket_once(staff_page, unique):
    page = staff_page
    page.goto(f"{BASE_URL}/dashboard/")
    question = f"How do I sync stock with the Mars colony depot {unique}?"
    msg = ask(page, question)
    assert msg.get_attribute("data-source") == "ai_fallback"
    ticket_id = msg.locator("[data-testid=ticket-id]").inner_text().strip()
    assert re.match(r"^TKT-\d{8}-[0-9A-F]{6}$", ticket_id)
    shot(page, "assistant-ticket", full_page=False)
    again = ask(page, question)
    expect(again).to_contain_text("already asked")
    assert again.locator("[data-testid=ticket-id]").inner_text().strip() == ticket_id
    page.goto(f"{BASE_URL}/tickets/?q={ticket_id}")
    rows = page.locator("[data-testid=ticket-table] tbody tr")
    expect(rows).to_have_count(1)
    rows.first.locator("a").click()
    expect(page.locator("[data-testid=ticket-id-heading]")).to_have_text(ticket_id)


def test_feedback_stored_in_mongodb(page):
    pytest.importorskip("pymongo")
    from pymongo import MongoClient

    uri = os.environ.get("E2E_MONGODB_URI")
    if not uri:
        pytest.skip("E2E_MONGODB_URI not set (cannot inspect the server's MongoDB directly)")
    db = MongoClient(uri, serverSelectionTimeoutMS=3000)[os.environ.get("E2E_MONGODB_DB", "inventory_assistant")]
    page.goto(f"{BASE_URL}/faq/")
    msg = ask(page, "How do I add a supplier?")
    message_id = msg.get_attribute("data-message-id")
    assert message_id
    stored = db.messages.find_one({"_id": __import__("bson").ObjectId(message_id)})
    assert stored["source"] == "faq" and stored["user_message"] == "How do I add a supplier?"
    msg.locator("[data-testid=feedback-up]").click()
    expect(msg.locator("[data-testid=feedback-thanks]")).to_be_visible()
    fb = db.feedback.find_one({"message_id": message_id})
    assert fb and fb["rating"] == 1
    assert db.conversations.find_one({"conversation_id": stored["conversation_id"]})


def test_chat_error_handling(page):
    page.goto(f"{BASE_URL}/")
    page.route("**/assistant/chat/", lambda route: route.fulfill(status=500, body="oops"))
    page.click("[data-testid=chat-launcher]")
    page.fill("[data-testid=chat-input]", "hello")
    page.click("[data-testid=chat-send]")
    expect(page.locator(".msg-error")).to_contain_text("server error")
    page.unroute("**/assistant/chat/")
    page.route("**/assistant/chat/", lambda route: route.abort())
    page.fill("[data-testid=chat-input]", "hello again")
    page.click("[data-testid=chat-send]")
    expect(page.locator(".msg-error").nth(1)).to_contain_text("Network error")
