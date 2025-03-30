import json
import logging
import os
import re
from datetime import datetime, timedelta
import time
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpResponseNotFound, JsonResponse, StreamingHttpResponse
from django.db.models import Count, Avg, Q, Max, Sum, F
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views import View
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from NeuroDrive2 import settings
from users.forms import DriverUpdateForm, RideBookingForm, RideReviewForm
from users.models import Appointment, CustomUser, Driver, DriverBehavior, DriverBehaviorRating, DrowsinessAlert, Ride, RideReview
from django.views.generic import ListView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models.functions import TruncDay

# Check if the user is an admin
def is_admin(user):
    return user.is_superuser

class LandingView(View):
    def get(self, request):
        return render(request, "landing.html", context={})
    
def format_timedelta(duration):
    """Format a timedelta object into a user-friendly string."""
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"
    elif minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return f"{seconds} second{'s' if seconds > 1 else ''}"
    
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # User metrics
    total_users = CustomUser.objects.count()
    total_drivers = Driver.objects.count()
    
    # Calculate user growth (last 30 days vs previous 30 days)
    today = timezone.now().date()
    last_30_start = today - timedelta(days=30)
    prev_30_start = last_30_start - timedelta(days=30)
    
    current_users = CustomUser.objects.filter(date_joined__gte=last_30_start).count()
    prev_users = CustomUser.objects.filter(date_joined__gte=prev_30_start, date_joined__lt=last_30_start).count()
    user_growth = round(((current_users - prev_users) / prev_users * 100) if prev_users > 0 else 100, 1)
    
    # Driver growth
    current_drivers = Driver.objects.filter(created_at__gte=last_30_start).count()
    prev_drivers = Driver.objects.filter(created_at__gte=prev_30_start, created_at__lt=last_30_start).count()
    driver_growth = round(((current_drivers - prev_drivers) / prev_drivers * 100) if prev_drivers > 0 else 100, 1)
    
    # Ride metrics
    pending_approvals_count = Appointment.objects.filter(status='pending').count()
    active_rides = Ride.objects.filter(status__in=['assigned', 'in_progress']).count()
    
    # Calculate pending change
    current_pending = pending_approvals_count
    prev_pending = Appointment.objects.filter(
        created_at__gte=prev_30_start, 
        created_at__lt=last_30_start,
        status='pending'
    ).count()
    pending_change = round(((current_pending - prev_pending) / prev_pending * 100) if prev_pending > 0 else 0, 1)
    
    # Ride growth
    current_rides = Ride.objects.filter(created_at__gte=last_30_start).count()
    prev_rides = Ride.objects.filter(created_at__gte=prev_30_start, created_at__lt=last_30_start).count()
    ride_growth = round(((current_rides - prev_rides) / prev_rides * 100) if prev_rides > 0 else 100, 1)
    
    # User growth chart data (last 30 days)
    user_growth_data = (
        CustomUser.objects
        .filter(date_joined__gte=last_30_start)
        .annotate(day=TruncDay('date_joined'))
        .values('day')
        .annotate(count=Count('id')))
    
    user_growth_labels = []
    user_growth_counts = []
    
    for day in (today - timedelta(days=n) for n in range(29, -1, -1)):
        entry = next((item for item in user_growth_data if item['day'] == day), None)
        user_growth_labels.append(day.strftime('%b %d'))
        user_growth_counts.append(entry['count'] if entry else 0)
    
    # Ride status distribution
    ride_status_data = []
    ride_status_labels = []
    
    for status, label in Ride.RIDE_STATUS_CHOICES:
        count = Ride.objects.filter(status=status).count()
        ride_status_data.append(count)
        ride_status_labels.append(label)
    
    # Top performing drivers
    top_drivers = (
        Driver.objects
        .annotate(
            total_rides=Count('driver_rides'),
            completed_rides=Count('driver_rides', filter=Q(driver_rides__status='completed')),
            high_alerts=Count('drowsiness_alerts', filter=Q(drowsiness_alerts__alert_level='HIGH')),
            medium_alerts=Count('drowsiness_alerts', filter=Q(drowsiness_alerts__alert_level='MEDIUM')),
            low_alerts=Count('drowsiness_alerts', filter=Q(drowsiness_alerts__alert_level='LOW')),
            avg_behavior_rating=Avg('driver_rides__driver_behavior_rating__rating')
        )
        .order_by('-average_rating')[:10]
    )
    
    # Recent alerts
    recent_alerts = DrowsinessAlert.objects.select_related('driver', 'ride').order_by('-timestamp')[:10]
    
    # Add recent appointments for the approvals section
    recent_appointments = (
        Appointment.objects
        .select_related('user')
        .order_by('-created_at')[:5]
    )

    context = {
        'total_users': total_users,
        'total_drivers': total_drivers,
        'pending_approvals_count': pending_approvals_count,
        'active_rides': active_rides,
        'user_growth': user_growth,
        'driver_growth': driver_growth,
        'pending_change': pending_change,
        'ride_growth': ride_growth,
        'user_growth_labels': json.dumps(user_growth_labels),
        'user_growth_data': json.dumps(user_growth_counts),
        'ride_status_labels': json.dumps(ride_status_labels),
        'ride_status_data': json.dumps(ride_status_data),
        'top_drivers': top_drivers,
        'recent_alerts': recent_alerts,
    }

    context.update({
        'recent_appointments': recent_appointments,
    })
    
    return render(request, 'dashboard/admin_dashboard.html', context)

