from django.urls import path
from . import views

app_name = 'competitions'

urlpatterns = [

    # -----------------------------------------------------------------------
    # Public / Gamer-Facing URLs
    # -----------------------------------------------------------------------

    # Competition list — browsable by all users
    path(
        '',
        views.competition_list,
        name='list'
    ),

    # -----------------------------------------------------------------------
    # Gamer Dashboard URLs
    # -----------------------------------------------------------------------

    # Gamer's registered competitions overview
    path(
        'my-competitions/',
        views.gamer_competitions,
        name='gamer_competitions'
    ),

    # -----------------------------------------------------------------------
    # Shop Owner URLs
    # -----------------------------------------------------------------------

    # Shop owner's competition overview dashboard
    path(
        'manage/',
        views.shop_owner_competitions,
        name='shop_owner_competitions'
    ),

    # Create a new competition — AJAX POST
    path(
        'manage/create/',
        views.shop_owner_competition_create,
        name='shop_owner_create'
    ),

    # Competition detail — public detail page (MUST BE AFTER STATIC PATHS)
    path(
        '<slug:slug>/',
        views.competition_detail,
        name='detail'
    ),

    # Gamer registration — AJAX POST
    path(
        '<slug:slug>/register/',
        views.competition_register,
        name='register'
    ),

    # Check if gamer is already registered — AJAX GET
    path(
        'api/check-registration/<str:competition_id>/',
        views.check_registration_status,
        name='check_registration'
    ),

    # Gamer's result for a specific completed competition
    path(
        '<slug:slug>/my-result/',
        views.gamer_competition_result,
        name='gamer_result'
    ),

    # Shop owner's detail view for a specific competition
    path(
        'manage/<slug:slug>/',
        views.shop_owner_competition_detail,
        name='shop_owner_detail'
    ),

    # Edit a rejected competition and resubmit — GET (prefill) + POST (submit)
    path(
        'manage/<slug:slug>/edit/',
        views.shop_owner_competition_edit,
        name='shop_owner_edit'
    ),

    # Verify a gamer's unique code on competition day — AJAX POST
    path(
        'manage/<slug:slug>/verify-gamer/',
        views.shop_owner_verify_gamer,
        name='shop_owner_verify_gamer'
    ),

    # Submit check-in list to admin — AJAX POST
    path(
        'manage/<slug:slug>/submit-checkins/',
        views.shop_owner_submit_checkins,
        name='shop_owner_submit_checkins'
    ),

    # Submit final ranked results — AJAX POST
    path(
        'manage/<slug:slug>/submit-results/',
        views.shop_owner_submit_results,
        name='shop_owner_submit_results'
    ),

    # -----------------------------------------------------------------------
    # Admin Action URLs
    # (Called from the custom admin_panel; Django admin is the fallback)
    # -----------------------------------------------------------------------

    # Approve a pending competition — AJAX POST
    path(
        'admin/<int:integer_id>/approve/',
        views.admin_competition_approve,
        name='admin_approve'
    ),

    # Reject a pending competition — AJAX POST
    path(
        'admin/<int:integer_id>/reject/',
        views.admin_competition_reject,
        name='admin_reject'
    ),

    # Confirm check-in list — AJAX POST
    path(
        'admin/<int:integer_id>/confirm-checkins/',
        views.admin_confirm_checkins,
        name='admin_confirm_checkins'
    ),

    # Verify and publish results — AJAX POST
    path(
        'admin/<int:integer_id>/verify-results/',
        views.admin_verify_results,
        name='admin_verify_results'
    ),

    # Full competition data for custom admin panel — GET (JSON)
    path(
        'admin/<int:integer_id>/data/',
        views.admin_competition_detail_data,
        name='admin_detail_data'
    ),
]