import logging
from typing import Dict, Any, Optional, Tuple
from app.providers.base_plate_provider import BasePlateProvider

logger = logging.getLogger(__name__)

class PlacaFipeProvider(BasePlateProvider):
    """
    PlacaFipe Provider marked as NOT_VERIFIED due to lack of official public API documentation.
    Disabled by default for production use until official documentation is available.
    """
    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return "PLACAFIPE_NOT_VERIFIED"

    def fetch_plate_info(self, plate: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        logger.warning("PlacaFipe provider is marked as NOT_VERIFIED and disabled for production.")
        return "PROVIDER_NOT_CONFIGURED", None
