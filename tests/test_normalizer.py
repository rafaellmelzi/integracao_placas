import pytest
from app.services.vehicle_normalizer import normalize_make, normalize_engine
from app.services.query_normalizer import normalize_part_query

def test_vehicle_normalizer():
    # Brand normalization
    assert normalize_make("VW") == "Volkswagen"
    assert normalize_make("volkswagen do brasil") == "Volkswagen"
    assert normalize_make("CHEVROLET") == "Chevrolet"
    assert normalize_make("GM") == "Chevrolet"

    # Engine normalization
    assert normalize_engine("1.0 TSI Turbo Flex") == "1.0 TSI"
    assert normalize_engine("1.4T 16V") == "1.4 TSI"

def test_query_normalizer():
    # Synonym resolution
    cat = normalize_part_query("disco")
    assert cat == "BRAKE_DISC"

    cat2 = normalize_part_query("pastilha dianteira")
    assert cat2 == "BRAKE_PAD"

    cat3 = normalize_part_query("filtro oleo")
    assert cat3 == "OIL_FILTER"
