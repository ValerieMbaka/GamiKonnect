from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.utils.text import slugify
from django.db import transaction
import uuid


class Counter(models.Model):
    # Model to track sequential IDs for each model type
    model_name = models.CharField(max_length=50, unique=True, primary_key=True)
    last_id = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Counter'
        verbose_name_plural = 'Counters'
    
    @classmethod
    def get_next_id(cls, model_name):
        # Get the next sequential ID for a model with thread safety
        with transaction.atomic():
            # Lock the counter-row for this model
            counter, created = cls.objects.select_for_update().get_or_create(
                model_name=model_name,
                defaults={'last_id': 0}
            )
            counter.last_id += 1
            counter.save()
            return counter.last_id
    
    def __str__(self):
        return f"{self.model_name}: {self.last_id}"


class PlatformCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integer_id = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Platform Category'
        verbose_name_plural = 'Platform Categories'
        ordering = ['integer_id']
    
    def save(self, *args, **kwargs):
        # Generate integer_id only for new instances
        if not self.integer_id:
            self.integer_id = Counter.get_next_id('PlatformCategory')
        
        if not self.slug:
            self.slug = slugify(self.name)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def game_count(self):
        # Count games available in the platform category
        return Game.objects.filter(supported_platforms__category=self).distinct().count()
    
    game_count.short_description = 'Number of Games'


class Platform(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integer_id = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    category = models.ForeignKey(PlatformCategory, on_delete=models.CASCADE, related_name='platforms')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Platform'
        verbose_name_plural = 'Platforms'
        ordering = ['integer_id']
    
    def save(self, *args, **kwargs):
        # Generate integer_id only for new instances
        if not self.integer_id:
            self.integer_id = Counter.get_next_id('Platform')
        
        if not self.slug:
            self.slug = slugify(self.name)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def game_count(self):
        return self.games.count()
    
    game_count.short_description = 'Games Available'


class Genre(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integer_id = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['integer_id']
    
    def save(self, *args, **kwargs):
        # Generate integer_id only for new instances
        if not self.integer_id:
            self.integer_id = Counter.get_next_id('Genre')
        
        if not self.slug:
            self.slug = slugify(self.name)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def game_count(self):
        return self.games.count()
    
    game_count.short_description = 'Number of Games'


class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integer_id = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    genres = models.ManyToManyField(Genre, related_name='games', blank=True)
    supported_platforms = models.ManyToManyField(Platform, related_name='games', blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='game_images/', blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        ordering = ['integer_id']
    
    def save(self, *args, **kwargs):
        # Generate integer_id only for new instances
        if not self.integer_id:
            self.integer_id = Counter.get_next_id('Game')
        
        if not self.slug:
            self.slug = self.generate_unique_slug()
        
        super().save(*args, **kwargs)
    
    def generate_unique_slug(self):
        slug = slugify(self.name)
        unique_slug = slug
        num = 1
        while Game.objects.filter(slug=unique_slug).exists():
            unique_slug = f'{slug}-{num}'
            num += 1
        return unique_slug
    
    def platform_categories(self):
        # Get all platform categories the game is available on
        return PlatformCategory.objects.filter(
            platforms__games=self
        ).distinct()
    
    def platform_categories_list(self):
        # Get a list of platform categories
        categories = self.platform_categories()
        return ", ".join([category.name for category in categories])
    
    platform_categories_list.short_description = 'Platform Categories'
    
    def __str__(self):
        return self.name