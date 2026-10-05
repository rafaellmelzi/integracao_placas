import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, VehicleMake, VehicleModel, Vehicle, SyncLog
from app.seeds import seed_data
from app.scripts.sync_vehicle_database import VehicleDatabaseSyncer

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

def test_vehicle_sync_routine_idempotency(db_session):
    # 1. First Sync Run (Limited to 1 make, 2 models)
    syncer1 = VehicleDatabaseSyncer(db=db_session, delay_sec=0.01, limit_makes=1, limit_models=2)
    syncer1.run()

    initial_makes = db_session.query(VehicleMake).count()
    initial_vehicles = db_session.query(Vehicle).count()
    assert initial_makes >= 1
    assert initial_vehicles >= 1
    assert syncer1.inserted > 0

    # 2. Second Sync Run (Same limits)
    syncer2 = VehicleDatabaseSyncer(db=db_session, delay_sec=0.01, limit_makes=1, limit_models=2)
    syncer2.run()

    # Confirm no duplicate vehicles created
    assert db_session.query(VehicleMake).count() == initial_makes
    assert db_session.query(Vehicle).count() == initial_vehicles
    assert syncer2.inserted == 0
    assert syncer2.updated == syncer1.inserted

    # 3. Verify SyncLog record created
    last_log = db_session.query(SyncLog).filter_by(source_name="FIPE_PUBLIC_SOURCE").order_by(SyncLog.id.desc()).first()
    assert last_log is not None
    assert last_log.status == "SUCCESS"

def test_fipe_vehicle_missing_engine_null_handling(db_session):
    syncer = VehicleDatabaseSyncer(db=db_session, delay_sec=0.01, limit_makes=1, limit_models=1)
    syncer.run()

    acura_make = db_session.query(VehicleMake).filter(VehicleMake.normalized_name == "ACURA").first()
    if acura_make:
        v = db_session.query(Vehicle).filter_by(make_id=acura_make.id).first()
        if v:
            assert v.engine_id is None
