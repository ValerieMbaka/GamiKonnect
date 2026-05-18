"""
Handles all automated status transitions for the Competition lifecycle.

Scheduler Strategy:
- django-apscheduler handles dynamic per-competition jobs (precise timestamps)
- A periodic safety-net job runs every 30 minutes to catch any missed transitions
- All jobs are idempotent — safe to run multiple times without side effects

Job naming convention:
    competition_<integer_id>_<action>
    e.g. competition_42_open_registration
         competition_42_close_registration
         competition_42_start
         competition_42_end

Setup:
    Call start_scheduler() once from competitions/apps.py → ready()
    Call schedule_competition_jobs(competition) after admin approval
    Call remove_competition_jobs(competition) if a competition is cancelled
"""

import logging
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


# Scheduler Initialisation
def get_scheduler():
    """Returns the global scheduler instance, creating it if necessary."""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone=str(timezone.get_current_timezone()))
        scheduler.add_jobstore(DjangoJobStore(), 'default')
    return scheduler


def start_scheduler():
    """
    Starts the background scheduler.
    Called once from CompetitionsConfig.ready() in apps.py.
    Registers the periodic safety-net job on startup.
    """
    sched = get_scheduler()

    if sched.running:
        return

    # Periodic safety-net job
    # Runs every 30 minutes to catch any transitions the per-job scheduler missed
    # (e.g. after a server restart or a missed job execution)
    sched.add_job(
        safety_net_check,
        trigger=IntervalTrigger(minutes=30),
        id='competition_safety_net',
        name='Competition Safety Net — periodic status check',
        replace_existing=True,
        misfire_grace_time=60 * 10,  # 10 minute grace period
    )

    try:
        sched.start()
        logger.info('Competition scheduler started successfully.')
    except Exception as e:
        logger.error(f'Failed to start competition scheduler: {e}')


# Per-Competition Job Scheduling
def schedule_competition_jobs(competition):
    """
    Schedules all time-based transition jobs for a competition after approval.
    Called from the admin approval view.

    Jobs scheduled:
        1. open_registration  — at registration_opens_at
        2. close_registration — at registration_closes_at
        3. start_competition  — at scheduled_time
        4. end_competition    — at competition_end_time (if set)
    """
    sched = get_scheduler()
    cid = competition.integer_id
    now = timezone.now()

    job_definitions = [
        {
            'id': f'competition_{cid}_open_registration',
            'name': f'[#{cid}] Open Registration — {competition.name}',
            'func': open_registration,
            'run_at': competition.registration_opens_at,
        },
        {
            'id': f'competition_{cid}_close_registration',
            'name': f'[#{cid}] Close Registration — {competition.name}',
            'func': close_registration,
            'run_at': competition.registration_closes_at,
        },
        {
            'id': f'competition_{cid}_start',
            'name': f'[#{cid}] Start Competition — {competition.name}',
            'func': start_competition,
            'run_at': competition.scheduled_time,
        },
    ]

    if competition.competition_end_time:
        job_definitions.append({
            'id': f'competition_{cid}_end',
            'name': f'[#{cid}] End Competition — {competition.name}',
            'func': end_competition,
            'run_at': competition.competition_end_time,
        })

    for job in job_definitions:
        run_at = job['run_at']

        if not run_at:
            logger.warning(f"Skipping job '{job['id']}' — no timestamp set.")
            continue

        if run_at <= now:
            logger.warning(f"Skipping job '{job['id']}' — timestamp is in the past ({run_at}).")
            continue

        try:
            sched.add_job(
                job['func'],
                trigger=DateTrigger(run_date=run_at),
                id=job['id'],
                name=job['name'],
                args=[cid],
                replace_existing=True,
                misfire_grace_time=60 * 15,  # 15 minute grace period
            )
            logger.info(f"Scheduled job '{job['id']}' for {run_at}.")
        except Exception as e:
            logger.error(f"Failed to schedule job '{job['id']}': {e}")


def remove_competition_jobs(competition):
    """
    Removes all scheduled jobs for a competition.
    Call this if a competition is cancelled or deleted.
    """
    sched = get_scheduler()
    cid = competition.integer_id
    job_ids = [
        f'competition_{cid}_open_registration',
        f'competition_{cid}_close_registration',
        f'competition_{cid}_start',
        f'competition_{cid}_end',
    ]
    for job_id in job_ids:
        try:
            sched.remove_job(job_id)
            logger.info(f"Removed scheduled job '{job_id}'.")
        except Exception:
            pass  # Job may not exist — safe to ignore


