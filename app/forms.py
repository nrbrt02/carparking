from django import forms
from .models import ParkingLot, User, Subscription, ParkingSpace, Ticket, Subscribed
import re 


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'inputEmail'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'inputPassword'})
    )


class ParkingLotForm(forms.ModelForm):
    class Meta:
        model = ParkingLot
        fields = [
            'name', 'gpsLocation', 'address', 'type', 'capacity',
            'restrictions', 'security', 'lighting', 'chargingStation',
            'manager_1', 'manager_2'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter parking lot name'}),
            'gpsLocation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter GPS location'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter address'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter capacity'}),
            'restrictions': forms.SelectMultiple(
                attrs={'class': 'form-select', 'aria-label': 'Multiple select example'}
            ),
            'security': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lighting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'chargingStation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'manager_1': forms.Select(attrs={'class': 'form-select'}),
            'manager_2': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super(ParkingLotForm, self).__init__(*args, **kwargs)
        # Set the available restrictions
        self.fields['restrictions'].choices = [
            ('NO RESTRICTION', 'No Restriction'),
            ('HEIGHT LIMIT', 'Height Limit'),
            ('WEIGHT LIMIT', 'Weight Limit'),
            ('HANDICAPPED ONLY', 'Handicapped Only'),
        ]
        
        # Set the initial selected restrictions for update
        instance = kwargs.get('instance')
        if instance and instance.restrictions:
            self.initial['restrictions'] = instance.restrictions.split(',')

        # Filter managers for manager_1 and manager_2 fields
        attendants = User.objects.filter(role='ATTENDANTS')
        if instance:
            current_managers = [instance.manager_1, instance.manager_2]
            attendants = attendants | User.objects.filter(id__in=[m.id for m in current_managers if m])
        assigned_managers = ParkingLot.objects.exclude(id=instance.id if instance else None).values_list('manager_1', 'manager_2')
        assigned_managers = [manager for sublist in assigned_managers for manager in sublist if manager]
        self.fields['manager_1'].queryset = attendants.exclude(id__in=assigned_managers)
        self.fields['manager_2'].queryset = attendants.exclude(id__in=assigned_managers)

class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['name', 'price', 'discount_rate', 'terms']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter subscription name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price in RWF'}),
            'discount_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter discount rate (%)'}),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter subscription terms'}),
        }
        labels = {
            'name': 'Subscription Name',
            'price': 'Price (RWF)',
            'discount_rate': 'Discount Rate (%)',
            'terms': 'Terms and Conditions',
        }

class ParkingSpaceForm(forms.ModelForm):
    class Meta:
        model = ParkingSpace
        fields = ['parking_lot', 'subscription', 'type', 'status']  # Removed space_code
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super(ParkingSpaceForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class') != 'form-check-input':
                field.widget.attrs['class'] = 'form-control'


class ParkingSpaceFormUpdate(forms.ModelForm):
    class Meta:
        model = ParkingSpace
        fields = ['parking_lot', 'subscription', 'space_code', 'type', 'status']
        widgets = {
            'parking_lot': forms.Select(attrs={'class': 'form-select'}),
            'subscription': forms.Select(attrs={'class': 'form-select'}),
            'space_code': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['parking_space', 'name', 'plate']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter parking spaces to only show unoccupied ones
        self.fields['parking_space'].queryset = ParkingSpace.objects.filter(status=False)


class SubscribedForm(forms.ModelForm):
    class Meta:
        model = Subscribed
        fields = ['parking_space', 'plate', 'start_date', 'end_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_date'].required = False
        self.fields['end_date'].required = False
        
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError("End date must be after the start date.")
        
        return cleaned_data
    