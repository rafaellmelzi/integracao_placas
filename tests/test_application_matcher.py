import pytest
from app.services.application_matcher import ApplicationMatcher

@pytest.fixture
def renegade_vehicle():
    return {
        "make": "JEEP",
        "model": "RENEGADE",
        "model_year": 2016,
        "engine_displacement": "1.8",
        "fuel": "FLEX",
        "transmission": None,
        "drivetrain": "4X2"
    }

def test_matcher_exact(renegade_vehicle):
    app_text = "RENEGADE 1.8 FLEX 2015/..."
    res = ApplicationMatcher.match_application(renegade_vehicle, app_text)
    assert res["compatibility"] in ("EXACT", "COMPATIBLE")
    assert res["score"] >= 85
    assert len(res["conflicts"]) == 0

def test_matcher_compatible(renegade_vehicle):
    app_text = "JEEP RENEGADE TODOS 15/..."
    res = ApplicationMatcher.match_application(renegade_vehicle, app_text)
    assert res["compatibility"] == "COMPATIBLE"
    assert res["score"] == 85
    assert len(res["conflicts"]) == 0

def test_matcher_conditional(renegade_vehicle):
    # Transmission is UNKNOWN on vehicle but required on application
    app_text = "RENEGADE 1.8 4X2 AUTOMATICO 2015/..."
    res = ApplicationMatcher.match_application(renegade_vehicle, app_text)
    assert res["compatibility"] == "CONDITIONAL"
    assert res["score"] == 75
    assert "transmission required=Automático" in res["unknown"]

def test_matcher_rejected_diesel(renegade_vehicle):
    app_text = "RENEGADE 2.0 DIESEL 2015/..."
    res = ApplicationMatcher.match_application(renegade_vehicle, app_text)
    assert res["compatibility"] == "REJECTED"
    assert res["score"] == 0
    assert len(res["conflicts"]) >= 1

def test_matcher_rejected_displacement(renegade_vehicle):
    app_text = "RENEGADE 2.4 2016/..."
    res = ApplicationMatcher.match_application(renegade_vehicle, app_text)
    assert res["compatibility"] == "REJECTED"
    assert res["score"] == 0

def test_matcher_multi_vehicle_segmentation(renegade_vehicle):
    app_text = "ASTRA 1.8/2.0 1998/2005 -- BLAZER/S10 2.4 2000/2007 -- RENEGADE 2.4 2016/..."
    res = ApplicationMatcher.match_application(renegade_vehicle, app_text)
    assert res["compatibility"] == "REJECTED"
    # Ensure 1.8 from Astra was not applied to Renegade
    assert any("2.4" in c for c in res["conflicts"])

def test_matcher_year_list_matching(renegade_vehicle):
    app_text = "RENEGADE FWD 4X2 2015 2016 2017 2018 2019 2020"
    res = ApplicationMatcher.match_application(renegade_vehicle, app_text)
    assert res["compatibility"] in ("EXACT", "COMPATIBLE")
    assert any("year=2016" in m for m in res["matched"])
