from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('login', views.loginuser, name="login"),
    path('unauthorized', views.unauthorized, name="unauthorized"),
    path('logout', views.logoutuser, name="logoutuser"),
    path('signup', views.signup, name="signup"),
    path('parking/<int:parking_id>', views.parkingH, name="parkingH"),


    path('dashboard/', views.dashboard, name="dashboard"),
    path('dashboard/uaccounts/profile', views.profile, name="profile"),
    path('dashboard/uaccounts', views.uaccounts, name="uaccounts"),
    path('dashboard/uaccounts/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('dashboard/uaccounts/view/<int:user_id>/', views.view_userA, name='view_userA'),
    path('dashboard/uaccounts/create/', views.create_user, name='create_user'),

    path('dashboard/parking', views.parking, name="parking"),
    path('dashboard/parking/create/', views.create_parking_lot, name="create_parking_lot"),
    path('dashboard/parking/update/<int:pk>/', views.update_parking_lot, name='update_parking_lot'),
    path("dashboard/parking-lot/<int:pk>/delete/", views.delete_parking_lot, name="delete_parking_lot"),

    path('dashboard/subscriptions', views.subscriptions, name="subscriptions"),
    path("dashboard/subscriptions/create/", views.create_subscription, name="create_subscription"),
    path('dashboard/subscriptions/update/<int:subscription_id>/', views.update_subscription, name='update_subscription'),
    path('dashboard/subscription/<int:pk>/', views.subscription_view, name='subscription_view'),

    path('dashboard/parkingspace', views.parkingspace, name="parkingspace"),
    path('dashboard/parkingspace/create/', views.create_parking_space, name='create_parking_space'),
    path('dashboard/parkingspace/update/<int:pk>/', views.update_parking_space, name='update_parking_space'),
    path('dashboard/parkingspace/delete/<int:pk>/', views.delete_parking_space, name='delete_parking_space'),



    path('dashboard/create-ticket/', views.create_ticket, name='create_ticket'),
    path('dashboard/att-tickets/', views.att_tickets, name='att_tickets'),
    path('dashboard/tickets/<int:ticket_id>/end/', views.end_ticket, name='end_ticket'),
    path('dashboard/tickets/<int:ticket_id>/print/', views.print_receipt, name='print_receipt'),
    path('dashboard/tickets/<int:ticket_id>/change-payment-status/', views.change_payment_status, name='change_payment_status'),
    path('dashboard/att-summary/', views.attsummary, name='att_summary'),

    path("get-available-parking-spaces/<int:parking_lot_id>/", views.get_available_parking_spaces, name="get_available_parking_spaces"),
    path('dashboard/start-subscription/', views.start_subscription, name='start_subscription'),
    path('dashboard/subscribed-parking-spaces/', views.subscribed_parking_spaces, name='subscribed_parking_spaces'),
    path('dashboard/change-payment-status/<int:subscription_id>/', views.change_subpayment_status, name='change_subpayment_status'),
    path('dashboard/receipt/<int:subscription_id>/', views.print_subreceipt, name='print_subreceipt'),

]