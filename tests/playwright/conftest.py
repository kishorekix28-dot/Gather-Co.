"""Playwright end-to-end configuration.

Run against a running server (local production-mode gunicorn or the live HTTPS URL):

    E2E_BASE_URL=http://127.0.0.1:8001 E2E_ADMIN_PASSWORD=... E2E_STAFF_PASSWORD=... \
    E2E_MONGODB_URI=mongodb://127.0.0.1:27017 E2E_MONGODB_DB=inventory_e2e \
    pytest tests/playwright --html=docs/test-reports/playwright-report.html --self-contained-html
"""
import os
import re
import uuid
from pathlib import Path

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
ADMIN = (os.environ.get("E2E_ADMIN_USER", "admin"), os.environ.get("E2E_ADMIN_PASSWORD", ""))
STAFF = (os.environ.get("E2E_STAFF_USER", "staff"), os.environ.get("E2E_STAFF_PASSWORD", ""))
SCREENSHOT_DIR = Path(__file__).resolve().parents[2] / "docs" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1366, "height": 860}}


def login(page, creds):
    page.goto(f"{BASE_URL}/accounts/login/")
    page.fill("#id_username", creds[0])
    page.fill("#id_password", creds[1])
    page.click("form[data-testid=login-form] button[type=submit]")
    page.wait_for_url(re.compile(r".*/dashboard/$"))


@pytest.fixture
def admin_page(page):
    if not ADMIN[1]:
        pytest.skip("E2E_ADMIN_PASSWORD not set")
    login(page, ADMIN)
    return page


@pytest.fixture
def staff_page(page):
    if not STAFF[1]:
        pytest.skip("E2E_STAFF_PASSWORD not set")
    login(page, STAFF)
    return page


@pytest.fixture
def unique():
    return uuid.uuid4().hex[:6].upper()


def shot(page, name, full_page=True):
    page.screenshot(path=str(SCREENSHOT_DIR / f"{name}.png"), full_page=full_page)
