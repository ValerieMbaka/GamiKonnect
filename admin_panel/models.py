from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class AdminProfile(models.Model):
    # An extension of the default Django User model, specifically for admin staff.
    # The OneToOneField links this exactly to one specific User account.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    
    # Custom Admin Fields
    avatar = models.ImageField(upload_to='admin_avatars/', blank=True, null=True)
    job_title = models.CharField(max_length=100, default="System Administrator")
    phone_number = models.CharField(max_length=20, blank=True, null=True,
                                    help_text="For critical system alerts.")
    timezone = models.CharField(max_length=50, default="UTC", help_text="e.g., UTC, America/New_York")
    
    class Meta:
        verbose_name = 'Admin Profile'
        verbose_name_plural = 'Admin Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Admin Profile"


# Signals for Automation
@receiver(post_save, sender=User)
def manage_admin_profile(sender, instance, created, **kwargs):
    # Automatically creates an AdminProfile whenever a User is granted staff or superuser privileges.
    
    if instance.is_staff or instance.is_superuser:
        AdminProfile.objects.get_or_create(user=instance)