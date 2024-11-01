from django.urls import path

from .views import success, user_login, user_register

urlpatterns = [  
    path('login/', user_login.as_view(), name='user_login'),
    path('register/', user_register.as_view(), name='user_register'),
    path('success/', success.as_view(), name='register_success'),
]

