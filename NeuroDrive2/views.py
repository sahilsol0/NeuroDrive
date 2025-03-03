from datetime import datetime, timedelta
import re
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views import View
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from users.models import Appointment, CustomUser, Driver

# Check if the user is an admin
def is_admin(user):
    return user.is_superuser

class LandingView(View):
    def get(self, request):
        return render(request, "landing.html", context={})

@login_required()
def home(request):
    return render(request, "dashboard/home.html", context={})

@login_required()
def leaderboard(request):
    return render(request, "dashboard/leaderboard.html", context={})

@login_required()
def ratings(request):
    return render(request, "dashboard/ratings.html", context={})

@login_required
def appointments(request):
    return render(request, 'dashboard/appointments.html')

@login_required
def book_appointment(request):
    if not request.user.is_driver:
        raise PermissionDenied("You do not have permission to book an appointment.")

    if request.method == 'POST':
        appointment_type = request.POST.get('appointment_type')
        appointment_date = request.POST.get('appointment_date')
        time_slot = request.POST.get('time_slot')
        notes = request.POST.get('notes')
        
        # Save to database (you would create a model for this)
        Appointment.objects.create(
            user=request.user,
            appointment_type=appointment_type,
            appointment_date=appointment_date,
            time_slot=time_slot,
            notes=notes,
            status='pending'
        )
        
        messages.success(request, 'Appointment booked successfully!')
        return redirect('appointments')
    
    return render(request, 'dashboard/book_appointment.html')

@login_required
@user_passes_test(is_admin)
def register_driver(request):
    if request.method == 'POST':
        # Store form data in session for verification
        request.session['driver_data'] = {
            'user_id': request.POST.get('user'),
            'license_no': request.POST.get('license_no'),
            'full_name': request.POST.get('full_name'),
            'dob': request.POST.get('dob'),
            'address': request.POST.get('address'),
        }
        return redirect('verify_driver_registration')

    # Fetch all users who are not already drivers
    users = CustomUser.objects.filter(is_driver=False)
    return render(request, 'dashboard/register_driver.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def verify_driver_registration(request):
    driver_data = request.session.get('driver_data')
    if not driver_data:
        messages.error(request, 'No registration data found. Please fill out the form again.')
        return redirect('register_driver')

    try:
        user = CustomUser.objects.get(id=driver_data['user_id'])
    except CustomUser.DoesNotExist:
        messages.error(request, 'Selected user does not exist.')
        return redirect('register_driver')

    return render(request, 'dashboard/verify_driver.html', {
        'user': user,
        'driver_data': driver_data,
    })

@login_required
@user_passes_test(is_admin)
def confirm_driver_registration(request):
    driver_data = request.session.get('driver_data')
    print("Session Data:", driver_data['license_no'])
    if not driver_data:
        messages.error(request, 'No registration data found. Please fill out the form again.')
        return redirect('register_driver')

    try:
        user = CustomUser.objects.get(id=driver_data['user_id'])
        print(user.is_driver)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Selected user does not exist.')
        print('Selected user does not exist.')
        return redirect('register_driver')

    # Validate license number format
    license_regex = r'^[A-Za-z]{2}-\d{2}\d{4}\d{7}$'
    if not re.match(license_regex, driver_data['license_no']):
        messages.error(request, 'Invalid license number format. Please follow the format SS-RRYYYYNNNNNNN.')
        print('Invalid license number format. Please follow the format SS-RRYYYYNNNNNNN.')
        return redirect('register_driver')

    # Validate age (must be at least 18 years old)
    dob_date = datetime.strptime(driver_data['dob'], '%Y-%m-%d').date()  # Correct usage
    min_age_date = datetime.now().date() - timedelta(days=365 * 18)  # 18 years ago
    if dob_date > min_age_date:
        messages.error(request, 'You must be at least 18 years old to register as a driver.')
        return redirect('register_driver')

    # Create a new Driver profile
    try:
        Driver.objects.create(
            user=user,
            license_no=driver_data['license_no'],
            full_name=driver_data['full_name'],
            dob=driver_data['dob'],
            address=driver_data['address'],
        )
        print('success!!!!')
        return redirect('success_driver_registration')
    except Exception as e:
        print(f"Error: {e}")
        return redirect('register_driver')

@login_required
@user_passes_test(is_admin)
def success_driver_registration(request):
    return render(request, 'dashboard/success_driver.html')

@login_required
@user_passes_test(is_admin)
def search_users(request):
    query = request.GET.get('query', '')
    users = CustomUser.objects.filter(
        Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
    ).values('id', 'email', 'first_name', 'last_name')[:10]  # Limit to 10 results
    return JsonResponse(list(users), safe=False)