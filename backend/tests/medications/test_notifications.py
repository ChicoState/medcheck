from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from medications.models import (
    MedicationDose,
    MedicationSchedule,
    NotificationDelivery,
    NotificationSettings,
    RefillReminder,
)

pytestmark = pytest.mark.django_db


def logged_in(email="member@example.com") -> tuple[Any, Any]:
    user = get_user_model().objects.create_user(
        username=email, email=email, password="a-strong-password"
    )
    client: Any = Client()
    client.force_login(user)
    return client, user


def test_notification_settings_default_to_opt_in_for_dose_and_refill_and_vitamin_reminders():
    client, _ = logged_in()

    response = client.get("/api/notifications/settings/")

    assert response.status_code == 200
    assert response.json() == {
        "doseReminders": True,
        "vitaminReminders": True,
        "refillReminders": True,
    }


def test_notification_settings_can_be_updated_and_are_private():
    client, user = logged_in()
    other_client, other_user = logged_in("other@example.com")
    token = client.get("/api/auth/csrf/").json()["csrfToken"]

    response = client.patch(
        "/api/notifications/settings/",
        data='{"doseReminders": false, "vitaminReminders": true, "refillReminders": false}',
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    assert response.json()["doseReminders"] is False
    assert NotificationSettings.objects.get(user=user).refill_reminders is False
    assert other_client.get("/api/notifications/settings/").json()["doseReminders"] is True
    assert NotificationSettings.objects.get(user=other_user).dose_reminders is True


def test_refill_api_validates_dates_and_isolates_accounts():
    client, user = logged_in()
    other_client, _ = logged_in("other@example.com")
    token = client.get("/api/auth/csrf/").json()["csrfToken"]
    response = client.post(
        "/api/notifications/refills/",
        data='{"name": "Lisinopril", "dueDate": "2026-12-01"}',
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Lisinopril"
    assert other_client.get("/api/notifications/refills/").json() == {"data": []}
    assert RefillReminder.objects.filter(user=user).count() == 1
    assert (
        client.post(
            "/api/notifications/refills/",
            data='{"name": "", "dueDate": "not-a-date"}',
            content_type="application/json",
            headers={"X-CSRFToken": token},
        ).status_code
        == 400
    )


def test_notification_command_sends_dose_vitamin_and_refill_emails_once():
    client, user = logged_in()
    schedule = MedicationSchedule.objects.create(user=user)
    today = timezone.localtime().weekday()
    current = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
    MedicationDose.objects.create(
        schedule=schedule,
        day_of_week=today,
        medication_name="Lisinopril",
        time=(current + timedelta(hours=1)).time(),
        with_food=False,
        category=MedicationDose.Category.MEDICATION,
    )
    MedicationDose.objects.create(
        schedule=schedule,
        day_of_week=today,
        medication_name="Vitamin D",
        time=(current + timedelta(hours=1)).time(),
        with_food=True,
        category=MedicationDose.Category.VITAMIN,
    )
    RefillReminder.objects.create(
        user=user,
        name="Lisinopril",
        due_date=timezone.localdate() + timedelta(days=7),
    )

    with patch("medications.notifications.timezone.localtime") as localtime:
        localtime.return_value = current
        call_command("send_medication_notifications")
        call_command("send_medication_notifications")

    assert len(mail.outbox) == 3  # pyright: ignore[reportAttributeAccessIssue]
    assert NotificationDelivery.objects.filter(user=user).count() == 3
    assert {message.subject for message in mail.outbox} == {  # pyright: ignore[reportAttributeAccessIssue]
        "Time to take Lisinopril",
        "Time to take Vitamin D",
        "Lisinopril refill reminder",
    }


def test_notifications_require_authentication():
    client: Any = Client()
    assert client.get("/api/notifications/settings/").status_code == 401
    assert client.get("/api/notifications/refills/").status_code == 401
