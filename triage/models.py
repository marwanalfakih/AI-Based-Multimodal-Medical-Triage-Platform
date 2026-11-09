# triage/models.py
from django.db import models
from django.conf import settings
from patients.models import PatientCase

class TriageResult(models.Model):
    """نتيجة التصنيف"""
    TRIAGE_LEVELS = (
        ('red', 'أحمر - طارئ'),
        ('yellow', 'أصفر - متوسط'),
        ('green', 'أخضر - غير طارئ'),
    )
    
    case = models.OneToOneField(PatientCase, on_delete=models.CASCADE, related_name='triage_result')
    
    # نتائج التحليل
    nlp_score = models.FloatField(verbose_name="نتيجة تحليل النص", help_text="0-100")
    vision_score = models.FloatField(verbose_name="نتيجة تحليل الصور", help_text="0-100")
    composite_score = models.FloatField(verbose_name="النتيجة المركبة", help_text="0-100")
    
    # التصنيف
    suggested_level = models.CharField(max_length=10, choices=TRIAGE_LEVELS, verbose_name="التصنيف المقترح")
    final_level = models.CharField(max_length=10, choices=TRIAGE_LEVELS, null=True, blank=True, verbose_name="التصنيف النهائي")
    
    # شرح الذكاء الاصطناعي (XAI)
    nlp_explanation = models.JSONField(verbose_name="شرح تحليل النص", default=dict)
    vision_explanation = models.JSONField(verbose_name="شرح تحليل الصور", default=dict)
    
    # قرار الطبيب
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    doctor_notes = models.TextField(blank=True, verbose_name="ملاحظات الطبيب")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "نتيجة تصنيف"
        verbose_name_plural = "نتائج التصنيف"
    
    def __str__(self):
        return f"تصنيف حالة {self.case.id} - {self.get_suggested_level_display()}"