from django.urls import path

from . import views

app_name = "suppliers"

urlpatterns = [
    path("", views.supplier_list, name="list"),
    path("new/", views.supplier_form, name="create"),
    path("<int:pk>/", views.supplier_detail, name="detail"),
    path("<int:pk>/edit/", views.supplier_form, name="update"),
    path("<int:pk>/delete/", views.supplier_delete, name="delete"),
]
