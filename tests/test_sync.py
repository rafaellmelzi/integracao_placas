import os
import json
import pytest
import urllib.error
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, VehicleMake, VehicleModel, Vehicle, SyncLog
from app.seeds import seed_data
from app.scripts.sync_vehicle_database import (
    VehicleDatabaseSyncer, fetch_json, CheckpointManager, stats
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_data.SessionLocal = TestingSessionLocal
    seed_data.seed_database()

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_fetch_json_http_429_retry_after():
    """Test that fetch_json handles HTTP 429 with Retry-After header without throwing or dropping request."""
    mock_headers = {"Retry-After": "1"}
    err_429 = urllib.error.HTTPError(
        url="http://test", code=429, msg="Too Many Requests", hdrs=mock_headers, fp=None
    )

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'[{"codigo": "1", "nome": "Acura"}]'
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen") as mock_urlopen, patch("time.sleep") as mock_sleep:
        mock_urlopen.side_effect = [err_429, mock_resp]

        result = fetch_json("http://test", max_retries=3)
        assert result == [{"codigo": "1", "nome": "Acura"}]
        assert mock_urlopen.call_count == 2
        mock_sleep.assert_called()

def test_fetch_json_http_429_exponential_backoff():
    """Test exponential backoff when Retry-After header is missing."""
    err_429 = urllib.error.HTTPError(
        url="http://test", code=429, msg="Too Many Requests", hdrs={}, fp=None
    )

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"modelos": []}'
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen") as mock_urlopen, patch("time.sleep") as mock_sleep:
        mock_urlopen.side_effect = [err_429, err_429, mock_resp]

        result = fetch_json("http://test", max_retries=4)
        assert result == {"modelos": []}
        assert mock_urlopen.call_count == 3
        assert mock_sleep.call_count == 2

def test_checkpoint_manager(tmp_path):
    checkpoint_file = str(tmp_path / "test_checkpoint.json")
    mgr = CheckpointManager(filepath=checkpoint_file)

    assert not mgr.is_make_completed("1")
    mgr.mark_make_completed("1")
    assert mgr.is_make_completed("1")

    mgr.mark_model_failed("1", "101")
    assert "101" in mgr.data["failed_models"]["1"]

    mgr.mark_model_completed("1", "101")
    assert mgr.is_model_completed("1", "101")
    assert "101" not in mgr.data["failed_models"]["1"]

def test_vehicle_sync_routine_idempotency(db_session, tmp_path):
    checkpoint_path = str(tmp_path / "sync_idempotency_checkpoint.json")

    # 1. First Sync Run (Limited to 1 make, 2 models)
    syncer1 = VehicleDatabaseSyncer(db=db_session, delay_sec=0.01, limit_makes=1, limit_models=2)
    syncer1.checkpoint = CheckpointManager(filepath=checkpoint_path)
    syncer1.run()

    initial_makes = db_session.query(VehicleMake).count()
    initial_vehicles = db_session.query(Vehicle).count()
    assert initial_makes >= 1
    assert initial_vehicles >= 1
    assert syncer1.inserted > 0

    # 2. Second Sync Run (Same limits, resume enabled)
    syncer2 = VehicleDatabaseSyncer(db=db_session, delay_sec=0.01, limit_makes=1, limit_models=2, resume=True)
    syncer2.checkpoint = CheckpointManager(filepath=checkpoint_path)
    syncer2.run()

    # Confirm no duplicate vehicles created
    assert db_session.query(VehicleMake).count() == initial_makes
    assert db_session.query(Vehicle).count() == initial_vehicles
    assert syncer2.inserted == 0

def test_fipe_vehicle_missing_engine_null_handling(db_session, tmp_path):
    checkpoint_path = str(tmp_path / "null_engine_checkpoint.json")

    syncer = VehicleDatabaseSyncer(db=db_session, delay_sec=0.01, limit_makes=1, limit_models=1)
    syncer.checkpoint = CheckpointManager(filepath=checkpoint_path)
    syncer.run()

    acura_make = db_session.query(VehicleMake).filter(VehicleMake.normalized_name == "ACURA").first()
    if acura_make:
        v = db_session.query(Vehicle).filter_by(make_id=acura_make.id).first()
        if v:
            assert v.engine_id is None
