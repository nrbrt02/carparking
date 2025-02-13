from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import UserChangeForm
from .forms import LoginForm, ParkingLotForm, SubscriptionForm, ParkingSpaceForm, ParkingSpaceFormUpdate, TicketForm, SubscribedForm, ContactForm
from .models import User, ParkingLot, Subscription, ParkingSpace, Ticket, Subscribed
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from .decorators import admin_required, attendants_required, client_required, admin_or_attendant_required
import random
from django.utils import timezone
from django.db import models
from django.db.models import Q, Sum, F, ProtectedError, Sum, Count
from django.http import HttpResponse, JsonResponse
from datetime import timedelta, datetime
from django.utils.timezone import now
from django.db import transaction
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from collections import defaultdict

def home(request):
    parkinglots = ParkingLot.objects.all()
    Subscribed.objects.filter(end_date__lt=now(), status='ACTIVE').update(status='EXPIRED')

    return render(request, 'index.html', {'parkinglots': parkinglots, 'active_menu': 'home'})


def parkingH(request, parking_id):
    parking_lot = get_object_or_404(ParkingLot, id=parking_id)
    parking_spaces = parking_lot.parking_spaces.all()

    # Calculate percentage of fullness
    total_spaces = parking_spaces.count()
    occupied_spaces = parking_spaces.filter(status=True).count()  # Status True = occupied
    fullness_percentage = (occupied_spaces / total_spaces) * 100 if total_spaces > 0 else 0
    parkinglots = ParkingLot.objects.all()
    context = {
        'parking_lot': parking_lot,
        'parking_spaces': parking_spaces,
        'fullness_percentage': round(fullness_percentage, 2),
        'active_menu': 'parkingH',
        'parkinglots': parkinglots,
    }
    return render(request, 'parking_details.html', context)


def contact_view(request):
    parkinglots = ParkingLot.objects.all()

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save the form data
            contact_message = form.save()

            # Render the email template
            html_message = render_to_string('email_templates/confirmation_email.html', {
                'name': contact_message.name,
                'message': contact_message.message,
                'year': datetime.now().year,
            })

            # Send the HTML email
            email = EmailMessage(
                subject="Thank you for contacting us!",
                body=html_message,
                from_email="no-reply@carparking.com",  # Replace with your email
                to=[contact_message.email],
            )
            email.content_subtype = "html"  # Specify the email type as HTML
            email.send()

            # Show success message
            messages.success(request, 'Your message has been sent successfully! A confirmation email has been sent to your inbox.')
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form, 'parkinglots': parkinglots,})

def unauthorized(request):
    return render(request, 'unauthorized.html')


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

def get_ticket_statistics(user):
    """Returns ticket statistics for a given user."""
    total_tickets = Ticket.objects.filter(parking_attendee=user).count()
    total_open_tickets = Ticket.objects.filter(parking_attendee=user, exit_time__isnull=True).count()
    total_paid_tickets = Ticket.objects.filter(parking_attendee=user, payment_status=True).aggregate(total=Sum('total_payment'))['total'] or 0
    total_not_paid_tickets = Ticket.objects.filter(parking_attendee=user, exit_time__isnull=False, payment_status=False).aggregate(total=Sum('total_payment'))['total'] or 0

    total_paid_tickets_percentage = (
        (total_paid_tickets / (total_paid_tickets + total_not_paid_tickets) * 100)
        if (total_paid_tickets + total_not_paid_tickets) > 0
        else 0
    )
    total_open_tickets_percentage = (
        (total_open_tickets / total_tickets * 100) if total_tickets > 0 else 0
    )
    total_not_paid_tickets_percentage = (
        (total_not_paid_tickets / total_tickets * 100) if total_tickets > 0 else 0
    )

    return {
        "total_tickets": total_tickets,
        "total_open_tickets": total_open_tickets,
        "total_paid_tickets": total_paid_tickets,
        "total_not_paid_tickets": total_not_paid_tickets,
        "total_paid_tickets_percentage": total_paid_tickets_percentage,
        "total_open_tickets_percentage": total_open_tickets_percentage,
        "total_not_paid_tickets_percentage": total_not_paid_tickets_percentage,
    }

