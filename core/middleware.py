"""Request logging middleware.

Logs timestamp, HTTP method, path (without the query string, which may hold
sensitive tokens), response status and processing time. Request bodies,
headers, cookies and credentials are never logged.
"""
import logging
import time

logger = logging.getLogger("inventory.requests")

SKIP_PREFIXES = ("/static/", "/favicon.ico")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        status = 500
        try:
            response = self.get_response(request)
            status = response.status_code
            return response
        finally:
            if not request.path.startswith(SKIP_PREFIXES):
                duration_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "method=%s path=%s status=%s duration_ms=%.2f",
                    request.method,
                    request.path,
                    status,
                    duration_ms,
                )
