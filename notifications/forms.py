"""Forms for notifications admin interface."""
from django import forms
from .models import Notification, NotificationGroup


class NotificationForm(forms.ModelForm):
    """Form for creating/editing notifications."""
    
    class Meta:
        model = Notification
        fields = ['category', 'importance', 'title', 'message', 'message_template']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Notification message content'
            }),
            'message_template': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Optional: Template with merge fields like {{username}}, {{level}}, {{game}}'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['message_template'].help_text = (
            'Use {{username}}, {{level}}, {{game}}, {{email}} for personalized messages. '
            'If left empty, the message field will be used as-is.'
        )


class NotificationGroupForm(forms.ModelForm):
    """Form for creating/editing notification groups."""
    
    class Meta:
        model = NotificationGroup
        fields = ['name', 'description', 'criteria_type', 'criteria_data', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'criteria_data': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'JSON format. Examples:\n'
                              '{"levels": [1, 2, 3]}\n'
                              '{"games": ["chess", "scrabble"]}\n'
                              '{"user_ids": [5, 10, 15]}\n'
                              '{"competition_id": 42}\n'
                              '{"payment_status": "completed"}'
            }),
        }
    
    def clean_criteria_data(self):
        """Validate that criteria_data is valid JSON."""
        import json
        data = self.cleaned_data.get('criteria_data')
        
        if isinstance(data, dict):
            return data
        
        try:
            if isinstance(data, str):
                return json.loads(data)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")
        
        return data


class BulkNotificationForm(forms.Form):
    """Form for admin bulk notification action."""
    
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Notification title'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Notification message'
        })
    )
    category = forms.ChoiceField(
        choices=Notification._meta.get_field('category').choices
    )
    importance = forms.ChoiceField(
        choices=Notification._meta.get_field('importance').choices,
        help_text='Importance level determines auto-expiry: Critical (90d), High (30d), Medium (14d), Low (7d)'
    )
    
    target_group = forms.ModelChoiceField(
        queryset=NotificationGroup.objects.filter(is_active=True),
        required=False,
        empty_label='-- Select a group --'
    )
    
    target_all_users = forms.BooleanField(
        required=False,
        label='Send to all users (ignores group selection)',
        help_text='Check this to send to all gamers'
    )
    
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        label='Send email notifications'
    )
    
    schedule_for_later = forms.BooleanField(
        required=False,
        label='Schedule for later'
    )
    
    scheduled_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text='Leave blank to send immediately'
    )