def home(request):
    context = {}
    if request.user.is_superuser:
        context.update({
            'total_users': CustomUser.objects.count(),
            'total_drivers': Driver.objects.count(),
            'pending_approvals_count': Appointment.objects.filter(status='pending').count(),
        })
    elif request.user.is_driver:
        driver = request.user.driver
        context.update({
            'completed_rides': Ride.objects.filter(driver=driver, status='completed').count(),
            # 'earnings': driver.earnings,  # Assuming earnings is a field in the Driver model
            'average_rating': driver.average_rating,
        })
    else:
        context.update({
            'total_rides': Ride.objects.filter(passenger=request.user).count(),
            'active_bookings': Ride.objects.filter(passenger=request.user, status__in=['assigned', 'in_progress']).count(),
            # 'favorite_driver': request.user.favorite_driver,  # Assuming favorite_driver is a field in the User model
        })
    return render(request, 'dashboard/home.html', context)

def leaderboard(request):
    # Fetch drivers with their ratings, number of rides, active rate, and behavior ratings
    drivers = Driver.objects.annotate(
        total_rides_count=Count('driver_rides', filter=Q(driver_rides__status='completed')),  # Renamed to total_rides_count
        avg_rating=Avg('driver_rides__review__driver_rating'),
        avg_behavior_rating=Avg('driver_rides__driver_behavior_rating__rating'),  # Traverse Ride → DriverBehaviorRating
        last_ride_date=Max('driver_rides__created_at', filter=Q(driver_rides__status='completed')),  # Renamed to last_ride_date
    ).annotate(
        combined_score=(F('avg_rating') * 0.7 + F('avg_behavior_rating') * 0.3)  # Combined score (equal weight)
    ).order_by('-combined_score', '-avg_behavior_rating')  # Sort by combined score, then by behavior rating

    # Calculate active rate for each driver
    for driver in drivers:
        total_assigned_rides = driver.driver_rides.filter(status__in=['assigned', 'in_progress', 'completed']).count()
        total_completed_rides = driver.driver_rides.filter(status='completed').count()
        driver.active_rate = (total_completed_rides / total_assigned_rides * 100) if total_assigned_rides > 0 else 0

    # Calculate the overall average rating and behavior rating for all drivers
    overall_avg_rating = Driver.objects.aggregate(
        overall_avg_rating=Avg('driver_rides__review__driver_rating')
    )['overall_avg_rating'] or 0

    overall_behavior_rating = DriverBehaviorRating.objects.aggregate(
        overall_behavior_rating=Avg('rating')
    )['overall_behavior_rating'] or 0

    context = {
        'drivers': drivers,
        'active_drivers_count': drivers.filter(user__is_active=True).count(),
        'average_rating': overall_avg_rating,  # Use the calculated overall average rating
        'average_behavior_rating': overall_behavior_rating,  # Use the calculated overall behavior rating
    }
    return render(request, 'dashboard/leaderboard.html', context)

