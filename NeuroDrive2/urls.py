from django.contrib import admin
from django.urls import include, path

from .views import DriverDeleteView, DriverListView, DriverUpdateView, LandingView, appointments, book_appointment, book_ride_view, cancel_ride_view, confirm_driver_registration, estimate_fare_view, home, leaderboard, my_rides_view, ratings, register_driver, ride_details_view, search_drivers, search_users, success_driver_registration, verify_driver_registration

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingView.as_view(), name='landing'),
    path('home/', home, name='home'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('ratings/', ratings, name='ratings'),
    path('appointments/', appointments, name='appointments'),
    path('book-appointment/', book_appointment, name='book_appointment'),
    path('drivers/', DriverListView.as_view(), name='driver_list'),
    path('driver/<int:pk>/update/', DriverUpdateView.as_view(), name='driver_update'),
    path('driver/<int:pk>/delete/', DriverDeleteView.as_view(), name='driver_delete'),
    path('register-driver/', register_driver, name='register_driver'),
    path('verify-driver/', verify_driver_registration, name='verify_driver_registration'),
    path('confirm-driver/', confirm_driver_registration, name='confirm_driver_registration'),
    path('success-driver/', success_driver_registration, name='success_driver_registration'),
    path('search-drivers/', search_drivers, name='search_drivers'),
    path('search-users/', search_users, name='search_users'),
    path('book-ride/', book_ride_view, name='book_ride'),
    path('rides/', my_rides_view, name='my_rides'),
    path('ride/<int:ride_id>/', ride_details_view, name='ride_details'),
    path('ride/<int:ride_id>/cancel/', cancel_ride_view, name='cancel_ride'),
    path('estimate-fare/', estimate_fare_view, name='estimate_fare'),
    path('accounts/', include('allauth.urls')),
]
