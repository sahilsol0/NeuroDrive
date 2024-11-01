from django.shortcuts import redirect, render
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.edit import CreateView
from . forms import CustomUserCreationForm

class UserLogin(View):
    def get(self, request):
        return render(request, 'login.html',context={})

class UserRegister(CreateView):
    template_name = 'register.html'
    success_url = '/user/success'
    form_class = CustomUserCreationForm
    
class UserLogout(View):
    def get(self, request):
        pass
    
class Success(View):
    def get(self, request):
        return render(request, 'register_success.html',context={})