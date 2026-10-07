import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from app.integrations.erp.base import BaseERPConnector, validate_readonly_query
from app.integrations.erp.models import ERPProduct, ERPAvailability

logger = logging.getLogger("erp_postgresql")

class PostgreSQLERPConnector(BaseERPConnector):
    """
    Read-Only PostgreSQL Connector for external ERPs using psycopg/psycopg2.
    """
    def _get_connection_url(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?connect_timeout={self.timeout}"

    def test_connection(self) -> bool:
        try:
            engine = create_engine(self._get_connection_url(), pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(self._sanitize_log(f"PostgreSQL ERP Connection failed: {e}"))
            return False

    def fetch_products(self, sql_query: str, params: Dict[str, Any]) -> List[ERPProduct]:
        validate_readonly_query(sql_query)
        engine = create_engine(self._get_connection_url(), pool_pre_ping=True)
        products = []

        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql_query), params)
                rows = result.fetchmany(self.max_rows)
                for row in rows:
                    mapping = row._mapping
                    if "internal_code" not in mapping:
                        raise ValueError("Product query must return 'internal_code' alias.")

                    products.append(ERPProduct(
                        internal_code=str(mapping["internal_code"]).strip(),
                        factory_code=str(mapping.get("factory_code", "")).strip() if mapping.get("factory_code") else None,
                        description=str(mapping.get("description", "")).strip(),
                        brand=str(mapping.get("brand", "")).strip() if mapping.get("brand") else None,
                        application=str(mapping.get("application", "")).strip() if mapping.get("application") else None
                    ))
        except Exception as e:
            logger.error(self._sanitize_log(f"Error executing ERP fetch_products: {e}"))
            raise

        return products

    def fetch_availability(self, sql_query: str, internal_codes: List[str]) -> List[ERPAvailability]:
        if not internal_codes:
            return []

        validate_readonly_query(sql_query)
        engine = create_engine(self._get_connection_url(), pool_pre_ping=True)
        availabilities = []
        params = {"codes": tuple(internal_codes)}

        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql_query), params)
                rows = result.fetchmany(self.max_rows)
                for row in rows:
                    mapping = row._mapping
                    if "internal_code" not in mapping or "company" not in mapping:
                        raise ValueError("Availability query must return 'internal_code' and 'company' aliases.")

                    availabilities.append(ERPAvailability(
                        internal_code=str(mapping["internal_code"]).strip(),
                        company=str(mapping["company"]).strip(),
                        stock=float(mapping.get("stock", 0.0) or 0.0),
                        price=float(mapping.get("price", 0.0) or 0.0)
                    ))
        except Exception as e:
            logger.error(self._sanitize_log(f"Error executing ERP fetch_availability: {e}"))
            raise

        return availabilities
