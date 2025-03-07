import random
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver

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
    
class Ride(models.Model):
    RIDE_STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('assigned', 'Driver Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    )

    RIDE_TYPE_CHOICES = (
        ('standard', 'Standard'),
        ('shared', 'Shared Ride'),
        ('premium', 'Premium')
    )
    
    ride_type = models.CharField(
        max_length=20, 
        choices=RIDE_TYPE_CHOICES, 
        default='standard'
    )
    special_requirements = models.TextField(
        blank=True, 
        null=True
    )

    passenger = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='passenger_rides')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_rides')
    
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    
    pickup_time = models.DateTimeField()
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=RIDE_STATUS_CHOICES, default='requested')
    
    fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ride from {self.pickup_location} to {self.dropoff_location}"

    def assign_random_driver(self):
        """
        Assign a random available driver to the ride.
        A driver is considered available if:
        1. They are not currently on an active ride
        2. They have an active driver profile
        """
        # Find drivers who are not currently on an active ride
        active_ride_drivers = Ride.objects.filter(
            Q(status__in=['assigned', 'in_progress']) & 
            Q(driver__isnull=False)
        ).values_list('driver_id', flat=True)

        # Get available drivers (those with driver profiles who are not on active rides)
        available_drivers = Driver.objects.exclude(id__in=active_ride_drivers)

        if available_drivers.exists():
            # Randomly select a driver
            selected_driver = random.choice(available_drivers)
            self.driver = selected_driver
            self.status = 'assigned'
            self.save()
            return selected_driver
        
        return None

class RideReview(models.Model):
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='review')
    passenger_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    driver_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    passenger_comment = models.TextField(blank=True, null=True)
    driver_comment = models.TextField(blank=True, null=True)
    
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