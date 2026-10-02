from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BasePlateProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns provider identifier name."""
        pass

    @abstractmethod
    def fetch_plate_info(self, plate: str) -> Optional[Dict[str, Any]]:
        """
        Fetches vehicle information for a plate from the provider.
        Returns a dictionary with standardized keys or None if not found/error.

        Expected fields in returned dict:
        - make (str)
        - model (str)
        - version (str)
        - year_manufacture (int)
        - year_model (int)
        - engine (str)
        - fuel (str)
        - transmission (str)
        - fipe_code (str)
        - source_vehicle_id (str)
        - data_quality (str)
        - confidence (float)
        - is_ambiguous (bool)
        - raw_data (dict/json)
        """
        pass
