from django.urls import path
from .views import UserLogin, UserRegister, Success


urlpatterns = [  
    path('login/', UserLogin.as_view(), name='user_login'),
    path('register/', UserRegister.as_view(), name='user_register'),
    path('success/', Success.as_view(), name='register_success'),
]

