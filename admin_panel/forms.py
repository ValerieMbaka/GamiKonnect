from django import forms
from django.contrib.auth.models import User
from .models import AdminProfile
from core.models import ProjectDetail, SiteStyle
from django import forms
from games.models import Game, Genre, Platform

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
        
class ProjectDetailForm(forms.ModelForm):
    class Meta:
        model = ProjectDetail
        fields = ['title', 'logo', 'short_description', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
        }

class SiteStyleForm(forms.ModelForm):
    class Meta:
        model = SiteStyle
        fields = [
            'font_family', 'custom_font_family', 'font_size',
            'font_color', 'background_color', 'primary_color',
            'secondary_color', 'link_color', 'button_color', 'button_text_color'
        ]
        # Native color picker widgets
        widgets = {
            'font_color': forms.TextInput(attrs={'type': 'color', 'class': 'color-picker'}),
            'background_color': forms.TextInput(attrs={'type': 'color', 'class': 'color-picker'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'color-picker'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'color-picker'}),
            'link_color': forms.TextInput(attrs={'type': 'color', 'class': 'color-picker'}),
            'button_color': forms.TextInput(attrs={'type': 'color', 'class': 'color-picker'}),
            'button_text_color': forms.TextInput(attrs={'type': 'color', 'class': 'color-picker'}),
        }
        
class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = [
            'name', 'description', 'image', 'genres',
            'supported_platforms', 'is_verified', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Game overview...'}),
            'genres': forms.SelectMultiple(attrs={'class': 'form-select-multiple'}),
            'supported_platforms': forms.SelectMultiple(attrs={'class': 'form-select-multiple'}),
        }