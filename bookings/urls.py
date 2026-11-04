from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.customer_dashboard, name="customer_dashboard"),
    path("new/", views.booking_create, name="create"),
    path("mine/", views.my_bookings, name="mine"),
    path("manage/", views.manage, name="manage"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("<str:booking_id>/", views.booking_detail, name="detail"),
    path("<str:booking_id>/cancel/", views.booking_cancel, name="cancel"),
    path("<str:booking_id>/<str:action>/", views.review, name="review"),
]
