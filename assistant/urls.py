from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("chat/", views.chat, name="chat"),
    path("history/", views.history, name="history"),
    path("feedback/", views.feedback, name="feedback"),
    path("faq/", views.faq_page, name="faq"),
    path("knowledge-base/", views.knowledge_base, name="knowledge_base"),
    path("knowledge-base/faqs/new/", views.faq_form, name="faq_create"),
    path("knowledge-base/faqs/<int:pk>/edit/", views.faq_form, name="faq_update"),
    path("knowledge-base/errors/new/", views.error_form, name="error_create"),
    path("knowledge-base/errors/<int:pk>/edit/", views.error_form, name="error_update"),
    path("knowledge-base/<str:kind>/<int:pk>/delete/", views.kb_delete, name="kb_delete"),
]
