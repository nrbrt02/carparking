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
    path('uaccounts/profile', views.profile, name="profile"),
    path('uaccounts', views.uaccounts, name="uaccounts"),
    path('uaccounts/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('uaccounts/create/', views.create_user, name='create_user'),

]