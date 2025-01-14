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
    path('dashboard/parking/update/<int:pk>/', views.update_parking_lot, name='update_parking_lot'),
    path("dashboard/parking-lot/<int:pk>/delete/", views.delete_parking_lot, name="delete_parking_lot"),

    path('dashboard/subscriptions', views.subscriptions, name="subscriptions"),
    path("dashboard/subscriptions/create/", views.create_subscription, name="create_subscription"),
    path('dashboard/subscriptions/update/<int:subscription_id>/', views.update_subscription, name='update_subscription'),
    path('dashboard/subscription/<int:pk>/', views.subscription_view, name='subscription_view'),



]