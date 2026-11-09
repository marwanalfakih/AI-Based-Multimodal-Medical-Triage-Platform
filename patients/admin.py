# patients/admin.py
from django.contrib import admin
from .models import PatientCase, CaseImage, Appointment, Notification

@admin.register(PatientCase)
class PatientCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'created_at', 'is_processed', 'is_sent_to_hospital')
    list_filter = ('is_processed', 'is_sent_to_hospital', 'created_at')
    search_fields = ('patient__username', 'patient__email', 'text_description')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('patient',)
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient',)
        }),
        ('Case Details', {
            'fields': ('text_description', 'voice_recording')
        }),
        ('Status', {
            'fields': ('is_processed', 'is_sent_to_hospital')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CaseImage)
class CaseImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'uploaded_at')
    list_filter = ('uploaded_at',)
    raw_id_fields = ('case',)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'appointment_date', 'appointment_type', 'status')
    list_filter = ('status', 'appointment_type', 'appointment_date')
    search_fields = ('patient__username', 'doctor__username')
    raw_id_fields = ('patient', 'doctor', 'specialization')
    
    fieldsets = (
        ('Patient & Doctor', {
            'fields': ('patient', 'specialization', 'doctor')
        }),
        ('Appointment Details', {
            'fields': ('appointment_date', 'appointment_type', 'notes')
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('user__username', 'title', 'message')