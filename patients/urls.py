# patients/urls.py
from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    # Patient Dashboard
    path('dashboard/', views.patient_dashboard, name='patient_dashboard'),
    
    # Case Management
    path('cases/new/', views.new_case, name='new_case'),
    path('cases/', views.my_cases, name='my_cases'),
    path('cases/<int:case_id>/', views.case_detail, name='case_detail'),
    path('cases/<int:case_id>/edit/', views.edit_case, name='edit_case'),
    path('cases/<int:case_id>/delete/', views.delete_case, name='delete_case'),
    path('delete-account/', views.delete_account, name='delete_account'),

    
    # Medical History
    path('history/', views.medical_history, name='medical_history'),
    
    # Appointments 
    path('appointments/', views.my_appointments, name='my_appointments'),
    path('appointments/new/', views.new_appointment, name='new_appointment'),
    path('appointments/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'), 

    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/<int:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    # Profile Settings
    path('settings/', views.patient_settings, name='patient_settings'),
    path('settings/update/', views.update_profile, name='update_profile'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),

    # Delete Account
    path('delete-account/', views.delete_account, name='delete_account'),
    path('ajax/load-doctors/', views.load_doctors, name='ajax_load_doctors'),
]