def get_recent_tickets(user, limit=3):
    """Returns the most recent tickets for a given user."""
    return Ticket.objects.filter(parking_attendee=user).order_by('-created_at')[:limit]

def get_client_subscription(user):
    """
    Retrieves the active subscription for the logged-in client.
    Returns None if no active subscription exists.
    """
    if user.role != 'CLIENT':
        return None

    # Fetch the active subscription for the user
    active_subscription = Subscribed.objects.filter(
        client=user,
        status='ACTIVE',
        end_date__gt=now()
    ).first()

    return active_subscription

@login_required
def get_available_parking_spaces(request, parking_lot_id):
    spaces = ParkingSpace.objects.filter(parking_lot_id=parking_lot_id, status=False)
    return JsonResponse([{"id": space.id, "space_code": space.space_code} for space in spaces], safe=False)

def send_subscription_email(user, subscription):
    subject = "Subscription Confirmation"
    message = render_to_string('dashboard/emails/subscription_confirmation.html', {
        'user': user,
        'subscription': subscription,
    })
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,  # Your configured email sender
        [user.email],  # Recipient's email
    )
    email.content_subtype = "html"  # Send as HTML
    email.send()

def get_unpaid_subscriptions_count(user):
    """
    Returns the count of unpaid subscriptions for the logged-in user (attendant).
    """
    parking_lots = ParkingLot.objects.filter(manager_1=user) | ParkingLot.objects.filter(manager_2=user)
    parking_spaces = ParkingSpace.objects.filter(parking_lot__in=parking_lots)
    return Subscribed.objects.filter(parking_space__in=parking_spaces, payment_status=False).count()

def send_payment_status_email(subscription):
    subject = "Subscription Payment Status Updated"
    message = render_to_string('dashboard/emails/payment_status_update.html', {
        'user': subscription.client,
        'subscription': subscription,
    })
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,  # Configured email sender
        [subscription.client.email],  # Client's email
    )
    email.content_subtype = "html"  # Send as HTML
    email.send()


