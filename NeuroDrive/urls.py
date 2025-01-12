from django.contrib import admin
from django.urls import path, include
from .views import LandingView

urlpatterns = [
    path('', LandingView.as_view(), name='landing'),
    path('auth/', include('authentication.urls')),
    path('admin/', admin.site.urls),
]