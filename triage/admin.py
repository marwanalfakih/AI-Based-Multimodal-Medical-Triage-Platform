# triage/admin.py
from django.contrib import admin
from .models import TriageResult

@admin.register(TriageResult)
class TriageResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'composite_score', 'suggested_level', 'final_level', 'reviewed_at')
    list_filter = ('suggested_level', 'final_level', 'reviewed_at')
    search_fields = ('case__id', 'case__patient__username')
    readonly_fields = ('created_at',)
    raw_id_fields = ('case', 'reviewed_by')
    
    fieldsets = (
        ('Case', {
            'fields': ('case',)
        }),
        ('AI Scores', {
            'fields': ('nlp_score', 'vision_score', 'composite_score')
        }),
        ('Triage Levels', {
            'fields': ('suggested_level', 'final_level')
        }),
        ('Doctor Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'doctor_notes')
        }),
        ('AI Explanations', {
            'fields': ('nlp_explanation', 'vision_explanation'),
            'classes': ('collapse',)
        }),
    )