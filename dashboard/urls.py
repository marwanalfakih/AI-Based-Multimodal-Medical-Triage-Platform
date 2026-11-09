# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Cases management
    path('incoming/', views.incoming_cases, name='incoming_cases'),
    path('case/<int:case_id>/', views.case_detail, name='case_detail'),
    path('case/<int:case_id>/update-triage/', views.update_triage, name='update_triage'),
    
    # Appointments
    path('appointments/', views.appointments, name='appointments'),
    path('appointments/<int:appointment_id>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    # Patients management
    path('patients/', views.patients_list, name='patients_list'),
    path('patients/<int:patient_id>/history/', views.patient_history, name='patient_history'),
    
    # Statistics
    path('stats/', views.stats, name='stats'),
    
    # Reviewed cases
    #path('reviewed/', views.incoming_cases, {'reviewed': True}, name='reviewed_cases'),

    path('reviewed/', views.reviewed_cases, name='reviewed_cases'),
]