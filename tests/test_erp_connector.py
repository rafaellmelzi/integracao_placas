import pytest
from app.integrations.erp.base import validate_readonly_query
from app.integrations.erp.connectors.mysql import MySQLERPConnector
from app.integrations.erp.connectors.postgresql import PostgreSQLERPConnector

def test_validate_readonly_query_valid():
    sql = "SELECT CADITE.ITE_CODITE AS internal_code FROM CADITE WHERE CADITE.ITE_APLICA LIKE :vehicle_model"
    validate_readonly_query(sql) # Should not raise

def test_validate_readonly_query_forbidden_keywords():
    forbidden_queries = [
        "UPDATE CADITE SET ITE_APLICA = 'x'",
        "DELETE FROM CADITE WHERE ITE_CODITE = '1'",
        "DROP TABLE CADITE",
        "TRUNCATE TABLE CADITE",
        "INSERT INTO CADITE (ITE_CODITE) VALUES ('1')",
        "ALTER TABLE CADITE ADD COLUMN x VARCHAR(10)"
    ]
    for sql in forbidden_queries:
        with pytest.raises(ValueError, match="Security Violation"):
            validate_readonly_query(sql)

def test_connector_initialization_and_sanitization():
    conn = MySQLERPConnector(
        host="localhost",
        port=3306,
        database="autcom_db",
        user="reader",
        password="secret_password_123"
    )
    assert conn.host == "localhost"
    sanitized = conn._sanitize_log("Error connecting with password secret_password_123")
    assert "secret_password_123" not in sanitized
    assert "***PWD_HIDDEN***" in sanitized
