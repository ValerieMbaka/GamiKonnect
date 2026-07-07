from django import forms
from django.contrib.auth.models import User, Group

from progression.models import Achievement, Level
from core.models import (
    About,
    Event,
    FeatureCard,
    Footer,
    FooterLink,
    FooterSection,
    NavigationLink,
    ProjectDetail,
    Section,
    SectionHeading,
    SiteStyle,
    Slider,
)
from games.models import Game, Genre, Platform
from notifications.models import Notification, NotificationGroup, NotificationSchedule
from shops.models import Console, GamePricing, Shop

from .models import AdminProfile


class AdminStyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget
            existing_classes = widget.attrs.get('class', '')
            class_names = {name for name in existing_classes.split() if name}

            if isinstance(widget, forms.CheckboxInput):
                class_names.add('form-check-input')
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                class_names.add('form-select')
                if isinstance(widget, forms.SelectMultiple):
                    class_names.add('form-select-multiple')
            else:
                class_names.add('form-control')

            widget.attrs['class'] = ' '.join(sorted(class_names))


class AdminUserUpdateForm(AdminStyledModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class AdminProfileUpdateForm(AdminStyledModelForm):
    class Meta:
        model = AdminProfile
        fields = ['avatar', 'job_title', 'phone_number', 'timezone']


class ProjectDetailForm(AdminStyledModelForm):
    class Meta:
        model = ProjectDetail
        fields = ['title', 'logo', 'short_description', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
        }


class SiteStyleForm(AdminStyledModelForm):
    class Meta:
        model = SiteStyle
        fields = [
            'font_family',
            'custom_font_family',
            'font_size',
            'font_color',
            'background_color',
            'primary_color',
            'secondary_color',
            'link_color',
            'button_color',
            'button_text_color',
        ]
        widgets = {
            'font_color': forms.TextInput(attrs={'type': 'color'}),
            'background_color': forms.TextInput(attrs={'type': 'color'}),
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color'}),
            'link_color': forms.TextInput(attrs={'type': 'color'}),
            'button_color': forms.TextInput(attrs={'type': 'color'}),
            'button_text_color': forms.TextInput(attrs={'type': 'color'}),
        }


class NavigationLinkForm(AdminStyledModelForm):
    class Meta:
        model = NavigationLink
        fields = ['link_text', 'link_icon', 'link', 'order', 'is_active']


class FooterSectionForm(AdminStyledModelForm):
    class Meta:
        model = FooterSection
        fields = ['title', 'order', 'is_active']


class FooterLinkForm(AdminStyledModelForm):
    class Meta:
        model = FooterLink
        fields = ['section', 'link_text', 'link', 'order', 'is_active']


class SectionForm(AdminStyledModelForm):
    class Meta:
        model = Section
        fields = ['name', 'slug', 'description', 'order', 'is_active']


class SectionHeadingForm(AdminStyledModelForm):
    class Meta:
        model = SectionHeading
        fields = ['section', 'badge_text', 'heading', 'content', 'subheading', 'is_active']


class SliderForm(AdminStyledModelForm):
    class Meta:
        model = Slider
        fields = ['title', 'subtitle', 'background_image', 'cta_text', 'cta_link', 'is_active', 'order']


class AboutForm(AdminStyledModelForm):
    class Meta:
        model = About
        fields = [
            'badge_text',
            'heading',
            'content',
            'image',
            'is_active',
            'active_players',
            'competitions',
            'platforms',
            'active_players_count',
            'competitions_count',
            'platforms_count',
        ]


class FeatureCardForm(AdminStyledModelForm):
    class Meta:
        model = FeatureCard
        fields = ['feature_name', 'feature_description', 'feature_icon', 'is_active', 'order']


class EventForm(AdminStyledModelForm):
    class Meta:
        model = Event
        fields = ['title', 'content', 'is_active']


class FooterForm(AdminStyledModelForm):
    class Meta:
        model = Footer
        fields = ['copy_right_text', 'ownership_text', 'is_active']


class GameForm(AdminStyledModelForm):
    class Meta:
        model = Game
        fields = [
            'name',
            'description',
            'image',
            'genres',
            'supported_platforms',
            'is_verified',
            'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Game overview...'}),
            'genres': forms.SelectMultiple(attrs={'class': 'form-select-multiple'}),
            'supported_platforms': forms.SelectMultiple(attrs={'class': 'form-select-multiple'}),
        }


class LevelForm(AdminStyledModelForm):
    class Meta:
        model = Level
        fields = ['name', 'min_xp', 'color_hex', 'badge_image', 'order']
        widgets = {
            'color_hex': forms.TextInput(attrs={'type': 'color'}),
        }


class AchievementForm(AdminStyledModelForm):
    class Meta:
        model = Achievement
        fields = [
            'name',
            'description',
            'category',
            'metric_key',
            'target_value',
            'xp_reward',
            'is_active',
            'is_hidden',
            'badge_image',
        ]


class ShopForm(AdminStyledModelForm):
    class Meta:
        model = Shop
        fields = ['is_approved', 'is_active']


class ConsoleForm(AdminStyledModelForm):
    class Meta:
        model = Console
        fields = ['shop', 'console_type', 'quantity', 'notes']


class GamePricingForm(AdminStyledModelForm):
    class Meta:
        model = GamePricing
        fields = ['shop', 'game', 'price_per_hour', 'is_premium', 'notes']


class NotificationForm(AdminStyledModelForm):
    class Meta:
        model = Notification
        fields = [
            'category',
            'importance',
            'title',
            'message',
            'message_template',
            'is_system',
            'expires_at',
        ]
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
            'message_template': forms.Textarea(attrs={'rows': 4}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class NotificationGroupForm(AdminStyledModelForm):
    class Meta:
        model = NotificationGroup
        fields = ['name', 'description', 'criteria_type', 'criteria_data', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'criteria_data': forms.Textarea(attrs={'rows': 4, 'placeholder': '{"user_ids": [1, 2, 3]}'}),
        }


class NotificationScheduleForm(AdminStyledModelForm):
    class Meta:
        model = NotificationSchedule
        fields = ['notification', 'scheduled_at', 'status', 'sent_at']
        widgets = {
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'sent_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class StaffUserCreateForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select form-select-multiple'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'groups', 'is_superuser']
        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            self.save_m2m()
        return user


class StaffUserEditForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select form-select-multiple'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'groups', 'is_active', 'is_superuser']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
