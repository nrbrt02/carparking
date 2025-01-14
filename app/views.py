from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import UserChangeForm
from .forms import LoginForm, ParkingLotForm, SubscriptionForm
from .models import User, ParkingLot, Subscription
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from .decorators import admin_required, attendants_required, client_required, admin_or_attendant_required



def home(request):
    return render(request, 'index.html')


def unauthorized(request):
    return render(request, 'unauthorized.html')

def loginuser(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_input = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            try:
                # Check if login_input is an email or username
                if '@' in login_input:
                    user = User.objects.get(email=login_input)
                    username = user.username
                else:
                    username = login_input

                # Authenticate user
                user = authenticate(request, username=username, password=password)

                if user is not None:
                    login(request, user)  # Correct usage of login
                    # Redirect based on user role
                    # if user.role == User.Role.ADMIN:
                    return redirect('dashboard')
                    # elif user.role == User.Role.ATTENDANTS:
                    #     return redirect('attendants-home')
                    # elif user.role == User.Role.CLIENT:
                    #     return redirect('client-home')
                    # else:
                        # return redirect('403')  # Permission denied
                else:
                    messages.error(request, "Invalid username/email or password.")
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

    
def signup(request):
    if request.method == 'POST':
        errors = {}  # Dictionary to hold error messages

    if request.method == 'POST':
        first_name = request.POST.get('firstname', '').strip()
        last_name = request.POST.get('lastname', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        # Validate fields
        if not first_name:
            errors['firstname'] = "First name is required."
        if not last_name:
            errors['lastname'] = "Last name is required."
        if not email:
            errors['email'] = "Email is required."
        elif User.objects.filter(email=email).exists():
            errors['email'] = "Email is already registered."
        if not password:
            errors['password'] = "Password is required."
        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        # If no errors, create the user
        if not errors:
            user = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=email,
                is_active=True,
            )
            user.password = make_password(password)
            user.save()

            messages.success(request, "Account created successfully. You can now log in.")
            return redirect('login')

        # Pass errors back to the template
        return render(request, 'signup.html', {'errors': errors})
    return render(request, 'signup.html')

@login_required
def logoutuser(request):
    logout(request)  # This logs out the user
    return redirect('home')

@login_required
def dashboard(request):
    return render(request, 'dashboard/index.html', {'active_menu': 'dashboard'})

@login_required
def profile(request):
    if request.method == 'POST':
        # Handling profile form submission
        if 'profile_form' in request.POST:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')

            # Validate data if necessary
            if first_name and last_name and email:
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.email = email
                request.user.phone_number = phone_number
                request.user.save()
                messages.success(request, "Your profile was successfully updated!")
                return redirect('profile')  # Redirect to the same page

            messages.error(request, "All required fields must be filled out.")
        
        # Handling password change form submission
        elif 'password_form' in request.POST:
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_new_password')

            # Validate password change logic
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            elif not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)  # Prevent user from being logged out
                messages.success(request, "Your password has been updated!")
                return redirect('profile')  # Redirect to the same page

    # Set up the form data for GET requests (to show in the form)
    context = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'phone_number': request.user.phone_number,
        'active_menu': 'uaccounts'
    }

    return render(request, 'dashboard/profile.html', context)

@login_required
@admin_required
def uaccounts(request):
    users = User.objects.all()
    return render(request, 'dashboard/uaccounts.html', {'users': users, 'active_menu': 'uaccounts'})


@login_required
@admin_required
def edit_user(request, user_id):
    # Check if the current user is an administrator
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to edit this user.")
        return redirect('uaccounts')  # Redirect to the user accounts page

    # Get the user object to edit
    user_to_edit = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        # Check if form is submitted for updates
        is_active = request.POST.get('is_active') == 'on'  # Checkbox for active status
        role = request.POST.get('role')  # New role
        password = request.POST.get('password')  # New password
        
        # Update the fields that can be edited
        user_to_edit.is_active = is_active
        user_to_edit.role = role  # Assuming role is a custom field in the User model

        # Update password only if it was provided
        if password:
            user_to_edit.password = make_password(password)  # Hash the password before saving

        user_to_edit.save()  # Save the changes
        
        # Display success message
        messages.success(request, "User details updated successfully.")
        return redirect('uaccounts')  # Redirect to the accounts list

    return render(request, 'dashboard/edit_user.html', {'user_to_edit': user_to_edit, 'active_menu': 'uaccounts'})