# Job Functions — Status Transitions
def open_registration(competition_id):
    """
    Transitions competition from 'approved' → 'registration_open'.
    Notifies shop owner that registration is now open.
    """
    from .models import Competition
    from core.email_service import EmailManager

    try:
        competition = Competition.objects.get(
            integer_id=competition_id,
            status='approved'
        )
        competition.status = 'registration_open'
        competition.save(update_fields=['status', 'updated_at'])

        EmailManager.send_competition_registration_opened(competition)
        # Audit
        try:
            from .models import CompetitionAuditLog
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='open_registration',
                details='Automated: registration opened by scheduler.'
            )
        except Exception:
            logger.exception('Failed to create audit log for open_registration')

        logger.info(f"[#{competition_id}] Registration opened.")

    except Competition.DoesNotExist:
        logger.warning(
            f"[#{competition_id}] open_registration skipped — "
            f"competition not found or not in 'approved' status."
        )
    except Exception as e:
        logger.error(f"[#{competition_id}] open_registration error: {e}")


def close_registration(competition_id):
    """
    Transitions competition from 'registration_open' → 'registration_closed'.
    Notifies shop owner with final participant count.
    Sends reminder email to all registered gamers with their unique code.
    """
    from .models import Competition
    from core.email_service import EmailManager

    try:
        competition = Competition.objects.get(
            integer_id=competition_id,
            status='registration_open'
        )
        competition.status = 'registration_closed'
        competition.save(update_fields=['status', 'updated_at'])

        # Notify shop owner
        EmailManager.send_competition_registration_closed(
            competition=competition,
            participant_count=competition.registered_count()
        )

        # Audit
        try:
            from .models import CompetitionAuditLog
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='close_registration',
                details='Automated: registration closed by scheduler.'
            )
        except Exception:
            logger.exception('Failed to create audit log for close_registration')

        # Send reminder to all registered gamers
        registrations = competition.registrations.filter(
            is_cancelled=False
        ).select_related('gamer')

        for registration in registrations:
            EmailManager.send_competition_reminder(
                gamer=registration.gamer,
                competition=competition,
                registration=registration
            )

        logger.info(
            f"[#{competition_id}] Registration closed. "
            f"{registrations.count()} gamers notified."
        )

    except Competition.DoesNotExist:
        logger.warning(
            f"[#{competition_id}] close_registration skipped — "
            f"competition not found or not in 'registration_open' status."
        )
    except Exception as e:
        logger.error(f"[#{competition_id}] close_registration error: {e}")


def start_competition(competition_id):
    """
    Transitions competition from 'registration_closed' → 'ongoing'.
    Expires all unused registration codes (gamers who haven't been verified yet).
    """
    from .models import Competition, CompetitionRegistration

    try:
        competition = Competition.objects.get(
            integer_id=competition_id,
            status='registration_closed'
        )
        competition.status = 'ongoing'
        competition.save(update_fields=['status', 'updated_at'])

        # Expire all codes that haven't been used yet
        # (checked_in=False means they haven't been verified by shop owner)
        expired_count = CompetitionRegistration.objects.filter(
            competition=competition,
            checked_in=False,
            code_expired=False,
            is_cancelled=False
        ).update(code_expired=True)

        # Audit
        try:
            from .models import CompetitionAuditLog
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='start',
                details=f'Automated: competition started; {expired_count} codes expired.'
            )
        except Exception:
            logger.exception('Failed to create audit log for start_competition')

        logger.info(
            f"[#{competition_id}] Competition started. "
            f"{expired_count} unused code(s) expired."
        )

    except Competition.DoesNotExist:
        logger.warning(
            f"[#{competition_id}] start_competition skipped — "
            f"competition not found or not in 'registration_closed' status."
        )
    except Exception as e:
        logger.error(f"[#{competition_id}] start_competition error: {e}")


def end_competition(competition_id):
    """
    Transitions competition from 'ongoing' → prompts shop owner to submit check-ins.
    Sends a notification to the shop owner reminding them to verify and submit check-ins.
    The competition stays in 'ongoing' status — shop owner must actively submit.
    """
    from .models import Competition
    from core.email_service import EmailManager

    try:
        competition = Competition.objects.get(
            integer_id=competition_id,
            status='ongoing'
        )

        # Notify shop owner to submit check-ins — status stays 'ongoing'
        # until the shop owner actively submits via shop_owner_submit_checkins view
        EmailManager.send_competition_ended_prompt(competition)

        # Audit
        try:
            from .models import CompetitionAuditLog
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='end',
                details='Automated: competition end time reached; shop owner prompted to submit check-ins.'
            )
        except Exception:
            logger.exception('Failed to create audit log for end_competition')

        logger.info(
            f"[#{competition_id}] Competition end time reached. "
            f"Shop owner notified to submit check-ins."
        )

    except Competition.DoesNotExist:
        logger.warning(
            f"[#{competition_id}] end_competition skipped — "
            f"competition not found or not in 'ongoing' status."
        )
    except Exception as e:
        logger.error(f"[#{competition_id}] end_competition error: {e}")


