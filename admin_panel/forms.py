from django import forms
from django.contrib.auth.models import User
from .models import AdminProfile

class AdminUserUpdateForm(forms.ModelForm):
    # Handles updates to the core Django User table
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class AdminProfileUpdateForm(forms.ModelForm):
    # Handles updates to the custom AdminProfile extension
    class Meta:
        model = AdminProfile
        fields = ['avatar', 'job_title', 'phone_number', 'timezone']