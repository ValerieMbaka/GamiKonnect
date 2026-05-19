"""
Forms for the feeds app.
Handles post creation, media uploads, and comments.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Post, PostMedia, Comment


class PostForm(forms.ModelForm):
    """Form for creating a new post with optional text content."""
    
    class Meta:
        model = Post
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What\'s on your mind, gamer?',
                'maxlength': '5000',
            }),
        }
    
    def clean_content(self):
        """Ensure content or media will be provided."""
        content = self.cleaned_data.get('content', '').strip()
        # Additional validation can be added here
        # (e.g., checking if media is also empty in the view)
        return content


class PostMediaForm(forms.ModelForm):
    """Form for uploading media to a post."""
    
    # Use choice field to let user select image or video
    media_type_select = forms.ChoiceField(
        choices=[('image', 'Image'), ('video', 'Video')],
        widget=forms.RadioSelect(),
        required=True,
        label="What are you uploading?"
    )
    
    class Meta:
        model = PostMedia
        fields = ['image_file', 'video_file']
        widgets = {
            'image_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/gif,image/webp',
                'data-max-size': '3145728',  # 3MB in bytes
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/mp4,video/webm,video/quicktime,video/x-msvideo',
                'data-max-size': '10485760',  # 10MB in bytes
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make both fields not required here; validation happens in view
        self.fields['image_file'].required = False
        self.fields['video_file'].required = False
    
    def clean(self):
        """Ensure exactly one of image or video is provided."""
        cleaned_data = super().clean()
        image = cleaned_data.get('image_file')
        video = cleaned_data.get('video_file')
        
        if image and video:
            raise ValidationError("Upload either an image or video, not both.")
        
        if not image and not video:
            raise ValidationError("Upload at least one image or video.")
        
        return cleaned_data


class CommentForm(forms.ModelForm):
    """Form for creating a comment on a post."""
    
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
                'placeholder': 'Add a comment...',
                'maxlength': '1000',
            }),
        }
    
    def clean_content(self):
        """Ensure comment is not empty."""
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise ValidationError("Comment cannot be empty.")
        return content
