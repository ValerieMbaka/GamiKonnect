import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator

from core.views import base_site_context
from accounts.models import Gamer
from games.models import Game
from .models import Level, Achievement, GamerAchievement, GamerLevel
from .services import (
    get_global_leaderboard,
    get_game_leaderboard,
    get_gamer_global_rank,
    get_gamer_game_rank,
)

logger = logging.getLogger(__name__)

TOP_N = 10  # Number of gamers shown in the widget


# ---------------------------------------------------------------------------
# Access Helpers
# ---------------------------------------------------------------------------

def get_gamer(request):
    """Returns the Gamer for the current session, or None."""
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        return None
    try:
        return Gamer.objects.get(id=request.session['user_id'])
    except Gamer.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Global Leaderboard
# ---------------------------------------------------------------------------

def leaderboard_global(request):
    """
    Full global leaderboard — all gamers ranked by total XP.
    Includes the current gamer's rank if logged in.
    """
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')

    gamer = get_gamer(request)

    all_gamers = get_global_leaderboard()

    # Pagination
    paginator = Paginator(all_gamers, 25)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    # Current gamer's rank
    gamer_rank = None
    if gamer:
        gamer_rank = get_gamer_global_rank(gamer)

    # Top 10 for widget
    top_10 = list(get_global_leaderboard(limit=TOP_N))

    # All games that have competition results (for per-game filter)
    games_with_competitions = Game.objects.filter(
        competitions__results__verified=True
    ).distinct().order_by('name')

    context = {
        **base_site_context(),
        'gamer': gamer,
        'profile_complete': gamer.profile_completed if gamer else False,
        'has_owner_access': False,
        'leaderboard': page,
        'top_10': top_10,
        'gamer_rank': gamer_rank,
        'total_gamers': paginator.count,
        'all_levels': Level.objects.all().order_by('order'),
        'games_with_competitions': games_with_competitions,
        'leaderboard_type': 'global',
        'selected_game': None,
    }
    return render(request, 'progression/leaderboard_global.html', context)


# ---------------------------------------------------------------------------
# Per-Game Leaderboard
# ---------------------------------------------------------------------------

def leaderboard_game(request, game_id):
    """
    Per-game leaderboard — gamers ranked by XP earned from a specific game.
    """
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')

    gamer = get_gamer(request)
    game = get_object_or_404(Game, id=game_id)

    all_results = get_game_leaderboard(game)

    # Pagination
    paginator = Paginator(all_results, 25)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    # Current gamer's game rank
    gamer_rank = None
    if gamer:
        gamer_rank = get_gamer_game_rank(gamer, game)

    # Top 10 for widget
    top_10 = get_game_leaderboard(game, limit=TOP_N)

    games_with_competitions = Game.objects.filter(
        competitions__results__verified=True
    ).distinct().order_by('name')

    context = {
        **base_site_context(),
        'gamer': gamer,
        'profile_complete': gamer.profile_completed if gamer else False,
        'has_owner_access': False,
        'leaderboard': page,
        'top_10': top_10,
        'gamer_rank': gamer_rank,
        'total_gamers': paginator.count,
        'all_levels': Level.objects.all().order_by('order'),
        'games_with_competitions': games_with_competitions,
        'leaderboard_type': 'game',
        'selected_game': game,
    }
    return render(request, 'progression/leaderboard_game.html', context)


# ---------------------------------------------------------------------------
# Top 10 Widget JSON Endpoint
# ---------------------------------------------------------------------------

def leaderboard_top10_api(request):
    """
    Returns top 10 global leaderboard as JSON.
    Used by the gamer dashboard widget via AJAX.
    """
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)

    top_10 = get_global_leaderboard(limit=TOP_N)

    data = []
    for i, g in enumerate(top_10, start=1):
        level = getattr(getattr(g, 'gamer_level', None), 'level', None)
        data.append({
            'rank': i,
            'username': g.custom_username or f"{g.first_name} {g.last_name}".strip(),
            'points': g.points,
            'level_name': level.name if level else '—',
            'level_color': level.color_hex if level else '#35A8F0',
            'profile_picture': g.profile_picture.url if g.profile_picture else None,
        })

    return JsonResponse({'success': True, 'data': data})


# ---------------------------------------------------------------------------
# Gamer Profile — Achievements & Level
# ---------------------------------------------------------------------------

def gamer_progression(request):
    """
    Shows the current gamer's full progression — level, achievements, stats.
    Rendered as a section on the gamer dashboard or public profile.
    """
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')

    gamer = get_gamer(request)
    if not gamer:
        messages.error(request, 'Gamer profile not found.')
        return redirect('core:home')

    # Current level
    try:
        gamer_level = GamerLevel.objects.select_related('level').get(gamer=gamer)
        current_level = gamer_level.level
    except GamerLevel.DoesNotExist:
        gamer_level = None
        current_level = None

    # Next level
    next_level = Level.get_next_level(current_level)

    # XP progress to next level
    xp_for_next = None
    xp_progress_pct = 0
    if current_level and next_level:
        xp_in_tier = gamer.points - current_level.min_xp
        tier_range = next_level.min_xp - current_level.min_xp
        xp_for_next = next_level.min_xp - gamer.points
        xp_progress_pct = min(round((xp_in_tier / tier_range) * 100), 100) if tier_range > 0 else 100

    # Achievements
    earned_achievements = GamerAchievement.objects.filter(
        gamer=gamer
    ).select_related('achievement').order_by('-earned_at')

    # Global rank
    global_rank = get_gamer_global_rank(gamer)

    context = {
        **base_site_context(),
        'gamer': gamer,
        'profile_complete': gamer.profile_completed,
        'has_owner_access': False,
        'gamer_level': gamer_level,
        'current_level': current_level,
        'next_level': next_level,
        'xp_for_next': xp_for_next,
        'xp_progress_pct': xp_progress_pct,
        'earned_achievements': earned_achievements,
        'global_rank': global_rank,
        'all_levels': Level.objects.all().order_by('order'),
    }
    return render(request, 'progression/gamer_progression.html', context)