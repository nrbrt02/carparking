from django.contrib import admin
from app.models import  User, ParkingLot, Ticket
# Register your models here.

admin.site.register(User)
admin.site.register(ParkingLot)
admin.site.register(Ticket)
