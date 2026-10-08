"""Fresh migrated database and restored application state for every test."""
import urllib.request

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.database import get_db
from app.main import app
from app.seeds import seed_data


@pytest.fixture(autouse=True)
def isolated_settings_and_network(monkeypatch):
    for key, value in {
        "APP_ENV": "development", "VEHICLE_PROVIDER": "MOCK",
        "VEHICLE_API_KEY": "", "FIPEPLACA_API_KEY": "", "ERP_ENABLED": False,
    }.items():
        monkeypatch.setattr(settings, key, value)
    attempts = []

    def unexpected_request(*args, **kwargs):
        attempts.append("unmocked urllib request")
        raise AssertionError("External HTTP requests must be mocked in tests")

    monkeypatch.setattr(urllib.request, "urlopen", unexpected_request)
    yield
    assert not attempts, "A test attempted an external HTTP request without a mock"


@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    cfg = Config("alembic.ini")
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    monkeypatch.setattr(seed_data, "SessionLocal", factory)
    seed_data.seed_database()
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
