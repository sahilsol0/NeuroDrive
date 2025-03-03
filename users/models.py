from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

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