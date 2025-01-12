from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return redirect(reverse('unauthorized'))  # Redirect to unauthorized page or a custom page
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def attendants_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role != 'ATTENDANTS':
            return redirect(reverse('unauthorized'))  # Redirect to unauthorized page or a custom page
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def client_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role != 'CLIENT':
            return redirect(reverse('unauthorized'))  # Redirect to unauthorized page or a custom page
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_or_attendant_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role not in ['ADMIN', 'ATTENDANTS']:
            return redirect(reverse('unauthorized'))  # Redirect to unauthorized page or a custom page
        return view_func(request, *args, **kwargs)
    return _wrapped_view