@login_required
def dashboard(request):
    parking_spaces = []
    form = TicketForm()
    modal_open = False

    if request.user.role == 'ADMIN':
        current_month = now().month
        current_year = now().year

        parking_lot_data = ParkingLot.objects.annotate(ticket_count=Count('parking_spaces__ticket'))
        top_parking_lots = (
            ParkingLot.objects.annotate(
                ticket_count=Count('parking_spaces__ticket'),
                total_income=Sum('parking_spaces__ticket__total_payment')
            )
            .order_by('-ticket_count')[:5]
        )

        parking_lot_labels = [lot.name for lot in parking_lot_data]
        parking_lot_counts = [lot.ticket_count for lot in parking_lot_data]

        income_data = {
            'total_subscription_income': Subscribed.objects.aggregate(total=Sum('total_cost'))['total'] or 0,
            'monthly_subscription_income': Subscribed.objects.filter(
                start_date__year=current_year, start_date__month=current_month
            ).aggregate(total=Sum('total_cost'))['total'] or 0,
            'total_ticket_income': Ticket.objects.aggregate(total=Sum('total_payment'))['total'] or 0,
            'monthly_ticket_income': Ticket.objects.filter(
                entry_time__year=current_year, entry_time__month=current_month
            ).aggregate(total=Sum('total_payment'))['total'] or 0,
            'total_subscribed': Subscribed.objects.count(),
            'total_clients': User.objects.filter(role='CLIENT').count(),
            'total_tickets': Ticket.objects.count(),
            'total_attendants': User.objects.filter(role='ATTENDANTS').count(),
        }

        context = {
            'top_parking_lots': top_parking_lots,
            'income_data': income_data,
            'parking_lot_labels': parking_lot_labels,
            'parking_lot_counts': parking_lot_counts,
        }

        return render(request, "dashboard/index.html", context)

    if request.user.role == 'CLIENT':
        active_subscription = get_client_subscription(request.user)
        parking_lots = ParkingLot.objects.all()

        progress_percentage = 0
        if active_subscription:
            start_date = active_subscription.start_date
            end_date = active_subscription.end_date
            now_time = now()

            total_time = (end_date - start_date).total_seconds()
            time_elapsed = (now_time - start_date).total_seconds()
            progress_percentage = min(max((time_elapsed / total_time) * 100, 0), 100)

        return render(
            request,
            "dashboard/index.html",
            {
                "active_menu": "dashboard",
                "active_subscription": active_subscription,
                "parking_lots": parking_lots,
                "progress_percentage": progress_percentage,
                "modal_open": modal_open,
            },
        )

    if request.user.role == 'ATTENDANTS':
        parking_spaces = get_user_parking_spaces(request.user)
        ticket_stats = get_ticket_statistics(request.user)
        tickets = get_recent_tickets(request.user)
        unpaid_count = get_unpaid_subscriptions_count(request.user)

        return render(
            request,
            "dashboard/index.html",
            {
                "tickets": tickets,
                "active_menu": "dashboard",
                "parking_spaces": parking_spaces,
                "form": form,
                "modal_open": modal_open,
                "unpaid_count": unpaid_count,
                **ticket_stats,
            },
        )

    return render(
        request,
        "dashboard/index.html",
        {
            "active_menu": "dashboard",
            "parking_spaces": parking_spaces,
            "form": form,
            "modal_open": modal_open,
        },
    )


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

    unpaid_count = get_unpaid_subscriptions_count(request.user)
    context = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'phone_number': request.user.phone_number,
        'unpaid_count': unpaid_count
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

    unpaid_count = get_unpaid_subscriptions_count(request.user)
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
        try:
            parking_lot.delete()
            messages.success(request, "Parking lot deleted successfully.")
            return redirect("parking")  # Update with your list view URL name
        except ProtectedError:
            messages.error(request, "This parking lot cannot be deleted because it is associated with existing parking spaces.")
            return redirect("parking")  # Redirect back to the list view or appropriate page

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
        print("Submited terms: "+request.POST.get("terms"))  # Debug: Check if the value is being sent
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscription created successfully!")
            return redirect("subscriptions")
        else:
            messages.error(request, "There were errors in your submission. Please correct them.")
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
            try:
                subscription.delete()
                messages.success(request, "Subscription deleted successfully!")
                return redirect('subscriptions')
            except ProtectedError:
                messages.error(request, "Cannot delete this subscription because it is in use or referenced by other entities.")
    
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
            try:
                parking_space.delete()
                messages.success(request, "Parking space deleted successfully!")
                return redirect('parkingspace')
            except ProtectedError:
                messages.error(request, "Cannot delete this parking space because it is in use or referenced by other entities.")

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
    unpaid_count = get_unpaid_subscriptions_count(request.user)

    return render(
        request,
        'dashboard/atttickets.html',
        {
            'tickets': tickets,
            'active_menu': 'tickets',
            'parking_spaces': parking_spaces,
            'unpaid_count': unpaid_count
        }
    )


@login_required
@attendants_required
def subscribed_parking_spaces(request):

    parking_lots = ParkingLot.objects.filter(manager_1=request.user) | ParkingLot.objects.filter(manager_2=request.user)

    # Get parking spaces associated with those parking lots
    parking_spaces = ParkingSpace.objects.filter(parking_lot__in=parking_lots)

    # Retrieve active subscriptions linked to those parking spaces
    subscriptions = Subscribed.objects.filter(
        parking_space__in=parking_spaces,
    ).select_related('client', 'parking_space')
    unpaid_count = get_unpaid_subscriptions_count(request.user)
    return render(
        request,
        "dashboard/attsubscriptions.html",
        {
            "active_menu": "subscription",
            "subscriptions": subscriptions,
            "unpaid_count": unpaid_count,
        },
    )


