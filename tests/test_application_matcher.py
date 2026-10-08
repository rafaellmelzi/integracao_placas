import pytest
from app.services.application_matcher import ApplicationMatcher

@pytest.fixture
def renegade_flex_18_2016():
    """
    Standard test vehicle: Jeep Renegade 2016 1.8 FLEX
    transmission = None (unknown)
    """
    return {
        "make": "JEEP",
        "model": "RENEGADE",
        "model_year": 2016,
        "manufacture_year": 2015,
        "engine_displacement": "1.8",
        "fuel": "FLEX",
        "transmission": None,
        "drivetrain": None
    }

# CASE 1: JEEP RENEGADE / SPORT - ANO: 15/... (GNV). -> INCOMPATIBLE (fuel mismatch)
def test_case_1_fuel_gnv_conflict(renegade_flex_18_2016):
    app_text = "JEEP RENEGADE / SPORT - ANO: 15/... (GNV)."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "INCOMPATIBLE"
    assert any("fuel" in c.lower() for c in res["conflicts"])

# CASE 2: Multi-vehicle string ending in RENEGADE 2.4 2016/... -> INCOMPATIBLE (engine mismatch)
def test_case_2_multi_vehicle_engine_mismatch(renegade_flex_18_2016):
    app_text = "ASTRA 1.8/2.0 1998/2005 -- BLAZER/S10 2.4 2000/2007 -- BLAZER/S10 2.2 1997/2000 -- ZAFIRA 2.0 2001/2005 -- XANTIA 2.0 1995/1998 -- FREEMONT 2.4 2012/... -- TORO 2.4 2017/... -- RENEGADE 2.4 2016/..."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "INCOMPATIBLE"
    assert any("engine" in c.lower() for c in res["conflicts"])

# CASE 3: Multi-application text with one matching segment -> COMPATIBLE
def test_case_3_at_least_one_compatible_segment(renegade_flex_18_2016):
    app_text = """
    RENEGADE 2.0 4X4 2015/...
    RENEGADE 1.8 FLEX 2015/...
    COMPASS 2.0 2016/...
    COMPASS 2.0 4X4 2016/...
    """
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "COMPATIBLE"
    assert "engine=1.8" in res["matched"]
    assert "fuel=FLEX" in res["matched"]

# CASE 4: Multiple engines in same application "1.8/2.0" -> COMPATIBLE
def test_case_4_multiple_engines_same_segment(renegade_flex_18_2016):
    app_text = "RENEGADE 4X2 1.8/2.0 2015/..."
    # Keep this scenario focused on the engine list; test unknown drivetrain separately.
    vehicle = dict(renegade_flex_18_2016, drivetrain="4X2")
    res = ApplicationMatcher.match_application(vehicle, app_text)
    assert res["compatibility"] == "COMPATIBLE"
    assert "engine=1.8" in res["matched"]

# CASE 5: Text with multiple vehicles -> COMPATIBLE for RENEGADE 1.8
def test_case_5_multi_vehicle_isolation(renegade_flex_18_2016):
    app_text = "RENEGADE 1.8/2.0 FLEX 2016/... - TORO 1.8/2.0 2017/... - ARGO 1.0/1.3/1.8 2017/..."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "COMPATIBLE"
    assert "engine=1.8" in res["matched"]

# CASE 6: Generic application "TODOS 15/..." -> COMPATIBLE
def test_case_6_generic_application_todos(renegade_flex_18_2016):
    app_text = "JEEP RENEGADE TODOS 15/..."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "COMPATIBLE"
    assert "model=RENEGADE" in res["matched"]

# CASE 7: Unknown transmission vehicle vs AUTOMATICO -> CONDITIONAL
def test_case_7_transmission_unknown_automatico(renegade_flex_18_2016):
    app_text = "RENEGADE 1.8 4X2 FLEX AUTOMATICO 2016/..."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "CONDITIONAL"
    assert "transmission=AUTOMÁTICO" in res["unknown"]

# CASE 8: Unknown transmission vehicle vs MECANICO -> CONDITIONAL
def test_case_8_transmission_unknown_mecanico(renegade_flex_18_2016):
    app_text = "RENEGADE 1.8 4X2 FLEX MECANICO 2016/..."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "CONDITIONAL"
    assert "transmission=MANUAL" in res["unknown"]

# CASE 9: Year out of range 2017/... vs 2016 vehicle -> INCOMPATIBLE
def test_case_9_year_out_of_range(renegade_flex_18_2016):
    app_text = "RENEGADE 1.8 FLEX 2017/..."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "INCOMPATIBLE"
    assert any("ano" in c.lower() for c in res["conflicts"])

# CASE 10: Diesel mismatch for FLEX vehicle -> INCOMPATIBLE
def test_case_10_diesel_mismatch(renegade_flex_18_2016):
    app_text = "RENEGADE 2.0 DIESEL 2015/..."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "INCOMPATIBLE"

