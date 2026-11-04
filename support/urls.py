from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("new/", views.ticket_create, name="create"),
    path("<str:ticket_id>/", views.ticket_detail, name="detail"),
    path("<str:ticket_id>/edit/", views.ticket_update, name="update"),
    path("<str:ticket_id>/close/", views.ticket_close, name="close"),
    path("<str:ticket_id>/delete/", views.ticket_delete, name="delete"),
]
