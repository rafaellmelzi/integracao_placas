import logging
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
import httpx
from app.providers.base_plate_provider import BasePlateProvider

logger = logging.getLogger(__name__)

class ApiPlacaProvider(BasePlateProvider):
    def __init__(self, api_key: str = "", base_url: str = "https://apiplaca.com.br/v1/consultar"):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "APIPLACA"

    def fetch_plate_info(self, plate: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        if not self.api_key:
            logger.warning("ApiPlaca API key not configured.")
            return "PROVIDER_NOT_CONFIGURED", None

        clean_plate = plate.upper().replace("-", "").strip()
        url = f"{self.base_url}/{clean_plate}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.get(url, headers=headers)

                if response.status_code == 401 or response.status_code == 403:
                    logger.error("ApiPlaca authentication error (Invalid or expired API Key).")
                    return "PROVIDER_AUTHENTICATION_ERROR", None
                elif response.status_code == 429:
                    logger.error("ApiPlaca rate limit / quota exceeded.")
                    return "PROVIDER_RATE_LIMIT", None
                elif response.status_code == 404:
                    return "VEHICLE_NOT_FOUND", None
                elif response.status_code != 200:
                    logger.error(f"ApiPlaca returned HTTP status code {response.status_code}")
                    return "PROVIDER_ERROR", None

                data = response.json()
                if not data or data.get("error") or data.get("code") == "NOT_FOUND":
                    return "VEHICLE_NOT_FOUND", None

                raw_json_str = json.dumps(data, sort_keys=True)
                raw_hash = hashlib.sha256(raw_json_str.encode('utf-8')).hexdigest()

                # Robust field mapping supporting multiple standard Brazilian provider JSON responses
                make = data.get("marca") or data.get("brand") or data.get("montadora")
                model = data.get("modelo") or data.get("model")
                version = data.get("versao") or data.get("version") or data.get("submodelo")

                year_mfg = data.get("ano_fabricacao") or data.get("anoFabricacao") or data.get("ano")
                year_mod = data.get("ano_modelo") or data.get("anoModelo") or data.get("ano")

                engine = data.get("motor") or data.get("motorizacao") or data.get("cilindrada")
                fuel = data.get("combustivel") or data.get("fuel")
                transmission = data.get("cambio") or data.get("transmissao") or data.get("transmission")
                fipe = data.get("codigo_fipe") or data.get("fipe_code") or data.get("fipe")

                parsed = {
                    "make": make if make else None,
                    "model": model if model else None,
                    "version": version if version else None,
                    "year_manufacture": int(year_mfg) if year_mfg and str(year_mfg).isdigit() else None,
                    "year_model": int(year_mod) if year_mod and str(year_mod).isdigit() else None,
                    "engine": engine if engine else None,
                    "fuel": fuel if fuel else None,
                    "transmission": transmission if transmission else None,
                    "fipe_code": str(fipe) if fipe else None,
                    "source_vehicle_id": str(data.get("id") or data.get("chassi_mascarado") or clean_plate),
                    "data_quality": "HIGH",
                    "confidence": 1.0,
                    "is_ambiguous": False,
                    "raw_data": data,
                    "raw_response_hash": raw_hash
                }
                return "SUCCESS", parsed

        except httpx.TimeoutException:
            logger.error("ApiPlaca request timed out.")
            return "PROVIDER_TIMEOUT", None
        except Exception as e:
            logger.error(f"Unexpected error querying ApiPlaca: {e}")
            return "PROVIDER_ERROR", None