# Safety-Net Job — Periodic Catch-All
def safety_net_check():
    """
    Runs every 30 minutes as a safety net.
    Catches any competitions whose status should have transitioned
    but didn't (e.g. due to a server restart or missed job execution).

    Handles:
        - approved → registration_open (if registration_opens_at has passed)
        - registration_open → registration_closed (if registration_closes_at has passed)
        - registration_closed → ongoing (if scheduled_time has passed)
    """
    from .models import Competition, CompetitionRegistration
    from core.email_service import EmailManager

    now = timezone.now()
    transitioned = 0

    # approved → registration_open
    missed_open = Competition.objects.filter(
        status='approved',
        registration_opens_at__lte=now
    )
    for competition in missed_open:
        competition.status = 'registration_open'
        competition.save(update_fields=['status', 'updated_at'])
        EmailManager.send_competition_registration_opened(competition)
        try:
            from .models import CompetitionAuditLog
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='open_registration',
                details='Safety-net automated transition: opened registration.'
            )
        except Exception:
            logger.exception('Failed to create safety-net audit log for open_registration')
        logger.info(f"[Safety Net] [#{competition.integer_id}] Opened registration (missed job).")
        transitioned += 1

    # registration_open → registration_closed
    missed_close = Competition.objects.filter(
        Q(status='registration_open'),
        Q(registration_closes_at__lte=now) | Q(is_registration_full=True)
    )
    for competition in missed_close:
        # Extra check for full registration if closes_at hasn't passed
        if competition.registration_closes_at > now and not competition.is_registration_full():
            continue
            
        competition.status = 'registration_closed'
        competition.save(update_fields=['status', 'updated_at'])

        EmailManager.send_competition_registration_closed(
            competition=competition,
            participant_count=competition.registered_count()
        )

        registrations = competition.registrations.filter(
            is_cancelled=False
        ).select_related('gamer')
        for registration in registrations:
            EmailManager.send_competition_reminder(
                gamer=registration.gamer,
                competition=competition,
                registration=registration
            )

        try:
            from .models import CompetitionAuditLog
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='close_registration',
                details='Safety-net automated transition: closed registration.'
            )
        except Exception:
            logger.exception('Failed to create safety-net audit log for close_registration')
        logger.info(f"[Safety Net] [#{competition.integer_id}] Closed registration (missed job).")
        transitioned += 1

    # registration_closed → ongoing
    missed_start = Competition.objects.filter(
        status='registration_closed',
        scheduled_time__lte=now
    )
    for competition in missed_start:
        competition.status = 'ongoing'
        competition.save(update_fields=['status', 'updated_at'])

        CompetitionRegistration.objects.filter(
            competition=competition,
            checked_in=False,
            code_expired=False,
            is_cancelled=False
        ).update(code_expired=True)
        try:
            from .models import CompetitionAuditLog
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='start',
                details='Safety-net automated transition: started competition and expired unused codes.'
            )
        except Exception:
            logger.exception('Failed to create safety-net audit log for start')
        logger.info(f"[Safety Net] [#{competition.integer_id}] Started competition (missed job).")
        transitioned += 1

    # ongoing → prompt shop owner (if end_time passed and still ongoing)
    missed_end = Competition.objects.filter(
        status='ongoing',
        competition_end_time__lte=now
    )
    for competition in missed_end:
        EmailManager.send_competition_ended_prompt(competition)
        try:
            from .models import CompetitionAuditLog
            CompetitionAuditLog.objects.create(
                competition=competition,
                action='end',
                details='Safety-net automated transition: end time passed; shop owner re-notified.'
            )
        except Exception:
            logger.exception('Failed to create safety-net audit log for end')
        logger.info(
            f"[Safety Net] [#{competition.integer_id}] End time passed — "
            f"shop owner re-notified to submit check-ins."
        )
        transitioned += 1

    if transitioned:
        logger.info(f"[Safety Net] Handled {transitioned} missed transition(s).")
    else:
        logger.debug("[Safety Net] No missed transitions found.")


# Job Execution Cleanup
def delete_old_job_executions(max_age_seconds=604_800):
    """
    Deletes job execution records older than max_age_seconds (default: 7 days).
    Called periodically to keep the DjangoJobExecution table clean.
    Registered as a weekly job in start_scheduler().
    """
    DjangoJobExecution.objects.delete_old_job_executions(max_age_seconds)
    logger.info("Cleaned up old job execution records.")