import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import (
    VehicleMake, VehicleModel, VehicleVersion, VehicleFuel, Vehicle, SyncLog
)
from app.providers.tabelafipe_provider import TabelaFipeProvider
from app.services.vehicle_normalizer import normalize_make, normalize_model

logger = logging.getLogger("fipe_service")

class FipeService:
    """
    On-Demand Hybrid Vehicle Service:
    1. Queries local PostgreSQL first for Make/Model/Year/Version/FIPE records.
    2. If missing or stale, queries TabelaFIPE.info provider, normalizes, upserts into PostgreSQL, and returns cached records.
    """
    def __init__(self, db: Session, provider: Optional[TabelaFipeProvider] = None):
        self.db = db
        self.provider = provider or TabelaFipeProvider(delay_sec=0.2)

    def get_or_fetch_vehicles(
        self,
        make_name: str,
        model_name: str,
        year: Optional[int] = None
    ) -> List[Vehicle]:
        norm_make = normalize_make(make_name) or make_name.strip()
        norm_model = normalize_model(model_name) or model_name.strip()

        # 1. Query local database
        q = self.db.query(Vehicle).join(VehicleMake).join(VehicleModel).filter(
            VehicleMake.name == norm_make,
            VehicleModel.normalized_name == norm_model.upper()
        )
        if year:
            q = q.filter((Vehicle.year_manufacture == year) | (Vehicle.year_model == year))

        local_vehicles = q.all()
        if local_vehicles:
            logger.info(f"FipeService: Found {len(local_vehicles)} vehicles locally for {norm_make} {norm_model} ({year or 'All Years'}).")
            return local_vehicles

        # 2. On-Demand Fetch from TabelaFIPE.info API
        logger.info(f"FipeService: Vehicle not found locally. On-demand fetching from TabelaFIPE.info for {norm_make} {norm_model}...")
        make_slug = norm_make.lower().replace(" ", "-").replace("/", "-")
        family_slug = norm_model.lower().replace(" ", "-").replace("/", "-")

        family_data = self.provider.get_family_prices(make_slug, family_slug)
        if not family_data or "precos" not in family_data:
            logger.warning(f"FipeService: No data returned from TabelaFIPE.info for {make_slug}/{family_slug}.")
            return []

        # Upsert Make
        db_make = self.db.query(VehicleMake).filter_by(normalized_name=norm_make.upper()).first()
        if not db_make:
            db_make = VehicleMake(name=norm_make, normalized_name=norm_make.upper())
            self.db.add(db_make)
            self.db.flush()

        # Upsert Model
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
            self.db.flush()

        saved_vehicles = []
        for item in family_data["precos"]:
            item_year = item.get("ano")
            if year and item_year != year:
                continue

            ver_name = item.get("versao", norm_model)
            fipe_code = item.get("codigo_fipe")
            fuel_name = item.get("combustivel", "Flex")

            # Upsert Fuel
            db_fuel = self.db.query(VehicleFuel).filter_by(name=fuel_name).first()
            if not db_fuel:
                db_fuel = VehicleFuel(name=fuel_name)
                self.db.add(db_fuel)
                self.db.flush()

            # Upsert Version
            norm_ver = ver_name.strip().upper()
            db_version = self.db.query(VehicleVersion).filter_by(normalized_name=norm_ver).first()
            if not db_version:
                db_version = VehicleVersion(name=ver_name.strip(), normalized_name=norm_ver)
                self.db.add(db_version)
                self.db.flush()

            # Upsert Vehicle
            existing_v = None
            if fipe_code:
                existing_v = self.db.query(Vehicle).filter_by(
                    make_id=db_make.id,
                    model_id=db_model.id,
                    year_model=item_year,
                    fipe_code=fipe_code
                ).first()

            if not existing_v:
                existing_v = self.db.query(Vehicle).filter_by(
                    make_id=db_make.id,
                    model_id=db_model.id,
                    version_id=db_version.id,
                    year_model=item_year
                ).first()

            if existing_v:
                existing_v.fipe_code = fipe_code
                existing_v.fuel_id = db_fuel.id
            else:
                existing_v = Vehicle(
                    make_id=db_make.id,
                    model_id=db_model.id,
                    version_id=db_version.id,
                    engine_id=None, # Explicitly NULL - do not invent motorization
                    transmission_id=None,
                    fuel_id=db_fuel.id,
                    year_manufacture=item_year,
                    year_model=item_year,
                    fipe_code=fipe_code
                )
                self.db.add(existing_v)

            saved_vehicles.append(existing_v)

        self.db.commit()
        logger.info(f"FipeService: Saved {len(saved_vehicles)} vehicles to PostgreSQL on-demand.")
        return saved_vehicles
