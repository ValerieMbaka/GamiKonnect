import logging
from django.db import transaction
from django.utils import timezone
from .models import Competition, CompetitionResult, CompetitionRegistration, CompetitionAuditLog
from .scheduler import schedule_competition_jobs, remove_competition_jobs
from core.email_service import EmailManager
from decimal import Decimal

logger = logging.getLogger(__name__)


class CompetitionService:
    @staticmethod
    @transaction.atomic
    def deploy_competition(competition, performed_by=None, performed_by_label=''):
        """
        Deploy a shop-owner-created competition immediately for gamer registration.
        Admin is notified for ongoing review.
        """
        competition.status = 'registration'
        competition.age_restricted = True
        competition.approved_at = timezone.now()
        if competition.prize_type:
            competition.prize_type = Competition.normalize_prize_type(competition.prize_type)
        competition.save()

        if not competition.registration_opens_at:
            competition.registration_opens_at = (
                competition.scheduled_time - timezone.timedelta(hours=1)
            )
        if not competition.registration_closes_at:
            competition.registration_closes_at = (
                competition.scheduled_time - timezone.timedelta(minutes=40)
            )
        competition.save(update_fields=['registration_opens_at', 'registration_closes_at'])

        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='approve',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details='Competition deployed by shop owner; pending admin review.',
            )
        except Exception:
            logger.exception('Failed to create audit log for deploy')

        schedule_competition_jobs(competition)
        EmailManager.send_competition_submitted(competition)
        EmailManager.send_competition_announced_to_gamers(competition)
        return competition

    @staticmethod
    @transaction.atomic
    def approve_competition(competition, approval_form, performed_by=None, performed_by_label=''):
        competition = approval_form.save(commit=False)
        competition.status = 'registration'
        competition.approved_at = timezone.now()
        competition.rejection_reason = ''
        competition.admin_reviewed = True
        if competition.prize_type:
            competition.prize_type = Competition.normalize_prize_type(competition.prize_type)
        competition.save()
        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='approve',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details='Competition approved via admin panel.',
            )
        except Exception:
            logger.exception('Failed to create audit log for approval')

        schedule_competition_jobs(competition)
        EmailManager.send_competition_approved(competition)
        return competition

    @staticmethod
    @transaction.atomic
    def reject_competition(competition, rejection_form, performed_by=None, performed_by_label=''):
        competition = rejection_form.save(commit=False)
        competition.status = 'rejected'
        competition.save()
        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='reject',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details=f"Rejected: {competition.rejection_reason}",
            )
        except Exception:
            logger.exception('Failed to create audit log for rejection')

        remove_competition_jobs(competition)
        EmailManager.send_competition_rejected(competition)
        return competition

    @staticmethod
    @transaction.atomic
    def suspend_competition(competition, reason, performed_by=None, performed_by_label=''):
        """Suspend a live competition and refund paid registrations."""
        from payments.refunds import RefundService

        if competition.status not in ['registration', 'ongoing', 'pending']:
            raise ValueError(f'Cannot suspend competition in {competition.status} status.')

        competition.status = 'suspended'
        competition.suspension_reason = reason
        competition.suspended_at = timezone.now()
        competition.save()

        refund_results = RefundService.refund_competition_registrations(
            competition,
            reason=reason,
        )

        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='suspend',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details=(
                    f"Suspended: {reason}. "
                    f"Refunded {refund_results['refunded']} registration(s)."
                ),
            )
        except Exception:
            logger.exception('Failed to create audit log for suspension')

        remove_competition_jobs(competition)
        EmailManager.send_competition_suspended(competition, refund_results)
        return competition, refund_results

    @staticmethod
    @transaction.atomic
    def edit_prizes(competition, form, performed_by=None, performed_by_label=''):
        """Admin edits prize details on a deployed competition."""
        competition = form.save(commit=False)
        if competition.prize_type:
            competition.prize_type = Competition.normalize_prize_type(competition.prize_type)
        competition.admin_reviewed = True
        competition.save()

        remove_competition_jobs(competition)
        schedule_competition_jobs(competition)

        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='edit_prizes',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details='Admin updated prize details.',
            )
        except Exception:
            logger.exception('Failed to create audit log for edit_prizes')

        return competition

    @staticmethod
    @transaction.atomic
    def confirm_checkins(competition, performed_by=None, performed_by_label=''):
        competition.save()
        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='confirm_checkins',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details='Admin confirmed check-ins.',
            )
        except Exception:
            logger.exception('Failed to create audit log for confirm_checkins')

        EmailManager.send_competition_checkins_confirmed(competition)
        return competition

    @staticmethod
    @transaction.atomic
    def edit_results(competition, results_data, performed_by=None, performed_by_label=''):
        """Admin edits competition results and notifies registered gamers."""
        CompetitionService._save_results(competition, results_data, reallocate_points=True)

        competition.save()
        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='edit_results',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details='Admin edited competition results.',
            )
        except Exception:
            logger.exception('Failed to create audit log for edit_results')

        for result in competition.results.select_related('gamer'):
            EmailManager.send_competition_result_to_gamer(
                gamer=result.gamer,
                competition=competition,
                result=result,
            )

        CompetitionService._notify_results_updated(competition)
        return competition

    @staticmethod
    @transaction.atomic
    def verify_results(competition, performed_by=None, performed_by_label=''):
        now = timezone.now()
        competition.results.filter(verified=False).update(
            verified=True, verified_at=now
        )
        competition.status = 'completed'
        competition.save()
        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='verify_results',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details='Admin verified results.',
            )
        except Exception:
            logger.exception('Failed to create audit log for verify_results')

        # Award points only if not already auto-allocated at submission time
        for result in competition.results.filter(
            verified=True, is_no_show=False, auto_allocated=False
        ).select_related('gamer'):
            points_to_award = competition.get_points_for_rank(result.rank)
            if points_to_award > 0:
                result.gamer.points += points_to_award
                result.gamer.save(update_fields=['points'])
                result.points_awarded = points_to_award
                result.auto_allocated = True
                result.save(update_fields=['points_awarded', 'auto_allocated'])

        allocations = []
        if competition.prize_type in ['money', 'money_points'] and competition.prize_money_total:
            total = Decimal(competition.prize_money_total)
            pct_map = {
                1: (competition.prize_money_1st_pct or 0),
                2: (competition.prize_money_2nd_pct or 0),
                3: (competition.prize_money_3rd_pct or 0),
            }
            for res in competition.results.filter(rank__in=[1, 2, 3], is_no_show=False).select_related('gamer').order_by('rank'):
                pct = pct_map.get(res.rank, 0)
                award = (total * Decimal(pct) / Decimal(100)) if pct else Decimal('0.00')
                setattr(res, 'money_awarded', award)
                allocations.append({'gamer': res.gamer, 'rank': res.rank, 'amount': award})
        elif competition.prize_type in ['gift', 'gift_points'] and competition.prize_gift_description:
            for res in competition.results.filter(rank__in=[1, 2, 3], is_no_show=False).select_related('gamer').order_by('rank'):
                setattr(res, 'gift_description', competition.prize_gift_description)
                allocations.append({'gamer': res.gamer, 'rank': res.rank, 'gift': competition.prize_gift_description})

        for result in competition.results.select_related('gamer'):
            EmailManager.send_competition_result_to_gamer(
                gamer=result.gamer,
                competition=competition,
                result=result,
            )

        EmailManager.send_competition_results_verified(competition)
        if allocations:
            try:
                EmailManager.send_competition_prize_allocations(competition, allocations)
            except Exception:
                logger.exception('Failed sending prize allocation summary to admin')

        CompetitionService._notify_results_updated(competition)
        return competition

    @staticmethod
    @transaction.atomic
    def submit_results(competition, results_data):
        CompetitionService._save_results(competition, results_data, reallocate_points=True)

        if competition.prize_type in ['points', None]:
            competition.status = 'completed'
            competition.save()
            EmailManager.send_competition_results_auto_completed(competition)
        else:
            competition.status = 'ongoing'
            competition.save()
            EmailManager.send_competition_results_submitted(competition)

        for result in competition.results.select_related('gamer'):
            EmailManager.send_competition_result_to_gamer(
                gamer=result.gamer,
                competition=competition,
                result=result,
            )

        from activities.services import AchievementService
        for result in competition.results.filter(is_no_show=False):
            AchievementService.check_post_competition_unlocks(result.gamer)

        return competition

    @staticmethod
    def _save_results(competition, results_data, reallocate_points=False):
        existing_results = {str(r.gamer_id): r for r in competition.results.all()}
        new_results_gamers = set()
        to_create = []
        to_update = []

        for item in results_data:
            gamer_id = str(item['gamer_id'])
            new_results_gamers.add(gamer_id)
            rank = item.get('rank')
            is_no_show = item.get('is_no_show', False)

            points_awarded = 0
            auto_allocated = False
            verified = False
            verified_at = None

            if not is_no_show:
                points_awarded = competition.get_points_for_rank(rank)
                auto_allocated = True
                if competition.prize_type in ['points', None]:
                    verified = True
                    verified_at = timezone.now()

            if gamer_id in existing_results:
                res = existing_results[gamer_id]
                if reallocate_points and res.auto_allocated and not res.is_no_show:
                    old_points = res.points_awarded or 0
                    res.gamer.points = max(0, res.gamer.points - old_points)
                    res.gamer.save(update_fields=['points'])

                res.rank = rank if not is_no_show else None
                res.is_no_show = is_no_show
                res.points_awarded = points_awarded
                res.auto_allocated = auto_allocated
                res.verified = verified
                res.verified_at = verified_at
                to_update.append(res)
            else:
                to_create.append(CompetitionResult(
                    competition=competition,
                    gamer_id=gamer_id,
                    rank=rank if not is_no_show else None,
                    is_no_show=is_no_show,
                    points_awarded=points_awarded,
                    auto_allocated=auto_allocated,
                    verified=verified,
                    verified_at=verified_at,
                ))

        to_delete_ids = [gid for gid in existing_results if gid not in new_results_gamers]
        if to_delete_ids:
            for gid in to_delete_ids:
                res = existing_results[gid]
                if reallocate_points and res.auto_allocated and not res.is_no_show:
                    res.gamer.points = max(0, res.gamer.points - (res.points_awarded or 0))
                    res.gamer.save(update_fields=['points'])
            competition.results.filter(gamer_id__in=to_delete_ids).delete()

        if to_create:
            CompetitionResult.objects.bulk_create(to_create)
        if to_update:
            CompetitionResult.objects.bulk_update(to_update, [
                'rank', 'is_no_show', 'points_awarded',
                'auto_allocated', 'verified', 'verified_at',
            ])

        if reallocate_points:
            for result in competition.results.filter(is_no_show=False, auto_allocated=True):
                result.gamer.points += result.points_awarded
                result.gamer.save(update_fields=['points'])

    @staticmethod
    def _notify_results_updated(competition):
        try:
            from notifications.models import Notification
            from notifications.services import send_notification_to_users

            gamers = competition.registrations.filter(
                is_cancelled=False
            ).select_related('gamer').values_list('gamer', flat=True)
            from accounts.models import Gamer
            eligible = Gamer.objects.filter(id__in=gamers)

            notification, _ = Notification.objects.get_or_create(
                title=f"Results Updated: {competition.name}",
                category="competition",
                importance="high",
                is_system=True,
                defaults={
                    'message': f"Results for {competition.name} have been updated. Check your competition page for details.",
                },
            )
            notification.set_expiry()
            notification.save()
            send_notification_to_users(notification, eligible, send_email=False)
        except Exception:
            logger.exception('Failed to send results update notifications')
