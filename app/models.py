from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from django.core.validators import MaxValueValidator

# Create your models here.

phone_regex = RegexValidator(
    regex=r'^07[8923]\d{7}$',
    message="Phone number must be entered in the format: '07XXXXXXXX'. Up to 10 digits allowed."
)

plate_regex = RegexValidator(
    regex=r'^[A-Z]{3} [0-9]{3} [A-Z]$',
    message="Plate number needd to be formated like AAA 000 A"
)

PARKING_TYPE = [
    ('ON STREET', 'on-street'),
    ('OFF STREET', 'off-street'),
    ('VALET', 'valet'),
    ('GARAGE', 'garage'),
]
RESTRICTION_CHOICES = [
        ('PERMIT REQUIRED', 'Permit Required'),
        ('SIZE RESTRICTION', 'Size Restriction'),
        ('NO RESTRICTION', 'None'),
    ]

SPACE_TYPE_CHOICES = [
        ('REGULAR', 'Regular'),
        ('HANDICAPPED', 'Handicapped'),
        ('ELECTRIC', 'Electric Vehicle Charging'),
    ]

PAYMENT_STATUS = [
    ('paid', 'Paid'),
    ('unpaid', 'Unpaid'),
    ('pending', 'Pending')
    ]

class User(AbstractUser):
    class Role(models.TextChoices):
        MCOLLECTOR = "ATTENDANTS", "Attendants"
        ADMIN = "ADMIN", "Admin"
    
    # base_role = Role.ADMIN

    role = models.CharField(max_length=50, choices=Role.choices)
    phone_number = models.CharField(validators=[phone_regex], max_length=10, unique=True, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='users',
        blank=True,
        help_text='The groups this user belongs to.'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='users',
        blank=True,
        help_text='Specific permissions for this user.'
    )
    def __str__(self):
        return f"{self.username} - {self.role}"

class Subscription(models.Model):
    name = models.CharField(max_length=255, unique=True)
    price = models.IntegerField()
    discount_rate = models.PositiveIntegerField(validators=[MaxValueValidator(100)])
    terms = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.name} - {self.price} RWF"

class ParkingLot(models.Model):
    name = models.CharField(max_length=255, unique=True)
    gpsLocation = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=PARKING_TYPE, default='ON STREET')
    capacity = models.IntegerField()
    restrictions = models.CharField(max_length=50, choices=RESTRICTION_CHOICES, default='NO RESTRICTION')
    security = models.BooleanField(default=False)
    lighting = models.BooleanField(default=False)
    chargingStation = models.BooleanField(default=False)
    manager_1 = models.ForeignKey('User', related_name='primary_manager', null=True, on_delete=models.SET_NULL)
    manager_2 = models.ForeignKey('User', related_name='secondary_manager', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.address} - {self.manager_1}"

class ParkingSpace(models.Model):
    parking_lot = models.ForeignKey('ParkingLot', on_delete=models.CASCADE, related_name='parking_spaces')
    subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True)
    space_code = models.CharField(max_length=6, unique=True)
    type = models.CharField(max_length=20, choices=SPACE_TYPE_CHOICES, default='REGULAR')
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Ticket(models.Model):
    parking = models.ForeignKey('ParkingLot', on_delete=models.DO_NOTHING)
    subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True)
    parking_space = models.ForeignKey('ParkingSpace', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    plate = models.CharField(validators=[plate_regex], max_length=9)
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField()
    total_payment = models.IntegerField
    payment_status = models.CharField(max_length=50, choices= PAYMENT_STATUS, default='unpaid')
    parking_attendee = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
