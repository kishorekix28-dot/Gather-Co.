import logging
import subprocess
from pathlib import Path
from unittest import mock

import requests
from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import include, path

from core import currency

from .helpers import PASSWORD, make_user

BASE_DIR = Path(settings.BASE_DIR)


def boom(request):
    raise RuntimeError("test failure")


urlpatterns = [path("boom/", boom), path("", include("config.urls"))]
handler500 = "core.views.server_error"


class ErrorPageTests(TestCase):
    def test_custom_404_page(self):
        resp = self.client.get("/definitely/not/here/")
        self.assertEqual(resp.status_code, 404)
        self.assertTemplateUsed(resp, "404.html")
        self.assertContains(resp, "Page not found", status_code=404)
        self.assertContains(resp, 'data-testid="return-home"', status_code=404)
        self.assertContains(resp, "data-open-assistant", status_code=404)
        self.assertContains(resp, 'id="assistant-widget"', status_code=404)

    def test_missing_record_returns_404(self):
        make_user("staff")
        self.client.login(username="staff", password=PASSWORD)
        self.assertEqual(self.client.get("/products/987654/").status_code, 404)

    @override_settings(ROOT_URLCONF="tests.test_infrastructure", DEBUG=False)
    def test_custom_500_page(self):
        client = Client(raise_request_exception=False)
        resp = client.get("/boom/")
        self.assertEqual(resp.status_code, 500)
        self.assertContains(resp, "Internal server error", status_code=500)
        self.assertContains(resp, "data-open-assistant", status_code=500)
        self.assertContains(resp, "Return Home", status_code=500)

    def test_diagnostics_route_returns_real_500_for_admin_only(self):
        client = Client(raise_request_exception=False)
        make_user("staff")
        client.login(username="staff", password=PASSWORD)
        self.assertEqual(client.get("/diagnostics/trigger-500/").status_code, 403)
        make_user("boss", "ADMIN")
        client.login(username="boss", password=PASSWORD)
        resp = client.get("/diagnostics/trigger-500/")
        self.assertEqual(resp.status_code, 500)
        self.assertContains(resp, "Ask Assistant", status_code=500)

    def test_403_page(self):
        make_user("staff")
        self.client.login(username="staff", password=PASSWORD)
        resp = self.client.get("/suppliers/")
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, "Access forbidden", status_code=403)


class WidgetOnEveryPageTests(TestCase):
    def test_widget_present_on_public_and_private_pages(self):
        for url in ("/", "/faq/", "/accounts/login/", "/accounts/register/"):
            self.assertContains(self.client.get(url), 'id="assistant-widget"', msg_prefix=url)
        make_user("boss", "ADMIN")
        self.client.login(username="boss", password=PASSWORD)
        for url in ("/dashboard/", "/products/", "/categories/", "/transactions/", "/transactions/new/",
                    "/suppliers/", "/reports/", "/faq/", "/tickets/", "/tickets/new/", "/accounts/profile/",
                    "/accounts/users/", "/assistant/knowledge-base/", "/products/new/"):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertContains(resp, 'id="assistant-widget"', msg_prefix=url)


class HealthAndLoggingTests(TestCase):
    def test_health_endpoint_checks_sql(self):
        resp = self.client.get("/health/")
        self.assertIn(resp.status_code, (200,))
        data = resp.json()
        self.assertEqual(data["application"], "Inventory Management System")
        self.assertEqual(data["database"], "connected")
        self.assertIn(data["status"], ("healthy", "degraded"))
        self.assertIn("mongodb", data)

    def test_health_unhealthy_when_sql_down(self):
        with mock.patch("core.views.check_sql", return_value={"status": "unavailable", "engine": "x"}):
            resp = self.client.get("/health/")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["status"], "unhealthy")

    def test_request_logging_fields_and_no_secrets(self):
        make_user("alice")
        with self.assertLogs("inventory.requests", level="INFO") as logs:
            self.client.post("/accounts/login/?token=SECRET123", {"username": "alice", "password": PASSWORD})
            self.client.get("/health/")
        joined = "\n".join(logs.output)
        self.assertRegex(joined, r"method=POST path=/accounts/login/ status=302 duration_ms=\d+\.\d+")
        self.assertIn("method=GET path=/health/ status=200", joined)
        self.assertNotIn(PASSWORD, joined)
        self.assertNotIn("SECRET123", joined)
        self.assertNotIn("sessionid", joined)

    def test_request_log_file_written(self):
        self.client.get("/health/")
        for h in logging.getLogger("inventory.requests").handlers:
            h.flush()
        log_file = Path(settings.LOG_DIR) / "requests.log"
        self.assertTrue(log_file.exists())
        self.assertIn("path=/health/", log_file.read_text())


class CurrencyApiTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_live_rates(self):
        fake = mock.Mock(status_code=200)
        fake.json.return_value = {"date": "2026-11-03", "rates": {"EUR": 0.9, "GBP": 0.8, "INR": 83.5, "JPY": 151.2}}
        with mock.patch("core.currency.requests.get", return_value=fake) as get:
            data = currency.convert_valuation(100)
        self.assertEqual(get.call_args.kwargs["timeout"], 5.0)
        self.assertEqual(data["source"], "live")
        self.assertEqual(str(data["converted"][0]["amount"]), "90.00")

    def test_timeout_falls_back(self):
        with mock.patch("core.currency.requests.get", side_effect=requests.Timeout()), \
                self.assertLogs("inventory.app", level="WARNING") as logs:
            data = currency.get_exchange_rates(use_cache=False)
        self.assertEqual(data["source"], "fallback")
        self.assertIn("timeout", data["error"])
        self.assertTrue(any("fallback" in line for line in logs.output))

    def test_connection_error_and_invalid_responses_fall_back(self):
        bad_json = mock.Mock(status_code=200)
        bad_json.json.side_effect = ValueError("no json")
        missing = mock.Mock(status_code=200)
        missing.json.return_value = {"unexpected": True}
        bad_rate = mock.Mock(status_code=200)
        bad_rate.json.return_value = {"rates": {"EUR": "x"}}
        server_err = mock.Mock(status_code=503)
        for effect in (requests.ConnectionError(), bad_json, missing, bad_rate, server_err):
            kwargs = {"side_effect": effect} if isinstance(effect, Exception) else {"return_value": effect}
            with mock.patch("core.currency.requests.get", **kwargs):
                data = currency.get_exchange_rates(use_cache=False)
            self.assertEqual(data["source"], "fallback")
            self.assertEqual(set(data["rates"]), set(currency.FALLBACK_RATES))

    def test_real_unreachable_host_times_out_quickly(self):
        import time
        with override_settings(CURRENCY_API_URL="http://10.255.255.1/latest", CURRENCY_API_TIMEOUT=1):
            started = time.perf_counter()
            data = currency.get_exchange_rates(use_cache=False)
        self.assertLess(time.perf_counter() - started, 5)
        self.assertEqual(data["source"], "fallback")

    def test_reports_page_works_when_api_down(self):
        make_user("boss", "ADMIN")
        self.client.login(username="boss", password=PASSWORD)
        with mock.patch("core.currency.requests.get", side_effect=requests.ConnectionError()):
            resp = self.client.get("/reports/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fallback rates")


class SecurityTests(TestCase):
    def test_csrf_enforced_on_forms_and_chat(self):
        client = Client(enforce_csrf_checks=True)
        make_user("alice")
        self.assertEqual(client.post("/accounts/login/", {"username": "alice", "password": PASSWORD}).status_code, 403)
        self.assertEqual(client.post("/assistant/chat/", '{"message":"hi"}', content_type="application/json").status_code,
                         403)

    def test_settings_come_from_environment(self):
        source = (BASE_DIR / "config" / "settings.py").read_text()
        for var in ("SECRET_KEY", "DEBUG", "DATABASE_URL", "MONGODB_URI", "AI_API_KEY", "ALLOWED_HOSTS"):
            self.assertTrue(var in source, f"{var} missing from settings")
        example = (BASE_DIR / ".env.example").read_text()
        for var in ("SECRET_KEY=", "DEBUG=", "DATABASE_URL=", "MONGODB_URI=", "AI_API_KEY=", "ALLOWED_HOSTS="):
            self.assertIn(var, example)

    def test_env_is_git_ignored(self):
        lines = (BASE_DIR / ".gitignore").read_text().splitlines()
        self.assertIn(".env", lines)

    def test_no_secrets_in_frontend(self):
        for js in (BASE_DIR / "static" / "js").glob("*.js"):
            text = js.read_text()
            for marker in ("mongodb://", "mongodb+srv://", "AI_API_KEY", "sk-", "SECRET_KEY"):
                self.assertNotIn(marker, text, js.name)

    def test_secret_key_required_in_production(self):
        result = subprocess.run(
            ["python", "-c", "import django,os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()"],
            cwd=BASE_DIR, capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin", "DEBUG": "False", "SECRET_KEY": "", "TESTING": "false",
                 "PYTHONPATH": str(BASE_DIR), **{k: v for k, v in __import__("os").environ.items()
                                                 if k.startswith(("VIRTUAL_ENV",))}},
            executable=__import__("sys").executable,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)
