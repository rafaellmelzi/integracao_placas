from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, distinct

from app.core.config import settings
from app.db.database import get_db
from app.schemas.schemas import (
    PlateLookupResponseSchema, PartsSearchResponseSchema,
    ERPProductMappingCreateSchema, ERPProductMappingSchema
)
from app.services.plate_lookup_service import PlateLookupService
from app.services.parts_search_service import PartsSearchService
from app.importers.catalog_importer import CatalogImporter
from app.db.models import (
    ERPProductMapping, ERPProductMappingType, ConfidenceLevel, Part,
    VehicleMake, VehicleModel, VehicleVersion, VehicleEngine, Vehicle,
    SyncLog
)
import asyncio

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Healthcheck endpoint verifying DB connectivity and provider configuration status.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    plate_provider_status = "configured" if (settings.VEHICLE_PROVIDER.upper() == "MOCK" or bool(settings.VEHICLE_API_KEY)) else "not_configured"
    catalog_parts_count = db.query(Part).count()
    catalog_status = "configured" if catalog_parts_count > 0 else "not_configured"

    makes_count = db.query(VehicleMake).count()
    models_count = db.query(VehicleModel).count()
    versions_count = db.query(VehicleVersion).count()
    vehicles_count = db.query(Vehicle).count()

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "app_env": settings.APP_ENV,
        "database": db_status,
        "plate_provider": settings.VEHICLE_PROVIDER,
        "plate_provider_available": plate_provider_status == "configured",
        "catalog_status": catalog_status,
        "catalog_parts_count": catalog_parts_count,
        "vehicle_stats": {
            "makes": makes_count,
            "models": models_count,
            "versions": versions_count,
            "vehicles": vehicles_count
        }
    }

# --- FIPE & Vehicle Database Sync Endpoints ---

@router.get("/fipe/reference")
def get_fipe_reference():
    """
    Get current FIPE reference period from active provider.
    """
    from app.providers.tabelafipe_provider import TabelaFipeProvider
    provider = TabelaFipeProvider(delay_sec=0.1)
    ref = provider.get_reference_period()
    return ref or {"periodo": "Indisponível", "label": "Não foi possível obter mês de referência"}

@router.get("/vehicles/sync/status")
def get_vehicle_sync_status(db: Session = Depends(get_db)):
    """
    Get statistics and last sync log status for vehicle database.
    """
    last_log = db.query(SyncLog).filter(SyncLog.source_name.in_(["TABELAFIPE_PUBLIC_SOURCE", "FIPE_PUBLIC_SOURCE"])).order_by(SyncLog.id.desc()).first()
    return {
        "fipe_provider": settings.FIPE_PROVIDER,
        "makes_count": db.query(VehicleMake).count(),
        "models_count": db.query(VehicleModel).count(),
        "versions_count": db.query(VehicleVersion).count(),
        "vehicles_count": db.query(Vehicle).count(),
        "last_sync": {
            "source_name": last_log.source_name if last_log else "N/A",
            "status": last_log.status if last_log else "NEVER_RUN",
            "processed": last_log.records_processed if last_log else 0,
            "success": last_log.records_success if last_log else 0,
            "failed": last_log.records_failed if last_log else 0,
            "details": last_log.details if last_log else None,
            "created_at": last_log.created_at.isoformat() if last_log else None
        } if last_log else None
    }

@router.post("/vehicles/sync")
def trigger_vehicle_sync(limit_makes: Optional[int] = Query(None, description="Optional limit of makes for testing"), db: Session = Depends(get_db)):
    """
    Trigger manual vehicle database synchronization with TabelaFIPE.info public API.
    """
    from app.scripts.sync_vehicle_database import VehicleDatabaseSyncer
    syncer = VehicleDatabaseSyncer(db=db, delay_sec=settings.FIPE_SYNC_DELAY, limit_makes=limit_makes)
    syncer.run()
    return {
        "status": "SUCCESS",
        "processed": syncer.processed,
        "inserted": syncer.inserted,
        "updated": syncer.updated,
        "errors": syncer.errors
    }

# --- Cascading Vehicle Dropdown Endpoints ---

@router.get("/vehicles/makes")
def get_vehicle_makes(db: Session = Depends(get_db)):
    """
    Get list of all vehicle makes in database.
    """
    makes = db.query(VehicleMake).order_by(VehicleMake.name).all()
    return [{"id": m.id, "name": m.name} for m in makes]

@router.get("/vehicles/makes/{make_id}/models")
def get_vehicle_models(make_id: int, db: Session = Depends(get_db)):
    """
    Get list of models for a specific vehicle make.
    """
    models = db.query(VehicleModel).filter(VehicleModel.make_id == make_id).order_by(VehicleModel.name).all()
    return [{"id": m.id, "name": m.name} for m in models]

@router.get("/vehicles/models/{model_id}/years")
def get_vehicle_years(model_id: int, db: Session = Depends(get_db)):
    """
    Get list of available model years for a vehicle model.
    """
    years_mfg = db.query(distinct(Vehicle.year_manufacture)).filter(Vehicle.model_id == model_id).all()
    years_mod = db.query(distinct(Vehicle.year_model)).filter(Vehicle.model_id == model_id).all()

    unique_years = sorted(list(set([y[0] for y in years_mfg if y[0]] + [y[0] for y in years_mod if y[0]])), reverse=True)
    return [{"year": y} for y in unique_years]