@login_required
def appointments(request):
    appointments = Appointment.objects.all()

    if request.user.is_superuser:
        # Apply search filters for managers
        search_email = request.GET.get('search_email')
        search_type = request.GET.get('search_type')
        search_date = request.GET.get('search_date')
        search_status = request.GET.get('search_status')

        if search_email:
            appointments = appointments.filter(user__email__icontains=search_email)
        if search_type:
            appointments = appointments.filter(appointment_type=search_type)
        if search_date:
            appointments = appointments.filter(appointment_date=search_date)
        if search_status:
            appointments = appointments.filter(status=search_status)

        # Pending approvals for managers
        pending_approvals = appointments.filter(status='pending')
    else:
        # Drivers see their own appointments
        appointments = appointments.filter(user=request.user)
        pending_approvals = Appointment.objects.none()

    # Count upcoming and pending appointments
    upcoming_appointments_count = appointments.filter(status='confirmed').count()
    pending_appointments_count = pending_approvals.count()

    # Get the last appointment date
    last_appointment = appointments.order_by('-appointment_date').first()
    last_appointment_date = last_appointment.appointment_date if last_appointment else "No appointments yet"

    context = {
        'appointments': appointments,
        'pending_approvals': pending_approvals,
        'upcoming_appointments_count': upcoming_appointments_count,
        'pending_appointments_count': pending_appointments_count,
        'last_appointment_date': last_appointment_date,
        'APPOINTMENT_TYPES': Appointment.APPOINTMENT_TYPES,  # Pass appointment types
        'STATUS_CHOICES': Appointment.STATUS_CHOICES,        # Pass status choices
    }
    return render(request, 'dashboard/appointments.html', context)

@login_required
def book_appointment(request):
    # Allow passengers to book an appointment only if the type is "upgrade"
    if not request.user.is_driver and request.method == 'POST':
        appointment_type = request.POST.get('appointment_type')
        if appointment_type != 'upgrade':
            raise PermissionDenied("You do not have permission to book this type of appointment.")
    elif not request.user.is_driver:
        raise PermissionDenied("You do not have permission to book an appointment.")

    if request.method == 'POST':
        appointment_type = request.POST.get('appointment_type')
        appointment_date = request.POST.get('appointment_date')
        time_slot = request.POST.get('time_slot')
        notes = request.POST.get('notes')
        
        # Save to database
        Appointment.objects.create(
            user=request.user,
            appointment_type=appointment_type,
            appointment_date=appointment_date,
            time_slot=time_slot,
            notes=notes,
            status='pending'  # Set status to pending by default
        )
        
        messages.success(request, 'Appointment requested successfully! Awaiting manager approval.')
        return redirect('appointments')
    
    return render(request, 'dashboard/book_appointment.html')

@login_required
@user_passes_test(is_admin)  # Ensure only managers can access this view
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    context = {
        'appointment': appointment,
        'is_upgrade': appointment.appointment_type == 'upgrade',  # Check if appointment type is "upgrade"
        'user_email': appointment.user.email if appointment.appointment_type == 'upgrade' else None,  # Pass user email
    }
    return render(request, 'dashboard/appointment_detail.html', context)

@login_required
@user_passes_test(is_admin)
def approve_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = 'confirmed'
    appointment.save()
    messages.success(request, 'Appointment approved successfully.')
    return redirect('appointments')

@login_required
@user_passes_test(is_admin)
def reject_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = 'cancelled'
    appointment.save()
    messages.success(request, 'Appointment rejected successfully.')
    return redirect('appointments')

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

