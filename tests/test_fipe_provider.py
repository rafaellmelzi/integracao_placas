from unittest.mock import patch

from app.providers.tabelafipe_provider import TabelaFipeProvider
from app.services.fipe_service import FipeService


def test_tabelafipe_provider_get_makes():
    provider = TabelaFipeProvider(delay_sec=0.0)
    mock_resp = {"tipo": "carros", "count": 2, "brands": [{"slug": "fiat", "name": "Fiat"}, {"slug": "ford", "name": "Ford"}]}
    with patch.object(provider, "fetch_json", return_value=mock_resp):
        makes = provider.get_makes("carros")
        assert len(makes) == 2
        assert makes[0]["slug"] == "fiat"

def test_fipe_service_on_demand_caching(db_session):
    provider = TabelaFipeProvider(delay_sec=0.0)
    mock_family_resp = {
        "tipo": "carros",
        "marca": "VW - VolksWagen",
        "familia": "T-Cross",
        "precos": [
            {
                "versao": "T-Cross 1.0 TSI Flex 12V 5p Aut.",
                "ano": 2023,
                "combustivel": "Flex",
                "codigo_fipe": "005512-3"
            }
        ]
    }
    with patch.object(provider, "get_family_prices", return_value=mock_family_resp) as prices, \
         patch.object(provider, "get_models_by_make", return_value={"families": [{"slug": "t-cross", "name": "T-Cross"}]}), \
         patch.object(provider, "get_reference_period", return_value={"label": "outubro/2026"}):
        service = FipeService(db=db_session, provider=provider)
        vehicles = service.get_or_fetch_vehicles("Volkswagen", "T-Cross", 2023)
        assert len(vehicles) >= 1
        assert vehicles[0].fipe_code == "005512-3"
        assert prices.call_count == 1
        cached = service.get_or_fetch_vehicles("Volkswagen", "T-Cross", 2023)
        assert {v.id for v in cached} == {v.id for v in vehicles}
        assert prices.call_count == 1
