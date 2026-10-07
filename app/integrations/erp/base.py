import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.integrations.erp.models import ERPProduct, ERPAvailability

logger = logging.getLogger("erp_connector")

FORBIDDEN_SQL_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bTRUNCATE\b", r"\bCREATE\b", r"\bGRANT\b",
    r"\bREVOKE\b", r"\bEXEC\b", r"\bEXECUTE\b"
]

def validate_readonly_query(sql_query: str) -> None:
    """
    Validates that configured SQL queries are strictly read-only SELECT statements.
    Rejects any DDL or DML write operations.
    """
    if not sql_query or not sql_query.strip():
        raise ValueError("ERP SQL query is empty.")

    clean_sql = re.sub(r"--.*$", "", sql_query, flags=re.MULTILINE)
    clean_sql = re.sub(r"/\*.*?\*/", "", clean_sql, flags=re.DOTALL).strip().upper()

    if not clean_sql.startswith("SELECT") and not clean_sql.startswith("WITH"):
        raise ValueError("Security Violation: ERP queries must be SELECT or WITH statements.")

    for pattern in FORBIDDEN_SQL_KEYWORDS:
        if re.search(pattern, clean_sql):
            raise ValueError(f"Security Violation: Query contains forbidden keyword '{pattern}'. Write/DDL commands are strictly prohibited.")

class BaseERPConnector(ABC):
    """
    Abstract Base Class for Read-Only External ERP Database Connectors.
    Supports MySQL, PostgreSQL, Oracle, and SQL Server.
    """
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        timeout: int = 10,
        max_rows: int = 5000
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.timeout = timeout
        self.max_rows = max_rows

    def _sanitize_log(self, text: str) -> str:
        if self.password:
            return text.replace(self.password, "***PWD_HIDDEN***")
        return text

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify external ERP DB connection and read privileges."""
        pass

    @abstractmethod
    def fetch_products(self, sql_query: str, params: Dict[str, Any]) -> List[ERPProduct]:
        """Execute read-only product/application query returning ERPProduct objects."""
        pass

    @abstractmethod
    def fetch_availability(self, sql_query: str, internal_codes: List[str]) -> List[ERPAvailability]:
        """Execute read-only stock/price query for internal codes returning ERPAvailability objects."""
        pass
