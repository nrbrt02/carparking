from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import UserChangeForm
from .forms import LoginForm, ParkingLotForm, SubscriptionForm, ParkingSpaceForm, ParkingSpaceFormUpdate, TicketForm
from .models import User, ParkingLot, Subscription, ParkingSpace, Ticket
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from .decorators import admin_required, attendants_required, client_required, admin_or_attendant_required
import random
from django.utils import timezone
from django.db.models import Q, Sum, F
from django.http import HttpResponse, JsonResponse
from datetime import timedelta, datetime
from django.utils.timezone import now


def home(request):
    return render(request, 'index.html')


def unauthorized(request):
    return render(request, 'unauthorized.html')

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import LoginForm  # Ensure your LoginForm is correctly imported

def loginuser(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_input = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Check if login_input is an email or username
            if '@' in login_input:
                try:
                    # Try to get user by email
                    user = User.objects.get(email=login_input)
                except User.DoesNotExist:
                    user = None
            else:
                try:
                    # Try to get user by username
                    user = User.objects.get(username=login_input)
                except User.DoesNotExist:
                    user = None

            if user is not None:
                # Authenticate user
                user = authenticate(request, username=user.username, password=password)

                if user is not None:
                    # Check if the account is active
                    if user.is_active:
                        login(request, user)
                        return redirect('dashboard')
                    else:
                        return redirect('unauthorized')
                else:
                    messages.error(request, "Invalid username/email or password.")
            else:
                messages.error(request, "User does not exist.")
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


def get_user_parking_spaces(user):
    parking_lots = ParkingLot.objects.filter(
        Q(manager_1=user) | Q(manager_2=user)
    )
    return ParkingSpace.objects.filter(parking_lot__in=parking_lots, status=False)


@login_required
def dashboard(request):
    # Initialize variables for parking_spaces and form
    parking_spaces = []
    form = TicketForm()
    modal_open = False

    if request.user.role == 'ATTENDANTS':
        parking_spaces = get_user_parking_spaces(request.user)

        # Get the total number of tickets issued by the logged-in user
        total_tickets = Ticket.objects.filter(parking_attendee=request.user).count()

        # Get the total number of open tickets (tickets without exit_time)
        total_open_tickets = Ticket.objects.filter(parking_attendee=request.user, exit_time__isnull=True).count()

        # Get the total number of paid tickets (tickets with exit_time and payment_status = True)
        total_paid_tickets = Ticket.objects.filter(parking_attendee=request.user, payment_status=True).aggregate(total=Sum('total_payment'))['total'] or 0

        # Get the total number of not paid tickets (tickets with exit_time but payment_status = False)
        total_not_paid_tickets = Ticket.objects.filter(parking_attendee=request.user, exit_time__isnull=False, payment_status=False).aggregate(total=Sum('total_payment'))['total'] or 0

        # Calculate the percentage of paid tickets
        total_paid_tickets_percentage = (total_paid_tickets / (total_paid_tickets + total_not_paid_tickets) * 100) if (total_paid_tickets + total_not_paid_tickets) > 0 else 0

        # Calculate the percentage of open tickets
        total_open_tickets_percentage = (total_open_tickets / total_tickets * 100) if total_tickets > 0 else 0

        # Calculate the percentage of not paid tickets
        total_not_paid_tickets_percentage = (total_not_paid_tickets / total_tickets * 100) if total_tickets > 0 else 0

        tickets = Ticket.objects.filter(parking_attendee=request.user).order_by('-created_at')[:3]
        return render(
            request,
            "dashboard/index.html",
            {
                "tickets": tickets,
                "active_menu": "dashboard",
                "parking_spaces": parking_spaces,
                "form": form,
                "modal_open": modal_open,
                "total_tickets": total_tickets,
                "total_open_tickets": total_open_tickets,
                "total_paid_tickets": total_paid_tickets,
                "total_not_paid_tickets": total_not_paid_tickets,
                "total_tickets_percentage": total_open_tickets_percentage,
                "total_open_tickets_percentage": total_open_tickets_percentage,
                "total_paid_tickets_percentage": total_paid_tickets_percentage,
                "total_not_paid_tickets_percentage": total_not_paid_tickets_percentage,
            },
        )

    # Add any additional logic if needed for non-'ATTENDANTS' role
    return render(request, "dashboard/index.html", {
        "active_menu": "dashboard",
        "parking_spaces": parking_spaces,
        "form": form,
        "modal_open": modal_open,
    })



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


def parkingspace(request):
    parkingspace = ParkingSpace.objects.all()
    context = {'parkingspaces': parkingspace, 'active_menu': 'parkingspace'}
    return render(request, 'dashboard/parkingspace.html', context)

@login_required
@admin_required
def create_parking_space(request):
    if request.method == 'POST':
        form = ParkingSpaceForm(request.POST)
        if form.is_valid():
            parking_space = form.save(commit=False)
            parking_lot = parking_space.parking_lot
            
            # Check if the parking lot has reached its capacity
            current_spaces = parking_lot.parking_spaces.count()
            if current_spaces >= parking_lot.capacity:
                messages.error(
                    request, 
                    f"Cannot create more parking spaces. The parking lot '{parking_lot.name}' has reached its maximum capacity of {parking_lot.capacity}."
                )
                return redirect('create_parking_space')  # Replace with your URL name
            
            # Generate space_code
            subscription = parking_space.subscription
            space_code = f"{parking_lot.name[0].upper()}{subscription.name[0].upper() if subscription else 'X'}{random.randint(10, 99)}"
            parking_space.space_code = space_code
            
            parking_space.save()
            messages.success(request, 'Parking space created successfully!')
            return redirect('parkingspace')
    else:
        form = ParkingSpaceForm()
        parking_lots = ParkingLot.objects.all()

    return render(request, 'dashboard/create_parking_space.html', {'form': form, 'parking_lots': parking_lots, 'active_menu': 'parking_spaces'})


@login_required
@admin_required
def update_parking_space(request, pk):
    parking_space = get_object_or_404(ParkingSpace, pk=pk)
    parking_lots = ParkingLot.objects.all()

    if request.method == 'POST':
        form = ParkingSpaceFormUpdate(request.POST, instance=parking_space)
        if form.is_valid():
            updated_parking_lot = form.cleaned_data['parking_lot']
            original_parking_lot = parking_space.parking_lot

            # Compare the submitted and original parking lot
            # if updated_parking_lot.id != original_parking_lot.id:
            current_spaces_count = updated_parking_lot.parking_spaces.count()
            if current_spaces_count >= updated_parking_lot.capacity +1:
                messages.error(
                    request,
                    f"Cannot assign this parking space to '{updated_parking_lot.name}'. "
                    f"The parking lot has reached its maximum capacity of {updated_parking_lot.capacity}."
                )
                return render(
                    request,
                    'dashboard/update_parking_space.html',
                    {'form': form, 'parking_lots': parking_lots, 'active_menu': 'parking_spaces'}
                )

            form.save()
            messages.success(request, "Parking space updated successfully!")
            return redirect('parkingspace')
    else:
        form = ParkingSpaceFormUpdate(instance=parking_space)

    return render(
        request,
        'dashboard/update_parking_space.html',
        {'form': form, 'parking_lots': parking_lots, 'active_menu': 'parking_spaces'}
    )


@login_required
@admin_required
def delete_parking_space(request, pk):
    parking_space = get_object_or_404(ParkingSpace, pk=pk)
    
    # Handle deletion
    if request.method == "POST":
        if "delete" in request.POST:  # Check if the delete button was clicked
            parking_space.delete()
            messages.success(request, "Parking space deleted successfully!")
            return redirect('parkingspace')

    return render(request, 'dashboard/view_parking_space.html', {
        'parking_space': parking_space,
        'active_menu': 'parking_spaces'
    })


@login_required
@attendants_required
def create_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.entry_time = timezone.now()
            ticket.payment_status = False
            ticket.parking_attendee = request.user
            ticket.save()

            parking_space = ticket.parking_space
            if parking_space:
                parking_space.status = True
                parking_space.save()
            messages.success(request, "Ticket created successfully!")
            return redirect('dashboard')
        else:
            parking_spaces = get_user_parking_spaces(request.user)
            return render(
                request,
                'dashboard/index.html',
                {
                    'form': form,
                    'modal_open': True,
                    'active_menu': 'dashboard',
                    'parking_spaces': parking_spaces,
                }
            )
    return redirect('dashboard')


@login_required
@attendants_required
def att_tickets(request):
    tickets = Ticket.objects.filter(parking_attendee=request.user)
    parking_spaces = get_user_parking_spaces(request.user)
    return render(
        request,
        'dashboard/atttickets.html',
        {
            'tickets': tickets,
            'active_menu': 'tickets',
            'parking_spaces': parking_spaces,
        }
    )

@login_required
@attendants_required
def end_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    # Ensure the ticket hasn't already been ended
    if not ticket.exit_time:
        ticket.exit_time = timezone.now()  # Set the exit time to the current time

        # Calculate the duration in hours as a float
        duration = (ticket.exit_time - ticket.entry_time).total_seconds() / 3600

        # Get the subscription price
        subscription_price = ticket.parking_space.subscription.price  # Assuming this relationship exists

        # Calculate the total payment
        if duration < 1:
            ticket.total_payment = subscription_price  # Charge the default price
        else:
            ticket.total_payment = round(duration * subscription_price, 2)  # Charge based on duration

        # Mark the parking space as available
        parking_space = ticket.parking_space
        parking_space.status = False
        parking_space.save()

        # Save the updated ticket
        ticket.save()

        messages.success(request, f"Ticket ended successfully! Total payment: {ticket.total_payment} RWF")
    else:
        messages.error(request, "Ticket has already been ended.")

    return redirect('att_tickets')



@login_required
@attendants_required

@login_required
def print_receipt(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if ticket.payment_status:
        parking_space = ticket.parking_space
        subscription = parking_space.subscription if hasattr(parking_space, 'subscription') else None
        current_date = now().strftime("%Y-%m-%d")

        # Calculate duration
        if ticket.exit_time:
            duration = ticket.exit_time - ticket.entry_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes = remainder // 60
            duration_str = f"{int(hours)} hours, {int(minutes)} minutes"
        else:
            duration_str = "N/A"

        return render(
            request,
            'dashboard/receipt.html',
            {
                'ticket': ticket,
                'parking_space': parking_space,
                'subscription': subscription,
                'current_date': current_date,
                'duration_str': duration_str,  # Pass the formatted duration
            }
        )
    else:
        messages.error(request, "Payment not completed. Cannot print receipt.")
        return redirect('att_tickets')


@login_required
@attendants_required
def change_payment_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if not ticket.payment_status:
        ticket.payment_status = True
        ticket.save()
        messages.success(request, f"Payment status for Ticket {ticket.id} updated to Paid.")
    else:
        messages.warning(request, f"Payment status for Ticket {ticket.id} is already Paid.")

    return redirect('att_tickets')


@login_required
@attendants_required
def attsummary(request):
    if request.method == "GET" and "option" in request.GET:
        option = request.GET.get("option")
        user = request.user
        response_data = ""

        if option == "tickets":
            tickets = Ticket.objects.filter(parking_attendee=user)
            open_tickets = tickets.filter(exit_time__isnull=True)
            not_paid_tickets = tickets.filter(exit_time__isnull=False, payment_status=False)
            completed_tickets = tickets.filter(exit_time__isnull=False, payment_status=True)

            response_data = f"Total Tickets: {tickets.count()}<br>" \
                            f"Open Tickets: {open_tickets.count()}<br>" \
                            f"Not Paid: {not_paid_tickets.count()}<br>" \
                            f"Completed Tickets: {completed_tickets.count()}<br>"

        elif option == "income":
            completed_tickets = Ticket.objects.filter(
                parking_attendee=user, exit_time__isnull=False, payment_status=True
            )
            not_paid_tickets = Ticket.objects.filter(
                parking_attendee=user, exit_time__isnull=False, payment_status=False
            )
            total_income = completed_tickets.aggregate(Sum("total_payment"))["total_payment__sum"] or 0
            expected_income = (
                completed_tickets.aggregate(Sum("total_payment"))["total_payment__sum"] or 0
            ) + (not_paid_tickets.aggregate(Sum("total_payment"))["total_payment__sum"] or 0)

            response_data = f"Total Income: {total_income} RWF<br>" \
                            f"Expected Income: {expected_income} RWF<br>"

        elif option == "this_month":
            current_month = datetime.now().month
            current_year = datetime.now().year
            tickets = Ticket.objects.filter(parking_attendee=user, created_at__year=current_year, created_at__month=current_month)
            open_tickets = tickets.filter(exit_time__isnull=True)
            total_income = tickets.filter(payment_status=True).aggregate(Sum("total_payment"))["total_payment__sum"] or 0
            expected_income = tickets.aggregate(Sum("total_payment"))["total_payment__sum"] or 0

            response_data = f"Total Tickets this Month: {tickets.count()}<br>" \
                            f"Total Income this Month: {total_income} RWF<br>" \
                            f"Open Tickets this Month: {open_tickets.count()}<br>" \
                            f"Expected Income this Month: {expected_income} RWF<br>"

        elif option == "general":
            tickets = Ticket.objects.filter(parking_attendee=user)
            open_tickets = tickets.filter(exit_time__isnull=True)
            total_income = tickets.filter(payment_status=True).aggregate(Sum("total_payment"))["total_payment__sum"] or 0
            expected_income = tickets.aggregate(Sum("total_payment"))["total_payment__sum"] or 0

            response_data = f"Total Tickets: {tickets.count()}<br>" \
                            f"Total Income: {total_income} RWF<br>" \
                            f"Open Tickets: {open_tickets.count()}<br>" \
                            f"Expected Income: {expected_income} RWF<br>"

        return JsonResponse({"message": response_data})

    tickets = Ticket.objects.filter(parking_attendee=request.user)
    parking_spaces = get_user_parking_spaces(request.user)
    return render(
        request,
        "dashboard/att_summary.html",
        {
            'tickets': tickets,
            'active_menu': 'summary',
            'parking_spaces': parking_spaces,
        }
    )
