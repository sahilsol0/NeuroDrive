from django.shortcuts import render, redirect
from django.views import View

# Create your views here.
class LoginView(View):
    def get(self, request):
        return render(request, 'login.html', context={})