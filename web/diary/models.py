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
    id = models.UUIDField(primary_key=True)
    occurred_at = models.DateTimeField()
    content_text = models.TextField()
    is_deleted = models.BooleanField()
    tags = models.ManyToManyField("Tag", through="ItemTag", related_name="ingest_items")

    class Meta:
        managed = False
        db_table = "ingest_item"


