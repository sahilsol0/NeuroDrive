from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views import View

class LandingView(View):
    def get(self, request):
        return render(request, "landing.html", context= {})
    
@login_required()
def home(request):
    print(request)
    return render(request, "dashboard/home.html", context={})

@login_required()
def leaderboard(request):
    return render(request, "dashboard/leaderboard.html", context={})

@login_required()
def ratings(request):
    return render(request, "dashboard/ratings.html", context={})