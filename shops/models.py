from django.db import models
from accounts.models import ShopOwner
from games.models import Platform


class Console(models.Model):
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE, related_name='consoles')
    
    console_type = models.ForeignKey(
        Platform,
        on_delete=models.CASCADE,
        limit_choices_to={'category__name': 'Console'},  # Only show console platforms
        related_name='shop_consoles'
    )
    
    quantity = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=255, blank=True, help_text="e.g., Special editions, models, etc.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Console'
        verbose_name_plural = 'Consoles'
        unique_together = ['shop', 'console_type']  # Prevent duplicate console types per shop
    
    def __str__(self):
        return f"{self.console_type.name} x{self.quantity}"


class GamePricing(models.Model):
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE, related_name='game_prices')
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE)
    price_per_hour = models.DecimalField(max_digits=6, decimal_places=2)
    is_premium = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['shop', 'game']
        verbose_name = 'Game Pricing'
        verbose_name_plural = 'Game Pricing'
    
    def __str__(self):
        return f"{self.game.name} - ${self.price_per_hour}/hr"


class Shop(models.Model):
    # Shop details
    name = models.CharField(max_length=255, verbose_name="Shop Name", blank=False, default="")
    logo = models.ImageField(upload_to='shop_logos/', blank=False, null=False, default="shop_logos/placeholder.png")
    description = models.TextField(blank=False, help_text="A brief description of your shop", default="")
    
    # Detailed Location
    city = models.CharField(max_length=100, blank=False, verbose_name="City", default="")
    location = models.CharField(max_length=100, blank=False, verbose_name="Location", default="")
    building = models.CharField(max_length=255, blank=False, default="")
    floor = models.CharField(max_length=50, blank=False, default="")
    room_number = models.CharField(max_length=50, blank=False, default="")
    address = models.CharField(max_length=255, blank=False, help_text="Full address or landmarks", default="")
    
    screen_number = models.PositiveIntegerField(default=0, verbose_name="Number of screens", blank=False)
    base_price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                              blank=False, help_text="Default price for games without specific pricing")
    
    # Verification
    business_permit = models.FileField(upload_to='business_permits/', blank=False, null=False,
                                       help_text="Upload your business permit for verification", default="business_permits/placeholder.pdf")
    
    opening_hours = models.TextField(blank=False, default="Opening Hours")
    closing_hours = models.TextField(blank=False, default="Closing Hours")
    is_active = models.BooleanField(default=True)
    games_available = models.ManyToManyField('games.Game', related_name='shops', blank=True)
    
    owners = models.ManyToManyField(ShopOwner, related_name='shops', blank=True)
    
    # Track submissions prior to admin approval
    submitted_by_uid = models.CharField(max_length=128, blank=True, null=True)
    submitted_by_email = models.EmailField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Shop'
        verbose_name_plural = 'Shops'
    
    def __str__(self):
        return self.name
    
    def owner_names(self):
        return ", ".join([f"{owner.first_name} {owner.last_name}" for owner in self.owners.all()])
    
    owner_names.short_description = 'Owners'
    
    def total_consoles(self):
        return sum(console.quantity for console in self.consoles.all())
    
    total_consoles.short_description = 'Total Consoles'
    
    def console_summary(self):
        consoles = self.consoles.all()
        if not consoles:
            return "No consoles added"
        return ", ".join([f"{console.console_type.name}({console.quantity})" for console in consoles])
    
    console_summary.short_description = 'Console Summary'
    
    def available_console_platforms(self):
        # Get a list of console platform names available at the shop
        return [console.console_type.name for console in self.consoles.all()]
    
    def get_game_price(self, game):
        # Get price for a specific game, fallback to base price if not found
        try:
            pricing = self.game_prices.get(game=game)
            return pricing.price_per_hour
        except GamePricing.DoesNotExist:
            return self.base_price_per_hour
    
    def premium_games_count(self):
        return self.game_prices.filter(is_premium=True).count()
    
    premium_games_count.short_description = 'Premium Games'
    
    def supported_platform_categories(self):
        # Get platform categories supported by the shop based on consoles
        from games.models import PlatformCategory
        return PlatformCategory.objects.filter(
            platforms__shop_consoles__shop=self
        ).distinct()