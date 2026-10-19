from django.conf import settings
from django.db import models
from django.db.models import Q


class Medication(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medications",
    )
    name = models.CharField(max_length=120)
    dosage = models.CharField(max_length=120)
    frequency = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(name=""),
                name="medication_name_not_blank",
            ),
            models.CheckConstraint(
                condition=~Q(dosage=""),
                name="medication_dosage_not_blank",
            ),
            models.CheckConstraint(
                condition=~Q(frequency=""),
                name="medication_frequency_not_blank",
            ),
        ]
