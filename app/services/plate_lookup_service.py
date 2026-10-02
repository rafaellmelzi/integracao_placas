import re
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    VehiclePlateCache, Vehicle, VehicleMake, VehicleModel,
    VehicleVersion, VehicleEngine, VehicleFuel, VehicleTransmission
)
from app.providers.mock_plate_provider import MockPlateProvider
from app.providers.apiplaca_provider import ApiPlacaProvider
from app.providers.placafipe_provider import PlacaFipeProvider
from app.services.vehicle_normalizer import (
    normalize_make, normalize_model, normalize_engine
)

logger = logging.getLogger(__name__)

MERCOSUL_REGEX = r'^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$'
OLD_PLATE_REGEX = r'^[A-Z]{3}[0-9]{4}$'

def validate_plate_format(plate: str) -> str:
    clean = plate.upper().replace("-", "").replace(" ", "").strip()
    if not (re.match(MERCOSUL_REGEX, clean) or re.match(OLD_PLATE_REGEX, clean)):
        raise ValueError("INVALID_PLATE")
    return clean

class PlateLookupService:
    def __init__(self, db: Session):
        self.db = db
        self.providers = []
        selected_provider = settings.VEHICLE_PROVIDER.upper().strip()

        if selected_provider == "MOCK":
            if settings.APP_ENV.lower() == "production":
                logger.warning("VEHICLE_PROVIDER is set to MOCK in production environment.")
            else:
                self.providers.append(MockPlateProvider())
        elif selected_provider == "APIPLACA":
            self.providers.append(ApiPlacaProvider(api_key=settings.VEHICLE_API_KEY, base_url=settings.VEHICLE_API_URL or "https://apiplaca.com.br/v1/consultar"))
        else:
            # Fallback
            self.providers.append(ApiPlacaProvider(api_key=settings.VEHICLE_API_KEY, base_url=settings.VEHICLE_API_URL or "https://apiplaca.com.br/v1/consultar"))
            if settings.APP_ENV.lower() != "production":
                self.providers.append(MockPlateProvider())

    def get_or_fetch_plate(self, plate: str) -> Dict[str, Any]:
        try:
            clean_plate = validate_plate_format(plate)
        except ValueError:
            return {
                "plate": plate,
                "status": "INVALID_PLATE",
                "message": "Formato de placa inválido. Utilize o padrão antigo (ABC1234) ou Mercosul (ABC1D23).",
                "vehicle": None
            }

        # 1. Check local PostgreSQL/SQLite cache
        cache = self.db.query(VehiclePlateCache).filter(VehiclePlateCache.plate == clean_plate).first()
        if cache and cache.expires_at > datetime.utcnow():
            vehicle_data = None
            if cache.vehicle:
                vehicle_data = self._format_vehicle_dict(cache.vehicle)

            possible_vehicle_ids = []
            if cache.possible_vehicle_ids:
                possible_vehicle_ids = [int(vid.strip()) for vid in cache.possible_vehicle_ids.split(",") if vid.strip()]

            return {
                "plate": clean_plate,
                "status": "VEHICLE_VARIANT_AMBIGUOUS" if cache.is_ambiguous else ("SUCCESS" if cache.vehicle else "VEHICLE_NOT_FOUND"),
                "vehicle": vehicle_data,
                "is_ambiguous": cache.is_ambiguous,
                "possible_vehicle_ids": possible_vehicle_ids,
                "cache_info": {
                    "source": cache.source,
                    "consulted_at": cache.consulted_at.isoformat(),
                    "expires_at": cache.expires_at.isoformat(),
                    "data_quality": cache.data_quality,
                    "confidence": cache.confidence,
                    "from_cache": True
                }
            }

        # Production check for mock/unconfigured settings
        if settings.APP_ENV.lower() == "production" and (settings.VEHICLE_PROVIDER.upper() == "MOCK" or not settings.VEHICLE_API_KEY):
            return {
                "plate": clean_plate,
                "status": "PROVIDER_NOT_CONFIGURED",
                "message": "Nenhum provedor oficial de consulta por placa está configurado em ambiente de produção.",
                "vehicle": None
            }

        # 2. Query external provider chain
        raw_info = None
        used_provider = None
        last_provider_status = "PROVIDER_NOT_CONFIGURED"

        for provider in self.providers:
            status_code, info = provider.fetch_plate_info(clean_plate)
            if status_code == "SUCCESS" and info:
                raw_info = info
                used_provider = provider.provider_name
                last_provider_status = "SUCCESS"
                break
            else:
                last_provider_status = status_code

        if not raw_info or last_provider_status != "SUCCESS":
            return {
                "plate": clean_plate,
                "status": last_provider_status,
                "message": f"Erro na consulta do provedor: {last_provider_status}",
                "vehicle": None
            }

        # 3. Normalize & Persist Vehicle in DB
        vehicle_entity, is_ambiguous, possible_ids = self._get_or_create_vehicle(raw_info)

        # 4. Save/Update Cache
        expires_at = datetime.utcnow() + timedelta(days=settings.PLATE_CACHE_TTL_DAYS)
        if not cache:
            cache = VehiclePlateCache(
                plate=clean_plate,
                vehicle_id=vehicle_entity.id if vehicle_entity else None,
                is_ambiguous=is_ambiguous,
                possible_vehicle_ids=",".join(map(str, possible_ids)) if possible_ids else None,
                source=used_provider,
                source_vehicle_id=str(raw_info.get("source_vehicle_id", "")),
                consulted_at=datetime.utcnow(),
                expires_at=expires_at,
                data_quality=raw_info.get("data_quality", "HIGH"),
                confidence=float(raw_info.get("confidence", 1.0)),
                raw_response_hash=raw_info.get("raw_response_hash", "hash_placeholder"),
                raw_response_json=json.dumps(raw_info.get("raw_data", {}))
            )
            self.db.add(cache)
        else:
            cache.vehicle_id = vehicle_entity.id if vehicle_entity else None
            cache.is_ambiguous = is_ambiguous
            cache.possible_vehicle_ids = ",".join(map(str, possible_ids)) if possible_ids else None
            cache.source = used_provider
            cache.consulted_at = datetime.utcnow()
            cache.expires_at = expires_at
            cache.data_quality = raw_info.get("data_quality", "HIGH")
            cache.confidence = float(raw_info.get("confidence", 1.0))
            cache.raw_response_hash = raw_info.get("raw_response_hash", "hash_placeholder")
            cache.raw_response_json = json.dumps(raw_info.get("raw_data", {}))

        self.db.commit()
        self.db.refresh(cache)

        vehicle_data = self._format_vehicle_dict(vehicle_entity) if vehicle_entity else None

        return {
            "plate": clean_plate,
            "status": "VEHICLE_VARIANT_AMBIGUOUS" if is_ambiguous else "SUCCESS",
            "vehicle": vehicle_data,
            "is_ambiguous": is_ambiguous,
            "possible_vehicle_ids": possible_ids,
            "cache_info": {
                "source": cache.source,
                "consulted_at": cache.consulted_at.isoformat(),
                "expires_at": cache.expires_at.isoformat(),
                "data_quality": cache.data_quality,
                "confidence": cache.confidence,
                "from_cache": False
            }
        }

    def _get_or_create_vehicle(self, info: Dict[str, Any]) -> Tuple[Optional[Vehicle], bool, List[int]]:
        make_name = normalize_make(info.get("make"))
        model_name = normalize_model(info.get("model"))
        engine_desc = normalize_engine(info.get("engine"))

        if not make_name or not model_name:
            return None, False, []

        make = self.db.query(VehicleMake).filter(VehicleMake.name == make_name).first()
        if not make:
            make = VehicleMake(name=make_name, normalized_name=make_name.upper())
            self.db.add(make)
            self.db.flush()

        model = self.db.query(VehicleModel).filter(
            VehicleModel.make_id == make.id,
            VehicleModel.normalized_name == model_name.upper()
        ).first()
        if not model:
            model = VehicleModel(make_id=make.id, name=model_name, normalized_name=model_name.upper())
            self.db.add(model)
            self.db.flush()

        version_str = info.get("version", "").strip() if info.get("version") else ""
        version = None
        if version_str:
            version = self.db.query(VehicleVersion).filter(VehicleVersion.name == version_str).first()
            if not version:
                version = VehicleVersion(name=version_str, normalized_name=version_str.upper())
                self.db.add(version)
                self.db.flush()

        engine = None
        if engine_desc:
            engine = self.db.query(VehicleEngine).filter(VehicleEngine.description == engine_desc).first()
            if not engine:
                engine = VehicleEngine(description=engine_desc)
                self.db.add(engine)
                self.db.flush()

        fuel_str = info.get("fuel").strip() if info.get("fuel") else None
        fuel = None
        if fuel_str:
            fuel = self.db.query(VehicleFuel).filter(VehicleFuel.name == fuel_str).first()
            if not fuel:
                fuel = VehicleFuel(name=fuel_str)
                self.db.add(fuel)
                self.db.flush()

        trans_str = info.get("transmission").strip() if info.get("transmission") else None
        transmission = None
        if trans_str:
            transmission = self.db.query(VehicleTransmission).filter(VehicleTransmission.type == trans_str).first()
            if not transmission:
                transmission = VehicleTransmission(type=trans_str)
                self.db.add(transmission)
                self.db.flush()

        year_mfg = int(info.get("year_manufacture")) if info.get("year_manufacture") else 2020
        year_mod = int(info.get("year_model")) if info.get("year_model") else 2021
        fipe = info.get("fipe_code")

        is_ambiguous = bool(info.get("is_ambiguous", False))

        vehicle_filter = [
            Vehicle.make_id == make.id,
            Vehicle.model_id == model.id,
            Vehicle.year_manufacture == year_mfg,
            Vehicle.year_model == year_mod
        ]
        if version:
            vehicle_filter.append(Vehicle.version_id == version.id)
        if engine:
            vehicle_filter.append(Vehicle.engine_id == engine.id)

        vehicle = self.db.query(Vehicle).filter(*vehicle_filter).first()

        if not vehicle:
            vehicle = Vehicle(
                make_id=make.id,
                model_id=model.id,
                version_id=version.id if version else None,
                engine_id=engine.id if engine else None,
                transmission_id=transmission.id if transmission else None,
                fuel_id=fuel.id if fuel else None,
                year_manufacture=year_mfg,
                year_model=year_mod,
                fipe_code=fipe
            )
            self.db.add(vehicle)
            self.db.flush()

        possible_ids = [vehicle.id]
        return vehicle, is_ambiguous, possible_ids

    def _format_vehicle_dict(self, vehicle: Vehicle) -> Dict[str, Any]:
        return {
            "id": vehicle.id,
            "make": vehicle.make.name if vehicle.make else None,
            "model": vehicle.model.name if vehicle.model else None,
            "version": vehicle.version.name if vehicle.version else None,
            "year_manufacture": vehicle.year_manufacture,
            "year_model": vehicle.year_model,
            "engine": vehicle.engine.description if vehicle.engine else None,
            "fuel": vehicle.fuel.name if vehicle.fuel else None,
            "transmission": vehicle.transmission.type if vehicle.transmission else None,
            "fipe_code": vehicle.fipe_code
        }
