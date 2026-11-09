# patients/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class PatientCase(models.Model):
    """Patient case model"""
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cases')
    text_description = models.TextField(verbose_name="Text Description")
    voice_recording = models.FileField(upload_to='voice_recordings/', null=True, blank=True)
    
    # Status
    is_processed = models.BooleanField(default=False)
    is_sent_to_hospital = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Patient Case"
        verbose_name_plural = "Patient Cases"
    
    def __str__(self):
        return f"Case #{self.id} - {self.patient.username}"

class CaseImage(models.Model):
    """Images for patient cases"""
    case = models.ForeignKey(PatientCase, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='case_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Case Image"
        verbose_name_plural = "Case Images"

class MedicalHistory(models.Model):
    """Patient medical history"""
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medical_history')
    date = models.DateField()
    diagnosis = models.TextField()
    treatment = models.TextField()
    doctor_name = models.CharField(max_length=100)
    hospital = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Medical History"
        verbose_name_plural = "Medical Histories"

class Specialization(models.Model):
    """Doctor specialization"""

    name = models.CharField(
        max_length=100,
        unique=True
    )

    def __str__(self):
        return self.name

class Doctor(models.Model):
    """Doctors"""

    full_name = models.CharField(
        max_length=200
    )

    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.CASCADE,
        related_name='doctors'
    )

    is_available = models.BooleanField(
        default=True
    )

    def __str__(self):
        return (
            f"{self.full_name}"
            f" ({self.specialization})"
        )
    
class Appointment(models.Model):
    """Patient appointments"""
    APPOINTMENT_TYPES = [
        ('checkup', 'Regular Checkup'),
        ('followup', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('consultation', 'Consultation'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    
    specialization = models.ForeignKey('accounts.Specialization', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    #doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_appointments', limit_choices_to={'user_type': 'doctor'})
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments', limit_choices_to={'user_type': 'doctor'})
    appointment_date = models.DateTimeField()
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPES)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['appointment_date']
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
    
    def __str__(self):
        return f"{self.patient.username} - {self.appointment_type} - {self.appointment_date}"

class Notification(models.Model):
    """User notifications"""
    NOTIFICATION_TYPES = [
        ('case_update', 'Case Update'),
        ('appointment', 'Appointment'),
        ('triage_result', 'Triage Result'),
        ('system', 'System'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

