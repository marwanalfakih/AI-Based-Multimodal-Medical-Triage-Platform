# patients/views.py
import os
import base64
import tempfile
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import PatientCase, CaseImage, MedicalHistory, Appointment, Notification, Doctor
from .forms import PatientCaseForm, PatientProfileForm, AppointmentForm
from accounts.models import Specialization, User

# Import AI services
try:
    from ai_analysis.services.triage_service import TriageService
    AI_AVAILABLE = True
except ImportError:
    TriageService = None
    AI_AVAILABLE = False

# Import triage models
try:
    from triage.models import TriageResult
except ImportError:
    TriageResult = None


@login_required
def patient_dashboard(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    recent_cases = PatientCase.objects.filter(patient=request.user).order_by('-created_at')[:5]
    total_cases = PatientCase.objects.filter(patient=request.user).count()
    pending_cases = PatientCase.objects.filter(patient=request.user, is_processed=False).count()
    completed_cases = PatientCase.objects.filter(patient=request.user, is_processed=True).count()
    
    cases_with_triage = []
    for case in recent_cases:
        try:
            if TriageResult:
                triage = TriageResult.objects.get(case=case)
                cases_with_triage.append({'case': case, 'triage': triage})
            else:
                cases_with_triage.append({'case': case, 'triage': None})
        except:
            cases_with_triage.append({'case': case, 'triage': None})
    
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    upcoming_appointments = Appointment.objects.filter(
        patient=request.user, appointment_date__gte=timezone.now()
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


# patients/views.py - دالة new_case المصححة

@login_required
def new_case(request):
    """Submit a new medical case"""
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
            voice_base64 = request.POST.get('voice_recording', '')

            if voice_base64 and voice_base64.startswith('data:audio'):
                try:
                    import base64
                    import tempfile
                    import os
                    
                    header, encoded = voice_base64.split(',', 1)
                    audio_data = base64.b64decode(encoded)
                    temp_dir = tempfile.gettempdir()
                    temp_filename = f"voice_case_{case.id}.wav"
                    temp_path = os.path.join(temp_dir, temp_filename)
                    
                    with open(temp_path, 'wb') as f:
                        f.write(audio_data)
                    
                    case.voice_recording.save(temp_filename, open(temp_path, 'rb'))
                    voice_path = case.voice_recording.path
                    print(f"🎤 Voice recording saved at: {voice_path}")
                    print(f"   File exists: {os.path.exists(voice_path)}")
                    os.remove(temp_path)             
                    
                except Exception as e:
                    print(f"Voice recording error: {e}")
            
            # ========== RUN AI ANALYSIS ==========

            print("="*60)
            print("🚀 ABOUT TO CALL TRIAGE SERVICE")
            print(f"   Images: {len(image_paths)}")
            #print(f"   Text: {bool(analysis_text)}")
            #print(f"   Audio: {bool(analysis_audio)}")
            print("="*60)

            
                
                
                
            
            #--------------------------------------
            try:
                from ai_analysis.services.triage_service import TriageService
                from ai_analysis.services.vision_service import VisionService
                from PIL import Image
                
                triage_service = TriageService()
                vision_service = VisionService()
                
                # Prepare inputs
                analysis_text = text_description if text_description else None
                analysis_images = image_paths if image_paths else None
                analysis_audio = voice_path if voice_path else None
                
                # Run analysis
                analysis_result = triage_service.analyze_case(
                    text=analysis_text,
                    image_paths=analysis_images,
                    audio_path=analysis_audio
                )
                
                # ========== GENERATE VISION DETAILS ==========
                vision_heatmap = None
                vision_all_predictions = {}
                vision_explanation_text = ""
                
                if image_paths and len(image_paths) > 0:
                    try:
                        first_image = Image.open(image_paths[0])
                        heatmap_base64, explanation, all_preds = vision_service.generate_heatmap(first_image)
                        vision_heatmap = heatmap_base64
                        vision_explanation_text = explanation
                        vision_all_predictions = all_preds
                        print(f"✅ Heatmap generated: {len(vision_heatmap) if vision_heatmap else 0} chars")
                        print(f"✅ Predictions: {vision_all_predictions}")
                    except Exception as ve:
                        print(f"Heatmap error: {ve}")
                
                # ========== PREPARE NLP DATA ==========
                nlp_data = {
                    # degree and keywords from NLP service
                    'score': analysis_result.get('nlp_score', 25),
                    'keywords': analysis_result.get('nlp_keywords', []),
                    'explanation': analysis_result.get('nlp_explanation', ''),

                    # details from clinical_nlp 
                    'symptoms': analysis_result.get('symptoms', []),
                    'medications': analysis_result.get('medications', []),
                    'injuries': analysis_result.get('detected_injuries', []),
                    'timing': analysis_result.get('timing', []),
                    'summary': analysis_result.get('clinical_summary', 'No clinical summary available')
                }
                
                # ========== PREPARE VISION DATA ==========
                vision_data = {
                    'injury_type': analysis_result.get('vision_injury', 'unknown'),
                    'confidence': analysis_result.get('vision_confidence', 0),
                    'severity_level': analysis_result.get('severity_level', 'unknown'),
                    'recommended_treatment': analysis_result.get('recommended_treatment', ''),
                    'heatmap': vision_heatmap,
                    'all_predictions': vision_all_predictions,
                    'explanation_text': vision_explanation_text
                }
                
                # ========== SAVE TRIAGE RESULT ==========
                TriageResult.objects.create(
                    case=case,
                    nlp_score=analysis_result.get('nlp_score', 50),
                    vision_score=analysis_result.get('vision_score', 50),
                    composite_score=analysis_result.get('composite_score', 50),
                    suggested_level=analysis_result.get('suggested_level', 'yellow'),
                    nlp_explanation=nlp_data,      # ✅ تخزين بيانات NLP
                    vision_explanation=vision_data  # ✅ تخزين بيانات Vision
                )
                
                # Mark case as processed
                case.is_processed = True
                case.save()
                
                print(f"✅ Triage saved - NLP symptoms: {len(nlp_data['symptoms'])}")
                print(f"   Vision predictions: {len(vision_all_predictions)}")
                
                messages.success(request, f'✅ Case submitted! Triage: {analysis_result.get("suggested_level", "yellow").upper()}')
                
            except Exception as e:
                import traceback
                print(f"AI Analysis Error: {e}")
                traceback.print_exc()
                messages.warning(request, f'Case saved but AI analysis issue.')

                #-------------------------------------------------------------------
            
            return redirect('patients:case_detail', case_id=case.id)
        else:
            messages.error(request, 'Please correct the errors below.')
            print("="*50)
            print("❌ FORM ERRORS:")
            print(form.errors)
            print("="*50)
            print("POST data keys:", list(request.POST.keys()))
            print("FILES data keys:", list(request.FILES.keys()))
            print("="*50)
    else:
        form = PatientCaseForm()
    
    return render(request, 'patients/new_case.html', {'form': form})

@login_required
def my_cases(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    cases = PatientCase.objects.filter(patient=request.user)
    
    if status_filter == 'pending':
        cases = cases.filter(is_processed=False)
    elif status_filter == 'completed':
        cases = cases.filter(is_processed=True)
    
    if search_query:
        cases = cases.filter(Q(text_description__icontains=search_query) | Q(id__icontains=search_query))
    
    paginator = Paginator(cases.order_by('-created_at'), 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    cases_with_triage = []
    for case in page_obj:
        try:
            if TriageResult:
                triage = TriageResult.objects.get(case=case)
                cases_with_triage.append({'case': case, 'triage': triage})
            else:
                cases_with_triage.append({'case': case, 'triage': None})
        except:
            cases_with_triage.append({'case': case, 'triage': None})
    
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
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    case = get_object_or_404(PatientCase, id=case_id, patient=request.user)
    
    triage_result = None
    vision_predictions = {}
    vision_heatmap = None
    vision_explanation = ""
    nlp_data = {}
    
    if TriageResult:
        try:
            triage_result = TriageResult.objects.get(case=case)
            
            # استخراج بيانات الرؤية من JSON
            if triage_result.vision_explanation:
                vision_predictions = triage_result.vision_explanation.get('all_predictions', {})
                vision_heatmap = triage_result.vision_explanation.get('heatmap')
                vision_explanation = triage_result.vision_explanation.get('explanation_text', '')
            
            # استخراج بيانات NLP من JSON
            if triage_result.nlp_explanation:
                nlp_data = triage_result.nlp_explanation
                
        except TriageResult.DoesNotExist:
            pass
    
    context = {
        'case': case,
        'triage_result': triage_result,
        'images': case.images.all(),
        'vision_predictions': vision_predictions,
        'vision_heatmap': vision_heatmap,
        'vision_explanation': vision_explanation,
        'nlp_symptoms': nlp_data.get('symptoms', []),
        'nlp_medications': nlp_data.get('medications', []),
        'nlp_injuries': nlp_data.get('injuries', []),
        'nlp_timing': nlp_data.get('timing', []),
        'nlp_summary': nlp_data.get('summary', ''),
    }
    return render(request, 'patients/case_detail.html', context)


@login_required
def edit_case(request, case_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    case = get_object_or_404(PatientCase, id=case_id, patient=request.user)
    
    if case.is_processed:
        messages.error(request, 'Cannot edit a processed case.')
        return redirect('patients:case_detail', case_id=case.id)
    
    if request.method == 'POST':
        form = PatientCaseForm(request.POST, request.FILES, instance=case)
        if form.is_valid():
            form.save()
            images = request.FILES.getlist('images')
            for image in images:
                CaseImage.objects.create(case=case, image=image)
            messages.success(request, 'Case updated.')
            return redirect('patients:case_detail', case_id=case.id)
    else:
        form = PatientCaseForm(instance=case)
    
    return render(request, 'patients/edit_case.html', {'form': form, 'case': case, 'existing_images': case.images.all()})


@login_required
def delete_case(request, case_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    case = get_object_or_404(PatientCase, id=case_id, patient=request.user)
    
    #if case.is_processed:
     #   messages.error(request, 'Cannot delete a processed case.')
      #  return redirect('patients:my_cases')
    
    if request.method == 'POST':
        for image in case.images.all():
            if image.image and os.path.isfile(image.image.path):
                os.remove(image.image.path)
        if case.voice_recording and os.path.isfile(case.voice_recording.path):
            os.remove(case.voice_recording.path)
        case.delete()
        messages.success(request, 'Case deleted.')
        return redirect('patients:my_cases')
    
    return render(request, 'patients/delete_case.html', {'case': case})


@login_required
def medical_history(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    history = MedicalHistory.objects.filter(patient=request.user).order_by('-date')
    years = list(set([r.date.year for r in history]))
    
    context = {
        'history_list': history,
        'total_records': history.count(),
        'years': sorted(years, reverse=True),
    }
    return render(request, 'patients/medical_history.html', context)


@login_required
def my_appointments(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    filter_type = request.GET.get('filter', 'upcoming')
    now = timezone.now()
    
    appointments = Appointment.objects.filter(patient=request.user)
    if filter_type == 'upcoming':
        appointments = appointments.filter(appointment_date__gte=now).order_by('appointment_date')
    elif filter_type == 'past':
        appointments = appointments.filter(appointment_date__lt=now).order_by('-appointment_date')
    else:
        appointments = appointments.order_by('-appointment_date')
    
    return render(request, 'patients/appointments.html', {'appointments': appointments, 'filter_type': filter_type, 'now': now})


@login_required
def new_appointment(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            apt = form.save(commit=False)
            apt.patient = request.user
            apt.status = 'pending'
            apt.save()
            Notification.objects.create(
                user=request.user,
                title='Appointment Request',
                message=f'Appointment request for {apt.appointment_date.strftime("%B %d, %Y at %I:%M %p")} submitted.',
                notification_type='appointment'
            )
            messages.success(request, 'Appointment request submitted.')
            return redirect('patients:my_appointments')
    else:
        form = AppointmentForm()
    
    upcoming = Appointment.objects.filter(
        patient=request.user, appointment_date__gte=timezone.now()
    ).order_by('appointment_date')[:3]
    
    return render(request, 'patients/new_appointment.html', {'form': form, 'upcoming_appointments': upcoming})


@login_required
def appointment_detail(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    return render(request, 'patients/appointment_detail.html', {'appointment': appointment, 'now': timezone.now()})


@login_required
def cancel_appointment(request, appointment_id):
    if request.user.user_type != 'patient':
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    
    if request.method == 'POST':
        if appointment.status in ['pending', 'confirmed']:
            appointment.status = 'cancelled'
            appointment.save()
            Notification.objects.create(
                user=request.user,
                title='Appointment Cancelled',
                message=f'Appointment on {appointment.appointment_date.strftime("%B %d, %Y")} cancelled.',
                notification_type='appointment'
            )
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Cannot cancel this appointment'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


@login_required
def reschedule_appointment(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            apt = form.save(commit=False)
            apt.status = 'pending'
            apt.save()
            Notification.objects.create(
                user=request.user,
                title='Appointment Rescheduled',
                message=f'Appointment rescheduled to {apt.appointment_date.strftime("%B %d, %Y at %I:%M %p")}.',
                notification_type='appointment'
            )
            messages.success(request, 'Appointment rescheduled.')
            return redirect('patients:my_appointments')
    else:
        form = AppointmentForm(instance=appointment)
    
    return render(request, 'patients/reschedule_appointment.html', {'form': form, 'appointment': appointment})


@login_required
def patient_settings(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('home:index')
    
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('patients:patient_settings')
    else:
        form = PatientProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'total_cases': PatientCase.objects.filter(patient=request.user).count(),
        'total_appointments': Appointment.objects.filter(patient=request.user).count(),
    }
    return render(request, 'patients/settings.html', context)


@login_required
def update_profile(request):
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
def notifications(request):
    notifications_list = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    if request.GET.get('mark_all_read'):
        notifications_list.filter(is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('patients:notifications')
    
    paginator = Paginator(notifications_list, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'notifications': page_obj,
        'unread_count': notifications_list.filter(is_read=False).count(),
        'total_count': notifications_list.count(),
        'page_obj': page_obj,
    }
    return render(request, 'patients/notifications.html', context)


@login_required
def mark_notification_read(request, notif_id):
    notification = get_object_or_404(Notification, id=notif_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})


@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Account deleted.')
        return redirect('home:index')
    return render(request, 'patients/delete_account.html')


@login_required
def load_doctors(request):
    """AJAX endpoint to load doctors based on specialization"""
    specialization_id = request.GET.get('specialization')
    
    if specialization_id:
        # فلترة الأطباء حسب التخصص المختار
        doctors = User.objects.filter(
            user_type='doctor',
            specialization_id=specialization_id
        ).values('id', 'first_name', 'last_name')
        
        doctors_list = list(doctors)
        
        # تنسيق اسم الدكتور
        for doctor in doctors_list:
            doctor['name'] = f"Dr. {doctor['first_name']} {doctor['last_name']}".strip()
            if not doctor['name'].strip() or doctor['name'] == 'Dr. ':
                doctor['name'] = f"Dr. {doctor['id']}"
        
        return JsonResponse({'doctors': doctors_list})
    
    return JsonResponse({'doctors': []})

   