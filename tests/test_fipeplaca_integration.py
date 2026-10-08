import pytest
from unittest.mock import patch, MagicMock

from app.providers.fipeplaca_provider import FipePlacaProvider
from app.services.plate_lookup_service import PlateLookupService
from app.services.parts_compatibility_service import PartsCompatibilityService
from app.integrations.erp.models import ERPProduct, ERPAvailability

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

def test_parts_compatibility_endpoint_with_ohf1i18(db_session, mock_ohf1i18_payload, client):
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
        assert data["parts"][0]["compatibility"] == "CONDITIONAL"
        assert data["parts"][0]["requires_confirmation"] is True
        assert "drivetrain=4X2" in data["parts"][0]["match_details"]["unknown"]


def test_endpoint_filters_conflicts_and_preserves_conditional_on_cache_hit(
        client, mock_ohf1i18_payload, monkeypatch):
    from app.core.config import settings
    from app.schemas.schemas import PlatePartsResponseSchema

    monkeypatch.setattr(settings, "VEHICLE_PROVIDER", "FIPEPLACA")
    applications = {
        "compatible": "JEEP RENEGADE 1.8 FLEX 2015/...",
        "automatic": "RENEGADE 1.8 FLEX AUT 2016/...",
        "manual": "RENEGADE 1.8 FLEX MEC 2016/...",
        "cvt": "RENEGADE 1.8 FLEX CVT 2016/...",
        "wrong_engine": "RENEGADE 2.4 2016/...",
        "wrong_year": "RENEGADE 1.8 FLEX 2017/...",
        "wrong_fuel": "JEEP RENEGADE / SPORT - ANO: 15/... (GNV)",
        "comma": "ASTRA 1.8 FLEX 2015/..., RENEGADE 2.4 2016/...",
        "dashes": "ASTRA 1.8 FLEX 2015/...--RENEGADE 2.4 2016/...",
        "empty": "",
        "unmatched": "COMPASS TODOS 2015/...",
    }
    connector = MagicMock()
    connector.fetch_products.return_value = [
        ERPProduct(code, None, "Test part", None, application)
        for code, application in applications.items()
    ]
    connector.fetch_availability.return_value = [ERPAvailability("compatible", "001", 10, 20)]
    expected = {"compatible", "automatic", "manual", "cvt"}
    with patch.object(PartsCompatibilityService, "_init_connector", return_value=connector), \
         patch.object(FipePlacaProvider, "fetch_plate_info", return_value=("SUCCESS", mock_ohf1i18_payload)) as provider:
        for _ in range(2):
            response = client.get("/api/v1/vehicles/plate/OHF1I18/parts")
            assert response.status_code == 200
            data = response.json()
            PlatePartsResponseSchema.model_validate(data)
            assert data["parts_count"] == len(data["parts"]) == 4
            assert {p["internal_code"] for p in data["parts"]} == expected
            assert data["vehicle"]["year_model"] == 2016
            assert data["vehicle"]["year_manufacture"] == 2015
            assert data["vehicle"]["engine"] == "1.8"
            assert data["vehicle"]["transmission"] is None
            for part in data["parts"]:
                details = part["match_details"]
                assert "year=2016" in details["matched"]
                assert "engine=1.8" in details["matched"]
                assert "fuel=FLEX" in details["matched"]
                assert not details["conflicts"]
                if part["internal_code"] == "compatible":
                    assert part["compatibility"] == "COMPATIBLE"
                    assert part["requires_confirmation"] is False
                    assert not details["unknown"]
                    assert part["availability"][0]["stock"] == 10
                else:
                    assert part["compatibility"] == "CONDITIONAL"
                    assert part["requires_confirmation"] is True
                    assert any(item.startswith("transmission=") for item in details["unknown"])
            assert set(connector.fetch_availability.call_args.args[1]) == expected
        assert provider.call_count == 1


@pytest.mark.parametrize("scenario", ["disabled", "no_products", "only_incompatible", "query_error", "not_found"])
def test_endpoint_empty_result_contract(client, monkeypatch, scenario):
    from app.schemas.schemas import PlatePartsResponseSchema

    connector = None if scenario == "disabled" else MagicMock()
    vehicle = dict(make="Jeep", model="Renegade", year_model=2016, year_manufacture=2015,
                   engine="1.8", fuel="FLEX", transmission=None)
    plate_response = {"status": "SUCCESS", "vehicle": vehicle}
    if scenario == "not_found":
        plate_response = {"status": "VEHICLE_NOT_FOUND", "vehicle": None}
    if connector:
        connector.fetch_products.return_value = [] if scenario == "no_products" else [
            ERPProduct("bad", None, "Wrong engine", None, "RENEGADE 2.4 2016/...")]
        if scenario == "query_error":
            connector.fetch_products.side_effect = RuntimeError("test connection unavailable")
    with patch.object(PartsCompatibilityService, "_init_connector", return_value=connector), \
         patch.object(PlateLookupService, "get_or_fetch_plate", return_value=plate_response):
        response = client.get("/api/v1/vehicles/plate/OHF1I18/parts")
        assert response.status_code == 200
        data = response.json()
        PlatePartsResponseSchema.model_validate(data)
        assert data["parts_count"] == 0
        assert data["parts"] == []
        if connector:
            connector.fetch_availability.assert_not_called()
        if scenario == "query_error":
            assert data["error"]
