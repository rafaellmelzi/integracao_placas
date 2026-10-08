from unittest.mock import patch

from app.providers.fipeplaca_provider import FipePlacaProvider
from app.services.plate_lookup_service import PlateLookupService


def test_fipeplaca_provider_valid_plate_direct_list_format():
    """Test FipePlacaProvider when /fipe endpoint returns direct list [...] format."""
    provider = FipePlacaProvider(api_key="valid_key_123")
    basic_resp = (200, {
        "marca": "JEEP",
        "modelo": "RENEGADE",
        "anoFabricacao": 2015,
        "anoModelo": 2016,
        "cor": "VERDE",
        "cilindradas": 1800,
        "potencia": 132,
        "combustivel": "ALCOOL / GASOLINA"
    })
    fipe_direct_list_resp = (200, [
        {"codigoFipe": "017062-3", "modelo": "Renegade 1.8 4x2 Flex 16V Aut.", "anoModelo": 2016, "combustivel": "Flex"},
        {"codigoFipe": "017040-2", "modelo": "Renegade 1.8 4x2 Flex 16V Mec.", "anoModelo": 2016, "combustivel": "Flex"},
        {"codigoFipe": "017034-8", "modelo": "Renegade Sport 1.8 4x2 Flex 16V Aut.", "anoModelo": 2016, "combustivel": "Flex"},
        {"codigoFipe": "017033-0", "modelo": "Renegade Sport 1.8 4x2 Flex 16V Mec.", "anoModelo": 2016, "combustivel": "Flex"},
        {"codigoFipe": "017043-7", "modelo": "Renegade 75 Anos 1.8 4X2 Flex 16V Aut.", "anoModelo": 2016, "combustivel": "Flex"}
    ])

    with patch.object(provider, "_make_request", side_effect=[basic_resp, fipe_direct_list_resp]):
        status, payload = provider.fetch_plate_info("OHF1I18")
        assert status == "SUCCESS"
        assert payload["plate"] == "OHF1I18"
        assert payload["vehicle"]["make"] == "Jeep"
        assert payload["vehicle"]["model"] == "Renegade"
        assert payload["vehicle"]["engine_displacement"] == "1.8"
        assert payload["vehicle"]["power_cv"] == 132
        assert payload["vehicle"]["fuel"] == "FLEX"
        assert payload["vehicle"]["transmission"] is None  # Ambiguous automatic and manual candidates -> transmission = None
        assert payload["identification"]["candidate_count"] == 5
        assert payload["identification"]["exact_version"] is False
        assert payload["identification"]["status"] == "PARTIAL"

def test_fipeplaca_provider_valid_plate_wrapper_dict_format():
    """Test FipePlacaProvider when /fipe endpoint returns dict wrapper {"value": [...]} format."""
    provider = FipePlacaProvider(api_key="valid_key_123")
    basic_resp = (200, {
        "marca": "JEEP",
        "modelo": "RENEGADE",
        "anoFabricacao": 2015,
        "anoModelo": 2016,
        "cor": "VERDE",
        "cilindradas": 1800,
        "potencia": 132,
        "combustivel": "ALCOOL / GASOLINA"
    })
    fipe_wrapper_dict_resp = (200, {
        "value": [
            {"codigoFipe": "017062-3", "modelo": "Renegade 1.8 4x2 Flex 16V Aut.", "anoModelo": 2016},
            {"codigoFipe": "017040-2", "modelo": "Renegade 1.8 4x2 Flex 16V Mec.", "anoModelo": 2016}
        ],
        "Count": 2
    })

    with patch.object(provider, "_make_request", side_effect=[basic_resp, fipe_wrapper_dict_resp]):
        status, payload = provider.fetch_plate_info("OHF1I18")
        assert status == "SUCCESS"
        assert payload["identification"]["candidate_count"] == 2

def test_fipeplaca_provider_invalid_plate():
    provider = FipePlacaProvider(api_key="valid_key_123")
    status, payload = provider.fetch_plate_info("INVALID123")
    assert status == "INVALID_PLATE"
    assert payload is None

def test_fipeplaca_provider_unconfigured_api_key():
    provider = FipePlacaProvider(api_key="")
    status, payload = provider.fetch_plate_info("OHF1I18")
    assert status == "PROVIDER_NOT_CONFIGURED"
    assert payload is None

def test_fipeplaca_provider_http_401_unauthorized():
    provider = FipePlacaProvider(api_key="invalid_key")
    with patch.object(provider, "_make_request", return_value=(401, None)):
        status, payload = provider.fetch_plate_info("OHF1I18")
        assert status == "PROVIDER_AUTHENTICATION_ERROR"

def test_fipeplaca_provider_http_402_insufficient_credits():
    provider = FipePlacaProvider(api_key="valid_key")
    with patch.object(provider, "_make_request", return_value=(402, None)):
        status, payload = provider.fetch_plate_info("OHF1I18")
        assert status == "PROVIDER_INSUFFICIENT_CREDITS"

def test_fipeplaca_provider_http_429_rate_limit():
    provider = FipePlacaProvider(api_key="valid_key")
    with patch.object(provider, "_make_request", return_value=(429, None)):
        status, payload = provider.fetch_plate_info("OHF1I18")
        assert status == "PROVIDER_RATE_LIMIT"

def test_fipeplaca_provider_log_sanitization():
    provider = FipePlacaProvider(api_key="SECRET_KEY_999")
    msg = f"Error connecting to API with Bearer {provider.api_key}"
    sanitized = provider._sanitize_log_message(msg)
    assert "SECRET_KEY_999" not in sanitized
    assert "***API_KEY_HIDDEN***" in sanitized

def test_plate_lookup_cache_hit_and_miss(db_session):
    service = PlateLookupService(db=db_session)
    mock_info = {
        'make': 'Jeep',
        'model': 'Renegade',
        'year_manufacture': 2015,
        'year_model': 2016,
        'engine': '1.8',
        'fuel': 'Flex',
        'fipe_code': '017062-3',
        'raw_response_hash': 'hash_test_123',
        'raw_data': {}
    }
    mock_provider = FipePlacaProvider(api_key="secret_key_123")
    with patch.object(mock_provider, 'fetch_plate_info', return_value=('SUCCESS', mock_info)):
        service.providers = [mock_provider]

        # Call 1: Cache Miss
        res1 = service.get_or_fetch_plate('OHF1I18')
        assert res1['status'] == 'SUCCESS'
        assert res1['cache_info']['from_cache'] is False

        # Call 2: Cache Hit
        res2 = service.get_or_fetch_plate('OHF1I18')
        assert res2['status'] == 'SUCCESS'
        assert res2['cache_info']['from_cache'] is True