@login_required
@attendants_required
def change_subpayment_status(request, subscription_id):
    subscription = get_object_or_404(Subscribed, id=subscription_id)

    if subscription.payment_status:
        messages.warning(request, "Ticket payment status already ok!")
    else:
        # Update payment status
        subscription.payment_status = True
        subscription.save()
        send_payment_status_email(subscription)
        messages.success(request, "Payment status updated successfully.")

    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
@attendants_required
def end_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if not ticket.exit_time:
        ticket.exit_time = timezone.now()  
        duration = (ticket.exit_time - ticket.entry_time).total_seconds() / 3600

        # Get the subscription price or set a default
        subscription = ticket.parking_space.subscription
        subscription_price = subscription.price if subscription else 500  # Default price

        # Calculate total payment
        ticket.total_payment = subscription_price if duration < 1 else round(duration * subscription_price, 2)

        # Mark the space as available
        parking_space = ticket.parking_space
        parking_space.status = False
        parking_space.save()

        ticket.save()
        messages.success(request, f"Ticket ended successfully! Total payment: {ticket.total_payment} RWF")
    else:
        messages.error(request, "Ticket has already been ended.")

    return redirect('att_tickets')




@login_required
@admin_or_attendant_required
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
    unpaid_count = get_unpaid_subscriptions_count(request.user)

    return render(
        request,
        "dashboard/att_summary.html",
        {
            'tickets': tickets,
            'active_menu': 'summary',
            'parking_spaces': parking_spaces,
            'unpaid_count': unpaid_count
        }
    )

@login_required
@admin_required
def view_userA(request, user_id):
    # Get the specific attendant
    user = get_object_or_404(User, id=user_id, role='ATTENDANTS')

    # Retrieve ticket statistics using the helper function
    ticket_stats = get_ticket_statistics(user)

    # Retrieve recent tickets using the helper function
    recent_tickets = Ticket.objects.filter(parking_attendee=user).order_by('-created_at')

    assigned_parking_lots = ParkingLot.objects.filter(
        models.Q(manager_1=user) | models.Q(manager_2=user)
    )
    # Prepare chart data
    tickets_chart_data = {
        "labels": ["Total Tickets", "Open Tickets"],
        "data": [ticket_stats['total_tickets'], ticket_stats['total_open_tickets']],
    }
    payments_chart_data = {
        "labels": ["Paid Tickets", "Not Paid Tickets"],
        "data": [ticket_stats['total_paid_tickets'], ticket_stats['total_not_paid_tickets']],
    }

    # Pass context to the template
    return render(
        request,
        'dashboard/view_user.html',
        {
            "user": user,
            "tickets": recent_tickets,
            "active_menu": "uaccounts",
            **ticket_stats,  # Unpack the ticket statistics into the context
            "tickets_chart_data": tickets_chart_data,
            "payments_chart_data": payments_chart_data,
            "assigned_parking_lots": assigned_parking_lots,
        },
    )


@login_required
@admin_required
def view_userC(request, user_id):
    user = get_object_or_404(User, id=user_id, role='CLIENT')
    active_subscription = get_client_subscription(user)

    progress_percentage = 0
    if active_subscription:
        start_date = active_subscription.start_date
        end_date = active_subscription.end_date
        now = timezone.now()  # Use timezone-aware current time

        # Calculate total time and elapsed time in seconds
        total_time = (end_date - start_date).total_seconds()
        time_elapsed = (now - start_date).total_seconds()

        # Ensure progress percentage is within bounds
        progress_percentage = min(max((time_elapsed / total_time) * 100, 0), 100)

    return render(request, 'dashboard/view-client.html', {'client': user, 'active_subscription': active_subscription, 'progress_percentage': progress_percentage})

