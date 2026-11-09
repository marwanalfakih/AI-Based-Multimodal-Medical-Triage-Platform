# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Specialization

class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('id', 'username', 'email', 'user_type', 'get_specialization', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number', 'national_id', 'first_name', 'last_name')
    
    def get_specialization(self, obj):
        if obj.specialization:
            return obj.specialization.name
        return '-'
    get_specialization.short_description = 'Specialization'
    
    fieldsets = UserAdmin.fieldsets + (
        ('Personal Information', {
            'fields': ('phone_number', 'national_id', 'date_of_birth')
        }),
        ('Account Type', {
            'fields': ('user_type',),
        }),
        ('Doctor Information', {
            'fields': ('specialization', 'license_number', 'years_of_experience', 
                      'hospital_affiliation', 'consultation_fee', 'bio', 'profile_picture'),
            'classes': ('collapse',),
            'description': 'These fields are only for doctors'
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Personal Information', {
            'fields': ('phone_number', 'national_id', 'date_of_birth')
        }),
        ('Account Type', {
            'fields': ('user_type',),
        }),
    )

admin.site.register(Specialization, SpecializationAdmin)