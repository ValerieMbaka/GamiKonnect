import datetime
from django.db import models
from django.utils import timezone


class Account(models.Model):
    # Personal Information
    uid = models.CharField(max_length=255, unique=True, verbose_name="Firebase UID")
    first_name = models.CharField(max_length=255, blank=False, null=False)
    last_name = models.CharField(max_length=255, blank=False, null=False)
    email = models.EmailField(max_length=150, unique=True, verbose_name="Email Address", blank=False, null=False)
    phone = models.CharField(max_length=15, blank=False, null=False, unique=True, verbose_name="Phone Number")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Gamer(Account):
    # Additional Gamer-specific personal information
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    custom_username = models.CharField(max_length=30, unique=True, blank=True, null=True,
                                       verbose_name="Custom Username")
    bio = models.TextField(blank=False, default="Bio")
    about = models.TextField(blank=True, default="About")
    date_of_birth = models.DateField(null=False, default=datetime.date(2025, 1, 1))
    location = models.CharField(max_length=255, blank=False, default="")
    platforms = models.JSONField(default=list)
    games = models.ManyToManyField('games.Game', related_name='gamers', blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    profile_completed = models.BooleanField(default=False)
    points = models.PositiveIntegerField(default=0,
                                         help_text="User's total points earned from gaming activities")
    
    class Meta:
        verbose_name = 'Gamer'
        verbose_name_plural = 'Gamers'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ShopOwner(Account):
    # ShopOwner specific fields
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Shop Owner'
        verbose_name_plural = 'Shop Owners'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class PendingRegistration(models.Model):
    """
    Stores registration details until the user verifies their email in Firebase.
    After successful verification, create the actual Account and role-specific record,
    then delete the PendingRegistration entry.
    """
    uid = models.CharField(max_length=255, unique=True, verbose_name="Firebase UID")
    email = models.EmailField(max_length=150, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=(('gamer', 'Gamer'), ('shop_owner', 'Shop Owner')))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pending Registration'
        verbose_name_plural = 'Pending Registrations'
    
    def __str__(self):
        return f"{self.email} ({self.role})"