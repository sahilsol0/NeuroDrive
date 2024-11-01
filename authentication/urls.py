from django.urls import path

from .views import login

urlpatterns = [  
    path('login/', login.as_view(), name='home'),
]

