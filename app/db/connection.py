"""Shared SQLAlchemy configuration for application and migrations."""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def database_url(raw: str):
    try:
        url = make_url(raw)
    except Exception:
        raise ValueError("Invalid database connection configuration") from None
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    return url


def create_database_engine(raw: str, config, *, migration=False):
    url = database_url(raw)
    options = dict(pool_pre_ping=True, hide_parameters=True, echo=False)
    if url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
    elif url.get_backend_name() == "postgresql":
        args = {"connect_timeout": config.DB_CONNECT_TIMEOUT}
        if config.DB_SSL_MODE:
            args["sslmode"] = config.DB_SSL_MODE
        options["connect_args"] = args
        if not migration:
            options.update(pool_size=config.DB_POOL_SIZE, max_overflow=config.DB_MAX_OVERFLOW,
                           pool_timeout=config.DB_POOL_TIMEOUT, pool_recycle=300)
    if migration:
        options["poolclass"] = NullPool
    engine = create_engine(url, **options)
    if url.get_backend_name() == "postgresql":
        # Session poolers may ignore startup options. Set these on the actual
        # server session outside a transaction so a rollback cannot undo them.
        @event.listens_for(engine, "connect")
        def configure_session(dbapi_connection, _record):
            previous = dbapi_connection.autocommit
            dbapi_connection.autocommit = True
            try:
                with dbapi_connection.cursor() as cursor:
                    cursor.execute(f'SET search_path TO "{config.DATABASE_SCHEMA}"')
                    cursor.execute(f"SET statement_timeout TO {int(config.DB_STATEMENT_TIMEOUT_MS)}")
            finally:
                dbapi_connection.autocommit = previous
    return engine
