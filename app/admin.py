from django.contrib import admin
from app.models import  User, ParkingLot, Ticket, Subscribed
# Register your models here.

admin.site.register(User)
admin.site.register(ParkingLot)
admin.site.register(Ticket)
admin.site.register(Subscribed)
