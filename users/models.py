import random
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField('email address', unique=True)
    is_driver = models.BooleanField(default=False)  # New field to differentiate between normal user and driver

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

@receiver(pre_delete, sender=CustomUser)
def log_user_delete_attempt(sender, instance, **kwargs):
    print(f"Attempting to delete user: {instance.email}")

@receiver(post_delete, sender=CustomUser)
def log_user_deleted(sender, instance, **kwargs):
    print(f"User deleted: {instance.email}")

class Driver(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='driver')
    license_no = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    dob = models.DateField()
    address = models.TextField(blank=True, null=True)
    average_rating = models.FloatField(default=0.0)  # Add average_rating here
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

# Signal to update is_driver field when a Driver profile is created
@receiver(post_save, sender=Driver)
def update_user_is_driver(sender, instance, created, **kwargs):
    if created:
        instance.user.is_driver = True
        instance.user.save()

# Signal to update is_driver field when a Driver profile is deleted
@receiver(pre_delete, sender=Driver)
def update_user_is_driver_on_delete(sender, instance, **kwargs):
    instance.user.is_driver = False
    instance.user.save()

class Appointment(models.Model):
    APPOINTMENT_TYPES = (
        ('maintenance', 'Vehicle Maintenance'),
        ('training', 'Safety Training'),
        ('review', 'Performance Review'),
        ('other', 'Other'),
        ('upgrade', 'Upgrade to Driver'),  # New appointment type for upgrading to driver
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='appointments')
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPES)
    appointment_date = models.DateField()
    time_slot = models.CharField(max_length=10)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['appointment_date', 'time_slot']
    
    def __str__(self):
        return f"{self.get_appointment_type_display()} - {self.appointment_date} {self.time_slot}"

    def is_for_driver(self):
        return self.appointment_type == 'upgrade'

User = get_user_model()

class Ride(models.Model):
    RIDE_STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('assigned', 'Driver Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    )

    special_requirements = models.TextField(blank=True, null=True)
    passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passenger_rides')
    driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_rides')
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    code = models.CharField(max_length=6, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=RIDE_STATUS_CHOICES, default='requested')
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_code(self):
        """Generate a random 6-digit code."""
        return ''.join(random.choices('0123456789', k=6))

    def __str__(self):
        return f"Ride from {self.pickup_location} to {self.dropoff_location}"
    
    @property
    def review(self):
        try:
            return self.review
        except RideReview.DoesNotExist:
            return None

    def assign_random_driver(self):
        active_ride_drivers = Ride.objects.filter(
            Q(status__in=['assigned', 'in_progress']) & 
            Q(driver__isnull=False)
        ).values_list('driver_id', flat=True)

        available_drivers = Driver.objects.exclude(id__in=active_ride_drivers)

        if available_drivers.exists():
            selected_driver = random.choice(available_drivers)
            self.driver = selected_driver
            self.status = 'assigned'
            self.save()
            return selected_driver
        return None

    def update_driver_rating(self):
        """
        Update the driver's average rating based on user reviews and drowsiness scores.
        """
        if self.driver and self.status == 'completed':
            # Calculate average user rating
            user_ratings = RideReview.objects.filter(ride__driver=self.driver).values_list('passenger_rating', flat=True)
            avg_user_rating = sum(user_ratings) / len(user_ratings) if user_ratings else 0

            # Calculate average drowsiness score
            drowsiness_scores = DriverBehavior.objects.filter(driver=self.driver).values_list('drowsiness_score', flat=True)
            avg_drowsiness_score = sum(drowsiness_scores) / len(drowsiness_scores) if drowsiness_scores else 0

            # Combine ratings (e.g., 70% user rating, 30% drowsiness score)
            self.driver.average_rating = (avg_user_rating * 0.7) + (avg_drowsiness_score * 0.3)
            self.driver.save()  # Save the updated average_rating in the Driver model

class RideReview(models.Model):
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='review')
    driver_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=False)  # Ensure not nullable
    passenger_comment = models.TextField(blank=True, null=True)  # Passenger's comment
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for Ride {self.ride_id}"

# Helper method to book a ride
def book_ride(passenger, pickup_location, dropoff_location, pickup_time):
    """
    Helper function to book a ride and automatically assign a driver
    """
    ride = Ride.objects.create(
        passenger=passenger,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        pickup_time=pickup_time
    )
    
    # Attempt to assign a random driver
    ride.assign_random_driver()
    
    return ride

class DriverBehavior(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='behaviors')  # Link to Driver
    blink_rate = models.FloatField()
    yawn_frequency = models.FloatField()
    head_pose = models.CharField(max_length=50)
    drowsiness_score = models.FloatField()
    alert_level = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Behavior for {self.driver.full_name} at {self.timestamp}"