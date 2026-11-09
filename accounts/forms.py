# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class PatientRegistrationForm(UserCreationForm):
    """نموذج تسجيل المريض"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 05XXXXXXXX'
        })
    )
    national_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your national ID'
        })
    )
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'national_id', 'date_of_birth', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص حقول النموذج
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['username'].help_text = 'Required. 150 characters or fewer.'
        
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password1'].help_text = '''
            <ul class="text-muted small">
                <li>Your password can\'t be too similar to your personal information.</li>
                <li>Your password must contain at least 8 characters.</li>
                <li>Your password can\'t be entirely numeric.</li>
            </ul>
        '''
        
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'patient'
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data['phone_number']
        user.national_id = self.cleaned_data['national_id']
        user.date_of_birth = self.cleaned_data['date_of_birth']
        
        if commit:
            user.save()
        return user