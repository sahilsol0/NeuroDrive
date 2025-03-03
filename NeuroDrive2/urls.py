from django.contrib import admin
from django.urls import include, path

from .views import LandingView, appointments, book_appointment, confirm_driver_registration, home, leaderboard, ratings, register_driver, search_users, success_driver_registration, verify_driver_registration

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingView.as_view(), name='landing'),
    path('home/', home, name='home'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('ratings/', ratings, name='ratings'),
    path('appointments/', appointments, name='appointments'),
    path('book-appointment/', book_appointment, name='book_appointment'),
    path('register-driver/', register_driver, name='register_driver'),
    path('verify-driver/', verify_driver_registration, name='verify_driver_registration'),
    path('confirm-driver/', confirm_driver_registration, name='confirm_driver_registration'),
    path('success-driver/', success_driver_registration, name='success_driver_registration'),
    path('search-users/', search_users, name='search_users'),
    path('accounts/', include('allauth.urls')),
]
