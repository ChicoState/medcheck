from django.conf import settings
from django.db import models


class Medication(models.Model):
    objects = models.Manager()
    provider = models.CharField(max_length=24)
    external_id = models.UUIDField()
    display_name = models.CharField(max_length=240)
    generic_name = models.CharField(max_length=240, null=True)
    brand_names = models.JSONField(default=list)
    active_ingredients = models.JSONField(default=list)
    dosage_forms = models.JSONField(default=list)
    routes = models.JSONField(default=list)
    rxcui = models.CharField(max_length=24, null=True)
    label_sections = models.JSONField(default=list)
    label_effective_date = models.DateField(null=True)
    dataset_updated_at = models.DateField(null=True)
    fetched_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"], name="unique_provider_label"
            )
        ]


class SavedMedication(models.Model):
    objects = models.Manager()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "medication"], name="unique_user_label")
        ]


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
