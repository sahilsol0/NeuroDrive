from django.urls import path
from .views import register_view, login_view, logout_view, register_success_view


urlpatterns = [  
    path('register/', register_view, name='user_register'),
    path('login/', login_view, name='user_login'),
    path('logout/', logout_view, name='user_logout'),
    path('success/', register_success_view, name='register_success'),
]

