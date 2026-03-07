from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import PlatformCategory, Game


@require_GET
def get_profile_form_data(request):
    # Returns data required by the gamer profile completion form - games and platform categories for active games
    try:
        categories = list(
            PlatformCategory.objects.all().values('id', 'name')
        )
        games = list(
            Game.objects.filter(is_active=True).values('id', 'name')
        )
        return JsonResponse({
            'success': True,
            'platform_categories': categories,
            'games': games,
        })
    except Exception:
        return JsonResponse({'success': False})
