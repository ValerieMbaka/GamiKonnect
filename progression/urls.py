from django.urls import path
from . import views

app_name = 'progression'

urlpatterns = [

    # -----------------------------------------------------------------------
    # Leaderboards
    # -----------------------------------------------------------------------

    # Global leaderboard — full page
    path(
        'leaderboard/',
        views.leaderboard_global,
        name='leaderboard_global'
    ),

    # Per-game leaderboard — full page
    path(
        'leaderboard/game/<uuid:game_id>/',
        views.leaderboard_game,
        name='leaderboard_game'
    ),

    # Top 10 widget JSON endpoint — for dashboard AJAX
    path(
        'leaderboard/top10/',
        views.leaderboard_top10_api,
        name='leaderboard_top10_api'
    ),

    # -----------------------------------------------------------------------
    # Gamer Progression — level, achievements, stats
    # -----------------------------------------------------------------------

    path(
        'progression/',
        views.gamer_progression,
        name='gamer_progression'
    ),
]