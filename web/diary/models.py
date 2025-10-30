from django.db import models


class Tag(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.TextField(unique=True)
    kind = models.TextField()

    class Meta:
        managed = False
        db_table = "tag"


class ItemTag(models.Model):
    ingest_item = models.ForeignKey("IngestItem", on_delete=models.CASCADE, db_column="ingest_item_id")
    tag = models.ForeignKey("Tag", on_delete=models.CASCADE, db_column="tag_id")
    added_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "item_tag"
        unique_together = [["ingest_item", "tag"]]


class IngestItem(models.Model):
    """
    Voice diary entry model.
    
    Deletion workflow:
    - Soft delete (default): Sets is_deleted=True, deletion_type='soft', deleted_at=now()
      Entry is hidden from views but preserved in database for recovery
    - Hard delete (future): Sets deletion_type='hard' before physical deletion
      Used when permanent removal is required
    """
    id = models.UUIDField(primary_key=True)
    occurred_at = models.DateTimeField()
    content_text = models.TextField()
    is_deleted = models.BooleanField()
    deletion_type = models.CharField(max_length=10, default='soft')  # 'soft' or 'hard'
    deleted_at = models.DateTimeField(null=True, blank=True)  # Timestamp when deleted
    tags = models.ManyToManyField("Tag", through="ItemTag", related_name="ingest_items")

    class Meta:
        managed = False
        db_table = "ingest_item"


