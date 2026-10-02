import logging
import hashlib
import json
from typing import Dict, Any, Optional
import httpx
from app.providers.base_plate_provider import BasePlateProvider

logger = logging.getLogger(__name__)

class PlacaFipeProvider(BasePlateProvider):
    def __init__(self, api_key: str = "", base_url: str = "https://placafipe.com/api/v1/consultar"):
        self.api_key = api_key
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return "PLACAFIPE"

    def fetch_plate_info(self, plate: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("PlacaFipe API key not configured.")
            return None

        clean_plate = plate.upper().replace("-", "").strip()
        url = f"{self.base_url}?plate={clean_plate}&token={self.api_key}"

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code != 200:
                    logger.error(f"PlacaFipe returned status code {response.status_code}")
                    return None

                data = response.json()
                if not data or data.get("error"):
                    return None

                raw_json_str = json.dumps(data, sort_keys=True)
                raw_hash = hashlib.sha256(raw_json_str.encode('utf-8')).hexdigest()

                return {
                    "make": data.get("brand") or data.get("marca"),
                    "model": data.get("model") or data.get("modelo"),
                    "version": data.get("version") or data.get("versao") or "",
                    "year_manufacture": int(data.get("year_manufacture") or data.get("ano") or 0),
                    "year_model": int(data.get("year_model") or data.get("ano_modelo") or 0),
                    "engine": data.get("engine") or data.get("motor") or "",
                    "fuel": data.get("fuel") or data.get("combustivel") or "",
                    "transmission": data.get("transmission") or "",
                    "fipe_code": data.get("fipe_code") or data.get("codigo_fipe") or "",
                    "source_vehicle_id": str(data.get("id", "")),
                    "data_quality": "HIGH",
                    "confidence": 1.0,
                    "is_ambiguous": False,
                    "raw_data": data,
                    "raw_response_hash": raw_hash
                }
        except Exception as e:
            logger.error(f"Error querying PlacaFipe: {e}")
            return None
