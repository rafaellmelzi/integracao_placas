import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.providers.fipeplaca_provider import FipePlacaProvider
from app.services.plate_lookup_service import PlateLookupService
from app.services.parts_compatibility_service import PartsCompatibilityService
from app.integrations.erp.models import ERPProduct, ERPAvailability
from app.db.models import Base
from app.seeds import seed_data
from app.main import app
from app.db.database import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_module_db():
    Base.metadata.create_all(bind=engine)
    seed_data.SessionLocal = TestingSessionLocal
    seed_data.seed_database()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def override_db_dependency():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)

client = TestClient(app)

@pytest.fixture
def mock_ohf1i18_payload():
    return {
        "plate": "OHF1I18",
        "vehicle": {
            "make": "JEEP",
            "model": "RENEGADE",
            "manufacture_year": 2015,
            "model_year": 2016,
            "engine_displacement": "1.8",
            "power_cv": 132,
            "fuel": "FLEX",
            "color": "VERDE",
            "transmission": None
        },
        "identification": {
            "status": "PARTIAL",
            "exact_version": False,
            "candidate_count": 5
        },
        "fipe_candidates": [
            {
                "fipe_code": "017062-3",
                "description": "Renegade 1.8 4x2 Flex 16V Aut.",
                "model_year": 2016,
                "fuel": "Flex",
                "confidence": "alta",
                "year_match": True,
                "fuel_match": True
            },
            {
                "fipe_code": "017040-2",
                "description": "Renegade 1.8 4x2 Flex 16V Mec.",
                "model_year": 2016,
                "fuel": "Flex",
                "confidence": "alta",
                "year_match": True,
                "fuel_match": True
            },
            {
                "fipe_code": "017034-8",
                "description": "Renegade Sport 1.8 4x2 Flex 16V Aut.",
                "model_year": 2016,
                "fuel": "Flex",
                "confidence": "alta",
                "year_match": True,
                "fuel_match": True
            },
            {
                "fipe_code": "017033-0",
                "description": "Renegade Sport 1.8 4x2 Flex 16V Mec.",
                "model_year": 2016,
                "fuel": "Flex",
                "confidence": "alta",
                "year_match": True,
                "fuel_match": True
            },
            {
                "fipe_code": "017043-7",
                "description": "Renegade 75 Anos 1.8 4X2 Flex 16V Aut.",
                "model_year": 2016,
                "fuel": "Flex",
                "confidence": "alta",
                "year_match": True,
                "fuel_match": True
            }
        ],
        "provider": "FIPEPLACA",
        "cached": False
    }

def test_fipeplaca_ohf1i18_canonical_adaptation_and_caching(db_session, mock_ohf1i18_payload):
    service = PlateLookupService(db=db_session)
    provider = FipePlacaProvider(api_key="secret_test_key")

    with patch.object(provider, "fetch_plate_info", return_value=("SUCCESS", mock_ohf1i18_payload)):
        service.providers = [provider]

        # Call 1: Provider Query + Persistence (Cache Miss)
        res1 = service.get_or_fetch_plate("OHF1I18")
        assert res1["status"] in ("SUCCESS", "VEHICLE_VARIANT_AMBIGUOUS")
        assert res1["vehicle"] is not None
        assert res1["vehicle"]["make"] == "Jeep"
        assert res1["vehicle"]["model"] == "Renegade"
        assert res1["vehicle"]["year_manufacture"] == 2015
        assert res1["vehicle"]["year_model"] == 2016
        assert res1["vehicle"]["engine"] == "1.8"
        assert res1["vehicle"]["fuel"].upper() == "FLEX"
        assert res1["vehicle"]["transmission"] is None  # Transmission is NULL due to automatic/manual ambiguity
        assert res1["cache_info"]["from_cache"] is False
        assert len(res1["fipe_candidates"]) == 5
        assert res1["identification"]["candidate_count"] == 5
        assert res1["identification"]["exact_version"] is False
        assert res1["identification"]["status"] == "PARTIAL"

        # Call 2: PostgreSQL Cache Hit
        res2 = service.get_or_fetch_plate("OHF1I18")
        assert res2["status"] in ("SUCCESS", "VEHICLE_VARIANT_AMBIGUOUS")
        assert res2["vehicle"] is not None
        assert res2["vehicle"]["make"] == "Jeep"
        assert res2["vehicle"]["model"] == "Renegade"
        assert res2["cache_info"]["from_cache"] is True
        assert len(res2["fipe_candidates"]) == 5

def test_parts_compatibility_endpoint_with_ohf1i18(db_session, mock_ohf1i18_payload):
    mock_products = [
        ERPProduct(
            internal_code="52384",
            factory_code="AMD2410",
            description="AMORT DT LADO DIREITO",
            brand="PERFE",
            application="JEEP RENEGADE FWD 4X2 2015/..."
        )
    ]
    mock_avail = [
        ERPAvailability(internal_code="52384", company="001", stock=10.0, price=290.18)
    ]

    mock_provider = FipePlacaProvider(api_key="secret_test_key")

    with patch.object(mock_provider, "fetch_plate_info", return_value=("SUCCESS", mock_ohf1i18_payload)), \
         patch.object(PartsCompatibilityService, "_init_connector") as mock_init:

        mock_connector = MagicMock()
        mock_connector.fetch_products.return_value = mock_products
        mock_connector.fetch_availability.return_value = mock_avail
        mock_init.return_value = mock_connector

        def side_effect_service(db):
            s = PartsCompatibilityService(db)
            s.plate_service.providers = [mock_provider]
            s.connector = mock_connector
            return s

        with patch("app.api.endpoints.PartsCompatibilityService", side_effect=side_effect_service):
            response = client.get("/api/v1/vehicles/plate/OHF1I18/parts")
        assert response.status_code == 200
        data = response.json()

        assert data["plate"] == "OHF1I18"
        assert data["vehicle"] is not None
        assert data["vehicle"]["make"] == "Jeep"
        assert data["vehicle"]["model"] == "Renegade"
        assert data["vehicle"]["year_model"] == 2016
        assert len(data["parts"]) == 1
        assert data["parts"][0]["internal_code"] == "52384"
        assert data["parts"][0]["compatibility"] == "COMPATIBLE"
