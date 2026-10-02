from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.db.models import (
    Part, PartApplication, PartCategory, PartManufacturer,
    ERPProductMapping, Vehicle, PartCrossReference, ConfidenceLevel
)
from app.services.plate_lookup_service import PlateLookupService
from app.services.query_normalizer import normalize_part_query

class PartsSearchService:
    def __init__(self, db: Session):
        self.db = db
        self.plate_service = PlateLookupService(db)

    def search_parts_by_plate_and_query(self, plate: str, query: str) -> Dict[str, Any]:
        # 1. Resolve vehicle from plate
        plate_res = self.plate_service.get_or_fetch_plate(plate)
        if plate_res.get("status") == "DATA_SOURCE_NOT_CONFIGURED" or not plate_res.get("vehicle"):
            return {
                "plate": plate,
                "query": query,
                "status": "DATA_SOURCE_NOT_CONFIGURED",
                "message": "Vehicle could not be resolved or dataset provider not configured.",
                "vehicle": None,
                "results": []
            }

        vehicle_info = plate_res["vehicle"]
        vehicle_id = vehicle_info["id"]

        # 2. Normalize search term category
        category_code = normalize_part_query(query)

        # 3. Find matching applications for vehicle_id
        query_filter = [PartApplication.vehicle_id == vehicle_id]

        applications = self.db.query(PartApplication).join(Part).join(PartCategory).filter(*query_filter).all()

        # If filtered by category code, refine results
        if category_code:
            applications = [app for app in applications if app.part.category.code == category_code]

        if not applications:
            # Check if catalog has any parts at all
            total_parts = self.db.query(Part).count()
            if total_parts == 0:
                return {
                    "vehicle": vehicle_info,
                    "query": query,
                    "category_identified": category_code,
                    "status": "APPLICATION_CATALOG_NOT_CONFIGURED",
                    "message": "No parts catalog loaded in system.",
                    "results": []
                }
            return {
                "vehicle": vehicle_info,
                "query": query,
                "category_identified": category_code,
                "status": "NO_COMPATIBLE_PARTS_FOUND",
                "results_count": 0,
                "results": []
            }

        # 4. Format search results and look up ERP mappings & cross references
        results = []
        for app in applications:
            part = app.part

            # Find ERP product mapping
            erp_map = self.db.query(ERPProductMapping).filter(ERPProductMapping.part_id == part.id).first()
            erp_dict = None
            if erp_map:
                erp_dict = {
                    "erp_product_id": erp_map.erp_product_id,
                    "verified": erp_map.verified,
                    "mapping_type": erp_map.mapping_type.value,
                    "confidence": erp_map.confidence.value
                }

            # Find Cross References
            cross_refs = self.db.query(PartCrossReference).filter(
                or_(PartCrossReference.part_id == part.id, PartCrossReference.reference_part_id == part.id)
            ).all()

            cross_ref_list = []
            for ref in cross_refs:
                ref_part = ref.reference_part if ref.part_id == part.id else ref.part
                cross_ref_list.append({
                    "manufacturer": ref_part.manufacturer.name,
                    "code": ref_part.manufacturer_part_number,
                    "type": ref.reference_type.value,
                    "confidence": ref.confidence.value
                })

            results.append({
                "part_id": part.id,
                "manufacturer": part.manufacturer.name,
                "manufacturer_code": part.manufacturer_part_number,
                "ean": part.ean,
                "description": part.description,
                "category": part.category.name,
                "position": app.position or "Dianteiro",
                "compatibility": app.confidence.value,
                "confidence_score": 1.0 if app.confidence == ConfidenceLevel.CONFIRMED else 0.8,
                "source": app.source,
                "notes": app.notes,
                "cross_references": cross_ref_list,
                "erp_mapping": erp_dict
            })

        return {
            "vehicle": vehicle_info,
            "query": query,
            "category_identified": category_code,
            "status": "SUCCESS",
            "results_count": len(results),
            "results": results
        }
