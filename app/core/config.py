import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
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

    class Config:
        case_sensitive = True

settings = Settings()
