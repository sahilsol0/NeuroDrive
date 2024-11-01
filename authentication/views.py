from django.shortcuts import render
from django.contrib.auth.models import User, auth
from django.views import View

class user_login(View):
    def get(self, request):
        return render(request, 'login.html',context={})
    
class user_register(View):
    def get(self, request):
        return render(request, 'register.html',context={})
    
class user_logout(View):
    def get(self, request):
        pass
    
class success(View):
    def get(self, request):
        return render(request, 'register_success.html',context={})