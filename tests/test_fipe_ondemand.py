from unittest.mock import patch

from app.db.models import VehicleMake, VehicleModel
from app.services.fipe_service import FipeService
from app.providers.tabelafipe_provider import TabelaFipeProvider


def test_ondemand_models_expansion_chevrolet(db_session):
    """
    Test scenario: Chevrolet initially has only 1 model (Onix).
    GET /vehicles/makes/{chevrolet_id}/models detects incomplete cache and queries provider,
    performing UPSERT of all returned Chevrolet models (Astra, Blazer, Corsa, etc.).
    A second call uses valid PostgreSQL cache without external API calls.
    """
    gm = db_session.query(VehicleMake).filter_by(name="Chevrolet").first()
    assert gm is not None

    mock_models_resp = {
        "tipo": "carros",
        "marca": "chevrolet",
        "count": 3,
        "families": [
            {"slug": "onix", "name": "Onix"},
            {"slug": "astra", "name": "Astra"},
            {"slug": "cruze", "name": "Cruze"}
        ]
    }

    provider = TabelaFipeProvider(delay_sec=0.0)
    with patch.object(provider, "get_reference_period", return_value={"label": "outubro/2026"}), \
         patch.object(provider, "get_models_by_make", return_value=mock_models_resp) as mock_get_models:

        service = FipeService(db=db_session, provider=provider)
        models = service.get_models_ondemand(gm.id)

        assert len(models) >= 3
        model_names = [m.name for m in models]
        assert "Onix" in model_names
        assert "Astra" in model_names
        assert "Cruze" in model_names
        assert mock_get_models.call_count == 1

        # Second call: must hit PostgreSQL cache and NOT call API provider again
        mock_get_models.reset_mock()
        models_cached = service.get_models_ondemand(gm.id)
        assert len(models_cached) >= 3
        assert mock_get_models.call_count == 0

def test_ondemand_years_and_versions(db_session):
    """
    Test scenario: Model -> Years -> Versions cascading on-demand.
    """
    vw = db_session.query(VehicleMake).filter_by(name="Volkswagen").first()
    tcross = db_session.query(VehicleModel).filter_by(make_id=vw.id, name="T-Cross").first()

    mock_family_resp = {
        "tipo": "carros",
        "marca": "VW - VolksWagen",
        "familia": "T-Cross",
        "precos": [
            {"versao": "T-Cross 1.0 TSI", "ano": 2023, "combustivel": "Flex", "codigo_fipe": "005512-3"},
            {"versao": "T-Cross 1.4 TSI", "ano": 2022, "combustivel": "Flex", "codigo_fipe": "005513-1"}
        ]
    }

    provider = TabelaFipeProvider(delay_sec=0.0)
    with patch.object(provider, "get_reference_period", return_value={"label": "outubro/2026"}), \
         patch.object(provider, "get_family_prices", return_value=mock_family_resp) as mock_get_prices:

        service = FipeService(db=db_session, provider=provider)
        years = service.get_years_ondemand(tcross.id)
        assert 2023 in years
        assert 2022 in years

        versions = service.get_versions_ondemand(tcross.id, 2023)
        assert len(versions) >= 1
        assert versions[0]["fipe_code"] == "005512-3"

def test_offline_fallback_when_provider_unavailable(db_session):
    """
    Test scenario: When external FIPE API is unavailable but local DB cache exists,
    system falls back safely to local PostgreSQL records without raising error or corrupting DB.
    """
    vw = db_session.query(VehicleMake).filter_by(name="Volkswagen").first()
    provider = TabelaFipeProvider(delay_sec=0.0)

    with patch.object(provider, "get_reference_period", return_value=None), \
         patch.object(provider, "get_models_by_make", return_value=None):

        service = FipeService(db=db_session, provider=provider)
        models = service.get_models_ondemand(vw.id)
        assert len(models) >= 1
        model_names = [m.name for m in models]
        assert "T-Cross" in model_names

def test_background_sync_endpoint(client):
    """
    Test scenario: POST /vehicles/sync returns HTTP 202 Accepted immediately.
    """
    with patch("app.api.endpoints.run_background_sync"):
        response = client.post("/api/v1/vehicles/sync?limit_makes=1")
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "SYNC_STARTED"
