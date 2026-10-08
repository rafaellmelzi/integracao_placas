import os
from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, hide_input_in_errors=True)
    DEPLOYMENT_MODE: Literal["local", "cloud"] = "local"
    API_ACCESS_TOKEN: str = ""
    CORS_ORIGINS: list[str] = []
    DATABASE_SCHEMA: str = Field(default="public", pattern=r"^[a-z_][a-z0-9_]*$")
    MIGRATION_DATABASE_URL: str = ""
    DB_SSL_MODE: str = ""
    DB_POOL_SIZE: int = Field(default=2, ge=1, le=10)
    DB_MAX_OVERFLOW: int = Field(default=0, ge=0, le=10)
    DB_POOL_TIMEOUT: int = Field(default=5, ge=1)
    DB_CONNECT_TIMEOUT: int = Field(default=5, ge=1)
    DB_STATEMENT_TIMEOUT_MS: int = Field(default=10000, ge=1000)
    PROJECT_NAME: str = "AutoParts Plate & Applicability API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # APP Environment: 'development' or 'production'
    APP_ENV: str = os.getenv("APP_ENV", "development")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./autoparts.db")

    # Plate Provider Configuration
    # Options: MOCK, FIPEPLACA, APIPLACA, PLACAFIPE, SERPRO
    VEHICLE_PROVIDER: str = os.getenv("VEHICLE_PROVIDER", "MOCK")
    VEHICLE_API_URL: str = os.getenv("VEHICLE_API_URL", "")
    VEHICLE_API_KEY: str = os.getenv("VEHICLE_API_KEY", "")
    FIPEPLACA_API_KEY: str = os.getenv("FIPEPLACA_API_KEY", "")
    PLATE_CACHE_TTL_DAYS: int = int(os.getenv("PLATE_CACHE_TTL_DAYS", "90"))

    # Parts Provider / Catalog Configuration
    PARTS_PROVIDER: str = os.getenv("PARTS_PROVIDER", "LOCAL_DB")
    PARTS_API_URL: str = os.getenv("PARTS_API_URL", "")
    PARTS_API_KEY: str = os.getenv("PARTS_API_KEY", "")

    # FIPE Vehicle Synchronization & Provider Options
    # Options: TABELAFIPE, PARALLELUM
    FIPE_PROVIDER: str = os.getenv("FIPE_PROVIDER", "TABELAFIPE")
    FIPE_SYNC_ENABLED: bool = os.getenv("FIPE_SYNC_ENABLED", "true").lower() in ("true", "1", "yes")
    FIPE_CACHE_ENABLED: bool = os.getenv("FIPE_CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
    FIPE_SYNC_DELAY: float = float(os.getenv("FIPE_SYNC_DELAY", "1.0"))
    FIPE_AUTO_UPDATE: bool = os.getenv("FIPE_AUTO_UPDATE", "true").lower() in ("true", "1", "yes")

    # External ERP Integration Options (e.g., AUTCOM)
    ERP_ENABLED: bool = os.getenv("ERP_ENABLED", "false").lower() in ("true", "1", "yes")
    ERP_DB_TYPE: str = os.getenv("ERP_DB_TYPE", "mysql")  # mysql, postgresql, oracle, sqlserver
    ERP_DB_HOST: str = os.getenv("ERP_DB_HOST", "")
    ERP_DB_PORT: int = int(os.getenv("ERP_DB_PORT", "3306"))
    ERP_DB_NAME: str = os.getenv("ERP_DB_NAME", "")
    ERP_DB_USER: str = os.getenv("ERP_DB_USER", "")
    ERP_DB_PASSWORD: str = os.getenv("ERP_DB_PASSWORD", "")
    ERP_QUERY_TIMEOUT_SECONDS: int = int(os.getenv("ERP_QUERY_TIMEOUT_SECONDS", "10"))
    ERP_MAX_ROWS: int = int(os.getenv("ERP_MAX_ROWS", "5000"))

    # Configurable ERP SQL Queries
    ERP_PRODUCT_QUERY: str = os.getenv(
        "ERP_PRODUCT_QUERY",
        "SELECT CADITE.ITE_CODITE AS internal_code, CADITE.ITE_CODFAB AS factory_code, CADITE.ITE_DESITE AS description, CADMAR.MAR_DESMAR AS brand, CADITE.ITE_APLICA AS application FROM CADITE LEFT JOIN CADMAR ON CADITE.ITE_CODMAR = CADMAR.MAR_CODMAR WHERE UPPER(CADITE.ITE_APLICA) LIKE :vehicle_model"
    )
    ERP_AVAILABILITY_QUERY: str = os.getenv(
        "ERP_AVAILABILITY_QUERY",
        "SELECT ITEGER.ITE_CODITE AS internal_code, ITEGER.ITE_CODEMP AS company, ITEGER.ITE_SALDOS AS stock, ITEGER.ITE_PREVE1 AS price FROM ITEGER WHERE ITEGER.ITE_CODITE IN :codes"
    )

    @model_validator(mode="after")
    def cloud_requirements(self):
        if self.DEPLOYMENT_MODE == "cloud":
            if self.APP_ENV != "production":
                raise ValueError("Cloud deployment requires APP_ENV=production")
            if not self.DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
                raise ValueError("Cloud deployment requires PostgreSQL")
            if self.DB_SSL_MODE not in {"require", "verify-ca", "verify-full"}:
                raise ValueError("Cloud deployment requires PostgreSQL TLS")
            if self.VEHICLE_PROVIDER.upper() == "MOCK":
                raise ValueError("Cloud deployment cannot use mock vehicle data")
            if self.PARTS_PROVIDER.upper() != "LOCAL_DB":
                raise ValueError("Cloud deployment requires the real local catalog provider")
            if len(self.API_ACCESS_TOKEN) < 32:
                raise ValueError("Cloud deployment requires an API access token of at least 32 characters")
            if self.FIPE_SYNC_ENABLED or self.FIPE_AUTO_UPDATE:
                raise ValueError("Disable bulk FIPE sync and automatic catalog expansion in cloud mode")
        return self

settings = Settings()
