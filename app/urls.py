from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('login', views.loginuser, name="login"),
    path('unauthorized', views.unauthorized, name="unauthorized"),
    path('logout', views.logoutuser, name="logoutuser"),
    path('signup', views.signup, name="signup"),
    path('dashboard', views.dashboard, name="dashboard"),
    path('dashboard/uaccounts/profile', views.profile, name="profile"),
    path('dashboard/uaccounts', views.uaccounts, name="uaccounts"),
    path('dashboard/uaccounts/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('dashboard/uaccounts/create/', views.create_user, name='create_user'),

    path('dashboard/parking', views.parking, name="parking"),
    path('dashboard/parking/create/', views.create_parking_lot, name="create_parking_lot"),


]