def load_kerala_locations():
    """Load location data directly from JSON file"""
    # Define the path to the JSON file
    json_file = os.path.join(settings.BASE_DIR, 'data', 'kerala_locations.json')
    
    try:
        with open(json_file, 'r') as file:
            locations_data = json.load(file)
            return locations_data.get('popular_locations', [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Return empty list if file not found or invalid JSON
        print(f"Error loading locations: {e}")
        return []

@login_required
def request_ride(request):
    locations = load_kerala_locations()

    if request.method == 'POST':
        form = RideBookingForm(request.POST)
        if form.is_valid():
            ride = form.save(commit=False)
            ride.passenger = request.user

            # Generate a unique code for the ride
            ride.code = ride.generate_code()

            # Save the ride to the database
            ride.save()

            # Attempt to assign a random driver
            assigned_driver = ride.assign_random_driver()

            if assigned_driver:
                messages.success(request, f"Ride requested! Your code is: {ride.code}. Driver {assigned_driver.full_name} has been assigned.")
            else:
                messages.warning(request, f"Ride requested! Your code is: {ride.code}. No available drivers at the moment. Please wait for a driver to become available.")

            return redirect('ride_status', ride_id=ride.id)
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = RideBookingForm()
    return render(request, 'dashboard/rides/book_ride.html', {
        'form': form,
        'locations': locations,
    })

@login_required
def start_ride(request, ride_id):
    # Ensure the user is a driver
    if not request.user.is_driver:
        raise PermissionDenied("You do not have permission to start a ride.")

    # Get the Driver instance associated with the current user
    driver = request.user.driver

    # Filter the ride by the driver
    ride = get_object_or_404(Ride, id=ride_id, driver=driver)

    if request.method == 'POST':
        code = request.POST.get('code')
        if code == ride.code:
            # Start the ride
            ride.status = 'in_progress'
            ride.save()

            # Create a DriverBehaviorRating record for this ride
            DriverBehaviorRating.objects.update_or_create(
                ride=ride,
                defaults={'rating': 5.0}  # Default rating
            )

            messages.success(request, "Ride started!")
            return redirect('ride_status', ride_id=ride.id)
        else:
            messages.error(request, "Invalid code. Please try again.")

    return render(request, 'dashboard/rides/start_ride.html', {'ride': ride})

@login_required
def complete_ride(request, ride_id):
    # Ensure the user is a driver
    if not request.user.is_driver:
        raise PermissionDenied("You do not have permission to complete a ride.")

    # Get the Driver instance associated with the current user
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        raise PermissionDenied("Driver profile not found.")

    # Filter the ride by the driver and ensure it's in progress
    ride = get_object_or_404(Ride, id=ride_id, driver=driver, status='in_progress')

    if request.method == 'POST':
        # Update the ride status to 'completed'
        ride.status = 'completed'
        ride.save()

        # Calculate and save the driver's behavior rating
        ride.calculate_driver_behavior_rating()

        messages.success(request, "Ride completed successfully!")
        return redirect('ride_status', ride_id=ride.id)

    return render(request, 'dashboard/rides/complete_ride.html', {'ride': ride})

@login_required
def cancel_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, passenger=request.user)

    if request.method == 'POST':
        ride.status = 'cancelled'
        ride.save()
        messages.success(request, "Ride cancelled successfully.")
        return redirect('my_rides')

    return render(request, 'dashboard/rides/cancel_ride.html', {'ride': ride})

@login_required
def ride_status(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id)

    # Ensure the user is either the passenger or the driver
    if ride.passenger != request.user and (not request.user.is_driver or ride.driver != request.user.driver):
        messages.error(request, "You do not have permission to view this ride.")
        return redirect('home')

    # Fetch the review if it exists
    try:
        review = RideReview.objects.get(ride=ride)
    except RideReview.DoesNotExist:
        review = None

    # Calculate alert counts for the ride (both in_progress and completed)
    if ride.status in ['in_progress', 'completed']:
        high_alerts = DrowsinessAlert.objects.filter(ride=ride, alert_level='HIGH').count()
        medium_alerts = DrowsinessAlert.objects.filter(ride=ride, alert_level='MEDIUM').count()
        low_alerts = DrowsinessAlert.objects.filter(ride=ride, alert_level='LOW').count()
    else:
        high_alerts = medium_alerts = low_alerts = 0

    # Calculate and format ride duration if the ride is completed
    ride_duration = None
    if ride.status == 'completed':
        duration = ride.updated_at - ride.created_at
        ride_duration = format_timedelta(duration)

    return render(request, 'dashboard/rides/ride_status.html', {
        'ride': ride,
        'review': review,
        'driver_id': ride.driver.id if ride.driver else None,
        'high_alerts': high_alerts,  # Pass high alert count
        'medium_alerts': medium_alerts,  # Pass medium alert count
        'low_alerts': low_alerts,  # Pass low alert count
        'ride_duration': ride_duration,  # Pass ride duration
    })

@login_required
def my_rides_view(request):
    if request.user.is_driver:
        # If the user is a driver, show rides assigned to them
        rides = Ride.objects.filter(driver=request.user.driver).order_by('-created_at')
    else:
        # If the user is a passenger, show rides they booked
        rides = Ride.objects.filter(passenger=request.user).order_by('-created_at')
    
    return render(request, 'dashboard/rides/my_rides.html', {'rides': rides})

def estimate_fare_view(request):
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
            
            # Placeholder for distance factor (you can replace this with actual distance calculation)
            distance_factor = 1.0
            
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

@login_required
def submit_review(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id)

    # Ensure the user is the passenger
    if ride.passenger != request.user:
        messages.error(request, "You do not have permission to review this ride.")
        return redirect('home')

    # Check if a review already exists for this ride
    try:
        review = RideReview.objects.get(ride=ride)
    except RideReview.DoesNotExist:
        review = None

    if request.method == 'POST':
        form = RideReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.ride = ride
            review.save()
            messages.success(request, "Thank you for your feedback!")
            return redirect('ride_status', ride_id=ride.id)
    else:
        form = RideReviewForm(instance=review)

    return render(request, 'dashboard/rides/submit_review.html', {'form': form, 'ride': ride})

@csrf_exempt
def receive_drowsiness_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get the driver instance
            driver = Driver.objects.get(id=data['driver_id'])
            
            # Find active ride for this driver
            active_ride = Ride.objects.filter(
                driver=driver,
                status__in=['assigned', 'in_progress']
            ).first()
            
            # Create the alert
            alert = DrowsinessAlert.objects.create(
                ride=active_ride,  # Could be None if no active ride
                driver=driver,
                blink_rate=data['blink_rate'],
                yawn_frequency=data['yawn_frequency'],
                head_pose=data['head_pose'],
                min_ear=data['min_ear'],  # Using min_ear instead of drowsiness_score
                alert_level=data['alert_level']
            )
            
            return JsonResponse({'status': 'success', 'alert_id': alert.id})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

logger = logging.getLogger(__name__)

@csrf_exempt
def drowsiness_alert(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            driver_id = data.get('driver_id')
            blink_rate = data.get('blink_rate')
            yawn_frequency = data.get('yawn_frequency')
            head_pose = data.get('head_pose')
            drowsiness_score = data.get('drowsiness_score')
            alert_level = data.get('alert_level')

            # Validate driver_id
            try:
                driver = Driver.objects.get(id=driver_id)
            except Driver.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Driver not found'}, status=400)

            # Find the active ride for this driver
            active_ride = Ride.objects.filter(
                driver=driver,
                status__in=['assigned', 'in_progress'],
            ).first()

            if not active_ride:
                return JsonResponse({'status': 'error', 'message': 'No active ride found for this driver'}, status=400)

            # Create the drowsiness alert
            alert = DrowsinessAlert.objects.create(
                driver=driver,
                ride=active_ride,  # Link to the active ride
                blink_rate=blink_rate,
                yawn_frequency=yawn_frequency,
                head_pose=head_pose,
                drowsiness_score=drowsiness_score,
                alert_level=alert_level,
            )

            # Recalculate and update the driver's behavior rating
            active_ride.calculate_driver_behavior_rating()

            return JsonResponse({'status': 'success'}, status=200)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def sse_drowsiness_alerts(request, ride_id):
    # Verify the requesting user is the passenger of this specific ride
    try:
        ride = Ride.objects.get(id=ride_id)
        if ride.passenger != request.user:
            # If not the passenger, deny access
            return HttpResponseForbidden("You do not have permission to access alerts for this ride.")
    except Ride.DoesNotExist:
        return HttpResponseNotFound("Ride not found.")

    def event_stream():
        last_alert_id = None
        try:
            while True:
                # Check if ride is still active (refresh from DB)
                try:
                    current_ride_status = Ride.objects.get(pk=ride_id).status
                    if current_ride_status not in ['assigned', 'in_progress']:
                        break # Stop streaming if ride is completed/cancelled
                except Ride.DoesNotExist:
                     break # Stop if ride somehow got deleted

                # ... (Get new alerts logic) ...
                new_alerts_query = DrowsinessAlert.objects.filter(
                    ride_id=ride_id,
                    alert_level__in=['HIGH', 'MEDIUM']
                )
                if last_alert_id is not None:
                    new_alerts_query = new_alerts_query.filter(id__gt=last_alert_id)
                new_alerts = new_alerts_query.order_by('id')

                for alert in new_alerts:
                    yield f"data: {json.dumps({
                        'type': 'alert',
                        'alert_level': alert.alert_level,
                        'drowsiness_score': alert.drowsiness_score,
                        'timestamp': alert.timestamp.isoformat()
                    })}\n\n"
                    last_alert_id = alert.id

                # ... (Calculate and send counts logic) ...
                high_alerts = DrowsinessAlert.objects.filter(ride_id=ride_id, alert_level='HIGH').count()
                medium_alerts = DrowsinessAlert.objects.filter(ride_id=ride_id, alert_level='MEDIUM').count()
                low_alerts = DrowsinessAlert.objects.filter(ride_id=ride_id, alert_level='LOW').count()

                yield f"data: {json.dumps({
                    'type': 'counts',
                    'high': high_alerts,
                    'medium': medium_alerts,
                    'low': low_alerts
                })}\n\n"

                time.sleep(2) # Interval for sending counts

        except Exception as e:
            # Handle client disconnect or other errors gracefully
            print(f"SSE Error for ride {ride_id}: {str(e)}")
        # Ensure the loop terminates and the response finishes when done

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    return response