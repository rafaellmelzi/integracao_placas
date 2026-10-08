from logging.config import fileConfig
from sqlalchemy import text
from alembic import context
from app.db.models import Base
import os
from app.core.config import settings
from app.core.security import install_log_redaction
from app.db.connection import create_database_engine, database_url
install_log_redaction()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = database_url(os.getenv("MIGRATION_DATABASE_URL") or os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=settings.DATABASE_SCHEMA if url.get_backend_name() == "postgresql" else None,
    )

    with context.begin_transaction():
        if url.get_backend_name() == "postgresql" and settings.DATABASE_SCHEMA != "public":
            context.execute(f'CREATE SCHEMA IF NOT EXISTS "{settings.DATABASE_SCHEMA}"')
            context.execute(f'SET search_path TO "{settings.DATABASE_SCHEMA}"')
        context.run_migrations()

def run_migrations_online() -> None:
    # Tests and embedded callers can migrate the exact connection they use.
    # This is essential for SQLite in-memory databases, whose engines do not
    # share state merely because they have the same URL.
    connection = config.attributes.get("connection")
    if connection is not None:
        if connection.dialect.name == "postgresql" and settings.DATABASE_SCHEMA != "public":
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.DATABASE_SCHEMA}"'))
            connection.execute(text(f'SET search_path TO "{settings.DATABASE_SCHEMA}"'))
        context.configure(connection=connection, target_metadata=target_metadata,
                          version_table_schema=settings.DATABASE_SCHEMA if connection.dialect.name == "postgresql" else None)
        with context.begin_transaction():
            context.run_migrations()
        return

    raw_url = os.getenv("MIGRATION_DATABASE_URL") or os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    connectable = create_database_engine(raw_url, settings, migration=True)

    with connectable.connect() as connection:
        if connection.dialect.name == "postgresql" and settings.DATABASE_SCHEMA != "public":
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.DATABASE_SCHEMA}"'))
            connection.commit()
        context.configure(
            connection=connection, target_metadata=target_metadata,
            version_table_schema=settings.DATABASE_SCHEMA if connection.dialect.name == "postgresql" else None,
        )

        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
