from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from .models import Shop
from core.email_service import EmailManager


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'is_approved', 'is_active', 'created_at')
    list_filter = ('is_approved', 'is_active')
    search_fields = ('name', 'location', 'submitted_by_email')
    
    # Register the custom dropdown actions
    actions = ['approve_shops', 'reject_shops']
    
    def save_model(self, request, obj, form, change):
        """Handles manual state changes inside the individual shop edit page"""
        if change:
            old_shop = Shop.objects.get(pk=obj.pk)
            
            # If the admin just changed 'is_approved' from False to True
            if not old_shop.is_approved and obj.is_approved:
                obj.is_active = True
                if hasattr(obj, 'approved_at'):
                    obj.approved_at = timezone.now()
                EmailManager.send_shop_approval(obj, approved=True)
            
            # If the admin just revoked the approval (True to False)
            elif old_shop.is_approved and not obj.is_approved:
                obj.is_active = False
                EmailManager.send_shop_approval(obj, approved=False)
        
        # Proceed with saving the object to the database
        super().save_model(request, obj, form, change)
    
    @admin.action(description='Approve selected shops')
    def approve_shops(self, request, queryset):
        """Allows 1-click approval from the main list view"""
        count = 0
        for shop in queryset.filter(is_approved=False):
            shop.is_approved = True
            shop.is_active = True
            if hasattr(shop, 'approved_at'):
                shop.approved_at = timezone.now()
            shop.save(update_fields=['is_approved', 'is_active', 'approved_at'])
            
            # Trigger the approval email
            EmailManager.send_shop_approval(shop, approved=True)
            count += 1
        
        self.message_user(request, f"Successfully approved {count} shop(s).", messages.SUCCESS)
    
    @admin.action(description='Reject selected pending shops')
    def reject_shops(self, request, queryset):
        """Allows explicitly triggering rejection emails for pending shops"""
        count = 0
        # Only process shops that are currently pending/unapproved
        for shop in queryset.filter(is_approved=False):
            
            # Trigger the rejection email using your EmailManager
            email_sent = EmailManager.send_shop_approval(shop, approved=False)
            
            if email_sent:
                count += 1
        
        self.message_user(
            request,
            f"Successfully processed {count} shop(s) and sent rejection notifications.",
            messages.SUCCESS
        )