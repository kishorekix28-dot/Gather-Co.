from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from assistant.views import faq_page
from core import views as core_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("health/", core_views.health_check, name="health"),
    path("accounts/", include("accounts.urls")),
    path("suppliers/", include("suppliers.urls")),
    path("tickets/", include("support.urls")),
    path("faq/", faq_page, name="faq"),
    path("assistant/", include("assistant.urls")),
    path("api/", include("api.urls")),
    path("diagnostics/trigger-500/", core_views.trigger_server_error, name="trigger_500"),
    path("", include("inventory.urls")),
    # Uploaded product images (small deployments; use object storage at scale).
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

handler400 = "core.views.bad_request"
handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"
