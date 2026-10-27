import logging
import time


request_logger = logging.getLogger('myapp.requests')


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            request_logger.exception(
                'request method=%s path=%s status=500 duration_ms=%s',
                request.method,
                request.path,
                elapsed_ms,
            )
            raise

        elapsed_ms = round((time.perf_counter() - started) * 1000)
        request_logger.info(
            'request method=%s path=%s status=%s duration_ms=%s',
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response