# CASE 11: Complex text containing multiple vehicles and engines -> INCOMPATIBLE
def test_case_11_complex_text_multi_vehicles_all_mismatch(renegade_flex_18_2016):
    app_text = "ASTRA 1.8/2.0 1998/2005 -- FREEMONT 2.4 2012/... -- TORO 2.4 2017/... -- RENEGADE 2.4 2016/..."
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "INCOMPATIBLE"

# CASE 12: Multiple transmission restricted segments without unrestricted -> CONDITIONAL
def test_case_12_multiple_transmission_restricted_segments(renegade_flex_18_2016):
    app_text = """
    RENEGADE 2.0 DIESEL
    RENEGADE 1.8 FLEX AUTOMATICO 2016
    RENEGADE 1.8 FLEX MECANICO 2016
    """
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "CONDITIONAL"

# CASE 13: Multiple segments containing transmission restricted AND unrestricted segment -> COMPATIBLE
def test_case_13_unrestricted_segment_overrides_conditional(renegade_flex_18_2016):
    app_text = """
    RENEGADE 2.0 DIESEL
    RENEGADE 1.8 FLEX AUTOMATICO 2016
    RENEGADE 1.8 FLEX MECANICO 2016
    RENEGADE 1.8 FLEX 2015/...
    """
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, app_text)
    assert res["compatibility"] == "COMPATIBLE"


@pytest.mark.parametrize("separator", [", ", ",", "--", " -- ", ";", "\n", " - "])
@pytest.mark.parametrize("first,last,expected", [
    ("ASTRA 1.8 FLEX 2015/...", "RENEGADE 2.4 2016/...", "INCOMPATIBLE"),
    ("ASTRA 2.4 GNV 2017/...", "RENEGADE 1.8 FLEX 2015/...", "COMPATIBLE"),
    ("RENEGADE 1.8 FLEX 2017/...", "COMPASS 1.8 FLEX 2015/...", "INCOMPATIBLE"),
    ("RENEGADE 1.8 GNV 2015/...", "COMPASS 1.8 FLEX 2015/...", "INCOMPATIBLE"),
])
def test_attribute_isolation(renegade_flex_18_2016, separator, first, last, expected):
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, first + separator + last)
    assert res["compatibility"] == expected


@pytest.mark.parametrize("text,expected", [
    ("RENEGADE 1.8 FLEX CVT 2015/...", "CONDITIONAL"),
    ("RENEGADE 1.8 FLEX 4X2 2015/...", "CONDITIONAL"),
    ("RENEGADE 1.8 - GASOLINA 2017/...", "INCOMPATIBLE"),
    ("COMPASS TODOS 2015/...", "INCOMPATIBLE"),
    ("RENEGADEPLUS 1.8 FLEX 2015/...", "INCOMPATIBLE"),
    ("RENEGADE", "CONDITIONAL"),
    ("TODOS", "INCOMPATIBLE"),
    ("RENEGADE 1.8 FLEX 2015 2017", "INCOMPATIBLE"),
    ("RENEGADE/COMPASS 1.8/2.0 FLEX 2015/2021", "COMPATIBLE"),
    ("RENEGADE 1,8 FLEX 2015/...", "COMPATIBLE"),
    ("RENEGADE 1.8, FLEX, ANO: 15/...", "COMPATIBLE"),
    ("FIAT RENEGADE 1.8 FLEX 2015/...", "INCOMPATIBLE"),
    ("RENEGADE 2.4 2015/... -- RENEGADE 1.8 2017/...", "INCOMPATIBLE"),
    ("RENEGADE 2.4 2015/... -- RENEGADE 1.8 CVT 2015/...", "CONDITIONAL"),
    ("RENEGADE 2.4 COMPASS 1.8 FLEX 2015/...", "CONDITIONAL"),
    ("RENEGADE 2.4/COMPASS 1.8 FLEX 2015/...", "INCOMPATIBLE"),
    ("FIAT - RENEGADE 1.8 FLEX 2015/...", "INCOMPATIBLE"),
    ("RENEGADE 1.8 - SPORT 2017/...", "INCOMPATIBLE"),
    ("RENEGADE 1.8 FLEX ANO: 17/.", "INCOMPATIBLE"),
    ("RENEGADE 1.8 2017/... / 2.4 2016/...", "CONDITIONAL"),
    ("RENEGADE 1.8 FLEX 2015/... EXCETO FLEX", "INCOMPATIBLE"),
])
def test_conservative_classification(renegade_flex_18_2016, text, expected):
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, text)
    assert res["compatibility"] == expected
    if expected == "CONDITIONAL":
        assert res["unknown"]


@pytest.mark.parametrize("text,reason", [(None, "EMPTY_APPLICATION"), ("", "EMPTY_APPLICATION"),
    ("   ", "EMPTY_APPLICATION"), (123, "INVALID_APPLICATION"), ("1234", "INVALID_APPLICATION"),
    ("COMPASS 2.0 2015/...", "MODEL_NOT_FOUND"), ("RENEGADE 1.8 2021/2015", "INVALID_APPLICATION")])
