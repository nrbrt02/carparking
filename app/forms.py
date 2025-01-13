from django import forms
from .models import ParkingLot, User


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

    def clean_restrictions(self):
        restrictions = self.cleaned_data.get('restrictions', [])
        # if not restrictions:
        #     return ''  
        return ','.join(restrictions)  # Properly join selected restrictions into a string

    def __init__(self, *args, **kwargs):
        super(ParkingLotForm, self).__init__(*args, **kwargs)
        # Filter managers based on the ATTENDANT role
        attendants = User.objects.filter(role='ATTENDANTS')

        # Exclude users already assigned as managers
        assigned_managers = ParkingLot.objects.values_list('manager_1', 'manager_2')
        assigned_managers = [manager for sublist in assigned_managers for manager in sublist if manager]

        self.fields['manager_1'].queryset = attendants.exclude(id__in=assigned_managers)
        self.fields['manager_2'].queryset = attendants.exclude(id__in=assigned_managers)

