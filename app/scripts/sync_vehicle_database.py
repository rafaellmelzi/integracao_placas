import sys
import os
import time
import random
import argparse
import urllib.request
import urllib.error
import email.utils
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

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
CHECKPOINT_FILE = "vehicle_sync_checkpoint.json"

class RateLimitError(Exception):
    pass

class SyncStats:
    def __init__(self):
        self.http_429_count = 0

stats = SyncStats()

def parse_retry_after(header_val: Optional[str]) -> Optional[float]:
    """
    Parse Retry-After header as integer seconds or HTTP-date.
    Returns float seconds if valid, or None if invalid/negative.
    """
    if not header_val or not header_val.strip():
        return None

    val_str = header_val.strip()
    if val_str.isdigit():
        sec = float(val_str)
        return sec if sec >= 0 else None

    # Try parsing as HTTP-date
    try:
        dt = email.utils.parsedate_to_datetime(val_str)
        if dt:
            now = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = (dt - now).total_seconds()
            return delta if delta > 0 else 0.0
    except Exception:
        pass

    return None

def fetch_json(url: str, max_retries: int = 10) -> Optional[Any]:
    """
    Polite and resilient HTTP fetcher for public APIs.
    Specifically handles HTTP 429 Too Many Requests using Retry-After headers or exponential backoff with jitter.
    Strictly caps any wait time to MAX 60 seconds (min(calculated, 60.0)).
    Differentiates between valid empty responses, HTTP 429, permanent HTTP errors, and transient network timeouts.
    """
    backoff_schedule = [5.0, 10.0, 20.0, 40.0, 60.0]

    for attempt in range(max_retries):
        req = urllib.request.Request(url, headers=HTTP_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    raw_body = resp.read().decode("utf-8")
                    return json.loads(raw_body)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                stats.http_429_count += 1
                retry_after_hdr = e.headers.get("Retry-After")
                parsed_sec = parse_retry_after(retry_after_hdr)

                if parsed_sec is not None and parsed_sec > 0:
                    base_wait = parsed_sec
                else:
                    idx = min(attempt, len(backoff_schedule) - 1)
                    base_wait = backoff_schedule[idx]

                # Cap base wait to 60.0 max BEFORE or AFTER jitter
                base_wait_capped = min(base_wait, 60.0)
                jitter = random.uniform(0.5, 1.5)
                wait_time = min(base_wait_capped + jitter, 60.0)

                logger.warning(
                    f"HTTP 429 Rate Limit hit for {url}. Original Retry-After: '{retry_after_hdr}', "
                    f"Chosen Wait Time: {wait_time:.1f}s (Attempt {attempt+1}/{max_retries})..."
                )
                time.sleep(wait_time)
                continue
            elif e.code in (400, 404):
                logger.warning(f"Permanent HTTP {e.code} for {url}: Resource not found or bad request.")
                return None
            else:
                logger.warning(f"HTTP {e.code} error for {url}: {e}")
                time.sleep(2.0 + attempt)
        except Exception as e:
            logger.warning(f"Transient network/connection error for {url} (attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(2.0 + attempt)

    logger.error(f"Exhausted {max_retries} attempts for {url} due to persistent errors/rate limits.")
    return None

class CheckpointManager:
    def __init__(self, filepath: str = CHECKPOINT_FILE):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load checkpoint file {self.filepath}: {e}")
        return {
            "completed_makes": [],
            "failed_makes": [],
            "completed_models": {},
            "failed_models": {}
        }

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving checkpoint file {self.filepath}: {e}")

    def is_make_completed(self, make_id: str) -> bool:
        return str(make_id) in self.data["completed_makes"]

    def mark_make_completed(self, make_id: str):
        str_id = str(make_id)
        if str_id not in self.data["completed_makes"]:
            self.data["completed_makes"].append(str_id)
        if str_id in self.data["failed_makes"]:
            self.data["failed_makes"].remove(str_id)
        self.save()

    def mark_make_failed(self, make_id: str):
        str_id = str(make_id)
        if str_id not in self.data["failed_makes"]:
            self.data["failed_makes"].append(str_id)
        self.save()

    def is_model_completed(self, make_id: str, model_id: str) -> bool:
        make_models = self.data["completed_models"].get(str(make_id), [])
        return str(model_id) in make_models

    def mark_model_completed(self, make_id: str, model_id: str):
        mk_str = str(make_id)
        md_str = str(model_id)
        if mk_str not in self.data["completed_models"]:
            self.data["completed_models"][mk_str] = []
        if md_str not in self.data["completed_models"][mk_str]:
            self.data["completed_models"][mk_str].append(md_str)

        if mk_str in self.data["failed_models"] and md_str in self.data["failed_models"][mk_str]:
            self.data["failed_models"][mk_str].remove(md_str)
        self.save()

    def mark_model_failed(self, make_id: str, model_id: str):
        mk_str = str(make_id)
        md_str = str(model_id)
        if mk_str not in self.data["failed_models"]:
            self.data["failed_models"][mk_str] = []
        if md_str not in self.data["failed_models"][mk_str]:
            self.data["failed_models"][mk_str].append(md_str)
        self.save()

class VehicleDatabaseSyncer:
    def __init__(
        self,
        db: Session,
        delay_sec: float = 0.2,
        limit_makes: Optional[int] = None,
        limit_models: Optional[int] = None,
        resume: bool = True,
        retry_failed: bool = False
    ):
        self.db = db
        self.delay_sec = delay_sec
        self.limit_makes = limit_makes
        self.limit_models = limit_models
        self.resume = resume
        self.retry_failed = retry_failed

        self.checkpoint = CheckpointManager()
        self.processed = 0
        self.inserted = 0
        self.updated = 0
        self.errors = 0
        self.start_time = datetime.now(timezone.utc)

    def run(self):
        logger.info("=== Starting Vehicle Database Synchronization (Source: Parallelum FIPE) ===")
        print("Sincronizando marcas da FIPE pública...")

        makes_data = fetch_json(f"{BASE_FIPE_URL}/marcas")
        if not makes_data:
            logger.error("Could not fetch vehicle makes from FIPE API due to connection or rate limits.")
            print("ERRO CRÍTICO: Não foi possível obter as marcas da FIPE. A sincronização foi interrompida.")
            return

        print(f"-> {len(makes_data)} marcas encontradas no catálogo FIPE.")
        if self.limit_makes:
            makes_data = makes_data[:self.limit_makes]
            print(f"-> Limite de teste aplicado: sincronizando apenas {self.limit_makes} marca(s).")

        for idx, make_item in enumerate(makes_data, 1):
            fipe_make_id = str(make_item.get("codigo"))
            raw_make_name = make_item.get("nome", "").strip()
            norm_make_name = normalize_make(raw_make_name) or raw_make_name.title()

            # Handle Resume / Retry-Failed logic
            if self.resume and not self.retry_failed and self.checkpoint.is_make_completed(fipe_make_id):
                print(f"[{idx}/{len(makes_data)}] Marca {norm_make_name} (ID: {fipe_make_id}) já concluída no checkpoint. Pulando...")
                continue

            if self.retry_failed and fipe_make_id not in self.checkpoint.data["failed_makes"]:
                continue

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

            if models_resp is None or "modelos" not in models_resp:
                logger.error(f"Failed to fetch models for make {norm_make_name} (ID: {fipe_make_id}). Marking make as failed.")
                self.checkpoint.mark_make_failed(fipe_make_id)
                self.errors += 1
                continue

            models_data = models_resp["modelos"]
            print(f"  └─ {len(models_data)} modelos encontrados.")
            if self.limit_models:
                models_data = models_data[:self.limit_models]

            make_success = True
            for m_idx, model_item in enumerate(models_data, 1):
                fipe_model_id = str(model_item.get("codigo"))
                raw_model_name = model_item.get("nome", "").strip()
                norm_model_name = normalize_model(raw_model_name) or raw_model_name.title()

                if self.resume and not self.retry_failed and self.checkpoint.is_model_completed(fipe_make_id, fipe_model_id):
                    continue

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

                if years_data is None:
                    logger.error(f"Failed to fetch years for model {norm_model_name} (ID: {fipe_model_id}). Marking model as failed.")
                    self.checkpoint.mark_model_failed(fipe_make_id, fipe_model_id)
                    make_success = False
                    self.errors += 1
                    continue

                model_success = True
                for year_item in years_data:
                    fipe_year_id = year_item.get("codigo")

                    # Fetch Vehicle Detail
                    detail_url = f"{BASE_FIPE_URL}/marcas/{fipe_make_id}/modelos/{fipe_model_id}/anos/{fipe_year_id}"
                    detail = fetch_json(detail_url)
                    time.sleep(self.delay_sec)

                    if not detail:
                        self.errors += 1
                        model_success = False
                        continue

                    self.processed += 1
                    fipe_code = detail.get("CodigoFipe")
                    year_model = detail.get("AnoModelo")
                    fuel_name = detail.get("Combustivel", "Flex")
                    version_name = detail.get("Modelo", raw_model_name)

                    if not year_model or year_model == 32000: # Zero KM placeholder in FIPE
                        year_model = datetime.now(timezone.utc).year

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

                if model_success:
                    self.checkpoint.mark_model_completed(fipe_make_id, fipe_model_id)
                else:
                    self.checkpoint.mark_model_failed(fipe_make_id, fipe_model_id)
                    make_success = False

            if make_success:
                self.checkpoint.mark_make_completed(fipe_make_id)
            else:
                self.checkpoint.mark_make_failed(fipe_make_id)

        self.db.commit()
        end_time = datetime.now(timezone.utc)

        # Record SyncLog
        log_entry = SyncLog(
            source_name="FIPE_PUBLIC_SOURCE",
            records_processed=self.processed,
            records_success=self.inserted + self.updated,
            records_failed=self.errors,
            status="SUCCESS" if self.errors == 0 and len(self.checkpoint.data["failed_makes"]) == 0 else "PARTIAL_SUCCESS",
            details=f"Processed: {self.processed}, Inserted: {self.inserted}, Updated: {self.updated}, Errors: {self.errors}, HTTP 429 Limits: {stats.http_429_count}, Pending Failed Makes: {len(self.checkpoint.data['failed_makes'])}",
            created_at=end_time
        )
        self.db.add(log_entry)
        self.db.commit()

        print("\n==================================================")
        print("RESUMO DA SINCRONIZAÇÃO DA BASE DE VEÍCULOS")
        print("==================================================")
        print(f"Fonte de Dados          : FIPE_PUBLIC_SOURCE (Parallelum)")
        print(f"Veículos Processados    : {self.processed}")
        print(f"Veículos Inseridos      : {self.inserted}")
        print(f"Veículos Atualizados    : {self.updated}")
        print(f"Ocorrências HTTP 429    : {stats.http_429_count}")
        print(f"Erros / Falhas          : {self.errors}")
        print(f"Marcas Pendentes/Falhas : {len(self.checkpoint.data['failed_makes'])}")
        print(f"Duração                 : {end_time - self.start_time}")
        print("==================================================")

        if len(self.checkpoint.data["failed_makes"]) > 0 or self.errors > 0:
            print("ATENÇÃO: A base de veículos ainda NÃO está 100% sincronizada.")
            print("Para reprocessar os itens pendentes, execute:")
            print("  python -m app.scripts.sync_vehicle_database --retry-failed\n")
        else:
            print("SUCESSO: Sincronização da base de veículos finalizada sem erros pendentes!\n")

def main():
    parser = argparse.ArgumentParser(description="Sincronizador Idempotente de Base de Veículos com FIPE Gratuita")
    parser.add_argument("--limit-makes", type=int, default=None, help="Limita o número de marcas a sincronizar (útil para testes)")
    parser.add_argument("--limit-models", type=int, default=None, help="Limita o número de modelos por marca")
    parser.add_argument("--delay", type=float, default=0.2, help="Intervalo de pausa conservador entre requisições externas em segundos (default: 0.2s)")
    parser.add_argument("--no-resume", action="store_true", help="Desativa a retomada por checkpoint e reprocessa a partir do início")
    parser.add_argument("--retry-failed", action="store_true", help="Processa exclusivamente os itens marcados como falhos no checkpoint")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        syncer = VehicleDatabaseSyncer(
            db=db,
            delay_sec=args.delay,
            limit_makes=args.limit_makes,
            limit_models=args.limit_models,
            resume=not args.no_resume,
            retry_failed=args.retry_failed
        )
        syncer.run()
    finally:
        db.close()

if __name__ == "__main__":
    main()
