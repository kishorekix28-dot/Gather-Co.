import logging
import time

from django.conf import settings
from django.db import connection
from django.http import Http404, HttpResponseServerError, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from accounts.roles import admin_required
from assistant import mongo

logger = logging.getLogger("inventory.app")


def check_sql():
    started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"status": "connected", "engine": connection.vendor,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except Exception as exc:
        logger.error("Health check: SQL database unavailable: %s", exc.__class__.__name__)
        return {"status": "unavailable", "engine": connection.vendor, "error": exc.__class__.__name__}


@never_cache
@require_GET
def health_check(request):
    sql = check_sql()
    mongo_status = mongo.ping()
    if sql["status"] != "connected":
        overall, code = "unhealthy", 503
    elif mongo_status["status"] != "connected":
        overall, code = "degraded", 200
    else:
        overall, code = "healthy", 200
    return JsonResponse(
        {
            "status": overall,
            "application": "Inventory Management System",
            "database": sql["status"],
            "mongodb": mongo_status["status"],
            "services": {"sql": sql, "mongodb": mongo_status},
            "timestamp": timezone.now().isoformat(),
        },
        status=code,
    )


@admin_required
def trigger_server_error(request):
    """Admin-only route that raises a real exception to verify the 500 page."""
    if not settings.ENABLE_ERROR_TEST_ROUTE:
        raise Http404("Diagnostics route disabled.")
    raise RuntimeError("Intentional error raised from the diagnostics route.")


def _error(request, template, status, exception=None):
    return render(request, template, {"status_code": status}, status=status)


def bad_request(request, exception=None):
    return _error(request, "400.html", 400)


def permission_denied(request, exception=None):
    return _error(request, "403.html", 403)


def page_not_found(request, exception=None):
    return _error(request, "404.html", 404)


def server_error(request):
    """Render the custom 500 page; fall back to a minimal response if rendering fails."""
    try:
        return render(request, "500.html", {"status_code": 500}, status=500)
    except Exception:
        try:
            return HttpResponseServerError(loader.get_template("500.html").render({"status_code": 500}))
        except Exception:
            return HttpResponseServerError("<h1>500 – Internal Server Error</h1>")
