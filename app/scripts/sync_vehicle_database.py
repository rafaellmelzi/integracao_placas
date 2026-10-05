import sys
import time
import argparse
import urllib.request
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import (
    VehicleMake, VehicleModel, VehicleVersion, VehicleFuel, Vehicle, SyncLog
)
from app.services.vehicle_normalizer import normalize_make, normalize_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vehicle_sync")

BASE_FIPE_URL = "https://parallelum.com.br/fipe/api/v1/carros"
HTTP_HEADERS = {"User-Agent": "AutoParts-VehicleSync/1.0"}

def fetch_json(url: str, retries: int = 3, backoff: float = 1.0) -> Optional[Any]:
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                logger.warning(f"Failed to fetch {url} after {retries} attempts: {e}")
                return None
            time.sleep(backoff * (attempt + 1))
    return None

class VehicleDatabaseSyncer:
    def __init__(self, db: Session, delay_sec: float = 0.1, limit_makes: Optional[int] = None, limit_models: Optional[int] = None):
        self.db = db
        self.delay_sec = delay_sec
        self.limit_makes = limit_makes
        self.limit_models = limit_models

        self.processed = 0
        self.inserted = 0
        self.updated = 0
        self.skipped = 0
        self.errors = 0
        self.start_time = datetime.utcnow()

    def run(self):
        logger.info("=== Starting Vehicle Database Synchronization (Source: Parallelum FIPE) ===")
        print("Sincronizando marcas da FIPE pública...")

        makes_data = fetch_json(f"{BASE_FIPE_URL}/marcas")
        if not makes_data:
            logger.error("Could not fetch vehicle makes from FIPE API.")
            return

        print(f"-> {len(makes_data)} marcas encontradas no catálogo FIPE.")
        if self.limit_makes:
            makes_data = makes_data[:self.limit_makes]
            print(f"-> Limite de teste aplicado: sincronizando apenas {self.limit_makes} marca(s).")

        for idx, make_item in enumerate(makes_data, 1):
            fipe_make_id = make_item.get("codigo")
            raw_make_name = make_item.get("nome", "").strip()
            norm_make_name = normalize_make(raw_make_name) or raw_make_name.title()

            print(f"\n[{idx}/{len(makes_data)}] Processando Marca: {norm_make_name} (FIPE Code: {fipe_make_id})...")

            # Upsert VehicleMake
            db_make = self.db.query(VehicleMake).filter_by(normalized_name=norm_make_name.upper()).first()
            if not db_make:
                db_make = VehicleMake(name=norm_make_name, normalized_name=norm_make_name.upper())
                self.db.add(db_make)
                self.db.flush()

            # Fetch models
            models_url = f"{BASE_FIPE_URL}/marcas/{fipe_make_id}/modelos"
            models_resp = fetch_json(models_url)
            time.sleep(self.delay_sec)

            if not models_resp or "modelos" not in models_resp:
                logger.warning(f"No models found for make {norm_make_name}")
                continue

            models_data = models_resp["modelos"]
            print(f"  └─ {len(models_data)} modelos encontrados.")
            if self.limit_models:
                models_data = models_data[:self.limit_models]

            for m_idx, model_item in enumerate(models_data, 1):
                fipe_model_id = model_item.get("codigo")
                raw_model_name = model_item.get("nome", "").strip()
                norm_model_name = normalize_model(raw_model_name) or raw_model_name.title()

                # Upsert VehicleModel
                db_model = self.db.query(VehicleModel).filter_by(
                    make_id=db_make.id,
                    normalized_name=norm_model_name.upper()
                ).first()

                if not db_model:
                    db_model = VehicleModel(
                        make_id=db_make.id,
                        name=norm_model_name,
                        normalized_name=norm_model_name.upper()
                    )
                    self.db.add(db_model)
                    self.db.flush()

                # Fetch Years/Versions
                years_url = f"{BASE_FIPE_URL}/marcas/{fipe_make_id}/modelos/{fipe_model_id}/anos"
                years_data = fetch_json(years_url)
                time.sleep(self.delay_sec)

                if not years_data:
                    continue

                for year_item in years_data:
                    fipe_year_id = year_item.get("codigo")

                    # Fetch Vehicle Detail
                    detail_url = f"{BASE_FIPE_URL}/marcas/{fipe_make_id}/modelos/{fipe_model_id}/anos/{fipe_year_id}"
                    detail = fetch_json(detail_url)
                    time.sleep(self.delay_sec)

                    if not detail:
                        self.errors += 1
                        continue

                    self.processed += 1
                    fipe_code = detail.get("CodigoFipe")
                    year_model = detail.get("AnoModelo")
                    fuel_name = detail.get("Combustivel", "Flex")
                    version_name = detail.get("Modelo", raw_model_name)

                    if not year_model or year_model == 32000: # Zero KM placeholder in FIPE
                        year_model = datetime.now().year

                    # Upsert Fuel
                    db_fuel = self.db.query(VehicleFuel).filter_by(name=fuel_name).first()
                    if not db_fuel:
                        db_fuel = VehicleFuel(name=fuel_name)
                        self.db.add(db_fuel)
                        self.db.flush()

                    # Upsert Version
                    norm_ver = version_name.strip().upper()
                    db_version = self.db.query(VehicleVersion).filter_by(normalized_name=norm_ver).first()
                    if not db_version:
                        db_version = VehicleVersion(name=version_name.strip(), normalized_name=norm_ver)
                        self.db.add(db_version)
                        self.db.flush()

                    # Check existing Vehicle by FIPE code or Make/Model/Year/Version
                    existing_vehicle = None
                    if fipe_code:
                        existing_vehicle = self.db.query(Vehicle).filter_by(
                            make_id=db_make.id,
                            model_id=db_model.id,
                            year_model=year_model,
                            fipe_code=fipe_code
                        ).first()

                    if not existing_vehicle:
                        existing_vehicle = self.db.query(Vehicle).filter_by(
                            make_id=db_make.id,
                            model_id=db_model.id,
                            version_id=db_version.id,
                            year_model=year_model
                        ).first()

                    if existing_vehicle:
                        existing_vehicle.fipe_code = fipe_code
                        existing_vehicle.fuel_id = db_fuel.id
                        self.updated += 1
                    else:
                        new_vehicle = Vehicle(
                            make_id=db_make.id,
                            model_id=db_model.id,
                            version_id=db_version.id,
                            engine_id=None, # Strictly NULL - Do not invent motorization
                            transmission_id=None,
                            fuel_id=db_fuel.id,
                            year_manufacture=year_model,
                            year_model=year_model,
                            fipe_code=fipe_code
                        )
                        self.db.add(new_vehicle)
                        self.inserted += 1

                    if self.processed % 20 == 0:
                        self.db.commit()
                        print(f"  └─ Progresso: {self.processed} veículos processados ({self.inserted} inseridos, {self.updated} atualizados)...")

        self.db.commit()
        end_time = datetime.utcnow()

        # Record SyncLog
        log_entry = SyncLog(
            source_name="FIPE_PUBLIC_SOURCE",
            records_processed=self.processed,
            records_success=self.inserted + self.updated,
            records_failed=self.errors,
            status="SUCCESS" if self.errors == 0 else "PARTIAL_SUCCESS",
            details=f"Processed: {self.processed}, Inserted: {self.inserted}, Updated: {self.updated}, Skipped: {self.skipped}, Errors: {self.errors}",
            created_at=end_time
        )
        self.db.add(log_entry)
        self.db.commit()

        print("\n==================================================")
        print("RESUMO DA SINCRONIZAÇÃO DA BASE DE VEÍCULOS")
        print("==================================================")
        print(f"Fonte de Dados       : FIPE_PUBLIC_SOURCE (Parallelum)")
        print(f"Veículos Processados : {self.processed}")
        print(f"Veículos Inseridos   : {self.inserted}")
        print(f"Veículos Atualizados : {self.updated}")
        print(f"Erros / Falhas       : {self.errors}")
        print(f"Duração              : {end_time - self.start_time}")
        print("==================================================\n")

def main():
    parser = argparse.ArgumentParser(description="Sincronizador Idempotente de Base de Veículos com FIPE Gratuita")
    parser.add_argument("--limit-makes", type=int, default=None, help="Limita o número de marcas a sincronizar (útil para testes)")
    parser.add_argument("--limit-models", type=int, default=None, help="Limita o número de modelos por marca")
    parser.add_argument("--delay", type=float, default=0.05, help="Intervalo de pausa entre requisições externas em segundos")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        syncer = VehicleDatabaseSyncer(
            db=db,
            delay_sec=args.delay,
            limit_makes=args.limit_makes,
            limit_models=args.limit_models
        )
        syncer.run()
    finally:
        db.close()

if __name__ == "__main__":
    main()
