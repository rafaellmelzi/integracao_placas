import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.database import get_db
from app.main import app
from app.seeds.seed_data import seed_database
from app.core.config import settings

# Setup in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        from app.seeds import seed_data
        seed_data.SessionLocal = TestingSessionLocal
        seed_database()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# 1. Healthcheck Endpoint
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "plate_provider" in data

# 2. Plate Lookups (Dev / Mock Mode)
def test_lookup_mercosul_plate():
    response = client.get("/api/v1/vehicles/plate/ABC1D23")
    assert response.status_code == 200
    data = response.json()
    assert data["plate"] == "ABC1D23"
    assert data["status"] == "SUCCESS"
    assert data["vehicle"]["make"] == "Volkswagen"
    assert data["vehicle"]["model"] == "T-Cross"
    assert data["vehicle"]["engine"] == "1.0 TSI"

def test_lookup_old_plate():
    response = client.get("/api/v1/vehicles/plate/ABC1234")
    assert response.status_code == 200
    data = response.json()
    assert data["plate"] == "ABC1234"
    assert data["status"] == "SUCCESS"
    assert data["vehicle"]["model"] == "Gol"

def test_lookup_invalid_plate():
    response = client.get("/api/v1/vehicles/plate/INVALID123")
    assert response.status_code == 400
    data = response.json()
    assert "Invalid Brazilian license plate" in data["detail"]

def test_lookup_ambiguous_vehicle():
    response = client.get("/api/v1/vehicles/plate/AMB1G88")
    assert response.status_code == 200
    data = response.json()
    assert data["is_ambiguous"] is True
    assert data["status"] == "VEHICLE_VARIANT_AMBIGUOUS"

def test_lookup_not_found_plate():
    response = client.get("/api/v1/vehicles/plate/ZZZ9999")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VEHICLE_NOT_FOUND" or data["status"] == "DATA_SOURCE_NOT_CONFIGURED"

# 3. Production Mode unconfigured behavior
def test_production_mode_unconfigured_provider():
    orig_env = settings.APP_ENV
    orig_provider = settings.VEHICLE_PROVIDER
    try:
        settings.APP_ENV = "production"
        settings.VEHICLE_PROVIDER = "MOCK"
        settings.VEHICLE_API_KEY = ""

        response = client.get("/api/v1/vehicles/plate/RRR8888")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DATA_SOURCE_NOT_CONFIGURED"
    finally:
        settings.APP_ENV = orig_env
        settings.VEHICLE_PROVIDER = orig_provider

# 4. Cache Hit Test
def test_cache_hit_performance():
    res1 = client.get("/api/v1/vehicles/plate/XYZ9876")
    assert res1.status_code == 200

    res2 = client.get("/api/v1/vehicles/plate/XYZ9876")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["cache_info"]["from_cache"] is True

# 5. Parts Search
def test_parts_search_brake_disc():
    response = client.get("/api/v1/parts/search?plate=ABC1D23&query=disco%20de%20freio")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["category_identified"] == "BRAKE_DISC"
    assert data["results_count"] >= 1

    first_result = data["results"][0]
    assert first_result["manufacturer"] == "Fremax"
    assert first_result["manufacturer_code"] == "BD1234"
    assert first_result["compatibility"] == "CONFIRMED"
    assert first_result["erp_mapping"]["erp_product_id"] == "AUTCOM-PRD-9988"

def test_parts_search_synonym_query():
    response = client.get("/api/v1/parts/search?plate=ABC1D23&query=disco")
    assert response.status_code == 200
    data = response.json()
    assert data["category_identified"] == "BRAKE_DISC"
    assert data["results_count"] >= 1

def test_parts_search_no_matching_parts():
    response = client.get("/api/v1/parts/search?plate=ABC1234&query=correia%20dentada")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NO_COMPATIBLE_PARTS_FOUND"

# 6. Catalog Importer
def test_catalog_importer_csv():
    csv_content = """fabricante,codigo,categoria,descricao,marca_veiculo,modelo_veiculo,motor,ano_inicio,ano_fim
Bosch,0986BB0001,Filtro de Oleo,Filtro Lubrificante,VW,T-Cross,1.0 TSI,2019,2024
"""
    response = client.post(
        "/api/v1/catalog/import",
        files={"file": ("test_catalog.csv", csv_content, "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["success"] == 1

# 7. ERP Product Mapping
def test_create_erp_mapping():
    payload = {
        "erp_product_id": "AUTCOM-PRD-5544",
        "manufacturer_code": "N-1234",
        "ean": "7891234567892",
        "mapping_type": "MANUFACTURER_CODE",
        "verified": True
    }
    response = client.post("/api/v1/erp/mapping", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
