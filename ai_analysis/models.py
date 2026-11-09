# ai_analysis/models.py
from django.db import models
from django.conf import settings
from patients.models import PatientCase

class AIAnalysis(models.Model):
    """Store AI analysis results for each case"""
    case = models.OneToOneField(PatientCase, on_delete=models.CASCADE, related_name='ai_analysis')
    
    # NLP Analysis
    nlp_score = models.FloatField(help_text="Severity score from text/voice analysis (0-100)")
    nlp_keywords = models.JSONField(default=list, help_text="Extracted keywords with weights")
    nlp_entities = models.JSONField(default=list, help_text="Medical entities detected")
    
    # Vision Analysis
    vision_score = models.FloatField(help_text="Severity score from image analysis (0-100)")
    vision_affected_areas = models.JSONField(default=list, help_text="Detected affected areas")
    vision_heatmap_path = models.CharField(max_length=500, blank=True, help_text="Path to Grad-CAM heatmap")
    
    # Combined Results
    composite_score = models.FloatField(help_text="Combined severity score (0-100)")
    suggested_level = models.CharField(max_length=10, choices=[
        ('red', 'Emergency'),
        ('yellow', 'Urgent'),
        ('green', 'Non-urgent')
    ])
    
    # XAI Explanations
    nlp_explanation = models.JSONField(default=dict, help_text="Explanation for NLP decision")
    vision_explanation = models.JSONField(default=dict, help_text="Explanation for vision decision")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Analysis"
        verbose_name_plural = "AI Analyses"
    
    def __str__(self):
        return f"AI Analysis for Case #{self.case.id}"