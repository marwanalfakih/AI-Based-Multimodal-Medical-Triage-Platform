# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/patient/', views.register_patient, name='register_patient'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('doctor/profile/', views.doctor_profile, name='doctor_profile'),
]