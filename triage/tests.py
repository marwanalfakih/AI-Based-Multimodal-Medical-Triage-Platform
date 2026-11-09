# triage/models.py
from django.db import models
from django.conf import settings
from patients.models import PatientCase

class TriageResult(models.Model):
    """Triage Result Model"""
    TRIAGE_LEVELS = (
        ('red', 'Red - Emergency'),
        ('yellow', 'Yellow - Urgent'),
        ('green', 'Green - Non-urgent'),
    )
    
    case = models.OneToOneField(PatientCase, on_delete=models.CASCADE, related_name='triage_result')
    
    # Analysis results - made optional
    nlp_score = models.FloatField(
        verbose_name="NLP Analysis Score", 
        help_text="0-100", 
        null=True, 
        blank=True,
        default=50.0
    )
    vision_score = models.FloatField(
        verbose_name="Vision Analysis Score", 
        help_text="0-100", 
        null=True, 
        blank=True,
        default=50.0
    )
    composite_score = models.FloatField(
        verbose_name="Composite Score", 
        help_text="0-100", 
        null=True, 
        blank=True,
        default=50.0
    )
    
    # Triage classification
    suggested_level = models.CharField(
        max_length=10, 
        choices=TRIAGE_LEVELS, 
        verbose_name="Suggested Triage Level",
        default='yellow'
    )
    final_level = models.CharField(
        max_length=10, 
        choices=TRIAGE_LEVELS, 
        null=True, 
        blank=True, 
        verbose_name="Final Triage Level"
    )
    
    # AI Explanation (XAI)
    nlp_explanation = models.JSONField(
        verbose_name="NLP Analysis Explanation", 
        default=dict, 
        blank=True
    )
    vision_explanation = models.JSONField(
        verbose_name="Vision Analysis Explanation", 
        default=dict, 
        blank=True
    )
    
    # Doctor's decision
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Reviewed By"
    )
    reviewed_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Review Date"
    )
    doctor_notes = models.TextField(
        blank=True, 
        verbose_name="Doctor's Notes"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    
    class Meta:
        verbose_name = "Triage Result"
        verbose_name_plural = "Triage Results"
    
    def __str__(self):
        return f"Case #{self.case.id} - {self.get_suggested_level_display()}"