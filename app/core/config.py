import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoParts Plate & Applicability API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./autoparts.db")

    # Plate Provider Configuration
    PLATE_PROVIDER_PRIMARY: str = os.getenv("PLATE_PROVIDER_PRIMARY", "MOCK") # MOCK, APIPLACA, SERPRO
    PLATE_CACHE_TTL_DAYS: int = int(os.getenv("PLATE_CACHE_TTL_DAYS", "90"))

    # API Keys for external providers
    APIPLACA_API_KEY: str = os.getenv("APIPLACA_API_KEY", "")
    SERPRO_CONSUMER_KEY: str = os.getenv("SERPRO_CONSUMER_KEY", "")
    SERPRO_CONSUMER_SECRET: str = os.getenv("SERPRO_CONSUMER_SECRET", "")

    class Config:
        case_sensitive = True

settings = Settings()