def calculate_cost(parking_space, subscription_time=None, start_date=None, end_date=None):
    """
    Calculate the total cost of a subscription.

    Args:
        parking_space (ParkingSpace): The parking space for which the subscription is made.
        subscription_time (int): The subscription duration in days (optional).
        start_date (datetime): Start date of the subscription (optional).
        end_date (datetime): End date of the subscription (optional).

    Returns:
        int: The total cost after applying the discount rate.
    """
    # Ensure parking space has a related subscription
    if not parking_space.subscription:
        raise ValueError("The selected parking space does not have an associated subscription plan.")

    subscription = parking_space.subscription
    price_per_hour = subscription.price / 24  # Convert daily price to hourly price

    # Determine the duration in hours
    if subscription_time:
        total_hours = subscription_time * 24
    elif start_date and end_date:
        total_hours = int((end_date - start_date).total_seconds() // 3600)
    else:
        raise ValueError("Either subscription_time or start_date and end_date must be provided.")

    # Calculate the base cost
    base_cost = total_hours * price_per_hour

    # Apply the discount rate
    discount = (base_cost * subscription.discount_rate) / 100
    final_cost = int(base_cost - discount)

    return final_cost


@login_required
def start_subscription(request):
    if request.method == "POST":
        form = SubscribedForm(request.POST)
        if form.is_valid():
            subscription_time = int(request.POST.get("subscription_time"))
            parking_space = form.cleaned_data.get("parking_space")
            start_date = now()
            end_date = start_date + timedelta(days=subscription_time)

            # Validation: Ensure no overlapping subscriptions
            overlapping_subscriptions = Subscribed.objects.filter(
                parking_space=parking_space,
                status='ACTIVE'
            )

            if overlapping_subscriptions.exists():
                messages.error(
                    request, "There is already an active subscription for this parking space during the selected period."
                )
                return render(
                    request, 
                    "dashboard/includes/subscription_form_fragment.html", 
                    {"form": form, "parking_lots": ParkingSpace.objects.all()}
                )

            # Calculate the total cost
            try:
                total_cost = calculate_cost(
                    parking_space=parking_space,
                    subscription_time=subscription_time
                )
            except ValueError as e:
                messages.error(request, str(e))
                return render(
                    request, 
                    "dashboard/includes/subscription_form_fragment.html", 
                    {"form": form, "parking_lots": ParkingSpace.objects.all()}
                )

            # If all is valid, create the subscription and update the parking space status
            with transaction.atomic():  # Ensure atomicity
                subscription = form.save(commit=False)
                subscription.client = request.user
                subscription.start_date = start_date
                subscription.end_date = end_date
                subscription.total_cost = total_cost
                subscription.save()

                # Update parking space status
                parking_space.status = True
                parking_space.save()

            # Send email notification
            send_subscription_email(request.user, subscription)

            messages.success(request, "Subscription created successfully!")
            return JsonResponse({"success": True})

        else:
            # Render only the form fragment with errors
            parking_lots = ParkingLot.objects.all()
            return render(
                request, 
                "dashboard/includes/subscription_form_fragment.html", 
                {"form": form, "parking_lots": parking_lots}
            )
    
    return JsonResponse({"error": "Invalid request method."}, status=400)


@login_required
def print_subreceipt(request, subscription_id):
    subscription = get_object_or_404(Subscribed, id=subscription_id)

    if not subscription.payment_status:
        return HttpResponse("Cannot print receipt for unpaid subscription.", status=400)

    return render(
        request,
        "dashboard/subreceipt.html",
        {"subscription": subscription},
    )

@login_required
def allticket(request):
    tickets = Ticket.objects.all()
    return render(request, "dashboard/atttickets.html", {'tickets': tickets})


def subscription_list(request):
    subscriptions = Subscribed.objects.all().order_by('-created_at')  # Fetch all subscriptions ordered by latest
    return render(request, 'dashboard/subscribed-list.html', {'subscriptions': subscriptions})