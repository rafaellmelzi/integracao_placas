import logging
import hashlib
import json
from typing import Dict, Any, Optional
import httpx
from app.providers.base_plate_provider import BasePlateProvider

logger = logging.getLogger(__name__)

class ApiPlacaProvider(BasePlateProvider):
    def __init__(self, api_key: str = "", base_url: str = "https://apiplaca.com.br/v1/consultar"):
        self.api_key = api_key
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return "APIPLACA"

    def fetch_plate_info(self, plate: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("ApiPlaca API key not configured.")
            return None

        clean_plate = plate.upper().replace("-", "").strip()
        url = f"{self.base_url}/{clean_plate}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code != 200:
                    logger.error(f"ApiPlaca returned status code {response.status_code}")
                    return None

                data = response.json()
                raw_json_str = json.dumps(data, sort_keys=True)
                raw_hash = hashlib.sha256(raw_json_str.encode('utf-8')).hexdigest()

                return {
                    "make": data.get("marca"),
                    "model": data.get("modelo"),
                    "version": data.get("versao") or data.get("modelo"),
                    "year_manufacture": int(data.get("ano_fabricacao", 0)),
                    "year_model": int(data.get("ano_modelo", 0)),
                    "engine": data.get("motor", ""),
                    "fuel": data.get("combustivel", ""),
                    "transmission": data.get("cambio", ""),
                    "fipe_code": data.get("codigo_fipe", ""),
                    "source_vehicle_id": str(data.get("id", "")),
                    "data_quality": "HIGH",
                    "confidence": 1.0,
                    "is_ambiguous": False,
                    "raw_data": data,
                    "raw_response_hash": raw_hash
                }
        except Exception as e:
            logger.error(f"Error querying ApiPlaca: {e}")
            return None
