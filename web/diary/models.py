from django.db import models


class IngestItem(models.Model):
    id = models.UUIDField(primary_key=True)
    occurred_at = models.DateTimeField()
    content_text = models.TextField()
    is_deleted = models.BooleanField()

    class Meta:
        managed = False
        db_table = "ingest_item"


