# patients/forms.py
from django import forms
from .models import PatientCase, CaseImage, Appointment, Doctor
from accounts.models import User, Specialization
from django.utils import timezone

class PatientCaseForm(forms.ModelForm):
    """Form for submitting a new case - all fields are optional, at least one required"""
    
    
    class Meta:
        model = PatientCase
        fields = ['text_description', 'voice_recording']
        widgets = {
            'text_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe your symptoms (optional if you upload images or voice)',
                'style': 'resize: vertical; min-height: 120px;'
            }),
            'voice_recording': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'audio/*',
            }),
        }
        labels = {
            'text_description': 'Symptoms Description (Optional)',
            'voice_recording': 'Voice Recording (Optional)',
        }
        help_texts = {
            'text_description': 'You can skip this if you upload images or voice recording.',
            'voice_recording': 'Record your symptoms (optional). Supported: MP3, WAV, M4A',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # جعل الحقول اختيارية
        self.fields['text_description'].required = False
        self.fields['voice_recording'].required = False
    
    def clean(self):
        """Validate that at least one input is provided"""
        cleaned_data = super().clean()
        text_description = cleaned_data.get('text_description', '').strip()
        voice_recording = self.files.get('voice_recording')
       # images = self.files.getlist('images')
        images = self.files.getlist('images') if hasattr(self, 'files') else []
        
        if not text_description and not voice_recording and not images:
            #raise forms.ValidationError(
             #   'Please provide at least one of: symptoms description, voice recording, or images.'
            #)
            pass
        
        return cleaned_data


class CaseImageForm(forms.ModelForm):
    """Form for individual case images"""
    class Meta:
        model = CaseImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }


class PatientProfileForm(forms.ModelForm):
    """Form for patient profile settings"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'date_of_birth']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 05XXXXXXXX'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'date_of_birth': 'Date of Birth',
        }


class AppointmentForm(forms.ModelForm):
    """Form for booking appointments"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحديث قائمة الدكاترة عند اختيار التخصص
        if 'specialization' in self.data:
            try:
                specialization_id = int(self.data.get('specialization'))
                self.fields['doctor'].queryset = User.objects.filter(
                    user_type='doctor',
                    specialization_id=specialization_id
                )
            except (ValueError, TypeError):
                pass
        else:
            self.fields['doctor'].queryset = User.objects.none()
    
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'specialization', 'doctor','appointment_type', 'notes']
        widgets = {
            'specialization': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_specialization'
            }),
            'doctor': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_doctor'
            }),
            'appointment_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
            }),
            'appointment_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes or specific requirements...',
                'style': 'resize: vertical;'
            }),
        }
        labels = {
            'specialization': 'Specialization',
            'doctor': 'Doctor',
            'appointment_date': 'Preferred Date & Time',
            'appointment_type': 'Appointment Type',
            'notes': 'Additional Notes (optional)',
        }
        help_texts = {
            'appointment_date': 'Select your preferred date and time for the appointment',
            'appointment_type': 'Choose the type of appointment you need',
        }        

    def clean_appointment_date(self):
        """Validate appointment date is in the future"""
        appointment_date = self.cleaned_data.get('appointment_date')
        if appointment_date and appointment_date < timezone.now():
            raise forms.ValidationError('Appointment date must be in the future.')
        return appointment_date