from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from .models import Competition, CompetitionRegistration, CompetitionResult


# Inlines
class CompetitionRegistrationInline(admin.TabularInline):
    model = CompetitionRegistration
    extra = 0
    readonly_fields = [
        'gamer', 'unique_code', 'registered_at',
        'checked_in', 'checked_in_at', 'code_expired', 'is_cancelled',
        'payment_status', 'payment_phone_number', 'paid_at',
    ]
    fields = [
        'gamer', 'unique_code', 'registered_at',
        'payment_status', 'payment_phone_number', 'paid_at',
        'checked_in', 'checked_in_at', 'code_expired', 'is_cancelled',
    ]
    can_delete = False
    show_change_link = False
    verbose_name = 'Registered Gamer'
    verbose_name_plural = 'Registered Gamers'


class CompetitionResultInline(admin.TabularInline):
    model = CompetitionResult
    extra = 0
    readonly_fields = [
        'gamer', 'rank', 'points_awarded', 'is_no_show',
        'auto_allocated', 'verified', 'verified_at',
    ]
    fields = [
        'gamer', 'rank', 'points_awarded', 'is_no_show',
        'auto_allocated', 'verified', 'verified_at',
    ]
    can_delete = False
    show_change_link = False
    verbose_name = 'Result'
    verbose_name_plural = 'Results'


# Competition Admin
@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    # List View
    list_display = [
        'integer_id', 'name', 'shop', 'game', 'platform',
        'scheduled_time', 'max_participants', 'registered_count_display',
        'prize_type', 'status_badge', 'created_by',
    ]
    list_filter = ['status', 'prize_type', 'age_restricted', 'game', 'platform', 'shop']
    search_fields = ['name', 'shop__name', 'game__name', 'created_by__first_name', 'created_by__last_name']
    ordering = ['-created_at']
    list_per_page = 20

    # Detail View
    readonly_fields = [
        'integer_id', 'slug', 'registered_count_display',
        'created_at', 'updated_at', 'approved_at',
    ]

    fieldsets = (
        ('Identification', {
            'fields': ('integer_id', 'slug'),
        }),
        ('Core Details', {
            'fields': (
                'name', 'description', 'game', 'platform', 'shop',
                'scheduled_time', 'competition_end_time',
                'entry_fee', 'max_participants', 'registered_count_display',
                'age_restricted', 'rules', 'timeline',
            ),
        }),
        ('Registration Window', {
            'description': 'Set by admin during approval. Automated jobs use these timestamps.',
            'fields': ('registration_opens_at', 'registration_closes_at'),
        }),
        ('Prize Configuration', {
            'description': 'Set by admin during approval. Only fill the fields relevant to the selected prize type.',
            'fields': (
                'prize_type',
                # Points
                'points_1st', 'points_2nd', 'points_3rd',
                'points_4_to_10', 'points_beyond_10',
                # Money
                'prize_money_total',
                'prize_money_1st_pct', 'prize_money_2nd_pct', 'prize_money_3rd_pct',
                # Gift
                'prize_gift_description',
            ),
        }),
        ('Ownership & Status', {
            'fields': ('created_by', 'status', 'rejection_reason'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at', 'approved_at'),
        }),
    )

    inlines = [CompetitionRegistrationInline, CompetitionResultInline]

    # Custom Display Methods
    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {
            'draft':                    '#6c757d',  # grey
            'pending':                  '#fd7e14',  # orange
            'rejected':                 '#dc3545',  # red
            'registration':             '#0d6efd',  # blue
            'ongoing':                  '#0dcaf0',  # cyan
            'completed':                '#198754',  # green
        }
        colour = colours.get(obj.status, '#6c757d')
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            colour, label
        )

    @admin.display(description='Registered')
    def registered_count_display(self, obj):
        count = obj.registered_count()
        return format_html(
            '{} / {}',
            count, obj.max_participants
        )

    # Admin Actions
    @admin.action(description='Approve selected competitions')
    def approve_competitions(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='registration',
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} competition(s) approved.')

    @admin.action(description='Mark selected competitions as completed')
    def mark_completed(self, request, queryset):
        updated = queryset.exclude(status='completed').update(status='completed')
        self.message_user(request, f'{updated} competition(s) marked as completed.')

    actions = ['approve_competitions', 'mark_completed']


# Competition Registration Admin
@admin.register(CompetitionRegistration)
class CompetitionRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'gamer', 'competition', 'registered_at',
        'payment_status_badge', 'checked_in', 'checked_in_at', 'is_cancelled',
    ]
    list_filter = ['payment_status', 'checked_in', 'code_expired', 'is_cancelled', 'competition__status', 'registered_at']
    search_fields = [
        'gamer__first_name', 'gamer__last_name',
        'gamer__email', 'competition__name', 'payment_phone_number',
    ]
    ordering = ['-registered_at']
    list_per_page = 25

    readonly_fields = [
        'unique_code', 'registered_at', 'checked_in_at',
        'paid_at', 'participation_hours_display',
    ]

    fieldsets = (
        ('Registration Details', {
            'fields': ('competition', 'gamer', 'unique_code', 'registered_at'),
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'payment_phone_number', 'paid_at'),
        }),
        ('Check-in', {
            'fields': ('checked_in', 'checked_in_at', 'code_expired', 'participation_hours_display'),
        }),
        ('Status', {
            'fields': ('is_cancelled',),
        }),
    )

    @admin.display(description='Payment Status')
    def payment_status_badge(self, obj):
        colours = {
            'pending': '#ffc107',    # yellow
            'processing': '#0dcaf0', # cyan
            'completed': '#198754',  # green
            'failed': '#dc3545',     # red
        }
        colour = colours.get(obj.payment_status, '#6c757d')
        label = obj.get_payment_status_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            colour, label
        )

    @admin.display(description='Participation Hours')
    def participation_hours_display(self, obj):
        hours = obj.participation_hours()
        if hours is not None:
            return f'{hours} hrs'
        return '—'


# Competition Result Admin
@admin.register(CompetitionResult)
class CompetitionResultAdmin(admin.ModelAdmin):

    list_display = [
        'gamer', 'competition', 'rank', 'points_awarded',
        'is_no_show', 'auto_allocated', 'verified', 'verified_at', 'is_win_display',
    ]
    list_filter = ['verified', 'is_no_show', 'auto_allocated', 'competition__prize_type']
    search_fields = [
        'gamer__first_name', 'gamer__last_name',
        'competition__name', 'competition__shop__name',
    ]
    ordering = ['competition', 'rank']
    list_per_page = 25

    readonly_fields = ['auto_allocated', 'verified_at', 'is_win_display']

    fieldsets = (
        ('Result Details', {
            'fields': ('competition', 'gamer', 'rank', 'points_awarded', 'is_no_show'),
        }),
        ('Verification', {
            'fields': ('verified', 'verified_at', 'auto_allocated'),
        }),
        ('Win Status', {
            'fields': ('is_win_display',),
        }),
    )

    @admin.display(description='Win?', boolean=True)
    def is_win_display(self, obj):
        return obj.is_win()