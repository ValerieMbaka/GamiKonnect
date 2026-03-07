from .models import Gamer, ShopOwner
from core.models import ProjectDetail


def shop_owner_context(request):
    # Context processor for shop owner dashboard pages
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
    # Provide the current gamer object to all templates when logged in as gamer
    context = {}
    if request.session.get('role') == 'gamer' and request.session.get('user_id'):
        gamer = Gamer.objects.filter(id=request.session['user_id']).first()
        if gamer:
            context['gamer'] = gamer
    return context

