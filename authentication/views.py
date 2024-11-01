from django.shortcuts import render
from django.contrib.auth.models import User, auth
from django.views import View

class login(View):
    def get(self, request):
        return render(request, 'login.html',context={})