@router.get("/vehicles/models/{model_id}/years/{year}/versions")
def get_vehicle_versions(model_id: int, year: int, db: Session = Depends(get_db)):
    """
    Get versions for a specific vehicle model and year.
    """
    vehicles = db.query(Vehicle).filter(
        Vehicle.model_id == model_id,
        (Vehicle.year_manufacture == year) | (Vehicle.year_model == year)
    ).all()

    versions = []
    seen = set()
    for v in vehicles:
        if v.version and v.version.id not in seen:
            seen.add(v.version.id)
            versions.append({"id": v.version.id, "name": v.version.name})

    return versions

@router.get("/vehicles/versions/{version_id}/engines")
def get_vehicle_engines(version_id: int, db: Session = Depends(get_db)):
    """
    Get engines for a specific vehicle version.
    """
    vehicles = db.query(Vehicle).filter(Vehicle.version_id == version_id).all()
    engines = []
    seen = set()
    for v in vehicles:
        if v.engine and v.engine.id not in seen:
            seen.add(v.engine.id)
            engines.append({"id": v.engine.id, "description": v.engine.description, "displacement": v.engine.displacement})

    return engines

# --- Vehicle Lookup and Parts Search ---

@router.get("/vehicles/plate/{plate}", response_model=PlateLookupResponseSchema)
def lookup_vehicle_by_plate(plate: str, db: Session = Depends(get_db)):
    """
    Look up vehicle information by old or Mercosul license plate.
    """
    try:
        service = PlateLookupService(db)
        res = service.get_or_fetch_plate(plate)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/parts/search", response_model=PartsSearchResponseSchema)
def search_parts(
    plate: Optional[str] = Query(None, description="Vehicle plate number"),
    make: Optional[str] = Query(None, description="Vehicle make (e.g. Volkswagen)"),
    model: Optional[str] = Query(None, description="Vehicle model (e.g. T-Cross)"),
    year: Optional[int] = Query(None, description="Vehicle year (e.g. 2023)"),
    version: Optional[str] = Query(None, description="Vehicle version (e.g. Comfortline)"),
    engine: Optional[str] = Query(None, description="Vehicle engine (e.g. 1.0 TSI)"),
    category: Optional[str] = Query(None, description="Part category code"),
    query: Optional[str] = Query(None, description="Part query term, e.g. 'disco de freio'"),
    db: Session = Depends(get_db)
):
    """
    Search for compatible auto parts by plate OR direct vehicle parameters.
    """
    try:
        service = PartsSearchService(db)
        return service.search_parts(
            plate=plate,
            make=make,
            model=model,
            year=year,
            version=version,
            engine=engine,
            category=category,
            query=query
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/erp/mapping")
def create_or_update_erp_mapping(payload: ERPProductMappingCreateSchema, db: Session = Depends(get_db)):
    """
    Create or update an Autcom ERP Product mapping to a catalog part.
    """
    mapping = db.query(ERPProductMapping).filter(ERPProductMapping.erp_product_id == payload.erp_product_id).first()
    if not mapping:
        mapping = ERPProductMapping(
            erp_product_id=payload.erp_product_id,
            part_id=payload.part_id,
            manufacturer_code=payload.manufacturer_code,
            ean=payload.ean,
            mapping_type=ERPProductMappingType[payload.mapping_type],
            confidence=ConfidenceLevel.CONFIRMED if payload.verified else ConfidenceLevel.UNVERIFIED,
            verified=payload.verified
        )
        db.add(mapping)
    else:
        mapping.part_id = payload.part_id
        mapping.manufacturer_code = payload.manufacturer_code
        mapping.ean = payload.ean
        mapping.mapping_type = ERPProductMappingType[payload.mapping_type]
        mapping.verified = payload.verified
        mapping.confidence = ConfidenceLevel.CONFIRMED if payload.verified else ConfidenceLevel.UNVERIFIED

    db.commit()
    return {"status": "SUCCESS", "erp_product_id": payload.erp_product_id}

@router.post("/catalog/import")
async def import_catalog_file(file: UploadFile = File(...), mapping_json: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Import catalog applicability data from CSV, XLSX, JSON, or XML files.
    """
    importer = CatalogImporter(db)
    filename = file.filename.lower()
    content_bytes = await file.read()

    mapping_dict = None
    if mapping_json:
        import json
        try:
            mapping_dict = json.loads(mapping_json)
        except Exception:
            pass

    if filename.endswith(".csv"):
        res = importer.import_from_csv(content_bytes.decode("utf-8", errors="ignore"), source_name=filename, column_mapping=mapping_dict)
    elif filename.endswith(".xlsx"):
        res = importer.import_from_xlsx(content_bytes, source_name=filename, column_mapping=mapping_dict)
    elif filename.endswith(".json"):
        res = importer.import_from_json(content_bytes.decode("utf-8", errors="ignore"), source_name=filename, column_mapping=mapping_dict)
    elif filename.endswith(".xml"):
        res = importer.import_from_xml(content_bytes.decode("utf-8", errors="ignore"), source_name=filename, column_mapping=mapping_dict)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Allowed: .csv, .xlsx, .json, .xml")

    return res
