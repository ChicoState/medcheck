from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    MedicationDose,
    MedicationSchedule,
    NotificationDelivery,
    NotificationSettings,
    RefillReminder,
)

REFILL_REMINDER_DAYS = 7
REFILL_SEND_TIME = time(9, 0)


def _settings_for(user):
    notification_settings, _ = NotificationSettings.objects.get_or_create(user=user)
    return notification_settings


def _send_once(user, kind, dedupe_key, subject, body):
    try:
        with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
            NotificationDelivery.objects.create(user=user, kind=kind, dedupe_key=dedupe_key)
    except IntegrityError:
        return False
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        NotificationDelivery.objects.filter(dedupe_key=dedupe_key).delete()
        raise
    return True


def send_due_notifications(now=None):
    current = timezone.localtime(now or timezone.now()).replace(second=0, microsecond=0)
    sent = 0
    for schedule in MedicationSchedule.objects.select_related("user").prefetch_related("doses"):
        notification_settings = _settings_for(schedule.user)
        for dose in schedule.doses.all():
            if dose.day_of_week != current.weekday():
                continue
            if dose.category == MedicationDose.Category.VITAMIN:
                if not notification_settings.vitamin_reminders:
                    continue
            elif not notification_settings.dose_reminders:
                continue
            dose_at = datetime.combine(current.date(), dose.time, tzinfo=current.tzinfo)
            target = dose_at - timedelta(hours=1)
            if target != current:
                continue
            kind = "vitamin" if dose.category == MedicationDose.Category.VITAMIN else "dose"
            key = f"{kind}:{schedule.user_id}:{dose.pk}:{target.isoformat()}"
            subject = f"Time to take {dose.medication_name}"
            body = (
                f"This is your reminder to take {dose.medication_name} at "
                f"{dose.time.strftime('%-I:%M %p')}. Follow your clinician's instructions."
            )
            if _send_once(schedule.user, kind, key, subject, body):
                sent += 1

    if current.time() == REFILL_SEND_TIME:
        due_date = current.date() + timedelta(days=REFILL_REMINDER_DAYS)
        for refill in RefillReminder.objects.select_related("user").filter(due_date=due_date):
            if not _settings_for(refill.user).refill_reminders:
                continue
            key = f"refill:{refill.pk}:{due_date.isoformat()}"
            subject = f"{refill.name} refill reminder"
            body = (
                f"Your refill reminder for {refill.name} is due on {due_date.isoformat()}. "
                "Confirm availability with your pharmacy and follow your clinician's instructions."
            )
            if _send_once(refill.user, "refill", key, subject, body):
                sent += 1
    return sent
