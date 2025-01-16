from django.contrib import admin
from django.urls import include, path

from .views import LandingView, home, leaderboard, ratings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingView.as_view(), name='landing'),
    path('home/', home, name='home'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('ratings/', ratings, name='ratings'),
    path('accounts/', include('allauth.urls')),
]
