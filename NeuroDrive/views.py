from django.shortcuts import render , redirect
from django.http import HttpResponse

from django.contrib import messages
from django.views import View

class home(View):
    def get(self, request):
        return render(request, "home.html", context={})
         