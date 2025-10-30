"""
Add deletion tracking columns to ingest_item table.

This migration adds:
- deletion_type ENUM ('soft', 'hard')
- deletion_type column with default 'soft'
- deleted_at TIMESTAMPTZ column
- Index on deletion_type for deleted items

This enables flexible deletion modes with audit trail and future recovery options.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('diary', '__first__'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Create deletion_type ENUM if it doesn't exist
            DO $$
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deletion_type') THEN
                CREATE TYPE deletion_type AS ENUM ('soft', 'hard');
              END IF;
            END$$;
            
            -- Add deletion_type column with default 'soft'
            ALTER TABLE ingest_item 
              ADD COLUMN IF NOT EXISTS deletion_type deletion_type DEFAULT 'soft';
            
            -- Add deleted_at timestamp column
            ALTER TABLE ingest_item 
              ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
            
            -- Create index on deletion_type for deleted items
            CREATE INDEX IF NOT EXISTS idx_ingest_item_deletion_type 
              ON ingest_item(deletion_type) 
              WHERE is_deleted = true;
            """,
            reverse_sql="""
            -- Remove index
            DROP INDEX IF EXISTS idx_ingest_item_deletion_type;
            
            -- Remove columns
            ALTER TABLE ingest_item 
              DROP COLUMN IF EXISTS deleted_at,
              DROP COLUMN IF EXISTS deletion_type;
            
            -- Drop ENUM type (only if not used elsewhere)
            DROP TYPE IF EXISTS deletion_type;
            """
        ),
    ]

