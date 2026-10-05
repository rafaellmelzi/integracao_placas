import os
import glob
import re
import tempfile
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect

def test_alembic_revision_id_lengths():
    """Ensure all Alembic migration revision IDs are <= 32 chars to prevent PostgreSQL string truncation errors."""
    versions_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic", "versions")
    migration_files = glob.glob(os.path.join(versions_dir, "*.py"))
    assert len(migration_files) > 0, "No migration files found in alembic/versions"

    for filepath in migration_files:
        if os.path.basename(filepath).startswith("__"):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
        assert match is not None, f"Could not find revision string in {filepath}"
        revision_id = match.group(1)

        assert len(revision_id) <= 32, (
            f"Revision ID '{revision_id}' in {os.path.basename(filepath)} has length {len(revision_id)}, "
            f"which exceeds Alembic default column limit of 32 characters!"
        )

def test_clean_database_migrations():
    """
    Integration test verifying that running 'alembic upgrade head' on a completely fresh database
    applies all migrations (001 -> 002) step-by-step without duplicate column or constraint errors.
    """
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db_url = f"sqlite:///{tmp.name}"
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # 1. Upgrade step-by-step to 001_initial_schema
        command.upgrade(alembic_cfg, "001_initial_schema")

        engine = create_engine(db_url)
        inspector = inspect(engine)

        # Verify 001 schema exists and does NOT contain 002 additions
        part_cols_001 = [col["name"] for col in inspector.get_columns("part")]
        assert "manufacturer_part_number" in part_cols_001
        assert "oem_codes" not in part_cols_001
        assert "technical_specs" not in part_cols_001

        # 2. Upgrade to 002_parts_catalog (head)
        command.upgrade(alembic_cfg, "head")

        # Verify 002 columns were properly added
        inspector = inspect(engine)
        part_cols_002 = [col["name"] for col in inspector.get_columns("part")]
        assert "oem_codes" in part_cols_002
        assert "equivalent_codes" in part_cols_002
        assert "technical_specs" in part_cols_002
        assert "source" in part_cols_002

        app_cols_002 = [col["name"] for col in inspector.get_columns("part_application")]
        assert "axis" in app_cols_002
