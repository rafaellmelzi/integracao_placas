import pytest
from app.services.vehicle_normalizer import parse_version_specs

def test_parse_version_specs_onix_2025():
    name = "ONIX HATCH LTZ 1.0 12V TB Flex 5p Aut."
    specs = parse_version_specs(name)
    assert specs["displacement"] == "1.0"
    assert specs["valves"] == 12
    assert specs["engine_desc"] == "1.0 12V Turbo"
    assert specs["transmission"] == "Automático"
    assert specs["fuel"] == "Flex"

def test_parse_version_specs_corolla():
    name = "Corolla XEi 2.0 16V Flex Aut."
    specs = parse_version_specs(name)
    assert specs["displacement"] == "2.0"
    assert specs["valves"] == 16
    assert specs["engine_desc"] == "2.0 16V"
    assert specs["transmission"] == "Automático"
    assert specs["fuel"] == "Flex"

def test_parse_version_specs_v8_mustang():
    name = "Mustang GT 5.0 V8 Gasolina Aut."
    specs = parse_version_specs(name)
    assert specs["displacement"] == "5.0"
    assert specs["valves"] is None
    assert specs["engine_desc"] == "5.0"
    assert specs["transmission"] == "Automático"
    assert specs["fuel"] == "Gasolina"

def test_parse_version_specs_bare_description():
    name = "Fusca 1300"
    specs = parse_version_specs(name)
    assert specs["displacement"] is None
    assert specs["valves"] is None
    assert specs["engine_desc"] is None
    assert specs["transmission"] is None
    assert specs["fuel"] is None

def test_parse_version_specs_empty_or_none():
    assert parse_version_specs(None) == {"displacement": None, "valves": None, "engine_desc": None, "transmission": None, "fuel": None}
    assert parse_version_specs("") == {"displacement": None, "valves": None, "engine_desc": None, "transmission": None, "fuel": None}
