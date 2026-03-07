from .models import Gamer, ShopOwner
from core.models import ProjectDetail
from notifications.models import Notification


def shop_owner_context(request):
    """Context processor for shop owner dashboard pages"""
    context = {}

    # Add project_detail to all pages
    project_detail = ProjectDetail.objects.filter(is_active=True).first()
    context['project_detail'] = project_detail

    # Add shop owner info if user is logged in as shop owner
    if request.session.get('role') == 'shop_owner' and request.session.get('user_id'):
        try:
            shop_owner = ShopOwner.objects.get(id=request.session['user_id'])
            context['shop_owner'] = shop_owner
            # Handle profile picture gracefully
            context['shop_owner_avatar'] = getattr(shop_owner, 'profile_picture', None)
        except ShopOwner.DoesNotExist:
            pass

    return context


def gamer_context(request):
    """Provide the current gamer object to all templates when logged in as gamer."""
    context = {}
    if request.session.get('role') == 'gamer' and request.session.get('user_id'):
        gamer = Gamer.objects.filter(id=request.session['user_id']).first()
        if gamer:
            context['gamer'] = gamer
    return context


def notifications_unread_counts(request):
    """Provide unread notification counts for gamer and shop owner dashboards."""
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    context = {}
    if not role or not user_id:
        return context
    if role == 'gamer':
        gamer = Gamer.objects.filter(id=user_id).first()
        if gamer:
            context['gamer_unread_notifications_count'] = Notification.objects.filter(
                recipient_gamer=gamer,
                is_read=False,
                is_deleted=False,
            ).count()
    elif role == 'shop_owner':
        owner = ShopOwner.objects.filter(id=user_id).first()
        if owner:
            context['shop_owner_unread_notifications_count'] = Notification.objects.filter(
                recipient_shop_owner=owner,
                is_read=False,
                is_deleted=False,
            ).count()
    return context

