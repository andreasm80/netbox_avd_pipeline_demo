# In netbox_run_anta_plugin/netbox_run_anta_plugin/models.py

from django.db import models

class AntaStatus(models.Model):
    """
    Singleton model to store the last known hash of the ANTA status file.
    """
    last_known_hash = models.CharField(
        max_length=64,  # SHA256 hash length is 64 characters
        blank=True,
        help_text="The SHA256 hash of the status file content from the last run"
    )

    class Meta:
        verbose_name = "ANTA Status"
        verbose_name_plural = "ANTA Status"

    def __str__(self):
        return self.last_known_hash
