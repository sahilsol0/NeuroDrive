from django.contrib import admin
from django.urls import include, path
from . import views
from NeuroDrive.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home.as_view(), name='home'),
    path('user/', include('authentication.urls')),
]
