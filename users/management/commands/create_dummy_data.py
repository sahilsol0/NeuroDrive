# users/management/commands/create_dummy_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import random
import string
from users.models import Driver

# Get the CustomUser model
CustomUser = get_user_model()

rto_codes = [
    {"state": "Andhra Pradesh", "code": "AP"},
    {"state": "Arunachal Pradesh", "code": "AR"},
    {"state": "Assam", "code": "AS"},
    {"state": "Bihar", "code": "BR"},
    {"state": "Chhattisgarh", "code": "CG"},
    {"state": "Goa", "code": "GA"},
    {"state": "Gujarat", "code": "GJ"},
    {"state": "Haryana", "code": "HR"},
    {"state": "Himachal Pradesh", "code": "HP"},
    {"state": "Jharkhand", "code": "JH"},
    {"state": "Karnataka", "code": "KA"},
    {"state": "Kerala", "code": "KL"},
    {"state": "Madhya Pradesh", "code": "MP"},
    {"state": "Maharashtra", "code": "MH"},
    {"state": "Manipur", "code": "MN"},
    {"state": "Meghalaya", "code": "ML"},
    {"state": "Mizoram", "code": "MZ"},
    {"state": "Nagaland", "code": "NL"},
    {"state": "Odisha", "code": "OD"},
    {"state": "Punjab", "code": "PB"},
    {"state": "Rajasthan", "code": "RJ"},
    {"state": "Sikkim", "code": "SK"},
    {"state": "Tamil Nadu", "code": "TN"},
    {"state": "Telangana", "code": "TS"},
    {"state": "Tripura", "code": "TR"},
    {"state": "Uttar Pradesh", "code": "UP"},
    {"state": "Uttarakhand", "code": "UK"},
    {"state": "West Bengal", "code": "WB"},
    {"state": "Andaman and Nicobar Islands", "code": "AN"},
    {"state": "Chandigarh", "code": "CH"},
    # {"state": "Dadra and Nagar Haveli and Daman and Diu", "code": "DD/DN"},
    {"state": "Delhi", "code": "DL"},
    {"state": "Jammu and Kashmir", "code": "JK"},
    {"state": "Ladakh", "code": "LA"},
    {"state": "Lakshadweep", "code": "LD"},
    {"state": "Puducherry", "code": "PY"}
]

# Example of how to access the data:
#print(rto_codes[0]["state"])  # Output: Andhra Pradesh
#print(rto_codes[5]["code"])   # Output: GA

# Function to generate a random license number
def generate_license_number():
    # Format: SS-RRYYYYNNNNNNN
    random_state = random.choice(rto_codes)
    letters = random_state["code"]  # SS
    region = random.randint(10, 99)  # RR
    year = random.randint(2000, 2023)  # YYYY
    number = random.randint(1000000, 9999999)  # NNNNNNN
    return f"{letters}-{region}{year}{number}"

# Function to generate a random date of birth (at least 18 years old)
def generate_dob(min_age=18):
    today = datetime.today()
    min_date = today - timedelta(days=365 * min_age)
    random_days = random.randint(0, (today - min_date).days)
    return (min_date + timedelta(days=random_days)).date()

class Command(BaseCommand):
    help = 'Create dummy users and drivers for testing'

    def handle(self, *args, **kwargs):
        # Create dummy users
        users_data = [
            {"email": "user1@example.com", "password": "password123", "is_driver": False},
            {"email": "user2@example.com", "password": "password123", "is_driver": False},
            {"email": "user3@example.com", "password": "password123", "is_driver": False},
            {"email": "driver_candidate1@example.com", "password": "password123", "is_driver": True},
            {"email": "driver_candidate2@example.com", "password": "password123", "is_driver": True},
        ]

        for user_data in users_data:
            user = CustomUser.objects.create_user(
                email=user_data["email"],
                password=user_data["password"],
                is_driver=user_data["is_driver"]
            )
            self.stdout.write(self.style.SUCCESS(f"Created user: {user.email}"))

        # Create dummy drivers
        driver_candidates = CustomUser.objects.filter(is_driver=True)
        self.stdout.write(self.style.SUCCESS(f"Drivers: {driver_candidates}"))

        for user in driver_candidates:
            # Generate driver data
            license_no = generate_license_number()
            full_name = f"{user.email.split('@')[0].title()} Driver"
            dob = generate_dob(min_age=18)  # Ensure age is at least 18
            address = "123 Main St, Springfield"

            # Create driver profile
            Driver.objects.create(
                user=user,
                license_no=license_no,
                full_name=full_name,
                dob=dob,
                address=address,
            )
            self.stdout.write(self.style.SUCCESS(f"Created driver: {full_name} (License: {license_no}, DOB: {dob})"))