"""Reconcile production DB schema with current models.

The production database was originally created by a different project (OpenShareHQ)
with a different skills_skill schema. Migrations 0001-0005 were rewritten for the
new schema but marked as applied on production, leaving the actual columns out of sync.

This migration uses raw SQL with IF NOT EXISTS / IF EXISTS guards so it's idempotent
and safe to run on both fresh databases and the diverged production DB.
"""
from django.db import migrations


FORWARD_SQL = """
-- ─── skills_skill: rename price_per_use → price ───────────────────────────────
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'skills_skill' AND column_name = 'price_per_use'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'skills_skill' AND column_name = 'price'
  ) THEN
    ALTER TABLE skills_skill RENAME COLUMN price_per_use TO price;
  END IF;
END $$;

-- ─── skills_skill: add missing columns ───────────────────────────────────────
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS price DECIMAL(6,2);
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS package_file VARCHAR(200) DEFAULT '';
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS package_sha256 VARCHAR(64) DEFAULT '';
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS package_size INTEGER DEFAULT 0;
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS readme_html TEXT DEFAULT '';
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS download_count INTEGER DEFAULT 0;

-- ─── skills_skill: drop old columns that no longer exist in the model ────────
ALTER TABLE skills_skill DROP COLUMN IF EXISTS system_prompt;
ALTER TABLE skills_skill DROP COLUMN IF EXISTS user_prompt_template;
ALTER TABLE skills_skill DROP COLUMN IF EXISTS output_format;
ALTER TABLE skills_skill DROP COLUMN IF EXISTS example_input;
ALTER TABLE skills_skill DROP COLUMN IF EXISTS example_output;

-- ─── skills_skill_version: add missing columns ──────────────────────────────
ALTER TABLE skills_skill_version ADD COLUMN IF NOT EXISTS package_file VARCHAR(200) DEFAULT '';
ALTER TABLE skills_skill_version ADD COLUMN IF NOT EXISTS package_sha256 VARCHAR(64) DEFAULT '';
ALTER TABLE skills_skill_version ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'APPROVED';
ALTER TABLE skills_skill_version ADD COLUMN IF NOT EXISTS scan_result VARCHAR(10) DEFAULT '';
ALTER TABLE skills_skill_version ADD COLUMN IF NOT EXISTS scan_warnings JSONB DEFAULT '[]';
ALTER TABLE skills_skill_version ADD COLUMN IF NOT EXISTS pending_metadata JSONB DEFAULT '{}';

-- Rename change_note → changelog if applicable
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'skills_skill_version' AND column_name = 'change_note'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'skills_skill_version' AND column_name = 'changelog'
  ) THEN
    ALTER TABLE skills_skill_version RENAME COLUMN change_note TO changelog;
  END IF;
END $$;

-- Convert version column from integer to varchar(50) if needed
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'skills_skill_version'
      AND column_name = 'version'
      AND data_type = 'integer'
  ) THEN
    ALTER TABLE skills_skill_version ALTER COLUMN version TYPE VARCHAR(50) USING version::text;
  END IF;
END $$;

-- Drop old columns from skills_skill_version
ALTER TABLE skills_skill_version DROP COLUMN IF EXISTS system_prompt;
ALTER TABLE skills_skill_version DROP COLUMN IF EXISTS user_prompt_template;
ALTER TABLE skills_skill_version DROP COLUMN IF EXISTS is_major;

-- ─── skills_skill_call: fix skill_version type ──────────────────────────────
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'skills_skill_call'
      AND column_name = 'skill_version'
      AND data_type = 'integer'
  ) THEN
    ALTER TABLE skills_skill_call ALTER COLUMN skill_version TYPE VARCHAR(50) USING skill_version::text;
  END IF;
END $$;

-- Drop amount_charged if it exists (not in current model)
ALTER TABLE skills_skill_call DROP COLUMN IF EXISTS amount_charged;

-- ─── skills_skill_version: make version + skill unique ──────────────────────
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'skills_skill_version_skill_id_version_uniq'
  ) THEN
    BEGIN
      ALTER TABLE skills_skill_version
        ADD CONSTRAINT skills_skill_version_skill_id_version_uniq UNIQUE (skill_id, version);
    EXCEPTION WHEN duplicate_table THEN NULL;
    END;
  END IF;
END $$;

-- ─── skills_skill_review: ensure unique (skill, reviewer) ──────────────────
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'skills_skill_review_skill_id_reviewer_id_uniq'
  ) THEN
    BEGIN
      ALTER TABLE skills_skill_review
        ADD CONSTRAINT skills_skill_review_skill_id_reviewer_id_uniq UNIQUE (skill_id, reviewer_id);
    EXCEPTION WHEN duplicate_table THEN NULL;
    END;
  END IF;
END $$;

-- ─── skills_skill_purchase: ensure unique (skill, user) ────────────────────
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'skills_skill_purchase_skill_id_user_id_uniq'
  ) THEN
    BEGIN
      ALTER TABLE skills_skill_purchase
        ADD CONSTRAINT skills_skill_purchase_skill_id_user_id_uniq UNIQUE (skill_id, user_id);
    EXCEPTION WHEN duplicate_table THEN NULL;
    END;
  END IF;
END $$;

-- ─── skills_skill_report: ensure unique (skill, reporter) ─────────────────
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'skills_skill_report_skill_id_reporter_id_uniq'
  ) THEN
    BEGIN
      ALTER TABLE skills_skill_report
        ADD CONSTRAINT skills_skill_report_skill_id_reporter_id_uniq UNIQUE (skill_id, reporter_id);
    EXCEPTION WHEN duplicate_table THEN NULL;
    END;
  END IF;
END $$;

-- ─── skills_skill_usage_preference: fix locked_version type ────────────────
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'skills_skill_usage_preference'
      AND column_name = 'locked_version'
      AND data_type = 'integer'
  ) THEN
    ALTER TABLE skills_skill_usage_preference
      ALTER COLUMN locked_version TYPE VARCHAR(50) USING COALESCE(locked_version::text, '');
    ALTER TABLE skills_skill_usage_preference
      ALTER COLUMN locked_version SET DEFAULT '';
  END IF;
END $$;
"""

REVERSE_SQL = """
-- Reverse is not fully invertible; this is a best-effort rollback.
-- Re-adding dropped columns with empty defaults.
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS system_prompt TEXT DEFAULT '';
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS user_prompt_template TEXT DEFAULT '';
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS output_format TEXT DEFAULT '';
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS example_input TEXT DEFAULT '';
ALTER TABLE skills_skill ADD COLUMN IF NOT EXISTS example_output TEXT DEFAULT '';
"""


class Migration(migrations.Migration):
    dependencies = [
        ("skills", "0005_add_pending_metadata_to_skillversion"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
