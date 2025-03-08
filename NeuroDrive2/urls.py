from django.contrib import admin
from django.urls import include, path

from .views import DriverDeleteView, DriverListView, DriverUpdateView, LandingView, appointments, approve_appointment, book_appointment, cancel_ride, complete_ride, confirm_driver_registration, estimate_fare_view, home, leaderboard, my_rides_view, receive_drowsiness_data, register_driver, reject_appointment, request_ride, ride_status, search_drivers, search_users, start_ride, submit_review, success_driver_registration, verify_driver_registration

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingView.as_view(), name='landing'),
    path('home/', home, name='home'),
    path('leaderboard/', leaderboard, name='leaderboard'),

    path('appointments/', appointments, name='appointments'),
    path('book-appointment/', book_appointment, name='book_appointment'),
    path('approve-appointment/<int:appointment_id>/', approve_appointment, name='approve_appointment'),
    path('reject-appointment/<int:appointment_id>/', reject_appointment, name='reject_appointment'),

    path('drivers/', DriverListView.as_view(), name='driver_list'),
    path('driver/<int:pk>/update/', DriverUpdateView.as_view(), name='driver_update'),
    path('driver/<int:pk>/delete/', DriverDeleteView.as_view(), name='driver_delete'),
    path('register-driver/', register_driver, name='register_driver'),
    path('verify-driver/', verify_driver_registration, name='verify_driver_registration'),
    path('confirm-driver/', confirm_driver_registration, name='confirm_driver_registration'),
    path('success-driver/', success_driver_registration, name='success_driver_registration'),

    path('request-ride/', request_ride, name='request_ride'),
    path('start-ride/<int:ride_id>/', start_ride, name='start_ride'),
    path('ride-status/<int:ride_id>/', ride_status, name='ride_status'),
    path('cancel-ride/<int:ride_id>/', cancel_ride, name='cancel_ride'),
    path('complete-ride/<int:ride_id>/', complete_ride, name='complete_ride'),
    path('my-rides/', my_rides_view, name='my_rides'),

    path('submit-review/<int:ride_id>/', submit_review, name='submit_review'),
    path('search-drivers/', search_drivers, name='search_drivers'),
    path('search-users/', search_users, name='search_users'),
    path('estimate-fare/', estimate_fare_view, name='estimate_fare'),
    path('api/drowsiness-data/', receive_drowsiness_data, name='receive_drowsiness_data'),

    path('accounts/', include('allauth.urls')),
]
