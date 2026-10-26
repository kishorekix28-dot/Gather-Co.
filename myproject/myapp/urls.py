from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('inventory/', views.home, name='inventory-list'),
    path('signup/', views.sign_up, name='signup'),
    path('register/', views.sign_up, name='register'),
    path('login/', views.sign_in, name='login'),
    path('logout/', views.sign_out, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('owner/dashboard/', views.owner_portal, name='owner-dashboard'),
    path('owner/inventory/', views.owner_portal, name='owner-inventory'),
    path('owner/bookings/', views.owner_portal, name='owner-bookings'),
    path('owner/calendar/', views.owner_calendar, name='owner-calendar'),
    path('my-bookings/', views.customer_bookings, name='my-bookings'),
    path('stock/add/', views.add_product, name='add-product'),
    path('stock/<int:product_id>/edit/', views.edit_product, name='edit-product'),
    path('stock/<int:product_id>/deactivate/', views.deactivate_product, name='deactivate-product'),
    path('products/<int:product_id>/book/', views.book_product, name='book-product'),
    path(
        'reservations/<int:booking_id>/action/',
        views.reservation_action,
        name='reservation-action',
    ),
    path(
        'reservations/<int:booking_id>/cancel/',
        views.cancel_booking,
        name='cancel-booking',
    ),
    path('reservations/<int:booking_id>/pay/', views.payment_checkout, name='payment-checkout'),
    path('reservations/<int:booking_id>/pay/demo/', views.mock_advance_payment, name='mock-payment'),
    path('reservations/<int:booking_id>/receipt/', views.receipt, name='receipt'),
]
