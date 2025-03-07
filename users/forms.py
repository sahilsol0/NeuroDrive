from django import forms
from django.utils import timezone
from .models import Driver, Ride

class DriverUpdateForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['license_no', 'full_name', 'dob', 'address']

class RideBookingForm(forms.ModelForm):
    """
    Form for booking a ride
    """
    pickup_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date
    )
    pickup_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        initial=timezone.now().time
    )

    class Meta:
        model = Ride
        fields = [
            'pickup_location', 
            'dropoff_location', 
            'ride_type', 
            'special_requirements'
        ]
        widgets = {
            'pickup_location': forms.TextInput(attrs={
                'placeholder': 'Enter pickup address',
                'class': 'form-control'
            }),
            'dropoff_location': forms.TextInput(attrs={
                'placeholder': 'Enter destination address',
                'class': 'form-control'
            }),
            'special_requirements': forms.Textarea(attrs={
                'placeholder': 'Any special requests or notes',
                'rows': 3
            })
        }

    def clean(self):
        """
        Custom validation
        """
        cleaned_data = super().clean()
        pickup_date = cleaned_data.get('pickup_date')
        pickup_time = cleaned_data.get('pickup_time')

        # Ensure pickup is in the future
        if pickup_date and pickup_time:
            pickup_datetime = timezone.datetime.combine(pickup_date, pickup_time)
            pickup_datetime = timezone.make_aware(pickup_datetime)
            
            if pickup_datetime <= timezone.now():
                raise forms.ValidationError("Pickup time must be in the future.")

        return cleaned_data