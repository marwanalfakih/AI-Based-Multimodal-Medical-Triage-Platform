# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from .forms import PatientRegistrationForm
from django.contrib.auth.forms import AuthenticationForm
from patients.models import PatientCase, Appointment, MedicalHistory, Notification
from triage.models import TriageResult
from .models import User 

from patients.models import PatientCase, Appointment, MedicalHistory, Notification
from triage.models import TriageResult


def register_patient(request):
    """تسجيل مريض جديد"""
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created successfully.')
            return redirect('home:index')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    """تسجيل الدخول"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # توجيه حسب نوع المستخدم
                if user.user_type == 'doctor':
                    return redirect('dashboard:incoming_cases')
                else:
                    return redirect('home:index')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    """تسجيل الخروج"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home:index')

@login_required
def profile(request):
    """View user profile with recent activity"""
    user = request.user
    
    # جلب البيانات حسب نوع المستخدم
    if user.user_type == 'patient':
        # Recent cases
        recent_cases = PatientCase.objects.filter(patient=user).order_by('-created_at')[:5]
        
        # تجهيز الحالات مع نتائج التصنيف
        cases_with_triage = []
        for case in recent_cases:
            try:
                triage = TriageResult.objects.get(case=case)
                cases_with_triage.append({
                    'case': case,
                    'triage': triage
                })
            except TriageResult.DoesNotExist:
                cases_with_triage.append({
                    'case': case,
                    'triage': None
                })
        
        # Upcoming appointments
        from django.utils import timezone
        upcoming_appointments = Appointment.objects.filter(
            patient=user,
            appointment_date__gte=timezone.now()
        ).order_by('appointment_date')[:3]
        
        # Medical history
        medical_history = MedicalHistory.objects.filter(patient=user).order_by('-date')[:3]
        
        # Statistics
        total_cases = PatientCase.objects.filter(patient=user).count()
        total_appointments = Appointment.objects.filter(patient=user).count()
        unread_notifications = Notification.objects.filter(user=user, is_read=False).count()
        
        context = {
            'user': user,
            'recent_cases': cases_with_triage,
            'upcoming_appointments': upcoming_appointments,
            'medical_history': medical_history,
            'total_cases': total_cases,
            'total_appointments': total_appointments,
            'unread_notifications': unread_notifications,
        }
    else:
        # للدكتور أو المشرف
        context = {
            'user': user,
        }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def doctor_profile(request):
    """Doctor profile view"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    # Get statistics - باستخدام PatientCase المستورد
    total_cases = PatientCase.objects.count()
    total_patients = User.objects.filter(user_type='patient').count()
    
    # Recent activity (last 5 actions)
    recent_activities = []
    
    # Add recent cases
    recent_cases = PatientCase.objects.order_by('-created_at')[:3]
    for case in recent_cases:
        # تنسيق الوقت
        time_diff = timezone.now() - case.created_at
        if time_diff.days > 0:
            time_str = f"{time_diff.days} days ago"
        elif time_diff.seconds > 3600:
            time_str = f"{time_diff.seconds // 3600} hours ago"
        elif time_diff.seconds > 60:
            time_str = f"{time_diff.seconds // 60} minutes ago"
        else:
            time_str = "just now"
            
        recent_activities.append({
            'title': f'New Case #{case.id}',
            'description': f'Patient: {case.patient.get_full_name() or case.patient.username}',
            'time': time_str,
            'color': 'primary'
        })
    
    # Add recent appointments
    recent_appointments = Appointment.objects.order_by('-created_at')[:2]
    for apt in recent_appointments:
        time_diff = timezone.now() - apt.created_at
        if time_diff.days > 0:
            time_str = f"{time_diff.days} days ago"
        elif time_diff.seconds > 3600:
            time_str = f"{time_diff.seconds // 3600} hours ago"
        elif time_diff.seconds > 60:
            time_str = f"{time_diff.seconds // 60} minutes ago"
        else:
            time_str = "just now"
            
        recent_activities.append({
            'title': f'Appointment #{apt.id}',
            'description': f'{apt.patient.get_full_name() or apt.patient.username} - {apt.get_appointment_type_display()}',
            'time': time_str,
            'color': 'success'
        })
    
    # Schedule (يمكن جلبها من قاعدة بيانات أو استخدام قيم افتراضية)
    schedule = {
        'monday': '9:00 AM - 5:00 PM',
        'tuesday': '9:00 AM - 5:00 PM',
        'wednesday': '9:00 AM - 5:00 PM',
        'thursday': '9:00 AM - 5:00 PM',
        'friday': '9:00 AM - 1:00 PM',
        'saturday': 'Closed',
        'sunday': 'Closed',
    }
    
    # Count for sidebar
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    context = {
        'total_cases': total_cases,
        'total_patients': total_patients,
        'years_exp': 5,  # يمكن جلبها من قاعدة البيانات
        'recent_activities': recent_activities,
        'schedule': schedule,
        'incoming_count': incoming_count,
    }
    
    return render(request, 'dashboard/doctor_profile.html', context)