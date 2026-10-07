import logging
import urllib.request
import urllib.error
import json
import re
from typing import Dict, Any, Optional, Tuple, List
from app.providers.base_plate_provider import BasePlateProvider
from app.services.vehicle_normalizer import normalize_make, normalize_model, parse_version_specs

logger = logging.getLogger(__name__)

class FipePlacaProvider(BasePlateProvider):
    """
    Official Provider for FipePlaca API integration.
    Queries vehicle information and FIPE candidates by license plate.
    Uses Bearer Token authentication: Authorization: Bearer <FIPEPLACA_API_KEY>.
    Performs conservative normalization without fabricating unstated technical specs.
    """
    def __init__(self, api_key: str = "", base_url: str = "https://fipeplaca.com.br/api/v1"):
        self.api_key = api_key.strip() if api_key else ""
        self.base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "FIPEPLACA"

    def _sanitize_log_message(self, message: str) -> str:
        """Helper to ensure API Key is never printed in logs."""
        if self.api_key:
            return message.replace(self.api_key, "***API_KEY_HIDDEN***")
        return message

    def _make_request(self, endpoint: str, timeout: int = 10) -> Tuple[int, Optional[Dict[str, Any]]]:
        if not self.api_key:
            logger.warning("FipePlaca API Key is not configured.")
            return 401, None

        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "AutoParts-FipePlacaProvider/1.0",
            "Accept": "application/json"
        }

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status in (200, 201):
                    data = json.loads(resp.read().decode("utf-8"))
                    return resp.status, data
                return resp.status, None
        except urllib.error.HTTPError as e:
            status = e.code
            log_msg = self._sanitize_log_message(f"FipePlaca HTTP {status} error for {endpoint}: {e.reason}")
            if status == 401:
                logger.error("FipePlaca Unauthorized: Invalid or missing API key.")
            elif status == 402:
                logger.error("FipePlaca Payment Required: Insufficient API credits.")
            elif status == 429:
                logger.warning("FipePlaca Rate Limit exceeded.")
            else:
                logger.warning(log_msg)
            return status, None
        except Exception as e:
            log_msg = self._sanitize_log_message(f"FipePlaca connection error for {endpoint}: {str(e)}")
            logger.warning(log_msg)
            return 500, None

    def fetch_plate_info(self, plate: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        clean_plate = re.sub(r'[^A-Z0-9]', '', plate.strip().upper())
        if not clean_plate or len(clean_plate) != 7:
            return "INVALID_PLATE", None

        if not self.api_key:
            return "PROVIDER_NOT_CONFIGURED", None

        # 1. Query Basic Vehicle Data
        status_code, basic_data = self._make_request(f"/placa/{clean_plate}")
        if status_code == 401:
            return "PROVIDER_AUTHENTICATION_ERROR", None
        elif status_code == 402:
            return "PROVIDER_INSUFFICIENT_CREDITS", None
        elif status_code == 429:
            return "PROVIDER_RATE_LIMIT", None
        elif status_code in (400, 404) or not basic_data:
            return "VEHICLE_NOT_FOUND", None

        # 2. Query FIPE Candidates
        _, fipe_resp = self._make_request(f"/placa/{clean_plate}/fipe")
        candidates = []
        if fipe_resp and isinstance(fipe_resp, dict) and "value" in fipe_resp:
            for item in fipe_resp["value"]:
                candidates.append({
                    "fipe_code": item.get("codigoFipe"),
                    "description": item.get("modelo"),
                    "model_year": item.get("anoModelo"),
                    "fuel": item.get("combustivel"),
                    "confidence": item.get("confianca", "alta"),
                    "year_match": item.get("matchAno", True),
                    "fuel_match": item.get("matchCombustivel", True),
                    "fipe_value": item.get("valorFipe")
                })

        # 3. Normalize Vehicle Data
        raw_make = basic_data.get("marca", "")
        raw_model = basic_data.get("modelo", "")
        norm_make = normalize_make(raw_make) or raw_make.title()
        norm_model = normalize_model(raw_model) or raw_model.title()

        # Engine Displacement Normalization (e.g. 1800 cc -> "1.8", 1000 cc -> "1.0")
        cilindradas = basic_data.get("cilindradas")
        engine_displacement = None
        if cilindradas and isinstance(cilindradas, (int, float)) and cilindradas > 0:
            engine_displacement = f"{round(cilindradas / 1000.0, 1):.1f}"

        # Fuel Normalization (e.g. "ALCOOL / GASOLINA" -> "FLEX")
        raw_fuel = basic_data.get("combustivel", "")
        fuel = "FLEX" if ("ALCOOL" in raw_fuel.upper() or "FLEX" in raw_fuel.upper()) else raw_fuel.title()

        # Conservative Transmission Analysis across Candidates
        common_trans = None
        if candidates:
            trans_set = set()
            for cand in candidates:
                cand_specs = parse_version_specs(cand.get("description"))
                if cand_specs.get("transmission"):
                    trans_set.add(cand_specs["transmission"])
            if len(trans_set) == 1:
                common_trans = list(trans_set)[0]

        normalized_vehicle = {
            "make": norm_make,
            "model": norm_model,
            "manufacture_year": basic_data.get("anoFabricacao"),
            "model_year": basic_data.get("anoModelo"),
            "engine_displacement": engine_displacement,
            "power_cv": basic_data.get("potencia"),
            "fuel": fuel,
            "color": basic_data.get("cor"),
            "transmission": common_trans
        }

        response_payload = {
            "plate": clean_plate,
            "vehicle": normalized_vehicle,
            "identification": {
                "status": "EXACT" if len(candidates) == 1 else "PARTIAL",
                "exact_version": len(candidates) == 1,
                "candidate_count": len(candidates)
            },
            "fipe_candidates": candidates,
            "provider": "FIPEPLACA",
            "cached": False
        }

        return "SUCCESS", response_payload
