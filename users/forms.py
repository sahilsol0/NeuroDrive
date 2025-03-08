from django import forms
from django.utils import timezone
from .models import Driver, Ride, RideReview

class DriverUpdateForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['license_no', 'full_name', 'dob', 'address']

class RideBookingForm(forms.ModelForm):
    class Meta:
        model = Ride
        fields = ['pickup_location', 'dropoff_location']

class RideReviewForm(forms.ModelForm):
    class Meta:
        model = RideReview
        fields = ['driver_rating', 'passenger_comment']
        widgets = {
            'driver_rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'passenger_comment': forms.Textarea(attrs={'rows': 3}),
        }