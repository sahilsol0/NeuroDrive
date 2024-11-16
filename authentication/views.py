from django.shortcuts import redirect, render
from django.contrib.auth import login, authenticate, logout
from . forms import CustomUserCreationForm, CustomAutheticationForm

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('register_success')
    else:
        form = CustomUserCreationForm
    return render(request, 'register.html', {'form':form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAutheticationForm(request, request.POST)
        print(form.errors)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
        else:
            print('not valid')
        print(form.non_field_errors)
    else:
        form = CustomAutheticationForm
    return render(request, 'login.html', {'form': form})
    
def logout_view(request):
    logout(request)
    return redirect('user_register')
    
def register_success_view(request):
    return render(request, 'register_success.html')