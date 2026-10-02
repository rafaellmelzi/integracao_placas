from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

class BasePlateProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns provider identifier name."""
        pass

    @abstractmethod
    def fetch_plate_info(self, plate: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Fetches vehicle information for a plate from the provider.
        Returns a tuple: (status_code, vehicle_dict)

        status_code options:
        - SUCCESS
        - VEHICLE_NOT_FOUND
        - PROVIDER_NOT_CONFIGURED
        - PROVIDER_AUTHENTICATION_ERROR
        - PROVIDER_RATE_LIMIT
        - PROVIDER_TIMEOUT
        - PROVIDER_ERROR
        """
        pass
