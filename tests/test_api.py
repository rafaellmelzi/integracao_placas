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
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")

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

# 2. Cascading Vehicle Dropdowns
def test_get_vehicle_makes():
    response = client.get("/api/v1/vehicles/makes")
    assert response.status_code == 200
    makes = response.json()
    assert len(makes) >= 1
    make_names = [m["name"] for m in makes]
    assert "Volkswagen" in make_names

def test_get_vehicle_models():
    # Get Volkswagen ID
    makes_res = client.get("/api/v1/vehicles/makes")
    vw_id = [m["id"] for m in makes_res.json() if m["name"] == "Volkswagen"][0]

    response = client.get(f"/api/v1/vehicles/makes/{vw_id}/models")
    assert response.status_code == 200
    models = response.json()
    model_names = [m["name"] for m in models]
    assert "T-Cross" in model_names

# 3. Direct Vehicle Parts Search (Marca -> Modelo -> Ano -> Engine)
def test_direct_vehicle_parts_search():
    response = client.get("/api/v1/parts/search?make=Volkswagen&model=T-Cross&year=2023&engine=1.0%20TSI&query=disco%20de%20freio")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["results_count"] >= 1
    assert data["results"][0]["manufacturer"] == "Fremax"
    assert data["results"][0]["manufacturer_code"] == "BD1234"

def test_strict_motorization_filtering_prevention():
    # Search for 1.4 TSI should not return parts exclusive to 1.0 TSI
    response = client.get("/api/v1/parts/search?make=Volkswagen&model=T-Cross&year=2023&version=Highline%20250%20TSI&engine=1.4%20TSI&query=disco%20de%20freio")
    assert response.status_code == 200
    data = response.json()
    assert data["results_count"] == 0
    assert data["status"] == "NO_COMPATIBLE_PARTS_FOUND"

# 4. Plate Lookups
def test_lookup_mercosul_plate():
    response = client.get("/api/v1/vehicles/plate/ABC1D23")
    assert response.status_code == 200
    data = response.json()
    assert data["plate"] == "ABC1D23"
    assert data["status"] == "SUCCESS"
    assert data["vehicle"]["make"] == "Volkswagen"
    assert data["vehicle"]["model"] == "T-Cross"

def test_lookup_invalid_plate():
    response = client.get("/api/v1/vehicles/plate/INVALID123")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INVALID_PLATE"

# 5. Production Mode Unconfigured Provider
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
        assert data["status"] == "PROVIDER_NOT_CONFIGURED"
    finally:
        settings.APP_ENV = orig_env
        settings.VEHICLE_PROVIDER = orig_provider

# 6. Universal Catalog Importer
def test_catalog_importer_csv():
    csv_content = """fabricante,codigo,categoria,descricao,marca_veiculo,modelo_veiculo,motor,ano_inicio,ano_fim,oem
Bosch,0986BB0001,Filtro de Oleo,Filtro Lubrificante,VW,T-Cross,1.0 TSI,2019,2024,04E115561H
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
