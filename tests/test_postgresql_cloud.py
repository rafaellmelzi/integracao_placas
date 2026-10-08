"""Opt-in migrations on a disposable PostgreSQL database, never on AUTCOM."""
import os

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.config import Settings, settings
from app.db.connection import create_database_engine


def test_postgresql_private_schema_upgrade_downgrade_and_runtime_role(monkeypatch):
    raw = os.getenv("TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("Requires disposable PostgreSQL via TEST_POSTGRES_URL")
    # Refuse arbitrary hosts: this test deliberately reverses its own migrations.
    from app.db.connection import database_url
    assert database_url(raw).host == "integracao-cloud-validation-pg"
    assert database_url(raw).database == "validation"
    config = Settings(DATABASE_SCHEMA="cloud_validation", DB_SSL_MODE="")
    monkeypatch.setattr(settings, "DATABASE_SCHEMA", config.DATABASE_SCHEMA)
    engine = create_database_engine(raw, config, migration=True)
    cfg = Config("alembic.ini")
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS cloud_validation CASCADE"))
            connection.execute(text("DROP ROLE IF EXISTS cloud_runtime"))
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
            assert connection.scalar(text("SHOW search_path")) == "cloud_validation"
            assert connection.scalar(text("SHOW statement_timeout")) == "10s"
            assert "part" in inspect(connection).get_table_names(schema="cloud_validation")
            assert "part" not in inspect(connection).get_table_names(schema="public")
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == ScriptDirectory.from_config(cfg).get_current_head()
            assert len(inspect(connection).get_enums(schema="cloud_validation")) == 3
            command.downgrade(cfg, "base")
            assert inspect(connection).get_enums(schema="cloud_validation") == []
            command.upgrade(cfg, "head")
            connection.execute(text("CREATE ROLE cloud_runtime NOLOGIN"))
            connection.execute(text("GRANT USAGE ON SCHEMA cloud_validation TO cloud_runtime"))
            connection.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA cloud_validation TO cloud_runtime"))
            connection.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA cloud_validation TO cloud_runtime"))
            connection.execute(text("SET ROLE cloud_runtime"))
            connection.execute(text("INSERT INTO vehicle_make (name, normalized_name) VALUES ('Jeep', 'JEEP')"))
            assert connection.scalar(text("SELECT count(*) FROM vehicle_make")) == 1
            from app.health import readiness
            from sqlalchemy.orm import Session
            assert readiness(Session(bind=connection))["status"] == "healthy"
            assert not connection.scalar(text("SELECT has_schema_privilege(current_user, 'cloud_validation', 'CREATE')"))
            connection.execute(text("RESET ROLE"))
    finally:
        engine.dispose()
