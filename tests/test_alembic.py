import os
import glob
import re

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
