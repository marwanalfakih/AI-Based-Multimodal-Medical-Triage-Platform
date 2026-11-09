# dashboard/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from patients.models import PatientCase, Appointment, Notification, CaseImage
from triage.models import TriageResult
from accounts.models import User, Specialization
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os

@login_required
def dashboard(request):
    """Doctor's main dashboard"""
    # التحقق من أن المستخدم دكتور
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # إحصائيات سريعة
    pending_cases = PatientCase.objects.filter(is_processed=False).count()
   # reviewed_today = PatientCase.objects.filter(
    #    is_processed=True,
     #   updated_at__gte=today_start
    #).count()

    # 🔴 الحالات التي تمت مراجعتها اليوم (ذات صلة بالطبيب)
    reviewed_today = TriageResult.objects.filter(
        reviewed_by=request.user,
        reviewed_at__gte=today_start
    ).count()
    
    # الحالات العاجلة
    urgent_cases = PatientCase.objects.filter(
        is_processed=False,
        triage_result__suggested_level='red'
    ).count()
    
    # مواعيد اليوم
    appointments_today = Appointment.objects.filter(
        doctor=request.user,
        appointment_date__date=now.date()
    ).count()
    
    # آخر 5 حالات واردة
    recent_cases = PatientCase.objects.filter(
        is_processed=False
    ).select_related('patient', 'triage_result').order_by('-created_at')[:5]
    
    recent_cases_list = []
    for case in recent_cases:
        try:
            triage = TriageResult.objects.get(case=case)
        except TriageResult.DoesNotExist:
            triage = None
        recent_cases_list.append({
            'case': case,
            'triage_result': triage
        })
    
    # مواعيد اليوم
    today_appointments = Appointment.objects.filter(
        doctor=request.user,
        appointment_date__date=now.date()
    ).select_related('patient').order_by('appointment_date')[:5]
    
    # توزيع التصنيفات
    triage_counts = {
        'red': TriageResult.objects.filter(suggested_level='red').count(),
        'yellow': TriageResult.objects.filter(suggested_level='yellow').count(),
        'green': TriageResult.objects.filter(suggested_level='green').count(),
    }
    
    # إحصائيات إضافية
    new_today = PatientCase.objects.filter(created_at__gte=today_start).count()
    total_patients = User.objects.filter(user_type='patient').count()
    new_patients_month = User.objects.filter(
        user_type='patient',
        date_joined__year=now.year,
        date_joined__month=now.month
    ).count()
    
    # عدد الحالات الواردة (للسايدبار)
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    context = {
        'pending_cases': pending_cases,
        'reviewed_today': reviewed_today,
        'urgent_cases': urgent_cases,
        'appointments_today': appointments_today,
        'recent_cases': recent_cases_list,
        'today_appointments': today_appointments,
        'triage_counts': triage_counts,
        'new_today': new_today,
        'total_patients': total_patients,
        'new_patients_month': new_patients_month,
        'incoming_count': incoming_count,
        'now': now,
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
def incoming_cases(request):
    """List all incoming cases with filters"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    # Get filter parameters
    priority = request.GET.get('priority', 'all')
    sort = request.GET.get('sort', 'newest')
    page = request.GET.get('page', 1)
    
    # Base queryset
    cases = PatientCase.objects.filter(is_processed=False).select_related('patient')
    
    # Apply priority filter
    if priority != 'all':
        cases = cases.filter(triage_result__suggested_level=priority)
    
    # Apply sorting
    if sort == 'newest':
        cases = cases.order_by('-created_at')
    elif sort == 'oldest':
        cases = cases.order_by('created_at')
    elif sort == 'priority':
        cases = cases.order_by('-triage_result__composite_score')
    
    # Get triage results for each case
    cases_list = []
    for case in cases:
        try:
            triage = TriageResult.objects.get(case=case)
        except TriageResult.DoesNotExist:
            triage = None
        cases_list.append({
            'id': case.id,
            'case': case,
            'triage_result': triage
        })
    
    # Pagination
    paginator = Paginator(cases_list, 10)
    page_obj = paginator.get_page(page)
    
    # عدد الحالات الواردة (للسايدبار)
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    context = {
        'cases': page_obj,
        'total_cases': cases.count(),
        'priority': priority,
        'sort': sort,
        'incoming_count': incoming_count,
    }
    return render(request, 'dashboard/incoming_cases.html', context)

@login_required
def case_detail(request, case_id):
    """View and manage case details"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    # Get case with related data
    case = get_object_or_404(
        PatientCase.objects.select_related('patient'),
        id=case_id
    )
    
    # Get triage result
    try:
        triage_result = TriageResult.objects.get(case=case)
    except TriageResult.DoesNotExist:
        triage_result = None
    
    # Get all images
    images = CaseImage.objects.filter(case=case)
    
    # Get patient's history
    patient_cases = PatientCase.objects.filter(
        patient=case.patient
    ).exclude(id=case.id).select_related('patient').order_by('-created_at')[:5]
    
    # عدد الحالات الواردة (للسايدبار)
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    context = {
        'case': case,
        'triage_result': triage_result,
        'images': images,
        'patient_cases': patient_cases,
        'incoming_count': incoming_count,
    }
    return render(request, 'dashboard/case_detail.html', context)

@login_required
def reviewed_cases(request):
    """List all reviewed cases"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    # Get filter parameters
    priority = request.GET.get('priority', 'all')
    sort = request.GET.get('sort', 'newest')
    page = request.GET.get('page', 1)
    
    # Base queryset - فقط الحالات التي تمت مراجعتها
    cases = PatientCase.objects.filter(
        is_processed=True,
        triage_result__isnull=False
    ).select_related('patient')
    
    # Apply priority filter
    if priority != 'all':
        cases = cases.filter(triage_result__suggested_level=priority)
    
    # Apply sorting
    if sort == 'newest':
        cases = cases.order_by('-created_at')
    elif sort == 'oldest':
        cases = cases.order_by('created_at')
    elif sort == 'priority':
        cases = cases.order_by('-triage_result__composite_score')
    
    # Get triage results for each case
    cases_list = []
    for case in cases:
        try:
            triage = TriageResult.objects.get(case=case)
        except TriageResult.DoesNotExist:
            triage = None
        cases_list.append({
            'id': case.id,
            'case': case,
            'triage_result': triage
        })
    
    # Pagination
    paginator = Paginator(cases_list, 10)
    page_obj = paginator.get_page(page)
    
    # Count for sidebar
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    context = {
        'cases': page_obj,
        'total_cases': cases.count(),
        'priority': priority,
        'sort': sort,
        'incoming_count': incoming_count,
    }
    
    return render(request, 'dashboard/reviewed_cases.html', context)

@login_required
def update_triage(request, case_id):
    """Update or confirm triage result"""
    if request.user.user_type != 'doctor':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            case = get_object_or_404(PatientCase, id=case_id)
            
            # محاولة الحصول على تحليل الذكاء الاصطناعي للحالة
            # هذا افتراض أن لديك نموذج AIAnalysis مرتبط بالحالة
            try:
                # إذا كان هناك تحليل سابق من الذكاء الاصطناعي
                from ai_analysis.models import AIAnalysis  # عدل حسب اسم التطبيق
                ai_analysis = AIAnalysis.objects.get(case=case)
                nlp_score = ai_analysis.nlp_score
                vision_score = ai_analysis.vision_score
                composite_score = ai_analysis.composite_score
                suggested_level = ai_analysis.suggested_level
            except:
                # إذا لم يكن هناك تحليل، استخدم قيماً افتراضية
                nlp_score = 50.0
                vision_score = 50.0
                composite_score = 50.0
                suggested_level = 'yellow'
            
            # Get or create triage result
            triage, created = TriageResult.objects.get_or_create(
                case=case,
                defaults={
                    'nlp_score': nlp_score,
                    'vision_score': vision_score,
                    'composite_score': composite_score,
                    'suggested_level': suggested_level
                }
            )
            
            # Update triage information
            final_level = data.get('final_level')
            doctor_notes = data.get('notes', '')
            
            if final_level not in ['red', 'yellow', 'green']:
                return JsonResponse({'error': 'Invalid triage level'}, status=400)
            
            triage.final_level = final_level
            triage.reviewed_by = request.user
            triage.reviewed_at = timezone.now()
            triage.doctor_notes = doctor_notes
            triage.save()
            
            # Mark case as processed
            case.is_processed = True
            case.save()
            
            # Create notification for patient
            Notification.objects.create(
                user=case.patient,
                title='Case Reviewed',
                message=f'Your case #{case.id} has been reviewed. Final triage: {final_level.upper()}',
                notification_type='triage_result'
            )
            
            return JsonResponse({'success': True})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def appointments(request):
    """Manage appointments - shows only appointments for this doctor"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    # Get date filter
    date_str = request.GET.get('date', timezone.now().date().isoformat())
    status_filter = request.GET.get('status', 'all')
    
    try:
        filter_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        filter_date = timezone.now().date()
    
    # Calculate previous and next dates
    prev_date = filter_date - timezone.timedelta(days=1)
    next_date = filter_date + timezone.timedelta(days=1)
    today = timezone.now().date()

    # Get appointments
    appointments = Appointment.objects.filter(
        doctor=request.user,
        appointment_date__date=filter_date
    ).select_related('patient').order_by('appointment_date')
    
    if status_filter != 'all':
        appointments = appointments.filter(status=status_filter)
    
    # Calculate counts for summary cards
    pending_count = appointments.filter(status='pending').count()
    confirmed_count = appointments.filter(status='confirmed').count()
    completed_count = appointments.filter(status='completed').count()

    # عدد الحالات الواردة (للسايدبار)
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    context = {
        'appointments': appointments,
        'filter_date': filter_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'today': today,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'completed_count': completed_count,
        'incoming_count': incoming_count,
    }
    return render(request, 'dashboard/appointments.html', context)

@login_required
def update_appointment_status(request, appointment_id):
    """Update appointment status"""
    if request.user.user_type != 'doctor':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            #appointment = get_object_or_404(Appointment, id=appointment_id)
            appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
            
            new_status = data.get('status')
            
            if new_status not in ['confirmed', 'cancelled', 'completed']:
                return JsonResponse({'error': 'Invalid status'}, status=400)
            
            appointment.status = new_status
            appointment.save()
            
            # Notify patient
            Notification.objects.create(
                user=appointment.patient,
                title=f'Appointment {new_status.title()}',
                message=f'Your appointment on {appointment.appointment_date.strftime("%B %d, %Y at %I:%M %p")} has been {new_status}.',
                notification_type='appointment'
            )
            
            return JsonResponse({'success': True})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def patients_list(request):
    """List all patients"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    search = request.GET.get('search', '')
    page = request.GET.get('page', 1)
    
    patients = User.objects.filter(user_type='patient').prefetch_related('cases', 'appointments')
    
    if search:
        patients = patients.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(id__icontains=search)
        )
    
    paginator = Paginator(patients.order_by('-date_joined'), 20)
    page_obj = paginator.get_page(page)
    
    # عدد الحالات الواردة (للسايدبار)
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    context = {
        'patients': page_obj,
        'search': search,
        'incoming_count': incoming_count,
    }
    return render(request, 'dashboard/patients_list.html', context)

@login_required
def patient_history(request, patient_id):
    """View patient's complete history"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    patient = get_object_or_404(User, id=patient_id, user_type='patient')
    
    cases = PatientCase.objects.filter(patient=patient).select_related('patient').order_by('-created_at')
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date')
    
    # عدد الحالات الواردة (للسايدبار)
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    context = {
        'patient': patient,
        'cases': cases,
        'appointments': appointments,
        'incoming_count': incoming_count,
    }
    return render(request, 'dashboard/patient_history.html', context)

# dashboard/views.py
@login_required
def stats(request):

    """View statistics and analytics"""
    if request.user.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor access only.')
        return redirect('home:index')
    
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0)
    week_ago = now - timezone.timedelta(days=7)
    
    # Total counts
    total_patients = User.objects.filter(user_type='patient').count()
    total_cases = PatientCase.objects.count()
    processed_cases = PatientCase.objects.filter(is_processed=True).count()
    total_appointments = Appointment.objects.count()
    pending_appointments = Appointment.objects.filter(status='pending').count()
    
    # New this month
    new_patients_month = User.objects.filter(
        user_type='patient',
        date_joined__gte=month_start
    ).count()
    
    # Monthly active (patients with cases this month)
    monthly_active = PatientCase.objects.filter(
        created_at__gte=month_start
    ).values('patient').distinct().count()
    
    activity_rate = (monthly_active * 100 // total_patients) if total_patients > 0 else 0
    
    # Triage statistics
    triage_stats = {
        'red': TriageResult.objects.filter(suggested_level='red').count(),
        'yellow': TriageResult.objects.filter(suggested_level='yellow').count(),
        'green': TriageResult.objects.filter(suggested_level='green').count(),
    }
    
    # Daily activity for last 7 days
    daily_activity = []
    for i in range(7):
        day = now - timezone.timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        
        cases_count = PatientCase.objects.filter(created_at__range=[day_start, day_end]).count()
        appointments_count = Appointment.objects.filter(created_at__range=[day_start, day_end]).count()
        processed_count = PatientCase.objects.filter(
            updated_at__range=[day_start, day_end],
            is_processed=True
        ).count()
        
        # Calculate activity percentage (max 100)
        max_activity = max(cases_count, appointments_count, 1)
        activity_percentage = min(((cases_count + appointments_count) * 100) // (max_activity * 2), 100)
        
        daily_activity.append({
            'date': day.strftime('%Y-%m-%d'),
            'cases': cases_count,
            'appointments': appointments_count,
            'processed': processed_count,
            'activity_percentage': activity_percentage
        })
    
    # Reverse to show oldest first
    daily_activity.reverse()
    
    # Additional stats (placeholder values - you can calculate these from actual data)
    avg_response_time = "2.5h"
    fastest_response = "30m"
    slowest_response = "6h"
    busiest_day = "Monday"
    peak_hour = "10:00 AM"
    common_triage = max(triage_stats, key=triage_stats.get).title() if any(triage_stats.values()) else "Yellow"
    completion_rate = f"{(processed_cases * 100 // total_cases) if total_cases > 0 else 0}%"
    
    # Count for sidebar
    incoming_count = PatientCase.objects.filter(is_processed=False).count()
    
    # Debug prints
    print(f"DEBUG: total_patients={total_patients}")
    print(f"DEBUG: total_cases={total_cases}")
    print(f"DEBUG: daily_activity length={len(daily_activity)}")
    print(f"DEBUG: triage_stats={triage_stats}")


    # dashboard/views.py - أضف هذه المتغيرات داخل دالة stats

    # Calculate weekly totals
    weekly_cases_total = sum(day['cases'] for day in daily_activity)
    weekly_appointments_total = sum(day['appointments'] for day in daily_activity)
    weekly_cases_avg = round(weekly_cases_total / 7, 1) if daily_activity else 0
    weekly_appointments_avg = round(weekly_appointments_total / 7, 1) if daily_activity else 0

    
    context = {
        'total_patients': total_patients,
        'total_cases': total_cases,
        'processed_cases': processed_cases,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'new_patients_month': new_patients_month,
        'monthly_active': monthly_active,
        'activity_rate': activity_rate,
        'triage_stats': triage_stats,
        'daily_activity': daily_activity,
        'avg_response_time': avg_response_time,
        'fastest_response': fastest_response,
        'slowest_response': slowest_response,
        'busiest_day': busiest_day,
        'peak_hour': peak_hour,
        'common_triage': common_triage,
        'completion_rate': completion_rate,
        'incoming_count': incoming_count,
        'weekly_cases_total': weekly_cases_total,
        'weekly_appointments_total': weekly_appointments_total,
        'weekly_cases_avg': weekly_cases_avg,
        'weekly_appointments_avg': weekly_appointments_avg,
    }
    
    return render(request, 'dashboard/stats.html', context)