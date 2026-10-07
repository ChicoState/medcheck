from django.db import models


class DrugLabelInteraction(models.Model):
    """Raw FDA drug-interaction text for one SPL label version."""

    objects = models.Manager["DrugLabelInteraction"]()

    set_id = models.CharField(max_length=128)
    version = models.CharField(max_length=64)
    effective_time = models.CharField(blank=True, max_length=64)
    brand_name = models.CharField(blank=True, max_length=512)
    generic_name = models.CharField(blank=True, max_length=512)
    substance_names = models.JSONField(default=list)
    interaction_text = models.TextField()
    source_url = models.URLField(max_length=2_048)
    source_hash = models.CharField(max_length=64)
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["set_id", "version"],
                name="drug_label_interaction_set_id_version_uniq",
            )
        ]