def test_invalid_and_unmatched_applications(renegade_flex_18_2016, text, reason):
    res = ApplicationMatcher.match_application(renegade_flex_18_2016, text)
    assert res["compatibility"] == "INCOMPATIBLE"
    assert res["reason"] == reason
    assert res["conflicts"]


@pytest.mark.parametrize("field", ["engine_displacement", "model_year", "fuel", "transmission", "drivetrain"])
def test_required_unknown_attribute_is_conditional(renegade_flex_18_2016, field):
    vehicle = dict(renegade_flex_18_2016, transmission="CVT", drivetrain="4X2")
    vehicle[field] = None
    if field == "model_year":
        vehicle["manufacture_year"] = None
    res = ApplicationMatcher.match_application(vehicle, "RENEGADE 1.8 FLEX CVT 4X2 2015/...")
    assert res["compatibility"] == "CONDITIONAL"
    assert res["unknown"]


def test_normalized_api_vehicle_and_model_year_precedence():
    vehicle = dict(make="Jeep", model="Renegade", year_model="2016", year_manufacture=2015,
                   engine="1.8 16V", fuel="Flex", transmission=None)
    for text, expected in [("RENEGADE 2.4 2016/...", "INCOMPATIBLE"),
                           ("RENEGADE 1.8 FLEX 2017/...", "INCOMPATIBLE"),
                           ("RENEGADE 1.8 FLEX 2015/2015", "INCOMPATIBLE"),
                           ("RENEGADE 1.8 16V FLEX 2016/...", "COMPATIBLE")]:
        assert ApplicationMatcher.match_application(vehicle, text)["compatibility"] == expected


@pytest.mark.parametrize("transmission,expected", [("CVT", "COMPATIBLE"), ("Manual", "INCOMPATIBLE"), (None, "CONDITIONAL")])
def test_cvt_restriction(renegade_flex_18_2016, transmission, expected):
    vehicle = dict(renegade_flex_18_2016, transmission=transmission)
    assert ApplicationMatcher.match_application(vehicle, "RENEGADE 1.8 FLEX CVT 2015/...")["compatibility"] == expected


@pytest.mark.parametrize("engine,text,expected", [
    ("1.8 16V", "RENEGADE 1.8 16V FLEX 2015/...", "COMPATIBLE"),
    ("1.8 16V", "RENEGADE 1.8 8V FLEX 2015/...", "INCOMPATIBLE"),
    ("1.8", "RENEGADE 1.8 16V FLEX 2015/...", "CONDITIONAL"),
    ("1.8 Turbo", "RENEGADE 1.8 TURBO FLEX 2015/...", "COMPATIBLE"),
    ("1.8 Aspirado", "RENEGADE 1.8 TURBO FLEX 2015/...", "INCOMPATIBLE"),
    ("1.8", "RENEGADE 1.8 TURBO FLEX 2015/...", "CONDITIONAL"),
    ("1.8L", "RENEGADE 2.4 FLEX 2015/...", "INCOMPATIBLE"),
])
def test_engine_description_restrictions(engine, text, expected):
    vehicle = dict(make="Jeep", model="Renegade", year_model=2016, engine=engine, fuel="Flex")
    assert ApplicationMatcher.match_application(vehicle, text)["compatibility"] == expected


@pytest.mark.parametrize("text,expected", [
    ("RENEGADE 1.8 FLEX ANO MODELO: 2016 FABRICACAO: 2015", "COMPATIBLE"),
    ("RENEGADE 1.8 FLEX ANO MODELO: 2017 FABRICACAO: 2016", "INCOMPATIBLE"),
    ("RENEGADE 1.8 FLEX ANO FABRICACAO: 2016", "INCOMPATIBLE"),
    ("RENEGADE 1.8 FLEX ANO FABRICACAO: 2015", "COMPATIBLE"),
])
def test_model_and_manufacture_year_are_independent(renegade_flex_18_2016, text, expected):
    assert ApplicationMatcher.match_application(renegade_flex_18_2016, text)["compatibility"] == expected


def test_unknown_model_year_is_not_invented_from_manufacture_year(renegade_flex_18_2016):
    vehicle = dict(renegade_flex_18_2016, model_year=None)
    res = ApplicationMatcher.match_application(vehicle, "RENEGADE 1.8 FLEX 2015/2015")
    assert res["compatibility"] == "CONDITIONAL"
    assert any(value.startswith("model_year=") for value in res["unknown"])


@pytest.mark.parametrize("version,expected", [(None, "CONDITIONAL"), ("Sport", "COMPATIBLE"), ("Longitude", "INCOMPATIBLE")])
def test_explicit_version_restriction(renegade_flex_18_2016, version, expected):
    vehicle = dict(renegade_flex_18_2016, version=version)
    res = ApplicationMatcher.match_application(vehicle, "RENEGADE SPORT 1.8 FLEX 2015/...")
    assert res["compatibility"] == expected
