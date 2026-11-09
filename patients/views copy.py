# patients/views.py
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import PatientCase, CaseImage, MedicalHistory, Appointment, Notification
from triage.models import TriageResult
from .forms import PatientCaseForm, CaseImageForm, PatientProfileForm, AppointmentForm
import os
from django.conf import settings

import base64
import tempfile
from ai_analysis.services.triage_service import TriageService

@login_required
def patient_dashboard(request):
    """Patient Dashboard - Main page for patients"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    # Get recent cases
    recent_cases = PatientCase.objects.filter(
        patient=request.user
    ).order_by('-created_at')[:5]
    
    # Get statistics
    total_cases = PatientCase.objects.filter(patient=request.user).count()
    pending_cases = PatientCase.objects.filter(
        patient=request.user, 
        is_processed=False
    ).count()
    completed_cases = PatientCase.objects.filter(
        patient=request.user, 
        is_processed=True
    ).count()
    
    # Get triage results for recent cases
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
    
    # Get unread notifications count
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=request.user,
        appointment_date__gte=timezone.now()
    ).order_by('appointment_date')[:3]
    
    context = {
        'recent_cases': cases_with_triage,
        'total_cases': total_cases,
        'pending_cases': pending_cases,
        'completed_cases': completed_cases,
        'unread_notifications': unread_notifications,
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'patients/dashboard.html', context)

@login_required
def new_case(request):
    """Submit a new medical case with support for voice recording"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    if request.method == 'POST':
        form = PatientCaseForm(request.POST, request.FILES)
        
        # Check inputs
        text_description = request.POST.get('text_description', '').strip()
        images = request.FILES.getlist('images')
        voice_base64 = request.POST.get('voice_recording', '')
        
        # Validate at least one input
        if not text_description and not images and not voice_base64:
            messages.error(request, 'Please provide at least one of: description, image, or voice recording.')
            return render(request, 'patients/new_case.html', {'form': form})
        
        if form.is_valid():
            case = form.save(commit=False)
            case.patient = request.user
            case.save()
            
            # Save images
            image_paths = []
            for image in images:
                img = CaseImage.objects.create(case=case, image=image)
                image_paths.append(img.image.path)
            
            # Handle voice recording from base64
            voice_path = None
            if voice_base64 and voice_base64.startswith('data:audio'):
                try:
                    # Extract base64 data
                    header, encoded = voice_base64.split(',', 1)
                    audio_data = base64.b64decode(encoded)
                    
                    # Save to temporary file
                    temp_dir = tempfile.gettempdir()
                    temp_filename = f"voice_case_{case.id}.wav"
                    temp_path = os.path.join(temp_dir, temp_filename)
                    
                    with open(temp_path, 'wb') as f:
                        f.write(audio_data)
                    
                    # Save to case model
                    case.voice_recording.save(temp_filename, open(temp_path, 'rb'))
                    voice_path = case.voice_recording.path
                    
                    # Clean up temp file
                    os.remove(temp_path)
                    
                except Exception as e:
                    print(f"Error saving voice recording: {e}")
            
            # Run AI Analysis
            try:
                triage_service = TriageService()
                
                analysis_result = triage_service.analyze_case(
                    text=text_description if text_description else None,
                    image_paths=image_paths if image_paths else None,
                    audio_path=voice_path if voice_path else None
                )
                
                # Save triage result
                from triage.models import TriageResult
                TriageResult.objects.create(
                    case=case,
                    nlp_score=analysis_result['nlp_score'],
                    vision_score=analysis_result['vision_score'],
                    composite_score=analysis_result['composite_score'],
                    suggested_level=analysis_result['suggested_level'],
                    nlp_explanation={'score': analysis_result['nlp_score']},
                    vision_explanation={
                        'injury_type': analysis_result['vision_injury'],
                        'affected_areas': analysis_result['vision_affected_areas']
                    }
                )
                
                case.is_processed = True
                case.save()
                
                # Success message
                used_inputs = []
                if text_description:
                    used_inputs.append("text")
                if images:
                    used_inputs.append(f"{len(images)} image(s)")
                if voice_path:
                    used_inputs.append("voice recording")
                
                messages.success(
                    request, 
                    f'✅ Case submitted successfully! AI analysis used: {", ".join(used_inputs)}. '
                    f'Triage: {analysis_result["suggested_level"].upper()}'
                )
                
            except Exception as e:
                messages.warning(request, f'Case saved but AI analysis encountered an issue: {str(e)}')
            
            return redirect('patients:case_detail', case_id=case.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientCaseForm()
    
    return render(request, 'patients/new_case.html', {'form': form})

@login_required
def my_cases(request):
    """View all patient cases"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    # Filter cases
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    cases = PatientCase.objects.filter(patient=request.user)
    
    if status_filter == 'pending':
        cases = cases.filter(is_processed=False)
    elif status_filter == 'completed':
        cases = cases.filter(is_processed=True)
    
    if search_query:
        cases = cases.filter(
            Q(text_description__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(cases.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get triage results for each case
    cases_with_triage = []
    for case in page_obj:
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
    
    context = {
        'cases': cases_with_triage,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_cases': cases.count(),
    }
    return render(request, 'patients/my_cases.html', context)

@login_required
def case_detail(request, case_id):
    """View detailed case information"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    # جلب الحالة
    case = get_object_or_404(PatientCase, id=case_id, patient=request.user)
    
    # جلب نتيجة التصنيف إن وجدت
    try:
        triage_result = TriageResult.objects.get(case=case)
    except TriageResult.DoesNotExist:
        triage_result = None
    
    # جلب جميع الصور المرتبطة بالحالة
    images = case.images.all()
    
    context = {
        'case': case,
        'triage_result': triage_result,
        'images': images,
    }
    return render(request, 'patients/case_detail.html', context)

@login_required
def edit_case(request, case_id):
    """Edit an existing case"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    case = get_object_or_404(PatientCase, id=case_id, patient=request.user)
    
    # منع تعديل الحالات التي تمت معالجتها
    if case.is_processed:
        messages.error(request, 'Cannot edit a processed case.')
        return redirect('patients:case_detail', case_id=case.id)
    
    if request.method == 'POST':
        form = PatientCaseForm(request.POST, request.FILES, instance=case)
        if form.is_valid():
            form.save()
            
            # Handle new images
            images = request.FILES.getlist('images')
            for image in images:
                CaseImage.objects.create(case=case, image=image)
            
            messages.success(request, 'Case updated successfully.')
            return redirect('patients:case_detail', case_id=case.id)
    else:
        form = PatientCaseForm(instance=case)
    
    # جلب الصور الموجودة
    existing_images = case.images.all()
    
    context = {
        'form': form,
        'case': case,
        'existing_images': existing_images,
    }
    return render(request, 'patients/edit_case.html', context)

@login_required
def delete_case(request, case_id):
    """Delete a case"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    case = get_object_or_404(PatientCase, id=case_id, patient=request.user)
    
    # منع حذف الحالات التي تمت معالجتها
    if case.is_processed:
        messages.error(request, 'Cannot delete a processed case.')
        return redirect('patients:my_cases')
    
    if request.method == 'POST':
        # حذف الصور من المجلد (اختياري)
        for image in case.images.all():
            if image.image:
                if os.path.isfile(image.image.path):
                    os.remove(image.image.path)
        
        # حذف التسجيل الصوتي من المجلد (اختياري)
        if case.voice_recording:
            if os.path.isfile(case.voice_recording.path):
                os.remove(case.voice_recording.path)
        
        # حذف الحالة
        case.delete()
        
        messages.success(request, 'Case deleted successfully.')
        return redirect('patients:my_cases')
    
    context = {
        'case': case,
    }
    return render(request, 'patients/delete_case.html', context)

@login_required
def medical_history(request):
    """View patient's medical history"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    # جلب التاريخ الطبي للمريض
    history_list = MedicalHistory.objects.filter(patient=request.user).order_by('-date')
    
    # تجهيز الإحصائيات
    total_records = history_list.count()
    
    # تجهيز السنوات المتاحة للتصفية
    years = []
    for record in history_list:
        if record.date.year not in years:
            years.append(record.date.year)
    
    context = {
        'history_list': history_list,
        'total_records': total_records,
        'years': sorted(years, reverse=True),
    }
    return render(request, 'patients/medical_history.html', context)

@login_required
def my_appointments(request):
    """View patient's appointments"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    # Get filter from request
    filter_type = request.GET.get('filter', 'upcoming')
    now = timezone.now()
    
    # Base queryset
    appointments = Appointment.objects.filter(patient=request.user)
    
    # Apply filter
    if filter_type == 'upcoming':
        appointments = appointments.filter(appointment_date__gte=now).order_by('appointment_date')
    elif filter_type == 'past':
        appointments = appointments.filter(appointment_date__lt=now).order_by('-appointment_date')
    else:  # all
        appointments = appointments.order_by('-appointment_date')
    
    context = {
        'appointments': appointments,
        'filter_type': filter_type,
        'now': now,
    }
    return render(request, 'patients/appointments.html', context)

@login_required
def new_appointment(request):
    """Request a new appointment"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = request.user
            appointment.status = 'pending'  # حالة افتراضية
            appointment.save()
            
            # إنشاء إشعار للمريض
            Notification.objects.create(
                user=request.user,
                title='Appointment Request Submitted',
                message=f'Your appointment request for {appointment.appointment_date.strftime("%B %d, %Y at %I:%M %p")} has been submitted successfully. You will be notified once confirmed.',
                notification_type='appointment'
            )
            
            messages.success(request, 'Appointment request submitted successfully! You will be notified once confirmed.')
            return redirect('patients:my_appointments')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AppointmentForm()
    
    # جلب المواعيد القادمة للمريض (للعرض في الصفحة)
    upcoming_appointments = Appointment.objects.filter(
        patient=request.user,
        appointment_date__gte=timezone.now()
    ).order_by('appointment_date')[:3]
    
    context = {
        'form': form,
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'patients/new_appointment.html', context)

@login_required
def appointment_detail(request, appointment_id):
    """View appointment details"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    
    context = {
        'appointment': appointment,
        'now': timezone.now(),
    }
    return render(request, 'patients/appointment_detail.html', context)

@login_required
def cancel_appointment(request, appointment_id):
    """Cancel an appointment (AJAX endpoint)"""
    if request.user.user_type != 'patient':
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    
    if request.method == 'POST':
        # Only pending or confirmed appointments can be cancelled
        if appointment.status in ['pending', 'confirmed']:
            appointment.status = 'cancelled'
            appointment.save()
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                title='Appointment Cancelled',
                message=f'Your appointment on {appointment.appointment_date.strftime("%B %d, %Y")} has been cancelled.',
                notification_type='appointment'
            )
            
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({
                'status': 'error', 
                'message': f'Cannot cancel appointment with status: {appointment.status}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def reschedule_appointment(request, appointment_id):
    """Reschedule an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.status = 'pending'  # Reset status to pending
            appointment.save()
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                title='Appointment Rescheduled',
                message=f'Your appointment has been rescheduled to {appointment.appointment_date.strftime("%B %d, %Y at %I:%M %p")}.',
                notification_type='appointment'
            )
            
            messages.success(request, 'Appointment rescheduled successfully.')
            return redirect('patients:my_appointments')
    else:
        form = AppointmentForm(instance=appointment)
    
    context = {
        'form': form,
        'appointment': appointment,
    }
    return render(request, 'patients/reschedule_appointment.html', context)


@login_required
def patient_settings(request):
    """Patient settings page"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied. Patient access only.')
        return redirect('home:index')
    
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('patients:patient_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientProfileForm(instance=request.user)
    
    # جلب إحصائيات سريعة
    total_cases = PatientCase.objects.filter(patient=request.user).count()
    total_appointments = Appointment.objects.filter(patient=request.user).count()
    
    context = {
        'form': form,
        'total_cases': total_cases,
        'total_appointments': total_appointments,
    }

    return render(request, 'patients/settings.html', context)

@login_required
def notifications(request):
    """View all notifications"""
    notifications_list = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read
    if request.GET.get('mark_all_read'):
        notifications_list.filter(is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('patients:notifications')
    
    # Pagination
    paginator = Paginator(notifications_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    unread_count = notifications_list.filter(is_read=False).count()
    total_count = notifications_list.count()
    
    context = {
        'notifications': page_obj,
        'unread_count': unread_count,
        'total_count': total_count,
        'page_obj': page_obj,
    }
    return render(request, 'patients/notifications.html', context)

@login_required
def mark_notification_read(request, notif_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notif_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'success'})

@login_required
def update_profile(request):
    """AJAX endpoint for profile updates"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user = request.user
        field = request.POST.get('field')
        value = request.POST.get('value')
        
        if field and hasattr(user, field):
            setattr(user, field, value)
            user.save()
            return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_account(request):
    """حذف حساب المستخدم مع جميع بياناته"""
    if request.method == 'POST':
        user = request.user
        
        # تسجيل الخروج أولاً
        logout(request)
        
        # حذف المستخدم (سيحذف كل المرتبط به)
        user.delete()
        
        messages.success(request, 'Your account has been successfully deleted.')
        return redirect('home:index')
    
    return render(request, 'patients/delete_account.html')