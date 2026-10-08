import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.erp.connectors.mysql import MySQLERPConnector
from app.integrations.erp.connectors.postgresql import PostgreSQLERPConnector
from app.services.application_matcher import ApplicationMatcher
from app.services.vehicle_contract import Compatibility, MatchingVehicle
from app.services.plate_lookup_service import PlateLookupService

logger = logging.getLogger("parts_compatibility_service")

class PartsCompatibilityService:
    """
    Service for querying external ERP database for products matching vehicle applicability
    and fetching aggregated stock and price availability across companies/branches.
    """
    def __init__(self, db: Session):
        self.db = db
        self.plate_service = PlateLookupService(db)
        self.connector = self._init_connector()

    def _init_connector(self):
        if settings.DEPLOYMENT_MODE == "cloud":
            return None  # A private customer database is never contacted from cloud mode.
        if not settings.ERP_ENABLED or not settings.ERP_DB_HOST or not settings.ERP_DB_NAME:
            logger.info("PartsCompatibilityService: ERP Integration is disabled or not configured.")
            return None

        db_type = settings.ERP_DB_TYPE.lower().strip()
        if db_type == "mysql":
            return MySQLERPConnector(
                host=settings.ERP_DB_HOST,
                port=settings.ERP_DB_PORT,
                database=settings.ERP_DB_NAME,
                user=settings.ERP_DB_USER,
                password=settings.ERP_DB_PASSWORD,
                timeout=settings.ERP_QUERY_TIMEOUT_SECONDS,
                max_rows=settings.ERP_MAX_ROWS
            )
        elif db_type in ("postgresql", "postgres"):
            return PostgreSQLERPConnector(
                host=settings.ERP_DB_HOST,
                port=settings.ERP_DB_PORT,
                database=settings.ERP_DB_NAME,
                user=settings.ERP_DB_USER,
                password=settings.ERP_DB_PASSWORD,
                timeout=settings.ERP_QUERY_TIMEOUT_SECONDS,
                max_rows=settings.ERP_MAX_ROWS
            )
        else:
            logger.warning(f"Unsupported ERP_DB_TYPE '{db_type}'. Supported: mysql, postgresql.")
            return None

    def get_parts_by_plate(self, plate: str) -> Dict[str, Any]:
        """
        Main entry point: Plate -> Vehicle Lookup -> FIPE Candidates -> ERP Products -> Matcher -> Aggregated Availability
        """
        erp_status = ("PRIVATE_NETWORK_UNAVAILABLE" if settings.DEPLOYMENT_MODE == "cloud" else
                      "AVAILABLE" if self.connector else "DISABLED" if not settings.ERP_ENABLED else "NOT_CONFIGURED")
        # 1. Lookup Vehicle by Plate
        plate_res = self.plate_service.get_or_fetch_plate(plate)
        if plate_res.get("status") in ("INVALID_PLATE", "PROVIDER_NOT_CONFIGURED", "VEHICLE_NOT_FOUND") and not plate_res.get("vehicle"):
            return {
                "plate": plate,
                "vehicle": None,
                "identification_status": "NOT_FOUND",
                "erp_enabled": bool(self.connector),
                "erp_status": erp_status,
                "parts_count": 0,
                "parts": []
            }

        vehicle_dict = plate_res.get("vehicle") or {}
        matching_vehicle = MatchingVehicle.from_mapping(vehicle_dict)
        fipe_candidates = plate_res.get("fipe_candidates") or []

        if not self.connector:
            return {
                "plate": plate,
                "vehicle": vehicle_dict,
                "identification_status": plate_res.get("status"),
                "fipe_candidates": fipe_candidates,
                "erp_enabled": False,
                "erp_status": erp_status,
                "message": "AUTCOM indisponível: banco privado do cliente não acessível neste modo." if settings.DEPLOYMENT_MODE == "cloud" else "Integração ERP não configurada ou desativada.",
                "parts_count": 0,
                "parts": []
            }

        # 2. Query ERP Products matching Vehicle Model
        model_name = vehicle_dict.get("model", "")
        if not model_name:
            return {
                "plate": plate,
                "vehicle": vehicle_dict,
                "identification_status": plate_res.get("status"),
                "fipe_candidates": fipe_candidates,
                "erp_enabled": True,
                "erp_status": erp_status,
                "parts_count": 0,
                "parts": []
            }

        param_model = f"%{model_name.strip().upper()}%"
        try:
            erp_products = self.connector.fetch_products(settings.ERP_PRODUCT_QUERY, {"vehicle_model": param_model})
        except Exception as e:
            logger.error("ERP product query failed (%s)", type(e).__name__)
            return {
                "plate": plate,
                "vehicle": vehicle_dict,
                "identification_status": plate_res.get("status"),
                "fipe_candidates": fipe_candidates,
                "erp_enabled": True,
                "error": "Erro ao consultar produtos no banco do ERP.",
                "erp_status": "UNAVAILABLE",
                "parts_count": 0,
                "parts": []
            }

        # 3. Match Products against Vehicle using ApplicationMatcher
        matched_items = []
        valid_internal_codes = []

        for prod in erp_products:
            match_res = ApplicationMatcher.match_application(matching_vehicle, prod.application)
            if match_res["compatibility"] in (Compatibility.COMPATIBLE.value, Compatibility.CONDITIONAL.value):
                valid_internal_codes.append(prod.internal_code)
                matched_items.append({
                    "product": prod,
                    "match": match_res
                })

        if not matched_items:
            return {
                "plate": plate,
                "vehicle": vehicle_dict,
                "identification_status": plate_res.get("status"),
                "fipe_candidates": fipe_candidates,
                "erp_enabled": True,
                "erp_status": erp_status,
                "parts_count": 0,
                "parts": []
            }

        # 4. Fetch Availability for matched internal codes
        availability_map: Dict[str, List[Dict[str, Any]]] = {}
        availability_status = "AVAILABLE"
        if valid_internal_codes:
            try:
                avail_rows = self.connector.fetch_availability(settings.ERP_AVAILABILITY_QUERY, valid_internal_codes)
                for av in avail_rows:
                    if av.internal_code not in availability_map:
                        availability_map[av.internal_code] = []
                    availability_map[av.internal_code].append({
                        "company": av.company,
                        "stock": av.stock,
                        "price": av.price
                    })
            except Exception as e:
                availability_status = "UNAVAILABLE"
                logger.warning("ERP availability query failed (%s)", type(e).__name__)

        # 5. Format and aggregate response
        parts_list = []
        for item in matched_items:
            prod = item["product"]
            match_res = item["match"]
            code = prod.internal_code

            parts_list.append({
                "internal_code": prod.internal_code,
                "factory_code": prod.factory_code,
                "description": prod.description,
                "brand": prod.brand,
                "application": prod.application,
                "compatibility": match_res["compatibility"],
                "compatibility_score": match_res["score"],
                "requires_confirmation": match_res["compatibility"] == Compatibility.CONDITIONAL.value,
                "match_details": {
                    "reason": match_res["reason"],
                    "matched": match_res["matched"],
                    "unknown": match_res["unknown"],
                    "conflicts": match_res["conflicts"]
                },
                "availability": availability_map.get(code, [])
            })

        return {
            "plate": plate,
            "vehicle": vehicle_dict,
            "identification_status": plate_res.get("status"),
            "fipe_candidates": fipe_candidates,
            "erp_enabled": True,
            "parts_count": len(parts_list),
            "erp_status": erp_status,
            "availability_status": availability_status,
            "parts": parts_list
        }
