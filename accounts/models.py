# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class Specialization(models.Model):
    """تخصصات الأطباء"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Specialization"
        verbose_name_plural = "Specializations"
    
    def __str__(self):
        return self.name

class User(AbstractUser):
    """نموذج المستخدم الموحد - للمرضى والأطباء والمشرفين"""
    
    USER_TYPES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Administrator'),
    )
    
    # الحقول المشتركة
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='patient')
    phone_number = models.CharField(max_length=15, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # حقول الأطباء (تستخدم فقط إذا user_type = 'doctor')
    specialization = models.ForeignKey(
        Specialization, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='doctors'
    )
    license_number = models.CharField(max_length=50, blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    hospital_affiliation = models.CharField(max_length=200, blank=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    
    # حل مشكلة groups و user_permissions (تجنب التعارض مع auth)
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_('The groups this user belongs to.'),
        related_name="masarak_user_set",
        related_query_name="masarak_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="masarak_user_set",
        related_query_name="masarak_user",
    )
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def is_doctor(self):
        return self.user_type == 'doctor'
    
    @property
    def is_patient(self):
        return self.user_type == 'patient'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin' or self.is_superuser


# إذا كنت تريد نموذج Doctor منفصل، قم بإزالته أو تعليقه لتجنب التعارض
# class Doctor(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
#     ...

'''
class Doctor(models.Model):
    """نموذج منفصل للأطباء - معلومات مهنية متخصصة"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='doctor'
    )
    
    # معلومات المهنة
    specialization = models.ForeignKey(
        Specialization, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='doctors'
    )
    license_number = models.CharField(max_length=50, unique=True, blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    hospital_affiliation = models.CharField(max_length=200, blank=True)
    
    # معلومات إضافية
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='doctor_profiles/', null=True, blank=True)
    
    # التوفر والمواعيد
    is_available = models.BooleanField(default=True)
    working_hours = models.JSONField(default=dict, blank=True)  # {monday: "9-17", tuesday: "9-17"}
    
    # تقييمات
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        indexes = [
            models.Index(fields=['specialization']),
            models.Index(fields=['license_number']),
        ]
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"
    
    @property
    def full_name(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"
    
    '''