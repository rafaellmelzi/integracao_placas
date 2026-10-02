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
    # Options: MOCK, APIPLACA, PLACAFIPE, SERPRO
    VEHICLE_PROVIDER: str = os.getenv("VEHICLE_PROVIDER", "MOCK")
    VEHICLE_API_URL: str = os.getenv("VEHICLE_API_URL", "")
    VEHICLE_API_KEY: str = os.getenv("VEHICLE_API_KEY", "")
    PLATE_CACHE_TTL_DAYS: int = int(os.getenv("PLATE_CACHE_TTL_DAYS", "90"))

    # Parts Provider / Catalog Configuration
    PARTS_PROVIDER: str = os.getenv("PARTS_PROVIDER", "LOCAL_DB")
    PARTS_API_URL: str = os.getenv("PARTS_API_URL", "")
    PARTS_API_KEY: str = os.getenv("PARTS_API_KEY", "")

    class Config:
        case_sensitive = True

settings = Settings()
