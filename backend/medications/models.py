from django.conf import settings
from django.db import models


class MedicationSchedule(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medication_schedule",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MedicationDose(models.Model):
    schedule = models.ForeignKey(
        MedicationSchedule,
        on_delete=models.CASCADE,
        related_name="doses",
    )
    day_of_week = models.PositiveSmallIntegerField()
    medication_name = models.CharField(max_length=200)
    time = models.TimeField()
    with_food = models.BooleanField()

    class Meta:
        ordering = ["day_of_week", "time", "medication_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "day_of_week", "medication_name", "time"],
                name="unique_schedule_dose",
            ),
            models.CheckConstraint(
                condition=models.Q(day_of_week__gte=0, day_of_week__lte=6),
                name="valid_schedule_day",
            ),
        ]
