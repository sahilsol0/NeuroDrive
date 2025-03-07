import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views import View
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from users.forms import DriverUpdateForm, RideBookingForm
from users.models import Appointment, CustomUser, Driver, Ride
from django.views.generic import ListView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render
from django.db.models import Count, Avg

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
    # Fetch drivers with their ratings, number of rides, and active rate
    drivers = Driver.objects.annotate(
        total_rides=Count('driver_rides', filter=Q(driver_rides__status='completed')),
        avg_rating=Avg('driver_rides__review__driver_rating'),
    ).order_by('-avg_rating')  # Sort by average rating (highest first)

    # Add ranking to each driver
    for index, driver in enumerate(drivers, start=1):
        driver.rank = index

    context = {
        'drivers': drivers,
    }
    return render(request, 'dashboard/leaderboard.html', context)

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
    return render(request, 'dashboard/drivers/register_driver.html', {'users': users})

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

    return render(request, 'dashboard/drivers/verify_driver.html', {
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
    return render(request, 'dashboard/drivers/success_driver.html')


@login_required
@user_passes_test(is_admin)
def search_users(request):
    query = request.GET.get('query', '')
    exclude_drivers = request.GET.get('exclude_drivers', 'false').lower() == 'true'

    users = CustomUser.objects.filter(
        Q(email__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    )

    if exclude_drivers:
        users = users.filter(is_driver=False)

    user_list = [
        {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        for user in users
    ]

    return JsonResponse(user_list, safe=False)

def search_drivers(request):
    query = request.GET.get('query', '')

    # Filter drivers based on the search query
    drivers = Driver.objects.filter(
        Q(full_name__icontains=query) | 
        Q(license_no__icontains=query) | 
        Q(user__email__icontains=query)
    )

    driver_list = [
        {
            'id': driver.id,
            'full_name': driver.full_name,
            'license_no': driver.license_no,
            'dob': driver.dob.strftime('%Y-%m-%d'),  # Format date as string
            'address': driver.address,
        }
        for driver in drivers
    ]

    return JsonResponse(driver_list, safe=False)

class DriverListView(ListView):
    model = Driver
    template_name = 'dashboard/drivers/driver_list.html'
    context_object_name = 'drivers'

class DriverUpdateView(UpdateView):
    model = Driver
    form_class = DriverUpdateForm
    template_name = 'dashboard/drivers/driver_update.html'
    success_url = reverse_lazy('driver_list')

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        # Add the driver's email to the context
        context['driver_email'] = self.object.user.email
        return context

class DriverDeleteView(DeleteView):
    model = Driver
    template_name = 'dashboard/drivers/driver_confirm_delete.html'
    success_url = reverse_lazy('driver_list')

@login_required
def book_ride_view(request):
    """
    View to handle ride booking
    """
    if request.method == 'POST':
        form = RideBookingForm(request.POST)
        if form.is_valid():
            # Create ride instance
            ride = form.save(commit=False)
            ride.passenger = request.user
            
            # Combine date and time into a naive datetime object
            pickup_datetime = datetime.combine(
                form.cleaned_data['pickup_date'], 
                form.cleaned_data['pickup_time']
            )
            # Make the datetime object timezone-aware
            ride.pickup_time = timezone.make_aware(pickup_datetime)
            
            # Save the ride
            ride.save()
            
            # Attempt to assign a driver
            try:
                ride.assign_random_driver()
            except Exception as e:
                messages.warning(request, f"Could not assign a driver: {str(e)}")
            
            messages.success(request, "Ride booked successfully!")
            return redirect('my_rides')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = RideBookingForm()
    
    return render(request, 'dashboard/rides/book_ride.html', {
        'form': form,
        'recent_rides': Ride.objects.filter(passenger=request.user).order_by('-created_at')[:5]
    })

@login_required
def my_rides_view(request):
    """
    View to show user's ride history
    """
    rides = Ride.objects.filter(passenger=request.user).order_by('-created_at')
    return render(request, 'dashboard/rides/my_rides.html', {
        'rides': rides
    })

@login_required
def ride_details_view(request, ride_id):
    """
    View to show details of a specific ride
    """
    ride = get_object_or_404(Ride, id=ride_id, passenger=request.user)
    return render(request, 'dashboard/rides/ride_details.html', {
        'ride': ride
    })

@login_required
def cancel_ride_view(request, ride_id):
    """
    View to cancel a ride
    """
    ride = get_object_or_404(Ride, id=ride_id, passenger=request.user)
    
    # Only allow cancellation of pending or upcoming rides
    if ride.status in ['requested', 'assigned']:
        ride.status = 'cancelled'
        ride.save()
        messages.success(request, "Ride cancelled successfully.")
    else:
        messages.error(request, "This ride cannot be cancelled.")
    
    return redirect('my_rides')

def estimate_fare_view(request):
    """
    AJAX view to estimate ride fare
    """
    if request.method == 'POST':
        try:
            pickup_location = request.POST.get('pickup_location', '')
            dropoff_location = request.POST.get('dropoff_location', '')
            ride_type = request.POST.get('ride_type', 'standard')
            
            # Basic fare estimation logic
            base_fare = 5.00
            multipliers = {
                'standard': 1.0,
                'shared': 0.8,
                'premium': 1.5
            }
            
            # You would typically use a more sophisticated method 
            # like geocoding and distance calculation
            distance_factor = 1.0  # Placeholder
            
            estimated_fare = base_fare * multipliers.get(ride_type, 1.0) * distance_factor
            
            return JsonResponse({
                'success': True,
                'estimated_fare': round(estimated_fare, 2)
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })