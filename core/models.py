from django.db import models
from django.utils.text import slugify


class ProjectDetail(models.Model):
    title = models.CharField(max_length=50, default="GamiKonnect")
    logo = models.ImageField(upload_to='logo/', blank=True)
    description = models.TextField()
    short_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Project Detail'
        verbose_name_plural = 'Project Details'
    
    def __str__(self):
        return self.title


class NavigationLink(models.Model):
    # Navigation Links
    link_text = models.CharField(max_length=100, default="Home")
    link_icon = models.ImageField(upload_to='nav_icons/', blank=True)
    link = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Navigation Link'
        verbose_name_plural = 'Navigation Links'
        ordering = ['order']
    
    def __str__(self):
        return self.link_text


class FooterSection(models.Model):
    title = models.CharField(max_length=50, default="Quick Links")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Footer Section'
        verbose_name_plural = 'Footer Sections'
        ordering = ['order']
    
    def __str__(self):
        return self.title


class FooterLink(models.Model):
    section = models.ForeignKey(FooterSection, on_delete=models.CASCADE, related_name='links')
    link_text = models.CharField(max_length=100)
    link = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Footer Link'
        verbose_name_plural = 'Footer Links'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.section.title} - {self.link_text}"


class Section(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, help_text="Used to identify sections in code")
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Content Section'
        verbose_name_plural = 'Content Sections'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class SectionHeading(models.Model):
    section = models.OneToOneField(
        Section,
        on_delete=models.CASCADE,
        related_name='heading',
        limit_choices_to={'is_active': True},
        unique=True
    )
    badge_text = models.CharField(max_length=100, blank=True)
    heading = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    subheading = models.CharField(max_length=255, blank=True, help_text="Optional smaller text below heading")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Section Heading'
        verbose_name_plural = 'Section Headings'
        ordering = ['section__order']
    
    def __str__(self):
        return f"{self.section.name} Heading"


class Slider(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.TextField()
    background_image = models.ImageField(upload_to='sliders/')
    cta_text = models.CharField(max_length=100, blank=True)
    cta_link = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Slider'
        verbose_name_plural = 'Sliders'
    
    def __str__(self):
        return self.title


class About(models.Model):
    badge_text = models.CharField(max_length=100, default="WHO WE ARE")
    heading = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='about/', blank=True)
    is_active = models.BooleanField(default=True)
    
    # Statistics fields
    active_players = models.CharField(max_length=50, default="Active Players")
    competitions = models.CharField(max_length=50, default="Competitions")
    platforms = models.CharField(max_length=50, default="Platforms")
    active_players_count = models.CharField(max_length=50, default="10K+")
    competitions_count = models.CharField(max_length=50, default="100+")
    platforms_count = models.CharField(max_length=50, default="4")
    
    class Meta:
        verbose_name = 'About Us'
        verbose_name_plural = 'About Us'
    
    def __str__(self):
        return self.heading


class FeatureCard(models.Model):
    # Feature cards
    feature_name = models.CharField(max_length=50, default="Feature Name i.e Communities")
    feature_description = models.TextField(default="Feature Description")
    feature_icon = models.ImageField(upload_to='features/', blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Feature Card'
        verbose_name_plural = 'Feature Cards'
    
    def __str__(self):
        return self.feature_name


class Game(models.Model):
    # Games fields
    image = models.ImageField(upload_to='games/', blank=True)
    status = models.CharField(max_length=50, default='Trending')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100, default="Sports")
    platform = models.CharField(max_length=100, default="PS4")
    rating = models.FloatField(default=5)
    stats = models.CharField(max_length=50, default='12K+ players')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
    
    def __str__(self):
        return self.name


class Platform(models.Model):
    # Platforms
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='platforms/', blank=True)
    description = models.TextField()
    stats = models.CharField(max_length=50, default='12K+ players')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Platform'
        verbose_name_plural = 'Platforms'
    
    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
    
    def __str__(self):
        return self.title


class Footer(models.Model):
    # Copyright
    copy_right_text = models.CharField(max_length=255, default="© 2025 GamiKonnect. All rights reserved.")
    
    # Ownership
    ownership_text = models.CharField(max_length=255, default="A product by JM | In partnership with Biztimam "
                                                              "Ventures")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Footer'
        verbose_name_plural = 'Footer'
    
    def __str__(self):
        return self.copy_right_text


# Site-wide style customization
class SiteStyle(models.Model):
    FONT_CHOICES = [
        ("Arial", "Arial"),
        ("Roboto", "Roboto"),
        ("Open Sans", "Open Sans"),
        ("Lato", "Lato"),
        ("Montserrat", "Montserrat"),
        ("Poppins", "Poppins"),
        ("Nunito", "Nunito"),
        ("Other", "Other (specify below)")
    ]
    font_family = models.CharField(max_length=50, choices=FONT_CHOICES, default="Roboto")
    custom_font_family = models.CharField(max_length=100, blank=True, help_text="If 'Other', specify font family name.")
    font_color = models.CharField(max_length=20, default="#222222", help_text="Hex color for main text.")
    font_size = models.CharField(max_length=10, default="16px", help_text="CSS font size, e.g. 16px or 1rem.")
    background_color = models.CharField(max_length=20, default="#ffffff", help_text="Hex color for page background.")
    primary_color = models.CharField(max_length=20, default="#007bff", help_text="Primary accent color.")
    secondary_color = models.CharField(max_length=20, default="#6c757d", help_text="Secondary accent color.")
    link_color = models.CharField(max_length=20, default="#007bff", help_text="Link color.")
    button_color = models.CharField(max_length=20, default="#28a745", help_text="Button background color.")
    button_text_color = models.CharField(max_length=20, default="#ffffff", help_text="Button text color.")
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Site Style"
        verbose_name_plural = "Site Styles"
    
    def __str__(self):
        return f"Site Style (updated {self.updated_at:%Y-%m-%d %H:%M})"
    
    def get_font_family(self):
        if self.font_family == "Other" and self.custom_font_family:
            return self.custom_font_family
        return self.font_family
    
    @classmethod
    def get_active(cls):
        return cls.objects.order_by("-updated_at").first()
    
    def as_dict(self):
        return {
            "font_family": self.get_font_family(),
            "font_color": self.font_color,
            "font_size": self.font_size,
            "background_color": self.background_color,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "link_color": self.link_color,
            "button_color": self.button_color,
            "button_text_color": self.button_text_color,
        }