@login_required
@admin_required
def create_user(request):
    errors = {}
    form_data = {
        'username': '',
        'first_name': '',
        'last_name': '',
        'email': '',
        'phone_number': '',
        'role': '',
        'is_active': True,
    }

    if request.method == 'POST':
        # Extract form data
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        role = request.POST.get('role')
        is_active = request.POST.get('is_active') == 'on'
        password = request.POST.get('password')

        # Save form data for re-rendering
        form_data.update({
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone_number': phone_number,
            'role': role,
            'is_active': is_active,
        })

        # Validation checks
        if not username:
            errors['username'] = "Username is required."
        elif User.objects.filter(username=username).exists():
            errors['username'] = "Username already exists. Please choose another."

        if not first_name:
            errors['first_name'] = "First name is required."

        if not last_name:
            errors['last_name'] = "Last name is required."

        if not email:
            errors['email'] = "Email is required."
        elif User.objects.filter(email=email).exists():
            errors['email'] = "Email already exists. Please choose another."

        if not phone_number:
            errors['phone_number'] = "Phone number is required."

        if not role:
            errors['role'] = "Role is required."

        if not password:
            errors['password'] = "Password is required."

        # If no errors, create the user
        if not errors:
            user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=is_active
            )
            user.set_password(password)  # Hash the password before saving
            user.save()

            # Add custom fields for role and phone number
            user.role = role  # Assuming you have extended the User model via a Profile
            user.phone_number = phone_number
            user.save()

            # Redirect to accounts list with success message
            messages.success(request, "Account created successfully.")
            return redirect('uaccounts')

    return render(request, 'dashboard/create_user.html', {
        'errors': errors,
        'form_data': form_data,
        'active_menu': 'uaccounts'
    })


@login_required
@admin_required
def parking(request):
    parking_lots = ParkingLot.objects.all()

    for lot in parking_lots:
        # Use the restrictions field directly
        if lot.restrictions:  # Check if restrictions exist
            restrictions = lot.restrictions_list

    return render(request, 'dashboard/parking.html', {'parking_lots': parking_lots, 'active_menu': 'parking'})

@login_required
@admin_required
def create_parking_lot(request):
    if request.method == 'POST':
        form = ParkingLotForm(request.POST)
        if form.is_valid():
            parking_lot = form.save(commit=False)
            parking_lot.save()
            messages.success(request, 'Parking lot created successfully.')
            return redirect('parking')  # Redirect to a different view or the same page
        else:
            messages.error(request, 'There was an error with your submission. Please check the form.')
    else:
        form = ParkingLotForm()

    return render(request, 'dashboard/create_parking_lot.html', {'form': form})


@login_required
@admin_required
def update_parking_lot(request, pk):
    parking_lot = get_object_or_404(ParkingLot, pk=pk)

    if request.method == 'POST':
        form = ParkingLotForm(request.POST, instance=parking_lot)
        if form.is_valid():
            parking_lot = form.save(commit=False)
            parking_lot.save()
            messages.success(request, 'Parking lot updated successfully.')
            return redirect('parking')  # Redirect to the list or detail view
        else:
            messages.error(request, 'There was an error with your submission. Please check the form.')
    else:
        # Prepopulate the form with instance data
        form = ParkingLotForm(instance=parking_lot)

    return render(request, 'dashboard/update_parking_lot.html', {'form': form, 'parking_lot': parking_lot, 'active_menu': 'parking'})


@login_required
@admin_required
def delete_parking_lot(request, pk):
    parking_lot = get_object_or_404(ParkingLot, pk=pk)
    if request.method == "POST":
        parking_lot.delete()
        messages.success(request, "Parking lot deleted successfully.")
        return redirect("parking")  # Update with your list view URL name
    return render(request, "dashboard/delete_parking_lot.html", {"parking_lot": parking_lot, 'active_menu': 'parking'})


@login_required
@admin_required
def subscriptions(request):
    sublist = Subscription.objects.all()
    context={
        'subscriptions': sublist,
        'active_menu': 'subscriptions'
    }
    return render(request, "dashboard/subscriptions.html", context)


@login_required
@admin_required
def create_subscription(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscription created successfully!")
            return redirect("subscriptions")
    else:
        form = SubscriptionForm()
    
    return render(request, "dashboard/create_subscription.html", {"form": form, 'active_menu': 'subscriptions'})


@login_required
@admin_required
def update_subscription(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)
    if request.method == "POST":
        form = SubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscription updated successfully!")
            return redirect("subscriptions")
    else:
        form = SubscriptionForm(instance=subscription)

    context = {
        "form": form,
        "subscription": subscription,
        'active_menu': 'subscriptions',
    }
    return render(request, "dashboard/update_subscription.html", context)


@login_required
@admin_required
def subscription_view(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    
    # Handle deletion
    if request.method == "POST":
        if "delete" in request.POST:  # Check if the delete button was clicked
            subscription.delete()
            messages.success(request, "Subscription deleted successfully!")
            return redirect('subscriptions')

    return render(request, 'dashboard/view_sub.html', {
        'subscription': subscription,
        'active_menu': 'subscriptions'
    })