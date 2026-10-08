import io
import logging
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from app.core.config import Settings, settings
from app.core.security import install_log_redaction, redact
from app.db.connection import create_database_engine
from app.services.parts_compatibility_service import PartsCompatibilityService
from app.services.plate_lookup_service import PlateLookupService


def cloud_settings(**changes):
    values = dict(APP_ENV="production", DEPLOYMENT_MODE="cloud", DATABASE_URL="postgresql://user:placeholder@host/postgres",
                  DB_SSL_MODE="require", API_ACCESS_TOKEN="x" * 32, VEHICLE_PROVIDER="FIPEPLACA",
                  FIPE_SYNC_ENABLED=False, FIPE_AUTO_UPDATE=False)
    values.update(changes)
    return Settings(**values)


@pytest.mark.parametrize("changes", [{"DATABASE_URL": "sqlite://"}, {"DB_SSL_MODE": "disable"},
    {"VEHICLE_PROVIDER": "MOCK"}, {"PARTS_PROVIDER": "MOCK"}, {"API_ACCESS_TOKEN": "short"}, {"FIPE_SYNC_ENABLED": True}, {"FIPE_AUTO_UPDATE": True}])
def test_unsafe_cloud_configuration_fails(changes):
    with pytest.raises(ValidationError):
        cloud_settings(**changes)


def test_pool_and_tls_configuration_without_connecting():
    config = cloud_settings(DATABASE_SCHEMA="integracao_placas")
    engine = create_database_engine(config.DATABASE_URL, config)
    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.pool.size() == 2
    assert engine.pool._max_overflow == 0
    assert engine.hide_parameters is True
    engine.dispose()


def test_cloud_never_initializes_private_mysql(client, monkeypatch):
    monkeypatch.setattr(settings, "DEPLOYMENT_MODE", "cloud")
    monkeypatch.setattr(settings, "API_ACCESS_TOKEN", "x" * 32)
    monkeypatch.setattr(settings, "ERP_ENABLED", True)
    connector = MagicMock(side_effect=AssertionError("private MySQL must not be initialized"))
    monkeypatch.setattr("app.services.parts_compatibility_service.MySQLERPConnector", connector)
    monkeypatch.setattr(PlateLookupService, "get_or_fetch_plate", lambda self, plate: {
        "status": "SUCCESS", "vehicle": {"make": "Jeep", "model": "Renegade", "engine": "1.8", "year_model": 2016}})
    denied = client.get("/api/v1/vehicles/plate/OHF1I18/parts")
    assert denied.status_code == 401
    response = client.get("/api/v1/vehicles/plate/OHF1I18/parts", headers={"X-API-Key": "x" * 32})
    assert response.status_code == 200
    data = response.json()
    assert data["erp_status"] == "PRIVATE_NETWORK_UNAVAILABLE"
    assert data["availability_status"] == "NOT_QUERIED"
    assert data["erp_enabled"] is False
    assert data["parts_count"] == 0 and data["parts"] == []
    connector.assert_not_called()


def test_local_connector_stays_enabled(monkeypatch):
    for key, value in {"DEPLOYMENT_MODE": "local", "ERP_ENABLED": True, "ERP_DB_HOST": "client-db",
                       "ERP_DB_NAME": "autcom", "ERP_DB_TYPE": "mysql"}.items():
        monkeypatch.setattr(settings, key, value)
    connector = MagicMock()
    monkeypatch.setattr("app.services.parts_compatibility_service.MySQLERPConnector", connector)
    service = PartsCompatibilityService(None)
    assert service.connector is connector.return_value
    connector.assert_called_once()


def test_ready_requires_migrations_and_does_not_query_erp(client, db_session):
    from sqlalchemy import text
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    db_session.execute(text("UPDATE alembic_version SET version_num='old_revision'"))
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["database"] == "migration_required"


def test_readiness_hides_database_exception():
    from app.health import readiness
    db = MagicMock()
    db.execute.side_effect = RuntimeError("password SUPER_SECRET")
    response = readiness(db)
    assert response.status_code == 503
    assert b"SUPER_SECRET" not in response.body


def test_cloud_sync_disabled_and_admin_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings, "DEPLOYMENT_MODE", "cloud")
    monkeypatch.setattr(settings, "API_ACCESS_TOKEN", "x" * 32)
    monkeypatch.setattr(settings, "FIPE_SYNC_ENABLED", False)
    assert client.post("/api/v1/vehicles/sync", headers={"X-API-Key": "x" * 32}).status_code == 503
    assert client.get("/admin").status_code == 404


def test_logs_redact_credentials_in_arguments_and_tracebacks(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://role:s%23cret@host/db")
    monkeypatch.setenv("FIPEPLACA_API_KEY", "API_SENTINEL")
    monkeypatch.setenv("ERP_DB_PASSWORD", "ERP_SENTINEL")
    install_log_redaction()
    logger = logging.getLogger("cloud_redaction_test")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    try:
        logger.error("credentials %s %s", "s#cret", "API_SENTINEL")
        try:
            raise RuntimeError("ERP_SENTINEL postgres://role:unlisted@host/db Bearer opaque_token")
        except RuntimeError:
            logger.exception("connection failed")
    finally:
        logger.removeHandler(handler)
    output = stream.getvalue()
    for secret in ("s#cret", "s%23cret", "API_SENTINEL", "ERP_SENTINEL", "unlisted", "opaque_token"):
        assert secret not in output
    assert "[REDACTED]" in output


def test_dynamic_port_entrypoint(monkeypatch):
    from app.start import main
    run = MagicMock()
    monkeypatch.setattr("app.start.uvicorn.run", run)
    monkeypatch.setenv("PORT", "9123")
    main()
    assert run.call_args.kwargs["port"] == 9123
    assert run.call_args.kwargs["workers"] == 1


def test_disabled_fipe_auto_update_does_not_fetch_empty_catalog(db_session, monkeypatch):
    from app.services.fipe_service import FipeService
    from app.db.models import VehicleMake
    monkeypatch.setattr(settings, "FIPE_AUTO_UPDATE", False)
    db_session.query(VehicleMake).delete()
    provider = MagicMock()
    service = FipeService(db_session, provider=provider)
    assert service.get_makes_ondemand() == []
    provider.get_reference_period.assert_not_called()
    provider.get_makes.assert_not_called()
