import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import (
    VehicleMake, VehicleModel, VehicleVersion, VehicleEngine, VehicleTransmission, VehicleFuel, Vehicle,
    FipeCacheTracking, SyncLog
)
from app.providers.tabelafipe_provider import TabelaFipeProvider
from app.core.config import settings
from app.services.vehicle_normalizer import normalize_make, normalize_model, parse_version_specs

logger = logging.getLogger("fipe_service")

class FipeService:
    """
    On-Demand Hybrid Cascading FIPE Service with PostgreSQL Cache Tracking.
    Checks FipeCacheTracking for current FIPE reference month.
    If missing or stale, queries TabelaFIPE.info, performs idempotent UPSERTs into PostgreSQL,
    updates cache tracking, and returns complete vehicle cascading data.
    """
    def __init__(self, db: Session, provider: Optional[TabelaFipeProvider] = None):
        self.db = db
        self.provider = provider or TabelaFipeProvider(delay_sec=0.2)

    def _get_current_fipe_reference(self) -> str:
        ref_data = self.provider.get_reference_period() if settings.FIPE_AUTO_UPDATE else None
        if ref_data and "label" in ref_data:
            return str(ref_data["label"])
        return "outubro/2026"

    def is_cache_valid(self, cache_key: str, current_ref: str) -> bool:
        record = self.db.query(FipeCacheTracking).filter_by(cache_key=cache_key).first()
        if record and record.fipe_reference == current_ref and record.status == "VALID":
            return True
        return False

    def mark_cache_valid(self, cache_key: str, current_ref: str):
        record = self.db.query(FipeCacheTracking).filter_by(cache_key=cache_key).first()
        now = datetime.now(timezone.utc)
        if not record:
            record = FipeCacheTracking(
                cache_key=cache_key,
                fipe_reference=current_ref,
                last_synced_at=now,
                status="VALID"
            )
            self.db.add(record)
        else:
            record.fipe_reference = current_ref
            record.last_synced_at = now
            record.status = "VALID"
        self.db.commit()

    def get_makes_ondemand(self) -> List[VehicleMake]:
        current_ref = self._get_current_fipe_reference()
        cache_key = "MAKES"

        if not settings.FIPE_AUTO_UPDATE or self.is_cache_valid(cache_key, current_ref):
            makes = self.db.query(VehicleMake).order_by(VehicleMake.name).all()
            if makes or not settings.FIPE_AUTO_UPDATE:
                return makes

        # Fetch from TabelaFIPE.info
        logger.info("FipeService: Fetching makes on-demand from TabelaFIPE.info...")
        brands_data = self.provider.get_makes("carros")
        if not brands_data:
            logger.warning("FipeService: API unavailable or empty. Returning local DB makes.")
            return self.db.query(VehicleMake).order_by(VehicleMake.name).all()

        for b in brands_data:
            raw_name = b.get("name", "").strip()
            norm_name = normalize_make(raw_name) or raw_name.title()
            db_make = self.db.query(VehicleMake).filter_by(normalized_name=norm_name.upper()).first()
            if not db_make:
                db_make = VehicleMake(name=norm_name, normalized_name=norm_name.upper())
                self.db.add(db_make)

        self.db.commit()
        self.mark_cache_valid(cache_key, current_ref)
        return self.db.query(VehicleMake).order_by(VehicleMake.name).all()

    def get_models_ondemand(self, make_id: int) -> List[VehicleModel]:
        db_make = self.db.query(VehicleMake).filter_by(id=make_id).first()
        if not db_make:
            return []

        current_ref = self._get_current_fipe_reference()
        cache_key = f"MODELS:{make_id}"

        if not settings.FIPE_AUTO_UPDATE or self.is_cache_valid(cache_key, current_ref):
            models = self.db.query(VehicleModel).filter_by(make_id=make_id).order_by(VehicleModel.name).all()
            if models or not settings.FIPE_AUTO_UPDATE:
                return models

        # Fetch from TabelaFIPE.info
        logger.info(f"FipeService: Fetching models for make '{db_make.name}' on-demand from TabelaFIPE.info...")
        make_slug = db_make.name.lower().replace(" ", "-").replace("/", "-")
        models_resp = self.provider.get_models_by_make(make_slug)

        if not models_resp or "families" not in models_resp:
            logger.warning(f"FipeService: Provider returned no models for {make_slug}. Returning local DB models.")
            return self.db.query(VehicleModel).filter_by(make_id=make_id).order_by(VehicleModel.name).all()

        for fam in models_resp["families"]:
            fam_name = fam.get("name", "").strip()
            norm_model = normalize_model(fam_name) or fam_name.title()

            db_model = self.db.query(VehicleModel).filter_by(
                make_id=db_make.id,
                normalized_name=norm_model.upper()
            ).first()

            if not db_model:
                db_model = VehicleModel(
                    make_id=db_make.id,
                    name=norm_model,
                    normalized_name=norm_model.upper()
                )
                self.db.add(db_model)

        self.db.commit()
        self.mark_cache_valid(cache_key, current_ref)
        return self.db.query(VehicleModel).filter_by(make_id=make_id).order_by(VehicleModel.name).all()

    def get_years_ondemand(self, model_id: int) -> List[int]:
        db_model = self.db.query(VehicleModel).filter_by(id=model_id).first()
        if not db_model:
            return []

        current_ref = self._get_current_fipe_reference()
        cache_key = f"YEARS:{model_id}"

        if settings.FIPE_AUTO_UPDATE and not self.is_cache_valid(cache_key, current_ref):
            db_make = db_model.make
            make_slug = db_make.name.lower().replace(" ", "-").replace("/", "-")
            family_slug = db_model.name.lower().replace(" ", "-").replace("/", "-")

            prices_resp = self.provider.get_family_prices(make_slug, family_slug)
            if prices_resp and "precos" in prices_resp:
                for item in prices_resp["precos"]:
                    item_year = item.get("ano")
                    ver_name = item.get("versao", db_model.name)
                    fipe_code = item.get("codigo_fipe")
                    fuel_name = item.get("combustivel", "Flex")

                    if not item_year or item_year == 32000:
                        item_year = datetime.now(timezone.utc).year

                    # Parse version description specs
                    specs = parse_version_specs(ver_name)
                    effective_fuel = specs["fuel"] or fuel_name

                    # Fuel
                    db_fuel = self.db.query(VehicleFuel).filter_by(name=effective_fuel).first()
                    if not db_fuel:
                        db_fuel = VehicleFuel(name=effective_fuel)
                        self.db.add(db_fuel)
                        self.db.flush()

                    # Engine
                    db_engine = None
                    if specs["engine_desc"]:
                        db_engine = self.db.query(VehicleEngine).filter_by(description=specs["engine_desc"]).first()
                        if not db_engine:
                            db_engine = VehicleEngine(
                                description=specs["engine_desc"],
                                displacement=specs["displacement"],
                                valves=specs["valves"],
                                power_hp=None
                            )
                            self.db.add(db_engine)
                            self.db.flush()

                    # Transmission
                    db_trans = None
                    if specs["transmission"]:
                        db_trans = self.db.query(VehicleTransmission).filter_by(type=specs["transmission"]).first()
                        if not db_trans:
                            db_trans = VehicleTransmission(type=specs["transmission"])
                            self.db.add(db_trans)
                            self.db.flush()

                    # Version
                    norm_ver = ver_name.strip().upper()
                    db_version = self.db.query(VehicleVersion).filter_by(normalized_name=norm_ver).first()
                    if not db_version:
                        db_version = VehicleVersion(name=ver_name.strip(), normalized_name=norm_ver)
                        self.db.add(db_version)
                        self.db.flush()

                    # Vehicle
                    v_existing = self.db.query(Vehicle).filter_by(
                        make_id=db_make.id,
                        model_id=db_model.id,
                        version_id=db_version.id,
                        year_model=item_year
                    ).first()

                    if v_existing:
                        v_existing.fipe_code = fipe_code
                        v_existing.fipe_reference = current_ref
                        if db_engine:
                            v_existing.engine_id = db_engine.id
                        if db_trans:
                            v_existing.transmission_id = db_trans.id
                        if db_fuel:
                            v_existing.fuel_id = db_fuel.id
                    else:
                        v_new = Vehicle(
                            make_id=db_make.id,
                            model_id=db_model.id,
                            version_id=db_version.id,
                            engine_id=db_engine.id if db_engine else None,
                            transmission_id=db_trans.id if db_trans else None,
                            fuel_id=db_fuel.id,
                            year_manufacture=item_year,
                            year_model=item_year,
                            fipe_code=fipe_code,
                            fipe_reference=current_ref
                        )
                        self.db.add(v_new)

                self.db.commit()
                self.mark_cache_valid(cache_key, current_ref)

        # Return unique sorted years from DB
        vehicles = self.db.query(Vehicle).filter_by(model_id=model_id).all()
        years_set = set()
        for v in vehicles:
            if v.year_model:
                years_set.add(v.year_model)
            if v.year_manufacture:
                years_set.add(v.year_manufacture)
        return sorted(list(years_set), reverse=True)

    def get_versions_ondemand(self, model_id: int, year: int) -> List[Dict[str, Any]]:
        db_model = self.db.query(VehicleModel).filter_by(id=model_id).first()
        if not db_model:
            return []

        # Ensure model years/versions are loaded
        self.get_years_ondemand(model_id)

        vehicles = self.db.query(Vehicle).filter(
            Vehicle.model_id == model_id,
            (Vehicle.year_manufacture == year) | (Vehicle.year_model == year)
        ).all()

        versions = []
        seen = set()
        for v in vehicles:
            if v.version and v.version.id not in seen:
                seen.add(v.version.id)
                versions.append({
                    "id": v.version.id,
                    "name": v.version.name,
                    "fipe_code": v.fipe_code
                })
        return versions

    def get_or_fetch_vehicles(
        self,
        make_name: str,
        model_name: str,
        year: Optional[int] = None
    ) -> List[Vehicle]:
        norm_make = normalize_make(make_name) or make_name.strip()
        norm_model = normalize_model(model_name) or model_name.strip()

        q_make = self.db.query(VehicleMake).filter_by(normalized_name=norm_make.upper()).first()
        if q_make:
            models = self.get_models_ondemand(q_make.id)
            q_model = self.db.query(VehicleModel).filter_by(make_id=q_make.id, normalized_name=norm_model.upper()).first()
            if q_model:
                self.get_years_ondemand(q_model.id)

        q = self.db.query(Vehicle).join(VehicleMake).join(VehicleModel).filter(
            VehicleMake.name == norm_make,
            VehicleModel.normalized_name == norm_model.upper()
        )
        if year:
            q = q.filter((Vehicle.year_manufacture == year) | (Vehicle.year_model == year))

        return q.all()
