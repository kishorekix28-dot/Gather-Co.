from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("faqs/", views.FAQList.as_view(), name="faq_list"),
    path("faqs/search/", views.faq_search, name="faq_search"),
    path("faqs/<int:pk>/", views.FAQDetail.as_view(), name="faq_detail"),
    path("errors/", views.ErrorList.as_view(), name="error_list"),
    path("errors/search/", views.error_search, name="error_search"),
    path("errors/<int:code>/", views.ErrorDetail.as_view(), name="error_detail"),
    path("products/", views.ProductList.as_view(), name="product_list"),
    path("products/<int:pk>/", views.ProductDetail.as_view(), name="product_detail"),
    path("inventory/summary/", views.inventory_summary, name="inventory_summary"),
    path("tickets/", views.TicketList.as_view(), name="ticket_list"),
]
