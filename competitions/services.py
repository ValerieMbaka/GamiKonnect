import logging
from django.db import transaction
from django.utils import timezone
from .models import Competition, CompetitionResult, CompetitionRegistration, CompetitionAuditLog
from .scheduler import schedule_competition_jobs
from core.email_service import EmailManager
from decimal import Decimal

logger = logging.getLogger(__name__)


class CompetitionService:
    @staticmethod
    @transaction.atomic
    def approve_competition(competition, approval_form, performed_by=None, performed_by_label=''):
        competition = approval_form.save(commit=False)
        competition.status = 'live'
        competition.approved_at = timezone.now()
        competition.rejection_reason = ''
        competition.save()
        # Audit
        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='approve',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details='Competition approved via admin panel.'
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
                details=f"Rejected: {competition.rejection_reason}"
            )
        except Exception:
            logger.exception('Failed to create audit log for rejection')

        EmailManager.send_competition_rejected(competition)
        return competition
    
    @staticmethod
    @transaction.atomic
    def confirm_checkins(competition, performed_by=None, performed_by_label=''):
        competition.status = 'results_pending'
        competition.save()
        try:
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='confirm_checkins',
                performed_by=performed_by,
                performed_by_label=performed_by_label,
                details='Admin confirmed check-ins.'
            )
        except Exception:
            logger.exception('Failed to create audit log for confirm_checkins')

        EmailManager.send_competition_checkins_confirmed(competition)
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
                details='Admin verified results.'
            )
        except Exception:
            logger.exception('Failed to create audit log for verify_results')
        
        # Award points to gamers based on their rank (if prize_type is 'points')
        for result in competition.results.filter(verified=True, is_no_show=False).select_related('gamer'):
            if competition.prize_type == 'points':
                points_to_award = competition.get_points_for_rank(result.rank)
                if points_to_award > 0:
                    result.gamer.points += points_to_award
                    result.gamer.save(update_fields=['points'])
        
        # Prize allocation for money/gift types (no DB fields added; allocations are communicated via email)
        allocations = []
        if competition.prize_type == 'money' and competition.prize_money_total:
            total = Decimal(competition.prize_money_total)
            # Build mapping for pct fields
            pct_map = {
                1: (competition.prize_money_1st_pct or 0),
                2: (competition.prize_money_2nd_pct or 0),
                3: (competition.prize_money_3rd_pct or 0),
            }
            for res in competition.results.filter(rank__in=[1,2,3], is_no_show=False).select_related('gamer').order_by('rank'):
                pct = pct_map.get(res.rank, 0)
                award = (total * Decimal(pct) / Decimal(100)) if pct else Decimal('0.00')
                # Attach transient attribute used by email templates
                setattr(res, 'money_awarded', award)
                allocations.append({'gamer': res.gamer, 'rank': res.rank, 'amount': award})
        elif competition.prize_type == 'gift' and competition.prize_gift_description:
            # For gifts, include the description for top winners
            for res in competition.results.filter(rank__in=[1,2,3], is_no_show=False).select_related('gamer').order_by('rank'):
                setattr(res, 'gift_description', competition.prize_gift_description)
                allocations.append({'gamer': res.gamer, 'rank': res.rank, 'gift': competition.prize_gift_description})

        # Send individual notifications including transient prize info
        for result in competition.results.select_related('gamer'):
            EmailManager.send_competition_result_to_gamer(
                gamer=result.gamer,
                competition=competition,
                result=result
            )

        # Notify admin of the final verified results and prize allocations
        EmailManager.send_competition_results_verified(competition)
        if allocations:
            try:
                EmailManager.send_competition_prize_allocations(competition, allocations)
            except Exception:
                logger.exception('Failed sending prize allocation summary to admin')

        return competition
    
    @staticmethod
    @transaction.atomic
    def submit_results(competition, results_data):
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
            
            if not is_no_show and competition.prize_type == 'points':
                points_awarded = competition.get_points_for_rank(rank)
                auto_allocated = True
                verified = True
                verified_at = timezone.now()
            
            if gamer_id in existing_results:
                res = existing_results[gamer_id]
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
                    verified_at=verified_at
                ))
        
        to_delete_ids = [gid for gid in existing_results if gid not in new_results_gamers]
        if to_delete_ids:
            competition.results.filter(gamer_id__in=to_delete_ids).delete()
        
        if to_create:
            CompetitionResult.objects.bulk_create(to_create)
        if to_update:
            CompetitionResult.objects.bulk_update(to_update, [
                'rank', 'is_no_show', 'points_awarded',
                'auto_allocated', 'verified', 'verified_at'
            ])
        
        if competition.prize_type == 'points':
            for result in competition.results.filter(is_no_show=False):
                result.gamer.points += result.points_awarded
                result.gamer.save(update_fields=['points'])
            
            competition.status = 'completed'
            competition.save()
            
            EmailManager.send_competition_results_auto_completed(competition)
        else:
            competition.status = 'pending_prize_verification'
            competition.save()
            EmailManager.send_competition_results_submitted(competition)
        
        for result in competition.results.select_related('gamer'):
            EmailManager.send_competition_result_to_gamer(
                gamer=result.gamer,
                competition=competition,
                result=result
            )
        
        # --- ACHIEVEMENT ENGINE HOOK ---
        from activities.services import AchievementService
        for result in competition.results.filter(is_no_show=False):
            AchievementService.check_post_competition_unlocks(result.gamer)
        
        return competition