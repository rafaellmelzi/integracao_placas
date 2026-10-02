from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_

from app.db.models import (
    Part, PartApplication, PartCategory, PartManufacturer,
    ERPProductMapping, Vehicle, VehicleMake, VehicleModel,
    VehicleVersion, VehicleEngine, PartCrossReference, ConfidenceLevel
)
from app.services.plate_lookup_service import PlateLookupService
from app.services.query_normalizer import normalize_part_query
from app.services.vehicle_normalizer import (
    normalize_make, normalize_model, normalize_engine
)

class PartsSearchService:
    def __init__(self, db: Session):
        self.db = db
        self.plate_service = PlateLookupService(db)

    def search_parts(
        self,
        plate: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        version: Optional[str] = None,
        engine: Optional[str] = None,
        category: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:

        vehicle_info = None
        vehicle_ids = []
        is_ambiguous = False

        # 1. Resolve vehicle either via Plate or via Manual Selection
        if plate and plate.strip():
            plate_res = self.plate_service.get_or_fetch_plate(plate)
            if plate_res.get("status") in ["PROVIDER_NOT_CONFIGURED", "INVALID_PLATE", "VEHICLE_NOT_FOUND"] and not plate_res.get("vehicle"):
                return {
                    "plate": plate,
                    "query": query or "",
                    "status": plate_res.get("status"),
                    "message": plate_res.get("message", "Veículo não encontrado."),
                    "vehicle": None,
                    "results": []
                }
            vehicle_info = plate_res.get("vehicle")
            if vehicle_info:
                vehicle_ids = [vehicle_info["id"]]
            is_ambiguous = plate_res.get("is_ambiguous", False)

        elif make and model:
            normalized_make_name = normalize_make(make)
            normalized_model_name = normalize_model(model)
            normalized_engine_desc = normalize_engine(engine) if engine else None

            # Find matching vehicles in DB
            q_vehicle = self.db.query(Vehicle).join(VehicleMake).join(VehicleModel)
            q_vehicle = q_vehicle.filter(
                VehicleMake.name == normalized_make_name,
                VehicleModel.normalized_name == normalized_model_name.upper()
            )

            if year:
                q_vehicle = q_vehicle.filter((Vehicle.year_manufacture == year) | (Vehicle.year_model == year))

            if version and version.strip():
                q_vehicle = q_vehicle.join(VehicleVersion).filter(VehicleVersion.name == version.strip())

            if normalized_engine_desc:
                q_vehicle = q_vehicle.join(VehicleEngine).filter(VehicleEngine.description == normalized_engine_desc)

            matched_vehicles = q_vehicle.all()

            if not matched_vehicles:
                return {
                    "vehicle": {
                        "make": make,
                        "model": model,
                        "year": year,
                        "version": version,
                        "engine": engine
                    },
                    "query": query or "",
                    "status": "VEHICLE_NOT_FOUND",
                    "message": "Nenhum veículo encontrado no catálogo com esses parâmetros.",
                    "results_count": 0,
                    "results": []
                }

            vehicle_ids = [v.id for v in matched_vehicles]
            if len(matched_vehicles) > 1 and not (version and engine):
                is_ambiguous = True

            v_first = matched_vehicles[0]
            vehicle_info = {
                "id": v_first.id,
                "make": v_first.make.name if v_first.make else make,
                "model": v_first.model.name if v_first.model else model,
                "version": v_first.version.name if v_first.version else version,
                "year_manufacture": v_first.year_manufacture,
                "year_model": v_first.year_model,
                "engine": v_first.engine.description if v_first.engine else engine,
                "fuel": v_first.fuel.name if v_first.fuel else None,
                "transmission": v_first.transmission.type if v_first.transmission else None,
                "fipe_code": v_first.fipe_code
            }

        else:
            return {
                "status": "INVALID_PARAMETERS",
                "message": "Informe a placa do veículo ou selecione Marca, Modelo e Ano.",
                "vehicle": None,
                "results": []
            }

        # 2. Normalize search term/category
        search_query = query or ""
        category_code = category or normalize_part_query(search_query)

        # 3. Query Applications
        app_filter = [PartApplication.vehicle_id.in_(vehicle_ids)]
        applications = self.db.query(PartApplication).join(Part).join(PartCategory).filter(*app_filter).all()

        if category_code:
            applications = [app for app in applications if app.part.category.code == category_code]

        if not applications:
            total_parts = self.db.query(Part).count()
            if total_parts == 0:
                return {
                    "vehicle": vehicle_info,
                    "query": search_query,
                    "category_identified": category_code,
                    "status": "APPLICATION_CATALOG_NOT_CONFIGURED",
                    "message": "Catálogo de peças não cadastrado.",
                    "results_count": 0,
                    "results": []
                }
            return {
                "vehicle": vehicle_info,
                "query": search_query,
                "category_identified": category_code,
                "status": "APPLICATION_AMBIGUOUS" if is_ambiguous else "NO_COMPATIBLE_PARTS_FOUND",
                "message": "Veículo possui variações com peças diferentes. Especifique versão/motorização." if is_ambiguous else "Nenhuma peça compatível encontrada.",
                "results_count": 0,
                "results": []
            }

        # 4. Format Results
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
                "axis": app.axis or "Dianteiro",
                "compatibility": app.confidence.value,
                "confidence_score": 1.0 if app.confidence == ConfidenceLevel.CONFIRMED else 0.8,
                "source": part.source or app.source,
                "oem_codes": part.oem_codes,
                "equivalent_codes": part.equivalent_codes,
                "technical_specs": part.technical_specs,
                "notes": app.notes,
                "cross_references": cross_ref_list,
                "erp_mapping": erp_dict
            })

        return {
            "vehicle": vehicle_info,
            "query": search_query,
            "category_identified": category_code,
            "status": "APPLICATION_AMBIGUOUS" if (is_ambiguous and len(results) > 1) else "SUCCESS",
            "results_count": len(results),
            "results": results
        }
